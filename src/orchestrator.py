import re
import shutil
import subprocess
import tempfile
import traceback
from pathlib import Path

from src.config import channel, load_config, output_dir
from src.pipeline.assemble import assemble_video
from src.pipeline.captions import build_captions
from src.pipeline.ideate import pick_topic
from src.pipeline.metadata import generate_metadata
from src.pipeline.music import attribution_line, maybe_pick_track, track_path
from src.pipeline.script_gen import generate_script
from src.pipeline.script_gen_anime import generate_anime_content
from src.pipeline.script_gen_gaming import generate_gaming_content
from src.pipeline.visuals import download_media, fetch_clips
from src.pipeline.voiceover import synthesize_voiceover
from src.state import load_state, log_upload, mark_hook_used, mark_topic_used, save_state
from src.uploaders import facebook, instagram, tiktok, youtube

def _probe_duration(path: Path) -> float:
    """The real duration of the rendered audio, read from the file itself via
    ffprobe. edge-tts's WordBoundary stream (what the previous approach
    trusted) can report a garbage timestamp for the final word — and the
    bad value isn't reliably huge, so a sanity ceiling on it alone isn't
    enough of a backstop. Reading the actual file removes the whole class
    of bug instead of trying to catch one symptom of it."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


UPLOADERS = {
    "youtube": youtube.upload_short,
    "tiktok": tiktok.upload_short,
    "instagram": instagram.upload_short,
    "facebook": facebook.upload_short,
}

# Channels whose content is grounded in a real external data source instead
# of a freeform LLM topic — each returns a dict shaped like generate_script's,
# plus "visual_mode": "media" (see below) when it wants its own sourced
# assets instead of a Pexels keyword search.
CONTENT_GENERATORS = {
    "anime": generate_anime_content,
    "gaming": generate_gaming_content,
}


def run() -> None:
    config = load_config()
    state = load_state()

    generate = CONTENT_GENERATORS.get(channel(), generate_script)

    topic = pick_topic(state)
    print(f"[ideate] topic: {topic}")

    script = generate(topic, config, state)
    hook_id = script.get("hook_id")
    print(f"[script] hook: {hook_id or 'n/a'}, {len(script['script'].split())} words")

    metadata = generate_metadata(script["script"], config)
    print(f"[metadata] title: {metadata['title']}")
    if script.get("attribution"):
        metadata["description"] = metadata["description"] + "\n\n" + script["attribution"]

    music_track = maybe_pick_track(channel())
    if music_track:
        metadata["description"] = metadata["description"] + "\n\n" + attribution_line(music_track)
        print(f"[music] using {music_track['title']}")
    else:
        print("[music] none this run")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        voiceover_path = tmp_dir / "voiceover.mp3"
        word_boundaries = synthesize_voiceover(script["script"], config, voiceover_path)
        print(f"[voiceover] {len(word_boundaries)} words synthesized")

        if script.get("visual_mode") == "media":
            clip_paths = download_media(script["media_urls"], tmp_dir)
            print(f"[visuals] downloaded {len(clip_paths)} sourced assets")
        else:
            clip_paths = fetch_clips(script["visual_keywords"], config, tmp_dir, state)
            print(f"[visuals] fetched {len(clip_paths)} clips")

        captions_path = build_captions(word_boundaries, config, tmp_dir / "captions.ass")
        audio_duration = _probe_duration(voiceover_path)
        print(f"[voiceover] actual duration: {audio_duration:.1f}s")
        # Backstop, not the primary defense (that's reading the real file
        # above instead of trusting word_boundaries): a script this length
        # can never legitimately run past a couple of minutes, so treat
        # anything wildly beyond that as a red flag — e.g. TTS synthesis
        # itself producing a corrupt file — and fail fast rather than
        # silently building a runaway video.
        if audio_duration > 180:
            raise RuntimeError(
                f"Implausible audio_duration ({audio_duration:.1f}s) for "
                f"{len(word_boundaries)} words"
            )

        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", topic[:40].strip()).strip("_")
        final_path = output_dir() / f"{safe_name}.mp4"
        music_path = track_path(music_track) if music_track else None
        assemble_video(clip_paths, voiceover_path, audio_duration, captions_path, config, final_path, music_path)
        print(f"[assemble] video written to {final_path}")

        mark_topic_used(state, topic)
        if hook_id:
            mark_hook_used(state, hook_id)

        for platform, uploader in UPLOADERS.items():
            if not config["platforms"].get(platform, {}).get("enabled"):
                continue
            try:
                video_id = uploader(final_path, metadata, config)
                log_upload(state, platform, video_id, metadata["title"])
                print(f"[upload:{platform}] ok -> {video_id}")
            except Exception:
                print(f"[upload:{platform}] FAILED")
                traceback.print_exc()

        shutil.copy(final_path, output_dir() / "last_run.mp4")

    save_state(state)


if __name__ == "__main__":
    run()
