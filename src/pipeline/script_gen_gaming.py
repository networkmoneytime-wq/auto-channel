"""Script generation for the gaming channel. Regular topics stay on the
existing history/culture/hardware-fact path (LLM + Pexels B-roll, unchanged).
The literal topic "UPCOMING" is grounded in real release data pulled from
RAWG (src/pipeline/rawg.py) so the channel narrates real upcoming games
instead of inventing release dates — the same role AniList plays for the
anime channel's own "UPCOMING" topic. These segments mix RAWG's official
screenshots with a short real trailer clip pulled from Steam when a title
has one (src/pipeline/steam.py) — the deliberately riskier sourcing path
taken on with the user's explicit go-ahead, not a default.

topics.txt format: existing plain fact lines work unchanged; the literal
line "UPCOMING" triggers a roundup of real, currently-listed upcoming games.
"""

from src.pipeline.llm import chat_json
from src.pipeline.rawg import attribution_line, release_window, screenshots_for, upcoming_games
from src.pipeline.script_gen import generate_script
from src.pipeline.steam import steam_appid_for, trailer_url_for

SYSTEM_UPCOMING = """You write short narrated video scripts (YouTube Shorts / TikTok / \
Instagram Reels) previewing real upcoming video game releases for gamers, hooking \
viewers in the first two seconds and holding them to the last word. You are given a \
list of real upcoming games with their real release windows and official \
descriptions — use only that information, don't invent release dates, platforms, or \
features not grounded in what's given. Output strict JSON with one key:
- "script": narration text only, spoken conversationally, 100-150 words.
  - Open with the single most exciting title in the list as a hook, not a generic \
intro like "here's what's coming out soon".
  - Briefly cover each title with what it is and its release window, saving the one \
most likely to hook this audience for last.
  - Write like a person telling a friend something wild they just learned, not an \
encyclopedia entry read aloud. Use contractions, short punchy fragments, and plain \
words — avoid stiff constructions like "it is important to note that." Vary \
sentence length; a one-word sentence after a long one lands harder than two medium \
ones in a row.
  - End on a punchy final line, not a trailing-off summary.
  - No stage directions, no headings, no emojis, no hashtags."""


def _clean(text: str, limit: int) -> str:
    return (text or "").replace("\r\n", " ").replace("\n", " ").strip()[:limit]


def generate_gaming_content(topic: str, config: dict, state: dict) -> dict:
    if topic.strip().upper() != "UPCOMING":
        return generate_script(topic, config, state)

    games = upcoming_games(limit=5)
    if not games:
        raise RuntimeError("RAWG returned no upcoming titles")

    lines, media_urls = [], []
    used_steam = False
    for g in games:
        name = g.get("name") or "Untitled"
        window = release_window(g)
        desc = _clean(g.get("description_raw") or g.get("description"), 400)
        lines.append(f"- {name} (releasing {window}): {desc or 'no official description yet'}")
        media_urls.extend(screenshots_for(g["id"], limit=1))

        appid = steam_appid_for(g["id"])
        trailer_url = trailer_url_for(appid) if appid else None
        if trailer_url:
            media_urls.append(trailer_url)
            used_steam = True

    if not media_urls:
        raise RuntimeError("No RAWG screenshots resolved for this topic")

    user = "Upcoming games:\n" + "\n".join(lines) + "\n\nWrite the narration now."
    result = chat_json(SYSTEM_UPCOMING, user, model=config["llm"]["model"])
    if "script" not in result:
        raise ValueError(f"Unexpected LLM response shape: {result}")
    # An occasional runaway generation can come back far longer than asked,
    # which silently turns into a multi-minute video and a very slow ffmpeg
    # encode downstream. Fail fast here instead.
    word_count = len(result["script"].split())
    if word_count > 300:
        raise ValueError(f"LLM script way over length ({word_count} words) — likely a runaway generation")

    media_urls = (media_urls * 8)[:8]
    attribution = attribution_line()
    if used_steam:
        attribution += " · Trailer clips via Steam"
    return {
        "script": result["script"],
        "media_urls": media_urls,
        "visual_mode": "media",
        "hook_id": None,
        "attribution": attribution,
    }
