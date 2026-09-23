from __future__ import annotations

import random
import subprocess
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


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
    for i, (clip, per_clip) in enumerate(zip(clip_paths, durations)):
        if Path(clip).suffix.lower() in IMAGE_EXTS:
            # Still image -> looped video + a gentle Ken Burns zoom, cropped to frame
            # first so the pan/zoom operates on an already-correctly-framed image.
            frames = max(1, round(per_clip * 30))
            inputs += ["-loop", "1", "-framerate", "30", "-t", f"{per_clip:.3f}", "-i", str(clip)]
            filter_parts.append(
                f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
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
        rate = random.uniform(0.0005, 0.0014)
        cap = random.uniform(1.10, 1.22)
        filter_parts.append(
            f"[{i}:v]trim=0:{per_clip:.3f},setpts=PTS-STARTPTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps=30,"
            f"zoompan=z='min(zoom+{rate:.4f},{cap:.3f})':d=1:s={width}x{height}:fps=30,"
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
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return out_path
