from pathlib import Path

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, \
Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial Black,96,&H00FFFFFF,&H00000000,&H80000000,-1,0,1,5,0,2,60,60,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# ASS colors are &HBBGGRR& (reversed byte order). Amber/yellow accent for the
# word currently being spoken, white for surrounding context words — the
# word-by-word "karaoke highlight" style (Hormozi/MrBeast-style editors) that
# outperforms static multi-word caption cards in short-form retention.
ACCENT = r"{\c&H00D5FF&}"
WHITE = r"{\c&H00FFFFFF&}"
DIM = r"{\c&H00CCCCCC&}"
# The active word pops from 70% to 115% then settles at 100%, instead of
# appearing static — a sharper "punch" than a plain fade, matching the snappy
# word-reveal pacing common in top-performing shorts.
POP_IN = r"{\fscx70\fscy70\t(0,70,\fscx115\fscy115)\t(70,140,\fscx100\fscy100)}"

# Arial Black is missing glyphs for several punctuation marks edge-tts/the LLM
# sometimes emits (non-breaking hyphen, en/em dash, curly quotes, ellipsis),
# which render as a tofu box. Normalize to ASCII equivalents.
_SANITIZE = str.maketrans(
    {
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        " ": " ",
    }
)


def _clean(text: str) -> str:
    return text.translate(_SANITIZE)


def _ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_captions(word_boundaries: list[dict], config: dict, out_path: Path, context: int = 1) -> Path:
    """Word-by-word karaoke captions: each word gets its own timed line, shown
    with up to `context` neighboring words on either side for readability.
    The word currently being spoken is punched in accent color and popped up
    in scale; neighbors stay small and white/dimmed."""
    width = config["video"]["width"]
    height = config["video"]["height"]
    lines = [HEADER.format(width=width, height=height)]

    words = [_clean(w["text"]).upper() for w in word_boundaries]

    for i, w in enumerate(word_boundaries):
        start = w["offset"]
        end = w["offset"] + w["duration"]
        lo = max(0, i - context)
        hi = min(len(words), i + context + 1)

        parts = []
        for j in range(lo, hi):
            if j == i:
                parts.append(POP_IN + ACCENT + words[j] + r"{\r}")
            elif j < i:
                parts.append(DIM + words[j])
            else:
                parts.append(WHITE + words[j])
        text = " ".join(parts)
        lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Caption,,0,0,0,,{text}\n")

    out_path.write_text("".join(lines))
    return out_path
