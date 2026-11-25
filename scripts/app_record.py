#!/usr/bin/env python3
"""app_record — a desktop app's OPERATING STEPS, recorded for real: the app driven step by step with the real cursor,
its window recorded at its own pixels, every action logged with its time and place.

    python3 scripts/app_record.py <film_dir> <steps.json> [--name rec]

WHEN (SKILL.md step 6; the user, 2026-11-24): only for a film that must show HOW TO OPERATE an app — the steps a
viewer will repeat (this menu, this button, type this). A film that shows a product, what it looks like or what it
made, uses its real screenshots and captures, never a recording. A rebuilt UI is never a stand-in for operating
steps: the viewer has to see what they will really see.

steps.json:
  {"app": "Numbers", "window": [1440, 900],          # the app's front window is set to this size (points)
   "lead": 1.0, "tail": 1.5,                          # seconds held before the first and after the last step
   "steps": [{"click": [x, y]},                       # window points from its top-left
             {"click_text": "Chart", "nth": 1},       # the words on screen (OCR of the window, scripts/screen_text)
             {"menu": ["Insert", "Chart"]},           # a menu path, clicked item by item as a person would
             {"type": "Revenue", "cps": 9}, {"key": "cmd+a"},
             {"drag": [[x1, y1], [x2, y2]]}, {"move": [x, y]}, {"wait": 1.2},
             {"scroll": 10}]}                         # wheel lines under the cursor, positive toward the top (an
                                                      # app may scroll on its own: the Numbers chart insert did)
  Any step may carry "label" (what the narration calls it) and "ms" (the glide's length, default 650); a click or
  click_text step may carry "clicks": 2 (a double-click, e.g. into a chart's title) or 3, and "mods": "shift" (held
  through the click: shift-click extends a selection; Numbers ignores a synthetic drag-select, 2026-11-25).

A "menu" step is clicked as a person moves: down from the title, then across into each submenu (a straight glide
crossed the next title and opened THAT menu); an item its menu does not show is refused before anything is clicked.
With a menu step the window is placed under the menu bar at the screen's left and the recording grows to the screen's
top, so the menus are in the picture; action places are then in that region, not the window.

The cursor's every glide is logged too (rec.json "path"), so the edit can follow the pointer (a halo, E.cursor(t)).

OUTPUT <film_dir>/clips/<name>/: rec.mp4 (H.264, the window — or the region above — at its own pixels), frames/00001.jpg… (30 fps, for the
page: assets/html/screenrec.js) and rec.json — {fps, n, width, height (px), scale (px per point), window, app,
actions: [{i, kind, label, t, t_end, x, y, text (typed), clicks}] (seconds into rec.mp4, recording px), sync: {offset, confidence: the
share of actions that agree with it}}.

TIME. Each action is logged against the clock that started the recording; screencapture starts writing a little
later, so the log is aligned to the video by the video ITSELF: the offset at which the picture starts changing right
after the logged actions (searched over ±2 s) is applied. Exact on synthetic recordings; on a real one, look at the
click rings against the frames before building on them (the agreement figure is a hint, see align_offset).

NEEDS (macOS): Screen Recording and Accessibility for the terminal that runs this, and a process outside Claude
Code's command sandbox (inside it System Events answers 0 windows for every app; this stops and says so). Without Screen Recording it stops
before driving anything and says exactly where to turn it on; it never falls back to an imitation.
Exit 0 recorded; 2 a usage error, a missing permission, an app or step that could not be carried out.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_SWIFT = os.path.join(_HERE, "app_drive.swift")
_BIN_DIR = os.path.join(os.path.expanduser("~"), ".cache", "slides-to-video")
FPS = 30
KINDS = ("click", "click_text", "menu", "type", "key", "drag", "move", "scroll", "wait")
_USAGE = "usage: app_record.py <film_dir> <steps.json> [--name rec]"

PERMISSION_HELP = ("macOS has not given this terminal Screen Recording, so nothing can be recorded. Turn it on in "
                   "System Settings > Privacy & Security > Screen & System Audio Recording (add the terminal app with "
                   "+ if it is not listed), quit and reopen the terminal, and run this again. Turn it off again when "
                   "the recording is done if you prefer: it lets anything run from that terminal capture the screen.")


class RecordError(Exception):
    pass


# ── pure parts (tested without the permission) ─────────────────────────────────────────────────────────────────────
def check_steps(spec):
    """The steps file, validated: every problem at once, as sentences."""
    errs = []
    if not isinstance(spec, dict) or not isinstance(spec.get("app"), str) or not spec["app"].strip():
        return ["steps.json needs \"app\": the application's name, as in /Applications (\"Numbers\")"]
    w = spec.get("window")
    if w is not None and not (isinstance(w, list) and len(w) == 2 and all(isinstance(v, (int, float)) and v >= 400
                                                                            for v in w)):
        errs.append("\"window\" is [width, height] in points, each at least 400")
    steps = spec.get("steps")
    if not isinstance(steps, list) or not steps:
        return errs + ["\"steps\" is a list of at least one step"]
    for i, s in enumerate(steps, 1):
        kinds = [k for k in KINDS if isinstance(s, dict) and k in s]
        if len(kinds) != 1:
            errs.append("step %d: exactly one of %s, got %r" % (i, ", ".join(KINDS), s))
            continue
        k, v = kinds[0], s[kinds[0]]
        pt = lambda p: isinstance(p, list) and len(p) == 2 and all(isinstance(c, (int, float)) for c in p)  # noqa
        ok = {"click": pt(v), "move": pt(v), "drag": isinstance(v, list) and len(v) == 2 and all(pt(p) for p in v),
              "click_text": isinstance(v, str) and v.strip(), "type": isinstance(v, str) and v,
              "key": isinstance(v, str) and v.strip(), "wait": isinstance(v, (int, float)) and 0 < v <= 30,
              "scroll": isinstance(v, int) and not isinstance(v, bool) and v != 0 and abs(v) <= 60,
              "menu": isinstance(v, list) and len(v) >= 2 and all(isinstance(x, str) and x for x in v)}[k]
        if not ok:
            errs.append("step %d: %s has the wrong shape (%r)" % (i, k, v))
        if "clicks" in s and (k not in ("click", "click_text") or s["clicks"] not in (1, 2, 3)):
            errs.append("step %d: \"clicks\" is 1, 2 or 3, on a click or click_text step" % i)
        if "mods" in s and (k not in ("click", "click_text") or not isinstance(s["mods"], str) or not all(
                m in ("shift", "cmd", "alt", "option", "ctrl") for m in s["mods"].lower().split("+"))):
            errs.append("step %d: \"mods\" is e.g. \"shift\" or \"cmd+shift\", on a click or click_text step" % i)
    return errs


def align_offset(energy, fps, times, window=0.2, search=2.0):
    """The shift (s) that best lines the logged action times up with the video's frame-change energy, and how sure
    agreed: the share of actions that change the picture there at least half as much as anywhere in their own search.
    A HINT, not a proof: with a handful of actions, noise can agree too (measured: up to all 4 of 4 on random
    frames), so a low share is a warning and a high one still means "look at the click rings on the frames". Scored on the RISING EDGE (the change just after each shifted time minus the change just
    before it), so it lands where the app starts to answer, not anywhere inside a change longer than the window."""
    import numpy as np
    e = np.asarray(energy, float)
    if not len(times) or len(e) < 2:
        return 0.0, 0.0
    shifts = np.arange(-search, search + 1e-9, 1.0 / fps)
    w = max(1, int(round(window * fps)))

    def edge(t, s):
        a = int(round((t + s) * fps))
        return e[max(0, a):max(0, min(len(e), a + w))].sum() - e[max(0, a - w):max(0, min(len(e), a))].sum()
    per = np.array([[edge(t, s) for s in shifts] for t in times])
    best = float(shifts[int(per.sum(axis=0).argmax())])
    k = int(np.argmin(np.abs(shifts - best)))
    agree = np.mean([row[k] > 0 and row[k] >= 0.5 * row.max() for row in per])
    return best, float(agree)


def record_json(app, window, scale, size, n, actions, offset, confidence, path=()):
    acts = []
    for i, a in enumerate(actions):
        acts.append({"i": i, "kind": a["kind"], "label": a.get("label", ""),
                     "t": round(a["t"] + offset, 3), "t_end": round(a["t_end"] + offset, 3),
                     "x": None if a.get("x") is None else round(a["x"] * scale, 1),
                     "y": None if a.get("y") is None else round(a["y"] * scale, 1)})
        acts[-1].update({k: a[k] for k in ("text", "clicks", "mods", "key") if k in a})   # sound, keycaps
    out = {"fps": FPS, "n": n, "width": size[0], "height": size[1], "scale": round(scale, 4), "window": window,
           "app": app, "actions": acts, "sync": {"offset": round(offset, 3), "confidence": round(confidence, 2)}}
    if path:        # (t0, t1, x0, y0, x1, y1) in region points -> recording seconds and px
        out["path"] = [{"t0": round(p[0] + offset, 3), "t1": round(p[1] + offset, 3),
                        "x0": round(p[2] * scale, 1), "y0": round(p[3] * scale, 1),
                        "x1": round(p[4] * scale, 1), "y1": round(p[5] * scale, 1)} for p in path]
    return out


# ── the machine ─────────────────────────────────────────────────────────────────────────────────────────────────
def _driver():
    with open(_SWIFT, "rb") as fh:
        exe = os.path.join(_BIN_DIR, "app_drive-" + hashlib.sha256(fh.read()).hexdigest()[:16])
    if not os.path.exists(exe):
        if not shutil.which("swiftc"):
            raise RecordError("swiftc is needed to build the cursor driver (install the Xcode command line tools)")
        os.makedirs(_BIN_DIR, exist_ok=True)
        print("[app_record] building the cursor driver — once, about a minute…", file=sys.stderr, flush=True)
        tmp = exe + ".tmp"
        r = subprocess.run(["swiftc", "-O", _SWIFT, "-o", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            raise RecordError("building scripts/app_drive.swift failed: %s" % r.stderr.strip()[-300:])
        os.replace(tmp, exe)
    return exe


def _osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        raise RecordError("AppleScript failed: %s" % r.stderr.strip()[-300:])
    return r.stdout.strip()


def preflight():
    if sys.platform != "darwin":
        raise RecordError("recording an app's window needs macOS")
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        r = subprocess.run(["screencapture", "-x", "-R0,0,8,8", tmp], capture_output=True, text=True)
        if r.returncode != 0 or os.path.getsize(tmp) == 0:
            raise RecordError(PERMISSION_HELP)
    finally:
        os.remove(tmp)
    try:
        _osa('tell application "System Events" to get name of first application process whose frontmost is true')
    except RecordError:
        raise RecordError("macOS has not given this terminal Accessibility, so the app cannot be driven: System "
                          "Settings > Privacy & Security > Accessibility")


def _window(app, size, top_left=False):
    """The app's front window [x, y, w, h] (points), sized and placed. top_left: right under the menu bar at the
    screen's left edge, so a recording that includes the menu bar shows the menus a step opens."""
    _osa('tell application "%s" to activate' % app)
    time.sleep(1.0)
    proc = 'tell application "System Events" to tell process "%s"' % app
    if _osa('%s to get count of windows' % proc) in ("", "0"):
        raise RecordError("System Events sees no window of %s. Open the document to record first; if a window IS open, "
                          "this process cannot use Accessibility: a sandboxed shell (Claude Code's command sandbox, "
                          "measured 2026-11-25) gets 0 windows for every app although the terminal has the "
                          "permission, so run app_record outside the sandbox" % app)
    if size:
        _osa('%s to set size of front window to {%d, %d}' % (proc, size[0], size[1]))
        _osa('%s to set position of front window to {%d, %d}' % ((proc,) + ((0, 0) if top_left else (80, 60))))
        time.sleep(0.5)
    out = _osa('%s to get {position, size} of front window' % proc)
    x, y, w, h = [int(float(v)) for v in out.replace(" ", "").split(",")]
    return [x, y, w, h]


