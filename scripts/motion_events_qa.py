#!/usr/bin/env python3
"""motion_events_qa — every place the picture changes sharply where the film did not plan a cut, as a strip to LOOK at.
    python3 scripts/motion_events_qa.py <out_dir> [--video=PATH] [--json]

WHY (WorkBuddy, 2026-11-11). Three defects reached a delivered film with every gate green, and the user saw the first:
  * the last six frames of beat 11 jumped between five framings (coverage measured its punch-in afresh in each render
    tab, before layout) — no flash (each frame differs from both neighbours, but so do the neighbours), and shake_qa's
    half-second window held the cut into beat 12 too, so its net travel hid the vibration;
  * beat 10's light switched off six frames after its cut (a literal SVG id resolved to the leaving beat's gradient) —
    a change that stays changed reads as a cut to every frame-difference rule;
  * beat 17 cut to a close-up 0.3 s into the beat, mid-entrance (the carried cut's clock lead).
Each was a sharp change OFF THE PLAN. The plan is known: the seams (Film's cut frame) and coverage's steps (on the voice's
clock). This lists what is not on it, with a strip of the frames around each, for the reviewer's eye.

WHY ADVISORY. Registers snap legitimately inside a beat (a file drops, a logo lands, a carousel pans fast over repeating
slides), and on the corpus a frame-difference rule refused those as readily as the defects. The root causes of the three
above are fixed where they arose (runtime/coverage.tsx readiness, runtime/idScope.tsx, PictureLeadContext); this is the
net for the next kind, and a net that refuses designed motion would be switched off. Exit 0 always; the strip is the
output: <out_dir>/_motion_events.jpg.

A FOURTH (topic-to-video promo, 2026-11-12): six screens went black 8-10 frames before their cut — a clip's Sequence
sized from the beat's duration, which the cut carry's clock lead reaches before the beat leaves (runtime/motion
usePictureEnd; validate refuses the plain pattern). Inside the seam pad, so JUMP never saw five of them: BLANK does.

WHAT IT FLAGS (decoded 160x90 grey, the caption band excluded — it changes on every word):
  BLANK   before a seam, a region of the leaving picture (>= BLANK_CELLS cells of a 16x8 grid) switches in ONE frame to
          flat dark and stays so until the cut — what a span ending under a beat looks like (a designed fade is gradual);
  JUMP    one frame-to-frame change > JUMP_MIN and > JUMP_RATIO x both neighbours', off the plan;
  WANDER  a window of 4-8 frames whose summed change is > WANDER_PATH and > WANDER_RATIO x the change between its ends
          (the picture moved a lot and ended near where it began), with >= 3 large steps, off the plan.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

W, H = 160, 90
CAPTION_FROM = 0.8          # the caption band (layout contentBottom ~0.81 H) is not the picture
JUMP_MIN, JUMP_RATIO = 6.0, 4.0
WANDER_PATH, WANDER_RATIO, WANDER_STEP = 25.0, 2.5, 4.0
PLAN_PAD = 2                # frames either side of a planned cut
GX, GY = 16, 8              # BLANK's grid
BLANK_CELLS, BLANK_BACK = 3, 24
CUT_AT = 6                  # the leaving beat stays on screen to here in its seam (Film's cutFrame(TR))
FPS = 30


def frames(mp4):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vf", "scale=%d:%d" % (W, H), "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], capture_output=True).stdout
    if not raw:
        return None
    F = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
    return F[:, : int(H * CAPTION_FROM), :]


def planned(out_dir):
    """{frame: why} for every planned cut: each seam's span (the leaving beat's tail and the cut frame) and each coverage
    step on the voice's clock. And [(a, b)] per beat. Read from the render's own record and props."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import remotion_segments as rs
    rec = json.load(open(os.path.join(out_dir, ".render_record.json"), encoding="utf-8"))
    props = json.load(open(os.path.join(out_dir, ".remotion-props.json"), encoding="utf-8"))
    segs = [(a, b) for a, b, *_ in rec["segments"]]
    tr = rs.seam_frames()
    plan = {}
    for k, (a, b) in enumerate(segs):
        if k:
            for f in range(a - PLAN_PAD, a + tr + PLAN_PAD):
                plan.setdefault(f, "seam into beat %d" % (k + 1))
        scenes = props.get("scenes") or []
        for st in ((scenes[k].get("coverage") if k < len(scenes) else None) or [])[1:]:
            c = a + int(round(float(st["t"]) * FPS))
            for f in range(c - PLAN_PAD, c + PLAN_PAD + 1):
                plan.setdefault(f, "coverage step of beat %d" % (k + 1))
    return plan, segs


def scan(F, plan):
    import numpy as np
    d = np.abs(np.diff(F, axis=0)).mean(axis=(1, 2))
    events = []
    for i in range(1, len(d) - 1):
        if d[i] > JUMP_MIN and d[i] > JUMP_RATIO * max(d[i - 1], d[i + 1], 0.5) and i not in plan and i + 1 not in plan:
            events.append({"kind": "JUMP", "frame": i, "change": round(float(d[i]), 1)})
    for n in (4, 6, 8):
        for i in range(len(F) - n):
            if any(f in plan for f in range(i, i + n + 1)):
                continue
            path = float(d[i:i + n].sum())
            net = float(np.abs(F[i + n] - F[i]).mean())
            if path > WANDER_PATH and (d[i:i + n] > WANDER_STEP).sum() >= 3 and path > WANDER_RATIO * max(net, 1.0):
                events.append({"kind": "WANDER", "frame": i, "frames": n, "path": round(path, 1), "net": round(net, 1)})
    events.sort(key=lambda e: e["frame"])
    kept = []
    for e in events:                                  # one event per RUN: a sustained oscillation is one thing to judge
        if kept and e["frame"] - kept[-1]["to"] <= 15:
            kept[-1]["to"] = e["frame"]
            continue
        kept.append(dict(e, to=e["frame"]))
    return kept


