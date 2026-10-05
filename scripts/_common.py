"""Shared low-level helpers. No domain knowledge lives here."""
import json, os, re, shutil, subprocess, sys

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


# ── command-line flags, read the SAME way everywhere ────────────────────────────────────────────────────
#
# WHY THIS EXISTS, and what it cost. Nine scripts here parse their own flags with
# `next((a.split("=", 1)[1] for a in argv if a.startswith("--only=")), None)`, and not one of them refused an
# argument it did not understand. So `--only DollyZoom` — the spelling this repo's own docstrings use for
# `cjk_type_qa`, and the one a person types — matched nothing in `register_energy`, fell through to `None`,
# and ran a FULL 164-register sweep instead of the one that was asked for. Twice in one session, about
# forty-five minutes of renders each time, with no message: the progress counter read "measured 10/164" and
# nothing in the output said the filter had been dropped.
#
# Three scripts, three behaviours for the same typed flag: `register_energy` swept everything in silence,
# `cjk_type_qa` (argparse) accepted it, and `text_safe_qa` crashed trying to open `--only/storyboard.json`.
# Only the crash was honest.
#
# So: one reader that takes BOTH spellings, and one guard that REFUSES what a script did not claim. An
# unparsed argument must never be a silent change of scope — that is the "degrades loudly" rule applied to
# the command line, and the loud version costs a second while the quiet one costs an hour.
def argflag(argv, name, default=None):
    """The value of `--name=V` or `--name V`, or `default`. `name` is given without dashes."""
    pref = "--%s=" % name
    for i, a in enumerate(argv):
        if a.startswith(pref):
            return a[len(pref):]
        if a == "--" + name and i + 1 < len(argv) and not argv[i + 1].startswith("-"):
            return argv[i + 1]
    return default


def argflag_list(argv, name, default=None):
    """`--name=a,b` or `--name a,b` as a list of non-empty items, or `default`."""
    raw = argflag(argv, name)
    if raw is None:
        return default
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items or default


def refuse_unknown(argv, valued=(), switches=(), usage=""):
    """Exit non-zero naming any argument the caller did not claim, instead of ignoring it.

    `valued` are flags that take a value (either spelling); `switches` are bare ones. Anything else that
    starts with `-` is refused, and so is a bare word that follows a valued flag ONLY if that flag was not
    consumed — callers pass their positional count separately by just not listing it here.
    """
    valued, switches = set(valued), set(switches)
    unknown, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            name = a[2:].split("=", 1)[0]
            if name in valued:
                if "=" not in a and i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                    i += 1                       # the value belongs to this flag
            elif name not in switches:
                unknown.append(a)
        elif a.startswith("-") and a != "-":
            unknown.append(a)
        i += 1
    if unknown:
        print("[%s] unknown argument(s): %s" % (os.path.basename(sys.argv[0]), ", ".join(unknown)))
        if usage:
            print(usage)
        raise SystemExit(2)


# ── WHAT A SWEEP DID NOT MEASURE ──────────────────────────────────────────────────────────────────────
# A gate's headline counted what it MEASURED, and a skip read as a clean result. `ink_contrast_qa` swept the
# library and reported 19 registers "skipped"; behind those 19 were FOUR different bugs — a fixed frame past
# the end of seven short registers, six registers handed no picture to draw, a skip reason that printed
# `at process.processTicksAndRejections (node:internal/…)` for eight more, and a probe DNA value no preset
# ships, which made a register throw and be written down as refusing to render. None of it was visible in the
# headline, because the headline counted what the gate had measured.
#
# So: one reader of "what did this sweep NOT see", used by every sweep, because four disagreeing copies of
# the caption band is how this repository learned what a second definition costs.
def coverage(tag, measured, universe, not_measured=None, out=None):
    """Print `measured N of M · K NOT measured`, then NAME each one with a reason. Returns K.

    `measured` and `universe` may be counts or collections; `not_measured` is {item: why}. K comes from the
    UNIVERSE (M - N), never from the length of the reason map: a sweep that dropped an item without writing
    down why must not be able to hide it by having nothing to print.
    """
    n = measured if isinstance(measured, int) else len(measured)
    m = universe if isinstance(universe, int) else len(universe)
    nm = dict(not_measured or {})
    k = max(m - n, len(nm))
    w = out or sys.stdout
    w.write("[%s] measured %d of %d · %d NOT measured%s\n" % (tag, n, m, k, ":" if k else ""))
    for name in sorted(nm):
        w.write("    %-24s %s\n" % (name, nm[name]))
    if k > len(nm):
        w.write("    (and %d with NO recorded reason — a sweep that cannot say why it lost an item is "
                "itself the finding)\n" % (k - len(nm)))
    w.flush()
    return k


