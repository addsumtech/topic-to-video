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


_SPAN_DECL = re.compile(r"\bstatic\s+span\s*=\s*([0-9]*\.?[0-9]+)")
_DEFINE = re.compile(r"customElements\s*\.\s*define\s*\(\s*['\"`]([a-z][a-z0-9]*(?:-[a-z0-9]*)+)['\"`]")
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def component_spans(html):
    """{custom tag: seconds} — each component's declared `static span` (how long after its start its last part
    finishes animating), read from the component scripts the page links. A component with no declaration is
    absent: workshop.py `check` measures every component's parts and refuses one whose parts outlast the capture
    burst without saying so, so absent means "finishes inside an ordinary reveal"."""
    from urllib.parse import unquote, urlparse
    out = {}
    for src in re.findall(r"""<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["']""", html or "", re.I):
        u = urlparse(src)
        path = unquote(u.path) if u.scheme == "file" else (src if os.path.isabs(src) else None)
        if not path or not os.path.isfile(path):
            continue
        try:
            js = open(path, encoding="utf-8").read()
        except OSError:
            continue
        tags, spans = _DEFINE.findall(js), _SPAN_DECL.findall(js)
        if len(tags) == 1 and spans:
            out[tags[0]] = float(spans[0])
    return out


def _inline_delay(tag_html):
    m = re.search(r"animation-delay\s*:\s*(-?[\d.]+)(m?s)", tag_html)
    if not m or m.group(1) in ("", ".", "-"):
        return 0.0
    v = float(m.group(1))
    return v / 1000.0 if m.group(2) == "ms" else v


def cued_anim_need(html):
    """{data-cue-index: seconds after its cue that element's animation runs — plus any positive data-cue-offset
    lag} — what a cue's reveal needs after its moment to finish (the per-cue burst width and the end clamp read it).

    A cued element's PARTS count: seek.js times every animated descendant that carries no data-cue-index of its
    own from its cue host's start, its own animation-delay an offset from there — so a host needs the longest of
    (part's inline delay + its duration) too, and a component inside it (or the host itself, when it is one) its
    declared `static span` (component_spans). Before, only the host's own class was counted, and a component whose
    cells rippled in for 1.45 s got the ordinary 0.8 s burst and was frozen mid-ripple."""
    from html.parser import HTMLParser
    table = css_anim_durations()
    spans = component_spans(html)
    need = {}

    class _P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.stack = []                         # [(tag, cue index or None, lag)]

        def _host(self):
            for _t, ci, lag in reversed(self.stack):
                if ci is not None:
                    return ci, lag
            return None, 0.0

        def handle_starttag(self, tag, attrs):
            raw = self.get_starttag_text() or ""
            mi = re.search(r'data-cue-index\s*=\s*["\'](\d+)["\']', raw)
            mo = re.search(r'data-cue-offset\s*=\s*["\']([-\d.]+)["\']', raw)
            own = int(mi.group(1)) if mi else None
            lag = max(0.0, float(mo.group(1))) if (mi and mo) else 0.0
            sec = element_anim_seconds(raw, table)
            comp = spans.get(tag.lower())
            if own is not None:
                host, hlag, rel = own, lag, 0.0     # a host's own reveal starts on its cue
            else:
                host, hlag = self._host()
                rel = _inline_delay(raw)            # a part: its delay counts from the host's start
            if host is not None:
                for s in (sec, comp):
                    if s:
                        need[host] = max(need.get(host, 0.0), max(0.0, rel) + s + hlag)
            if tag.lower() not in _VOID and not raw.rstrip().endswith("/>"):
                self.stack.append((tag.lower(), own, lag))

        def handle_endtag(self, tag):
            for k in range(len(self.stack) - 1, -1, -1):
                if self.stack[k][0] == tag.lower():
                    del self.stack[k:]
                    break

    p = _P()
    p.feed(re.sub(r"(<(script|style)\b[^>]*>).*?(</\2\s*>)", r"\1\3", html or "", flags=re.S | re.I))
    p.close()
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


