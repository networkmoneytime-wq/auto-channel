from src.pipeline.llm import chat_json

SYSTEM = """You write short narrated scripts for faceless short-form video (YouTube \
Shorts / TikTok / Instagram Reels), designed to hook viewers in the first two \
seconds and hold them to the last word. Output strict JSON with keys:
- "script": the narration text only, spoken conversationally, 90-140 words \
(about 35-55 seconds at normal speaking pace).
  - Open with the single most surprising or shocking part of the topic as the \
very first sentence. No slow windups, no "did you know", no throat-clearing —
  start mid-punch.
  - Where the topic naturally breaks into a list, ranking, or sequence, structure \
it as a quick countdown building to the most striking item last (e.g. "here are \
3 ways..." / "and the last one is the wildest"). Only do this when the topic \
actually fits that shape — don't force a countdown onto something that isn't one.
  - End on a punchy final line, not a trailing-off summary.
  - No stage directions, no headings, no emojis, no hashtags.
- "visual_keywords": a list of 5 short stock-footage search terms (2-4 words each) \
that visually match the narration in order, one per beat of the script."""


def generate_script(topic: str, config: dict) -> dict:
    user = f"Topic: {topic}\n\nWrite the script and visual keywords now."
    result = chat_json(SYSTEM, user, model=config["llm"]["model"])
    if "script" not in result or "visual_keywords" not in result:
        raise ValueError(f"Unexpected LLM response shape: {result}")
    return result
