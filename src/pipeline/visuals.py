from __future__ import annotations

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


def _subject_gallery(subject: str | None) -> list[tuple[str, str]]:
    """(thumbnail URL, credit line) for up to 4 free photos from the Wikipedia
    article the topic's subject names, or [] when it names no article. The
    topic lines are written "Named thing: what happened", so the subject is
    everything before the colon."""
    if not subject:
        return []
    title = wikipedia.subject_article(subject)
    if not title:
        print(f"[visuals] subject {subject!r}: no Wikipedia article by that name")
        return []
    urls = wikipedia.article_photo_urls(title, limit=6)
    keys = [wikipedia.file_key(u) for u in urls]
    credits = wikipedia.credits_for([k for k in keys if k])
    gallery = [(u, credits[k]) for u, k in zip(urls, keys) if k and credits.get(k)]
    print(f"[visuals] subject {subject!r}: article {title!r}, {len(gallery[:4])} usable photos of {len(urls)}")
    return gallery[:4]


def fetch_clips(
    keywords: list[str], config: dict, out_dir: Path, state: dict, subject: str | None = None
) -> tuple[list[Path], list[str]]:
    """One visual per keyword. Returns the clip paths and a credit line for
    every Wikimedia Commons photo used (empty when none were)."""
    orientation = config["visuals"].get("orientation", "portrait")
    headers = {"Authorization": env("PEXELS_API_KEY")}
    clip_paths = []
    recent_ids = set(state.get("recent_clip_ids", []))
    used_ids = []
    credits = []
    used_files = set()
    # Off for channels whose keywords are decorative rather than about the
    # script's subject (the meme channel's "slime"/"arcade" backdrops) --
    # matching those to a Wikipedia article's photo would be a wrong match.
    use_wikipedia = config["visuals"].get("wikipedia", True)

    # Real photos of what the video is about, spread over the video (beats 0, 2,
    # 5, 8 in a 11-beat script) so the subject is on screen from the first
    # second and comes back, with stock footage between.
    try:
        gallery = _subject_gallery(subject) if use_wikipedia else []
    except Exception as e:  # photos are a bonus, never worth losing the video over
        print(f"[visuals] subject photos failed: {e!r}")
        gallery = []
    slots = {int(j * len(keywords) / len(gallery)): gallery[j] for j in range(len(gallery))} if gallery else {}

    def place_photo(thumb_url: str, credit: str | None, i: int) -> bool:
        key = wikipedia.file_key(thumb_url)
        if not key or key in used_files:
            return False
        if credit is None:
            credit = wikipedia.credits_for([key]).get(key) if key else None
            if not credit:
                return False
        photo = wikipedia.download_photo(thumb_url, out_dir / f"clip_{i}")
        if not photo:
            return False
        clip_paths.append(photo)
        used_files.add(key)
        credits.append(credit)
        return True

    for i, keyword in enumerate(keywords):
        # "Name | plain stock term": a beat that names a real person, place or
        # thing gets a real photo of it, and the stock term is what to show if
        # there is no free photo. A bare keyword is just a stock search term.
        name, _, fallback = keyword.partition("|")
        name, fallback = name.strip(), fallback.strip()
        stock_query = fallback or name

        # Every outcome is logged as what actually happened: this used to log
        # "wikipedia hit" for a photo whose download then failed, and the
        # fallback to stock was silent, so the whole feature looked fine while
        # doing nothing.
        if use_wikipedia:
            try:
                if i in slots and place_photo(slots[i][0], slots[i][1], i):
                    print(f"[visuals] beat {i}: real photo of the subject")
                    continue
                photo_url, detail = wikipedia.find_photo(name)
                if photo_url:
                    if place_photo(photo_url, None, i):
                        print(f"[visuals] {name!r}: wikipedia photo of {detail!r}")
                        continue
                    detail = f"photo of {detail!r} unusable (used already, license, or download)"
                if wikipedia.looks_like_a_name(name):
                    print(f"[visuals] {name!r}: stock {stock_query!r} ({detail})")
            except Exception as e:  # photos are a bonus, never worth losing the video over
                print(f"[visuals] {name!r}: wikipedia step failed ({e!r}), using stock")

        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params={"query": stock_query, "orientation": orientation, "per_page": 15},
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
        # stops the same specific clip resurfacing video after video. Only the
        # top 5, though: further down Pexels' ranking is mostly loose matches
        # ("gull wing doors" -> seagulls, "countdown graphic" -> a New Year sign).
        pool = videos[: min(5, len(videos))]
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
    return clip_paths, credits


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
