"""Steam's storefront API (undocumented but stable and widely used, no key
needed) — real trailer clips for games, used alongside RAWG's screenshots on
the gaming channel's upcoming-release videos. Unlike RAWG, Steam doesn't
publish terms explicitly granting third-party reuse of this data, so this is
in the same category as the YouTube-sourced anime footage (src/pipeline/
yt_clip.py): real footage that often contains actual gameplay, but without
an explicit permission grant behind it — a deliberate, disclosed choice
(see project memory), not an oversight."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import requests

from src.config import env

APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
_STEAM_APP_RE = re.compile(r"store\.steampowered\.com/app/(\d+)")


def steam_appid_for(rawg_game_id: int) -> int | None:
    resp = requests.get(
        f"https://api.rawg.io/api/games/{rawg_game_id}/stores",
        params={"key": env("RAWG_API_KEY")},
        timeout=15,
    )
    resp.raise_for_status()
    for entry in resp.json().get("results", []):
        match = _STEAM_APP_RE.search(entry.get("url", ""))
        if match:
            return int(match.group(1))
    return None


def trailer_url_for(appid: int) -> str | None:
    resp = requests.get(APPDETAILS_URL, params={"appids": appid}, timeout=15)
    resp.raise_for_status()
    entry = resp.json().get(str(appid), {})
    if not entry.get("success"):
        return None
    movies = entry.get("data", {}).get("movies", [])
    return movies[0]["hls_h264"] if movies else None


def fetch_trailer_clip(hls_url: str, dest: Path, duration: float = 6.0) -> bool:
    """Pull the first `duration` seconds of an HLS trailer stream into a
    local mp4. Returns False instead of raising on any failure — a single
    stale/expired stream URL (these carry a signed, time-limited token)
    shouldn't take down the whole video; the caller just skips that slot."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", hls_url, "-t", str(duration), "-c", "copy", str(dest)],
            check=True, capture_output=True, timeout=60,
        )
        return dest.exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
