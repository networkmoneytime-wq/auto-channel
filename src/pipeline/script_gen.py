from src.pipeline.hooks import pick_hook
from src.pipeline.llm import chat_json


def _system_prompt(hook_instruction: str) -> str:
    return f"""You write short narrated scripts for faceless short-form video (YouTube \
Shorts / TikTok / Instagram Reels), designed to hook viewers in the first two \
seconds and hold them to the last word. Output strict JSON with keys:
- "script": the narration text only, spoken conversationally, 90-140 words \
(about 35-55 seconds at normal speaking pace).
  - {hook_instruction}
  - Where the topic naturally breaks into a list, ranking, or sequence, structure \
it as a quick countdown building to the most striking item last (e.g. "here are \
3 ways..." / "and the last one is the wildest"). Only do this when the topic \
actually fits that shape — don't force a countdown onto something that isn't one.
  - Write like a person telling a friend something wild they just learned, not \
an encyclopedia entry read aloud. Use contractions, short punchy fragments, and \
plain words — avoid stiff constructions like "it is important to note that" or \
"this phenomenon occurs when." Vary sentence length; a one-word sentence after a \
long one lands harder than two medium ones in a row.
  - End on a punchy final line, not a trailing-off summary.
  - No stage directions, no headings, no emojis, no hashtags.
- "visual_keywords": a list of short stock-footage search terms (2-4 words each), \
one per distinct sentence or clear beat in the script — typically 10-16 for a \
script this length. More, shorter beats read as punchier fast-cut pacing, which \
outperforms a handful of long static shots on short-form; let the script's own \
sentence breaks set the beat count rather than picking a round number.
  - Search for the literal, physical thing the sentence is about — a specific \
object, place, animal, or action someone could point a camera at — not an \
abstract concept. "concrete steps" or "hands pouring concrete" beats "progress \
concept"; "beehive close up" beats "teamwork nature"; "person writing in \
notebook" beats "idea concept". Terms like "success", "innovation", \
"teamwork", "concept", or "background" reliably pull generic staged corporate \
stock — avoid them entirely; describe what's actually visible in the shot \
instead.
  - Write each term as something a stock library would tag literally. Never use \
a word whose everyday meaning differs from what you intend: "gull wing doors" \
finds seagulls, "flux" finds lightning, a film's title finds a school kid. Say \
what the shot looks like instead ("car door opening upward").
  - Exception: when the script names a specific real person, place, product, or \
object, use that beat for a real photo of it. Write the item's real name in \
Proper Case, the way its Wikipedia article is titled, then " | " and a plain \
lowercase stock term to fall back on if there's no free photo of it: \
"Hedy Lamarr | woman at desk", "Voyager 1 | spacecraft in space", "Boston | city \
street". Use at most 4 such beats, only for things you are sure exist, and name \
each one once. Every other beat is a plain lowercase stock term, as above."""


def generate_script(topic: str, config: dict, state: dict) -> dict:
    hook = pick_hook(state)
    user = f"Topic: {topic}\n\nWrite the script and visual keywords now."
    result = chat_json(_system_prompt(hook["instruction"]), user, model=config["llm"]["model"])
    if "script" not in result or "visual_keywords" not in result:
        raise ValueError(f"Unexpected LLM response shape: {result}")
    # The prompt asks for 90-140 words; an occasional runaway generation can
    # come back far longer, which silently turns into a multi-minute video
    # and a very slow ffmpeg encode downstream. Fail fast here instead.
    word_count = len(result["script"].split())
    if word_count > 300:
        raise ValueError(f"LLM script way over length ({word_count} words) — likely a runaway generation")
    result["hook_id"] = hook["id"]
    return result
