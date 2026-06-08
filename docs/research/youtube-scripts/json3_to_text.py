"""Convert a YouTube json3 subtitle file to clean, readable plain text.

Usage: python json3_to_text.py <input.json3> [--timestamps]
Prints the transcript to stdout.
"""
import json
import re
import sys


def ms_to_ts(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60:02d}:{s % 60:02d}"


def main() -> None:
    path = sys.argv[1]
    want_ts = "--timestamps" in sys.argv[2:]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    lines: list[str] = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(seg.get("utf8", "") for seg in segs)
        text = text.replace("\n", " ").strip()
        if not text:
            continue
        if want_ts:
            lines.append(f"[{ms_to_ts(ev.get('tStartMs', 0))}] {text}")
        else:
            lines.append(text)

    if want_ts:
        print("\n".join(lines))
        return

    # Paragraph mode: join, collapse whitespace, then wrap into sentences.
    full = " ".join(lines)
    full = re.sub(r"\s+", " ", full).strip()
    # Break into pseudo-paragraphs every ~3 sentences for readability.
    sentences = re.split(r"(?<=[.!?…]) ", full)
    out, buf = [], []
    for sent in sentences:
        buf.append(sent)
        if len(buf) >= 3:
            out.append(" ".join(buf))
            buf = []
    if buf:
        out.append(" ".join(buf))
    print("\n\n".join(out))


if __name__ == "__main__":
    main()
