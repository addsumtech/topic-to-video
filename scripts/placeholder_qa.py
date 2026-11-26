#!/usr/bin/env python3
"""placeholder_qa — a screen in a director-path film that shows placeholder shapes where its content should be.

    python3 scripts/placeholder_qa.py <film_dir> [--page film.html] [--every 0.5] [--frames A-B] [--json]

Loads film.html (scripts/_filmpage.py) with a hook on every 2D canvas: what each canvas paints (filled shapes, and
the text and images that are its content), reset when the canvas is cleared or painted over whole. An app screen laid
out as HTML (Stage3D.screen draws it as an SVG picture) is laid out again in the page and read the same way: boxes with
a background, and the text and pictures in them. Then it steps window.seek(t) through the film and judges every screen
SHOWN at that moment (a canvas on a visible mesh of a Stage3D stage, or a visible canvas in the page):

  BARS    three or more filled text-line shapes (at least 3x as wide as tall, no taller than 8 % of the screen, less
          than 9/10 of its width: a band across the whole screen is a highlight) with no text or picture on them:
          lines standing in for words;
  BLOCKS  three or more filled shapes of one colour, big enough to hold a word, with nothing in them, that do not
          stand on one baseline (a bar chart's bars do): an empty calendar, empty cards, empty tiles.

A shape the colour of the shape it sits on (invisible), a container (a quarter of the screen or more), and a drawing
(a gradient fill, or a path of several outlines: a ring, a glyph) are not judged. A screen that is meant to look like that says why: `data-placeholder-ok="<why>"` on its canvas (canvas.dataset
.placeholderOk) or on an element of its markup; it is listed, never red; an empty reason is red.

WHY (2026-11-26). A Grok Bot promo filled its Bots' screens with grey bars and empty tinted blocks ("names not sourced:
grey bars"): an inbox of grey lines, a calendar of blank events, receipts as bars. The user: "一些shot的bot上的屏幕没有
内容，我希望可以尽量确保每个屏幕上都有一些具体的内容，而不是一些灰色的block替代". A screen shows real content: the
product's own words, or plausible demo content declared `demo` in copy_ok.json; text too small to read is still drawn
as text (it reads as texture), never as a bar.
Exit 0 no placeholder screen, 1 a placeholder screen or a placeholder-ok without a reason, 2 usage error or the page
failed to load.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402
import _filmpage as _fp  # noqa: E402

_USAGE = "usage: placeholder_qa.py <film_dir> [--page film.html] [--every 0.5] [--frames A-B] [--json]"
MIN_GROUP = 3          # shapes of one kind on one screen before it reads as a placeholder
BAR_ASPECT = 3.0       # a text-line shape is at least this many times as wide as it is tall
BAR_MAX_H = 0.08       # ... and no taller than this share of the screen's height
BAR_MIN_H = 0.003      # ... and no thinner than this share (a hairline is a rule, not a line of text)
BLOCK_MIN = 0.02       # a block's short side, as a share of the screen's short side (an icon is smaller)
CONTAINER = 0.25       # a shape covering this share of the screen or more is a container, not content
LATTICE = 9            # blocks of one size, this many or more, are a pattern (a QR code's modules, keys), not stand-ins

# Records every 2D canvas's paint: shapes (fill / fillRect / roundRect, in canvas px through the current transform),
# its content (fillText / strokeText / drawImage boxes), and the SVG of an HTML screen drawn on it. A clear or a fill
# over (nearly) the whole canvas starts a new paint.
HOOK = r"""
(() => { const recs = new Map(); let next = 1; window.__ph = recs;
  const rec = (g) => { const c = g.canvas; if (!c.__phid) c.__phid = next++;
    let r = recs.get(c.__phid); if (!r) { r = {c, shapes: [], content: [], svg: null, keys: new Set(), path: null}; recs.set(c.__phid, r); } return r; };
  const pt = (g, x, y) => { const m = g.getTransform(); return [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f]; };
  const box = (ps) => { let L = 1e9, T = 1e9, R = -1e9, B = -1e9; for (const [x, y] of ps) { L = Math.min(L, x); T = Math.min(T, y); R = Math.max(R, x); B = Math.max(B, y); }
    return [L, T, R - L, B - T]; };
  const whole = (g, b) => b[2] * b[3] >= 0.95 * g.canvas.width * g.canvas.height;
  const reset = (r) => { r.shapes = []; r.content = []; r.svg = null; r.keys = new Set(); };
  const add = (r, kind, b, col) => { if (!(b[2] > 0 && b[3] > 0)) return; const k = kind + b.map((v) => Math.round(v)).join(',') + col;
    if (r.keys.has(k) || r.keys.size > 4000) return; r.keys.add(k); (kind === 's' ? r.shapes : r.content).push(kind === 's' ? [...b, col] : b); };
  const P = CanvasRenderingContext2D.prototype, wrap = (m, f) => { const o = P[m]; if (o) P[m] = function () { try { f(this, arguments); } catch (e) {} return o.apply(this, arguments); }; };
  const grow = (g, ps) => { const r = rec(g); r.path = (r.path || []).concat(ps.map(([x, y]) => pt(g, x, y))); };
  wrap('beginPath', (g) => { const r = rec(g); r.path = []; r.sub = 0; });
  wrap('moveTo', (g, a) => { rec(g).sub = (rec(g).sub || 0) + 1; grow(g, [[a[0], a[1]]]); });
  wrap('lineTo', (g, a) => grow(g, [[a[0], a[1]]]));
  wrap('rect', (g, a) => { rec(g).sub = (rec(g).sub || 0) + 1; grow(g, [[a[0], a[1]], [a[0] + a[2], a[1] + a[3]]]); });
  wrap('roundRect', (g, a) => { rec(g).sub = (rec(g).sub || 0) + 1; grow(g, [[a[0], a[1]], [a[0] + a[2], a[1] + a[3]]]); });
  wrap('arc', (g, a) => grow(g, [[a[0] - a[2], a[1] - a[2]], [a[0] + a[2], a[1] + a[2]]]));
  wrap('ellipse', (g, a) => grow(g, [[a[0] - a[2], a[1] - a[3]], [a[0] + a[2], a[1] + a[3]]]));
  wrap('arcTo', (g, a) => grow(g, [[a[0], a[1]], [a[2], a[3]]]));
  wrap('quadraticCurveTo', (g, a) => grow(g, [[a[0], a[1]], [a[2], a[3]]]));
  wrap('bezierCurveTo', (g, a) => grow(g, [[a[0], a[1]], [a[2], a[3]], [a[4], a[5]]]));
  wrap('fill', (g, a) => { const r = rec(g); if (a.length && typeof a[0] === 'object' || !r.path || !r.path.length) return;
    const b = box(r.path); if (whole(g, b)) return reset(r);
    if (r.sub > 1 || typeof g.fillStyle !== 'string') return;   // several outlines (a ring, a glyph) or a gradient: a drawing
    add(r, 's', b, String(g.fillStyle) + '@' + g.globalAlpha); });
  wrap('fillRect', (g, a) => { const r = rec(g), b = box([pt(g, a[0], a[1]), pt(g, a[0] + a[2], a[1] + a[3])]);
    if (whole(g, b)) return reset(r); if (typeof g.fillStyle === 'string') add(r, 's', b, String(g.fillStyle) + '@' + g.globalAlpha); });
  wrap('clearRect', (g, a) => { const b = box([pt(g, a[0], a[1]), pt(g, a[0] + a[2], a[1] + a[3])]); if (whole(g, b)) reset(rec(g)); });
  const text = (g, a) => { const s = String(a[0]); if (!s.trim()) return; const w = g.measureText(s).width,
      h = parseFloat((g.font.match(/([\d.]+)px/) || [0, 12])[1]), al = g.textAlign, bl = g.textBaseline;
    const x0 = al === 'center' ? a[1] - w / 2 : (al === 'right' || al === 'end') ? a[1] - w : a[1];
    const y0 = bl === 'middle' ? a[2] - h / 2 : (bl === 'top' || bl === 'hanging') ? a[2] : (bl === 'bottom' || bl === 'ideographic') ? a[2] - h : a[2] - 0.8 * h;
    add(rec(g), 'c', box([pt(g, x0, y0), pt(g, x0 + w, y0 + h)])); };
  wrap('fillText', text); wrap('strokeText', text);
  wrap('drawImage', (g, a) => { const im = a[0], n = a.length, r = rec(g);
    const [dx, dy, dw, dh] = n >= 9 ? [a[5], a[6], a[7], a[8]] : n >= 5 ? [a[1], a[2], a[3], a[4]]
      : [a[1], a[2], im.naturalWidth || im.width, im.naturalHeight || im.height];
    const b = box([pt(g, dx, dy), pt(g, dx + dw, dy + dh)]);
    const src = im && im.src && String(im.src);
    if (whole(g, b)) { reset(r); if (src && src.startsWith('data:image/svg+xml') && src.includes('foreignObject')) { r.svg = src; return; } }
    add(r, 'c', b); });
})();
"""

# The screens shown now: {id, name, W, H, shapes, content, ok, svg?}. A canvas on a visible mesh of a Stage3D stage
# (through a device's letterbox canvas too), or a visible canvas in the page.
_SHOWN = r"""
(async () => { const recs = window.__ph || new Map(), shown = new Set();
  const S = window.Stage3D;
  if (S && S.stages && S.THREE) for (const st of S.stages) { const T = S.THREE; st.scene.updateMatrixWorld(true);
    const fr = new T.Frustum().setFromProjectionMatrix(new T.Matrix4().multiplyMatrices(st.camera.projectionMatrix, st.camera.matrixWorldInverse));
    st.scene.traverseVisible((m) => { const im = m.material && m.material.map && m.material.map.image;
      if (!im || !(im instanceof HTMLCanvasElement)) return;
      m.geometry.computeBoundingSphere(); if (!fr.intersectsSphere(m.geometry.boundingSphere.clone().applyMatrix4(m.matrixWorld))) return;
      for (let e = m; e; e = e.parent) if (!e.visible) return;
      shown.add(im); if (im.__src) shown.add(im.__src); }); }
  for (const c of document.querySelectorAll('canvas')) { const r = c.getBoundingClientRect(); let vis = r.width > 4 && r.height > 4
      && r.right > 0 && r.bottom > 0 && r.left < innerWidth && r.top < innerHeight;
    for (let e = c; vis && e && e.nodeType === 1; e = e.parentElement) { const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) vis = false; }
    if (vis) shown.add(c); }
  const out = [];
  for (const [id, r] of recs) { if (!shown.has(r.c)) continue;
    const name = r.c.id ? '#' + r.c.id : r.c.dataset.name || ('canvas ' + id + ' ' + r.c.width + 'x' + r.c.height);
    const ok = r.c.dataset.placeholderOk;
    if (r.svg) { out.push(Object.assign({id: 'svg' + id, name, ok}, await window.__phLayout(r.svg))); continue; }
    if (r.shapes.length >= 3) out.push({id: 'c' + id, name, W: r.c.width, H: r.c.height, shapes: r.shapes, content: r.content, ok}); }
  return out; })()
