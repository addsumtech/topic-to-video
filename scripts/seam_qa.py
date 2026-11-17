"""seam_qa — does each cut the film's plan says is HIDDEN really hide, or is it a bare swap? Read from the pixels.

    python3 scripts/seam_qa.py <film_dir> [--json]      # reads final.mp4 (_plan.json "video"), _plan.json, shot_plan.json

A BARE cut: the whole picture swaps in one frame with nothing carrying the eye — no flash, no blur, no motion, no
travel. Measured at each cut of _plan.json on 320x180 luma: of all the frame-to-frame change within ±8 frames of the
cut, the share that happens in the single largest step, plus the brightness spike around it (a flash). Bare = one step
holds >= BARE_SHARE of the change and the spike is under SPIKE levels. Calibrated 2026-11-17 on synthetic seams of the
same two pictures: a hard cut put 1.00 of the change in one step; a white flash 0.51 (and a spike), a cross-fade 0.58,
a push 0.28. On the WorkBuddy launch film (round 3) every cut but one swapped a fully still frame for a new picture
(0.9+), and the one under a flash read as hidden.

Cross-checked against shot_plan.json (scripts/shot_plan_qa.py): a cut at a shot boundary whose planned seam_out claims
to hide or carry the change (travel, flash, whip, occlusion, light, line-carry, push, fade) but measures bare is an
ERROR: the plan says one thing and the film shows another. A bare cut planned as `beat-cut` (percussion), `match`
(a match cut is a hard cut by design) or `state` (a UI state change in one window) is what the plan said. Without a
shot plan, bare cuts are listed as a note and nothing fails (an explainer may cut plainly).
Exit 0 clean, 1 on a contradiction, 2 on a usage error or a missing video / plan.
"""
import json
import os
import subprocess
import sys

import numpy as np

import _common as _c

W, H = 320, 180
WIN = 8
BARE_SHARE = 0.85
SPIKE = 20.0
HARD_BY_DESIGN = {"beat-cut", "match", "state"}
_USAGE = "usage: seam_qa.py <film_dir> [--json]"


def _frames(video):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "scale=%d:%d" % (W, H), "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, H, W).astype(np.int16)


def measure(frames, cut):
    """{share, spike, bare} for a cut at frame index `cut` (the first frame of the new shot)."""
    a, b = max(1, cut - WIN), min(len(frames) - 1, cut + WIN)
    steps = np.array([np.abs(frames[i] - frames[i - 1]).mean() for i in range(a, b + 1)])
    if steps.sum() < 1e-6:
        return {"share": 0.0, "spike": 0.0, "bare": False}
    share = float(steps.max() / steps.sum())
    lum = np.array([frames[i].mean() for i in range(max(0, cut - 4), min(len(frames), cut + 4))])
    spike = float(lum.max() - np.median(lum))
    return {"share": round(share, 3), "spike": round(spike, 1), "bare": share >= BARE_SHARE and spike < SPIKE}


def judge(film_dir):
    plan = json.load(open(os.path.join(film_dir, "_plan.json"), encoding="utf-8"))
    fps = float(plan.get("fps", 30))
    video = os.path.join(film_dir, plan.get("video", "final.mp4"))
    sp_path = os.path.join(film_dir, "shot_plan.json")
    shots = json.load(open(sp_path, encoding="utf-8")).get("shots", []) if os.path.isfile(sp_path) else None
    frames = _frames(video)
    out = []
    for c in plan.get("cuts") or []:
        if c <= 1 or c >= len(frames) - 1:
            continue
        m = measure(frames, int(c))
        seam = None
        if shots:
            t = c / fps
            near = [s for s in shots[:-1] if abs(float(s["end"]) - t) <= 0.2]
            seam = near[0].get("seam_out") if near else None
        m.update(frame=int(c), seam=seam,
                 contradiction=bool(m["bare"] and seam is not None and seam not in HARD_BY_DESIGN))
        out.append(m)
    return out, shots is not None


def main(argv):
    _c.refuse_unknown(argv, valued=(), switches=("json",), usage=_USAGE)
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    if not os.path.isfile(os.path.join(d, "_plan.json")):
        print("seam_qa: %s has no _plan.json" % d, file=sys.stderr)
        return 2
    cuts, planned = judge(d)
    bad = [c for c in cuts if c["contradiction"]]
    if "--json" in argv:
        print(json.dumps({"cuts": cuts, "planned": planned}))
    else:
        for c in bad:
            print("BARE   cut at frame %d is a bare swap (%.0f%% of the change in one frame, no flash) but the plan "
                  "says '%s': hide it as planned, or plan it honestly" % (c["frame"], c["share"] * 100, c["seam"]))
        bare = [c for c in cuts if c["bare"]]
        note = "" if planned else " (no shot_plan.json: noted, not judged)"
        print("[seam_qa] %s  %d cut(s), %d bare%s" % ("OK" if not bad else "RED", len(cuts), len(bare), note))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
