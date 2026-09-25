"""Pulls a short clip from a specific YouTube video via yt-dlp — used for
real episode-footage trailers (anime, via AniList's trailer field, which
names a YouTube video id but hosts no video itself). This is the riskiest
sourcing path in this project: no permission grant from YouTube, downloading
violates YouTube's ToS regardless of what the clip is used for, and official
trailers like these are typically already Content-ID-fingerprinted, so an
upload built from one likely gets auto-claimed (ad revenue redirected to the
rights holder, not a takedown or ban). A deliberate, disclosed choice made
with the user, not an oversight — see project memory.

Confirmed 2026-09-25 via a manual CI run: YouTube answers GitHub-hosted
runners with "Sign in to confirm you're not a bot" for every video, so this
does not work from Actions at all (and even locally, stream URLs get cut off
after ~20 MB without a PO token). Callers must treat False as the normal
outcome in CI, not an exception."""

from __future__ import annotations

import subprocess
from pathlib import Path


def fetch_clip(video_id: str, dest: Path, start: int = 0, duration: int = 6) -> bool:
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--download-sections", f"*{start}-{start + duration}",
                "-f", "best[height<=1080]/best",
                "-o", str(dest),
                "--no-playlist",
                f"https://www.youtube.com/watch?v={video_id}",
            ],
            check=True, capture_output=True, text=True, timeout=90,
        )
        if not dest.exists():
            # A clean exit with no file written happens for reasons that
            # aren't a subprocess error (e.g. yt-dlp deciding sections
            # were out of range) -- worth knowing about, not just silently
            # skipping this beat like a real fetch failure would.
            print(f"[yt_clip] yt-dlp exited cleanly but wrote no file for {video_id}: {result.stdout[-300:]}")
        return dest.exists()
    except subprocess.CalledProcessError as e:
        print(f"[yt_clip] fetch failed for {video_id}: {(e.stderr or str(e))[-500:]}")
        return False
    except subprocess.TimeoutExpired:
        print(f"[yt_clip] fetch timed out for {video_id}")
        return False
