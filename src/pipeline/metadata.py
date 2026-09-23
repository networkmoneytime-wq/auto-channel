from src.pipeline.llm import chat_json

SYSTEM = """You write social media metadata for a short-form video. Given the \
narration script, output strict JSON with keys:
- "title": punchy, curiosity-driven, under 90 characters, no hashtags
- "description": a short caption for the post itself, in the voice of someone \
reacting to the video, not explaining it. One line, under 100 characters, before \
the hashtags. Cute/funny/deadpan over informative — think of how a real person \
captions a video they just found wild, not a summary of what it covers. Vary the \
pattern instead of reusing the same opener every time; some options in that \
register: a one-word or few-word reaction ("not me finding this out at 2am"), a \
deadpan understatement, a mock-serious warning, a rhetorical "wait—" opener, or \
just the punchiest detail restated as disbelief. No em dashes, no "here's why," \
no explaining the topic. Then 3-5 relevant hashtags on their own after it.
- "tags": a list of 8-12 short SEO keyword tags (no # symbol, for YouTube)
- "hashtags": a list of 4-6 hashtags (with # symbol, for TikTok/Instagram)"""


def generate_metadata(script: str, config: dict) -> dict:
    result = chat_json(SYSTEM, f"Script:\n{script}", model=config["llm"]["model"])
    for key in ("title", "description", "tags", "hashtags"):
        if key not in result:
            raise ValueError(f"Unexpected metadata response shape: {result}")
    return result
