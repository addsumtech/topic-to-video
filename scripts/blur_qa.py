#!/usr/bin/env python3
"""blur_qa — a real picture held out of focus on a director-path film page.

    python3 scripts/blur_qa.py <film_dir> [--page film.html] [--frames A-B] [--json]

Steps window.seek(t) through the film every STEP seconds and, at each step, finds every visible picture (an <img>, a
<video>, an svg <image>, an element painted with a background-image url) and the CSS blur it is under (its own
`filter: blur()` plus every ancestor's). A picture blurred by BLUR_PX or more for longer than MAX_RUN seconds is RED.

WHY (2026-11-25). The Airbnb film blurred two phones in its opening row "for depth", opened a chat phone out of focus
for 1.2 s and laid blurred review screenshots under a title. The user saw blurry pictures, not depth: "你的模糊特效不要随便
就加，不知道的以为是原始图片太糊了" (don't add blur casually: a viewer thinks the original picture is that blurry). Push a picture
back by size, dimming or overlap instead.

What passes: motion blur inside a whip or a quick hand-off (MAX_RUN, 0.5 s: the same film's whips blurred a screen for
0.32 s and 0.40 s); a blurred element that holds no picture (a soft shadow, a glow); a <canvas> (its drawing is not a
photograph this can recognise). A blur the film truly means — a picture whose softness IS the point, said so — is
marked on the element or an ancestor with `data-blur-ok="<why>"`; it is listed, never red; an empty reason is red.
Exit 0 none, 1 a held blur or a blur-ok without a reason, 2 usage error or the page failed to load.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402
import _filmpage as _fp  # noqa: E402

_USAGE = "usage: blur_qa.py <film_dir> [--page film.html] [--frames A-B] [--json]"
STEP = 0.1
BLUR_PX = 1.0
MAX_RUN = 0.5

_BLURRED = r"""
(() => { const out = [], W = innerWidth, H = innerHeight;
  const px = (f) => { let s = 0; for (const m of (f || '').matchAll(/blur\(([\d.]+)px\)/g)) s += parseFloat(m[1]); return s; };
  const name = (el) => el.id ? '#' + el.id : (el.getAttribute('src') ? el.tagName.toLowerCase() + '[' +
      el.getAttribute('src').split('/').pop() + ']' : el.tagName.toLowerCase() + '.' + (el.className.baseVal ?? el.className));
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el), tag = el.tagName;
    if (!(tag === 'IMG' || tag === 'VIDEO' || tag === 'image' || /url\(/.test(cs.backgroundImage))) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8 || r.right < 0 || r.bottom < 0 || r.left > W || r.top > H) continue;
    let blur = 0, op = 1, ok = null, shown = true;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const c = getComputedStyle(e);
      if (c.display === 'none' || c.visibility === 'hidden') { shown = false; break; }
      op *= parseFloat(c.opacity); blur += px(c.filter);
      if (ok === null && e.hasAttribute('data-blur-ok')) ok = e.getAttribute('data-blur-ok');
    }
    if (shown && op >= 0.05 && blur >= %(BLUR)s) out.push({el: name(el), blur: +blur.toFixed(2), ok});
  }
  return out; })()
""" % {"BLUR": BLUR_PX}


def runs(samples, step=STEP):
    """samples: [(t, [{el, blur, ok}])] in time order -> held blurs [{el, from, to, seconds, max_blur, ok}]."""
    open_, out = {}, []
    for t, hits in samples:
        now = {h["el"]: h for h in hits}
        for el in list(open_):
            if el not in now:
                out.append(open_.pop(el))
        for el, h in now.items():
            r = open_.setdefault(el, {"el": el, "from": t, "to": t, "max_blur": 0.0, "ok": h["ok"]})
            r["to"], r["max_blur"] = t, max(r["max_blur"], h["blur"])
    out += open_.values()
    for r in out:
        r["seconds"] = round(r["to"] - r["from"] + step, 2)
    return sorted(out, key=lambda r: r["from"])


def judge(found):
    """(red, declared): held longer than MAX_RUN without a reason, and those declared with one."""
    held = [r for r in found if r["seconds"] > MAX_RUN]
    declared = [r for r in held if isinstance(r["ok"], str) and r["ok"].strip()]
    return [r for r in held if r not in declared], declared


def main(argv):
    _c.refuse_unknown(argv, valued=("page", "frames"), switches=("json",), usage=_USAGE)
    span = _c.frame_span(argv)
    page = _c.argflag(argv, "page", None) or "film.html"
    args = [a for a in argv if not a.startswith("--") and a not in (page, _c.argflag(argv, "frames", None))]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    if not os.path.isfile(os.path.join(d, page)):
        print("blur_qa: no page at %s" % os.path.join(d, page), file=sys.stderr)
        return 2
    n = _fp.film_frames_count(d, 30)
    if not n:
        print("blur_qa: no _plan.json \"frames\" or timeline.json \"duration\"", file=sys.stderr)
        return 2
    port, srv = _fp.serve(d)
    samples = []
    try:
        p = _fp.FilmPage(port, page)
        try:
            t, t_end = (span[0] / 30.0, min(n, span[1]) / 30.0) if span else (0.0, n / 30.0)
            while t < t_end:
                p.seek(t)
                samples.append((round(t, 2), p.ev(_BLURRED) or []))
                t += STEP
        finally:
            p.close()
    except _fp.PageError as e:
        print("blur_qa: %s" % e, file=sys.stderr)
        return 2
    finally:
        srv.shutdown()
    red, declared = judge(runs(samples))
    if "--json" in argv:
        print(json.dumps({"red": red, "declared": declared}, ensure_ascii=False))
    else:
        for r in red:
            print("BLURRED   %.1f-%.1f s (%.1f s)  %s  up to %.1f px%s" % (
                r["from"], r["to"] + STEP, r["seconds"], r["el"], r["max_blur"],
                "  (data-blur-ok has no reason)" if r["ok"] is not None else ""))
        for r in declared:
            print("DECLARED  %.1f-%.1f s  %s: %s" % (r["from"], r["to"] + STEP, r["el"], r["ok"]))
        print("[blur_qa] %s  %d picture(s) held out of focus over %.1f s%s" % (
            "OK" if not red else "RED", len(red), MAX_RUN,
            "" if not red else " — a viewer reads a blurred picture as a blurry original: push it back by size, "
                               "dimming or overlap, or mark a blur that IS the point data-blur-ok=\"<why>\""))
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
