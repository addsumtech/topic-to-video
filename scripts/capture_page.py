#!/usr/bin/env python3
"""Bake a real page into a TEXTURE the remotion tier can film, plus the layout that makes it filmable.

    python3 scripts/capture_page.py <page.html|https://…> --name workspace
    python3 scripts/capture_page.py … --width 1600 --max-height 4000 --out remotion/public/textures

WHY. The bespoke-shot library can now DRAW an application window (`runtime/uiSurface`) and fly a camera over
it (`runtime/pageCam2D`), and a drawn window is still a drawing. The shots this library could not make are
the ones whose whole persuasive weight is that the product is REAL — a document writing itself, a dashboard
being pointed at — and those need the product's own pixels.

WHY A LAYOUT FILE AND NOT JUST A PNG. A screenshot alone can only be panned across. What makes it a SHOT is
knowing where things are in it: which rectangle is the third paragraph, so a reveal can uncover it in reading
order; where the sidebar ends, so a camera can hold on it. So the capture records both, from one page load —
the pixels and the boxes that produced them cannot disagree, which is the failure a hand-marked layout has by
construction and acquires the first time the page changes.

WHAT IT REFUSES TO DO. It writes nothing if the page rendered blank or the box list came back empty: a
texture of Chrome's own error page probes as a perfectly good image, and a shot built on one is a film of
nothing that passes every gate. It also never leaves a half-written pair on disk — a PNG with no layout is
the state where a register renders a picture it cannot animate.
"""
import argparse
import base64
import json
import os
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(_ROOT, "remotion", "public", "textures")

# The boxes worth knowing about: things a shot reveals, points at, or holds on. Deliberately not "every
# element" — a list of 4000 divs is not a layout, it is the DOM again, and nothing can direct from it.
_BLOCKS_JS = r"""
(() => {
  const SEL = 'h1,h2,h3,h4,p,li,blockquote,pre,code,figure,img,table,tr,th,td,button,a,input,label,' +
              'nav,aside,header,footer,section>div';
  const seen = [], out = [];
  const de = document.documentElement;
  for (const el of document.querySelectorAll(SEL)) {
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 6) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity || '1') < 0.05) continue;
    // skip a box that merely wraps one already recorded — a reveal wants the thing, not its container
    const key = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)].join(',');
    if (seen.indexOf(key) >= 0) continue;
    seen.push(key);
    const text = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120);
    out.push({x: Math.round(r.x + scrollX), y: Math.round(r.y + scrollY),
              w: Math.round(r.width), h: Math.round(r.height),
              tag: el.tagName.toLowerCase(), text});
  }
  // THE PAGE'S OWN GROUND, recorded here because a reveal has to be PAINTED in it. A shot that uncovers a
  // block by retracting a mask must draw that mask in the page's background colour or the wipe is a visible
  // grey bar travelling across the document — and TypeScript cannot sample a texture to find out.
  const bodyBg = getComputedStyle(document.body).backgroundColor;
  const htmlBg = getComputedStyle(de).backgroundColor;
  const solid = (c) => c && c !== 'transparent' && !/rgba\(0,\s*0,\s*0,\s*0\)/.test(c);
  return JSON.stringify({
    pageW: Math.max(de.scrollWidth, de.clientWidth),
    pageH: Math.max(de.scrollHeight, de.clientHeight),
    bg: solid(bodyBg) ? bodyBg : (solid(htmlBg) ? htmlBg : 'rgb(255,255,255)'),
    blocks: out,
  });
})()
"""


def _url_for(target):
    if target.startswith("http://") or target.startswith("https://") or target.startswith("file://"):
        return target
    if not os.path.isfile(target):
        raise FileNotFoundError(
            "%s is neither a URL nor a file. Chrome would render its own error page for it, and a texture of "
            "that probes as a perfectly good image." % target)
    return "file://" + quote(os.path.abspath(target))


def capture(target, name, width=1400, max_height=4000, out_dir=DEFAULT_OUT, chrome_bin=None):
    """Write `<name>.png` + `<name>.layout.json`. Returns the layout dict. Raises rather than half-write."""
    import _cdp
    import scenes
    url = _url_for(target)
    ch = _cdp.Chrome(chrome_bin or scenes._chrome_bin({}), width, 900)
    try:
        ch._cmd("Page.navigate", {"url": url}, ch.sid)
        ch._wait_ready() if hasattr(ch, "_wait_ready") else None
        # settle: readyState alone lands before webfonts paint, and a texture baked mid-swap ships the
        # fallback face into every frame of the film
        import time
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            r = ch._cmd("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True}, ch.sid)
            if r.get("result", {}).get("result", {}).get("value") == "complete":
                break
            time.sleep(0.1)
        try:
            ch._cmd("Runtime.evaluate", {"expression": "document.fonts && document.fonts.ready",
                                         "awaitPromise": True, "returnByValue": True}, ch.sid)
        except Exception:
            pass
        time.sleep(0.35)
        raw = ch._cmd("Runtime.evaluate", {"expression": _BLOCKS_JS, "returnByValue": True}, ch.sid)
        layout = json.loads(raw["result"]["result"]["value"])
        pageH = min(int(layout["pageH"]), max_height)
        layout["pageH"] = pageH
        layout["pageW"] = width
        layout["source"] = target
        if not layout["blocks"]:
            raise RuntimeError(
                "%s produced no measurable blocks. Either it did not load (Chrome renders its own error page, "
                "which screenshots perfectly well) or it has no content — and a texture of nothing is a shot "
                "of nothing that will pass every gate this repo has." % target)
        # the whole page in one grab, not the viewport
        shot = ch._cmd("Page.captureScreenshot",
                       {"format": "png", "captureBeyondViewport": True,
                        "clip": {"x": 0, "y": 0, "width": width, "height": pageH, "scale": 1}}, ch.sid)
        png = base64.b64decode(shot["result"]["data"])
    finally:
        ch.close()

    os.makedirs(out_dir, exist_ok=True)
    png_path = os.path.join(out_dir, name + ".png")
    lay_path = os.path.join(out_dir, name + ".layout.json")
    tmp_png, tmp_lay = png_path + ".part", lay_path + ".part"
    with open(tmp_png, "wb") as fh:
        fh.write(png)
    with open(tmp_lay, "w", encoding="utf-8") as fh:
        json.dump(layout, fh, ensure_ascii=False, indent=1)
    # both or neither: a PNG with no layout is a picture a register can show and cannot animate
    os.replace(tmp_png, png_path)
    os.replace(tmp_lay, lay_path)
    return layout


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target", help="a local .html file or a URL")
    ap.add_argument("--name", required=True, help="texture name (written as <name>.png + <name>.layout.json)")
    ap.add_argument("--width", type=int, default=1400)
    ap.add_argument("--max-height", type=int, default=4000)
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    lay = capture(a.target, a.name, a.width, a.max_height, a.out)
    print("[capture_page] %s -> %s.png %dx%d, %d blocks"
          % (a.target, os.path.join(a.out, a.name), lay["pageW"], lay["pageH"], len(lay["blocks"])))
    print("               film it with runtime/pageCam2D + the blocks in %s.layout.json" % a.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
