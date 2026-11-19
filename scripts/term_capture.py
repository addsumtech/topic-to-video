#!/usr/bin/env python3
"""term_capture — what a terminal program REALLY shows, captured cell by cell, for a film's terminal screens.

    python3 scripts/term_capture.py --out cap.json [--cols 100] [--rows 30] [--cwd DIR] [--wait 6]
        [--keys '[[3, "\\u001b[B"], [3.5, "\\r"]]'] [--type "help me find roles" --type-at 7 --type-every 0.06]
        [--replace "Claude Pro=>Claude Max"] [--keep-env] -- claude --permission-mode default

Runs the command in a pseudo-terminal of cols x rows (a clean environment: HOME, PATH, LANG, TERM=xterm-256color,
COLORTERM=truecolor, nothing of the session that runs this script), presses `--keys` at their times, and keeps the
screen it shows: one frame at the end, and with `--type`, one frame after each character typed (never Enter: nothing
is sent to anyone). It refuses to write a capture that still shows your home path or login name (the program may
shorten a path, e.g. "/…/-Users-name/…": replace what it shows). Each frame is the grid itself: every cell's character, its colours (truecolor hex or an ANSI
name), bold / italic / underline / reverse, and the cursor. `--replace "A=>B"` swaps account-specific text (a plan
name, a path, an email) in every frame, cell for cell; the run fails if a replacement does not fit where A was.
Stage3D.terminal(frame, {...}) draws a frame as markup for Stage3D.screen (assets/html/stage3d/screens.js).

WHY. A film's Claude Code window was written from memory: an old "Welcome to Claude Code!" box, a rounded input box,
"? for shortcuts", none of it what the program shows today (job-hunt film, 2026-11-19; the user: "终端窗口模拟的并不
真实"). A terminal is a grid of characters the program itself draws, so the real thing can be recorded exactly instead
of imitated: the same characters, the same colours, the same layout, at the size the film uses.

Before a program will show its main screen it may ask something first (Claude Code asks whether to trust a new
folder): answer it with `--keys`, or run it in a folder it already trusts and `--replace` the path.
Exit 0 written, 2 usage, the command could not start, or a replacement did not fit.
"""
import json
import os
import pty
import re
import select
import signal
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

_USAGE = __doc__.strip().splitlines()[2].strip()
# kitty keyboard-protocol and other private queries pyte does not parse (it printed their final byte as text)
_PRIVATE = re.compile(rb"\x1b\[[<>=?][0-9;]*[uqc]")


def _screen(cols, rows, fd):
    import pyte

    class Screen(pyte.Screen):
        def report_device_status(self, *a, **k):     # pyte rejects the private form (CSI ? 6 n) a TUI asks
            k.pop("private", None)
            return super().report_device_status(*a, **k)

        def write_process_input(self, data):          # answer the program's own queries (cursor position)
            os.write(fd, data.encode())

    return Screen(cols, rows)


def frame(scr, t):
    """The grid as rows of runs: [[text, {fg, bg, b, i, u, r}], ...]; wide characters are their own run with w: 2."""
    out = []
    for y in range(scr.lines):
        row, runs, x = scr.buffer[y], [], 0
        while x < scr.columns:
            c = row[x]
            st = {"fg": c.fg, "bg": c.bg}
            for k, a in (("b", "bold"), ("i", "italics"), ("u", "underscore"), ("r", "reverse")):
                if getattr(c, a):
                    st[k] = 1
            wide = x + 1 < scr.columns and row[x + 1].data == "" and c.data != ""
            if wide:
                st["w"] = 2
            ch = c.data or " "
            if runs and runs[-1][1] == st and not wide and "w" not in runs[-1][1]:
                runs[-1][0] += ch
            else:
                runs.append([ch, st])
            x += 2 if wide else 1
        out.append(runs)
    return {"t": round(t, 3), "cursor": [scr.cursor.x, scr.cursor.y, 0 if scr.cursor.hidden else 1], "rows": out}


def _cells(runs):
    out = []
    for text, st in runs:
        if st.get("w"):
            out.append([text, st])
        else:
            out.extend([ch, dict(st)] for ch in text)
    return out


def _runs(cells):
    runs = []
    for ch, st in cells:
        if runs and runs[-1][1] == st and "w" not in st:
            runs[-1][0] += ch
        else:
            runs.append([ch, st])
    return runs


def replace(fr, pairs):
    """Swap each A for B in a frame's text, cell for cell, in the style A started with (B padded with spaces to A's
    width; B wider than A fails: the cells after it belong to something else)."""
    for a, b in pairs:
        if len(b) > len(a):
            raise ValueError("--replace %r=>%r: the new text is longer than the old; it would not fit its cells" % (a, b))
        b = b + " " * (len(a) - len(b))
        for y, runs in enumerate(fr["rows"]):
            cells = _cells(runs)
            line = "".join(c[0] for c in cells)
            i = line.find(a)
            while i >= 0:
                st = dict(cells[i][1])
                for k, ch in enumerate(b):
                    cells[i + k] = [ch, dict(st)]
                line = "".join(c[0] for c in cells)
                i = line.find(a, i + len(b))
            fr["rows"][y] = _runs(cells)
    return fr


