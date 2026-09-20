import json
from datetime import datetime, timezone

from src.config import state_path


def load_state() -> dict:
    p = state_path()
    if not p.exists():
        return {"used_topics": [], "uploads": []}
    with open(p) as f:
        return json.load(f)


def save_state(state: dict) -> None:
    with open(state_path(), "w") as f:
        json.dump(state, f, indent=2)


def mark_topic_used(state: dict, topic: str) -> None:
    state["used_topics"].append(topic)
    save_state(state)


def log_upload(state: dict, platform: str, video_id: str, title: str) -> None:
    state["uploads"].append(
        {
            "platform": platform,
            "video_id": video_id,
            "title": title,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_state(state)
