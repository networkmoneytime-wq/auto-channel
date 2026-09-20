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
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", str(voiceover_path),
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", f"{audio_idx}:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        "-shortest",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return out_path
