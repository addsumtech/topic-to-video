#!/usr/bin/env python3
"""picture_legibility_qa — does every picture the film shows actually show something? Read off the rendered frame.

    python3 scripts/picture_legibility_qa.py <film_dir> [--page film.html] [--every 0.5] [--frames A-B] [--json]

Steps the film page (window.seek) and, at each step, finds the PICTURES on screen: the page's own <img>, <canvas> and
<video> elements (fully shown, at least 160 x 90 px, smaller than most of the frame: the full-frame stage is the scene,
not a picture in it) and every panel or card a stage3d stage shows (`st.pictures()`: its front face projected onto the
page). Each one is cropped off a screenshot of that frame, inset from its edges (a frame or a border is not the
picture), and measured on its blurred luma: a picture whose spread is tiny (standard deviation under STD and 1st-99th
percentile range under SPREAD levels) shows almost nothing, a near-black or near-white block. Reported when that
lasts at least MIN_S. A frame that is itself one flat field above the caption band (a dip to black, a fade) is
skipped: no picture is being shown, and empty_frame_qa judges the hold.

WHY. The MRI film's closing recap (2026-11-19) showed three callback pictures; the third, a switched-off lightbox,
measured std 0.8 and a range of 2 grey levels: a black rectangle under an icon, unreadable, and every check passed it
(they judge text and geometry, not whether a picture can be seen). The real pictures beside it measured std 27-44.
EXEMPT: a picture meant to be empty: `data-blank-ok` on the element or an ancestor; `userData.blankOk` on a stage3d
panel. A picture still fading in (strength under 0.9) is not judged yet.
Exit 0 clean, 1 an unreadable picture, 2 usage error, the page failed to load, or no plan.
"""
import json
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402
import _filmpage as _fp  # noqa: E402

STD = 4.0          # blurred-luma standard deviation; the dark MRI panel 0.8, real pictures 27-44
SPREAD = 16.0      # 1st-99th percentile range in grey levels; the dark panel 2, real pictures 97-179
MIN_S = 1.0        # two samples: a picture passing through a dip or a cut for a moment is not 'shown'
INSET = 0.08       # of each side: a picture's frame, border or rounded corner is not the picture
_USAGE = "usage: picture_legibility_qa.py <film_dir> [--page film.html] [--every 0.5] [--frames A-B] [--json]"

_PROBE = r"""
(() => {
  const W = innerWidth, H = innerHeight, out = [];
  const strength = (el) => { let op = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return 0; op *= parseFloat(cs.opacity); }
    return op; };
  // a name a builder can find: its own name, id or file, else its tag under the nearest ancestor with an id or class
  const name = (el) => { const own = el.getAttribute('data-name') || el.id || (el.currentSrc || el.src || '').split('/').pop();
    if (own) return own; const a = el.parentElement && el.parentElement.closest('[id], [class]');
    // its place among its own kind under that parent: stable while it moves (a position in the name split one
    // picture's run into many as it grew)
    const nth = el.parentElement ? Array.from(el.parentElement.children).filter((c) => c.tagName === el.tagName).indexOf(el) + 1 : 1;
    return (a ? (a.id ? '#' + a.id : '.' + String(a.className).trim().split(/\s+/)[0]) + ' > ' : '') + el.tagName.toLowerCase() + ' ' + nth; };
  const stageCanvases = new Set(((window.Stage3D && Stage3D.stages) || []).map((st) => st.renderer.domElement));
  for (const el of document.body.querySelectorAll('img, canvas, video')) {
    if (stageCanvases.has(el) || el.closest('[data-blank-ok]') || strength(el) < 0.9) continue;
    const r = el.getBoundingClientRect();
    const b = [Math.max(0, r.left), Math.max(0, r.top), Math.min(W, r.right), Math.min(H, r.bottom)];
    const w = b[2] - b[0], h = b[3] - b[1];
    if (w < 160 || h < 90 || w * h > 0.6 * W * H) continue;
    out.push({name: name(el), box: b});
  }
  for (const st of (window.Stage3D && Stage3D.stages) || []) {
    const cv = st.renderer.domElement; if (strength(cv) < 0.9 || typeof st.pictures !== 'function') continue;
    for (const p of st.pictures()) {
      const xs = p.quad.map((q) => q[0]), ys = p.quad.map((q) => q[1]);
      // the face's own inner box (a tilted face's bounding box would take in the ground beside it): the middle
      // of the quad's sides
      const b = [Math.max(0, (xs[0] + xs[3]) / 2), Math.max(0, (ys[0] + ys[1]) / 2), Math.min(W, (xs[1] + xs[2]) / 2), Math.min(H, (ys[2] + ys[3]) / 2)];
      const w = b[2] - b[0], h = b[3] - b[1];
      if (w < 160 || h < 90 || w * h > 0.6 * W * H) continue;
      out.push({name: 'stage panel ' + p.name, box: b});
    }
  }
  return out;
})()
"""


