"""Script generation for the anime channel — grounded in real AniList data so the
LLM narrates real titles/synopses instead of inventing plot details or hallucinating
upcoming releases that don't exist. Visuals are official artwork (cover/banner/
character art), never episode footage.

topics.txt format for this channel:
  "<Anime Title>|<angle to discuss>"  -> a grounded deep-dive on one real anime
  "UPCOMING"                          -> a roundup of real upcoming anime from AniList
"""

from src.pipeline.anilist import image_pool, search_anime, title_of, upcoming_anime
from src.pipeline.llm import chat_json

SYSTEM_EXPLAIN = """You write short narrated video scripts (YouTube Shorts / TikTok / \
Instagram Reels) that discuss a real, existing anime for fans and newcomers. You are \
given the anime's real title and official synopsis — use only information consistent \
with that synopsis and well-established, widely-known facts about the series. Do not \
invent plot details, character names, or events not grounded in what's given. Output \
strict JSON with one key:
- "script": narration text only, spoken conversationally, 90-140 words (about 35-55 \
seconds), discussing the requested angle. No stage directions, no headings, no \
emojis, no hashtags."""

SYSTEM_UPCOMING = """You write short narrated video scripts (YouTube Shorts / TikTok / \
Instagram Reels) previewing real upcoming anime releases for fans. You are given a \
list of real titles with official synopses and release windows — use only that \
information, don't invent plot details beyond it. Output strict JSON with one key:
- "script": narration text only, spoken conversationally, 100-150 words, briefly \
covering each title in the list in order with its premise and release window. No \
stage directions, no headings, no emojis, no hashtags."""


def _clean(text: str, limit: int) -> str:
    return (text or "").replace("<br>", " ").replace("\n", " ").strip()[:limit]


def generate_anime_content(topic: str, config: dict) -> dict:
    if topic.strip().upper() == "UPCOMING":
        media_list = upcoming_anime(limit=5)
        if not media_list:
            raise RuntimeError("AniList returned no upcoming titles")
        lines, image_urls = [], []
        for m in media_list:
            title = title_of(m)
            release = f"{(m.get('season') or '').title()} {m.get('seasonYear') or ''}".strip()
            lines.append(f"- {title} (releasing {release or 'TBA'}): {_clean(m.get('description'), 400)}")
            cover = (m.get("coverImage") or {}).get("extraLarge") or m.get("bannerImage")
            if cover:
                image_urls.append(cover)
        user = "Upcoming anime:\n" + "\n".join(lines) + "\n\nWrite the narration now."
        result = chat_json(SYSTEM_UPCOMING, user, model=config["llm"]["model"])
    else:
        title_part, _, angle = topic.partition("|")
        title = title_part.strip()
        angle = angle.strip() or "what makes this anime stand out"
        media = search_anime(title)
        if not media:
            raise RuntimeError(f"AniList had no match for anime title: {title!r}")
        real_title = title_of(media)
        user = (
            f"Anime: {real_title}\n"
            f"Official synopsis: {_clean(media.get('description'), 600)}\n"
            f"Angle to discuss: {angle}\n\nWrite the narration now."
        )
        result = chat_json(SYSTEM_EXPLAIN, user, model=config["llm"]["model"])
        image_urls = image_pool(media, max_images=5)

    if "script" not in result:
        raise ValueError(f"Unexpected LLM response shape: {result}")
    if not image_urls:
        raise RuntimeError("No AniList artwork resolved for this topic")

    image_urls = (image_urls * 5)[:5]
    return {"script": result["script"], "image_urls": image_urls}
