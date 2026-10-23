#!/usr/bin/env python3
"""BANDING — the rings a smooth dark gradient turns into once it has been encoded, measured on the DELIVERED file.

    python3 scripts/banding_qa.py <out_dir> [--every SECONDS] [--json]

WHY A GATE. A gradient banded by the encode looks clean in every still a gate renders (a PNG straight from Chrome)
and in the DOM; it shows only in the H.264 the viewer gets. Measured with CAMBI (libvmaf's Contrast-Aware Multiscale
Banding Index; visible past ~5 — references/craft-research.md §4): this tier's remotion films measured a median of 12-15 and
peaks of 22 on the dark radial grounds most DNAs paint — concentric rings on the opening frame — until the delivery
dither (remotion/src/runtime/dither.tsx) and JPEG-95 frames took the same opening to 0.0. Nothing else in the pipeline
could see it.

WHAT IT REPORTS. One frame every `--every` seconds (default 1) through ffmpeg's libvmaf `cambi` feature; a scene whose
MEDIAN sample is over BANDING_VISIBLE is a finding (a single banded frame inside a dissolve is not). Scenes are
located by the storyboard's durations, near enough to name the beat. Exit 0 clean · 1 findings · 2 not measured (no
out.mp4, or an ffmpeg without libvmaf/cambi — said, never passed off as clean). ADVISORY in the delivery gates
(critic_ledger.DELIVERY_GATES): it records, it does not block.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

BANDING_VISIBLE = 5.0      # CAMBI: ~5 is where banding starts to be visible (references/craft-research.md §4)


def cambi_samples(mp4, every=1.0):
    """[(seconds, cambi)] — one sample every `every` seconds; None when ffmpeg cannot measure (no libvmaf/cambi)."""
    fps = _fps(mp4)
    if not fps:
        return None
    n = max(1, int(round(every * fps)))
    fd, log = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-i", mp4, "-lavfi",
                            "[0:v][1:v]libvmaf=feature=name=cambi:n_subsample=%d:log_fmt=json:log_path=%s" % (n, log),
                            "-f", "null", "-"], capture_output=True, text=True)
        if r.returncode != 0:
            return None
        frames = json.load(open(log, encoding="utf-8")).get("frames") or []
    except (OSError, ValueError):
        return None
    finally:
        if os.path.exists(log):
            os.remove(log)
    out = [(f["frameNum"] / fps, float(f["metrics"]["cambi"])) for f in frames
           if isinstance(f.get("metrics"), dict) and "cambi" in f["metrics"]]
    return out or None


def _fps(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "default=nw=1:nk=1", mp4], capture_output=True, text=True)
    m = re.match(r"(\d+)/(\d+)", (r.stdout or "").strip())
    return int(m.group(1)) / int(m.group(2)) if m and int(m.group(2)) else None


def scene_spans(out_dir):
    """[(label, start, end)] from the storyboard's durations; [] when there is none to read."""
    try:
        board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return []
    spans, t = [], 0.0
    for i, s in enumerate(board.get("slides") or []):
        d = float(s.get("duration") or 0)
        spans.append(("scene %02d" % int(s.get("index") or i + 1), t, t + d))
        t += d
    return spans


def check(out_dir, every=1.0, mp4=None):
    mp4 = mp4 or os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(mp4):
        return {"measured": False, "why": "no %s" % os.path.basename(mp4), "findings": [], "samples": []}
    samples = cambi_samples(mp4, every)
    if samples is None:
        return {"measured": False, "why": "this ffmpeg cannot measure CAMBI (libvmaf with the cambi feature)",
                "findings": [], "samples": []}
    spans = scene_spans(out_dir) or [("the film", 0.0, float("inf"))]
    findings = []
    for label, a, b in spans:
        vals = sorted(v for t, v in samples if a <= t < b)
        if not vals:
            continue
        med = vals[len(vals) // 2]
        if med > BANDING_VISIBLE:
            worst = max(((t, v) for t, v in samples if a <= t < b), key=lambda x: x[1])
            findings.append({"scene": label, "median": round(med, 2), "worst": round(worst[1], 2),
                             "at": round(worst[0], 2)})
    return {"measured": True, "findings": findings, "samples": [(round(t, 2), round(v, 2)) for t, v in samples]}


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__.strip())
        return 2
    every = 1.0
    for a in argv:
        if a.startswith("--every="):
            every = float(a.split("=", 1)[1])
    r = check(os.path.abspath(args[0]), every)
    if "--json" in argv:
        print(json.dumps(r, ensure_ascii=False))
    elif not r["measured"]:
        print("[banding_qa] NOT MEASURED: %s" % r["why"])
    else:
        vals = sorted(v for _t, v in r["samples"])
        print("[banding_qa] %s  %d sample(s), CAMBI median %.2f max %.2f (visible past %.0f)"
              % ("FINDINGS" if r["findings"] else "OK", len(vals), vals[len(vals) // 2], vals[-1], BANDING_VISIBLE))
        for f in r["findings"]:
            print("  %s: CAMBI median %.1f, worst %.1f at %.1fs" % (f["scene"], f["median"], f["worst"], f["at"]))
        if r["findings"]:
            print("  a smooth ground bands after encoding: on the remotion tier the delivery dither is on unless "
                  "meta.dither is false (runtime/dither.tsx); on the html tier keep the theme's grain on those pages "
                  "(no body.no-grain)")
    return 2 if not r["measured"] else 1 if r["findings"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
