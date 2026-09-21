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
  - End on a punchy final line, not a trailing-off summary.
  - No stage directions, no headings, no emojis, no hashtags.
- "visual_keywords": a list of short stock-footage search terms (2-4 words each), \
one per distinct sentence or clear beat in the script — typically 10-16 for a \
script this length. More, shorter beats read as punchier fast-cut pacing, which \
outperforms a handful of long static shots on short-form; let the script's own \
sentence breaks set the beat count rather than picking a round number."""


def generate_script(topic: str, config: dict, state: dict) -> dict:
    hook = pick_hook(state)
    user = f"Topic: {topic}\n\nWrite the script and visual keywords now."
    result = chat_json(_system_prompt(hook["instruction"]), user, model=config["llm"]["model"])
    if "script" not in result or "visual_keywords" not in result:
        raise ValueError(f"Unexpected LLM response shape: {result}")
    result["hook_id"] = hook["id"]
    return result
