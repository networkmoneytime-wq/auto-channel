from pathlib import Path

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, \
Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial Black,90,&H00FFFFFF,&H00000000,&H80000000,-1,0,1,4,0,2,60,60,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


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
        text = " ".join(w["text"] for w in group).upper()
        lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Caption,,0,0,0,,{text}\n")

    out_path.write_text("".join(lines))
    return out_path
