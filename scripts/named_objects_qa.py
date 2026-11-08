#!/usr/bin/env python3
"""Does the rendered beat SHOW each object its voice names? Read it off the picture.

    python3 scripts/named_objects_qa.py <out_dir>

A delivery gate (fast tier). For every beat whose narration names a list (named_lists.lists_in), its settled frames
(60% and 85% of the beat, from the render record's frame ranges) are read by screen_text (macOS Vision, else
tesseract) with the CAPTION BAND LEFT OUT — the caption says every word by construction; only the picture above it
can show the object. Each item must be found: one of the words its `shot_fit.shows` declares (a file name, a heading),
or its own name. An item declared `{"by": "picture"}` (a drawing with no words) or `{"by": "voice"}` is left to the
critic and said in scope.

ERROR an item no sampled frame shows. WARN an item whose only evidence is type under LEGIBLE px (at a 1080 short side)
— there, but too small to read. Exit 0 ok · 1 an item is missing · 2 NOT MEASURED (no out.mp4, no render record, no
text recognition).

WHY. The WorkBuddy film (2026-11-08): "A report. A spreadsheet. A deck." over three identical blank cards, and the
three named again later — every gate green; the user caught it (named_lists.py has the story).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import named_lists  # noqa: E402

TAG = "[named_objects]"
SAMPLES = (0.6, 0.85)          # settled frames: never judge a reveal mid-flight
LEGIBLE = 16                   # px of glyph box at a 1080 short side: under it a word is there but not read
CAPTION_FRAC = 0.815           # the caption band starts here (200 px of 1080: _caption_band)


class NotMeasured(RuntimeError):
    pass


def _norm(s):
    s = unicodedata.normalize("NFKC", s or "").casefold()
    return "".join(ch for ch in s if ch.isalnum())


def video_size(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", video], capture_output=True, text=True)
    w, h = (int(x) for x in r.stdout.strip().split(",")[:2])
    return w, h


def frame_png(video, f, dest):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", "select=eq(n\\,%d)" % f, "-vframes", "1",
                    dest], check=True)
    return dest


def read(png):
    import screen_text
    return screen_text.recognize(png)


def _caption_top(meta, w, h):
    try:
        from _caption_band import caption_band_px
        return 1.0 - caption_band_px(w, h) / float(h)
    except Exception:                            # noqa: BLE001 - the 16:9 band when the table cannot say
        return CAPTION_FRAC


def judge(out_dir):
    """{errors, warnings, scope}."""
    import screen_text
    video = os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(video):
        raise NotMeasured("no out.mp4 — render the film first")
    try:
        board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
        rec = json.load(open(os.path.join(out_dir, ".render_record.json"), encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise NotMeasured("no storyboard or render record (%s) — the beats' frames are not known" % e)
    segs = rec.get("segments") or []
    slides = board.get("slides") or []
    if len(segs) != len(slides):
        raise NotMeasured("the render record has %d beat range(s) for %d beat(s) — re-render" % (len(segs), len(slides)))
    if read.__module__ == __name__ and screen_text.available() is None:
        raise NotMeasured("no text recognition here (macOS Vision needs swiftc; elsewhere tesseract)")
    w, h = video_size(video)
    k = min(w, h) / 1080.0
    cap = _caption_top(board.get("meta") or {}, w, h)
    errors, warnings, scope = [], [], []
    work = tempfile.mkdtemp(prefix="named_obj_")
    judged = 0
    for i, s in enumerate(slides):
        lists = named_lists.lists_in(s.get("narration") or "")
        if not lists:
            continue
        shows = ((s.get("shot_fit") or {}).get("shows")) or {}
        a, b = int(segs[i][0]), int(segs[i][1])
        lines = []
        for frac in SAMPLES:
            f = a + int(round((b - a) * frac))
            for ln in read(frame_png(video, f, os.path.join(work, "b%d_%d.png" % (i, f)))):
                box = ln.get("box") or [0, 0, 0, 0]
                if box[1] >= cap:                     # in the caption band: the caption's own words
                    continue
                lines.append((ln.get("text") or "", (box[3] - box[1]) * h))
        label = s.get("index", i + 1)
        missing, small = [], []
        for lst in lists:
            for it in lst:
                how = shows.get(it["key"])
                if isinstance(how, dict):
                    scope.append("beat %s: %r is shown by %s (%s) — the critic judges it, not this gate"
                                 % (label, it["key"], how.get("by"), how.get("how") or how.get("why") or "said"))
                    continue
                words = [w_ for w_ in (how if isinstance(how, list) else []) if isinstance(w_, str)] or [it["key"]]
                hits = [px for text, px in lines for w_ in words if _norm(w_) and _norm(w_) in _norm(text)]
                if not hits:
                    missing.append(it["key"])
                elif max(hits) < LEGIBLE * k:
                    small.append("%s (%.0f px)" % (it["key"], max(hits)))
            judged += 1
        if missing:
            errors.append("beat %s names %s and its picture shows %s nowhere above the caption — draw each as "
                          "itself (a report reads as a report: its heading, its file name), or declare "
                          "shot_fit.shows {item: {\"by\": \"picture\", \"how\": …}} for a drawing with no words"
                          % (label, ", ".join(it["key"] for lst in lists for it in lst), ", ".join(missing)))
        if small:
            warnings.append("beat %s: %s — named and drawn, but too small to read (under %d px at 1080)"
                            % (label, ", ".join(small), LEGIBLE))
    scope.append("%d named list(s) judged on %d sampled frame(s) a beat, the caption band left out" % (judged, len(SAMPLES)))
    return {"errors": errors, "warnings": warnings, "scope": scope}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir")
    a = ap.parse_args(argv)
    try:
        r = judge(os.path.abspath(a.out_dir))
    except NotMeasured as e:
        print("%s NOT MEASURED — %s" % (TAG, e))
        return 2
    for e in r["errors"]:
        print("%s ERROR %s" % (TAG, e))
    for w_ in r["warnings"]:
        print("%s WARN  %s" % (TAG, w_))
    for sc in r["scope"]:
        print("%s scope: %s" % (TAG, sc))
    print("%s %s — %d error(s), %d warning(s)" % (TAG, "FAIL" if r["errors"] else "OK", len(r["errors"]),
                                                  len(r["warnings"])))
    return 1 if r["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
