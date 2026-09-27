from __future__ import annotations

import random
import subprocess
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Anything wider than this (width / height) is shown whole over a blurred copy
# of itself instead of cropped to fill: a 16:9 screenshot or photo cropped to a
# 9:16 frame keeps only its middle third and usually loses the subject.
MAX_CROP_ASPECT = 0.75


def _needs_blur_fit(path: Path) -> bool:
    try:
        from PIL import Image

        with Image.open(path) as im:
            w, h = im.size
        return w / h > MAX_CROP_ASPECT
    except Exception:
        return False  # can't tell: keep the crop-to-fill framing


def _clip_durations(n: int, total: float, min_d: float, max_d: float) -> list[float]:
    """Split `total` seconds across `n` clips with random per-clip weight
    instead of one uniform length — alternating fast snaps and slow
    breathers reads as intentional editing, where identical-length cuts back
    to back reads as robotic (and is far slower-paced than what performs on
    TikTok/Shorts/Reels).

    Uses water-filling rather than clamp-then-rescale: a naive rescale after
    clamping re-inflates the clips already pinned at max_d past the cap
    whenever several land there at once, which defeats the cap. Clips get
    pinned to a bound only as the remaining pool forces them to, and only
    the still-free clips absorb each redistribution."""
    weights = [random.uniform(0.45, 1.6) for _ in range(n)]
    durations = [0.0] * n
    free = list(range(n))
    free_total = total

    while free:
        w_sum = sum(weights[i] for i in free)
        share = {i: free_total * weights[i] / w_sum for i in free}
        violators = [i for i in free if share[i] < min_d or share[i] > max_d]
        if not violators:
            for i in free:
                durations[i] = share[i]
            break
        for i in violators:
            durations[i] = min_d if share[i] < min_d else max_d
            free_total -= durations[i]
            free.remove(i)

    # Only mathematically possible to violate the bounds here when n is too
    # small for `total` even with every clip pinned at max_d (or too large
    # even at min_d) — spread that unavoidable leftover across the pinned
    # clips rather than drifting the total away from audio_duration.
    drift = total - sum(durations)
    if abs(drift) > 1e-6:
        pinned = [i for i in range(n) if i not in free]
        bump = drift / len(pinned)
        for i in pinned:
            durations[i] += bump
    return durations


def assemble_video(
    clip_paths: list[Path],
    voiceover_path: Path,
    audio_duration: float,
    captions_path: Path,
    config: dict,
    out_path: Path,
    music_path: Path | None = None,
) -> Path:
    width = config["video"]["width"]
    height = config["video"]["height"]
    min_clip = config["video"]["min_clip_sec"]
    max_clip = config["video"].get("max_clip_sec", min_clip * 3)
    durations = _clip_durations(len(clip_paths), audio_duration, min_clip, max_clip)

    inputs = []
    filter_parts = []
    elapsed = 0.0
    frames_so_far = 0
    for i, (clip, per_clip) in enumerate(zip(clip_paths, durations)):
        # Frames for this segment, allocated by cumulative rounding so the
        # segments add up to the narration's length instead of each one
        # drifting by up to half a frame.
        elapsed += per_clip
        frames = max(1, round(elapsed * 30) - frames_so_far)
        frames_so_far += frames
        if Path(clip).suffix.lower() in IMAGE_EXTS:
            # Still image -> Ken Burns zoom, cropped to frame first so the
            # pan/zoom operates on an already-correctly-framed image. The image
            # goes in as a single frame and zoompan expands it into `frames`
            # frames. It used to be looped at 30 fps *and* given d=frames, so
            # every looped frame expanded into `frames` frames again: the first
            # still in a video lasted minutes, nothing after it was ever reached
            # (anime showed its cover art for the whole video, restarting the
            # zoom every clip length), and the encode only stopped at -t below.
            inputs += ["-i", str(clip)]
            fill = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
            if _needs_blur_fit(Path(clip)):
                framed = (
                    f"[{i}:v]split[a{i}][b{i}];"
                    f"[a{i}]{fill},boxblur=40:10,eq=brightness=-0.1[bg{i}];"
                    f"[b{i}]scale={width}:{height}:force_original_aspect_ratio=decrease[fg{i}];"
                    f"[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2"
                )
            else:
                framed = f"[{i}:v]{fill}"
            filter_parts.append(
                f"{framed},"
                f"zoompan=z='min(zoom+0.0012,1.2)':d={frames}:s={width}x{height}:fps=30,"
                f"setsar=1[v{i}]"
            )
            continue
        inputs += ["-i", str(clip)]
        # d=1 keeps zoompan's per-frame zoom increment without holding/duplicating
        # frames, so real footage plays at its native rate while still gaining a
        # slow, continuous zoom-in — the "motion never stops" look that stands out
        # against static stock-footage cuts in top-performing shorts. Randomizing
        # the rate/cap per clip instead of one fixed value avoids every single cut
        # moving at the same mechanical speed, which itself becomes a recognizable
        # "auto-generated" tell once you've seen a few videos from the channel.
        # `pzoom` (the previous frame's zoom), not `zoom`: with d=1 every frame is
        # a new input frame and `zoom` starts over at 1 each time, so the old
        # `zoom+rate` expression never zoomed at all.
        rate = random.uniform(0.0005, 0.0014)
        cap = random.uniform(1.10, 1.22)
        # tpad first: a stock clip shorter than its slot used to end early and
        # pull the whole video short of the narration, so -shortest cut the
        # last words of the voiceover (dailyap's test video lost half a second).
        # Holding its last frame keeps every slot its full length.
        filter_parts.append(
            f"[{i}:v]tpad=stop_mode=clone:stop_duration={per_clip:.3f},"
            f"trim=0:{per_clip:.3f},setpts=PTS-STARTPTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps=30,"
            f"zoompan=z='min(pzoom+{rate:.4f},{cap:.3f})':d=1:s={width}x{height}:fps=30,"
            f"setsar=1[v{i}]"
        )
    concat_inputs = "".join(f"[v{i}]" for i in range(len(clip_paths)))
    filter_complex = (
        ";".join(filter_parts)
        + f";{concat_inputs}concat=n={len(clip_paths)}:v=1:a=0[vcat]"
        + f";[vcat]ass={captions_path}[vout]"
    )

    audio_idx = len(clip_paths)
    audio_inputs = ["-i", str(voiceover_path)]
    audio_map = f"{audio_idx}:a"

    if music_path is not None:
        music_idx = audio_idx + 1
        audio_inputs += ["-i", str(music_path)]
        # Trim/loop the track to the video's length and duck it well under the
        # narration (voiceover stays untouched, music sits quietly beneath it).
        filter_complex += (
            f";[{music_idx}:a]aloop=loop=-1:size=2e9,atrim=0:{audio_duration:.3f},"
            f"asetpts=PTS-STARTPTS,volume=0.10[music]"
            f";[{audio_idx}:a][music]amix=inputs=2:duration=first:dropout_transition=0,"
            f"volume=2[aout]"
        )
        audio_map = "[aout]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        *audio_inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", audio_map,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        "-shortest",
        # -shortest alone isn't reliable here: it stops at the shortest
        # mapped stream's EOF, but that detection can misfire on this
        # filter graph (looped -loop 1 image inputs feeding concat +
        # zoompan) and let the encode run for many minutes past the real
        # audio length instead of cutting at ~audio_duration. -t on the
        # output is a hard, unambiguous cutoff that doesn't depend on any
        # stream's EOF propagating correctly, so it stays even with
        # -shortest still in place as a second line of defense.
        "-t", f"{audio_duration:.3f}",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return out_path
