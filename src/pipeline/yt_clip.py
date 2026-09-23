"""Pulls a clip from a specific YouTube video via yt-dlp — used for real
episode-footage trailers (anime, via AniList's trailer field, which names a
YouTube video id but hosts no video itself) and for brainrot background
gameplay footage (src/pipeline/brainrot.py). This is the riskiest sourcing
path in this project: no permission grant from YouTube, downloading violates
YouTube's ToS regardless of what the clip is used for, and official trailers
like these are typically already Content-ID-fingerprinted, so an upload
built from one likely gets auto-claimed (ad revenue redirected to the rights
holder, not a takedown or ban). A deliberate, disclosed choice made with the
user, not an oversight — see project memory."""

from __future__ import annotations

import subprocess
from pathlib import Path


def fetch_clip(video_id: str, dest: Path, start: int = 0, duration: int = 6) -> bool:
    # A 6s trailer excerpt and a 60s brainrot background clip both call this;
    # scale the ceiling with what's actually being asked for rather than
    # sizing it for the short case and timing out the long one.
    timeout = max(90, duration * 3)
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
            check=True, capture_output=True, text=True, timeout=timeout,
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
