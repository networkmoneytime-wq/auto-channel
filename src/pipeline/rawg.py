"""RAWG's video game database API (free tier, needs an API key from
rawg.io/apidocs) — a grounded source of real upcoming release data for the
gaming channel's "what's coming out soon" segments, the same role AniList
plays for the anime channel. RAWG's terms (rawg.io/tos_api) permit this at
this project's scale as long as RAWG is credited with a link back wherever
its data/images are used — see attribution_line(), applied the same way
music credits already are in src/pipeline/music.py."""

from __future__ import annotations

import datetime

import requests

from src.config import env

BASE_URL = "https://api.rawg.io/api/games"


def _get(path: str = "", **params) -> dict:
    params["key"] = env("RAWG_API_KEY")
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def upcoming_games(limit: int = 5, window_days: int = 120) -> list[dict]:
    today = datetime.date.today()
    window_end = today + datetime.timedelta(days=window_days)
    results = _get(
        dates=f"{today.isoformat()},{window_end.isoformat()}",
        ordering="-added",
        page_size=limit,
    ).get("results", [])
    # The list endpoint doesn't carry the full description — fetch each
    # game's own detail record for that.
    detailed = []
    for g in results:
        try:
            detailed.append(_get(f"/{g['id']}"))
        except requests.HTTPError:
            detailed.append(g)
    return detailed


def screenshots_for(game_id: int, limit: int = 2) -> list[str]:
    data = _get(f"/{game_id}/screenshots", page_size=limit)
    return [s["image"] for s in data.get("results", []) if s.get("image")]


def release_window(game: dict) -> str:
    released = game.get("released")
    if not released:
        return "TBA"
    try:
        return datetime.date.fromisoformat(released).strftime("%B %Y")
    except (ValueError, TypeError):
        return released


def attribution_line() -> str:
    return "Upcoming release info via RAWG.io — https://rawg.io"
