import shutil
import tempfile
import traceback
from pathlib import Path

from src.config import load_config, output_dir
from src.pipeline.assemble import assemble_video
from src.pipeline.captions import build_captions
from src.pipeline.ideate import pick_topic
from src.pipeline.metadata import generate_metadata
from src.pipeline.script_gen import generate_script
from src.pipeline.visuals import fetch_clips
from src.pipeline.voiceover import synthesize_voiceover
from src.state import load_state, log_upload, mark_topic_used, save_state
from src.uploaders import instagram, tiktok, youtube

UPLOADERS = {
    "youtube": youtube.upload_short,
    "tiktok": tiktok.upload_short,
    "instagram": instagram.upload_short,
}


def run() -> None:
    config = load_config()
    state = load_state()

    topic = pick_topic(state)
    print(f"[ideate] topic: {topic}")

    script = generate_script(topic, config)
    print(f"[script] {len(script['script'].split())} words")

    metadata = generate_metadata(script["script"], config)
    print(f"[metadata] title: {metadata['title']}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        voiceover_path = tmp_dir / "voiceover.mp3"
        word_boundaries = synthesize_voiceover(script["script"], config, voiceover_path)
        print(f"[voiceover] {len(word_boundaries)} words synthesized")

        clip_paths = fetch_clips(script["visual_keywords"], config, tmp_dir)
        print(f"[visuals] fetched {len(clip_paths)} clips")

        captions_path = build_captions(word_boundaries, config, tmp_dir / "captions.ass")
        last_word = word_boundaries[-1]
        audio_duration = last_word["offset"] + last_word["duration"]

        final_path = output_dir() / f"{topic[:40].strip().replace(' ', '_')}.mp4"
        assemble_video(clip_paths, voiceover_path, audio_duration, captions_path, config, final_path)
        print(f"[assemble] video written to {final_path}")

        mark_topic_used(state, topic)

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
