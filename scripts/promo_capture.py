#!/usr/bin/env python3
"""promo_capture — the promo film's raw material: a 2x capture of a page AND the boxes of its elements.

    python3 scripts/promo_capture.py <film_dir> <url> --name=home [--width=1440] [--height=900] [--full]
                                     [--wait=1.5] [--eval="js; steps split by a line ;;;"] [--select="css,css"] [--max=80]
                                     [--hires="7;520,300,240,120"]   # 4x close-up captures: element ids or CSS boxes
    python3 scripts/promo_capture.py <film_dir> --boxes=<capture.png>     # a screenshot with no DOM (desktop app)
    python3 scripts/promo_capture.py <film_dir> --mark=<capture.png> --box=x,y,w,h [--name=mark]
                                     # the brand's own logo, cut from its own page: a transparent PNG for any ground

WEB (a url, file:// included): one headless Chrome at deviceScaleFactor 2 opens the page, waits for load, fonts and
images (+ `--wait` seconds for an app that renders late), runs `--eval` if given (open a menu, fill a field), and
writes `<film_dir>/caps/<name>.png` (pixels = 2 x CSS) and `<name>.layout.json`: {w, h, elements: [{id, tag, text,
x, y, w, h}]} in CSS px — the coordinate system of the promo table (`box`). `--full` captures the whole scroll
height (capped at 4 viewports). Elements are the ones a product shot acts on: controls, fields, cards, media,
headings — visible, not the page itself, de-duplicated; `--select` adds every match of the given CSS selectors.

SCREENSHOT (`--boxes=`): for a capture with no DOM (a desktop app's window), finds the card-like rectangles —
regions of one fill bounded by an edge — and writes the same layout.json beside the PNG, plus `<name>.boxes.jpg`:
the capture at CSS size with every box drawn and numbered and a 50 px grid, to pick boxes by eye.

WHY. The WorkBuddy film's boxes were measured by hand off grids (an hour, and one box wrong is an element that lands
beside its slot). A table written from a layout file is right by construction, and a director can build a film for
a product it has never seen.
"""
import base64
import json
import re
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import argflag, refuse_unknown, find_chrome  # noqa: E402

ELEMENTS_JS = r"""
(() => {
  const SEL = %s;
  const out = [], seen = new Set();
  const vw = document.documentElement.clientWidth;
  const docH = Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0);
  const visible = (el, r) => {
    if (r.width < 12 || r.height < 12) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05) return false;
    if (r.width >= vw * 0.98 && r.height >= 600) return false;      // the page / a full-bleed section
    return true;
  };
  const cardish = (el) => {
    const cs = getComputedStyle(el);
    const bg = cs.backgroundColor, pbg = el.parentElement ? getComputedStyle(el.parentElement).backgroundColor : bg;
    const border = parseFloat(cs.borderTopWidth) > 0 && cs.borderTopStyle !== 'none';
    return (cs.boxShadow && cs.boxShadow !== 'none') || border || (bg !== pbg && bg !== 'rgba(0, 0, 0, 0)') || parseFloat(cs.borderRadius) >= 6;
  };
  const push = (el, why) => {
    const r = el.getBoundingClientRect();
    if (!visible(el, r)) return;
    const x = Math.round(r.left + scrollX), y = Math.round(r.top + scrollY), w = Math.round(r.width), h = Math.round(r.height);
    const k = [x, y, w, h].join(',');
    if (seen.has(k)) return;
    seen.add(k);
    const text = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('alt') || '').trim().replace(/\s+/g, ' ').slice(0, 80);
    out.push({tag: el.tagName.toLowerCase(), why, text, x, y, w, h});
  };
  document.querySelectorAll('button,[role=button],a,input,textarea,select,img,video,canvas,h1,h2,h3,[role=tab],li,article,figure,nav,header,aside')
    .forEach((el) => push(el, 'semantic'));
  document.querySelectorAll('div,section').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width * r.height >= 6000 && (el.children.length >= 1 || (el.innerText || '').trim()) && cardish(el)) push(el, 'card');
  });
  for (const s of SEL) { try { document.querySelectorAll(s).forEach((el) => push(el, 'select:' + s)); } catch (e) {} }
  const meta = (n) => (document.querySelector(`meta[name="${n}"],meta[property="${n}"]`) || {}).content || '';
  return {w: vw, h: docH, elements: out, title: document.title, description: meta('description') || meta('og:description')};
})()
"""


HIRES = 4


