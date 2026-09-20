from src.pipeline.llm import chat_json

SYSTEM = """You write social media metadata for a short-form video. Given the \
narration script, output strict JSON with keys:
- "title": punchy, curiosity-driven, under 90 characters, no hashtags
- "description": 1-3 sentences plus 3-5 relevant hashtags at the end
- "tags": a list of 8-12 short SEO keyword tags (no # symbol, for YouTube)
- "hashtags": a list of 4-6 hashtags (with # symbol, for TikTok/Instagram)"""


def generate_metadata(script: str, config: dict) -> dict:
    result = chat_json(SYSTEM, f"Script:\n{script}", model=config["llm"]["model"])
    for key in ("title", "description", "tags", "hashtags"):
        if key not in result:
            raise ValueError(f"Unexpected metadata response shape: {result}")
    return result