# WORDS AND SUBSTANCE IN ANY SCRIPT. A word is a run between spaces and punctuation that holds a letter — so a
# Devanagari word keeps its vowel signs (Python's \w does not count combining marks, and splitting on it counted one
# Hindi word as two or three), an apostrophe stays inside "don't", and a CJK character is counted on its own (half a
# word each). A run of 12+ letters with no spaces (Thai, Lao, Khmer...) counts one word per 6 more. The first
# versions counted Latin words and CJK only, so a Russian, Greek, Arabic or Hindi line measured zero words: an ideal
# or a waiver reason in those languages was refused as "not specific", and pace.py predicted only a line's pauses.
_CJK_CHARS = re.compile(r"[぀-ヿ㐀-鿿가-힯豈-﫿]")
_WORD_SPLIT = re.compile(r"[\s,.;:!?()\[\]{}<>\"`“”«»—–\-/\\|…·、，。！？；：（）【】《》「」『』]+")
_HAS_LETTER = re.compile(r"[^\W\d_]")


def words(text, digits=True):
    """The words of `text` outside CJK, in any script; `digits=False` drops tokens that hold no letter."""
    toks = [w for w in _WORD_SPLIT.split(_CJK_CHARS.sub(" ", str(text or ""))) if w.strip("'’‘")]
    return [w for w in toks if (_HAS_LETTER.search(w) or (digits and re.search(r"\d", w)))]


_CLIP_BREAK = re.compile(r"[\s,.;:!?()\[\]{}<>\"“”«»—–/\\|…·、，。！？；：（）【】《》「」『』]")
_LATIN_RUN = re.compile(r"[A-Za-z0-9À-ɏЀ-ӿ'’+.-]")


def clip_text(text, n, ellipsis="…"):
    """`text` cut to at most `n` characters at a BOUNDARY — a space, a punctuation mark, or between two CJK glyphs —
    never inside a Latin or Cyrillic word or a number. `t[:n]` printed "镜头像在看一张 NAS…" and the wordmark
    "DIETER RAMS 少，但更好 WENI" into contest samples. The ellipsis is added only when something was cut."""
    t = " ".join(str(text or "").split())
    if len(t) <= n:
        return t
    room = max(1, n - len(ellipsis))
    cut = 0
    for i in range(1, room + 1):
        a, b = t[i - 1], t[i] if i < len(t) else " "
        if _CLIP_BREAK.match(b) or _CLIP_BREAK.match(a) or not (_LATIN_RUN.match(a) and _LATIN_RUN.match(b)):
            cut = i
    head = t[:cut].rstrip(" ,.;:—–-/|·、，。；：") if cut else t[:room]
    return head + ellipsis


