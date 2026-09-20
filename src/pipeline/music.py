"""Optional background music beds — royalty-free tracks from Kevin MacLeod
(incompetech.com), licensed CC BY 4.0. Only used on a random subset of videos
so music is variety, not a blanket rule, and the track is picked from a small
mood set that loosely fits the channel."""

from __future__ import annotations

import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MUSIC_DIR = ROOT / "assets" / "music"

ATTRIBUTION_SUFFIX = "(CC BY 4.0)"

TRACKS = [
    {"file": "ancient_mystery_waltz_presto.mp3", "title": "Ancient Mystery Waltz (Presto)", "mood": "mysterious"},
    {"file": "brain_dance.mp3", "title": "Brain Dance", "mood": "driving"},
    {"file": "magistar.mp3", "title": "Magistar", "mood": "epic"},
    {"file": "newer_wave.mp3", "title": "Newer Wave", "mood": "uplifting"},
]

# Loose per-channel mood affinity, just to bias which track gets picked when
# music is used — not a strict rule.
CHANNEL_MOODS = {
    "dailyap": ["mysterious", "uplifting"],
    "cars": ["driving", "uplifting"],
    "gaming": ["driving", "epic"],
    "technology": ["driving", "uplifting"],
    "anime": ["epic", "mysterious"],
}


def maybe_pick_track(channel: str, probability: float = 0.35) -> dict | None:
    if random.random() > probability:
        return None
    moods = CHANNEL_MOODS.get(channel, [t["mood"] for t in TRACKS])
    candidates = [t for t in TRACKS if t["mood"] in moods] or TRACKS
    return random.choice(candidates)


def track_path(track: dict) -> Path:
    return MUSIC_DIR / track["file"]


def attribution_line(track: dict) -> str:
    return f'Music: "{track["title"]}" by Kevin MacLeod (incompetech.com) {ATTRIBUTION_SUFFIX}'
