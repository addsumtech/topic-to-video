#!/usr/bin/env python3
"""repetition_qa — beats that share ONE staging: the same layout of light and dark, whatever each one says.

    python3 scripts/repetition_qa.py <out_dir> [--video=PATH] [--json]

WHY (2026-11-12). A lit-window pass staged 16 of Grok Bot's 36 beats the same way — a dark ground, a tilted white
page — through 13 different registers, and the user saw it at once: "感觉都是黑色背景用一个斜的页面展示内容，是不是有点
过于特意和重复" ("it all looks like a dark background with a tilted page showing the content; isn't that a bit too
deliberate and repetitive"). A register count cannot see it (13 registers, one wrapper); the picture can. Each beat's
settled frame (85 % of its span, caption band excluded) is reduced to a 32x18 luminance layout, normalised (so the
palette does not count, only where the light and the dark are), and beats whose layouts correlate >= R are one
staging.
Measured: the lit Grok cut 14 of 36 in one staging; the published Grok 1; WorkBuddy 5 of 24 (its night-desk plane,
which the user chose and kept); job-hunt, slide-maker, ANC and the topic-to-video promo at most 3.
WARN when the largest staging holds >= MIN_BEATS beats AND >= SHARE of the film: one staging as a film's device. It
writes <out_dir>/_repetition.jpg (those beats side by side) to LOOK at. ADVISORY: it always exits 0. A treatment the
user chose for a film's world is theirs to keep. The warning says it is there, not that it is wrong.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GW, GH = 32, 18
R = 0.8
MIN_BEATS, SHARE = 6, 0.25
SEAM = 12
CAPTION = 0.8


def _layout(video, t):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1", "-vf",
                          "scale=%d:%d,format=gray" % (GW, GH), "-f", "rawvideo", "-"], capture_output=True).stdout
    if len(raw) < GW * GH:
        return None
    f = np.frombuffer(raw[:GW * GH], np.uint8).reshape(GH, GW).astype(float)[: int(GH * CAPTION)]
    return ((f - f.mean()) / (f.std() + 1e-6)).ravel()


def largest_staging(layouts, r=R):
    """The beats (indices) of the largest group whose layouts all correlate >= r with one beat's."""
    import numpy as np
    ok = [i for i, s in enumerate(layouts) if s is not None]
    if len(ok) < 2:
        return []
    C = np.corrcoef(np.array([layouts[i] for i in ok]))
    best = []
    for a in range(len(ok)):
        m = [ok[b] for b in range(len(ok)) if C[a, b] >= r]
        if len(m) > len(best):
            best = m
    return best


def verdict(n_beats, group):
    return len(group) >= MIN_BEATS and len(group) >= SHARE * n_beats


def main(argv):
    from _common import argflag, refuse_unknown
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 0
    refuse_unknown(argv, valued=("video",), switches=("json",))
    out_dir = argv[0]
    video = argflag(argv, "video", os.path.join(out_dir, "out.mp4"))
    try:
        import numpy  # noqa: F401
        segs = [(int(a), int(b)) for a, b, *_ in json.load(open(os.path.join(out_dir, ".render_record.json"),
                                                                 encoding="utf-8"))["segments"]]
    except (ImportError, OSError, ValueError, KeyError):
        print("[repetition] UNMEASURED — needs numpy and the render record of a remotion film")
        return 0
    if not os.path.isfile(video):
        print("[repetition] UNMEASURED — no film at %s" % video)
        return 0
    ts = [((a + (SEAM if k else 0)) + ((b - a - (SEAM if k else 0)) * 0.85)) / 30.0 for k, (a, b) in enumerate(segs)]
    group = largest_staging([_layout(video, t) for t in ts])
    warn = verdict(len(segs), group)
    if "--json" in argv:
        print(json.dumps({"beats": len(segs), "largest": [g + 1 for g in group], "warn": warn}))
    if warn:
        from PIL import Image
        import io
        ims = []
        for g in group[:12]:
            r = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % ts[g], "-i", video, "-frames:v", "1", "-vf",
                                "scale=320:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
            if r.stdout:
                ims.append(Image.open(io.BytesIO(r.stdout)).convert("RGB"))
        if ims:
            sheet = Image.new("RGB", (len(ims) * 324, ims[0].height), "white")
            for i, im in enumerate(ims):
                sheet.paste(im, (i * 324, 0))
            sheet.save(os.path.join(out_dir, "_repetition.jpg"), quality=84)
        print("[repetition] WARN %d of %d beats share one staging (beats %s) — one treatment as the film's device; "
              "LOOK at _repetition.jpg: keep it only where it carries the beat, and keep the film's own contrast"
              % (len(group), len(segs), ", ".join(str(g + 1) for g in group)))
    else:
        print("[repetition] OK  the largest shared staging is %d of %d beats" % (len(group), len(segs)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
