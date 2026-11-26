"""page_overlap_qa — do words or controls collide on a film page? Read from the page itself, over time.

    python3 scripts/page_overlap_qa.py <film_dir> [--page film.html] [--every 0.25] [--frames A-B] [--json]

A director-path film is one page whose every frame is `window.seek(t)` (SKILL.md step 6). This loads that page in
headless Chrome, steps t through the film (`_plan.json` frames / fps, else timeline.json's duration), and at each step collects the VISIBLE text and
controls — elements with their own text, buttons, inputs, [role=button], typeset equations ([data-math]) — with their
on-screen boxes. Two of them COLLIDE when neither contains the other and their boxes overlap by more than a quarter
of the smaller one. A collision that lasts at least MIN_S is reported with both elements' text and the time span.

Also WORDS CUT BY THE FRAME'S EDGE (EDGE-CUT): a line of readable text (20 px or taller, at 60 % strength or more)
whose glyphs, cut to every clipping ancestor, cross the picture's edge for EDGE_MIN_S or more. A camera following
typing left "…for topic-to-video itself, th" running off the right edge for over a second (topic-to-video launch
film, 2026-11-19; no check saw it). A deliberate bleed (giant type running off the frame) is marked `data-bleed-ok`.

WHY. A Grok Bot film (2026-11-17) laid buttons over one another; the user saw it and no check had. Pixels cannot tell
an overlap from a design, the page can: it knows which boxes are words and controls.
EXEMPT: anything inside an element marked `data-overlap-ok` (a deliberate stack, a pile of cards). Images and canvases
are not judged (type over a picture is a design choice). Boxes are axis-aligned, so a strongly rotated element is
judged by its bounding box (it can over-report there; mark it if it is intended).
Exit 0 clean, 1 on a collision, 2 on a usage error, a missing page, or a page without window.seek.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

MIN_S = 0.5
EDGE_MIN_S = 0.75     # a line passing the edge in a push or a slide is gone sooner; one held there is cut
SHARE = 0.25
_USAGE = "usage: page_overlap_qa.py <film_dir> [--page film.html] [--every 0.25] [--frames A-B] [--json]"

_JS = r"""
(async (times) => {
  if (typeof window.seek !== 'function') return {error: 'no window.seek'};
  const vis = (el) => {
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.35) return false;
      if (e.hasAttribute('data-overlap-ok')) return false;
    }
    return true;
  };
  const ownText = (el) => Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
  const isCtl = (el) => /^(BUTTON|INPUT|SELECT|TEXTAREA)$/.test(el.tagName) || el.getAttribute('role') === 'button';
  const out = [], edges = [];
  for (const t of times) {
    const r = window.seek(t); if (r && r.then) await r;
    const items = [];
    for (const el of document.body.querySelectorAll('*')) {
      const math = el.getAttribute('data-math');    // a typeset equation (assets/html/math.js): glyph paths, no text
      if (!(ownText(el) || isCtl(el) || math)) continue;
      if (!vis(el)) continue;
      // per LINE fragment: a highlight that wraps has one box per line; its overall box would span both lines
      // and "overlap" its neighbour on the next line (a false collision measured on a real film)
      const frags = Array.from(el.getClientRects()).filter(b => b.width * b.height >= 40 && b.right > 0 && b.bottom > 0
                                                             && b.left < innerWidth && b.top < innerHeight);
      if (!frags.length) continue;
      items.push({el, frags, label: (math || el.innerText || el.value || el.tagName).trim().slice(0, 40)});
    }
    // words cut by the FRAME's edge: a text line whose glyphs (trailing spaces left out), cut to every clipping
    // ancestor, still cross the edge of the picture, read at a readable size and strength
    for (const el of document.body.querySelectorAll('*')) {
      const tn = Array.from(el.childNodes).filter(n => n.nodeType === 3 && n.textContent.trim());
      if (!tn.length || !vis(el) || el.closest('[data-bleed-ok]')) continue;
      if (!tn.some(n => /[\p{L}\p{N}]/u.test(n.textContent))) continue;   // words, not a rule of box-drawing marks
      let op = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) op *= parseFloat(getComputedStyle(e).opacity);
      if (op < 0.6) continue;
      let clip = {left: -1e9, top: -1e9, right: 1e9, bottom: 1e9};
      for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
        const cs = getComputedStyle(e);
        if (cs.overflow !== 'visible' || cs.overflowX !== 'visible' || cs.overflowY !== 'visible' || cs.clipPath !== 'none') {
          const r = e.getBoundingClientRect();
          clip = {left: Math.max(clip.left, r.left), top: Math.max(clip.top, r.top), right: Math.min(clip.right, r.right), bottom: Math.min(clip.bottom, r.bottom)};
        }
      }
      for (const n of tn) {
        const txt = n.textContent, a = txt.search(/\S/), b = txt.length - (txt.length - txt.trimEnd().length);
        const rg = document.createRange(); rg.setStart(n, a); rg.setEnd(n, b);
        for (const q of rg.getClientRects()) {
          if (q.height < 20) continue;
          // what shows: the glyphs cut to the clipping ancestors and the picture. They are cut BY THE FRAME where a
          // side of what shows lies on the picture's edge (a shot's own frame-sized clip box counts as the frame)
          const v = {left: Math.max(q.left, clip.left, 0), top: Math.max(q.top, clip.top, 0),
                     right: Math.min(q.right, clip.right, innerWidth), bottom: Math.min(q.bottom, clip.bottom, innerHeight)};
          if (v.right - v.left < 4 || v.bottom - v.top < 4) continue;
          const cut = (q.left < v.left - 2 && v.left <= 2) || (q.right > v.right + 2 && v.right >= innerWidth - 2)
                   || (q.top < v.top - 2 && v.top <= 2) || (q.bottom > v.bottom + 2 && v.bottom >= innerHeight - 2);
          if (cut) { edges.push({t, a: txt.trim().slice(0, 40)}); break; }
        }
      }
    }
    for (let i = 0; i < items.length; i++) for (let j = i + 1; j < items.length; j++) {
      const A = items[i], B = items[j];
      if (A.el.contains(B.el) || B.el.contains(A.el)) continue;
      let hit = false;
      for (const a of A.frags) { for (const b of B.frags) {
        const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (w > 0 && h > 0 && w * h > %SHARE% * Math.min(a.width * a.height, b.width * b.height)) { hit = true; break; }
      } if (hit) break; }
      if (hit) out.push({t, a: A.label, b: B.label});
    }
  }
  return {hits: out, edges};
})(%TIMES%)
"""


def spans(hits, every, min_s=MIN_S):
    """[(a, b, start, end)] for each pair that collides over consecutive samples for at least min_s."""
    by = {}
    for h in hits:
        by.setdefault((h["a"], h["b"]), []).append(h["t"])
    out = []
    for (a, b), ts in by.items():
        ts.sort()
        s = prev = ts[0]
        for t in ts[1:] + [None]:
            if t is not None and t - prev <= every * 1.5:
                prev = t
                continue
            if prev - s + every >= min_s:
                out.append((a, b, round(s, 2), round(prev + every, 2)))
            if t is not None:
                s = prev = t
    return sorted(out, key=lambda x: x[2])


def main(argv):
    _c.refuse_unknown(argv, valued=("page", "every", "frames"), switches=("json",), usage=_USAGE)
    span = _c.frame_span(argv)
    args = [a for a in argv if not a.startswith("--") and a not in (_c.argflag(argv, "page", None), _c.argflag(argv, "every", None),
                                                                        _c.argflag(argv, "frames", None))]
    if len(args) != 1:
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    page = os.path.join(d, _c.argflag(argv, "page", "film.html"))
    every = float(_c.argflag(argv, "every", 0.25))
    if not os.path.isfile(page):
        print("page_overlap_qa: no page at %s" % page, file=sys.stderr)
        return 2
    plan = os.path.join(d, "_plan.json")
    dur = 60.0
    if os.path.isfile(plan):
        p = json.load(open(plan, encoding="utf-8"))
        dur = float(p.get("frames", 0)) / float(p.get("fps", 30)) or dur
    else:                                        # the blocking page, before the build: the voice's clock
        import _filmpage
        dur = (_filmpage.film_frames_count(d, 30) or dur * 30) / 30.0
    times = [round(i * every, 3) for i in range(int(dur / every))]
    if span:                                     # one builder's stretch only (film_qc --frames)
        times = [t for t in times if span[0] / 30.0 <= t < span[1] / 30.0]
    # served over http and loaded as film_frames loads it (fonts, window.filmReady): from file:// a page with absolute
    # script paths never defined window.seek, and the check failed on both 2026-11-18 films instead of looking
    import _filmpage as _fp
    port, srv = _fp.serve(d)
    hits, edge_hits = [], []
    try:
        pg = _fp.FilmPage(port, os.path.relpath(page, d))
        try:
            for k in range(0, len(times), 40):
                js = _JS.replace("%TIMES%", json.dumps(times[k:k + 40])).replace("%SHARE%", str(SHARE))
                val = pg.ev(js, True) or {}
                if val.get("error"):
                    print("page_overlap_qa: %s — the page must expose window.seek(t)" % val["error"], file=sys.stderr)
                    return 2
                hits += val.get("hits", [])
                edge_hits += [dict(h, b="the frame's edge") for h in val.get("edges", [])]
        finally:
            pg.close()
    except _fp.PageError as e:
        print("page_overlap_qa: %s" % e, file=sys.stderr)
        return 2
    finally:
        srv.shutdown()
    found = spans(hits, every)
    cut = spans(edge_hits, every, EDGE_MIN_S)
    if "--json" in argv:
        print(json.dumps({"collisions": [{"a": a, "b": b, "start": s, "end": e} for a, b, s, e in found],
                          "cut_by_edge": [{"a": a, "start": s, "end": e} for a, _b, s, e in cut]}, ensure_ascii=False))
    else:
        for a, b, s, e in found:
            print("COLLIDE  %.2f-%.2fs  %r over %r" % (s, e, a, b))
        for a, _b, s, e in cut:
            print("EDGE-CUT %.2f-%.2fs  %r runs off the frame's edge (reframe, wrap, or mark a deliberate bleed data-bleed-ok)" % (s, e, a))
        print("[page_overlap_qa] %s  %d collision(s), %d line(s) cut by the frame's edge over %.0f s sampled every %.2f s"
              % ("OK" if not (found or cut) else "RED", len(found), len(cut), dur, every))
    return 1 if (found or cut) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
