import asyncio
from pathlib import Path

import edge_tts


async def _synthesize(text: str, voice: str, rate: str, out_path: Path) -> list[dict]:
    communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    word_boundaries = []
    with open(out_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append(
                    {
                        "text": chunk["text"],
                        "offset": chunk["offset"] / 10_000_000,  # 100ns units -> seconds
                        "duration": chunk["duration"] / 10_000_000,
                    }
                )
    return word_boundaries


def synthesize_voiceover(text: str, config: dict, out_path: Path) -> list[dict]:
    voice = config["tts"]["voice"]
    rate = config["tts"].get("rate", "+0%")
    return asyncio.run(_synthesize(text, voice, rate, out_path))