def measure(img, box, inset=INSET):
    """(std, spread) of the blurred luma inside box (page px), inset from its sides."""
    from PIL import ImageFilter
    x0, y0, x1, y1 = box
    dx, dy = (x1 - x0) * inset, (y1 - y0) * inset
    crop = img.crop((int(x0 + dx), int(y0 + dy), int(x1 - dx), int(y1 - dy))).convert("L").filter(ImageFilter.GaussianBlur(2))
    a = np.asarray(crop, float)
    return float(a.std()), float(np.percentile(a, 99) - np.percentile(a, 1))


def unreadable(std, spread):
    return std < STD and spread < SPREAD


def spans(hits, every, min_s=MIN_S):
    """hits: [(t, name, std, spread)] -> [(name, start, end, worst std, worst spread)] lasting min_s or more."""
    by, out = {}, []
    for t, n, sd, sp in sorted(hits):
        by.setdefault(n, []).append((t, sd, sp))
    for n, xs in by.items():
        run = [xs[0]]
        for x in xs[1:] + [None]:
            if x is not None and x[0] - run[-1][0] <= every * 1.5:
                run.append(x)
                continue
            if run[-1][0] - run[0][0] + every >= min_s - 1e-6:
                out.append((n, run[0][0], run[-1][0] + every, min(r[1] for r in run), min(r[2] for r in run)))
            if x is not None:
                run = [x]
    return sorted(out, key=lambda x: x[1])


def main(argv):
    _c.refuse_unknown(argv, valued=("page", "every", "frames"), switches=("json",), usage=_USAGE)
    span = _c.frame_span(argv)
    vals = {k: _c.argflag(argv, k, None) for k in ("page", "every", "frames")}
    args = [a for a in argv if not a.startswith("--") and a not in vals.values()]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    page = vals["page"] or "film.html"
    if not os.path.isfile(os.path.join(d, page)):
        print("picture_legibility_qa: no page at %s" % os.path.join(d, page), file=sys.stderr)
        return 2
    every = float(vals["every"] or 0.5)
    n = _fp.film_frames_count(d, 30)
    if not n:
        print("picture_legibility_qa: no _plan.json \"frames\" or timeline.json \"duration\"", file=sys.stderr)
        return 2
    t0, t_end = (span[0] / 30.0, min(n, span[1]) / 30.0) if span else (0.0, n / 30.0)
    from PIL import Image
    port, srv = _fp.serve(d)
    hits, judged = [], 0
    tmp = tempfile.mkdtemp(prefix="legibility_")
    try:
        p = _fp.FilmPage(port, page)
        try:
            k = 0
            while t0 + k * every < t_end:
                t = round(t0 + k * every, 4)
                k += 1
                p.seek(t)
                pics = p.ev(_PROBE) or []
                if not pics:
                    continue
                shot = os.path.join(tmp, "f.png")
                p.shot(shot, "png")
                img = Image.open(shot)
                sx = img.width / float(p.ev("innerWidth"))
                # the whole picture above the caption band is one flat field: a dip to black or a fade, which
                # empty_frame_qa judges as a hold; no picture in it is being shown
                if unreadable(*measure(img, [0, 0, img.width, img.height * 0.8], 0)):
                    continue
                for q in pics:
                    judged += 1
                    sd, sp = measure(img, [v * sx for v in q["box"]])
                    if unreadable(sd, sp):
                        hits.append((t, q["name"], sd, sp))
        finally:
            p.close()
    except _fp.PageError as e:
        print("picture_legibility_qa: %s" % e, file=sys.stderr)
        return 2
    finally:
        srv.shutdown()
    found = spans(hits, every)
    if "--json" in argv:
        print(json.dumps({"unreadable": [{"picture": a, "start": round(s, 2), "end": round(e, 2), "std": round(sd, 1),
                                          "spread": round(sp, 1)} for a, s, e, sd, sp in found]}, ensure_ascii=False))
    else:
        for a, s, e, sd, sp in found:
            print("UNREADABLE %6.2f-%6.2fs  %r shows almost nothing (luma std %.1f, spread %.0f levels): light it, "
                  "use a picture that reads at this size, or mark an intended blank data-blank-ok" % (s, e, a, sd, sp))
        print("[picture_legibility_qa] %s  %d unreadable picture(s); %d picture sighting(s) judged, sampled every %.2f s"
              % ("OK" if not found else "RED", len(found), judged, every))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
