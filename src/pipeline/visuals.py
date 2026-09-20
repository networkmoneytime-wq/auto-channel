from pathlib import Path

import requests

from src.config import env


def fetch_clips(keywords: list[str], config: dict, out_dir: Path) -> list[Path]:
    orientation = config["visuals"].get("orientation", "portrait")
    headers = {"Authorization": env("PEXELS_API_KEY")}
    clip_paths = []

    for i, keyword in enumerate(keywords):
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params={"query": keyword, "orientation": orientation, "per_page": 3},
            timeout=30,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if not videos:
            continue

        video_files = sorted(
            videos[0]["video_files"],
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
