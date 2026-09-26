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
from urllib.parse import quote, unquote

import requests

SEARCH_URL = "https://en.wikipedia.org/w/rest.php/v1/search/page"
MEDIA_LIST_URL = "https://en.wikipedia.org/api/rest_v1/page/media-list/{title}"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "auto-channel/1.0 (https://github.com/networkmoneytime-wq/auto-channel)"}

# Licenses this project will show: public domain, CC0, CC BY and CC BY-SA. The
# last two need credit, which credits_for() builds. Commons holds only free
# media, but GFDL-only and similar files would need more than a credit line.
_USABLE_LICENSE = re.compile(r"^(public domain|pd\b|cc0|cc[ -]by(?:[ -]sa)?\b)", re.I)

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


def _tokens(text: str) -> list[str]:
    text = re.sub(r"\([^)]*\)", " ", text.lower())  # "(film)"-style qualifiers
    text = re.sub(r"['\u2019]s\b", "", text)
    words = (w for w in re.findall(r"[a-z0-9]+", text) if w not in _STOPWORDS)
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words]


_NAME_SUFFIXES = {"ii", "iii", "iv", "jr", "sr"}


def names_article(keyword: str, title: str) -> bool:
    """The keyword is the article's name, or the name contains the keyword
    ("Amazon Fire Phone" -> "Fire Phone"; "Sealand" -> "Principality of
    Sealand"): every word of one side appears in the other. Deliberately
    strict — the top search hit for a loose phrase is often unrelated
    ("molasses thick freeze" -> the Applejack article). The same words in a
    different order don't count ("The Ford Edsel" is the car, "Edsel Ford" the
    man who ran the company), and neither does a person's name that only adds
    a generation suffix ("Edsel Ford II")."""
    k, t = _tokens(keyword), _tokens(title)
    if not k or not t:
        return False
    if set(k) == set(t):
        return k == t
    if set(t) < set(k):
        return True
    return set(k) < set(t) and not (set(t) - set(k)) <= _NAME_SUFFIXES


def _named(keyword: str, pages: list[dict]) -> list[dict]:
    """The pages whose titles the keyword names, in the search's own relevance
    order (which beats any ranking of mine: "Sealand" is the micronation on
    top and a shipping company lower down, and the reverse looks tidier)."""
    return [p for p in pages if names_article(keyword, p.get("title", ""))]


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
    named = _named(keyword, pages)
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


def file_key(url: str) -> str | None:
    """The Commons file name in a thumbnail or original URL
    ("BostonMolassesDisaster.jpg"), which identifies a photo across sizes."""
    m = re.search(r"/wikipedia/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/?]+)", url)
    return unquote(m.group(1)) if m else None


def subject_article(subject: str) -> str | None:
    """Title of the article a topic's subject names ("The Great Molasses Flood
    of 1919" -> "Great Molasses Flood"), or None if it isn't a name or no
    article matches. Same strictness as find_photo."""
    if not looks_like_a_name(subject):
        return None
    try:
        named = _named(subject, search(subject, limit=3))
        if named:
            return named[0]["title"]
    except requests.RequestException as e:
        print(f"[wikipedia] search failed for {subject!r}: {e}")
    return None


def article_photo_urls(title: str, limit: int = 6) -> list[str]:
    """Thumbnail URLs of the free photos in the article `title`, in article
    order with the lead image first. Skips vector files, logos, flags, maps and
    diagrams, and anything not hosted on Commons."""
    try:
        resp = requests.get(MEDIA_LIST_URL.format(title=quote(title.replace(" ", "_"), safe="")), headers=HEADERS, timeout=20)
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except (requests.RequestException, ValueError) as e:
        print(f"[wikipedia] media list failed for {title!r}: {e}")
        return []
    items.sort(key=lambda it: not it.get("leadImage"))  # stable: lead first, rest in article order
    urls = []
    for it in items:
        if it.get("type") != "image" or not it.get("srcset"):
            continue
        src = it["srcset"][0]["src"]
        url = "https:" + src if src.startswith("//") else src
        name = file_key(url)
        if not name or not re.search(r"\.(jpe?g|png)$", name, re.I) or _NOT_A_PHOTO.search(name):
            continue
        urls.append(url)
    return urls[:limit]


def credits_for(keys: list[str]) -> dict[str, str | None]:
    """{file name: credit line} for each Commons file whose license this
    project can show, and None for the ones it can't (or can't confirm). The
    line is what goes in the video's description: CC BY and CC BY-SA require
    the author and license to be named, and naming public-domain sources too
    costs nothing."""
    result: dict[str, str | None] = {k: None for k in keys}
    if not keys:
        return result
    try:
        resp = requests.get(
            COMMONS_API,
            params={
                "action": "query", "format": "json", "formatversion": 2, "prop": "imageinfo",
                "iiprop": "extmetadata", "titles": "|".join("File:" + k for k in keys),
            },
            headers=HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        pages = resp.json()["query"]["pages"]
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"[wikipedia] license lookup failed: {e}")
        return result
    by_name = {k.replace("_", " "): k for k in keys}
    for page in pages:
        key = by_name.get(page.get("title", "").removeprefix("File:").replace("_", " "))
        meta = (page.get("imageinfo") or [{}])[0].get("extmetadata", {})
        licence = (meta.get("LicenseShortName", {}).get("value") or "").strip()
        if key is None or not _USABLE_LICENSE.match(licence):
            continue
        artist = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", meta.get("Artist", {}).get("value") or "")).strip()
        artist = re.sub(r"(?i)\bunknown( author)?\b|\bnot specified\b", "", artist).strip(" ,;")
        result[key] = f"{key.rsplit('.', 1)[0].replace('_', ' ')}: {artist + ', ' if artist else ''}{licence}"
    return result


def download_photo(thumb_url: str, dest_stem: Path) -> Path | None:
    """Saves a real-sized copy of `thumb_url` (a Commons thumbnail URL) next to
    `dest_stem`, with the extension its content type calls for, and returns
    the path — or None after printing why it failed. (This step used to fail
    silently for every photo: no User-Agent -> 403, and the 1080px width it
    asked for is not one Wikimedia serves -> 400.) A file narrower than the
    smallest standard width is only served as the original, so that is the
    last thing tried."""
    last = "no attempt"
    bare = thumb_url.split("?")[0]
    original = re.sub(r"/thumb/([0-9a-f]/[0-9a-f]{2}/[^/]+)/[^/]+$", r"/\1", bare)
    original = original.replace("://thumb.wikimedia.org/", "://upload.wikimedia.org/")
    candidates = [re.sub(r"/\d+px-", f"/{w}px-", thumb_url, count=1) for w in THUMB_WIDTHS]
    if original != bare:
        candidates.append(original)
    for label, url in zip([*(f"{w}px" for w in THUMB_WIDTHS), "original"], candidates):
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=30) as r:
                content_type = r.headers.get("content-type", "")
                if r.status_code != 200:
                    last = f"HTTP {r.status_code} at {label}"
                    continue
                if not (content_type.startswith("image/jpeg") or content_type.startswith("image/png")):
                    last = f"{content_type or 'unknown type'} at {label}"
                    continue
                if int(r.headers.get("content-length") or 0) > 25_000_000:
                    last = f"{label} is over 25 MB"
                    continue
                ext = ".png" if "png" in content_type else ".jpg"
                dest = dest_stem.with_suffix(ext)
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
                return dest
        except requests.RequestException as e:
            last = str(e)
    print(f"[wikipedia] photo download failed ({last}): {thumb_url}")
    return None