def _hires_boxes(spec, els):
    """`--hires` items: an element id from this capture (`7`) or a CSS box (`x,y,w,h`), `;`-separated."""
    out = []
    for item in [x.strip() for x in (spec or "").split(";") if x.strip()]:
        if re.fullmatch(r"\d+", item):
            e = next((e for e in els if e["id"] == int(item)), None)
            if e is None:
                raise SystemExit("[promo_capture] --hires: no element %s in this capture (see its .boxes.jpg)" % item)
            out.append({k: e[k] for k in ("x", "y", "w", "h")})
        else:
            v = [float(x) for x in item.split(",")]
            if len(v) != 4 or v[2] <= 0 or v[3] <= 0:
                raise SystemExit("[promo_capture] --hires: %r is neither an element id nor x,y,w,h" % item)
            out.append(dict(zip(("x", "y", "w", "h"), v)))
    return out


def capture_web(film, url, name, W=1440, H=900, full=False, wait=1.5, js=None, select=(), max_el=80, hires_spec=None):
    import socket
    try:
        return _capture_web(film, url, name, W, H, full, wait, js, select, max_el, hires_spec)
    except (socket.timeout, TimeoutError) as e:
        raise SystemExit("[promo_capture] %s did not answer in time (%s). A slow or very long page: try --wait=4, a "
                         "narrower page, or capture it by hand and use --boxes" % (url, e))


