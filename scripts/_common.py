"""Shared low-level helpers. No domain knowledge lives here."""
import json, os, shutil, subprocess, sys

def progress(done, total, prefix="", width=22, stream=None):
    """A single-line terminal progress bar that overwrites itself in place on a TTY. On a non-TTY
    (piped to a log / CI) it stays silent until 100%, then prints one summary line — so background
    render logs aren't flooded with carriage-return spam. Safe to call every step."""
    stream = stream or sys.stderr
    if total <= 0:
        return
    done = max(0, min(int(done), int(total)))
    if getattr(stream, "isatty", lambda: False)():
        fill = int(width * done / total)
        bar = "█" * fill + "·" * (width - fill)
        stream.write(f"\r  {prefix} [{bar}] {done}/{total}" + ("\n" if done >= total else ""))
        stream.flush()
    elif done >= total:
        stream.write(f"  {prefix}: {total} frames\n")
        stream.flush()

SOFFICE_CANDIDATES = [
    "soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]

def run(cmd, **kw):
    """Run a command, raise on non-zero, return stdout (text)."""
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout

def have_tool(name):
    return shutil.which(name) is not None

def find_soffice():
    for cand in SOFFICE_CANDIDATES:
        if os.path.exists(cand) or shutil.which(cand):
            return cand
    return None

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
CHROME_PATH_NAMES = ("google-chrome", "chromium", "chromium-browser", "chrome")

def find_chrome(meta=None):
    """Locate a Chrome/Chromium binary: meta.chrome_path, the macOS apps, then PATH. None if
    absent. Single source of truth so the doctor preflight and the HTML renderer agree."""
    c = (meta or {}).get("chrome_path")
    if c and os.path.exists(c):
        return c
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    for n in CHROME_PATH_NAMES:
        w = shutil.which(n)
        if w:
            return w
    return None

def audio_duration(path):
    """Seconds, via ffprobe. Source of truth for slide timing. NEVER raises — a header-only clip (e.g.
    macOS `say ' '`, which writes an AIFF with no format.duration) falls back to the audio-stream probe,
    then 0.0 — so one odd/empty clip can't abort the whole tts step with a KeyError."""
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "json", path])
    try:
        d = (json.loads(out).get("format") or {}).get("duration")
        if d is not None:
            return float(d)
    except Exception:
        pass
    try:
        out2 = run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                    "-show_entries", "stream=duration", "-of", "json", path])
        streams = json.loads(out2).get("streams") or [{}]
        d2 = streams[0].get("duration")
        return float(d2) if d2 is not None else 0.0
    except Exception:
        return 0.0
