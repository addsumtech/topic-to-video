#!/usr/bin/env python3
"""craft_qa — three things a viewer feels and our films measurably lack, against a reference corpus.

    python3 scripts/craft_qa.py <out_dir> [--json]          # out.mp4 + storyboard.json, findings by beat
    python3 scripts/craft_qa.py --file film.mp4 [--json]    # any film, no board
    python3 scripts/craft_qa.py --reference                 # the reference numbers this compares against

WHY. On 2026-10-31 this instrument measured 28 launch-film previews published on skillry.dev and 22 of our own
Remotion films. Three axes separated them; one did not:

    axis (measured by this file, 12 fps)       reference median   ours median   over the line
    longest still (s)                             2.5              5.0        ours 16 of 22 > 3 s, theirs 12 of 28
    motion p90 (mean |Δ| per 1/12 s, 0..255)      4.3              2.1
    hierarchy: largest element / layout           0.63             0.48
    hierarchy: main elements per frame            2                3
    hierarchy: seconds one element leads          47%              38%
    content occupancy (bbox / frame)              0.32           similar   NOT a gap — not measured here

So the films hold a frame too long, move with no accent, and give no single element the frame. Every one of those
is felt, none was measured, and every gate here was green on all 22 films.

WHAT EACH AXIS IS.
  still      a 1/12 s step whose mean absolute difference is under STILL_DELTA grey levels changed nothing a viewer
             sees; `longest_still_s` is the longest run of them. Captions changing count as change — they are.
  motion_p90 the 90th percentile of the per-step difference: how hard the film's accents hit, not how often.
  hierarchy  sampled once a second on the frame ABOVE the caption band (captions are a constant of our films and
             absent from the reference ones). Content = pixels more than INK_DELTA from the frame's border colour,
             dilated so a word's letters join; elements = connected blobs of at least MIN_BLOB of the frame.
             `dom` = the largest element's box over the box around all of them (1 = one thing owns the layout);
             `one_thing` = share of seconds where dom > ONE_THING. A frame with nothing drawn is not a verdict.

WHAT IT IS NOT. Advisory: it names beats, it does not block a render. A beat held still on purpose (a closing
lockup, a quiet reading hold) is a decision, and the finding says how long so the author can see whether it was one.
The reference holds NUMBERS and where they came from, never the films (references/craft_reference.json).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE_PATH = os.path.join(_HERE, "..", "references", "craft_reference.json")

FPS = 12
LONG_SIDE = 192            # film_energy_qa's motion decode: the same picture of motion for both corpora
STILL_DELTA = 0.3          # grey levels; under this a 1/12 s step changed nothing visible
HIER_SHORT_SIDE = 240      # the hierarchy decode fixes the SHORT side: fixed on the long side, a 9:16 frame was
                           # 136 px wide and a scattered motif speck crossed MIN_BLOB as an "element"
CAPTION_CROP = 0.20        # bottom share of the frame left out of the hierarchy read
INK_DELTA = 24             # per-channel distance from the border colour that counts as drawn
DILATE_SHARE = 0.022       # of the short side: the gap that still joins one word's letters and one block's lines.
                           # A fixed pixel radius made the measure depend on decode size (0.72 -> 0.49 on the same films)
MIN_BLOB = 0.002           # an element's box must be at least this share of the frame
ONE_THING = 0.7

TYPE_LEAD_LINE = 0.06       # largest type under this share of the short side ... (census line box; see type_by_beat)
TYPE_LINES = 5              # ... among this many lines or more, with no element leading: small crowded type
TYPE_SETTLE = 0.4           # read a beat's type from this share of it on: its entrances are not its layout
STILL_LINE = 3.0           # 16 of 28 reference films never hold longer; their median is 2.5 s
DOM_LINE = 0.5             # under this with MANY_BLOBS elements, nothing leads the frame
MANY_BLOBS = 4


class Unmeasurable(Exception):
    pass


def _size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        w, h = (int(x) for x in out.stdout.strip().split(",")[:2])
        return w, h
    except ValueError:
        raise Unmeasurable("%s: no video stream (%s)" % (path, out.stderr.strip()[:200]))


def _decode(path, fps, long_side, gray, short_side=None):
    import numpy as np
    W, H = _size(path)
    if short_side:
        long_side = int(round(short_side * max(W, H) / float(min(W, H))))
    if W >= H:
        w, h = long_side, max(2, int(round(long_side * H / W)) // 2 * 2)
    else:
        h, w = long_side, max(2, int(round(long_side * W / H)) // 2 * 2)
    ch = 1 if gray else 3
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "fps=%g,scale=%d:%d" % (fps, w, h),
                           "-pix_fmt", "gray" if gray else "rgb24", "-f", "rawvideo", "-"], capture_output=True)
    n = len(proc.stdout) // (w * h * ch)
    if proc.returncode != 0 or n < 2:
        raise Unmeasurable("%s: decode failed (%s)" % (path, proc.stderr.decode(errors="replace").strip()[:200]))
    a = np.frombuffer(proc.stdout[: n * w * h * ch], np.uint8)
    return a.reshape((n, h, w) if gray else (n, h, w, 3))


def _longest_run(mask):
    best = run = 0
    for x in mask:
        run = run + 1 if x else 0
        best = max(best, run)
    return best


def _hierarchy_one(frame):
    """(dom, nblob) for one RGB frame, or None when nothing is drawn above the caption band."""
    import numpy as np
    from scipy import ndimage
    f = frame[: int(frame.shape[0] * (1 - CAPTION_CROP))].astype(np.int16)
    h, w, _ = f.shape
    border = np.concatenate([f[:3].reshape(-1, 3), f[:, :3].reshape(-1, 3), f[:, -3:].reshape(-1, 3)])
    m = np.abs(f - np.median(border, axis=0)).max(axis=2) > INK_DELTA
    if m.sum() < 30:
        return None
    r = max(1, int(round(DILATE_SHARE * min(frame.shape[0], frame.shape[1]))))
    lab, _n = ndimage.label(ndimage.binary_dilation(m, iterations=r))
    boxes = [s for s in ndimage.find_objects(lab)
             if (s[0].stop - s[0].start) * (s[1].stop - s[1].start) >= MIN_BLOB * h * w]
    if not boxes:
        return None
    y0 = min(s[0].start for s in boxes); y1 = max(s[0].stop for s in boxes)
    x0 = min(s[1].start for s in boxes); x1 = max(s[1].stop for s in boxes)
    big = max((s[0].stop - s[0].start) * (s[1].stop - s[1].start) for s in boxes)
    return big / float((y1 - y0) * (x1 - x0)), len(boxes)


def _hier_summary(rows):
    import numpy as np
    got = [r for r in rows if r is not None]
    if not got:
        return {"dom_med": None, "nblob_med": None, "one_thing": None, "measured_s": 0}
    d = np.array([r[0] for r in got]); nb = np.array([r[1] for r in got])
    return {"dom_med": round(float(np.median(d)), 3), "nblob_med": float(np.median(nb)),
            "one_thing": round(float((d > ONE_THING).mean()), 3), "measured_s": len(got)}


def measure(path, board=None):
    """{longest_still_s, still_share, motion_p90, hierarchy, beats}. Raises Unmeasurable when the film cannot be
    decoded — a film that was not looked at is never reported as one that passed."""
    import numpy as np
    g = _decode(path, FPS, LONG_SIDE, gray=True).astype(np.float32)
    d = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2))
    still = d < STILL_DELTA
    rgb = _decode(path, 1, None, gray=False, short_side=HIER_SHORT_SIDE)
    hier = [_hierarchy_one(f) for f in rgb]
    out = {"seconds": round(len(g) / float(FPS), 2),
           "longest_still_s": round(_longest_run(still) / float(FPS), 2),
           "still_share": round(float(still.mean()), 3),
           "motion_p90": round(float(np.percentile(d, 90)), 2),
           "hierarchy": _hier_summary(hier), "beats": []}
    if board:
        import film_energy_qa as fe
        for idx, shot, f0, f1 in fe.beat_spans(board, len(g), FPS):
            seg = d[f0:max(f0, f1 - 1)]
            if len(seg) < 4:
                continue
            s0, s1 = int(f0 / FPS), int(np.ceil(f1 / FPS))
            out["beats"].append({"index": idx, "shot": shot, "seconds": round(len(seg) / float(FPS), 2),
                                 "longest_still_s": round(_longest_run(seg < STILL_DELTA) / float(FPS), 2),
                                 "motion_p90": round(float(np.percentile(seg, 90)), 2),
                                 "hierarchy": _hier_summary(hier[s0:s1])})
    return out


def type_by_beat(frames, segs, short_side, settle=TYPE_SETTLE):
    """{beat index (0-based): {lead, lines, frames}} from a type census (text_safe_qa.glide_run of the Film): per settled
    frame, the tallest readable line (opacity >= 0.5) over the short side, and how many readable lines; the median of
    each. The census measures LINE BOXES and the reference was measured on GLYPH boxes (Vision OCR); on the same film
    the two read 0.95 of each other (IQR 0.78-1.12, 78 frames, 2026-11-01), so the numbers stand against each other."""
    import statistics as st
    per = {}
    for f, rec in frames.items():
        f = int(f)
        for k, (a, b) in enumerate(segs):
            if a + settle * (b - a) <= f < b:
                lines = [ln for ln in (rec.get("lines") or []) if ln.get("b") is not None and int(ln["b"]) == k
                         and float(ln.get("o") or 0) >= 0.5 and float(ln.get("h") or 0) > 0]
                if lines:
                    per.setdefault(k, []).append((max(float(ln["h"]) for ln in lines) / float(short_side), len(lines)))
    return {k: {"lead": round(st.median(x[0] for x in v), 4), "lines": st.median(x[1] for x in v), "frames": len(v)}
            for k, v in per.items()}


def measure_type(out_dir, board, every=15):
    """type_by_beat for a rendered film, from one census of its Film (every `every` frames). Raises Unmeasurable."""
    import shutil
    import tempfile
    import render_remotion as rr
    import remotion_segments as _rs
    import text_safe_qa as tq
    import workshop as _ws
    from _caption_band import aspect_table
    props, _slides = rr.film_props(out_dir, board)
    props = dict(props, typeGlide=True)
    segs, _total = _rs.timeline(props["scenes"], _rs.seam_frames())
    work = tempfile.mkdtemp(prefix="craft_type_")
    try:
        public = _rs.minimal_public(props, out_dir, os.path.join(work, "public"))
        bundle = tq.glide_bundle(os.path.join(work, "bundle"), public, _ws.prepare(out_dir))
        res = tq.glide_run([{"tag": "f", "id": "Film", "props": props}], bundle, extra=("--every=%d" % every,))["f"]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if not res.get("done"):
        raise Unmeasurable("the type census did not finish (%s)" % (res.get("error") or "no done line"))
    W, H = aspect_table().get(str((board.get("meta") or {}).get("aspect") or "16:9"), (1920, 1080))
    return type_by_beat(res["frames"], segs, min(W, H))


def findings(m):
    """Advisory lines, by beat when the board placed them, else for the film."""
    lines = []
    rows = m.get("beats") or [dict(m, index=None, shot="film")]
    for r in rows:
        tag = "beat %s %s" % (r["index"], r["shot"]) if r.get("index") else "film"
        if r["longest_still_s"] > STILL_LINE:
            lines.append("%s: holds still for %.1f s (reference films: median 2.5 s, 16 of 28 never past %.0f s) — "
                         "a reveal, a camera move or a change of emphasis inside the hold"
                         % (tag, r["longest_still_s"], STILL_LINE))
        h = r["hierarchy"]
        ty = r.get("type")
        if (ty and ty["lead"] < TYPE_LEAD_LINE and ty["lines"] >= TYPE_LINES and h["dom_med"] is not None
                and h["dom_med"] < DOM_LINE):
            lines.append("%s: small crowded type — the largest line is %.1f%% of the short side among %g lines and "
                         "nothing else leads (reference films: ~7%% lead type, ~3 lines) — let one line lead: larger, "
                         "fewer words; a beat led by its drawing keeps small labels" % (tag, 100 * ty["lead"], ty["lines"]))
        if h["dom_med"] is not None and h["dom_med"] < DOM_LINE and h["nblob_med"] >= MANY_BLOBS:
            lines.append("%s: no element leads the frame — the largest is %.0f%% of the layout among %d elements "
                         "(reference: %.0f%% among 2)" % (tag, 100 * h["dom_med"], h["nblob_med"], 63))
    return lines


def reference():
    return json.load(open(REFERENCE_PATH, encoding="utf-8"))


def _report(m, ref):
    med = ref["median"]
    h = m["hierarchy"]
    print("[craft] %.1fs  longest still %.1fs (ref %.1f) · motion p90 %.2f (ref %.2f) · lead element %s (ref %.2f) · "
          "elements %s (ref %g)" % (m["seconds"], m["longest_still_s"], med["longest_still_s"], m["motion_p90"],
                                    med["motion_p90"], "-" if h["dom_med"] is None else "%.2f" % h["dom_med"],
                                    med["dom_med"], "-" if h["nblob_med"] is None else "%g" % h["nblob_med"],
                                    med["nblob_med"]))
    for ln in findings(m):
        print("  ADVISORY  " + ln)


_USAGE = "usage: craft_qa.py <out_dir> [--type] [--json] | --file film.mp4 [--json] | --reference"


def main(argv):
    import _common as _c
    _c.refuse_unknown(argv, switches=("json", "file", "reference", "type"), usage=_USAGE)
    as_json = "--json" in argv
    args = [a for a in argv if not a.startswith("--")]
    if "--reference" in argv:
        ref = reference()
        print(json.dumps(ref["median"], indent=1))
        return 0
    if "--file" in argv:
        if not args:
            print(_USAGE)
            return 2
        path, board = args[0], None
    else:
        if not args:
            print(_USAGE)
            return 2
        path = os.path.join(args[0], "out.mp4")
        bp = os.path.join(args[0], "storyboard.json")
        board = json.load(open(bp, encoding="utf-8")) if os.path.exists(bp) else None
    try:
        m = measure(path, board=board)
    except Unmeasurable as e:
        print("[craft] NOT MEASURED — %s" % e)
        return 1
    if "--type" in argv and board:
        try:
            ty = measure_type(args[0], board)
            for r in m["beats"]:
                if (r["index"] - 1) in ty:
                    r["type"] = ty[r["index"] - 1]
        except Unmeasurable as e:
            print("[craft] type NOT MEASURED — %s" % e)
    if as_json:
        print(json.dumps(dict(m, findings=findings(m)), ensure_ascii=False, indent=1))
    else:
        _report(m, reference())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
