#!/usr/bin/env python3
"""Render ONE designed HTML page to a PNG frozen at ?p= and run the keyframe_qa floor probe on it.

The REGISTER-CONTEST primitive: each divergent register candidate gets a real rendered frame + a
deterministic floor verdict (canvas overflow / intra-box text clip / caption-zone occlusion) WITHOUT
needing a storyboard.json or a full render — so candidates are judged on pixels, and one that breaks
the floor is disqualified before any style points. Also handy for one-off page checks while authoring.

Usage:
  python scripts/snapshot.py <page.html> <out.png> [--p 1.0] [--vertical] [--no-captions] [--json]
  python scripts/snapshot.py <page.html> <out.png> --motion <clip.mp4> [--mseconds 2.0] [--mfps 12]
    — ALSO render a short ANIMATED snippet (the page's paused reveals swept p=0..1) so a register-
    contest finalist is judged in MOTION, not just as a still (a motion-led register can't show
    itself in one frame). ~24 CDP grabs + one ffmpeg encode; still writes the PNG + floor verdict.

Exit codes: 0 = rendered + floor clean · 2 = rendered but floor ISSUES (printed) · 3 = rendered but the
floor could NOT be probed (no CDP — screenshot only; UNUSABLE as a contest verdict, fall back to paper
mode) · 1 = could not render at all (missing page / no Chrome). argparse usage errors also exit 2
(stderr disambiguates). The floor is keyframe_qa._geometry_issues — the SAME classifier the pre-render
gate uses (one source of truth, thresholds can't drift). --no-captions skips the caption-zone check
(band-mode / captions-off decks); --vertical probes on the 1080x1920 canvas. Default --p 1.0 = the
settled state (what the floor is calibrated for); a mid-reveal p is for eyeballing — its verdict is
marked `advisory` in the result and should not gate anything.
"""
import argparse
import json
import os
import sys
from urllib.parse import quote

import keyframe_qa
from keyframe_qa import _geometry_issues   # noqa: F401 — re-exported: snapshot's floor IS keyframe_qa's


def _ensure_png(path):
    """The CDP fast path captures JPEG bytes; when the caller named the file .png, transcode so the
    artifact matches its extension (extension-trusting tools would mislabel it otherwise)."""
    if not path.lower().endswith(".png"):
        return
    try:
        from PIL import Image
        with Image.open(path) as im:
            if (im.format or "").upper() != "PNG":
                im.convert("RGB").save(path, "PNG")
    except Exception:
        pass   # a mislabeled-but-openable frame beats a crashed snapshot


def motion_snippet(page, out_mp4, seconds=2.0, fps=12, vertical=False, meta=None):
    """Sweep the page's frozen reveals p=0..1 into a short mp4 — the contest's motion sample.
    Deterministic (same p ladder every run). Raises when Chrome/CDP is unavailable (the still+floor
    path is the fallback; a motion snippet without CDP would be too slow to be worth it)."""
    import subprocess
    import tempfile
    meta = dict(meta or {})
    W, H = (1080, 1920) if vertical else (1920, 1080)
    url = "file://" + quote(os.path.abspath(page))
    chrome = keyframe_qa._open_cdp(meta, W, H)
    if not chrome:
        raise RuntimeError("no CDP — motion snippet unavailable (still + paper judging only)")
    n = max(2, int(round(seconds * fps)))
    try:
        with tempfile.TemporaryDirectory() as td:
            for i in range(n):
                p = i / (n - 1)
                # .jpg names: the CDP fast path captures JPEG bytes; ffmpeg's image2 demuxer picks the
                # decoder by EXTENSION, so jpeg-in-.png frames fail to decode
                chrome.shot(f"{url}?p={p:.4f}", os.path.join(td, f"f_{i:04d}.jpg"))
            # scale to the canonical canvas: the headless viewport can come up short of the window
            # size (e.g. 1920x993), and an ODD height breaks yuv420p/x264 outright
            subprocess.run(["ffmpeg", "-y", "-framerate", str(fps),
                            "-i", os.path.join(td, "f_%04d.jpg"),
                            "-vf", f"scale={W}:{H}",
                            "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", out_mp4],
                           check=True, capture_output=True)
    finally:
        chrome.close()
    return out_mp4


