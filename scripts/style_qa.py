#!/usr/bin/env python3
"""style_qa — did the film's DRAWING change the way its style says, on every beat? Measured from the pixels.

    python3 scripts/style_qa.py <out_dir> [--json]

WHY. The failure the user named is a film that "only changed colour; the drawing and the lines are as they were"
(只换了配色，画法和线条还是原来的样子). A recolour moves hue and keeps every edge where it was, every gradient
smooth, every surface clean. A drawing style moves the edges (outlines, weights, shadows, corners), flattens or steps
the fills, puts a tooth on the surface. So every beat is rendered at its settled frame twice — with the film's
`meta.style` and without it — and three things are measured, styled against unstyled:

    edges    1 - IoU of the luminance-edge maps: how much of the drawing's line structure moved
    fills    the drop in the share of gently-ramping (gradient) pixels away from edges: fills flattened or stepped
    tooth    the gain in high-frequency energy away from edges: a medium's surface

THE VERDICTS (exit 2 on any ERROR):
  * an axis the spec sets away from `as-drawn` whose measure changed on NO beat the style can reach is an ERROR —
    what is on screen for that axis is a recolour, not a style. An axis left as drawn is not checked;
  * a beat on which NONE of the spec's measures changed while other beats changed is an ERROR — that beat is
    unstyled, and the film's drawing is inconsistent;
  * beats whose picture the style cannot reach (a photograph, a canvas: scripts/style_coverage.py) are listed and
    left out of both.

It writes `<out_dir>/_style/sheet.png` — each beat unstyled beside styled — because a gate pass is never the verdict
on its own: someone looks. The tolerances below are where synthetic recolours and real restyles separate; each is
stated with what it was measured on.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TAG = "[style_qa]"
EDGE_T = 18.0          # an edge: the largest per-channel step of the 3x3-blurred picture (0-255) — colour, not luminance:
                       # a recolour moves luminance contrast across a luminance threshold (60° of hue moved a luminance
                       # edge map 0.38) while every colour boundary stays where it was (0.002 measured that way)
RAMP_LO, RAMP_HI = 0.15, 6.0   # a GRADIENT pixel: the 15x15-blurred luminance changing this much per px over a 4 px
                       # stride — blurred that hard, a medium's per-pixel grain no longer reads as a ramp
# what counts as CHANGED, styled vs unstyled at the same frame. Measured: a pure hue rotation (60°, 120°) on the
# synthetic scene moves edges 0.002, fills ±0.002, tooth −0.02; a 4 px outline + flat fill moves edges 0.56 and fills
# 0.13; on the cartoon-like corpus (spike3) every restyled register moved edges 0.34–0.75, and a paper surface adds
# tooth 2.7–3.0 (tests/test_style_qa.py; references/style-engine-spike.md).
TONE_MAX = 6.0         # levels (0-255) a medium may move the picture's mean luminance: grain, not a veil. A dark film's
                       # first tooth lifted every dark ground ~70 levels to mid-grey and this gate passed it (looked at)
EDGE_MOVED = 0.05
FILLS_MOVED = 0.01
TOOTH_MOVED = 0.5

# which measure answers for which axis group; `type` (glyphs never change) and `motion` (a clip, not a still) are
# judged elsewhere
AXIS_MEASURE = {"line": "edges", "shadow": "edges", "form": "edges", "fill": "fills", "shade": "fills",
                "surface": "tooth"}
MEASURE_WORDS = {"edges": "line structure", "fills": "fills", "tooth": "surface"}


def _rgb(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(float)


def _box(a, k):
    """A k×k box blur (edge-padded), any number of channels."""
    a3 = a if a.ndim == 3 else a[..., None]
    p = k // 2
    c = np.pad(a3, ((p, p), (p, p), (0, 0)), mode="edge").cumsum(0).cumsum(1)
    c = np.pad(c, ((1, 0), (1, 0), (0, 0)))
    out = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / float(k * k)
    return out if a.ndim == 3 else out[..., 0]


def _grow(m, n=1):
    for _ in range(n):
        g = m.copy()
        g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
        m = g
    return m


def _stats(a):
    b = _box(a, 3)
    g = np.zeros(a.shape[:2])
    g[:, :-1] = np.abs(b[:, 1:] - b[:, :-1]).max(axis=2)
    g[:-1, :] = np.maximum(g[:-1, :], np.abs(b[1:, :] - b[:-1, :]).max(axis=2))
    edges = g > EDGE_T
    away = ~_grow(edges, 3)                 # an edge's neighbourhood is neither a fill nor a surface
    L = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    L15 = _box(L, 15)
    s = 4
    r = np.zeros_like(L15)
    r[:, :-s] = np.abs(L15[:, s:] - L15[:, :-s]) / s
    r[:-s, :] = np.maximum(r[:-s, :], np.abs(L15[s:, :] - L15[:-s, :]) / s)
    n = max(1, int(away.sum()))
    ramp = float(((r > RAMP_LO) & (r <= RAMP_HI) & away).sum()) / n
    tooth = float(np.abs(L[:, 1:] - L[:, :-1])[away[:, 1:]].mean()) if away[:, 1:].any() else 0.0
    return edges, ramp, tooth


def measure(styled_png, unstyled_png, structure_png=None):
    """{"edges", "fills", "tooth"} — how much each moved, styled against unstyled (see the header). `structure_png` is
    the beat styled WITHOUT its surface: a medium's grain is read as edges and ramps by any measure fine enough to see
    a line, so lines and fills are measured on the drawing without its medium, and the medium on the drawing with it."""
    sa = _rgb(structure_png or styled_png)
    es, rs, _ = _stats(sa)
    st = _rgb(styled_png)
    _, _, ts = _stats(st)
    eu, ru, tu = _stats(_rgb(unstyled_png))
    union = float((es | eu).sum())
    iou = float((es & eu).sum()) / union if union else 1.0
    lum = lambda a: 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    tone = float((lum(st) - lum(sa)).mean()) if structure_png else 0.0     # what the medium alone did to the tone
    return {"edges": round(1.0 - iou, 4), "fills": round(ru - rs, 4), "tooth": round(ts - tu, 4), "tone": round(tone, 2)}


_MOVED = {"edges": EDGE_MOVED, "fills": FILLS_MOVED, "tooth": TOOTH_MOVED}


def _moved(m, measure_name):
    return m.get(measure_name, 0.0) >= _MOVED[measure_name]


def judge(spec, beats):
    """[(level, message)] for `beats` = [{"beat", "shot", "exempt", "m": measure()}] under `spec`."""
    import style_spec as ss
    out = []
    groups = sorted({a.split(".")[0] for a in ss.structural_axes(spec)} & set(AXIS_MEASURE))
    measures = sorted({AXIS_MEASURE[g] for g in groups})
    live = [b for b in beats if not b.get("exempt")]
    for b in beats:
        if b.get("exempt"):
            out.append(("NOTE", "beat %s (%s) is outside the style's reach and outside these checks"
                        % (b["beat"], b["shot"])))
    if not measures or not live:
        return out
    for g in groups:
        meas = AXIS_MEASURE[g]
        if not any(_moved(b["m"], meas) for b in live):
            axes = [a for a in ss.structural_axes(spec) if a.startswith(g + ".")]
            out.append(("ERROR", "style.%s is set (%s) and no beat's %s changed — on screen that is a recolour, not "
                        "this style's %s" % (g, ", ".join(axes), MEASURE_WORDS[meas], g)))
    if "surface" in groups:
        for b in live:
            t = b["m"].get("tone", 0.0)
            if abs(t) > TONE_MAX:
                out.append(("ERROR", "beat %s (%s): the surface %s the whole picture by %.0f levels — a medium is grain on "
                            "the drawing, not a change of its tone (the palette, the caption's contrast)"
                            % (b["beat"], b["shot"], "lifts" if t > 0 else "darkens", abs(t))))
    styled = [b for b in live if any(_moved(b["m"], m) for m in measures)]
    if styled:
        for b in live:
            if b not in styled:
                out.append(("ERROR", "beat %s (%s) is unstyled: none of the style's %s changed on it while %d other "
                            "beat(s) did — the film's drawing is inconsistent (%s)"
                            % (b["beat"], b["shot"], "/".join(MEASURE_WORDS[m] for m in measures), len(styled),
                               ", ".join("%s %.3f" % (m, b["m"].get(m, 0)) for m in measures))))
    return out


def _sheet(rows, out_png):
    """Each beat: unstyled | styled, labelled."""
    tw = 480
    ims = []
    for r in rows:
        a, b = Image.open(r["un"]).convert("RGB"), Image.open(r["st"]).convert("RGB")
        th = int(a.height * tw / a.width)
        a, b = a.resize((tw, th)), b.resize((tw, th))
        row = Image.new("RGB", (tw * 2 + 30, th + 34), "white")
        row.paste(a, (0, 34))
        row.paste(b, (tw + 30, 34))
        ImageDraw.Draw(row).text((4, 6), "beat %s %s%s  edges %.3f  fills %.3f  tooth %.2f" % (
            r["beat"], r["shot"], "  (outside the style's reach)" if r["exempt"] else "",
            r["m"]["edges"], r["m"]["fills"], r["m"]["tooth"]), fill=(20, 20, 20))
        ims.append(row)
    if not ims:
        return None
    sheet = Image.new("RGB", (ims[0].width, sum(i.height for i in ims) + 10 * len(ims)), (235, 235, 235))
    y = 0
    for i in ims:
        sheet.paste(i, (0, y))
        y += i.height + 10
    sheet.save(out_png)
    return out_png


def check(out_dir, settled=0.9):
    """{"measured", "why", "findings", "beats", "sheet"} for the film in `out_dir`."""
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = board.get("meta") or {}
    spec = meta.get("style")
    if not isinstance(spec, dict):
        return {"measured": False, "why": "no meta.style — the film draws as its registers do", "findings": [],
                "beats": [], "sheet": None}
    import fidelity as fid
    import render_remotion as rr
    import style_coverage as sc
    exempt = sc.exempt_registers()
    dna = meta.get("design_dna") or meta.get("shot_template")
    aspect = meta.get("aspect") or "16:9"
    work = os.path.join(out_dir, "_style")
    os.makedirs(work, exist_ok=True)
    jobs, rows = [], []
    surfaced = ((spec.get("surface") or {}).get("kind") or "none") != "none"
    bare = dict(spec, surface={"kind": "none"})          # the drawing without its medium (see measure())
    for i, s in enumerate(board.get("slides") or []):
        shot = s.get("shot")
        if not shot:
            continue
        n = s.get("index", i + 1)
        frames = max(2, int(round(float(s.get("duration") or 5.0) * 30)))
        props = dict(rr.film_shot_props(s, out_dir), aspect=aspect, holdFrames=frames)
        if dna:
            props["dna"] = dna
        f = int(round((frames - 1) * settled))
        un, st = os.path.join(work, "%02d.un.png" % n), os.path.join(work, "%02d.st.png" % n)
        jobs += [{"tag": "%d:un" % n, "id": shot, "props": props, "frame": f, "png": un},
                 {"tag": "%d:st" % n, "id": shot, "props": dict(props, style=spec), "frame": f, "png": st}]
        ns = None
        if surfaced:
            ns = os.path.join(work, "%02d.ns.png" % n)
            jobs.append({"tag": "%d:ns" % n, "id": shot, "props": dict(props, style=bare), "frame": f, "png": ns})
        rows.append({"beat": n, "shot": shot, "exempt": shot in exempt, "un": un, "st": st, "ns": ns})
    if not rows:
        return {"measured": False, "why": "no beat names a shot", "findings": [], "beats": [], "sheet": None}
    fid._render_all(out_dir, jobs, parts=False)
    for r in rows:
        r["m"] = measure(r["st"], r["un"], r["ns"])
    findings = judge(spec, rows)
    sheet = _sheet(rows, os.path.join(work, "sheet.png"))
    return {"measured": True, "why": "", "findings": findings, "sheet": sheet,
            "beats": [{k: r[k] for k in ("beat", "shot", "exempt", "m")} for r in rows]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rep = check(os.path.abspath(args.out_dir))
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    elif not rep["measured"]:
        print("%s NOTHING TO JUDGE: %s" % (TAG, rep["why"]))
    else:
        for b in rep["beats"]:
            print("%s beat %s (%s)%s edges %.3f fills %.3f tooth %.2f" % (
                TAG, b["beat"], b["shot"], " [outside the style's reach]" if b["exempt"] else "",
                b["m"]["edges"], b["m"]["fills"], b["m"]["tooth"]))
        for lv, m in rep["findings"]:
            print("%s %s %s" % (TAG, lv, m))
        print("%s sheet: %s — look at it; a pass here is not the verdict" % (TAG, rep["sheet"]))
    return 2 if any(lv == "ERROR" for lv, _m in rep["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
