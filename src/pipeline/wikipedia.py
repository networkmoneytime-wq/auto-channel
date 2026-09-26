"""Wikipedia's public REST API (no auth, no key) — lets a video's visuals
match what the narration is actually naming instead of generic stock footage
(narration mentions "the Super Bowl" -> the Super Bowl's own real photo, not
an arbitrary football clip that merely matches the keyword). Images pulled
from here are real Wikimedia Commons photographs, same "sourced, not
generated" spirit as this project's other real-asset channels (AniList,
RAWG) — see feedback_sourced_not_generated_images.

Only the beats that name a specific thing get a photo (see find_photo); every
generic beat stays stock footage. History: this module used to look up a photo
for every keyword and take the top search hit, and the downloads it planned
never worked (see download_photo), so for weeks the logs said "wikipedia hit"
while every clip was really stock footage."""

from __future__ import annotations

import re
from pathlib import Path

import requests

SEARCH_URL = "https://en.wikipedia.org/w/rest.php/v1/search/page"
HEADERS = {"User-Agent": "auto-channel/1.0 (https://github.com/networkmoneytime-wq/auto-channel)"}

# Wikimedia only serves a fixed set of thumbnail widths (asking for 1080px or
# 640px is an HTTP 400), and answers 403 to any request without a descriptive
# User-Agent. Widest first: a source narrower than the width asked for is
# refused too, so fall through to the next.
THUMB_WIDTHS = (1280, 960, 500)

_NOT_A_PHOTO = re.compile(r"logo|wordmark|icon|flag_of|coat_of_arms|signature|diagram|locator|_map", re.I)
_LOWERCASE_OK = {"of", "the", "and", "a", "an", "in", "on", "at", "to", "for", "de", "la", "von", "van", "vs"}
_STOPWORDS = {"the", "a", "an", "of", "in", "on", "at", "and", "to", "for", "by", "with"}


def search(query: str, limit: int = 1) -> list[dict]:
    resp = requests.get(SEARCH_URL, params={"q": query, "limit": limit}, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json().get("pages", [])


def looks_like_a_name(keyword: str) -> bool:
    """True for a Proper Case phrase ("Great Molasses Flood", "Voyager 1",
    "Tetris"): every word capitalized or numeric, apart from small joining
    words. The script prompt asks the LLM to write named subjects this way and
    everything else in lowercase, so a lowercase stock term ("hands typing")
    never gets a Wikipedia lookup — real footage of the action beats a random
    article thumbnail."""
    words = re.findall(r"[^\s]+", keyword.strip())
    if not words:
        return False
    return all(any(c.isupper() or c.isdigit() for c in w) or w.lower() in _LOWERCASE_OK for w in words)


def _tokens(text: str) -> set[str]:
    text = re.sub(r"\([^)]*\)", " ", text.lower())  # "(film)"-style qualifiers
    text = re.sub(r"['’]s\b", "", text)
    words = (w for w in re.findall(r"[a-z0-9]+", text) if w not in _STOPWORDS)
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words}


def names_article(keyword: str, title: str) -> bool:
    """The keyword is the article's name, or the name contains the keyword
    ("Amazon Fire Phone" -> "Fire Phone"): every word of one side appears in
    the other. Deliberately strict — the top search hit for a loose phrase is
    often unrelated ("molasses thick freeze" -> the Applejack article)."""
    k, t = _tokens(keyword), _tokens(title)
    return bool(k) and bool(t) and (k <= t or t <= k)


def find_photo(keyword: str) -> tuple[str | None, str]:
    """(thumbnail URL, article title) for a real, freely-licensed photo of the
    thing `keyword` names, or (None, reason) when there isn't a confident one.

    Uses the search hit's own thumbnail rather than that page's summary/
    infobox image: the two aren't always the same file (a franchise/brand
    page's infobox commonly shows its logo — e.g. "Eiffel Tower" itself
    resolves to a logo via /page/summary/ even though the search result for
    the same page carries an actual tower photo as its thumbnail), and the
    search thumbnail was the one that was consistently a real photo across
    manual testing. It's tiny (60px); download_photo swaps in a real width.

    Wikimedia always renders SVG thumbnails to raster, so the delivered URL
    for a logo/diagram ends in ".svg.png" rather than ".svg" — matching the
    substring anywhere in the path (not just the extension) is what actually
    catches these; endswith(".svg") would miss every single one.

    Only files hosted on Wikimedia Commons are used. Commons holds free
    media only; the English Wikipedia's own uploads (paths under
    /wikipedia/en/) are mostly non-free "fair use" images — logos, product
    shots, game screenshots — that this project has no right to repost."""
    if not looks_like_a_name(keyword):
        return None, "not a proper name"
    try:
        pages = search(keyword, limit=3)
    except requests.RequestException as e:
        # Distinct from "no confident match" so the two don't look identical
        # in logs — a real network/API failure here is worth knowing about,
        # not silently indistinguishable from "this topic just isn't a
        # specific enough thing to have a Wikipedia photo."
        return None, f"search failed: {e}"
    named = [p for p in pages if names_article(keyword, p.get("title", ""))]
    if not named:
        top = pages[0]["title"] if pages else "nothing"
        return None, f"no article by that name (top hit: {top!r})"
    for page in named:
        thumb = page.get("thumbnail")
        if not thumb:
            continue
        url = thumb["url"]
        if url.startswith("//"):
            url = "https:" + url
        if ".svg" in url.lower() or "/wikipedia/commons/" not in url:
            continue
        if _NOT_A_PHOTO.search(url.rsplit("/", 1)[0]):
            continue  # a logo, flag, map or diagram uploaded as a raster file
        return url, page["title"]
    return None, f"article {named[0]['title']!r} has no free photo"


def download_photo(thumb_url: str, dest_stem: Path) -> Path | None:
    """Saves a real-sized copy of `thumb_url` (a search thumbnail) next to
    `dest_stem`, with the extension its content type calls for, and returns
    the path — or None after printing why it failed. (This step used to fail
    silently for every photo: no User-Agent -> 403, and the 1080px width it
    asked for is not one Wikimedia serves -> 400.)"""
    last = "no attempt"
    for width in THUMB_WIDTHS:
        url = re.sub(r"/\d+px-", f"/{width}px-", thumb_url, count=1)
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=30) as r:
                if r.status_code != 200:
                    last = f"HTTP {r.status_code} at {width}px"
                    continue
                ext = ".png" if "png" in r.headers.get("content-type", "") else ".jpg"
                dest = dest_stem.with_suffix(ext)
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
                return dest
        except requests.RequestException as e:
            last = str(e)
    print(f"[wikipedia] photo download failed ({last}): {thumb_url}")
    return None