def _exit_code(r):
    """0 clean · 2 floor issues · 3 rendered-but-unprobed (unusable as a contest verdict)."""
    return 2 if r["issues"] else (0 if r["probed"] else 3)


def shoot(page, out_png, p=1.0, vertical=False, captions=True, meta=None):
    """Render one page frozen at ?p= and probe it. Returns {probed, p, advisory, issues, [info|note]}.
    Raises when the page cannot be rendered at all (missing file / no Chrome)."""
    meta = dict(meta or {})
    if not captions:
        meta["captions"] = False
    if not os.path.isfile(page):
        # fail FAST: Chrome would otherwise render its ERR_FILE_NOT_FOUND page, which probes "clean"
        # (real textlen, no overflowing boxes) — a false floor-PASS on a page that never existed.
        raise FileNotFoundError(page)
    W, H = (1080, 1920) if vertical else (1920, 1080)
    # percent-encode the path: an unquoted '#'/'%' truncates the file:// URL, Chrome loads its error
    # page, and the probe would return a clean verdict for a frame that was never rendered.
    url = "file://" + quote(os.path.abspath(page)) + f"?p={p}"
    advisory = p < 1.0                       # mid-reveal states shift boxes — never gate on them
    chrome = keyframe_qa._open_cdp(meta, W, H)
    if chrome:
        try:
            chrome.shot(url, out_png)
            _ensure_png(out_png)
            info = keyframe_qa._dom_probe(chrome)   # page still at the frozen state — measure it
            issues = _geometry_issues(info, meta, H)
            blank = keyframe_qa._blank_issue(info)  # a never-fired/empty page must not pass as "clean"
            if blank:
                issues = [blank] + issues
            return {"probed": True, "p": p, "advisory": advisory, "issues": issues, "info": info}
        finally:
            chrome.close()
    import scenes
    scenes._chrome_shot(url, out_png, W, H, meta)   # raises if Chrome is absent entirely
    return {"probed": False, "p": p, "advisory": advisory, "issues": [],
            "note": "no CDP — screenshot only, floor NOT probed (unusable as a contest verdict; exit 3)"}


def main():
    ap = argparse.ArgumentParser(description="one-page snapshot + keyframe_qa floor verdict")
    ap.add_argument("page")
    ap.add_argument("out")
    ap.add_argument("--p", type=float, default=1.0)
    ap.add_argument("--vertical", action="store_true")
    ap.add_argument("--no-captions", action="store_true", dest="no_captions")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--motion", default=None, metavar="CLIP_MP4",
                    help="also sweep p=0..1 into a short animated mp4 (contest finalists)")
    ap.add_argument("--mseconds", type=float, default=2.0)
    ap.add_argument("--mfps", type=int, default=12)
    a = ap.parse_args()
    try:
        r = shoot(a.page, a.out, p=a.p, vertical=a.vertical, captions=not a.no_captions)
    except Exception as e:
        print(f"[snapshot] could not render: {e}")
        sys.exit(1)
    if a.motion:
        try:
            motion_snippet(a.page, a.motion, seconds=a.mseconds, fps=a.mfps, vertical=a.vertical)
            r["motion"] = a.motion
            print(f"[snapshot] motion snippet -> {a.motion}")
        except Exception as e:
            print(f"[snapshot] motion snippet failed ({e}) — still + floor verdict only")
    if a.as_json:
        print(json.dumps(r))
    else:
        note = "" if r["probed"] else "  (" + r["note"] + ")"
        adv = "  [ADVISORY — mid-state p, do not gate]" if r["advisory"] else ""
        print(f"[snapshot] {a.out}{note}{adv}")
        for i in r["issues"]:
            print("  ✗ " + i)
    sys.exit(_exit_code(r))


if __name__ == "__main__":
    main()
