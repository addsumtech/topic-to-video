"""Deterministic keyframe QA for the REMOTION bespoke-shot tier — the machine partner behind the shot-critic
(the html tier's keyframe_qa.py filters to type=="html" and returns 0 on a remotion deck, so remotion had no
deterministic backstop). It scans the per-scene keyframes render_remotion.py writes (<out>/_keyframes/scene_NN.png)
and fails LOUD on frames that rendered BLANK / near-uniform — the failure mode a bespoke shot silently hits when
a prop is malformed, a bundle regressed, or a beat froze on empty background.

Mirrors check_av.py/doctor.py: a pure evaluate() over probe results, a check() IO wrapper, and a main() that
prints a human summary (or --json) and exits non-zero only when a scene keyframe is blank/missing/unreadable.

THE UNIVERSE IS THE FILM, NOT THE DIRECTORY. This used to build its list by globbing `_keyframes/scene_*.png`,
so a beat whose keyframe was never written was not "missing" — it was not in the universe at all. The `missing`
branch could never fire (every frame was appended with exists=True by construction) and `render_remotion` writes
those frames with `subprocess.run(..., check=False)`, so a failed ffmpeg seek leaves no file and says nothing.
A seven-of-eight render therefore printed "7 scene(s), 0 blank, 0 missing" and exited 0. The list now comes from
`storyboard.json` — the same source of truth the renderer numbers its frames from — so an absent frame is a
MISSING beat. And a frame PIL cannot open is reported with PIL's own message instead of being dropped from both
the blank test and the verdict: an unreadable frame is not a clean one.
"""
import argparse, json, os, sys

BLANK_STD = 8.0   # grayscale stddev below this ⇒ the frame is a near-uniform (blank) field
FRAME_NAME = "scene_%02d.png"   # render_remotion.py writes one per beat, numbered by POSITION (1-based)



def _pixels(im):
    """Every pixel of `im` as a list. Pillow 12 deprecates getdata() (gone in 14); get_flattened_data()
    is its replacement, with getdata() kept only for an older Pillow."""
    flat = getattr(im, "get_flattened_data", None)
    return list(flat() if flat else im.getdata())

def _frame_std(path):
    """(grayscale pixel stddev, None) for a keyframe, or (None, reason) when it cannot be read.

    The reason is the exception's own message — never a bare "unreadable". A missing PIL, a truncated PNG
    and a zero-byte file are three different repairs, and a gate that prints one word for all three sends
    the reader back to reproduce it by hand.
    """
    try:
        from PIL import Image
    except Exception as e:                                   # noqa: BLE001 — report, don't drop the frame
        return None, "Pillow is not importable (%s: %s) — no keyframe can be measured" % (type(e).__name__, e)
    try:
        im = Image.open(path).convert("L")
        # downsample for speed; stddev is scale-stable enough for a blank check
        im = im.resize((160, 90))
        px = _pixels(im)
        n = len(px)
        m = sum(px) / n
        return (sum((p - m) ** 2 for p in px) / n) ** 0.5, None
    except Exception as e:                                   # noqa: BLE001 — report, don't drop the frame
        return None, "%s: %s" % (type(e).__name__, e)


def _unpack(f):
    """(scene, path, exists, std, reason) from a 4- or 5-tuple probe row."""
    idx, path, exists, std = f[0], f[1], f[2], f[3]
    reason = f[4] if len(f) > 4 else None
    if std is None and not reason and exists:
        reason = "could not be read (no reason recorded)"
    return idx, path, exists, std, reason