def blanks(F, segs):
    """BLANK events: per seam, the step (before the seam starts) at which the most cells switch to flat dark in one frame
    and hold flat dark until the leaving beat's last frame on screen."""
    import numpy as np
    N, H, W_ = F.shape
    ch, cw = H // GY, W_ // GX
    c = F[:, :GY * ch, :GX * cw].reshape(N, GY, ch, GX, cw).transpose(0, 1, 3, 2, 4).reshape(N, GY, GX, -1)
    M, S = c.mean(-1), c.std(-1)
    out = []
    for k in range(1, len(segs)):
        a = segs[k][0]
        end, lo = a + CUT_AT, max(segs[k - 1][0] + 3, a - BLANK_BACK)
        if end >= N or lo >= a:
            continue
        best = None
        for f in range(lo, a):
            flat = np.all((S[f:end] < 3) & (M[f:end] < 40), axis=0)
            was = (S[f - 1] > 4) | (M[f - 1] - M[f] > 12)
            step = np.abs(M[f] - M[f - 1]) + np.abs(S[f] - S[f - 1])
            before = np.abs(M[f - 1] - M[f - 2]) + np.abs(S[f - 1] - S[f - 2])
            jump = (step > 10) & (step > 3 * before + 2)     # a SWITCH out of a steady picture, not a fade's last step
            n = int((flat & was & jump).sum())
            if n and (best is None or n > best[1]):
                best = (f, n)
        if best and best[1] >= BLANK_CELLS:
            out.append({"kind": "BLANK", "frame": best[0], "to": end - 1, "cells": best[1]})
    return out


def strip(mp4, events, out_path, beat_of):
    from PIL import Image, ImageDraw
    import io
    rows = []
    for e in events[:24]:
        f0 = max(0, e["frame"] - 2)
        # one input-seeked decode per event (a `select` per frame decodes the film from its start every time)
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.4f" % (f0 / FPS), "-i", mp4, "-frames:v", "8",
                            "-vf", "scale=240:-2,tile=8x1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
        tile = Image.open(io.BytesIO(r.stdout)).convert("RGB") if r.stdout else Image.new("RGB", (8 * 240, 135))
        tw = tile.width // 8
        rows.append((e, [tile.crop((c * tw, 0, (c + 1) * tw, tile.height)) for c in range(8)]))
    if not rows:
        return None
    w, h = rows[0][1][0].size
    sheet = Image.new("RGB", (8 * (w + 4), len(rows) * (h + 22)), "white")
    dr = ImageDraw.Draw(sheet)
    for r, (e, ims) in enumerate(rows):
        y = r * (h + 22)
        dr.text((4, y + 4), "%s  frames %d-%d  (%.2f s)  beat %s  %s" % (
            e["kind"], e["frame"], e["to"], e["frame"] / FPS, beat_of(e["frame"]),
            ("change %.1f" % e["change"]) if e["kind"] == "JUMP" else
            ("%d cells blank to the cut" % e["cells"]) if e["kind"] == "BLANK" else
            ("path %.1f net %.1f over %d frames" % (e["path"], e["net"], e["frames"]))), fill="black")
        for c, im in enumerate(ims):
            sheet.paste(im, (c * (w + 4), y + 20))
    sheet.save(out_path, quality=85)
    return out_path


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 0
    from _common import argflag, refuse_unknown
    refuse_unknown(argv, valued=("video",), switches=("json",))
    out_dir = argv[0]
    video = argflag(argv, "video", os.path.join(out_dir, "out.mp4"))
    try:
        import numpy  # noqa: F401
    except ImportError:
        print("[motion_events] UNMEASURED — needs numpy")
        return 0
    if not os.path.exists(video):
        print("[motion_events] UNMEASURED — no film at %s" % video)
        return 0
    F = frames(video)
    if F is None or len(F) < 10:
        print("[motion_events] UNMEASURED — could not decode %s" % video)
        return 0
    try:
        plan, segs = planned(out_dir)
    except (OSError, ValueError, KeyError) as e:
        print("[motion_events] no render record (%s): every sharp change is listed, planned or not" % e)
        plan, segs = {}, []

    def beat_of(f):
        for k, (a, b) in enumerate(segs):
            if a <= f <= b:
                return k + 1
        return "?"
    events = sorted(blanks(F, segs) + scan(F, plan), key=lambda e: (e["kind"] != "BLANK", e["frame"]))
    path = strip(video, events, os.path.join(out_dir, "_motion_events.jpg"), beat_of) if events else None
    if "--json" in argv:
        print(json.dumps({"events": events, "sheet": path}, ensure_ascii=False))
    print("[motion_events] ADVISORY  %d sharp change(s) off the planned cuts in %d frames%s" % (
        len(events), len(F), (" — LOOK at each: %s" % path) if path else ""))
    for e in events:
        print("  %-6s frames %5d-%-5d %6.2f s  beat %s" % (e["kind"], e["frame"], e["to"], e["frame"] / FPS,
                                                         beat_of(e["frame"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
