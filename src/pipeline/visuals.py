import random
from pathlib import Path
from urllib.parse import unquote

import requests

from src.config import env
from src.pipeline import image_gen, steam, wikipedia, yt_clip
from src.state import mark_clips_used


def _stream_download(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)


def fetch_clips(keywords: list[str], config: dict, out_dir: Path, state: dict) -> tuple[list[Path], bool]:
    orientation = config["visuals"].get("orientation", "portrait")
    headers = {"Authorization": env("PEXELS_API_KEY")}
    clip_paths = []
    recent_ids = set(state.get("recent_clip_ids", []))
    used_ids = []
    used_wikipedia = False
    # Off for channels whose keywords are decorative rather than about the
    # script's subject (the meme channel's "slime"/"arcade" backdrops) --
    # matching those to a Wikipedia article's photo would be a wrong match.
    use_wikipedia = config["visuals"].get("wikipedia", True)

    for i, keyword in enumerate(keywords):
        # A beat naming a specific real person/place/thing (e.g. "the Super
        # Bowl") should show that actual thing, not an arbitrary stock clip
        # that merely matches the keyword — try a real Wikipedia photo of it
        # first, and only fall back to stock footage when there's no
        # confident real-world match (an abstract/generic beat like "hands
        # typing" won't resolve to a specific article, which is correct).
        wiki_photo = wikipedia.real_photo_for(keyword) if use_wikipedia else None
        if use_wikipedia:
            print(f"[visuals] {keyword!r}: {'wikipedia hit' if wiki_photo else 'no wikipedia match, using stock'}")
        if wiki_photo:
            dest = out_dir / f"clip_{i}.jpg"
            try:
                _stream_download(wiki_photo, dest)
                clip_paths.append(dest)
                used_wikipedia = True
                continue
            except requests.RequestException:
                pass  # fall through to stock footage for this beat

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
        _stream_download(best["link"], dest)
        clip_paths.append(dest)

    if not clip_paths:
        raise RuntimeError("No stock clips found for any visual keyword")
    mark_clips_used(state, used_ids)
    return clip_paths, used_wikipedia


def download_media(urls: list[str], out_dir: Path) -> list[Path]:
    """Download a list of direct asset URLs (official art, screenshots, or
    video clips) — used for channels grounded in a real data source (AniList,
    RAWG) instead of a stock-footage keyword search. assemble.py tells
    images and real footage apart by extension, so plain URLs just need to
    preserve the real one. Two special, non-plain-URL forms get routed to a
    dedicated fetcher instead of a raw download, since neither is a simple
    file: a Steam trailer's ".m3u8" is a streaming manifest, not a video
    file, and "youtube-clip://<id>" is a marker (see anilist.trailer_marker)
    naming a specific YouTube video rather than a URL at all. A third form,
    "ai-image://<url-encoded prompt>", isn't sourced from anywhere at all --
    it's rendered on demand by image_gen (Cloudflare Workers AI), the one
    deliberately-AI-generated visual in this project; see script_gen_meme.py
    for why that channel is the named exception."""
    paths = []
    for i, url in enumerate(urls):
        if url.startswith("youtube-clip://"):
            dest = out_dir / f"media_{i}.mp4"
            if yt_clip.fetch_clip(url.removeprefix("youtube-clip://"), dest):
                paths.append(dest)
            continue

        if url.startswith("ai-image://"):
            prompt = unquote(url.removeprefix("ai-image://"))
            dest = out_dir / f"media_{i}.jpg"
            if image_gen.generate_image(prompt, dest):
                paths.append(dest)
            continue

        clean = url.lower().split("?")[0]
        if ".m3u8" in clean:
            dest = out_dir / f"media_{i}.mp4"
            if steam.fetch_trailer_clip(url, dest):
                paths.append(dest)
            continue

        if clean.endswith((".mp4", ".webm", ".mov")):
            ext = Path(clean).suffix
        elif clean.endswith(".webp"):
            ext = ".webp"
        elif clean.endswith(".png"):
            ext = ".png"
        else:
            ext = ".jpg"
        dest = out_dir / f"media_{i}{ext}"
        _stream_download(url, dest)
        paths.append(dest)
    return paths
