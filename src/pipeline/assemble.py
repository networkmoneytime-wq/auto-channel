from __future__ import annotations

import subprocess
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


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
    per_clip = max(config["video"]["min_clip_sec"], audio_duration / len(clip_paths))

    inputs = []
    filter_parts = []
    for i, clip in enumerate(clip_paths):
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
        filter_parts.append(
            f"[{i}:v]trim=0:{per_clip:.3f},setpts=PTS-STARTPTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps=30,setsar=1[v{i}]"
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
