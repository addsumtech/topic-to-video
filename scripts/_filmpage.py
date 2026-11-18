"""_filmpage — load a director-path film page (film.html) the way every frame tool must: served over local http (WebGL
textures need same-origin loads), headless Chrome with the GPU, the page READY before frame 0.

READY means, in order: the document loaded; `window.filmReady` (when the page defines it) resolved to "ok" (anything
starting "ERR" or a rejection fails loudly); every FontFace loaded (`document.fonts.ready`, and none in status
"error"); `window.seek` is a function. A page that draws canvas text before its fonts load draws it in a fallback font
in one render page and the real one in another (Grok Bot 2026-11-18: an arrow changed shape frame to frame), so the
fonts are part of ready, not an afterthought.
"""
import base64
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402
from _cdp import _WS  # noqa: E402


class PageError(RuntimeError):
    """The page could not be made ready (it threw, its filmReady failed, a font failed, no window.seek)."""


def serve(root):
    """Serve `root` on a free local port in a daemon thread. Returns (port, server)."""
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=root, **k)

        def log_message(self, *a):
            pass

    class TS(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
        allow_reuse_address = True
        # the default backlog (5) refuses connections when several pages load dozens of files at once: images then
        # fail to load at random (measured: cast PNGs 'failed' in 2 of 3 runs with two pages)
        request_queue_size = 256

    s = TS(("127.0.0.1", 0), H)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s.server_address[1], s


# Installed before the page's own scripts: records canvas text drawn while its font was not loaded yet. Such text is
# drawn in a fallback face, and whether the font was ready depends on each page's timing: the race that made an arrow
# change shape between render pages. Deterministic where a two-page probe only catches the race when it happens.
EARLY_TEXT_HOOK = r"""
(() => { const early = window.__earlyCanvasText = [];
  for (const C of [window.CanvasRenderingContext2D, window.OffscreenCanvasRenderingContext2D]) { if (!C) continue;
    for (const m of ['fillText', 'strokeText']) { const f = C.prototype[m];
      C.prototype[m] = function (txt) { try { if (document.fonts && !document.fonts.check(this.font, String(txt)) && early.length < 50)
        early.push(this.font + ' :: ' + String(txt).slice(0, 60)); } catch (e) {} return f.apply(this, arguments); }; } } })();
"""


class FilmPage:
    """One headless Chrome page on the film. `init_script` runs before any of the page's own scripts."""

    def __init__(self, port, page="film.html", W=1920, H=1080, init_script=None, timeout=300):
        self.prof = tempfile.mkdtemp(prefix="filmpage_")
        self.n = 0
        self.proc = subprocess.Popen(
            [_c.find_chrome(), "--headless=new", "--hide-scrollbars", "--no-sandbox", "--use-angle=metal",
             "--ignore-gpu-blocklist", "--remote-debugging-port=0", "--user-data-dir=" + self.prof,
             "--window-size=%d,%d" % (W, H), "--force-device-scale-factor=1", "about:blank"],
            stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 60
            while True:
                line = self.proc.stderr.readline().decode("utf-8", "replace")
                m = re.search(r"ws://([\d.]+):(\d+)(/devtools/\S+)", line)
                if m:
                    break
                if (not line and self.proc.poll() is not None) or time.monotonic() > deadline:
                    raise PageError("chrome exited before listening")
            self.ws = _WS(m.group(1), int(m.group(2)), m.group(3), timeout)
            tgt = self.cmd("Target.createTarget", {"url": "about:blank"})["result"]["targetId"]
            self.sid = self.cmd("Target.attachToTarget", {"targetId": tgt, "flatten": True})["result"]["sessionId"]
            self.cmd("Emulation.setDeviceMetricsOverride", {"width": W, "height": H, "deviceScaleFactor": 1,
                                                            "mobile": False}, self.sid)
            self.cmd("Page.enable", {}, self.sid)
            self.cmd("Page.addScriptToEvaluateOnNewDocument", {"source": EARLY_TEXT_HOOK}, self.sid)
            if init_script:
                self.cmd("Page.addScriptToEvaluateOnNewDocument", {"source": init_script}, self.sid)
            self.cmd("Page.navigate", {"url": "http://127.0.0.1:%d/%s" % (port, page)}, self.sid)
            self._ready()
        except Exception:
            self.close()
            raise

    def _ready(self):
        for _ in range(1200):
            if self.ev("document.readyState") == "complete":
                break
            time.sleep(0.05)
        else:
            raise PageError("the page never finished loading")
        v = self.ev("(async () => { try { if (window.filmReady === undefined) return 'ok';"
                    " const r = await window.filmReady; return r === undefined ? 'ok' : String(r); }"
                    " catch (e) { return 'ERR ' + (e && e.stack || e); } })()", True)
        if v != "ok" and not (isinstance(v, str) and not v.startswith("ERR") and v.strip()):
            raise PageError("window.filmReady failed: %s" % v)
        bad = self.ev("(async () => { await document.fonts.ready;"
                      " return [...document.fonts].filter(f => f.status === 'error').map(f => f.family + ' ' + f.weight); })()", True)
        if bad:
            raise PageError("font(s) failed to load: %s (canvas/DOM text would fall back per page)" % ", ".join(bad))
        early = self.ev("window.__earlyCanvasText || []")
        if early:
            raise PageError("canvas text was drawn before its font loaded (it falls back to another face, differently in "
                            "each render page): %s. Draw it after `await document.fonts.load(...)`, e.g. in filmReady"
                            % "; ".join(sorted(set(early))[:5]))
        if self.ev("typeof window.seek") != "function":
            raise PageError("the page has no window.seek(t) (did its scripts load and run? a script that fails to load "
                            "or throws leaves no seek)")

    def cmd(self, method, params=None, sid=None):
        self.n += 1
        msg = {"id": self.n, "method": method, "params": params or {}}
        if sid:
            msg["sessionId"] = sid
        self.ws.send(msg)
        while True:
            r = self.ws.recv()
            if r.get("id") == self.n:
                if "error" in r:
                    raise PageError("%s: %s" % (method, r["error"]))
                return r

    def ev(self, expr, aw=False):
        r = self.cmd("Runtime.evaluate", {"expression": expr, "awaitPromise": aw, "returnByValue": True}, self.sid)
        res = r["result"]
        if "exceptionDetails" in res:
            raise PageError(json.dumps(res["exceptionDetails"])[:1500])
        return res["result"].get("value")

    def seek(self, t):
        """seek(t), await it when it returns a promise, then two animation frames so the picture is presented."""
        self.ev("(async () => { const r = window.seek(%r); if (r && r.then) await r;"
                " await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); })()" % float(t), True)

    def shot(self, path, fmt="jpeg", quality=95):
        p = {"format": fmt}
        if fmt == "jpeg":
            p["quality"] = quality
        d = self.cmd("Page.captureScreenshot", p, self.sid)["result"]["data"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(d))

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(10)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        shutil.rmtree(self.prof, ignore_errors=True)


def film_frames_count(film_dir, fps):
    """Frames in the film: _plan.json "frames", else timeline.json "duration" x fps. None when neither exists."""
    plan = os.path.join(film_dir, "_plan.json")
    if os.path.isfile(plan):
        n = json.load(open(plan, encoding="utf-8")).get("frames")
        if n:
            return int(n)
    tl = os.path.join(film_dir, "timeline.json")
    if os.path.isfile(tl):
        d = json.load(open(tl, encoding="utf-8")).get("duration")
        if d:
            return int(round(float(d) * fps))
    return None
