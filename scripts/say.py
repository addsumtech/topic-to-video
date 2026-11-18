#!/usr/bin/env python3
"""say — voice ONE line (or a file of lines) with the skill's voice layer, for a film with no storyboard.

    python3 scripts/say.py "一句台词" --out voice/l01.mp3 [--voice edge:zh-CN-YunxiNeural] [--speed 1.08]
                           [--lexicon lexicon.json]
    python3 scripts/say.py --lines script.txt --out-dir voice/ [--voice …] [--speed …] [--lexicon …]

The voice layer (scripts/tts.py `speak`): the engines (edge neural, free; `minimax:` and `openai:` with the user's key;
macOS `say`), the pronunciation lexicon ({written: spoken}, applied for the voice only and mapped back, so the
caption keeps the written word), Chinese-voice initialisms spelled out ("AI" as A-I), and, for edge, per-word
timings in <clip>.words.json under the WRITTEN words — the timeline captions and cuts are built from (for minimax /
openai / say, which report none, they are ALIGNED from edge saying the same words: scripts/word_align.py). A transient
edge failure is retried; any other failure stops with its reason (never a silent fallback to a different voice).
--lines voices one clip per non-empty line: l01.mp3, l02.mp3, …
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def voice_one(text, dest, voice, meta):
    import tts
    prov, name = tts._provider(voice)
    os.makedirs(os.path.dirname(os.path.abspath(dest)) or ".", exist_ok=True)
    tts.speak_retrying(text, dest, meta, prov, name)
    if prov != "edge":
        # the timeline is built from per-word timings; this engine reports none, so they are aligned from the edge
        # voice saying the same words (scripts/word_align.py). No timings is an error here, never a guess.
        try:
            tts.align_words_from_edge(text, dest, meta)
        except RuntimeError as e:
            raise SystemExit("say: %s: %s" % (dest, e))
    return dest


def main(argv):
    ap = argparse.ArgumentParser(description="voice one line or a file of lines with the skill's TTS layer")
    ap.add_argument("text", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--lines", help="a text file: one clip per non-empty line")
    ap.add_argument("--out-dir")
    ap.add_argument("--voice", default="edge:zh-CN-YunxiNeural", help="edge:<id> | minimax:<id> | openai:<id> | say:<name>")
    ap.add_argument("--speed", type=float, default=1.0, help="1.0 natural; edge handles about 0.7-1.3")
    ap.add_argument("--lexicon", help="JSON file {written: spoken}")
    a = ap.parse_args(argv)
    meta = {"tts_speed": a.speed}
    if a.lexicon:
        meta["tts_lexicon"] = json.load(open(a.lexicon, encoding="utf-8"))
    if a.lines:
        if not a.out_dir:
            ap.error("--lines needs --out-dir")
        lines = [l.strip() for l in open(a.lines, encoding="utf-8") if l.strip()]
        for i, line in enumerate(lines, 1):
            print("[say] %s" % voice_one(line, os.path.join(a.out_dir, "l%02d.mp3" % i), a.voice, meta))
        return 0
    if not a.text or not a.out:
        ap.error("give a line and --out, or --lines with --out-dir")
    print("[say] %s" % voice_one(a.text, a.out, a.voice, meta))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