def _capture_web(film, url, name, W=1440, H=900, full=False, wait=1.5, js=None, select=(), max_el=80, hires_spec=None):
    import _cdp
    chrome = find_chrome()
    if not chrome:
        raise SystemExit("[promo_capture] no Chrome/Chromium found")
    caps = os.path.join(film, "caps")
    os.makedirs(caps, exist_ok=True)
    with _cdp.Chrome(chrome, W, H, device_scale=2, timeout=90) as c:
        c._cmd("Page.navigate", {"url": url}, c.sid)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            r = c._cmd("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True}, c.sid)
            if r.get("result", {}).get("result", {}).get("value") == "complete":
                break
            time.sleep(0.05)
        # fonts and image decodes, each BOUNDED: a page with hundreds of lazy images (an encyclopedia article) never
        # finishes decoding them all, and an unbounded wait is a hang, not a capture
        for expr in ("Promise.race([document.fonts ? document.fonts.ready.then(()=>1) : 1, new Promise(r=>setTimeout(()=>r(0), 8000))])",
                     "Promise.race([Promise.all(Array.from(document.images).filter(i=>i.getBoundingClientRect().top < innerHeight*1.5)"
                     ".map(i=>i.decode().catch(()=>1))).then(()=>1), new Promise(r=>setTimeout(()=>r(0), 8000))])"):
            c._cmd("Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True}, c.sid)
        time.sleep(wait)
        for step in [x for x in (js or "").split("\n;;;\n") if x.strip()]:
            # one state change per step (load a scene and reload; then open a dialog), each settled before the next
            try:
                c._cmd("Runtime.evaluate", {"expression": step, "awaitPromise": True, "returnByValue": True}, c.sid)
            except _cdp.CDPUnavailable as e:
                raise SystemExit("[promo_capture] --eval step failed: %s" % e)
            time.sleep(max(0.6, wait))
            for expr in ("document.fonts ? document.fonts.ready.then(()=>1) : 1",):
                c._cmd("Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True}, c.sid)
        lay = c._cmd("Runtime.evaluate", {"expression": ELEMENTS_JS % json.dumps(list(select)), "returnByValue": True},
                     c.sid)["result"]["result"]["value"]
        h = min(lay["h"], H * 4) if full else H
        if full and h != H:
            c._cmd("Emulation.setDeviceMetricsOverride", {"width": W, "height": h, "deviceScaleFactor": 2, "mobile": False}, c.sid)
            time.sleep(0.8)
        shot = c._cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False}, c.sid)["result"]["data"]
        png = os.path.join(caps, name + ".png")
        with open(png, "wb") as f:
            f.write(base64.b64decode(shot))
        from PIL import Image
        with Image.open(png) as im:
            pw, ph = im.size
        els = [e for e in lay["elements"] if e["y"] + e["h"] <= ph / 2 + 1 and e["x"] + e["w"] <= pw / 2 + 1 and e["x"] >= 0 and e["y"] >= 0]
        els.sort(key=lambda e: (e["why"] == "semantic" and e["tag"] in ("li", "a"), -(e["w"] * e["h"])))
        els = els[:max_el]
        els.sort(key=lambda e: (e["y"], e["x"]))
        for i, e in enumerate(els):
            e["id"] = i
        # HIGH-RES CLOSE-UPS: the elements a film pushes into past the page's own 2x, captured again at 4x (the same
        # page state, the same load) — the camera's close-up draws them over the page so the subject stays sharp
        hires = []
        boxes = _hires_boxes(hires_spec, els)
        if boxes:
            # the page REDRAWN at 4x (deviceScaleFactor), not the 2x picture scaled: a canvas app paints its bitmap at the
            # device ratio, so only a real ratio change gives its close-up real pixels
            vh = h if full else H
            c._cmd("Emulation.setDeviceMetricsOverride", {"width": W, "height": vh, "deviceScaleFactor": HIRES, "mobile": False}, c.sid)
            time.sleep(max(0.8, wait))
            for k, hb in enumerate(boxes):
                clip = {"x": hb["x"], "y": hb["y"], "width": hb["w"], "height": hb["h"], "scale": 1}
                data = c._cmd("Page.captureScreenshot", {"format": "png", "clip": clip, "captureBeyondViewport": False}, c.sid)["result"]["data"]
                hp = os.path.join(caps, "%s.hi%d.png" % (name, k))
                with open(hp, "wb") as f:
                    f.write(base64.b64decode(data))
                with Image.open(hp) as hi:
                    if abs(hi.size[0] - hb["w"] * HIRES) > 4:
                        raise SystemExit("[promo_capture] the %dx close-up of %s came back %dpx wide, not %d" % (HIRES, hb, hi.size[0], hb["w"] * HIRES))
                hires.append({"box": hb, "src": "caps/%s.hi%d.png" % (name, k), "scale": HIRES})
    # the page's own title and description: the product's words, citable as the film's source
    out = {"src": "caps/%s.png" % name, "w": pw // 2, "h": ph // 2, "url": url, "title": lay.get("title", ""),
           "description": lay.get("description", ""), "captured": time.strftime("%Y-%m-%d"), "elements": els, "hires": hires}
    json.dump(out, open(os.path.join(caps, name + ".layout.json"), "w"), indent=1)
    overlay(png, out, os.path.join(caps, name + ".boxes.jpg"))
    return out


def find_boxes(png, min_area=1800, max_frac=0.6):
    """Card-like rectangles in a screenshot with no DOM: connected regions of (nearly) one fill whose bounding box
    they mostly fill, bounded by a visible edge. CSS px (the capture is 2x)."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage as ndi
    im = Image.open(png).convert("RGB")
    a = np.asarray(im.resize((im.width // 2, im.height // 2), Image.BILINEAR)).astype(np.int16)
    H, W, _ = a.shape
    # a fill region = pixels whose 4-neighbours are within a small colour step (flat), labelled by quantised colour
    flat = np.ones((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        d = np.abs(a - np.roll(a, (dy, dx), (0, 1))).sum(-1)
        flat &= d < 10
    q = (a // 6).astype(np.int32)
    key = (q[..., 0] * 64 + q[..., 1]) * 64 + q[..., 2]
    boxes = []
    for v in np.unique(key[flat]):
        m = flat & (key == v)
        if m.sum() < min_area:
            continue
        lab, n = ndi.label(m)
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            if sl is None:
                continue
            h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            area = (lab[sl] == i).sum()
            if h * w < min_area or w * h > max_frac * W * H or w < 40 or h < 24:
                continue
            fill = area / (h * w)
            if fill < 0.55:          # a card's own fill covers most of its box (its text is the rest)
                continue
            # it is a CARD only if its edge is visible: the ring just outside differs from its fill
            y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
            ring = np.concatenate([a[max(0, y0 - 2), x0:x1], a[min(H - 1, y1 + 1), x0:x1], a[y0:y1, max(0, x0 - 2)], a[y0:y1, min(W - 1, x1 + 1)]])
            inner = a[(y0 + y1) // 2, (x0 + x1) // 2]
            if np.abs(ring - a[y0 + 1, x0 + w // 2]).sum(-1).mean() < 6:
                continue
            boxes.append({"x": int(x0), "y": int(y0), "w": int(w), "h": int(h), "fill": "#%02x%02x%02x" % tuple(int(c) for c in a[y0 + 1, x0 + w // 2]),
                          "score": round(float(fill), 2)})
            del inner
    # drop near-duplicates (keep the larger)
    boxes.sort(key=lambda b: -b["w"] * b["h"])
    kept = []
    for b in boxes:
        if any(abs(b["x"] - k["x"]) < 6 and abs(b["y"] - k["y"]) < 6 and abs(b["w"] - k["w"]) < 12 and abs(b["h"] - k["h"]) < 12 for k in kept):
            continue
        kept.append(b)
    kept.sort(key=lambda b: (b["y"], b["x"]))
    for i, b in enumerate(kept):
        b["id"] = i
    return {"src": png, "w": W, "h": H, "elements": kept}


def cut_mark(png, box, out_png):
    """The logo as the page draws it, cut out (CSS box on a 2x capture) with its flat ground keyed to alpha, so the
    same mark sits on a light or a dark ground. The ground is the box's border colour. Ink INTERIORS stay opaque at
    their own colour, whatever their tone (a mid-tone purple is ink, not a half-transparent black); only the
    anti-aliased rim is unmixed — its alpha is how far it sits from the ground toward the NEAREST interior colour,
    and its colour is that interior's, so the edge keeps no halo of the old ground."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage as ndi
    x, y, w, h = (int(round(v * 2)) for v in box)
    a = np.asarray(Image.open(png).convert("RGB").crop((x, y, x + w, y + h))).astype(float)
    edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(edge, 0)
    d = np.abs(a - bg).max(-1)
    ink = d > 24
    interior = ndi.binary_erosion(ink, iterations=2)
    if not interior.any():
        interior = ink
    if not interior.any():
        raise SystemExit("[promo_capture] the --box holds no mark: nothing in it differs from its ground %s" % bg.astype(int).tolist())
    _, (iy, ix) = ndi.distance_transform_edt(~interior, return_indices=True)
    C = a[iy, ix]                                           # the nearest interior (ink) colour, per pixel
    v = C - bg
    alpha = np.clip(((a - bg) * v).sum(-1) / np.maximum((v * v).sum(-1), 1e-6), 0, 1)
    alpha = np.where(interior, 1.0, np.where(d > 3, alpha, 0.0))
    rgb = np.where(interior[..., None], a, C)
    out = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(out_png)
    return {"w": w // 2, "h": h // 2, "aspect": round(w / h, 4), "ground": "#%02x%02x%02x" % tuple(int(c) for c in bg)}


def overlay(png, lay, out_jpg):
    from PIL import Image, ImageDraw
    im = Image.open(png).convert("RGB")
    im = im.resize((lay["w"], lay["h"]), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for x in range(0, lay["w"], 50):
        d.line([(x, 0), (x, lay["h"])], fill=(200, 220, 255) if x % 100 else (150, 180, 255))
    for y in range(0, lay["h"], 50):
        d.line([(0, y), (lay["w"], y)], fill=(200, 220, 255) if y % 100 else (150, 180, 255))
    for e in lay["elements"]:
        d.rectangle([e["x"], e["y"], e["x"] + e["w"], e["y"] + e["h"]], outline=(230, 40, 120), width=2)
        d.rectangle([e["x"], e["y"], e["x"] + 26, e["y"] + 14], fill=(230, 40, 120))
        d.text((e["x"] + 3, e["y"] + 1), str(e["id"]), fill="white")
    im.save(out_jpg, quality=85)


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__.strip().splitlines()[0])
        return 2
    refuse_unknown(argv[1:], valued=("name", "width", "height", "wait", "eval", "select", "max", "boxes", "mark", "box", "hires"), switches=("full",))
    film = os.path.abspath(argv[0])
    mk = argflag(argv, "mark", None)
    if mk:
        box = [float(v) for v in (argflag(argv, "box", "") or "").split(",") if v.strip()]
        if len(box) != 4:
            print("[promo_capture] --mark needs --box=x,y,w,h (CSS px of the capture)")
            return 2
        os.makedirs(os.path.join(film, "brand"), exist_ok=True)
        out = os.path.join(film, "brand", argflag(argv, "name", "mark") + ".png")
        info = cut_mark(mk if os.path.isabs(mk) else os.path.join(film, mk), box, out)
        print("[promo_capture] %s: aspect %.3f (use as the shot's `aspect`), ground %s keyed out" % (os.path.relpath(out, film), info["aspect"], info["ground"]))
        return 0
    bx = argflag(argv, "boxes", None)
    if bx:
        png = bx if os.path.isabs(bx) else os.path.join(film, bx)
        lay = find_boxes(png)
        lay["src"] = os.path.relpath(png, film)
        base = os.path.splitext(png)[0]
        json.dump(lay, open(base + ".layout.json", "w"), indent=1)
        overlay(png, lay, base + ".boxes.jpg")
        print("[promo_capture] %d boxes -> %s.layout.json (look at %s.boxes.jpg)" % (len(lay["elements"]), base, base))
        return 0
    if len(argv) < 2 or argv[1].startswith("-"):
        print("[promo_capture] needs a url (or --boxes=<png>)")
        return 2
    sel = [s for s in (argflag(argv, "select", "") or "").split(",") if s.strip()]
    lay = capture_web(film, argv[1], argflag(argv, "name", "page"), int(argflag(argv, "width", 1440)), int(argflag(argv, "height", 900)),
                      "--full" in argv, float(argflag(argv, "wait", 1.5)), argflag(argv, "eval", None), sel, int(argflag(argv, "max", 80)),
                      argflag(argv, "hires", None))
    print("[promo_capture] %s: %dx%d CSS, %d elements -> caps/%s.layout.json" % (lay["src"], lay["w"], lay["h"], len(lay["elements"]),
                                                                               argflag(argv, "name", "page")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
