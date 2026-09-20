from src.pipeline.llm import chat_json

SYSTEM = """You write short narrated scripts for faceless short-form video (YouTube \
Shorts / TikTok / Instagram Reels). Output strict JSON with keys:
- "script": the narration text only, spoken conversationally, 90-140 words \
(about 35-55 seconds at normal speaking pace). No stage directions, no headings.
- "visual_keywords": a list of 5 short stock-footage search terms (2-4 words each) \
that visually match the narration in order, one per beat of the script.
Do not include emojis or hashtags in the script."""


def generate_script(topic: str, config: dict) -> dict:
    user = f"Topic: {topic}\n\nWrite the script and visual keywords now."
    result = chat_json(SYSTEM, user, model=config["llm"]["model"])
    if "script" not in result or "visual_keywords" not in result:
        raise ValueError(f"Unexpected LLM response shape: {result}")
    return result