"""

# An HTML screen (the SVG picture Stage3D.screen draws) laid out again: boxes with a background, and what is in them.
_LAYOUT = r"""
window.__phLayout = window.__phLayout || (async (src) => {
  const svg = new DOMParser().parseFromString(decodeURIComponent(src.slice(src.indexOf(',') + 1)), 'image/svg+xml');
  const fo = svg.querySelector('foreignObject'), vb = (svg.documentElement.getAttribute('viewBox') || '0 0 0 0').split(/\s+/).map(Number);
  const W = vb[2], H = vb[3], host = document.createElement('div');
  host.style.cssText = 'position:fixed;left:0;top:0;width:' + W + 'px;height:' + H + 'px;visibility:hidden;pointer-events:none;z-index:-1;overflow:hidden';
  document.body.appendChild(host); const sh = host.attachShadow({mode: 'open'});
  sh.innerHTML = '<div id="__r" style="width:' + W + 'px;height:' + H + 'px;position:relative;overflow:hidden">' + (fo ? fo.innerHTML : '') + '</div>';
  await document.fonts.ready;
  const R = sh.getElementById('__r').getBoundingClientRect(), rel = (b) => [b.left - R.left, b.top - R.top, b.width, b.height];
  const shapes = [], content = []; let ok;
  for (const el of sh.querySelectorAll('#__r *')) { if (/^(STYLE|SCRIPT)$/.test(el.tagName)) continue;
    // (the host is visibility:hidden, which every element inherits: judge display and opacity only)
    const cs = getComputedStyle(el); if (cs.display === 'none' || parseFloat(cs.opacity) < 0.05) continue;
    if (el.hasAttribute('data-placeholder-ok') && ok === undefined) ok = el.getAttribute('data-placeholder-ok');
    for (const n of el.childNodes) if (n.nodeType === 3 && n.textContent.trim()) { const g = document.createRange(); g.selectNodeContents(n);
      for (const b of g.getClientRects()) content.push(rel(b)); }
    const b = el.getBoundingClientRect(); if (b.width < 1 || b.height < 1) continue;
    if (/^(IMG|svg|SVG|CANVAS|VIDEO|PICTURE)$/.test(el.tagName) || /url\(/.test(cs.backgroundImage)) { content.push(rel(b)); continue; }
    if (el.closest('[data-placeholder-ok]')) continue;
    const bg = cs.backgroundColor, has = (bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') || /gradient/.test(cs.backgroundImage);
    if (has) shapes.push([...rel(b), bg + '|' + cs.backgroundImage]); }
  host.remove(); return {W, H, shapes, content, ok}; });
"""


def _inside(c, s, pad=1.0):
    """Is the centre of content box c inside shape s (both [x, y, w, h])?"""
    cx, cy = c[0] + c[2] / 2.0, c[1] + c[3] / 2.0
    return s[0] - pad <= cx <= s[0] + s[2] + pad and s[1] - pad <= cy <= s[1] + s[3] + pad


def _contains(a, b, pad=0.5):
    return a[0] - pad <= b[0] and a[1] - pad <= b[1] and b[0] + b[2] <= a[0] + a[2] + pad and b[1] + b[3] <= a[1] + a[3] + pad


def _touch(a, b, gap=1.5):
    """Do boxes a and b touch or overlap (within `gap` px)?"""
    return a[0] - gap <= b[0] + b[2] and b[0] - gap <= a[0] + a[2] and a[1] - gap <= b[1] + b[3] and b[1] - gap <= a[1] + a[3]


def judge(W, H, shapes, content):
    """One screen's paint -> (bars, blocks): the empty text-line shapes and the empty same-colour blocks that make it a
    placeholder screen ([] when it is not). shapes: [x, y, w, h, colour] in paint order; content: [x, y, w, h]."""
    W, H = float(W), float(H)
    empty = []
    for i, s in enumerate(shapes):
        x, y, w, h, col = s[0], s[1], s[2], s[3], s[4]
        if w * h >= CONTAINER * W * H or w <= 0 or h <= 0:
            continue
        # invisible: the colour of the smallest earlier shape it sits in
        holders = [p for p in shapes[:i] if p[2] * p[3] > w * h and _contains(p, s)]
        if holders and min(holders, key=lambda p: p[2] * p[3])[4] == col:
            continue
        if any(_inside(c, s) for c in content):
            continue
        # a shape with another shape drawn in it is a drawing (an icon, a QR code's finder square), not an empty box
        if any(j != i and p[2] * p[3] < w * h and _contains(s, p) and p[4] != col for j, p in enumerate(shapes)):
            continue
        empty.append(s)
    # a line of text never runs the screen's whole width: a band that does is a highlight or a bar of the UI
    bars = [s for s in empty if s[2] >= BAR_ASPECT * s[3] and BAR_MIN_H * H <= s[3] <= BAR_MAX_H * H and s[3] >= 2
            and s[2] < 0.9 * W]
    bars = bars if len(bars) >= MIN_GROUP else []
    blocks, bysize = [], {}
    for s in empty:
        if s in bars or min(s[2], s[3]) < max(10.0, BLOCK_MIN * min(W, H)) or s[2] >= BAR_ASPECT * s[3]:
            continue
        bysize.setdefault(s[4], []).append(s)
    for col, g in bysize.items():
        if len(g) < MIN_GROUP:
            continue
        base = [s[1] + s[3] for s in g]
        if max(base) - min(base) <= 0.01 * H:      # one baseline: a bar chart
            continue
        sizes = {}
        for s in g:
            k = (round(s[2] / max(1.0, 0.02 * s[2])), round(s[3] / max(1.0, 0.02 * s[3])))
            sizes[k] = sizes.get(k, 0) + 1
        if len(g) >= LATTICE and max(sizes.values()) >= 0.6 * len(g):   # one size, many times: a QR code, keys, a grid
            continue
        # blocks that touch each other are one pattern (modules, pixel art); stand-ins sit apart, with a gap between
        g = [s for s in g if not any(o is not s and _touch(s, o) for o in g)]
        if len(g) < MIN_GROUP:
            continue
        blocks += g
    return bars, blocks


def main(argv):
    _c.refuse_unknown(argv, valued=("page", "every", "frames"), switches=("json",), usage=_USAGE)
    span = _c.frame_span(argv)
    vals = {k: _c.argflag(argv, k, None) for k in ("page", "every", "frames")}
    pos = [a for a in argv if not a.startswith("--") and a not in vals.values()]
    if len(pos) != 1 or not os.path.isdir(pos[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d, page = os.path.abspath(pos[0]), vals["page"] or "film.html"
    if not os.path.isfile(os.path.join(d, page)):
        print("placeholder_qa: no page at %s" % os.path.join(d, page), file=sys.stderr)
        return 2
    every = float(vals["every"] or 0.5)
    n = _fp.film_frames_count(d, 30)
    if not n:
        print("placeholder_qa: no _plan.json \"frames\" or timeline.json \"duration\"", file=sys.stderr)
        return 2
    found, oks = {}, {}
    port, srv = _fp.serve(d)
    try:
        p = _fp.FilmPage(port, page, init_script=HOOK)
        try:
            p.ev(_LAYOUT)
            t, t_end = (span[0] / 30.0, min(n, span[1]) / 30.0) if span else (0.0, n / 30.0)
            while t < t_end:
                p.seek(t)
                for sc in p.ev(_SHOWN, True) or []:
                    bars, blocks = judge(sc["W"], sc["H"], sc["shapes"], sc["content"])
                    if not (bars or blocks):
                        continue
                    if sc.get("ok") is not None:
                        oks.setdefault(sc["name"], (sc["ok"], round(t, 2)))
                        continue
                    f = found.setdefault(sc["name"], {"t0": round(t, 2), "t1": round(t, 2), "bars": 0, "blocks": 0,
                                                      "size": [round(sc["W"]), round(sc["H"])], "example": None})
                    f["t1"] = round(t, 2)
                    f["bars"], f["blocks"] = max(f["bars"], len(bars)), max(f["blocks"], len(blocks))
                    f["example"] = f["example"] or [round(v) for v in (bars or blocks)[0][:4]]
                t += every
        finally:
            p.close()
    except _fp.PageError as e:
        print("placeholder_qa: %s" % e, file=sys.stderr)
        return 2
    finally:
        srv.shutdown()
    no_reason = [k for k, (why, _) in oks.items() if not str(why).strip()]
    if "--json" in argv:
        print(json.dumps({"placeholders": found, "ok": {k: {"why": w, "t": t} for k, (w, t) in oks.items()},
                          "ok_without_reason": no_reason}, ensure_ascii=False))
    else:
        for k, f in found.items():
            print("PLACEHOLDER  t=%.1f-%.1fs  %s (%dx%d): %d empty text-line bar(s), %d empty block(s), e.g. a box at %s"
                  % (f["t0"], f["t1"], k, f["size"][0], f["size"][1], f["bars"], f["blocks"], f["example"]))
        for k, (w, t) in oks.items():
            print("%s  %s  t=%.1fs  data-placeholder-ok: %r" % ("NO REASON" if not str(w).strip() else "declared ", k, t, w))
        print("[placeholder_qa] %s  %d placeholder screen(s)%s" % (
            "OK" if not found and not no_reason else "RED", len(found),
            "" if not found else " — give each screen its real content: the product's own words, or plausible demo"
            " content declared `demo` in copy_ok.json; text too small to read is still drawn as text, never a bar"))
    return 1 if found or no_reason else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
