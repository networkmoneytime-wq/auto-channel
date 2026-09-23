import random
from pathlib import Path

import requests

from src.config import env
from src.state import mark_clips_used


def fetch_clips(keywords: list[str], config: dict, out_dir: Path, state: dict) -> list[Path]:
    orientation = config["visuals"].get("orientation", "portrait")
    headers = {"Authorization": env("PEXELS_API_KEY")}
    clip_paths = []
    recent_ids = set(state.get("recent_clip_ids", []))
    used_ids = []

    for i, keyword in enumerate(keywords):
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params={"query": keyword, "orientation": orientation, "per_page": 15},
            timeout=30,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if not videos:
            continue

        # Pexels' top result for a common keyword (space, history, city...) is
        # the same clip every time, across every channel and every run — a
        # handful of overused stock clips showing up repeatedly is a fast way
        # for an account to read as generic/automated. Picking randomly among
        # the top matches spreads runs across different real footage, and
        # skipping clips this channel posted recently (tracked in state)
        # stops the same specific clip resurfacing video after video.
        pool = videos[: min(8, len(videos))]
        fresh = [v for v in pool if v["id"] not in recent_ids]
        chosen = random.choice(fresh or pool)
        used_ids.append(chosen["id"])
        video_files = sorted(
            chosen["video_files"],
            key=lambda vf: abs((vf.get("height") or 0) - config["video"]["height"]),
        )
        best = next((vf for vf in video_files if vf.get("height", 0) >= 720), video_files[0])

        dest = out_dir / f"clip_{i}.mp4"
        with requests.get(best["link"], stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    f.write(chunk)
        clip_paths.append(dest)

    if not clip_paths:
        raise RuntimeError("No stock clips found for any visual keyword")
    mark_clips_used(state, used_ids)
    return clip_paths


def download_images(urls: list[str], out_dir: Path) -> list[Path]:
    paths = []
    for i, url in enumerate(urls):
        ext = ".png" if url.lower().split("?")[0].endswith(".png") else ".jpg"
        dest = out_dir / f"image_{i}{ext}"
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    f.write(chunk)
        paths.append(dest)
    return paths
