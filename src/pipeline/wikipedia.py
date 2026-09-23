"""Wikipedia's public REST API (no auth, no key) — lets a video's visuals
match what the narration is actually naming instead of generic stock footage
(narration mentions "the Super Bowl" -> the Super Bowl's own real photo, not
an arbitrary football clip that merely matches the keyword). Images pulled
from here are real Wikimedia Commons photographs, same "sourced, not
generated" spirit as this project's other real-asset channels (AniList,
RAWG) — see feedback_sourced_not_generated_images."""

from __future__ import annotations

import re

import requests

SEARCH_URL = "https://en.wikipedia.org/w/rest.php/v1/search/page"
HEADERS = {"User-Agent": "auto-channel/1.0 (https://github.com/networkmoneytime-wq/auto-channel)"}


def search(query: str, limit: int = 1) -> list[dict]:
    resp = requests.get(SEARCH_URL, params={"q": query, "limit": limit}, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json().get("pages", [])


def real_photo_for(query: str) -> str | None:
    """Best-effort: resolve `query` to a real Wikipedia article and return a
    URL to a real photo from it, or None when there's no confident match —
    no search hit, no page image, or the only image is a logo/diagram.

    Uses the search hit's own thumbnail rather than that page's summary/
    infobox image: the two aren't always the same file (a franchise/brand
    page's infobox commonly shows its logo — e.g. "Eiffel Tower" itself
    resolves to a logo via /page/summary/ even though the search result for
    the same page carries an actual tower photo as its thumbnail), and the
    search thumbnail was the one that was consistently a real photo across
    manual testing. It's tiny (60px) by default; Wikimedia thumbnail URLs
    embed the requested width in the path itself, so asking for the same
    file at 1080px is just a string substitution, not a second lookup.

    Wikimedia always renders SVG thumbnails to raster, so the delivered URL
    for a logo/diagram ends in ".svg.png" rather than ".svg" — matching the
    substring anywhere in the path (not just the extension) is what actually
    catches these; endswith(".svg") would miss every single one."""
    try:
        pages = search(query, limit=1)
        if not pages:
            return None
        thumb = pages[0].get("thumbnail")
        if not thumb or ".svg" in thumb["url"].lower():
            return None
        url = thumb["url"]
        if url.startswith("//"):
            url = "https:" + url
        return re.sub(r"/\d+px-", "/1080px-", url, count=1)
    except requests.RequestException as e:
        # Distinct from "no confident match" so the two don't look identical
        # in logs — a real network/API failure here is worth knowing about,
        # not silently indistinguishable from "this topic just isn't a
        # specific enough thing to have a Wikipedia photo."
        print(f"[wikipedia] request failed for {query!r}: {e}")
        return None
