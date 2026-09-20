"""AniList's public GraphQL API (no auth, no key) — used as a grounded source of
real anime data and official artwork (cover/banner/character images the studios
and publishers release for exactly this kind of display), so the anime channel
never has to fabricate titles or reuse actual episode footage."""

from __future__ import annotations

import requests

API_URL = "https://graphql.anilist.co"

_MEDIA_FIELDS = """
    title { romaji english }
    description(asHtml: false)
    coverImage { extraLarge }
    bannerImage
    startDate { year month day }
    season
    seasonYear
    genres
    characters(sort: [ROLE, RELEVANCE], perPage: 6) {
      nodes { name { full } image { large } }
    }
"""

SEARCH_QUERY = f"query($search: String) {{ Media(search: $search, type: ANIME, sort: POPULARITY_DESC) {{ {_MEDIA_FIELDS} }} }}"

UPCOMING_QUERY = f"""query($perPage: Int) {{
  Page(page: 1, perPage: $perPage) {{
    media(status: NOT_YET_RELEASED, type: ANIME, sort: POPULARITY_DESC) {{ {_MEDIA_FIELDS} }}
  }}
}}"""


def _post(query: str, variables: dict) -> dict:
    resp = requests.post(API_URL, json={"query": query, "variables": variables}, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"]


def search_anime(title: str) -> dict | None:
    return _post(SEARCH_QUERY, {"search": title}).get("Media")


def upcoming_anime(limit: int = 5) -> list[dict]:
    return _post(UPCOMING_QUERY, {"perPage": limit}).get("Page", {}).get("media", [])


def title_of(media: dict) -> str:
    return media["title"].get("english") or media["title"]["romaji"]


def image_pool(media: dict, max_images: int = 6) -> list[str]:
    """Official artwork only: cover, banner, then character portraits."""
    urls = []
    if media.get("coverImage", {}).get("extraLarge"):
        urls.append(media["coverImage"]["extraLarge"])
    if media.get("bannerImage"):
        urls.append(media["bannerImage"])
    for node in media.get("characters", {}).get("nodes", []):
        img = node.get("image", {}).get("large")
        if img:
            urls.append(img)
    return urls[:max_images]
