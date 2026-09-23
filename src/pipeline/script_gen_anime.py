"""Script generation for the anime channel — grounded in real AniList data so the
LLM narrates real titles/synopses instead of inventing plot details or hallucinating
upcoming releases that don't exist. Visuals are mostly official artwork (cover/
banner/character art), mixed with a short real clip from the title's official
trailer when AniList has one (src/pipeline/yt_clip.py) — the deliberately
riskier sourcing path taken on with the user's explicit go-ahead, not a default.

topics.txt format for this channel:
  "<Anime Title>|<angle to discuss>"  -> a grounded deep-dive on one real anime
  "UPCOMING"                          -> a roundup of real upcoming anime from AniList
"""

from src.pipeline.anilist import image_pool, search_anime, title_of, trailer_marker, upcoming_anime
from src.pipeline.hooks import pick_hook
from src.pipeline.llm import chat_json


def _system_explain(hook_instruction: str) -> str:
    return f"""You write short narrated video scripts (YouTube Shorts / TikTok / \
Instagram Reels) that discuss a real, existing anime for fans and newcomers, hooking \
viewers in the first two seconds and holding them to the last word. You are given the \
anime's real title and official synopsis — use only information consistent with that \
synopsis and well-established, widely-known facts about the series. Do not invent \
plot details, character names, or events not grounded in what's given. Output strict \
JSON with one key:
- "script": narration text only, spoken conversationally, 90-140 words (about 35-55 \
seconds), discussing the requested angle.
  - {hook_instruction}
  - Write like a person telling a friend something wild they just learned, not \
an encyclopedia entry read aloud. Use contractions, short punchy fragments, and \
plain words — avoid stiff constructions like "it is important to note that" or \
"this phenomenon occurs when." Vary sentence length; a one-word sentence after a \
long one lands harder than two medium ones in a row.
  - End on a punchy final line, not a trailing-off summary.
  - No stage directions, no headings, no emojis, no hashtags."""

SYSTEM_UPCOMING = """You write short narrated video scripts (YouTube Shorts / TikTok / \
Instagram Reels) previewing real upcoming anime releases for fans, hooking viewers in \
the first two seconds and holding them to the last word. You are given a list of real \
titles with official synopses and release windows — use only that information, don't \
invent plot details beyond it. Output strict JSON with one key:
- "script": narration text only, spoken conversationally, 100-150 words.
  - Open with the single most exciting title or premise in the list as a hook, not a \
generic intro like "here's what's coming".
  - Briefly cover each title in the list with its premise and release window, saving \
the one most likely to hook this audience for last.
  - Write like a person telling a friend something wild they just learned, not \
an encyclopedia entry read aloud. Use contractions, short punchy fragments, and \
plain words — avoid stiff constructions like "it is important to note that" or \
"this phenomenon occurs when." Vary sentence length; a one-word sentence after a \
long one lands harder than two medium ones in a row.
  - End on a punchy final line, not a trailing-off summary.
  - No stage directions, no headings, no emojis, no hashtags."""


def _clean(text: str, limit: int) -> str:
    return (text or "").replace("<br>", " ").replace("\n", " ").strip()[:limit]


def generate_anime_content(topic: str, config: dict, state: dict) -> dict:
    hook_id = None
    used_trailer = False
    if topic.strip().upper() == "UPCOMING":
        media_list = upcoming_anime(limit=5)
        if not media_list:
            raise RuntimeError("AniList returned no upcoming titles")
        lines, media_urls = [], []
        for m in media_list:
            title = title_of(m)
            release = f"{(m.get('season') or '').title()} {m.get('seasonYear') or ''}".strip()
            lines.append(f"- {title} (releasing {release or 'TBA'}): {_clean(m.get('description'), 400)}")
            cover = (m.get("coverImage") or {}).get("extraLarge")
            banner = m.get("bannerImage")
            media_urls += [u for u in (cover, banner) if u]
            marker = trailer_marker(m)
            if marker:
                media_urls.append(marker)
                used_trailer = True
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
        hook = pick_hook(state)
        hook_id = hook["id"]
        result = chat_json(_system_explain(hook["instruction"]), user, model=config["llm"]["model"])
        media_urls = image_pool(media, max_images=8)
        marker = trailer_marker(media)
        if marker:
            media_urls.append(marker)
            used_trailer = True

    if "script" not in result:
        raise ValueError(f"Unexpected LLM response shape: {result}")
    if not media_urls:
        raise RuntimeError("No AniList artwork resolved for this topic")
    # The prompt asks for 90-150 words; an occasional runaway generation can
    # come back far longer, which silently turns into a multi-minute video
    # and a very slow ffmpeg encode downstream. Fail fast here instead.
    word_count = len(result["script"].split())
    if word_count > 300:
        raise ValueError(f"LLM script way over length ({word_count} words) — likely a runaway generation")

    media_urls = (media_urls * 8)[:8]
    output = {"script": result["script"], "media_urls": media_urls, "visual_mode": "media", "hook_id": hook_id}
    if used_trailer:
        output["attribution"] = "Some footage via official trailers"
    return output
