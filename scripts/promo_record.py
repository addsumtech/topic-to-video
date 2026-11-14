#!/usr/bin/env python3
"""promo_record — the product IN MOTION: a deterministic 2x recording of a web page acting out a script.

    python3 scripts/promo_record.py <film_dir> <url> --name=rec --seconds=6 [--script=steps.json] [--setup="js"]
                                    [--width=1440] [--height=900] [--fps=30] [--wait=2]

A capture (promo_capture) is the product still; this is the product doing something — a field filling, a panel
opening, a result arriving with the page's OWN animation. After load (and `--setup`), the time the page can see is
replaced by a clock the recorder advances exactly 1/fps s per frame: performance.now, Date, timers and
requestAnimationFrame run on it, and every CSS transition / animation is pinned to it. Each frame is screenshotted at
deviceScaleFactor 2 and the script's actions fire on their frames. So the recording is frame-exact and the same every
run, however slow the machine.

script (JSON list, times in seconds of the recording):
  {"t": 0.6, "click": "button.primary"}            a CSS selector (its centre) or [x, y] in CSS px
  {"t": 1.0, "type": "a sentence", "into": "input", "cps": 18}   typed key by key into a field (focus by click)
  {"t": 2.0, "scroll": [0, 400], "dur": 0.6}      scroll the window, eased over `dur` s (or {"el": "selector", "by": [0, 400]})
  {"t": 2.5, "eval": "document.body.classList.add('x')"}   not awaited (a page timer it waits on runs on the frame clock): async work -> --setup
  {"t": 3.0, "hover": "selector"}
  {"t": 3.5, "drag": [[x0, y0], [x1, y1]], "dur": 0.8}   press, move smoothly (eased) over `dur` s, release

Writes caps/<name>.mp4 (2x, `fps`), caps/<name>.png (its first frame, the poster) and caps/<name>.layout.json — the
first frame's elements as promo_capture lists them, plus `events`: every click / keystroke run with its FRAME and
place, so the film can lay its own cursor over the recording on the same frames (headless Chrome draws no pointer).
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import argflag, refuse_unknown, find_chrome  # noqa: E402
import promo_capture as pc  # noqa: E402


class _Session:
    """A CDP session that KEEPS the events it reads."""

    def __init__(self, chrome):
        self.c = chrome
        self.events = []

    def cmd(self, method, params=None):
        c = self.c
        c._id += 1
        i = c._id
        c.ws.send({"id": i, "method": method, "params": params or {}, "sessionId": c.sid})
        while True:
            m = c.ws.recv()
            if m.get("id") == i:
                if "error" in m:
                    raise SystemExit("[promo_record] %s failed: %s" % (method, m["error"]))
                return m.get("result", {})
            if "method" in m:
                self.events.append(m)

    def wait(self, method, timeout=30.0):
        for k, e in enumerate(self.events):
            if e.get("method") == method:
                return self.events.pop(k)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            m = self.c.ws.recv()
            if m.get("method") == method:
                return m
            if "method" in m:
                self.events.append(m)
        raise SystemExit("[promo_record] no %s within %.0f s" % (method, timeout))

    def js(self, expr, wait=True):
        """`wait=False` for anything run inside the frame loop: a promise there may settle only on frames not advanced
        yet (a page timer, a scrollTo), so awaiting it would hang."""
        r = self.cmd("Runtime.evaluate", {"expression": expr, "awaitPromise": wait, "returnByValue": True})
        if r.get("exceptionDetails"):
            raise SystemExit("[promo_record] script step threw: %s" % (r["exceptionDetails"].get("exception", {}).get("description")
                                                                     or r["exceptionDetails"].get("text")))
        return (r.get("result") or {}).get("value")


# THE PAGE'S CLOCK IS OURS. Chrome's virtual time was the first design: pause it, advance 1/fps a frame. Measured, a
# still page under budgets under ~100 ms produced NO new frame and captureScreenshot waited forever — 30 fps never
# recorded (it had passed only on pages that never stop animating, and at 10 fps). So the page renders in real time,
# and the time it can SEE is replaced: performance.now, Date, setTimeout/setInterval and requestAnimationFrame run on
# `__vt`, which the recorder advances by exactly 1000/fps ms per frame (due timers in order, then one rAF round).
# CSS transitions/animations are pinned separately (ANIM_JS). Work that waits on the network or a worker still
# finishes in real time, so it lands on whichever frame is next.
CLOCK_JS = """(()=>{ if (window.__vt) return 0;
const rNow = performance.now.bind(performance), RD = Date, rST = window.setTimeout.bind(window), rCT = window.clearTimeout.bind(window),
      rCI = window.clearInterval.bind(window), rCAF = window.cancelAnimationFrame.bind(window);
const base = rNow(), dbase = RD.now();
const V = window.__vt = {t: base, timers: [], id: 1e9, raf: [], rid: 1e9};
const wall = () => dbase + (V.t - base);
performance.now = () => V.t;
class VDate extends RD { constructor(...a) { if (a.length) super(...a); else super(wall()); } static now() { return wall(); } }
window.Date = VDate;
window.setTimeout = (fn, ms, ...args) => { const id = V.id++; V.timers.push({id, at: V.t + Math.max(0, +ms || 0), fn, args}); return id; };
window.setInterval = (fn, ms, ...args) => { const e = Math.max(1, +ms || 0), id = V.id++; V.timers.push({id, at: V.t + e, fn, args, every: e}); return id; };
window.clearTimeout = (id) => { if (id >= 1e9) V.timers = V.timers.filter(x => x.id !== id); else rCT(id); };
window.clearInterval = (id) => { if (id >= 1e9) V.timers = V.timers.filter(x => x.id !== id); else rCI(id); };
window.requestAnimationFrame = (fn) => { const id = V.rid++; V.raf.push({id, fn}); return id; };
window.cancelAnimationFrame = (id) => { if (id >= 1e9) V.raf = V.raf.filter(x => x.id !== id); else rCAF(id); };
const call = (f, args) => { try { typeof f === 'function' ? f(...args) : (0, eval)(String(f)); } catch (e) { console.error(e); } };
V.advance = (ms) => {
  const end = V.t + ms;
  for (let guard = 0; guard < 20000; guard++) {
    let n = null;
    for (const x of V.timers) if (x.at <= end && (!n || x.at < n.at || (x.at === n.at && x.id < n.id))) n = x;
    if (!n) break;
    V.t = Math.max(V.t, n.at);
    if (n.every) n.at += n.every; else V.timers = V.timers.filter(x => x !== n);
    call(n.fn, n.args);
  }
  V.t = end;
  const cbs = V.raf; V.raf = [];
  for (const c of cbs) call(c.fn, [V.t]);
  return 0;
};
return 1; })()"""

ANIM_JS = """(()=>{const vt=%f; const seen=window.__recAnims||(window.__recAnims=new WeakMap());
for (const a of document.getAnimations()) {
  if (!seen.has(a)) seen.set(a, vt - (a.currentTime || 0));
  try { a.pause(); a.currentTime = vt - seen.get(a); } catch (e) {}
}})()"""


def _centre(s, target):
    if isinstance(target, (list, tuple)):
        return float(target[0]), float(target[1])
    r = s.js("(()=>{const e=document.querySelector(%s); if(!e) return null; const b=e.getBoundingClientRect();"
             " return [b.left+b.width/2, b.top+b.height/2];})()" % json.dumps(target))
    if not r:
        raise SystemExit("[promo_record] nothing on the page matches %r" % target)
    return float(r[0]), float(r[1])


def _click(s, x, y):
    for t in ("mouseMoved", "mousePressed", "mouseReleased"):
        s.cmd("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1})


def record(film, url, name, seconds=6.0, script=(), setup=None, W=1440, H=900, fps=30, wait=2.0):
    chrome = find_chrome()
    if not chrome:
        raise SystemExit("[promo_record] no Chrome/Chromium found")
    import _cdp
    caps = os.path.join(film, "caps")
    os.makedirs(caps, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="promo_rec_")
    n = int(round(seconds * fps))
    events_out = []
    with _cdp.Chrome(chrome, W, H, device_scale=2, timeout=90) as c:
        s = _Session(c)
        s.cmd("Page.navigate", {"url": url})
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and s.js("document.readyState") != "complete":
            time.sleep(0.05)
        s.js("Promise.race([document.fonts ? document.fonts.ready.then(()=>1) : 1, new Promise(r=>setTimeout(()=>r(0), 8000))])")
        time.sleep(wait)
        if setup:
            for step in pc.split_steps(setup):
                s.js(step)
                time.sleep(wait)
        lay = s.js(pc.ELEMENTS_JS % json.dumps([]))
        # the clock stops here: from now on the page moves only when we advance it, one frame at a time
        s.js(CLOCK_JS)
        todo = sorted(script, key=lambda st: float(st.get("t", 0)))
        typing = []                                   # [(frame, char)] pending keystrokes
        drags = []                                    # [(frame, type, x, y)] pending pointer moves of a drag
        scrolls = []                                  # [(frame, target js, x, y)] pending scroll positions
        for k in range(n):
            t = k / fps
            if k:
                s.js("window.__vt.advance(%r)" % (1000.0 / fps), wait=False)     # timers due, then one rAF round
            while todo and float(todo[0].get("t", 0)) <= t:
                st = todo.pop(0)
                if "click" in st or "hover" in st:
                    x, y = _centre(s, st.get("click", st.get("hover")))
                    if "click" in st:
                        _click(s, x, y)
                        events_out.append({"frame": k, "kind": "click", "x": x, "y": y})
                    else:
                        s.cmd("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
                        events_out.append({"frame": k, "kind": "hover", "x": x, "y": y})
                elif "type" in st:
                    if st.get("into"):
                        x, y = _centre(s, st["into"])
                        _click(s, x, y)
                        events_out.append({"frame": k, "kind": "click", "x": x, "y": y})
                    cps = float(st.get("cps", 18))
                    for j, ch in enumerate(str(st["type"])):
                        typing.append((k + int(round(j * fps / cps)), ch))
                    events_out.append({"frame": k, "kind": "type", "text": st["type"],
                                       "until": k + int(round(len(str(st["type"])) * fps / cps))})
                elif "scroll" in st or ("el" in st and "by" in st):
                    # scrolled BY US, frame by frame on an eased curve: a smooth scrollBy runs on the compositor, off the
                    # frame clock (and under the first, virtual-time design its promise never settled: it hung)
                    by = st["scroll"] if "scroll" in st else st["by"]
                    el = st.get("el")
                    tgt = "document.querySelector(%s)" % json.dumps(el) if el else "document.scrollingElement"
                    x0, y0 = s.js("(()=>{const e=%s; if(!e) return null; return [e.scrollLeft, e.scrollTop];})()" % tgt) or (None, None)
                    if x0 is None:
                        raise SystemExit("[promo_record] nothing on the page matches %r to scroll" % el)
                    m = max(2, int(round(float(st.get("dur", 0.6)) * fps)))
                    for j in range(1, m + 1):
                        u = j / m
                        e = u * u * (3 - 2 * u)
                        scrolls.append((k + j - 1, tgt, x0 + by[0] * e, y0 + by[1] * e))
                    ev = {"frame": k, "kind": "scroll", "by": list(by), "until": k + m - 1}
                    if el:
                        ev["el"] = el
                    events_out.append(ev)
                elif "drag" in st:
                    (x0, y0), (x1, y1) = st["drag"]
                    m = max(2, int(round(float(st.get("dur", 0.8)) * fps)))
                    drags.append((k, "mousePressed", x0, y0))
                    for j in range(1, m + 1):
                        u = j / m
                        e = u * u * (3 - 2 * u)               # eased: a hand starts and stops gently
                        drags.append((k + j, "mouseMoved", x0 + (x1 - x0) * e, y0 + (y1 - y0) * e))
                    drags.append((k + m, "mouseReleased", x1, y1))
                    events_out.append({"frame": k, "kind": "drag", "from": [x0, y0], "to": [x1, y1], "until": k + m})
                elif "eval" in st:
                    s.js(st["eval"], wait=False)
                    events_out.append({"frame": k, "kind": "eval"})
            for f_, typ, x_, y_ in [d for d in drags if d[0] == k]:
                s.cmd("Input.dispatchMouseEvent", {"type": typ, "x": x_, "y": y_, "button": "left", "buttons": 1 if typ != "mouseReleased" else 0,
                                                   "clickCount": 1 if typ != "mouseMoved" else 0})
            drags = [d for d in drags if d[0] > k]
            for f_, tg, x_, y_ in [d for d in scrolls if d[0] == k]:
                # wrapped: scrollTo returns a promise in current Chrome that settles on a later frame — awaited, it hangs
                s.js("(()=>{%s.scrollTo({left:%s, top:%s, behavior:'instant'}); return 0;})()" % (tg, round(x_, 2), round(y_, 2)))
            scrolls = [d for d in scrolls if d[0] > k]
            for ch in [c_ for f_, c_ in typing if f_ == k]:
                s.cmd("Input.insertText", {"text": ch})
            typing = [(f_, c_) for f_, c_ in typing if f_ > k]
            # CSS transitions/animations and element.animate() are put on the frame clock BY HAND: each is paused and set
            # to (now - when it was first seen). Left to Chrome, a transform/opacity animation runs on the compositor
            # thread, on its own clock (measured under virtual time: a 0.5 s transform transition sampled at 2/3 its
            # pace and then snapping to its end, its first frame different run to run).
            s.js(ANIM_JS % (k * 1000.0 / fps))
            # JPEG at 95: a 2x PNG per frame took ~2 s on a heavy page; the encode below is the quality bottleneck anyway
            shot = s.cmd("Page.captureScreenshot", {"format": "jpeg", "quality": 95})["data"]
            with open(os.path.join(tmp, "f%05d.jpg" % k), "wb") as fh:
                fh.write(base64.b64decode(shot))
            if k % 30 == 0:
                print("[promo_record] %d / %d frames" % (k, n), flush=True)
    mp4 = os.path.join(caps, name + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(tmp, "f%05d.jpg"), "-c:v", "libx264",
                    "-crf", "14", "-pix_fmt", "yuv420p", "-preset", "slow", mp4], check=True)
    import shutil
    Image_ = __import__("PIL.Image", fromlist=["Image"])
    Image_.open(os.path.join(tmp, "f00000.jpg")).save(os.path.join(caps, name + ".png"))
    from PIL import Image
    with Image.open(os.path.join(caps, name + ".png")) as im:
        pw, ph = im.size
    els = [e for e in lay["elements"] if e["x"] >= 0 and e["y"] >= 0 and e["x"] + e["w"] <= pw / 2 + 1 and e["y"] + e["h"] <= ph / 2 + 1]
    els.sort(key=lambda e: (e["y"], e["x"]))
    for i, e in enumerate(els):
        e["id"] = i
    out = {"src": "caps/%s.png" % name, "video": "caps/%s.mp4" % name, "w": pw // 2, "h": ph // 2, "fps": fps, "frames": n,
           "url": url, "title": lay.get("title", ""), "description": lay.get("description", ""), "elements": els, "events": events_out}
    json.dump(out, open(os.path.join(caps, name + ".layout.json"), "w"), indent=1)
    pc.overlay(os.path.join(caps, name + ".png"), out, os.path.join(caps, name + ".boxes.jpg"))
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def main(argv):
    if len(argv) < 2 or argv[0].startswith("-"):
        print(__doc__.strip())
        return 0 if argv[:1] in (["--help"], ["-h"]) else 2
    refuse_unknown(argv[2:], valued=("name", "seconds", "script", "setup", "width", "height", "fps", "wait"))
    film = os.path.abspath(argv[0])
    sp = argflag(argv, "script", None)
    script = json.load(open(sp if os.path.isabs(sp) else os.path.join(film, sp))) if sp else []
    out = record(film, argv[1], argflag(argv, "name", "rec"), float(argflag(argv, "seconds", 6)), script, argflag(argv, "setup", None),
                 int(argflag(argv, "width", 1440)), int(argflag(argv, "height", 900)), int(argflag(argv, "fps", 30)), float(argflag(argv, "wait", 2)))
    print("[promo_record] %s: %d frames at %d fps, %d event(s) -> caps/%s.layout.json" % (out["video"], out["frames"], out["fps"],
                                                                                       len(out["events"]), argflag(argv, "name", "rec")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