def substance(text):
    """How much a justification says: words (any script) + CJK characters / 2."""
    t = str(text or "")
    return sum(1 + (len(w) // 6 if len(w) >= 12 else 0) for w in words(t)) + len(_CJK_CHARS.findall(t)) / 2.0


# ── ONE RENDER AT A TIME, MACHINE-WIDE ────────────────────────────────────────────────────────────────────────────
# Renders that overlap starve each other: four concurrent cjk shards reported registers as render failures that
# render fine alone, and a delivery run that overlapped another render timed two gates out. A PARALLEL design pass
# (several builders at once) is only safe because their renders take turns. Every `npx remotion` call a builder or the
# lead's design gates make holds this lock for the length of ONE render, so builders interleave while they think and
# write in parallel. It is an OS lock on a file: a process that dies releases it, and the same process may re-enter it.
RENDER_LOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", ".render.lock")
_LOCK_DEPTH = [0, None]


class render_lock:
    """`with render_lock(): subprocess.run([...remotion...])` — waits for any other render on this machine to finish.
    Off with TOPIC_VIDEO_RENDER_LOCK=0 (a sweep that manages its own concurrency)."""

    def __enter__(self):
        if os.environ.get("TOPIC_VIDEO_RENDER_LOCK") == "0":
            return self
        if _LOCK_DEPTH[0] == 0:
            import fcntl
            fh = open(RENDER_LOCK, "a+")
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            _LOCK_DEPTH[1] = fh
        _LOCK_DEPTH[0] += 1
        return self

    def __exit__(self, *exc):
        if os.environ.get("TOPIC_VIDEO_RENDER_LOCK") == "0" or _LOCK_DEPTH[0] == 0:
            return False
        _LOCK_DEPTH[0] -= 1
        if _LOCK_DEPTH[0] == 0 and _LOCK_DEPTH[1] is not None:
            import fcntl
            try:
                fcntl.flock(_LOCK_DEPTH[1].fileno(), fcntl.LOCK_UN)
            finally:
                _LOCK_DEPTH[1].close()
                _LOCK_DEPTH[1] = None
        return False


def run_render(run, *args, **kw):
    """`run(*args, **kw)` — one `npx remotion …` render — under the machine-wide render lock, WATCHED (`watched_run`):
    a render whose process tree stops working is killed and retried once. `run` is the CALLER's own
    `subprocess.run`, looked up at the call, so a test that replaces a module's subprocess still intercepts it
    (a replaced `run` is called as given — the watch is for real renders)."""
    with render_lock():
        if run is _REAL_RUN:
            return watched_run(*args, **kw)
        return run(*args, **kw)


# ── A RENDER THAT STOPS WORKING IS KILLED, NOT WAITED ON ──────────────────────────────────────────────────────────
# `remotion still --gl=angle` has hung on this machine at 0% CPU — one sat 2 h 18 min holding a render slot — and no
# caller passed a timeout, so one hung still stalled a whole gate run until something outside killed it. A wall clock
# cannot tell a hang from a slow film render, so the watch is on WORK: the CPU the render's whole process TREE spends.
#   * The TREE, not the process group. Remotion launches Chrome `detached` (@remotion/renderer
#     dist/browser/BrowserRunner.js: `detached: process.platform !== 'win32'`), so the browser — where a still
#     spends most of its CPU — leads a process group of its own. A group-only watch sees node idling while Chrome
#     works and kills a working render; a group KILL leaves that Chrome running as an orphan (seven orphaned
#     browsers, 33 processes and ~1.5 GB, were found on this machine, the oldest 13 h old).
#   * Summed as per-process DELTAS. A total over the LIVING processes falls each time one exits, so a high-water
#     mark on it calls a busy run of short renders "no progress" — reproduced: a command at 100% CPU throughout, as
#     one 20 s child then 2 s children, was killed 60 s in by such a watch.
RENDER_IDLE_S = 120.0       # no work for this long = hung (TOPIC_VIDEO_RENDER_IDLE_S overrides)
_IDLE_CPU_PER_S = 0.01      # "no work": under 1% of one core across the tree, averaged over the idle window
_POLL_S = 2.0
# Lines a render prints when it is BROKEN although its tree keeps working (busy-looping on a dead page): the anc
# film, 2026-11-05 — the Mac's network changed, Chrome lost Remotion's local server and spun for 1 h 35 min on one
# beat, CPU never idle. A matching line on the render's stderr kills the tree and retries it like a hang.
RENDER_FATAL = re.compile(r"net::ERR_NETWORK_CHANGED|A network error occurred|Session closed\. Most likely the page has been closed")
_REAL_RUN = subprocess.run


def _cpu_seconds(txt):
    """ps `time` -> seconds. macOS prints `M:SS.ss`, `H:MM:SS.ss` or `D-HH:MM:SS`; Linux `[DD-]HH:MM:SS`."""
    days = 0
    if "-" in txt:
        d, txt = txt.split("-", 1)
        days = int(d)
    sec = 0.0
    for part in txt.split(":"):
        sec = sec * 60 + float(part)
    return days * 86400 + sec


def _proc_table():
    """{pid: (ppid, pgid, cpu_seconds, stat, command)} of every process on the machine (one `ps`)."""
    out = _REAL_RUN(["ps", "-A", "-o", "pid=,ppid=,pgid=,time=,stat=,command="],
                    capture_output=True, text=True).stdout
    table = {}
    for line in out.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 5:
            continue
        try:
            table[int(parts[0])] = (int(parts[1]), int(parts[2]), _cpu_seconds(parts[3]), parts[4],
                                    parts[5] if len(parts) > 5 else "")
        except ValueError:
            continue
    return table


def _proc_tree(table, root):
    """`root` and every descendant of it, by parent pid — which follows a child into a process group or session of
    its own, where a group walk loses it."""
    kids = {}
    for pid, row in table.items():
        kids.setdefault(row[0], []).append(pid)
    tree, todo = [], [root]
    while todo:
        pid = todo.pop()
        if pid in table and pid not in tree:
            tree.append(pid)
            todo.extend(kids.get(pid, []))
    return tree


def _kill_tree(table, pids):
    """SIGKILL every process of the tree, and the whole group of any group leader inside it (Chrome's GPU and
    renderer processes are in the browser's group). Never this process's own group."""
    import signal
    own = os.getpgrp()
    for g in {table[p][1] for p in pids if p in table and table[p][1] in pids and table[p][1] != own}:
        try:
            os.killpg(g, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    for p in pids:
        try:
            os.kill(p, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _hang_dir():
    import tempfile
    import time
    d = os.path.join(tempfile.gettempdir(), "topic-to-video-render-hangs", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(d, exist_ok=True)
    return d


def _record_hang(table, pids, cmd, idle_s, work, err_tail):
    """Write what the hung tree looked like — each process's state and CPU, and on macOS a `sample` of the node and
    Chrome processes — so the NEXT hang says where it waited. Returns the folder (or None)."""
    try:
        d = _hang_dir()
        rows = ["%7d %7d %7d %10.2f %-5s %s" % ((p,) + table[p][:2] + (table[p][2], table[p][3], table[p][4][:220]))
                for p in pids if p in table]
        with open(os.path.join(d, "tree.txt"), "w", encoding="utf-8") as fh:
            fh.write("command: %s\nidle window: %.0f s, CPU spent in it: %.2f s\n\n    pid    ppid    pgid    cpu(s) stat  "
                     "command\n%s\n\nstderr tail:\n%s\n" % (" ".join(map(str, cmd)), idle_s, work, "\n".join(rows),
                                                             err_tail))
        if sys.platform == "darwin" and shutil.which("sample"):
            for p in pids:
                exe = os.path.basename((table.get(p, ("", "", 0, "", ""))[4].split(" ") or [""])[0])
                if exe in ("node", "remotion") or exe.startswith("chrome-headless-shell"):
                    try:
                        _REAL_RUN(["sample", str(p), "1", "-file", os.path.join(d, "sample_%d.txt" % p)],
                                  capture_output=True, timeout=30)
                    except (subprocess.TimeoutExpired, OSError):
                        pass
        return d
    except OSError:
        return None


def _say_cmd(cmd):
    """A render command as a reader names it: the verb and the composition, never a 2 KB props path."""
    words = [str(x) for x in cmd if not str(x).startswith("--props")]
    return " ".join(words[:7])[:200]


def _watch_once(cmd, idle_s, timeout, feed, kw, fatal=None, cap_s=None):
    """One watched attempt: (returncode, stdout, stderr, hang) — `hang` is None, or (CPU-s in the idle window,
    processes in the tree, diagnostics folder, why) when the tree stopped working (why 'idle'), printed a `fatal`
    line on its stderr ('fatal: <line>') or ran past `cap_s` seconds ('cap'), and was killed."""
    import threading
    import time
    # to read a fatal line the watch must OWN the child's stderr: it is piped through, line by line, to ours
    scan = fatal is not None and kw.get("stderr") is None
    broke = []
    if scan:
        kw = dict(kw, stderr=subprocess.PIPE)
    proc = subprocess.Popen(cmd, **kw)
    if scan:
        def _pump():
            for raw in iter(proc.stderr.readline, b"" if not kw.get("text") and not kw.get("universal_newlines") else ""):
                line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
                sys.stderr.write(line)
                sys.stderr.flush()
                if not broke and fatal.search(line):
                    broke.append(line.strip())
        pump = threading.Thread(target=_pump, daemon=True)
        pump.start()
    t0 = time.time()
    seen, work, window = {}, 0.0, [(t0, 0.0)]
    while True:
        try:
            if scan:
                proc.wait(timeout=_POLL_S)
                pump.join(timeout=5)
                out, err = (proc.stdout.read() if proc.stdout else None), None
            else:
                out, err = proc.communicate(input=feed, timeout=_POLL_S)
            if not broke:
                return proc.returncode, out, err, None
        except subprocess.TimeoutExpired:
            feed = None                                  # communicate() keeps what it was given the first time
        table = _proc_table()
        tree = _proc_tree(table, proc.pid)
        for pid in tree:
            cpu, prev = table[pid][2], seen.get(pid)
            work += cpu if prev is None else max(0.0, cpu - prev)
            seen[pid] = cpu
        now = time.time()
        window.append((now, work))
        while len(window) > 1 and now - window[1][0] >= idle_s:
            window.pop(0)
        spent = work - window[0][1]
        hung = now - window[0][0] >= idle_s and spent < idle_s * _IDLE_CPU_PER_S
        late = timeout is not None and now - t0 > timeout
        capped = cap_s is not None and now - t0 > cap_s
        if not (hung or late or capped or broke):
            continue
        why = "idle" if hung else ("fatal: " + broke[0]) if broke else "cap" if capped else "late"
        where = _record_hang(table, tree, cmd, idle_s, spent, "") if hung else None
        _kill_tree(table, tree)
        try:
            if scan:
                proc.wait(timeout=20)
                out, err = (proc.stdout.read() if proc.stdout else None), None
            else:
                out, err = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
        if late and not capped:
            raise subprocess.TimeoutExpired(cmd, timeout, output=out, stderr=err)
        return 124, out, err, (spent, len(tree), where, why)


def watched_run(cmd, idle_s=None, retries=1, fatal=None, cap_s=None, **kw):
    """`subprocess.run(cmd, **kw)` for one renderer call, KILLED when its whole process tree stops working: less than
    1% of a core for `idle_s` seconds (default RENDER_IDLE_S; env TOPIC_VIDEO_RENDER_IDLE_S). The tree is killed —
    detached Chrome included — the hang is said LOUDLY on stderr with a diagnostics folder, and the call is retried
    `retries` times. A render that hangs every time comes back as returncode 124 with a `RenderHangError:` line in its
    stderr (raised as CalledProcessError under check=True), so a caller's "render failed: <reason>" names the hang
    instead of waiting on it; a retry that worked carries the same line, so the hang is never silent.
    `timeout` keeps subprocess.run's meaning: a wall-clock cap that raises TimeoutExpired. A render can also BREAK and
    keep working (a dead page spun on for 1 h 35 min at full CPU): `fatal` (a compiled regex, e.g. RENDER_FATAL) is
    searched in its stderr, which is piped through to ours, and `cap_s` bounds one attempt's wall clock — either one
    kills the tree and is retried and reported exactly like a hang."""
    idle_s = float(os.environ.get("TOPIC_VIDEO_RENDER_IDLE_S") or idle_s or RENDER_IDLE_S)
    timeout = kw.pop("timeout", None)
    check = kw.pop("check", False)
    if kw.pop("capture_output", False):
        kw["stdout"] = kw["stderr"] = subprocess.PIPE
    feed = kw.pop("input", None)
    if feed is not None:
        kw["stdin"] = subprocess.PIPE
    said = []
    for attempt in range(retries + 1):
        rc, out, err, hang = _watch_once(cmd, idle_s, timeout, feed, kw, fatal=fatal, cap_s=cap_s)
        if hang is None:
            break
        spent, n, where, why = hang
        if why.startswith("fatal: "):
            said.append("RenderBrokeError: `%s` printed %r — its page is dead though its processes keep working — and "
                        "was killed (attempt %d of %d)" % (_say_cmd(cmd), why[7:][:160], attempt + 1, retries + 1))
        elif why == "cap":
            said.append("RenderHangError: `%s` ran longer than its cap of %.0f s and was killed (attempt %d of %d)"
                        % (_say_cmd(cmd), cap_s, attempt + 1, retries + 1))
        else:
            said.append("RenderHangError: `%s` made no CPU progress for %.0f s (%.2f CPU-s across its %d processes) "
                        "and was killed (attempt %d of %d)%s" % (_say_cmd(cmd), idle_s, spent, n, attempt + 1,
                                                                 retries + 1, "; diagnostics in " + where if where else ""))
        sys.stderr.write("[render] %s%s\n" % (said[-1], "; retrying once" if attempt < retries
                                                else "; not retried again: reported as a failed render"))
        sys.stderr.flush()
    if said:
        note = "\n".join(said) + "\n"
        if isinstance(err, bytes):
            err = err + note.encode()
        elif isinstance(err, str):
            err = err + "\n" + note
    if check and rc:
        raise subprocess.CalledProcessError(rc, cmd, out, err)
    return subprocess.CompletedProcess(cmd, rc, out, err)
