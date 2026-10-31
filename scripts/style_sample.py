#!/usr/bin/env python3
"""The style sample — 2–3 beats of the film in its style, beside the references, for the USER to approve.

    python3 scripts/style_sample.py <out_dir> [--to <folder>]     # build the sheet + a 2 s clip, deliver to the Desktop
    python3 scripts/style_sample.py <out_dir> --signoff            # record the user's yes — ONLY after they said it

WHY. A style decomposed wrong (the wrong line, a fill that should have stepped, a medium that reads as dirt) costs one
sample, not a film — the user decided that every styled film shows its sample before the full render (2026-10-31).
`render_remotion.py` refuses the full render of a styled film until `meta.style_signoff` holds the spec the user
approved; a spec changed afterwards makes the sign-off stale.

THE SHEET. Title: the style's name (and, when the spec was written with no references, that it was — in the title,
where it cannot be missed). Left: the references. Right: the picked beats at their settled frame. Under them: every
shortfall the spec records, every beat the style cannot reach and why, and — when the spec leaves every drawing axis
as drawn — that only the palette changes. The clip is the first picked beat played in the film (stepping and a
boiling line only show in motion).

`--signoff` is run by the agent when, and only when, the user has said yes to THIS sheet in chat. It is not a gate to
pass: it is the record of a human decision.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TAG = "[style_sample]"
TYPE_FAMILIES = {"C", "P"}
DATA_FAMILIES = {"D", "S", "H", "T", "K"}


def spec_hash(spec):
    import style_spec as ssp
    return ssp.spec_sha256(spec)


def _has_object(props):
    if isinstance(props, dict):
        if isinstance(props.get("id"), str) and set(props) <= {"id", "props"}:
            return True
        return any(_has_object(v) for v in props.values())
    if isinstance(props, list):
        return any(_has_object(v) for v in props)
    return False


def pick_beats(board):
    """2–3 beat indices the style can reach: an object beat, a data/diagram beat, a type-led beat — then whatever
    else there is, in film order."""
    import shot_director as sd
    import style_coverage as sc
    ex = sc.exempt_registers()
    live = [(s.get("index", i + 1), s) for i, s in enumerate(board.get("slides") or [])
            if s.get("shot") and s.get("shot") not in ex]
    picked = []
    for want in (lambda s: _has_object(s.get("shot_props")) or sd.FAMILY.get(s["shot"]) == "E",
                 lambda s: sd.FAMILY.get(s["shot"]) in DATA_FAMILIES,
                 lambda s: sd.FAMILY.get(s["shot"]) in TYPE_FAMILIES):
        for n, s in live:
            if n not in picked and want(s):
                picked.append(n)
                break
    for n, _s in live:
        if len(picked) >= min(3, len(live)):
            break
        if n not in picked:
            picked.append(n)
    return sorted(picked[:3])


def sheet_notes(spec, board):
    """{"title", "lines"} — what the sheet says in words."""
    import style_coverage as sc
    import style_spec as ssp
    title = "风格样张 · %s" % spec.get("name", "?")
    if not spec.get("refs"):
        title += "  —  NO REFERENCES (%s): please send one if you have it" % (spec.get("refs_missing") or "none given")
    lines = []
    for s in spec.get("shortfalls") or []:
        lines.append("shortfall · %s: wanted %s, got %s — %s" % (s.get("axis"), s.get("wanted"), s.get("got"), s.get("why")))
    cov = sc.film_coverage(board)
    for r in cov["exempt"]:
        lines.append("outside the style · beat %s (%s): %s" % (r["beat"], r["shot"], r["why"]))
    lines += ["note · " + w for w in cov["warnings"]]
    if ssp.is_recolour_only(spec):
        lines.append("note · this spec draws like the default: only the palette changes")
    if not lines:
        lines.append("no shortfalls; every beat is in the style's reach")
    return {"title": title, "lines": lines}


def _compose(out_png, notes, refs, stills):
    from PIL import Image, ImageDraw
    import fidelity as fid
    W = 2000
    ref_w, st_w = 460, 1440
    ref_ims = [Image.open(p).convert("RGB") for p in refs if os.path.isfile(p)][:4]
    st_ims = [(n, Image.open(p).convert("RGB")) for n, p in stills]
    def fit(im, w):
        return im.resize((w, max(1, int(im.height * w / im.width))))
    ref_ims = [fit(i, ref_w) for i in ref_ims]
    st_ims = [(n, fit(i, st_w)) for n, i in st_ims]
    body_h = max(sum(i.height + 16 for i in ref_ims), sum(i.height + 44 for _n, i in st_ims))
    line_h = 34
    H = 90 + body_h + 30 + line_h * len(notes["lines"]) + 30
    sheet = Image.new("RGB", (W, H), (246, 244, 239))
    d = ImageDraw.Draw(sheet)
    d.text((30, 26), notes["title"], fill=(20, 20, 20), font=fid._font(34, notes["title"]))
    y = 90
    d.text((30, y - 4), "references" if ref_ims else "references: none", fill=(90, 90, 90), font=fid._font(20))
    yy = y + 24
    for im in ref_ims:
        sheet.paste(im, (30, yy))
        yy += im.height + 16
    yy = y
    for n, im in st_ims:
        d.text((530, yy), "beat %s" % n, fill=(90, 90, 90), font=fid._font(20))
        sheet.paste(im, (530, yy + 26))
        yy += im.height + 44
    y = 90 + body_h + 30
    for ln in notes["lines"]:
        d.text((30, y), ln, fill=(40, 40, 40), font=fid._font(24, ln))
        y += line_h
    sheet.save(out_png)
    return out_png


def _clip(out_dir, board, beat, out_mp4, seconds=2.0):
    import _common as _c
    import remotion_segments as _rs
    import render_remotion as rr
    import workshop as ws
    props, _slides = rr.film_props(out_dir, board)
    segs, _total = _rs.timeline(props["scenes"], _rs.seam_frames())
    k = [s.get("index", i + 1) for i, s in enumerate(board["slides"])].index(beat)
    a, b = segs[k]
    start = a + int((b - a) * 0.3)
    end = min(b, start + int(seconds * 30) - 1)
    pf = os.path.join(out_dir, "_style", "clip.props.json")
    json.dump(props, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
    cmd = ["npx", "remotion", "render", "src/index.ts", "Film", out_mp4, "--frames=%d-%d" % (start, end), "--gl=angle",
           "--log=error", "--props=" + pf, "--public-dir=" + os.path.abspath(out_dir)]
    r = _c.run_render(subprocess.run, cmd, capture_output=True, text=True, cwd=ws.REMOTION,
                      **ws.env_kwargs(ws.prepare(out_dir)))
    if r.returncode != 0 or not os.path.isfile(out_mp4):
        raise SystemExit("%s the sample clip failed: %s" % (TAG, ((r.stdout or "") + (r.stderr or ""))[-600:]))
    return out_mp4


def build(out_dir, to=None):
    """Render the picked beats + a clip, compose the sheet, deliver both. {"png", "mp4", "sample_sha256", "beats"}."""
    import deliver
    import fidelity as fid
    import render_remotion as rr
    out_dir = os.path.abspath(out_dir)
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = board.get("meta") or {}
    spec = meta.get("style")
    if not isinstance(spec, dict):
        raise SystemExit("%s no meta.style — there is no style to sample" % TAG)
    beats = pick_beats(board)
    if not beats:
        raise SystemExit("%s no beat of this film is in the style's reach — there is nothing to sample" % TAG)
    work = os.path.join(out_dir, "_style")
    os.makedirs(work, exist_ok=True)
    dna = meta.get("design_dna") or meta.get("shot_template")
    jobs, stills = [], []
    by_n = {s.get("index", i + 1): s for i, s in enumerate(board["slides"])}
    for n in beats:
        s = by_n[n]
        frames = max(2, int(round(float(s.get("duration") or 5.0) * 30)))
        props = dict(rr.film_shot_props(s, out_dir), aspect=meta.get("aspect") or "16:9", holdFrames=frames, style=spec)
        if dna:
            props["dna"] = dna
        png = os.path.join(work, "sample.%02d.png" % n)
        jobs.append({"tag": str(n), "id": s["shot"], "props": props, "frame": int(round((frames - 1) * 0.9)), "png": png})
        stills.append((n, png))
    fid._render_all(out_dir, jobs, parts=False)
    refs = [os.path.join(out_dir, r["src"]) for r in spec.get("refs") or []
            if isinstance(r, dict) and isinstance(r.get("src"), str) and not re.match(r"https?://", r["src"])]
    notes = sheet_notes(spec, board)
    local_png = _compose(os.path.join(work, "sample.png"), notes, refs, stills)
    local_mp4 = _clip(out_dir, board, beats[0], os.path.join(work, "sample.mp4"))
    folder = deliver.destination(to)
    name = deliver.film_name(out_dir)
    png = os.path.join(folder, "%s 风格样张.png" % name)
    mp4 = os.path.join(folder, "%s 风格样张.mp4" % name)
    import shutil
    shutil.copyfile(local_png, png)
    shutil.copyfile(local_mp4, mp4)
    sha = hashlib.sha256(open(local_png, "rb").read()).hexdigest()
    json.dump({"sample_sha256": sha, "spec_sha256": spec_hash(spec), "beats": beats, "png": png, "mp4": mp4},
              open(os.path.join(work, "sample.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {"png": png, "mp4": mp4, "sample_sha256": sha, "beats": beats}


def record_signoff(out_dir):
    """Write meta.style_signoff for the sample last built — run ONLY after the user approved it in chat."""
    path = os.path.join(out_dir, "storyboard.json")
    board = json.load(open(path, encoding="utf-8"))
    spec = (board.get("meta") or {}).get("style")
    sample = os.path.join(out_dir, "_style", "sample.json")
    if not isinstance(spec, dict) or not os.path.isfile(sample):
        raise SystemExit("%s no sample to sign off — build it (style_sample.py <out_dir>) and show it to the user first" % TAG)
    kept = json.load(open(sample, encoding="utf-8"))
    if kept.get("spec_sha256") != spec_hash(spec):
        raise SystemExit("%s the spec changed after the sample was built — build a new sample and show it" % TAG)
    board["meta"]["style_signoff"] = {"spec_sha256": kept["spec_sha256"], "sample_sha256": kept["sample_sha256"],
                                      "user_ok": True}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False, indent=2)
    return board["meta"]["style_signoff"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--to", default=None, help="the folder to deliver to (default: the Desktop)")
    ap.add_argument("--signoff", action="store_true", help="record the user's approval of the last sample")
    a = ap.parse_args(argv)
    if a.signoff:
        so = record_signoff(a.out_dir)
        print("%s signed off: spec %s… sample %s…" % (TAG, so["spec_sha256"][:10], so["sample_sha256"][:10]))
        return 0
    rep = build(a.out_dir, a.to)
    print("%s beats %s\n%s sheet: %s\n%s clip:  %s\n%s show both to the user; on their yes run --signoff"
          % (TAG, rep["beats"], TAG, rep["png"], TAG, rep["mp4"], TAG))
    return 0


if __name__ == "__main__":
    sys.exit(main())
