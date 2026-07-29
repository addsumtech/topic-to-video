#!/usr/bin/env python3
"""SHOT QA (P5) — a deterministic, thresholded reviewer for the Remotion cinematic tier that scores the
RENDERED pixels before the full render ships. It is the mechanical half of the guide's "reviewer agent":
the design-critic (D12) still judges what only a human can (is the move MOTIVATED for this beat), but this
gate catches the objective failures from the frames themselves and can BLOCK a render.

DESIGN PRINCIPLE — measure, or abstain; never fake-confident. A gate that reports a proxy as if it were
truth is worse than no gate. So this scorer HARD-FAILS only on UNAMBIGUOUS defects it can measure reliably
(a blank/dead frame; a declared camera move that produced ~no motion — the "invisible move" bug), SCORES
the softer dimensions (composition focal-dominance, caption-zone cleanliness, depth differential) into a
0-100 composite, and ABSTAINS (returns None for a dimension) when it cannot measure it (e.g. motion on a
still hold, or anything at all when numpy/ffmpeg are missing). Abstained dimensions never lower a score.

It reads the same frames the D12 filmstrip is built from (samples per cinematic scene from the mp4), so
the reviewer and the human look at the same evidence. Emits <out_dir>/shot_qa.json.

Usage:  python scripts/shot_qa.py <out_dir> [--mp4 out.mp4] [--threshold 70] [--json]
        exit 0 = pass · 2 = below threshold / a hard floor tripped · 3 = could not score (no numpy/ffmpeg)
"""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_remotion as rr

_CAPTION_ZONE = 0.14      # bottom fraction where an overlay caption burns
_MOTION_DEAD = 0.004      # mean inter-frame |Δ| (0..1) below this on a declared move = the move didn't render
_MOTION_HEALTHY = 0.03    # inter-frame |Δ| that scores full motion marks
_BLANK_STD = 4.0          # a frame whose luma std is under this is near-uniform (blank / flat-collapsed)
_BLANK_DARK = 6.0         # ... or whose mean luma is under this is near-black


def _np():
    try:
        import numpy as np
        return np
    except Exception:
        return None


def _gray(im, np):
    return np.asarray(im.convert("L"), dtype=np.float32)


