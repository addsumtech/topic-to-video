#!/usr/bin/env python3
"""type_clock — the clock of a film told in TYPE and music, with no voice (the short promo: 15, 30 or 45 s).

    python3 scripts/type_clock.py <film_dir> --seconds 30 [--bpm 112] [--offset 0.0]

Reads <film_dir>/script.json (the director path's format: {language, sequences: [{name, lines: [{id, text, show?,
hold?}]}]}), where each line is one TYPE beat the viewer reads on screen, or a PICTURE beat (`"text": ""` with
`"show": <seconds>`: a product moment with no words). Writes <film_dir>/timeline.json in the voice clock's shape
({fps, duration, lines: [{id, text, start, end, words: [{w, t}], seq}], seams}) plus `"clock": "type"` and `"bpm"`,
so every tool that reads the voice clock (the designer, the animatic, Moments.wordTime, film_deliver's captions) reads
this one, and film_qc knows there is no voice to hear back.

HOW A LINE IS TIMED. Big type is read slower than speech is heard: about 0.30 s a word in a Latin script, 0.17 s a
character in Chinese or Japanese, plus 0.35 s to find the line, and every line ends with a still hold (`hold`, 0.6 s
by default; give the closing wordmark line 1.2). Picture beats take their `show`. Every beat is then rounded to WHOLE
BEATS of the music (at least two), so cuts land on the beat, and the remainder of the requested length goes to the
picture beats (they can breathe; type cannot be slower than reading). A line's words are spread over the first 60 %
of its span — the reveal — so a word's time is when it lands on screen.

DEGRADES LOUDLY: if the lines cannot be read in the length asked for (more than 8 % over), it exits 1 and says how
much to cut; it never squeezes reading time. Exit 0 written, 1 too long for the length, 2 usage or a bad script.
"""
import json
import math
import os
import re
import sys

USAGE = "usage: type_clock.py <film_dir> --seconds S [--bpm B] [--offset O]"
CJK = re.compile(r"[぀-ヿ㐀-鿿豈-﫿]")


def read_time(text, hold):
    """Seconds to read `text` set large on screen, with its still hold."""
    cjk = len(CJK.findall(text))
    words = len([w for w in re.split(r"\s+", CJK.sub(" ", text)) if re.search(r"\w", w)])
    return 0.35 + 0.30 * words + 0.17 * cjk + hold


def tokens(text):
    """The units that land on screen: words, or single CJK characters."""
    out = []
    for w in re.split(r"(\s+)", text):
        if not w.strip():
            continue
        if CJK.search(w):
            out += [c for c in w if c.strip()]
        else:
            out.append(w)
    return out


def clock(script, seconds, bpm, offset=0.0):
    beat = 60.0 / bpm
    beats = []
    for seq in script["sequences"]:
        for ln in seq["lines"]:
            text = (ln.get("text") or "").strip()
            if not text and "show" not in ln:
                raise ValueError("line %s has no text and no `show`: a beat must be read or shown" % ln.get("id"))
            need = float(ln["show"]) if not text else read_time(text, float(ln.get("hold", 0.6)))
            beats.append({"id": ln["id"], "text": text, "seq": seq["name"], "need": need, "picture": not text,
                          "n": max(2, int(math.ceil(need / beat - 1e-9)))})
    total = int(round((seconds - offset) / beat))
    used = sum(b["n"] for b in beats)
    if used * beat > (seconds - offset) * 1.08:
        raise OverflowError("the lines need %.1f s at %g bpm but the film is %g s: cut about %.1f s of lines"
                            % (used * beat + offset, bpm, seconds, used * beat + offset - seconds))
    spare, pics = total - used, [b for b in beats if b["picture"]] or beats
    i = 0
    while spare > 0:                          # the remainder goes to the picture beats, round robin
        pics[i % len(pics)]["n"] += 1
        spare -= 1
        i += 1
    while spare < 0:                          # within 8 %: take beats back from the longest lines, never below need
        b = max(beats, key=lambda x: x["n"] * beat - x["need"])
        if b["n"] <= 2:
            break
        b["n"] -= 1
        spare += 1
    t, lines, seams, prev = offset, [], [], None
    for b in beats:
        start, end = t, t + b["n"] * beat
        if prev is not None and b["seq"] != prev:
            seams.append(round(start, 3))
        toks = tokens(b["text"])
        span = (end - start) * 0.6
        words = [{"w": w, "t": round(start + span * k / max(1, len(toks)), 3)} for k, w in enumerate(toks)]
        lines.append({"id": b["id"], "text": b["text"], "start": round(start, 3), "end": round(end, 3),
                      "words": words, "seq": b["seq"], "kind": "picture" if b["picture"] else "type"})
        t, prev = end, b["seq"]
    return {"fps": 30, "duration": round(t, 3), "clock": "type", "bpm": bpm, "beat": round(beat, 4),
            "lines": lines, "seams": seams}


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(USAGE, file=sys.stderr)
        return 2
    d, args = argv[0], argv[1:]
    opts = dict(zip(args[::2], args[1::2]))
    unknown = set(opts) - {"--seconds", "--bpm", "--offset"}
    if unknown or "--seconds" not in opts or len(args) % 2:
        print(USAGE, file=sys.stderr)
        return 2
    sp = os.path.join(d, "script.json")
    try:
        script = json.load(open(sp, encoding="utf-8"))
        tl = clock(script, float(opts["--seconds"]), float(opts.get("--bpm", 112)), float(opts.get("--offset", 0)))
    except OverflowError as e:
        print("type_clock: %s" % e, file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as e:
        print("type_clock: %s: %s" % (sp, e), file=sys.stderr)
        return 2
    json.dump(tl, open(os.path.join(d, "timeline.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("[type_clock] %d beats, %.2f s at %g bpm -> %s" % (len(tl["lines"]), tl["duration"], tl["bpm"],
                                                           os.path.join(d, "timeline.json")))
    for ln in tl["lines"]:
        print("  %6.2f-%6.2f  %-8s %s" % (ln["start"], ln["end"], ln["kind"], ln["text"] or "(picture)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
