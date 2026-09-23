"""Pulls a short clip from a specific YouTube video via yt-dlp — used for
real episode-footage trailers (anime, via AniList's trailer field, which
names a YouTube video id but hosts no video itself). This is the riskiest
sourcing path in this project: no permission grant from YouTube, downloading
violates YouTube's ToS regardless of what the clip is used for, and official
trailers like these are typically already Content-ID-fingerprinted, so an
upload built from one likely gets auto-claimed (ad revenue redirected to the
rights holder, not a takedown or ban). A deliberate, disclosed choice made
with the user, not an oversight — see project memory."""

from __future__ import annotations

import subprocess
from pathlib import Path


def fetch_clip(video_id: str, dest: Path, start: int = 0, duration: int = 6) -> bool:
    try:
        subprocess.run(
            [
                "yt-dlp",
                "--download-sections", f"*{start}-{start + duration}",
                "-f", "best[height<=1080]/best",
                "-o", str(dest),
                "--no-playlist",
                "--quiet",
                f"https://www.youtube.com/watch?v={video_id}",
            ],
            check=True, capture_output=True, timeout=90,
        )
        return dest.exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