def evaluate(frames, universe="", extra=(), notes=()):
    """frames: list of (scene, path, exists, std[, reason]). Returns the report dict.

    `universe` names where the beat list came from, `extra` lists keyframes on disk that no beat claims,
    and `notes` carries anything that stopped the universe being derived from the film.
    """
    rows = [_unpack(f) for f in frames]
    missing = [r for r in rows if not r[2]]
    unreadable = [r for r in rows if r[2] and r[3] is None]
    blank = [r for r in rows if r[2] and r[3] is not None and r[3] < BLANK_STD]
    measured = [r for r in rows if r[2] and r[3] is not None]
    not_measured = ([{"scene": r[0], "reason": "no %s — the renderer wrote no frame for this beat "
                                                "(render_remotion runs ffmpeg with check=False, so a failed "
                                                "seek is silent)" % os.path.basename(r[1])} for r in missing]
                    + [{"scene": r[0], "reason": r[4]} for r in unreadable])
    return {
        "ok": not (missing or blank or unreadable),
        "complete": not not_measured,
        "universe": universe,
        "scenes": len(rows),
        "measured": len(measured),
        "checked": [r[0] for r in measured],
        "missing": [r[0] for r in missing],
        "blank": [{"scene": r[0], "std": round(r[3], 2)} for r in blank],
        "unreadable": [{"scene": r[0], "reason": r[4]} for r in unreadable],
        "not_measured": not_measured,
        "extra": list(extra),
        "notes": list(notes),
    }


def _beats(out_dir):
    """(ordered beat labels, universe sentence, notes) — parsed from storyboard.json, never globbed.

    Falls back to the directory listing when there is no readable board, and SAYS so: a universe taken
    from the artifact under test can only ever confirm what the artifact already contains.
    """
    board = os.path.join(out_dir, "storyboard.json")
    try:
        slides = json.load(open(board, encoding="utf-8")).get("slides") or []
        if not isinstance(slides, list):
            raise ValueError("`slides` is not a list")
        if slides:
            return (["%02d" % (i + 1) for i in range(len(slides))],
                    "%d beat(s) in storyboard.json" % len(slides), [])
        note = "storyboard.json declares no slides"
    except Exception as e:                                   # noqa: BLE001 — fall back, but never silently
        note = "storyboard.json could not be read (%s: %s)" % (type(e).__name__, e)
    kd = os.path.join(out_dir, "_keyframes")
    found = sorted(p[len("scene_"):-len(".png")] for p in os.listdir(kd)
                   if p.startswith("scene_") and p.endswith(".png")) if os.path.isdir(kd) else []
    return (found, "%d keyframe file(s) on disk" % len(found),
            [note + " — the beat list is the _keyframes/ listing, so a beat whose frame was never written "
                    "cannot be reported as missing. Fix the board and re-run to get a real coverage number."])


def check(out_dir):
    kd = os.path.join(out_dir, "_keyframes")
    beats, universe, notes = _beats(out_dir)
    frames = []
    for b in beats:
        path = os.path.join(kd, FRAME_NAME % int(b)) if str(b).isdigit() else \
            os.path.join(kd, "scene_%s.png" % b)
        if os.path.exists(path):
            std, reason = _frame_std(path)
            frames.append((b, path, True, std, reason))
        else:
            frames.append((b, path, False, None, None))
    on_disk = sorted(p for p in os.listdir(kd) if p.startswith("scene_") and p.endswith(".png")) \
        if os.path.isdir(kd) else []
    claimed = {os.path.basename(f[1]) for f in frames}
    extra = [p for p in on_disk if p not in claimed]
    return evaluate(frames, universe=universe, extra=extra, notes=notes)


def main():
    ap = argparse.ArgumentParser(description="Deterministic keyframe QA for the remotion tier")
    ap.add_argument("out_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = check(a.out_dir)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print("[keyframe_qa_remotion] %s  measured %d of %d beat(s) (%s) · %d not measured · %d blank"
              % ("OK" if r["ok"] else "FAIL", r["measured"], r["scenes"], r["universe"],
                 len(r["not_measured"]), len(r["blank"])))
        for b in r["blank"]:
            print("  BLANK scene %s (stddev %.1f < %.1f) — the beat rendered a near-empty frame; check its shot/props"
                  % (b["scene"], b["std"], BLANK_STD))
        for m in r["not_measured"]:
            print("  NOT MEASURED scene %s: %s" % (m["scene"], m["reason"]))
        for p in r["extra"]:
            print("  stale: %s is in _keyframes/ but no beat claims it — left by an earlier, longer cut" % p)
        for n in r["notes"]:
            print("  note: %s" % n)
        if r["scenes"] == 0:
            print("  (nothing to measure — run render_remotion.py first)")
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