# THE REASON, NOT THE LAST LINE OF THE STACK. `splitlines()[-1]` on a failed remotion render is
# `at process.processTicksAndRejections (node:internal/…)` — eight registers carried that non-reason into a
# skip list, which says nothing anyone can act on and is the same failure as a gate reporting a count instead
# of a coverage. The renderer prints the real message on a line naming an Error type, so that is what is
# kept, with the stack dropped. `RangeError: Cannot use frame 110: Duration of composition is 96` is the case
# that forced the match to be a TYPE rather than the literal word `Error` at the start of a line.
_ERR_LINE = re.compile(r"(?:^|\s)[A-Za-z]*Error\b|An error occurred:")


def render_error(stdout, stderr="", limit=220):
    """The message a failed subprocess refused with, from its combined output. Never empty."""
    out = ((stderr or "") + "\n" + (stdout or "")).strip()
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    for i, l in enumerate(lines):
        if _ERR_LINE.search(l):
            # A SELF-CONTAINED MESSAGE IS THE WHOLE REASON. Remotion prints some failures as a bare
            # `An error occurred:` followed by the message, so the window has to reach forward — and
            # reaching forward on a message that already said everything glues the progress counter
            # ("Rendered 0/1") onto the end of it.
            if ":" in l and len(l) > 40:
                return l[:limit]
            tail = [x for x in lines[i:i + 3] if not x.startswith("at ")]
            return " ".join(tail)[:limit]
    real = [l for l in lines if not l.startswith("at ") and not l.startswith("|")]
    if real:
        return real[-1][:limit]
    if lines:
        return ("no message, only a stack: " + lines[-1])[:limit]
    return "no output at all"


# ── a cued reveal must FINISH before the scene's visible end (scenes.html_capture_plan, validate) ──────
def out_edge_seconds(slide, meta, dur):
    """Seconds at the END of a scene's clip that its out-transition takes away — render.py `_edge_filter`'s
    rule (slide `transition` / `transition_seconds` over the meta defaults; 'dip' and 'out' close on the
    theme ground, 'in' and 'none' do not, and a clip too short for its seam gets none). Whatever is still
    arriving in that window is seen arriving into a fade, never at full strength."""
    import storyboard as _sb
    t, d = _sb.normalize_transition(slide or {})
    if t not in ("dip", "in", "out", "none"):
        t = (meta or {}).get("transition", "dip")
    if t not in ("dip", "out"):
        return 0.0
    d = float(d if d is not None else (meta or {}).get("transition_seconds", 0.2))
    need = 2.2 * d if t == "dip" else 1.1 * d
    if d <= 0 or dur <= need:
        return 0.0
    return d


def cued_anim_need(html):
    """{data-cue-index: seconds its cued element animates for, plus any positive data-cue-offset lag} — what
    a cue's reveal needs after its moment to finish (the per-cue burst width and the end clamp read it)."""
    import re
    table = css_anim_durations()
    need = {}
    for tag in re.findall(r"<[^>]+>", html):
        mi = re.search(r'data-cue-index\s*=\s*["\'](\d+)["\']', tag)
        if not mi:
            continue
        sec = element_anim_seconds(tag, table)
        if sec:
            ci = int(mi.group(1))
            mo = re.search(r'data-cue-offset\s*=\s*["\']([-\d.]+)["\']', tag)
            lag = max(0.0, float(mo.group(1))) if mo else 0.0
            need[ci] = max(need.get(ci, 0.0), sec + lag)
    return need


CUE_LEAD_MAX = 1.0   # s: the most a cue is ever led to let its reveal finish (sync_qa calls < 1 s early in sync)


def clamp_cues_to_end(ordered, times, need, dur, out_edge, max_lead=CUE_LEAD_MAX):
    """(times, led) — each cue moved early enough that its reveal FINISHES before the scene's visible end
    (dur - out_edge), when the scene is long enough for that; `led` lists the cue indices moved.

    WHY. A reveal anchored to one of the narration's LAST words used to start at its word (clamped only to
    dur - 0.5s) and was still fading in when the out-transition began: measured through this plan, a plain
    .reveal cued at 86% of a 4 s scene stood at 0.77 opacity when the dip started and 0.65 at 88% — the
    viewer saw it arrive into a fade and never saw it whole. Leading the word by the few tenths of a second
    the animation needs is the smaller error: sync_qa treats under a second early as in sync, and a reveal
    that never completes is not a reveal. A cue that would have to move more than `max_lead` is left on its
    word — a 1.4 s .draw on the last word wants a shorter duration or an earlier phrase, which validate's
    truncation gate says, not to be pulled a second and a half ahead of what it shows."""
    end = dur - out_edge
    out, led = [], []
    for (ci, _a), t in zip(ordered, times):
        n = need.get(ci)
        if t is not None and n and end - n >= 0 and end - n + 1e-9 < t <= end - n + max_lead:
            out.append(round(end - n, 3))
            led.append(ci)
        else:
            out.append(t)
    return out, led
