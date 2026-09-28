"""Keeps a channel's topics.txt from running dry by writing new lines itself
once too few unused ones remain — the same rewrite done by hand for all five
channels on 2026-09-26 (see project_auto_channel memory), now automatic and
recurring instead of a one-off.

Every new line is validated against the real, live source each channel is
already grounded in before it's trusted enough to append: a "Name: story"
line's Name must resolve to a real Wikipedia article (same check
src/pipeline/wikipedia.py does at render time — so a line that fails here
would only have silently fallen back to stock footage anyway), and anime's
"Title|angle" lines must resolve on AniList. A line that doesn't validate is
just dropped, not retried forever — cheap to lose one candidate out of a
batch.

Not every channel uses this: meme's topics aren't named-subject stories, and
gaming/anime's own "UPCOMING" roundup lines aren't something to imitate."""

from __future__ import annotations

import re

from src.config import channel, topics_path
from src.pipeline import anilist, performance, wikipedia
from src.pipeline.llm import chat_json

# Below this many still-unused lines, top the list up. Comfortably above one
# day's worth of runs (3/day) so there's always headroom while a batch
# validates.
MIN_UNUSED = 8
GENERATE_N = 12

_COLON_CHANNELS = {"dailyap", "cars", "technology", "gaming"}
_PIPE_CHANNELS = {"anime"}

_COLON_SYSTEM = """You write one-line video topic prompts for a narrated short-form video \
channel. Every line names one specific, real, well-documented thing (a person, event, \
object, place, or invention) and states the twist or stakes in a few words, exactly like:
"The Great Molasses Flood of 1919: how a burst tank sent a wave of syrup through Boston"
"The Tucker 48: the 1948 car whose creator went on trial for fraud and was acquitted"
Rules: only write about things you are confident really exist and are well documented \
(a viewer will look it up) -- never invent a name or event. ASCII characters only, no \
em dashes, ordinary hyphens only. One line per idea, ~12-25 words, ending after the \
colon's second half with no trailing period. No numbering, no extra commentary.
Output strict JSON: {"lines": ["Name: story", ...]}"""

_PIPE_SYSTEM = """You write one-line topic prompts for a channel that does grounded \
video-essay deep dives on real, existing anime. Every line is the exact common English \
title of one real, currently well-known anime, then "|", then a specific angle for that \
episode to take -- exactly like:
"Frieren: Beyond Journey's End|how a story that starts after the hero's victory became a hit"
Only write about real anime you are confident actually exist. ASCII characters only, no \
em dashes. One line per idea. No numbering, no extra commentary.
Output strict JSON: {"lines": ["Title|angle", ...]}"""


def _unused_lines(state: dict) -> list[str]:
    lines = [
        line.strip()
        for line in topics_path().read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    used = set(state.get("used_topics", []))
    return [t for t in lines if t not in used], lines


def _valid_colon_line(line: str, existing: set[str]) -> bool:
    if line in existing or ":" not in line or not line.isascii():
        return False
    subject = line.split(":", 1)[0].strip()
    return bool(subject) and wikipedia.subject_article(subject) is not None


def _valid_pipe_line(line: str, existing: set[str]) -> bool:
    if line in existing or "|" not in line or not line.isascii():
        return False
    title = line.split("|", 1)[0].strip()
    return bool(title) and anilist.search_anime(title) is not None


def maybe_extend_topics(state: dict, config: dict) -> None:
    """Best-effort: never lets a failure here touch the video this run is
    actually building. Call after this run's own topic has already been
    picked, so a slow or failed generation costs nothing this run either --
    it only affects whether a *future* run finds the list already topped up."""
    ch = channel()
    if ch not in _COLON_CHANNELS and ch not in _PIPE_CHANNELS:
        return
    try:
        unused, all_lines = _unused_lines(state)
        if len(unused) >= MIN_UNUSED:
            print(f"[topics] {len(unused)} unused topic(s) left, above the {MIN_UNUSED} threshold")
            return
        print(f"[topics] only {len(unused)} unused topic(s) left, writing {GENERATE_N} more")

        is_pipe = ch in _PIPE_CHANNELS
        system = _PIPE_SYSTEM if is_pipe else _COLON_SYSTEM
        niche = config.get("niche", "")
        user = (
            f"This channel's subject area: {niche!r}. Every new line must be something that "
            f"genuinely belongs on this specific channel, not just any well-known story.\n\n"
            f"Existing lines already on this channel (never repeat one of these, and match their "
            f"subject area):\n" + "\n".join(f"- {t}" for t in all_lines[-20:])
            + f"\n\nWrite {GENERATE_N} new lines in that same subject area, all different from each other."
        )
        examples = performance_examples(state)
        if examples:
            user += "\n\nFor reference, real past videos on this channel and how many views they got " \
                    "(lean toward whatever pattern the high performers share, avoid whatever the low " \
                    f"ones share):\n" + "\n".join(f"- {'high' if v >= 100 else 'low'}: {t!r} ({v} views)" for t, v in examples)
        result = chat_json(system, user, model=config["llm"]["model"])
        candidates = result.get("lines", [])

        existing = set(all_lines)
        validator = _valid_pipe_line if is_pipe else _valid_colon_line
        accepted = []
        for line in candidates:
            line = line.strip()
            if validator(line, existing | set(accepted)):
                accepted.append(line)

        print(f"[topics] {len(accepted)}/{len(candidates)} new line(s) validated")
        if not accepted:
            return
        with open(topics_path(), "a") as f:
            f.write(f"\n# Auto-generated {_today()}, grounded and validated (see topic_writer.py)\n")
            for line in accepted:
                f.write(line + "\n")
    except Exception as e:  # noqa: BLE001 - a topped-up list is never worth losing the video over
        print(f"[topics] auto-extend failed, leaving the list as-is: {e!r}")


def performance_examples(state: dict) -> list[tuple[str, int]]:
    return [(e["topic"], e["views"]) for e in performance.current().get("topic_examples", [])]


def _today() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
