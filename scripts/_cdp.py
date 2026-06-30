"""Minimal Chrome DevTools Protocol client (stdlib only) for FAST frame capture.

The `--screenshot` CLI launches a fresh headless Chrome per frame (~seconds of cold-start each) — the
render bottleneck. This drives ONE persistent headless Chrome and screenshots many frames over a
WebSocket, as JPEG (≈7x faster to encode+transfer than PNG). One launch + N fast captures instead of
N cold launches.

No third-party deps: a tiny WebSocket client (RFC 6455 handshake + framing) over a stdlib socket.
Everything here is best-effort — callers MUST catch `CDPUnavailable` and fall back to the
`--screenshot` path, so a missing/old/edge-case Chrome never breaks a render.
"""
import socket, base64, os, json, struct, subprocess, re, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class CDPUnavailable(Exception):
    """CDP capture could not run (no Chrome, launch/connect failed, or a shot errored). The caller
    should fall back to the per-frame `--screenshot` path."""


class _WS:
    """A minimal text-frame WebSocket client. Server frames are unmasked; client frames are masked."""
    def __init__(self, host, port, path, timeout=30):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
                           "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise CDPUnavailable("websocket handshake closed")
            resp += chunk
        if b" 101 " not in resp.split(b"\r\n", 1)[0] + b" ":
            raise CDPUnavailable(f"websocket handshake failed: {resp[:80]!r}")
        self.buf = resp.split(b"\r\n\r\n", 1)[1]

    def _recvn(self, n):
        while len(self.buf) < n:
            c = self.sock.recv(1 << 20)
            if not c:
                raise CDPUnavailable("websocket closed mid-frame")
            self.buf += c
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, obj):
        p = json.dumps(obj).encode()
        h = bytearray([0x81])                       # FIN + text opcode
        n = len(p); m = os.urandom(4)
        if n < 126:
            h.append(0x80 | n)
        elif n < 65536:
            h.append(0x80 | 126); h += struct.pack(">H", n)
        else:
            h.append(0x80 | 127); h += struct.pack(">Q", n)
        h += m
        self.sock.sendall(bytes(h) + bytes(b ^ m[i & 3] for i, b in enumerate(p)))

    def recv(self):
        data = b""
        while True:
            b0, b1 = self._recvn(2)
            fin = b0 & 0x80; op = b0 & 0x0f; ln = b1 & 0x7f
            if ln == 126:
                ln = struct.unpack(">H", self._recvn(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._recvn(8))[0]
            payload = self._recvn(ln)
            if op == 0x8:
                raise CDPUnavailable("websocket close frame")
            if op in (0x9, 0xa):                     # ping/pong — ignore
                continue
            data += payload
            if fin:
                return json.loads(data)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class Chrome:
    """One persistent headless Chrome with a single attached page target. `shot()` navigates to a
    url and writes a JPEG screenshot. NOTE: no `--user-data-dir` (it hangs vs a running Chrome on
    macOS); `--headless=new` auto-isolates, and `--remote-debugging-port=0` picks a free port."""
    def __init__(self, chrome_bin, W, H, quality=90, timeout=30):
        self.quality = quality
        self.timeout = timeout
        self._id = 0
        self.proc = subprocess.Popen(
            [chrome_bin, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
             "--remote-debugging-port=0", f"--window-size={W},{H}", "about:blank"],
            stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
        host, port, path = self._read_endpoint()
        self.ws = _WS(host, port, path, timeout)
        tgt = self._cmd("Target.createTarget", {"url": "about:blank"})["result"]["targetId"]
        self.sid = self._cmd("Target.attachToTarget", {"targetId": tgt, "flatten": True})["result"]["sessionId"]
        self._cmd("Page.enable", {}, self.sid)

    def _read_endpoint(self):
        # Chrome prints "DevTools listening on ws://127.0.0.1:PORT/devtools/browser/GUID" to stderr.
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            line = self.proc.stderr.readline().decode("utf-8", "replace")
            if not line:
                if self.proc.poll() is not None:
                    raise CDPUnavailable("chrome exited before listening")
                continue
            m = re.search(r"ws://([\d.]+):(\d+)(/devtools/\S+)", line)
            if m:
                return m.group(1), int(m.group(2)), m.group(3)
        raise CDPUnavailable("timed out waiting for DevTools endpoint")

    def _cmd(self, method, params=None, sid=None):
        self._id += 1
        i = self._id
        msg = {"id": i, "method": method, "params": params or {}}
        if sid:
            msg["sessionId"] = sid
        self.ws.send(msg)
        while True:
            m = self.ws.recv()
            if m.get("id") == i:
                if "error" in m:
                    raise CDPUnavailable(f"{method} error: {m['error']}")
                return m

    def shot(self, url, out_path):
        self._cmd("Page.navigate", {"url": url}, self.sid)
        # wait for load (poll readyState — simpler than event bookkeeping), then a short settle so
        # fonts/paint land before the grab
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            r = self._cmd("Runtime.evaluate",
                          {"expression": "document.readyState", "returnByValue": True}, self.sid)
            if r.get("result", {}).get("result", {}).get("value") == "complete":
                break
            time.sleep(0.01)
        # let webfonts resolve so CJK glyphs aren't tofu in the first paint
        self._cmd("Runtime.evaluate",
                  {"expression": "document.fonts ? document.fonts.ready.then(()=>1) : 1",
                   "awaitPromise": True, "returnByValue": True}, self.sid)
        data = self._cmd("Page.captureScreenshot",
                         {"format": "jpeg", "quality": self.quality}, self.sid)["result"]["data"]
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(data))

    def close(self):
        try:
            self.ws.close()
        finally:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass


def capture(shots, copies, workdir, index, W, H, meta, label, chrome_bin, workers, progress):
    """Capture a scene's frames via persistent Chrome(s) as JPEG. `shots`=[(i,url)] captured fresh;
    `copies`=[(i,src_i)] held frames (cheap file copies). Returns the ffmpeg frame PATTERN
    (…_%04d.jpg). Raises CDPUnavailable on any failure so the caller can fall back to --screenshot.

    Each worker thread keeps its OWN persistent Chrome (thread-local) and reuses it across its
    shots, so K Chromes serve all frames. Chromes are launched lazily and all closed at the end."""
    import shutil
    if not chrome_bin:
        raise CDPUnavailable("no chrome binary")
    pat = os.path.join(workdir, f"scene_{index:02d}_%04d.jpg")
    os.makedirs(workdir, exist_ok=True)
    quality = int((meta or {}).get("jpeg_quality", 90))
    total = len(shots)
    workers = max(1, min(workers, total or 1))
    progress(0, total, label)

    tl = threading.local()
    chromes = []
    chromes_lock = threading.Lock()
    done = [0]
    done_lock = threading.Lock()

    def get_chrome():
        c = getattr(tl, "chrome", None)
        if c is None:
            c = Chrome(chrome_bin, W, H, quality=quality)
            tl.chrome = c
            with chromes_lock:
                chromes.append(c)
        return c

    def shoot(i, url):
        get_chrome().shot(url, pat % i)
        with done_lock:
            done[0] += 1
            progress(done[0], total, label)

    try:
        if workers <= 1:
            for i, url in shots:
                shoot(i, url)
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                for f in as_completed([ex.submit(shoot, i, url) for i, url in shots]):
                    f.result()                       # propagate the first failure
        for i, src_i in copies:
            shutil.copyfile(pat % src_i, pat % i)
    except CDPUnavailable:
        raise
    except Exception as e:                            # any unexpected error -> fall back
        raise CDPUnavailable(f"cdp capture failed: {e}")
    finally:
        for c in chromes:
            c.close()
    return pat