def menu_item_follows(prev, box, depth):
    """Is `box` (x, y, w, h, points) where an OPEN menu puts the item after `prev`? depth 1: in the menu that drops
    from the menu-bar title `prev`; deeper: in the submenu beside the item `prev`. A closed menu reports a stale
    place (the Airbnb-day TextEdit run, 2026-11-25: "Bold" at (-80, 1047) while its Font submenu was shut, and the
    driver clicked the screen's corner), so an item anywhere else is refused before it is clicked."""
    px, py, pw, ph = prev
    x, y, w, h = box
    if w <= 0 or h <= 0:
        return False
    if depth == 1:
        return y >= py + ph - 2 and x - 40 <= px <= x + w
    beside = abs(x - (px + pw)) <= 24 or abs((x + w) - px) <= 24     # opens to the right, or to the left
    return beside and y + h >= py - 600 and y <= py + 600


def _menu_boxes(app, path):
    """Yield the box (x, y, w, h, global points) of each item of a menu path, querying each level only after the
    caller has clicked the one before it (so its menu is open), and refusing an item its menu does not show."""
    proc = 'tell application "System Events" to tell process "%s"' % app
    ref, prev = 'menu bar item "%s" of menu bar 1' % path[0], None
    for depth in range(len(path)):
        if depth:
            ref = 'menu item "%s" of menu 1 of %s' % (path[depth], ref)
        out = _osa('%s to get {position, size} of %s' % (proc, ref))
        box = tuple(float(v) for v in out.replace(" ", "").split(","))
        if depth and not menu_item_follows(prev, box, depth):
            _osa('tell application "System Events" to key code 53')     # escape: close what is open
            raise RecordError("the menu %s did not open where it should (%r is not beside %r); nothing was clicked "
                              "there" % (" > ".join(path[:depth + 1]), box, prev))
        yield box
        prev = box