def capture(cmd, cols=100, rows=30, cwd=None, wait=6.0, keys=(), typed="", type_at=None, type_every=0.06,
            keep_env=False):
    env = dict(os.environ) if keep_env else {k: os.environ[k] for k in ("HOME", "PATH", "LANG", "USER", "LOGNAME", "SHELL")
                                             if k in os.environ}
    env.update(TERM="xterm-256color", COLORTERM="truecolor", COLUMNS=str(cols), LINES=str(rows))
    if os.path.basename(cmd[0]) == "claude":
        # Claude Code counts a fullscreen launch that ends "before it was healthy" (a capture always does) as a crash,
        # and after two turns fullscreen off for every later session on the machine; this override skips that canary
        env["CLAUDE_CODE_NO_FLICKER"] = "1"
    env.setdefault("LANG", "en_US.UTF-8")
    pid, fd = pty.fork()
    if pid == 0:
        if cwd:
            os.chdir(cwd)
        try:
            os.execvpe(cmd[0], cmd, env)
        finally:
            os._exit(127)
    import fcntl
    import pyte
    import termios
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    scr = _screen(cols, rows, fd)
    stream = pyte.ByteStream(scr)
    events = sorted([(float(t), s, False) for t, s in keys] +
                    [((type_at if type_at is not None else wait) + i * type_every, ch, True) for i, ch in enumerate(typed)])
    end = max([wait] + [e[0] + 0.6 for e in events])
    frames, t0, ei, pending, typed_before = [], time.time(), 0, None, False

    def drain(timeout=0.02):
        """Feed everything the program has written so far (up to `timeout` s of waiting); False once it has exited."""
        while True:
            r, _, _ = select.select([fd], [], [], timeout)
            if not r:
                return True
            try:
                data = os.read(fd, 65536)
            except OSError:
                return False
            if not data:
                return False
            stream.feed(_PRIVATE.sub(b"", data))
            timeout = 0

    try:
        while True:
            now = time.time() - t0
            if now >= end:
                break
            if pending is not None and now >= pending:
                drain(0)
                frames.append(frame(scr, now))
                pending = None
            if ei < len(events) and now >= events[ei][0]:
                if events[ei][2] and typed_before:
                    drain(0)                       # the screen with the last character drawn: a full interval after it
                    frames.append(frame(scr, now))
                os.write(fd, events[ei][1].encode())
                if events[ei][2]:
                    typed_before = True
                    if not any(e[2] for e in events[ei + 1:]):
                        pending = now + type_every     # after the last character, the same interval
                ei += 1
            if not drain(0.02):
                break
        frames.append(frame(scr, time.time() - t0))
    finally:
        # leave the way a person would (Ctrl-C twice), and only then by signal
        for sig in (None, None, signal.SIGTERM, signal.SIGKILL):
            try:
                if sig is None:
                    os.write(fd, b"\x03")
                else:
                    os.kill(pid, sig)
                end = time.time() + 1.0
                while time.time() < end:
                    if os.waitpid(pid, os.WNOHANG)[0]:
                        return frames
                    time.sleep(0.05)
            except (OSError, ChildProcessError):
                return frames
    return frames


def main(argv):
    if "--" not in argv:
        print(_USAGE, file=sys.stderr)
        return 2
    i = argv.index("--")
    opts, cmd = argv[:i], argv[i + 1:]
    _c.refuse_unknown(opts, valued=("out", "cols", "rows", "cwd", "wait", "keys", "type", "type-at", "type-every", "replace"),
                      switches=("keep-env", "allow-private"), usage=_USAGE)
    out = _c.argflag(opts, "out")
    if not out or not cmd:
        print(_USAGE, file=sys.stderr)
        return 2
    pairs = []
    for k, a in enumerate(opts):     # --replace may repeat
        v = a.split("=", 1)[1] if a.startswith("--replace=") else (opts[k + 1] if a == "--replace" and k + 1 < len(opts) else None)
        if v is not None:
            if "=>" not in v:
                print("term_capture: --replace takes OLD=>NEW", file=sys.stderr)
                return 2
            pairs.append(tuple(v.split("=>", 1)))
    cols, rows = int(_c.argflag(opts, "cols", 100)), int(_c.argflag(opts, "rows", 30))
    try:
        frames = capture(cmd, cols, rows, _c.argflag(opts, "cwd"), float(_c.argflag(opts, "wait", 6)),
                         json.loads(_c.argflag(opts, "keys", "[]")), _c.argflag(opts, "type", ""),
                         None if _c.argflag(opts, "type-at") is None else float(_c.argflag(opts, "type-at")),
                         float(_c.argflag(opts, "type-every", 0.06)), "--keep-env" in opts)
        frames = [replace(f, pairs) for f in frames]
    except (OSError, ValueError) as e:
        print("term_capture: %s" % e, file=sys.stderr)
        return 2
    # nothing of the person running this goes into a film: their home path, their login name
    # (a login name also by its first five letters: a program cuts a long path mid-name, "-Users-dongh…")
    names = {os.environ.get("USER", ""), os.environ.get("LOGNAME", "")}
    private = [x for x in {os.path.expanduser("~")} | names | {n[:5] for n in names if len(n) >= 5} if len(x) > 2]
    hits = sorted({(x, k) for k, f in enumerate(frames) for runs in f["rows"] for x in private if x in "".join(r[0] for r in runs)})
    if hits and "--allow-private" not in opts:
        print("term_capture: frame(s) %s show %s; --replace it (the program may shorten a path: replace what it shows)"
              % (sorted({k for _, k in hits}), sorted({x for x, _ in hits})), file=sys.stderr)
        print("\n".join("".join(r[0] for r in runs).rstrip() for runs in frames[-1]["rows"]).strip("\n"), file=sys.stderr)
        return 2
    text = "\n".join("".join(r[0] for r in runs).rstrip() for runs in frames[-1]["rows"]).strip("\n")
    if not text:
        print("term_capture: the program drew nothing in %s s (did it start? is --wait long enough?)" % _c.argflag(opts, "wait", 6),
              file=sys.stderr)
        return 2
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"cols": cols, "rows": rows, "cmd": cmd, "frames": frames}, f, ensure_ascii=False)
    print(text)
    print("[term_capture] %d frame(s) of %dx%d -> %s" % (len(frames), cols, rows, out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
