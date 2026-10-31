#!/usr/bin/env python3
"""Measure the style engine's per-frame DOM pass on the development corpus (tests/fixtures/style/corpus.json).

The question it answers (docs/superpowers/specs/2026-10-31-style-engine-design.md, "Settled" 1): can a pass that
restyles what registers drew, after React drew it, be deterministic and leave type where it was? Per entry:

  * determinism — the styled frame rendered twice as a cold still, and once inside a sequence rendered across
    several tabs (frames out of order), must be the same pixels;
  * type — every line of type the census sees must sit where it sat unstyled (max px moved);
  * the change — pixels styled vs unstyled, and the pass's own report (shapes seen / properties changed).

    python3 scripts/style_spike.py <work_dir> [--only=Shot,Shot]

Writes <work_dir>/report.json and, per entry, unstyled/styled PNGs side by side in <work_dir>/sheets/.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REMOTION = os.path.join(ROOT, "remotion")
FIX = os.path.join(ROOT, "tests", "fixtures", "style")
sys.path.insert(0, HERE)

TOL = 2            # a channel difference this small is encoder/raster noise, not a different picture


def _run(cmd):
    r = subprocess.run(cmd, cwd=REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("%s failed: %s" % (cmd[2], (r.stdout + r.stderr)[-800:]))
    return r


def _props_file(work, name, props):
    p = os.path.join(work, "props", name + ".json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(props, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return p


def still(bundle, work, comp, props, frame, name):
    out = os.path.join(work, "png", name + ".png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    _run(["npx", "remotion", "still", bundle, comp, out, "--frame=%d" % frame, "--image-format=png", "--gl=angle",
          "--log=error", "--props=" + _props_file(work, name, props)])
    return out


def sequence_frame(bundle, work, comp, props, frame, name, span=4, conc=4):
    out = os.path.join(work, "seq", name)
    os.makedirs(out, exist_ok=True)
    a = max(0, frame - span + 1)
    _run(["npx", "remotion", "render", bundle, comp, out, "--sequence", "--image-format=png",
          "--frames=%d-%d" % (a, frame), "--concurrency=%d" % conc, "--gl=angle", "--log=error",
          "--props=" + _props_file(work, name + "_seq", props)])
    files = sorted(f for f in os.listdir(out) if f.endswith(".png"))
    return os.path.join(out, files[-1])


def diff(pa, pb):
    a = np.asarray(Image.open(pa).convert("RGB")).astype(np.int16)
    b = np.asarray(Image.open(pb).convert("RGB")).astype(np.int16)
    d = np.abs(a - b).max(axis=2)
    return {"max": int(d.max()), "frac": round(float((d > TOL).mean()), 5)}


def census(bundle, jobs):
    import text_safe_qa as tsq
    return tsq.glide_run(jobs, bundle, concurrency=4)


def _lines(rec):
    """Lines keyed by their TEXT and its occurrence — the census key is a DOM path, and the style layer is one more
    element on every path, so paths never match across the two renders."""
    out, seen = {}, {}
    for ln in rec.get("lines") or []:
        t = ln.get("t", "")
        seen[t] = seen.get(t, 0) + 1
        out["%s#%d" % (t, seen[t])] = ln
    return out


def type_moved(un, st):
    """Max px any line moved (x, y, w, h), and lines present in one census and not the other."""
    a, b = _lines(un), _lines(st)
    worst = 0.0
    for k in set(a) & set(b):
        for f in ("x", "y", "w", "h"):
            if f in a[k] and f in b[k]:
                worst = max(worst, abs(float(a[k][f]) - float(b[k][f])))
    return round(worst, 3), sorted(set(a) ^ set(b))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--only", default="")
    ap.add_argument("--spec", default=os.path.join(FIX, "spike_spec.json"), help="the style spec to measure")
    args = ap.parse_args(argv)
    corpus = json.load(open(os.path.join(FIX, "corpus.json"), encoding="utf-8"))
    spec = json.load(open(args.spec, encoding="utf-8"))
    only = {s for s in args.only.split(",") if s}
    entries = [e for e in corpus["entries"] if not only or e["shot"] in only]
    work = os.path.abspath(args.work)
    os.makedirs(work, exist_ok=True)
    bundle = os.path.join(work, "bundle")
    if not os.path.isfile(os.path.join(bundle, "index.html")):
        _run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + bundle, "--log=error",
              "--public-dir=" + os.path.normpath(os.path.join(FIX, corpus["public"]))])
    jobs = []
    for e in entries:
        for tag, props in (("un", e["props"]), ("st", dict(e["props"], style=spec))):
            jobs.append({"tag": "%s:%s" % (e["shot"], tag), "id": e["shot"], "props": dict(props, typeGlide=True),
                         "from": e["frame"], "to": e["frame"]})
    cen = census(bundle, jobs)
    report = []
    os.makedirs(os.path.join(work, "sheets"), exist_ok=True)
    for e in entries:
        s, f = e["shot"], e["frame"]
        row = {"shot": s, "frame": f}
        try:
            un = still(bundle, work, s, e["props"], f, s + "_un")
            sp = dict(e["props"], style=spec)
            st1 = still(bundle, work, s, sp, f, s + "_st1")
            st2 = still(bundle, work, s, sp, f, s + "_st2")
            seq = sequence_frame(bundle, work, s, sp, f, s + "_st")
            row["twice"] = diff(st1, st2)
            row["out_of_order"] = diff(st1, seq)
            row["changed"] = diff(un, st1)
            cu, cs = cen.get(s + ":un", {}), cen.get(s + ":st", {})
            fu, fs = (cu.get("frames") or {}).get(f), (cs.get("frames") or {}).get(f)
            if fu is None or fs is None:
                row["type"] = {"measured": False, "why": cu.get("error") or cs.get("error") or "no census frame"}
            else:
                moved, odd = type_moved(fu, fs)
                row["type"] = {"measured": True, "lines": len(fu.get("lines") or []), "max_px": moved, "only_one": odd}
            a, b = Image.open(un).convert("RGB"), Image.open(st1).convert("RGB")
            sheet = Image.new("RGB", (a.width * 2 + 20, a.height), "white")
            sheet.paste(a, (0, 0))
            sheet.paste(b, (a.width + 20, 0))
            sheet.thumbnail((1600, 1600))
            sheet.save(os.path.join(work, "sheets", s + ".png"))
        except Exception as ex:          # one register's failure is a row of the report, not the end of it
            row["error"] = str(ex)[:400]
        det = row.get("twice", {}).get("frac", 1) == 0 and row.get("out_of_order", {}).get("frac", 1) == 0
        row["deterministic"] = det
        report.append(row)
        print(json.dumps(row, ensure_ascii=False))
    json.dump(report, open(os.path.join(work, "report.json"), "w"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
