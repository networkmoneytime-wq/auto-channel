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
# punch word in each caption card, white for the rest.
ACCENT = r"{\c&H00D5FF&}"
WHITE = r"{\c&H00FFFFFF&}"
# Quick pop-in: each card starts at 55% scale and snaps up to 100% over 90ms,
# instead of appearing static — matches the punchier caption style of
# trending short-form edits.
POP_IN = r"{\fscx55\fscy55\t(0,90,\fscx100\fscy100)}"

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
        " ": " ",
    }
)


def _clean(text: str) -> str:
    return text.translate(_SANITIZE)


def _ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_captions(word_boundaries: list[dict], config: dict, out_path: Path, words_per_card: int = 3) -> Path:
    width = config["video"]["width"]
    height = config["video"]["height"]
    lines = [HEADER.format(width=width, height=height)]

    for i in range(0, len(word_boundaries), words_per_card):
        group = word_boundaries[i : i + words_per_card]
        if not group:
            continue
        start = group[0]["offset"]
        end = group[-1]["offset"] + group[-1]["duration"]
        words = [_clean(w["text"]).upper() for w in group]
        # Punch the last word of each card in the accent color, like the
        # bold-word-emphasis style common in high-retention short-form edits.
        if len(words) > 1:
            body = " ".join(words[:-1]) + " " + ACCENT + words[-1] + WHITE
        else:
            body = ACCENT + words[0] + WHITE
        text = POP_IN + body
        lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Caption,,0,0,0,,{text}\n")

    out_path.write_text("".join(lines))
    return out_path
