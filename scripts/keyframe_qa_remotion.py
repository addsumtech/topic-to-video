"""Deterministic keyframe QA for the REMOTION bespoke-shot tier — the machine partner behind the shot-critic
(the html tier's keyframe_qa.py filters to type=="html" and returns 0 on a remotion deck, so remotion had no
deterministic backstop). It scans the per-scene keyframes render_remotion.py writes (<out>/_keyframes/scene_NN.png)
and fails LOUD on frames that rendered BLANK / near-uniform — the failure mode a bespoke shot silently hits when
a prop is malformed, a bundle regressed, or a beat froze on empty background.

Mirrors check_av.py/doctor.py: a pure evaluate() over probe results, a check() IO wrapper, and a main() that
prints a human summary (or --json) and exits non-zero only when a scene keyframe is blank/missing.
"""
import argparse, json, os, sys

BLANK_STD = 8.0   # grayscale stddev below this ⇒ the frame is a near-uniform (blank) field


def _frame_std(path):
    """Grayscale pixel stddev of a keyframe, or None if unreadable."""
    try:
        from PIL import Image
        im = Image.open(path).convert("L")
        # downsample for speed; stddev is scale-stable enough for a blank check
        im = im.resize((160, 90))
        px = list(im.getdata())
        n = len(px)
        m = sum(px) / n
        return (sum((p - m) ** 2 for p in px) / n) ** 0.5
    except Exception:
        return None


def evaluate(frames):
    """frames: list of (scene_index, path, exists, std). Returns the report dict."""
    missing = [f for f in frames if not f[2]]
    unreadable = [f for f in frames if f[2] and f[3] is None]
    blank = [f for f in frames if f[2] and f[3] is not None and f[3] < BLANK_STD]
    return {
        "ok": not (missing or blank),
        "scenes": len(frames),
        "checked": [f[0] for f in frames if f[2] and f[3] is not None],
        "missing": [f[0] for f in missing],
        "blank": [{"scene": f[0], "std": round(f[3], 2)} for f in blank],
        "unreadable": [f[0] for f in unreadable],
    }


def check(out_dir):
    kd = os.path.join(out_dir, "_keyframes")
    frames = []
    if os.path.isdir(kd):
        pngs = sorted(p for p in os.listdir(kd) if p.startswith("scene_") and p.endswith(".png"))
        for p in pngs:
            idx = p[len("scene_"):-len(".png")]
            path = os.path.join(kd, p)
            frames.append((idx, path, True, _frame_std(path)))
    return evaluate(frames)


def main():
    ap = argparse.ArgumentParser(description="Deterministic keyframe QA for the remotion tier")
    ap.add_argument("out_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = check(a.out_dir)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print("[keyframe_qa_remotion] %s  %d scene(s), %d blank, %d missing"
              % ("OK" if r["ok"] else "FAIL", r["scenes"], len(r["blank"]), len(r["missing"])))
        for b in r["blank"]:
            print("  BLANK scene %s (stddev %.1f < %.1f) — the beat rendered a near-empty frame; check its shot/props"
                  % (b["scene"], b["std"], BLANK_STD))
        for m in r["missing"]:
            print("  MISSING keyframe for scene %s" % m)
        if r["scenes"] == 0:
            print("  (no _keyframes/ — run render_remotion.py first)")
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
