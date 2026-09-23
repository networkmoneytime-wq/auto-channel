"""Background "brainrot"-style gameplay footage: a continuous, hyperstimulating
clip (Subway Surfers, Minecraft parkour, ...) running under narration and
burned captions -- the format's whole visual is this one decorative clip, not
tied to what the script is about. Real gameplay footage, same risk profile
already taken on for gaming/anime trailers (see src/pipeline/yt_clip.py) --
pulled from long compilations their own uploaders titled for reuse ("free to
use" / "no copyright"), sampled at a random offset each run so a handful of
source videos still produce a lot of visual variety."""

from __future__ import annotations

import random

# (video_id, length_seconds) -- long compilations, verified real and each
# titled by its own uploader as free/no-copyright for reuse. Easy to extend;
# add more (video_id, length) pairs as they're found.
BACKGROUND_VIDEOS = [
    ("zZ7AimPACzc", 59 * 60),  # Subway surfers 1 hour gameplay, no commentary, free to use
    ("L_fcrOyoWZ8", 66 * 60),  # Subway Surfers compilation, 1 hour HD
    ("vTfD20dbxho", 126 * 60),  # Subway Surfers compilation, 2 hours HD
    ("iKggOfcKM28", 62 * 60),  # Subway Surfers gameplay, no copyright, 4K, 1 hour
    ("85z7jqGAGcc", 149 * 60),  # Minecraft parkour gameplay, no copyright, 2 hours
]


def random_background_marker(duration: int) -> str:
    """A "youtube-clip://" marker (see visuals.download_media) for a random
    offset into a random background video, long enough to cover `duration`
    seconds of narration with room to spare."""
    video_id, length = random.choice(BACKGROUND_VIDEOS)
    latest_start = max(0, length - duration - 10)
    start = random.randint(0, latest_start) if latest_start > 0 else 0
    return f"youtube-clip://{video_id}?start={start}&duration={duration}"
