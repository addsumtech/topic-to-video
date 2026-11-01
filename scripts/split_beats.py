#!/usr/bin/env python3
"""split_beats — cut a long beat into beats short enough to keep moving, BEFORE the voice is made.

    python3 scripts/split_beats.py <out_dir>                  # list the long beats and where each would split
    python3 scripts/split_beats.py <out_dir> --beat N         # split beat N (rewrites storyboard.json)

WHY. Measured on 311 beats of 22 of our films (scripts/craft_qa.py): a beat of 4-6 s held a frame still past 3 s 9% of
the time, 8-10 s 51%, 12 s and over 89-100% — one register reveals and then waits for the voice. Published launch films
hold 2.5 s at the median. The planner's rhythm already said ~3-6 s; nothing enforced it, and after tts a split means
re-voicing. So validate names the long beats with their split (pace.long_beats), and this applies one.

WHAT A SPLIT LEAVES. The narration is cut at sentence ends where it can (pace.split_point) into pieces under the limit.
The first piece keeps the beat's shot and props. Every later piece is a NEW beat with NO shot — `relation:
continuation`, `split_from: N` — and validate refuses a beat without a shot, so the director designs it: a second
picture for the second half of the thought. Copying the first beat's shot would replay the same reveal, which reads as
a stutter, not a cut. Captions follow the narration; indices are renumbered; audio is not touched (run tts after).
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c                                                            # noqa: E402
import pace                                                                     # noqa: E402

_USAGE = "usage: split_beats.py <out_dir> [--beat N] [--limit SECONDS]"
_KEEP_ON_NEW = ("type",)                    # what a new piece inherits besides its words (nothing about the picture)


def split(out_dir, beat, limit=pace.LONG_BEAT_S):
    """Split beat `beat` of out_dir's board into pieces under `limit`; returns how many beats it became (1 = unsplit)."""
    path = os.path.join(out_dir, "storyboard.json")
    board = json.load(open(path, encoding="utf-8"))
    slides = board.get("slides") or []
    pos = next((i for i, s in enumerate(slides) if isinstance(s, dict) and s.get("index") == beat), None)
    if pos is None:
        raise SystemExit("split_beats: no beat %r on the board" % beat)
    src = slides[pos]
    row = next((r for r in pace.long_beats(board, limit) if r["index"] == beat), None)
    if row is None or len(row["pieces"]) < 2:
        return 1
    first = copy.deepcopy(src)
    first["narration"] = row["pieces"][0]
    if "caption" in first:
        first["caption"] = row["pieces"][0]
    for k in ("duration", "audio"):
        first.pop(k, None)                                  # the voice is re-made for the shorter line
    new = [first]
    for piece in row["pieces"][1:]:
        sl = {k: src[k] for k in _KEEP_ON_NEW if k in src}
        sl.update({"narration": piece, "caption": piece, "relation": "continuation", "split_from": beat})
        new.append(sl)
    slides[pos:pos + 1] = new
    for i, s in enumerate(slides, start=1):
        if isinstance(s, dict):
            s["index"] = i
    board["slides"] = slides
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False, indent=1)
    return len(new)


def main(argv):
    _c.refuse_unknown(argv, valued=("beat", "limit"), usage=_USAGE)
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i and argv[i - 1] in ("--beat", "--limit"))]
    if not args:
        print(_USAGE)
        return 2
    out_dir = args[0]
    limit = float(_c.argflag(argv, "limit", pace.LONG_BEAT_S))
    beat = _c.argflag(argv, "beat")
    if beat is not None:
        n = split(out_dir, int(beat), limit)
        print("[split] beat %s -> %d beat(s)%s" % (beat, n, "" if n > 1 else " (already short enough, or no break)"))
        if n > 1:
            print("  the new beats have NO shot: design each (shot_fit, shot, shot_props), then run tts.py")
        return 0
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    rows = pace.long_beats(board, limit)
    if not rows:
        print("[split] no beat over %.0f s" % limit)
        return 0
    for r in rows:
        print("beat %s (%s): %.1f s -> %d beats: %s" % (r["index"], r["shot"], r["seconds"], len(r["pieces"]),
                                                       " ‖ ".join(p.strip()[:24] for p in r["pieces"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