def _detail_map(g, np, blocks=4):
    """Per-block detail (gradient energy) on a blocks×blocks grid — the basis for focal dominance."""
    gy, gx = np.gradient(g)
    energy = np.abs(gx) + np.abs(gy)
    h, w = energy.shape
    out = np.zeros((blocks, blocks), dtype=np.float32)
    for by in range(blocks):
        for bx in range(blocks):
            out[by, bx] = energy[by * h // blocks:(by + 1) * h // blocks,
                                 bx * w // blocks:(bx + 1) * w // blocks].mean()
    return out


def score_scene(frames, declared_move, is_3d):
    """Pure scoring core (testable without Node/ffmpeg): frames = a list of PIL Images across ONE scene.
    Returns {scores, floors, metrics}. scores values are 0-100 or None (ABSTAINED). floors is a list of
    unambiguous BLOCKING defects.

    HONESTY over coverage — only two things are measured with enough reliability to gate:
      • FLOORS (block): a blank/flat/collapsed frame; a DECLARED camera move that produced ~no motion.
      • composition (0-100): focal dominance — is there ONE clear focal region, or a flat/even frame.
    Everything else ABSTAINS on purpose: motion is NOT scored 'more is better' (restraint is the premium
    goal — only the dead-move floor is a defect); depth is reported as a metric but only SCORED for a
    declared 3D/lens scene; caption-zone/legibility can't be measured from a CAPTIONED frame (the burned
    caption's own edges confound it) so there is no typography score. An abstained dim never lowers a score.
    """
    np = _np()
    if np is None or not frames:
        return {"scores": {}, "floors": [], "metrics": {}, "abstained": True}
    grays = [_gray(im, np) for im in frames]
    floors, scores, metrics = [], {}, {}

    # ── FLOOR: a blank / near-black / flat frame is an unambiguous render failure ──
    stds = [float(g.std()) for g in grays]
    means = [float(g.mean()) for g in grays]
    metrics["luma_std_min"] = round(min(stds), 2)
    metrics["luma_mean_min"] = round(min(means), 2)
    if min(stds) < _BLANK_STD or min(means) < _BLANK_DARK:
        floors.append("blank/flat frame (luma std %.1f, mean %.1f) — a dead or collapsed render"
                      % (min(stds), min(means)))

    # ── motion: measured, but only the DEAD-MOVE case is a defect (restrained motion is GOOD) ──
    if len(grays) >= 2:
        steps = [float(np.abs(grays[i + 1] - grays[i]).mean()) / 255.0 for i in range(len(grays) - 1)]
        total = float(np.mean(steps))
        metrics["motion_mean"] = round(total, 5)
        if declared_move and total < _MOTION_DEAD:
            floors.append("declared camera move but ~no motion rendered (mean |Δ|=%.4f) — the move is invisible" % total)
        scores["motion"] = None  # abstain: a graded 'more motion = better' score would punish good restraint

        # depth differential (real parallax vs a uniform zoom) — reported always; SCORED only for a 3D scene
        diff = np.abs(grays[-1] - grays[0])
        h, w = diff.shape
        reg = [float(diff[:h // 2, :].mean()), float(diff[h // 2:, :].mean()),
               float(diff[:, :w // 2].mean()), float(diff[:, w // 2:].mean())]
        depth_ratio = (max(reg) - min(reg)) / (max(reg) + 1e-6)
        metrics["depth_differential"] = round(depth_ratio, 3)
        scores["depth"] = int(round(100 * max(0.0, min(1.0, depth_ratio / 0.5)))) if (is_3d and declared_move and total >= _MOTION_DEAD) else None
    else:
        scores["motion"] = scores["depth"] = None

    # ── composition: focal dominance — ONE region should carry the detail, not a flat/even spread ──
    dm = _detail_map(grays[len(grays) // 2], np)   # judge the mid (settled) frame
    flat = np.sort(dm.flatten())
    top = float(flat[-1]); med = float(np.median(flat)) + 1e-6
    dominance = top / med
    competing = int((flat >= 0.85 * top).sum())     # blocks within 85% of the peak (>2 = competing foci)
    metrics["focal_dominance"] = round(dominance, 2)
    metrics["competing_foci"] = competing
    if dominance < 1.15:
        floors.append("no focal dominance (dominance %.2f) — a flat, evenly-detailed frame with no subject" % dominance)
    # lenient: dominance 1.15 -> 20, >=3.5 -> 100; >2 competing peaks shave it a little.
    dom_s = 0.2 + 0.8 * max(0.0, min(1.0, (dominance - 1.15) / (3.5 - 1.15)))
    scores["composition"] = int(round(100 * dom_s * (1.0 if competing <= 2 else 0.8)))

    # ── LEGIBILITY FLOOR: the FOCAL region (centre, ABOVE the caption band) must not be a dark, flat
    # murk. This is the cinematic-tier analog of the HTML tier's WCAG contrast discipline — measured from
    # pixels, caption-excluded (so a burned caption can't confound it), and CONSERVATIVE: it fires only
    # when the focal region is BOTH dark AND low-contrast (a genuinely unreadable frame), never on a
    # legitimately dark-but-legible card (light text on a dark panel = high contrast = passes). ──
    g = grays[len(grays) // 2]
    fh, fw = g.shape
    focal = g[int(fh * 0.15):int(fh * 0.72), int(fw * 0.22):int(fw * 0.78)]
    f_mean, f_std = float(focal.mean()), float(focal.std())
    metrics["focal_luma_mean"] = round(f_mean, 1)
    metrics["focal_contrast_std"] = round(f_std, 1)
    if f_mean < 20 and f_std < 8:
        floors.append("focal region is dark + flat (luma %.0f, contrast %.0f) — content is murky/illegible; "
                      "lift exposure or give the subject a legible ground" % (f_mean, f_std))

    # typography/caption-zone: NOT scored — a captioned frame's burned caption confounds any bottom-band
    # measurement. (The HTML tier checks this pre-burn via keyframe_qa; the cinematic tier can't here.)
    scores["typography"] = None

    return {"scores": scores, "floors": floors, "metrics": metrics, "abstained": False}


def _declared_move(s):
    """Does this scene claim a camera move (so 'no motion' is a failure, not a valid hold)?"""
    shots = rr._scene_shots(s) or []
    if isinstance(shots, list) and (len(shots) > 1 or any(
            isinstance(sh, dict) and str(sh.get("motion", "STATIC")).upper() != "STATIC" for sh in shots)):
        return True
    cam = s.get("camera") or (s.get("props") or {}).get("camera")
    lens = s.get("lens") or (s.get("props") or {}).get("lens")
    c3d = s.get("camera3d") or (s.get("props") or {}).get("camera3d")
    return bool((isinstance(cam, list) and len(cam) > 1) or (isinstance(lens, list) and len(lens) > 1)
                or (isinstance(c3d, list) and len(c3d) > 1) or rr._scene_planes(s))


def _sample_frames(mp4, t0, dur, n=5):
    """Sample n full-res frames across a scene's span (mirrors _write_filmstrips' timing)."""
    try:
        from PIL import Image
    except Exception:
        return []
    import shutil, tempfile
    if not shutil.which("ffmpeg") or not os.path.exists(mp4):
        return []
    frames = []
    tmp = tempfile.mkdtemp()
    for i in range(n):
        t = t0 + dur * (0.06 + 0.9 * i / (n - 1))
        fp = os.path.join(tmp, "f%d.png" % i)
        subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", mp4, "-frames:v", "1", "-y", fp], check=False)
        if os.path.exists(fp):
            frames.append(Image.open(fp).copy())
    shutil.rmtree(tmp, ignore_errors=True)
    return frames


def evaluate(out_dir, mp4=None, threshold=70):
    """Score every cinematic scene of a rendered deck. Returns a report dict; writes shot_qa.json."""
    import shutil
    data = rr.sb.load(os.path.join(out_dir, "storyboard.json"))
    mp4 = mp4 or os.path.join(out_dir, "out.mp4")
    report = {"ok": True, "threshold": threshold, "scenes": [], "abstained": False}
    if _np() is None or not shutil.which("ffmpeg") or not os.path.exists(mp4):
        report.update(ok=True, abstained=True, reason="numpy/ffmpeg/mp4 unavailable — UNSCORED, not passed")
        _write(out_dir, report)
        return report
    t0 = 0.0
    for s in data.get("slides", []):
        dur = float(s.get("duration") or 0)
        is_cine = (s.get("type") == "cinematic" or rr._scene_layers(s) or rr._scene_planes(s)
                   or (rr._scene_stage(s) and rr._scene_shots(s)))
        if is_cine and dur > 0.2:
            frames = _sample_frames(mp4, t0, dur, n=5)
            is_3d = bool(s.get("lens") or (s.get("props") or {}).get("lens")
                         or rr._scene_planes(s) or (rr._scene_stage(s) and rr._scene_shots(s)))
            r = score_scene(frames, _declared_move(s), is_3d)
            vals = [v for v in r["scores"].values() if isinstance(v, (int, float))]
            composite = int(round(sum(vals) / len(vals))) if vals else None
            passed = (not r["floors"]) and (composite is None or composite >= threshold)
            report["scenes"].append({"index": s.get("index"), "composite": composite,
                                     "scores": r["scores"], "floors": r["floors"],
                                     "metrics": r["metrics"], "passed": passed})
            if not passed:
                report["ok"] = False
        t0 += dur
    _write(out_dir, report)
    return report


def _write(out_dir, report):
    try:
        with open(os.path.join(out_dir, "shot_qa.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(description="Score the rendered cinematic frames (P5 reviewer)")
    ap.add_argument("out_dir")
    ap.add_argument("--mp4", default=None)
    ap.add_argument("--threshold", type=int, default=70)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rep = evaluate(a.out_dir, a.mp4, a.threshold)
    if a.json:
        print(json.dumps(rep, indent=1))
    else:
        if rep.get("abstained"):
            print("[shot_qa] UNSCORED — %s" % rep.get("reason", "")); return sys.exit(3)
        for sc in rep["scenes"]:
            tag = "ok " if sc["passed"] else "FAIL"
            print("[shot_qa] scene %02d  %s  composite=%s  %s%s"
                  % (sc["index"], tag, sc["composite"], sc["scores"],
                     "  FLOORS: " + "; ".join(sc["floors"]) if sc["floors"] else ""))
        print("[shot_qa] %s (threshold %d)" % ("PASS" if rep["ok"] else "BELOW THRESHOLD / FLOOR", rep["threshold"]))
    sys.exit(0 if rep["ok"] else 2)


if __name__ == "__main__":
    main()