def run(film_dir, spec, name="rec"):
    errs = check_steps(spec)
    if errs:
        raise RecordError("; ".join(errs))
    preflight()
    drv = _driver()
    app = spec["app"]
    menus = any("menu" in s for s in spec["steps"])
    win = _window(app, spec.get("window"), top_left=menus)
    reg = [win[0], 0, win[2], win[1] + win[3]] if menus else list(win)   # the menu bar and its menus are in the picture
    out = os.path.join(film_dir, "clips", name)
    os.makedirs(out, exist_ok=True)
    mov = os.path.join(out, "raw.mov")
    est = spec.get("lead", 1.0) + spec.get("tail", 1.5) + 4.0 + sum(
        s.get("wait", 0) + (len(s.get("type", "")) / s.get("cps", 9)) + 1.2 * len(s.get("menu", [None])) for s in spec["steps"])
    cap = subprocess.Popen(["screencapture", "-v", "-x", "-C", "-V%d" % int(est + 1), "-R%d,%d,%d,%d" % tuple(reg), mov],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    t0 = time.monotonic()
    clock = lambda: time.monotonic() - t0   # noqa: E731
    time.sleep(spec.get("lead", 1.0))

    path, cur = [], None          # the cursor's glides (global points), for a halo that follows it (screenrec.js)

    def drive(*args):
        nonlocal cur
        ts = clock()
        if cur is None and args[0] != "pos":
            cur = [float(v) for v in drive("pos")]
        r = subprocess.run([drv] + [str(a) for a in args], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.startswith("ok"):
            raise RecordError("the cursor driver failed on %s: %s" % (args, (r.stderr or r.stdout).strip()))
        if args[0] in ("move", "click"):
            path.append((ts, ts + float(args[3]) / 1000.0, cur[0], cur[1], float(args[1]), float(args[2])))
        elif args[0] == "drag":       # app_drive: 500 ms to the start, press, 120 ms, then the drag itself
            x1, y1, x2, y2, ms = (float(v) for v in args[1:6])
            path.append((ts, ts + 0.5, cur[0], cur[1], x1, y1))
            path.append((ts + 0.62, ts + 0.62 + ms / 1000.0, x1, y1, x2, y2))
        cur = [float(v) for v in r.stdout.split()[1:3]]
        return r.stdout.split()[1:]

    def at(p):
        return win[0] + p[0], win[1] + p[1]

    acts = []
    for s in spec["steps"]:
        ms, label = s.get("ms", 650), s.get("label", "")
        a0 = clock()
        if "wait" in s:
            time.sleep(s["wait"])
            continue
        if "click" in s or "move" in s:
            gx, gy = at(s.get("click") or s.get("move"))
            got = drive(*(("click", gx, gy, ms, s.get("clicks", 1), s.get("mods", "")) if "click" in s
                          else ("move", gx, gy, ms)))
            if abs(int(got[0]) - round(gx)) > 2 or abs(int(got[1]) - round(gy)) > 2:
                raise RecordError("the cursor did not arrive (Accessibility off for this terminal?)")
            acts.append({"kind": "click" if "click" in s else "move", "label": label, "t": clock(), "t_end": clock(),
                         "clicks": s.get("clicks", 1), **({"mods": s["mods"]} if s.get("mods") else {}),
                         "x": gx - reg[0], "y": gy - reg[1]})
        elif "click_text" in s:
            import screen_text
            fd, png = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            subprocess.run(["screencapture", "-x", "-R%d,%d,%d,%d" % tuple(win), png], check=True)
            hit = screen_text.find_text(screen_text.recognize(png), s["click_text"], s.get("nth"))
            os.remove(png)
            px, py = hit["x"] * win[2], hit["y"] * win[3]
            drive("click", *at([px, py]), ms, s.get("clicks", 1), s.get("mods", ""))
            acts.append({"kind": "click", "label": label or s["click_text"], "t": clock(), "t_end": clock(),
                         "clicks": s.get("clicks", 1),
                         "x": px + win[0] - reg[0], "y": py + win[1] - reg[1]})
        elif "menu" in s:
            last = len(s["menu"]) - 1
            for k, (bx, by, bw, bh) in enumerate(_menu_boxes(app, s["menu"])):
                gx, gy = bx + bw / 2, by + bh / 2
                if k:   # an L, never a diagonal: a diagonal crosses the next menu-bar title or another item's submenu
                    cx, cy = [float(v) for v in drive("pos")]
                    drive("move", *((cx, gy) if k == 1 else (gx, cy)), 300)
                drive("click", gx, gy, ms if k == 0 else 300)
                acts.append({"kind": "click", "label": (label or s["menu"][k]) if k == last else
                             " > ".join(s["menu"][:k + 1]), "t": clock(), "t_end": clock(),
                             "x": gx - reg[0], "y": gy - reg[1]})
                time.sleep(0.35)
        elif "drag" in s:
            (x1, y1), (x2, y2) = at(s["drag"][0]), at(s["drag"][1])
            drive("drag", x1, y1, x2, y2, s.get("ms", 900))
            acts.append({"kind": "drag", "label": label, "t": a0, "t_end": clock(), "x": x2 - reg[0], "y": y2 - reg[1]})
        elif "type" in s:
            drive("type", s["type"], s.get("cps", 9))
            acts.append({"kind": "type", "label": label or s["type"], "text": s["type"], "t": a0, "t_end": clock(),
                         "x": None, "y": None})
        elif "scroll" in s:
            drive("scroll", s["scroll"])
            acts.append({"kind": "scroll", "label": label, "t": a0, "t_end": clock(), "x": None, "y": None})
        elif "key" in s:
            drive("key", s["key"])
            acts.append({"kind": "key", "label": label or s["key"], "key": s["key"], "t": clock(), "t_end": clock(),
                         "x": None, "y": None})
    end = clock() + spec.get("tail", 1.5)
    cap.wait()
    if not os.path.isfile(mov) or os.path.getsize(mov) == 0:
        raise RecordError("screencapture wrote no video: %s" % cap.stderr.read().decode(errors="replace")[-300:])
    rel = [(a, b, x0 - reg[0], y0 - reg[1], x1 - reg[0], y1 - reg[1]) for a, b, x0, y0, x1, y1 in path]
    return _finish(out, mov, app, reg, acts, end, rel)


def _finish(out, mov, app, win, acts, end, path=()):
    import numpy as np
    mp4 = os.path.join(out, "rec.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mov, "-t", "%.3f" % end, "-r", str(FPS), "-c:v", "libx264",
                    "-crf", "12", "-pix_fmt", "yuv420p", mp4], check=True)
    os.remove(mov)
    w, h = [int(v) for v in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                             "stream=width,height", "-of", "csv=p=0", mp4], capture_output=True,
                                            text=True).stdout.strip().split(",")[:2]]
    frames = os.path.join(out, "frames")
    shutil.rmtree(frames, ignore_errors=True)
    os.makedirs(frames)
    subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-q:v", "2", os.path.join(frames, "%05d.jpg")], check=True)
    n = len(os.listdir(frames))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vf", "scale=240:160,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    g = np.frombuffer(raw, np.uint8).reshape(-1, 240 * 160).astype(np.int16)
    energy = [0.0] + list(np.abs(np.diff(g, axis=0)).mean(axis=1))
    times = [a["t"] for a in acts if a["kind"] in ("click", "drag", "type", "key")]
    off, conf = align_offset(energy, FPS, times)
    if conf < 0.6:
        print("[app_record] WARN only %d%% of the actions line up with the video's own changes; check the click "
              "rings against the frames before building on them" % round(conf * 100), file=sys.stderr)
    rec = record_json(app, win, w / float(win[2]), (w, h), n, acts, off, conf, path)
    with open(os.path.join(out, "rec.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    return rec


def main(argv):
    import _common as _c
    _c.refuse_unknown(argv, valued=("name",), usage=_USAGE)
    name = _c.argflag(argv, "name", "rec")
    args = [a for a in argv if not a.startswith("--") and a != name]
    if len(args) != 2:
        print(_USAGE, file=sys.stderr)
        return 2
    try:
        spec = json.load(open(args[1], encoding="utf-8"))
        rec = run(args[0], spec, name)
    except (OSError, ValueError) as e:
        print("app_record: %s" % e, file=sys.stderr)
        return 2
    except RecordError as e:
        print("app_record: %s" % e, file=sys.stderr)
        return 2
    print("[app_record] %s: %d actions, %d frames %dx%d, sync %+.2f s (%.0f%% of actions agree)"
          % (rec["app"], len(rec["actions"]), rec["n"], rec["width"], rec["height"], rec["sync"]["offset"],
             rec["sync"]["confidence"] * 100))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
