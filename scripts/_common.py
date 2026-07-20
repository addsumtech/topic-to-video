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


_ANIM_DUR_CACHE = {}

def css_anim_durations():
    """{class_name: seconds} for every animation class in base.css/motifs.css, parsed from the CSS so
    it can never drift from the stylesheets. `var(--dur)` resolves via :root's own --dur.

    Shared by validate.py (does a cued animation finish before the scene cuts?) and scenes.py (how
    wide must the capture burst be so it doesn't freeze mid-flight?) — two questions that must agree
    on the same numbers, or one gate passes what the other renders wrong."""
    import re
    if _ANIM_DUR_CACHE:
        return _ANIM_DUR_CACHE
    here = os.path.dirname(os.path.abspath(__file__))
    css = ""
    for name in ("base.css", "motifs.css"):
        p = os.path.join(here, "..", "assets", "html", name)
        if os.path.exists(p):
            try:
                css += open(p, encoding="utf-8").read() + "\n"
            except Exception:
                pass
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)   # a comment naming .draw would pollute the next selector
    m = re.search(r"--dur\s*:\s*([\d.]+)s", css)
    base_dur = float(m.group(1)) if m else 0.7
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        ma = re.search(r"animation\s*:\s*[a-zA-Z0-9_-]+\s+(?:([\d.]+)s|var\(--dur\))", body)
        if not ma:
            continue
        secs = float(ma.group(1)) if ma.group(1) else base_dur
        for cls in re.findall(r"\.([a-zA-Z0-9_-]+)", sel):
            _ANIM_DUR_CACHE[cls] = max(_ANIM_DUR_CACHE.get(cls, 0.0), secs)
    return _ANIM_DUR_CACHE


AMBIENT_CLASSES = {"bg-live", "bg-drift"}

def element_anim_seconds(tag_html, table=None):
    """Effective animation-duration (seconds) for ONE element's opening tag: an inline
    `animation-duration` wins, else the longest duration among its animation classes. None when the
    element carries no animation at all (or is an ambient backdrop, which is progress-driven and
    never truncated)."""
    import re
    table = table if table is not None else css_anim_durations()
    mc = re.search(r'class\s*=\s*"([^"]*)"', tag_html)
    classes = set(re.findall(r"[\w-]+", mc.group(1))) if mc else set()
    if classes & AMBIENT_CLASSES or "data-ambient" in tag_html:
        return None
    mo = re.search(r"animation-duration\s*:\s*([\d.]*)s", tag_html)
    if mo and mo.group(1) not in ("", "."):
        return float(mo.group(1))
    hits = [table[c] for c in classes if c in table]
    return max(hits) if hits else None
