from __future__ import annotations

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


def mark_hook_used(state: dict, hook_id: str) -> None:
    recent = state.setdefault("recent_hooks", [])
    recent.append(hook_id)
    del recent[:-5]
    save_state(state)


def mark_clips_used(state: dict, clip_ids: list) -> None:
    recent = state.setdefault("recent_clip_ids", [])
    recent.extend(clip_ids)
    del recent[:-60]
    save_state(state)


def log_upload(
    state: dict, platform: str, video_id: str, title: str, topic: str | None = None, hook_id: str | None = None
) -> None:
    """`topic`/`hook_id` are what made this specific video (which real subject,
    which hook archetype) — src/pipeline/performance.py joins them back to
    this same upload's view count to learn which of each actually perform.
    Optional and omitted for content types that don't have one (e.g. a
    channel's grounded "UPCOMING" roundups have no single hook)."""
    record = {
        "platform": platform,
        "video_id": video_id,
        "title": title,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if topic is not None:
        record["topic"] = topic
    if hook_id is not None:
        record["hook_id"] = hook_id
    state["uploads"].append(record)
    save_state(state)
