#!/usr/bin/env python3
"""THE CINEMATIC TIER, ONE BEAT AT A TIME — render the film as per-beat segments and keep the ones that did
not change.

    python3 scripts/remotion_segments.py <out_dir> --plan     # which beats a render would redo, and why

WHY THIS EXISTS. `render_remotion.py` rendered the whole Film in one `npx remotion render`, so any edit
re-rendered every beat. SKILL.md records a 15-minute render for a 37-beat film, and on a machine with ~1 GB
free that render failed repeatedly — a one-beat fix the user asked for never reached the delivered film.
The html tier has had a per-slide clip cache from the start; this is the same idea on the other tier.

WHY IT IS THE SAME FILM. Every segment is rendered from the SAME props file with `--frames=a-b`, so frame f
of a segment is frame f of the full render by construction: a Remotion composition is a pure function of
the frame (its own contract, and the reason it can render frames in parallel tabs at all). Nothing is
re-laid-out or re-timed. Segment k is scene k's share of the timeline — from the first frame scene k is
mounted (the seam INTO it) to the frame before scene k+1 is. Video is joined with `-c copy`. Audio travels
in each segment as lossless PCM, is joined as raw samples and encoded ONCE: an AAC join at every boundary
would leave a priming gap at each one.

WHAT A SEGMENT DEPENDS ON — the cache key, read off Film.tsx, and pinned against it by
tests/test_remotion_segments.py so a new cross-scene read fails a test instead of serving a stale beat:
  * scene k, all of it, and its INDEX — the camera bed's direction alternates by index (bedPan);
  * scene k-1, all of it — its tail plays under the seam into k, and pickPresentation reads both beats;
  * whether k is the LAST scene — the outro veil and the caption's closing window;
  * on a STAGE RUN (scripts/stage_runs.py), every beat of the run and the files they name — one stage
    component draws the run, each frame a move between two beats' states, its face from the run's first beat;
  * the ABSOLUTE frames [a, b] — the Atmosphere's glow and the whole-film drift read the absolute frame;
  * every prop that is not `scenes` — DNA, theme, captions, brand, aspect, reduced motion, camera;
  * the CONTENT of every file any of those names — a re-synthesised mp3 at the same path is a new beat;
  * the code: every file under remotion/src, what it imports from outside src (the fonts), the lockfile
    and the bundler config.

THE HONEST LIMIT. Editing a beat's NARRATION changes its length, so every later beat starts on a different
frame. The Atmosphere's glow pulses on the absolute frame and nothing guarantees it is covered — BeatGround
paints nothing for a beat that declares no ground, so coverage is each of 185 registers' own business — so
those later beats are re-rendered too. A VISUAL edit (a prop, a register, a ground, a seam: everything the
shot-critic loop changes) re-renders that beat and the one after it, and nothing else.
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REMOTION = os.path.join(SKILL, "remotion")

FPS = 30
SAMPLE_RATE = 48000        # Remotion's default (renderer/dist/options/sample-rate.js)
AUDIO_BITRATE = "320k"     # what a full render ships: 317 kb/s AAC-LC measured on a delivered film
CACHE_DIR = ".remotion_segments"
CACHE_VERSION = 1          # bump when the MEANING of a key changes, so every old segment is re-rendered


def _wk(env):
    """subprocess kwargs for a film's environment — none at all when it has no workshop (scripts/workshop.py)."""
    import workshop as _ws
    return _ws.env_kwargs(env)


def default_gl():
    """The GL backend a render uses — ONE definition, because it is in every key: `--plan` asking with a
    different one would report every cached beat as stale."""
    return os.environ.get("REMOTION_GL") or ("angle" if sys.platform in ("darwin", "win32") else "swangle")


def pixel_flags(gl):
    """What reaches the pixels besides the props and the code. `--log`, `--timeout` and `--concurrency` do
    not, so they are not in the key."""
    return {"gl": gl, "codec": "h264", "audio": "pcm-16"}


# ── ONE BACKEND PER FILM ────────────────────────────────────────────────────────────────────────────────
# A GL backend is part of the picture, not a performance knob. Measured on this machine (the effects research's
# probes, 2026-10-24): the same frame rendered with --gl=angle and --gl=swangle differs by up to 10/255 on a
# plain gradient and by up to 255/255 on 3D or HtmlInCanvas content, while the same backend re-rendered is
# bit-identical (9/9) and concurrency 1 vs 3 stays within 2/255 on at most 0.003% of the pixels. A film whose
# beats come from two backends therefore carries a visible step at the cut where the backend changes.
#
# The renderer used to do exactly that: a segment that failed under --gl was retried WITHOUT --gl (whatever
# Chrome then picks), cached under a key that still said `angle`, and joined with neighbours rendered on angle.
# Now a GL failure on one beat re-renders the WHOLE film on the named fallback backend (the failing beat
# first, so a beat that fails there too — a register that throws, not a GL problem — is reported before
# anything else is rendered), every segment is keyed by the backend it was really drawn on, and the backend
# is written into the render record. `REMOTION_GL_FALLBACK=0` refuses the fallback and fails loudly instead.
FALLBACK_GL = "swangle"     # software ANGLE: slower, but present wherever Chrome is, and NAMED — never "no flag"
RECORD = ".render_record.json"


class BackendFailure(RuntimeError):
    """A beat failed on the film's GL backend and could not be rendered on the fallback either (or the fallback
    is disabled). Raised with both reasons, so the person reading it can tell a GL problem from a register."""


def gl_of(cli_flags):
    """The --gl value in a CLI flag list, or None when the list names none."""
    vals = [a.split("=", 1)[1] for a in cli_flags if a.startswith("--gl=")]
    if len(vals) > 1:
        raise ModelMismatch("the render flags name %d GL backends (%s) — a film renders on exactly one"
                            % (len(vals), ", ".join(vals)))
    return vals[0] if vals else None


def fallback_gl(gl):
    """The backend a film is re-rendered on when `gl` fails, or None: no --gl to fall back FROM, already on the
    fallback, or `REMOTION_GL_FALLBACK=0` (the caller then fails loudly with the original error)."""
    if not gl or gl == FALLBACK_GL or os.environ.get("REMOTION_GL_FALLBACK", "1") == "0":
        return None
    return FALLBACK_GL


def with_gl(cli_flags, gl):
    """The same flags on another backend — the only flag that changes."""
    return [a for a in cli_flags if not a.startswith("--gl=")] + ["--gl=" + gl]


def write_record(out_dir, record):
    """`<out_dir>/.render_record.json`: which backend drew the delivered film, and how. Written atomically."""
    path = os.path.join(out_dir, RECORD)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
    os.replace(tmp, path)
    return path


class ModelMismatch(RuntimeError):
    """The segment model disagrees with what Remotion rendered. Never shipped: the caller renders whole."""


def js_round(x):
    """`Math.round`, which Film.tsx uses: halves go UP. Python's round() sends 150.5 to 150 and the film to
    151, and one frame of disagreement per beat is a film whose seams all land in the wrong segment."""
    return int(math.floor(float(x) + 0.5))


def seam_frames():
    """SEAM_FRAMES, read from runtime/motion.ts rather than restated, so the two cannot drift."""
    src = open(os.path.join(REMOTION, "src", "runtime", "motion.ts"), encoding="utf-8").read()
    m = re.search(r"export const SEAM_FRAMES\s*=\s*(\d+)", src)
    if not m:
        raise ModelMismatch("SEAM_FRAMES not found in runtime/motion.ts — the segment timeline is derived from it")
    return int(m.group(1))


def timeline(scenes, tr):
    """([(a, b)] inclusive frame range per scene, total) — Film.tsx's TransitionSeries layout exactly: scene
    k+1 is mounted `tr` frames before scene k ends, and filmDuration is the sum of the rounded durations
    less one `tr` per cut."""
    if not scenes:
        raise ModelMismatch("a film with no scenes has no timeline")
    durs = [max(1, js_round(s.get("durF", 0))) for s in scenes]
    # a beat that CONTINUES a stage run (scripts/stage_runs.py) has no seam before it: it starts on the frame the run's
    # previous beat ends, where a beat after a cut mounts `tr` frames early — Film.tsx `sceneStarts`, exactly
    import stage_runs as _sr
    joined = _sr.joined_flags(scenes)
    starts, acc = [], 0
    for k, d in enumerate(durs):
        starts.append(acc)
        acc += d - (tr if k + 1 < len(durs) and not joined[k + 1] else 0)
    total = max(1, sum(durs) - sum(1 for k in range(1, len(durs)) if not joined[k]) * tr)
    out = []
    for k in range(len(scenes)):
        a = starts[k]
        b = starts[k + 1] - 1 if k + 1 < len(scenes) else total - 1
        if b < a:
            raise ModelMismatch("scene %d is %d frames, no longer than the %d-frame seam, so it owns no frames "
                                "of its own" % (k, durs[k], tr))
        out.append((a, b))
    return out, total


# ── the key ─────────────────────────────────────────────────────────────────────────────────────────────
def _canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_FILE_SHA = {}


def file_sha(path):
    st = os.stat(path)
    memo = (os.path.realpath(path), st.st_size, st.st_mtime_ns)
    if memo not in _FILE_SHA:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        _FILE_SHA[memo] = h.hexdigest()
    return _FILE_SHA[memo]


def referenced_files(obj, public_dir):
    """{name: sha256} for every string in `obj` naming a file inside the public dir — what `staticFile()`
    will load. Every staticFile call in the film takes its argument from a prop, the beat's mp3 or the
    brand block, so walking the props finds them all without knowing any register."""
    root = os.path.realpath(public_dir)
    found = {}

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        elif isinstance(v, str) and 0 < len(v) < 1024 and "\n" not in v:
            p = os.path.realpath(os.path.join(root, v.lstrip("/")))
            if p.startswith(root + os.sep) and os.path.isfile(p):
                found[v] = file_sha(p)

    walk(obj)
    return found


_IMPORT = re.compile(r"""(?:\bfrom\s+|\bimport\s*\(\s*|\brequire\s*\(\s*|^\s*import\s+)['"](\.{1,2}/[^'"]+)['"]""",
                     re.M)
_EXTS = ("", ".ts", ".tsx", ".js", ".jsx", ".json", "/index.ts", "/index.tsx", "/index.js")


def code_files(out_dir=None):
    """Every file the bundle is built from: remotion/src, whatever src imports from OUTSIDE src (the fonts
    live in the skill's assets/fonts), the lockfile and the bundler/TypeScript config — and, for a film with
    a workshop, every source of it (scripts/workshop.py)."""
    src = os.path.join(REMOTION, "src")
    files = set()
    for dp, dn, fn in os.walk(src):
        dn[:] = sorted(d for d in dn if d != "node_modules" and not d.startswith("."))
        for f in fn:
            p = os.path.join(dp, f)
            files.add(p)
            if not f.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".css")):
                continue
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for m in _IMPORT.finditer(text):
                base = os.path.normpath(os.path.join(dp, m.group(1)))
                if base.startswith(src + os.sep):
                    continue                                   # walked anyway
                hit = next((base + e for e in _EXTS if os.path.isfile(base + e)), None)
                if hit is None:
                    raise ModelMismatch("%s imports %r from outside src and it resolves to no file — the "
                                        "cache cannot hash what it cannot find" % (p, m.group(1)))
                files.add(hit)
    for extra in ("package.json", "package-lock.json", "remotion.config.ts", "remotion.config.js", "tsconfig.json"):
        p = os.path.join(REMOTION, extra)
        if os.path.isfile(p):
            files.add(p)
    if out_dir:
        import workshop as _ws
        files.update(_ws.code_files(out_dir))
    return sorted(files)


def code_hash(out_dir=None):
    """The code a segment is built from. The library hashes exactly as it always has — the same order,
    the same relative-path spelling — so a film with no workshop keeps a byte-identical key on every OS and
    on every disk layout. A workshop file is keyed by its path INSIDE the workshop and the workshop's own
    files are sorted by THAT key, never by their absolute path: two spellings of the same folder (a macOS
    volume alias is one) can sort on opposite sides of `SKILL`, and a merged, absolute-path sort would then
    hash the library and the workshop in a different relative order for the same film — a spurious full
    re-render, not a stale reuse, but a re-render all the same."""
    h = hashlib.sha256()
    for p in code_files():
        h.update(os.path.relpath(p, SKILL).encode("utf-8"))
        h.update(b"\0")
        h.update(file_sha(p).encode("ascii"))
        h.update(b"\n")
    if out_dir:
        import workshop as _ws
        ws_root = _ws.workshop_dir(out_dir) + os.sep
        keyed = sorted(("workshop/" + os.path.relpath(p, ws_root).replace(os.sep, "/"), p)
                       for p in _ws.code_files(out_dir))
        for rel, p in keyed:
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(file_sha(p).encode("ascii"))
            h.update(b"\n")
    return h.hexdigest()


def beat_code_hash(out_dir, scenes):
    """The workshop code the given scenes are built from (workshop.beat_files), keyed like code_hash keys the
    workshop: by path inside it, sorted by that, so moving the film never re-renders it. "" for none."""
    import workshop as _ws
    ws_root = _ws.workshop_dir(out_dir) + os.sep
    files = set()
    for sc in scenes:
        if isinstance(sc, dict):
            files.update(_ws.beat_files(out_dir, sc.get("shot"), sc.get("props")))
    if not files:
        return ""
    h = hashlib.sha256()
    for rel, p in sorted(("workshop/" + os.path.relpath(p, ws_root).replace(os.sep, "/"), p) for p in files):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(file_sha(p).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


TEASER_SHOTS = {"ColdOpen", "Callback"}     # mirrors runtime/teaser.tsx TEASER_SHOTS


def teaser_beats(scenes, k):
    """The 0-based scenes that scene k draws as teasers (its `props.beats`, 1-based), [] for any other beat."""
    sc = scenes[k] if 0 <= k < len(scenes) else {}
    if sc.get("shot") not in TEASER_SHOTS:
        return []
    beats = (sc.get("props") or {}).get("beats") or []
    return [b - 1 for b in beats if isinstance(b, int) and 1 <= b <= len(scenes) and b - 1 != k]


def plan(props, public_dir, flags, tr=None, code=None):
    """([{k, a, b, key}], total). Pure given its inputs — the render and the `--plan` report ask the same
    function.

    THE WORKSHOP IS KEYED PER BEAT. With `code` left to this function, the film-wide part hashes the LIBRARY
    only, and each segment adds the workshop files its own scenes (the beat and the one dissolving out of it)
    are built from — so editing one built object re-renders the beats that use it and no other. Which items
    EXIST still reaches every key through the film-wide hash of their names (the generated index is a
    function of them). A caller that passes `code` keeps the old single film-wide hash."""
    tr = seam_frames() if tr is None else tr
    scenes = props.get("scenes") or []
    ranges, total = timeline(scenes, tr)
    per_beat = code is None and bool(public_dir) and os.path.isdir(os.path.join(os.path.abspath(public_dir),
                                                                                "workshop"))
    if code is None:
        code = code_hash(None)
        if per_beat:
            import workshop as _ws
            ws_root = _ws.workshop_dir(public_dir) + os.sep
            names = sorted("workshop/" + os.path.relpath(p, ws_root).replace(os.sep, "/")
                           for p in _ws.code_files(public_dir))
            code = _sha(_canon({"lib": code, "workshop_names": names}))
    film = {k: v for k, v in props.items() if k != "scenes"}
    # THE ROOT FILL IS SCENE 0's OPENING GROUND (Film.tsx `rootBg`), under every frame of the film. It is
    # covered by the Atmosphere's opaque fill, so this is belt and braces — and cheap, because only what
    # decides that ground goes in: at frame 0 a ramp sits at its `from` whatever the beat's length, except
    # under reduced motion, where the ground freezes at a point that does depend on it.
    s0 = scenes[0] if scenes else {}
    root = {f: s0.get(f) for f in ("ground", "key", "shot")}
    if props.get("reducedMotion"):
        root["durF"] = s0.get("durF")
    g = _sha(_canon({"v": CACHE_VERSION, "film": film, "files": referenced_files(film, public_dir), "root": root,
                     "code": code, "flags": flags, "tr": tr, "fps": FPS, "sr": SAMPLE_RATE}))
    # A STAGE RUN's frames depend on every beat of the run (a frame is a move from one beat's state to the next), so
    # each of its segments keys on the whole run, not on itself and the beat before
    import stage_runs as _sr
    run_of = {}
    for first, last, _r in _sr.runs(scenes):
        for k in range(first, last + 1):
            run_of[k] = scenes[first:last + 1]
    segs = []
    for k, (a, b) in enumerate(ranges):
        prev = scenes[k - 1] if k else None
        # the files too: a run draws its FIRST beat's face (CardStage's `image`) in every one of its beats, so a
        # re-made card.png at the same path must re-render the run's last beat, whose prev never names it
        around = [prev, scenes[k]] + list(run_of.get(k, []))
        body = {"g": g, "k": k, "a": a, "b": b, "last": k == len(scenes) - 1, "prev": prev, "cur": scenes[k],
                "files": referenced_files(around, public_dir)}
        if k in run_of:
            body["run"] = run_of[k]
        # A BEAT BUILT OF OTHER BEATS (runtime/teaser: ColdOpen, Callback) draws each beat it names, frozen — so its
        # frames depend on those beats' whole scenes (their props, their grounds, their lengths), wherever in the film
        # they are. Keyed on them, an edit to a teased beat re-renders the cold open that flashes it.
        teased = teaser_beats(scenes, k)
        if teased:
            body["teased"] = [scenes[j] for j in teased]
            body["n"] = len(scenes)
            around = around + body["teased"]
            body["files"] = referenced_files(around, public_dir)
        if per_beat:
            body["ws"] = beat_code_hash(public_dir, around)
        segs.append({"k": k, "a": a, "b": b, "key": _sha(_canon(body))})
    return segs, total


# ── rendering and joining ───────────────────────────────────────────────────────────────────────────────
def seg_path(cache, key):
    return os.path.join(cache, key[:40] + ".mov")


def _probe(path, stream, entries):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries",
                        "stream=" + entries, "-of", "json", path], capture_output=True, text=True)
    if r.returncode != 0:
        raise ModelMismatch("ffprobe could not read %s: %s" % (path, r.stderr.strip()[-300:]))
    st = json.loads(r.stdout or "{}").get("streams") or []
    return st[0] if st else None


def video_frames(path):
    st = _probe(path, "v:0", "nb_frames")
    if not st or not str(st.get("nb_frames", "")).isdigit():
        raise ModelMismatch("%s has no countable video stream" % path)
    return int(st["nb_frames"])


TIMESCALE = 90000          # Remotion's own `-video_track_timescale`; every segment is held to it before a join


def video_timing(path):
    """(frames, seconds, time_base) of a file's video stream, as ffprobe reads them."""
    st = _probe(path, "v:0", "nb_frames,duration,time_base")
    if not st or not str(st.get("nb_frames", "")).isdigit():
        raise ModelMismatch("%s has no countable video stream" % path)
    try:
        dur = float(st.get("duration"))
    except (TypeError, ValueError):
        dur = float("nan")
    return int(st["nb_frames"]), dur, str(st.get("time_base") or "")


def timing_ok(frames, seconds, fps=None):
    """Whether a stream of `frames` frames lasts what it should at the film's fps (within one frame)."""
    fps = fps or FPS
    return seconds == seconds and abs(seconds - frames / float(fps)) <= 1.0 / fps + 1e-6


def normalized_segment(path, work):
    """`path`, or a stream-copy of it re-timed onto TIMESCALE when its video does not last its frame count.

    A SEGMENT CAN COME BACK ON ANOTHER TIME BASE. Measured on a benchmark film: one of ten segments rendered with a
    video time_base of 1/16000 where the other nine had 1/90000, and a `-c copy` concat of the ten produced an
    out.mp4 whose video stream lasted 352.6 s for 1882 frames against 62.8 s of audio — accepted, because the join
    counted frames only. A stream copy with `-video_track_timescale` re-times it without re-encoding a pixel; a
    segment that still does not last its frames after that is refused (the caller renders whole)."""
    frames, dur, tb = video_timing(path)
    if timing_ok(frames, dur) and tb == "1/%d" % TIMESCALE:
        return path
    fixed = os.path.join(work, "retimed_" + os.path.basename(path))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-map", "0", "-c", "copy",
                    "-video_track_timescale", str(TIMESCALE), fixed], check=True)
    f2, d2, tb2 = video_timing(fixed)
    if f2 != frames or not timing_ok(f2, d2):
        raise ModelMismatch("segment %s lasts %.3f s for %d frames (time base %s) and could not be re-timed (%.3f s, %s)"
                            % (os.path.basename(path), dur, frames, tb, d2, tb2))
    print("[segments] re-timed %s: %s %.3f s -> %s %.3f s for %d frames"
          % (os.path.basename(path), tb, dur, tb2, d2, frames))
    return fixed


_QUOTED_PATH = re.compile(r"""['"`]([^'"`$\n]{1,300}\.[A-Za-z0-9]{2,5})['"`]""")
_CODE_EXTS = (".ts", ".tsx", ".js", ".jsx")


def workshop_named_files(public_dir):
    """{name} of every file in the public dir a film's OWN shot names in its code. The library's registers take
    every file from a prop; a workshop shot may write `staticFile('media/b3/logo_drive.png')` or return that path
    from a helper (measured on a Grok Bot film, whose census then lost the logo and hung)."""
    root = os.path.realpath(public_dir)
    found = set()
    for d, _n, fs in os.walk(os.path.join(root, "workshop")):
        for f in fs:
            if not f.endswith(_CODE_EXTS):
                continue
            with open(os.path.join(d, f), encoding="utf-8", errors="replace") as fh:
                for m in _QUOTED_PATH.finditer(fh.read()):
                    v = m.group(1)
                    p = os.path.realpath(os.path.join(root, v.lstrip("/")))
                    if p.startswith(root + os.sep) and os.path.isfile(p) and not p.endswith(_CODE_EXTS):
                        found.add(v)
    return found


def minimal_public(props, public_dir, dest):
    """A public folder holding exactly the files the props name, linked (copied across filesystems).

    A bundle COPIES its public folder, and the real one is the film's out_dir — old renders, contest clips
    and this cache itself. Every library register's `staticFile()` takes its argument from a prop, the beat's
    mp3 or the brand block (checked across all 185 registers when this was written); a film's own workshop
    shots may also name files in their code (workshop_named_files). The same decoded MD5 came out of both
    folders on the 37-beat film."""
    names = set(referenced_files(props, public_dir)) | workshop_named_files(public_dir)
    for name in names:
        src = os.path.join(public_dir, name.lstrip("/"))
        dst = os.path.join(dest, name.lstrip("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            continue
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
    os.makedirs(dest, exist_ok=True)
    return dest


def _bundle(dest, public, run=subprocess.run, env=None):
    """Bundle the film ONCE for all the segments of this render — with the film's workshop, when it has one."""
    run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + dest, "--public-dir=" + public,
         "--log=error"], cwd=REMOTION, check=True, **_wk(env))
    if not os.path.isfile(os.path.join(dest, "index.html")):
        raise ModelMismatch("`remotion bundle` produced no index.html in %s" % dest)
    return dest


def render_segment(seg, last, props_path, public_dir, cache, cli_flags, run=subprocess.run, serve=None, env=None):
    """Render one segment to its cache file, atomically: a crash leaves no half file under the final name.

    `serve` is a bundle built once for the whole render (see `_bundle`); without one the CLI bundles from
    the entry point on every call, which measured 1.5-2 s of each segment's ~5 s of fixed cost."""
    final = seg_path(cache, seg["key"])
    tmp = final[:-4] + ".part.mov"
    if os.path.exists(tmp):
        os.remove(tmp)
    # the LAST segment runs to Remotion's own end ("a-"), so a timeline that came out one frame short can
    # never silently drop the close — it surfaces below as a frame count that disagrees with the model
    frames = "%d-%s" % (seg["a"], "" if last else seg["b"])
    source = ([serve] if serve else ["src/index.ts"])
    # ABSOLUTE, like the props and the public dir: the CLI runs in remotion/, so a relative path would put the
    # beat under remotion/<out_dir>/ while the cache looks for it under <out_dir>/ — found by nobody.
    cmd = (["npx", "remotion", "render"] + source + ["Film", os.path.abspath(tmp), "--codec=h264", "--audio-codec=pcm-16",
           "--enforce-audio-track", "--frames=" + frames, "--props=" + os.path.abspath(props_path)]
           + ([] if serve else ["--public-dir=" + os.path.abspath(public_dir)]) + list(cli_flags))
    # NO RETRY HERE. A retry on another backend inside one segment is how a film came to mix backends; a GL
    # failure propagates to render_film, which re-renders the whole film on the fallback (see FALLBACK_GL).
    # A HANG is the exception, retried once on the SAME backend: the real render is WATCHED (_common.watched_run) —
    # a segment whose process tree stops working is killed, said, and re-run; one that hangs twice fails like any
    # other render (exit 124), so it falls back like one.
    import _common as _c
    (_c.watched_run if run is _c._REAL_RUN else run)(cmd, cwd=REMOTION, check=True, **_wk(env))
    got, want = video_frames(tmp), seg["b"] - seg["a"] + 1
    if got != want:
        os.remove(tmp)
        raise ModelMismatch("beat %d rendered %d frames where the timeline model expects %d (frames %s) — the "
                            "model and Film.tsx disagree; nothing from this run is kept" % (seg["k"], got, want, frames))
    os.replace(tmp, final)
    return final


def _pcm(path, n_samples, channels):
    """Exactly `n_samples` frames of s16le PCM from a segment — the segment's own audio, never resampled."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-f", "s16le", "-acodec",
                        "pcm_s16le", "-ac", str(channels), "-ar", str(SAMPLE_RATE), "pipe:1"],
                       capture_output=True)
    if r.returncode != 0:
        raise ModelMismatch("could not read the audio of %s: %s" % (path, r.stderr.decode(errors="replace")[-300:]))
    want = n_samples * channels * 2
    got = len(r.stdout)
    # More than one video frame of disagreement is not rounding, it is a different timeline.
    if abs(got - want) > (SAMPLE_RATE // FPS) * channels * 2:
        raise ModelMismatch("%s carries %d audio samples where %d were expected" % (
            path, got // (channels * 2), n_samples))
    return r.stdout[:want] + b"\0" * max(0, want - got)


def assemble(segs, files, out_mp4, work):
    """Join the segments: video by stream copy, audio as raw samples encoded once."""
    first = _probe(files[0], "a:0", "channels,sample_rate")
    if not first:
        raise ModelMismatch("%s has no audio stream" % files[0])
    ch = int(first["channels"])
    # every segment on one time base, lasting its own frames, before a stream-copy join (normalized_segment)
    joined = [normalized_segment(f, work) for f in files]
    lst = os.path.join(work, "concat.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        for f in joined:
            fh.write("file '%s'\n" % os.path.abspath(f).replace("'", "'\\''"))
    vid = os.path.join(work, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-map", "0:v:0",
                    "-c", "copy", vid], check=True)
    raw = os.path.join(work, "audio.s16le")
    with open(raw, "wb") as out:
        for s, f in zip(segs, files):
            out.write(_pcm(f, (s["b"] - s["a"] + 1) * SAMPLE_RATE // FPS, ch))
    tmp = out_mp4 + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vid, "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", str(ch),
                    "-i", raw, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", AUDIO_BITRATE,
                    "-movflags", "+faststart", tmp], check=True)
    want = sum(s["b"] - s["a"] + 1 for s in segs)
    got, vdur, _tb = video_timing(tmp)
    if got != want:
        raise ModelMismatch("the joined film has %d frames, the segments %d" % (got, want))
    # and it LASTS them: the frame count alone accepted a 352 s video stream under 62.8 s of audio
    adur = _probe(tmp, "a:0", "duration") or {}
    try:
        adur = float(adur.get("duration"))
    except (TypeError, ValueError):
        adur = float("nan")
    if not timing_ok(got, vdur) or not (abs(adur - vdur) <= 2.0 / FPS):
        raise ModelMismatch("the joined film's video lasts %.3f s for %d frames (%.3f s expected) against %.3f s of "
                            "audio" % (vdur, got, got / float(FPS), adur))
    os.replace(tmp, out_mp4)
    for p in [lst, vid, raw] + [f for f in joined if f not in files]:
        if os.path.exists(p):
            os.remove(p)


def render_film(out_dir, props, props_path, out_mp4, cli_flags, flags, log=print, run=subprocess.run, labels=None):
    """Render `out_mp4` from cached and fresh segments, every one of them on ONE GL backend. Returns a summary
    dict whose `gl` is the backend that drew the film (and `gl_fallback_from` / `gl_reason` when it is not the
    one asked for).

    `labels` are the board's own beat numbers, for messages only: a person fixes "beat 21" by opening the
    board's index 21, and position+1 is not always that (the audition printed index+1 and pointed at the
    wrong slide)."""
    name = (lambda k: labels[k]) if labels else (lambda k: k + 1)
    gl = gl_of(cli_flags)
    if gl and flags.get("gl") not in (None, gl):
        raise ModelMismatch("the CLI renders on --gl=%s but the cache keys say gl=%s — a segment would be cached "
                            "under a backend that did not draw it" % (gl, flags.get("gl")))
    try:
        done = _render_film_on(out_dir, props, props_path, out_mp4, cli_flags, flags, log, run, name)
        done.update(gl=gl)
        return done
    except subprocess.CalledProcessError as first:
        beat = getattr(first, "beat", None)
        fb = fallback_gl(gl)
        if fb is None:
            raise
        log("[segments] beat %s failed on --gl=%s. A film is drawn on ONE backend (angle and swangle differ by up "
            "to 10/255 on a gradient, far more in 3D), so the WHOLE film is re-rendered on --gl=%s — beat %s first."
            % (name(beat) if beat is not None else "?", gl, fb, name(beat) if beat is not None else "?"))
        try:
            done = _render_film_on(out_dir, props, props_path, out_mp4, with_gl(cli_flags, fb), dict(flags, gl=fb),
                                   log, run, name, first=beat)
        except subprocess.CalledProcessError as second:
            raise BackendFailure(
                "beat %s failed on --gl=%s AND on the fallback --gl=%s, so it is not a GL problem — the register "
                "or the machine (memory: REMOTION_CONCURRENCY=1) is. First failure: %s. Second: %s."
                % (name(beat) if beat is not None else "?", gl, fb, first, second)) from second
        done.update(gl=fb, gl_fallback_from=gl, gl_reason="beat %s failed on --gl=%s: %s"
                    % (name(beat) if beat is not None else "?", gl, first))
        return done


def _render_film_on(out_dir, props, props_path, out_mp4, cli_flags, flags, log, run, name, first=None):
    """One attempt at the film on the backend `flags` names. `first` = a beat index to render before the others."""
    cache = os.path.join(out_dir, CACHE_DIR)
    os.makedirs(cache, exist_ok=True)
    segs, total = plan(props, out_dir, flags)
    # The ranges must TILE the film: contiguous from frame 0 to the last, nothing doubled, nothing missing.
    # `timeline` builds them that way; this is the check that it still does, before a frame is rendered.
    if segs[0]["a"] != 0 or segs[-1]["b"] != total - 1 or any(
            n["a"] != p["b"] + 1 for p, n in zip(segs, segs[1:])):
        raise ModelMismatch("the segment ranges do not tile the film's %d frames: %r"
                            % (total, [(s["a"], s["b"]) for s in segs]))
    stale = [s for s in segs if not os.path.exists(seg_path(cache, s["key"]))]
    if first is not None:                               # the beat that failed on the other backend goes first
        stale.sort(key=lambda s: s["k"] != first)
    log("[segments] %d beat(s): %d reused, %d to render%s" % (
        len(segs), len(segs) - len(stale), len(stale),
        (" (beats %s)" % ", ".join(str(name(s["k"])) for s in stale[:12]) + (" ..." if len(stale) > 12 else ""))
        if stale else ""))
    import workshop as _ws
    env = _ws.prepare(out_dir)       # the film's workshop enters the bundle here
    work = tempfile.mkdtemp(prefix="remotion_segments_") if stale else None
    try:
        serve = (_bundle(os.path.join(work, "bundle"), minimal_public(props, out_dir, os.path.join(work, "public")),
                         run=run, env=env) if stale else None)
        _render_stale(stale, segs, props_path, out_dir, cache, cli_flags, run, serve, name, log, env=env)
    finally:
        if work:
            shutil.rmtree(work, ignore_errors=True)
    files = [seg_path(cache, s["key"]) for s in segs]
    assemble(segs, files, out_mp4, cache)
    keep = {os.path.basename(f) for f in files}
    for f in os.listdir(cache):                         # a superseded segment is dead weight on a tight disk
        if f.endswith(".mov") and f not in keep:
            os.remove(os.path.join(cache, f))
    return {"beats": len(segs), "rendered": [s["k"] for s in stale], "frames": total,
            "segments": [(s["a"], s["b"], s["key"]) for s in segs]}


def _render_stale(stale, segs, props_path, out_dir, cache, cli_flags, run, serve, name, log, env=None):
    for i, s in enumerate(stale):
        log("[segments] rendering beat %s (%d of %d to render, frames %d-%d)"
            % (name(s["k"]), i + 1, len(stale), s["a"], s["b"]))
        try:
            render_segment(s, s["k"] == len(segs) - 1, props_path, out_dir, cache, cli_flags, run=run, serve=serve,
                           env=env)
        except subprocess.CalledProcessError as e:
            e.beat = s["k"]                             # render_film names it, and renders it first on the fallback
            # A real render failure (memory, a register that throws) is not the model's fault and a whole
            # render would hit it too. Say what is already safe, so a re-run is a resume, not a restart.
            log("[segments] beat %s failed. %d of %d beat(s) are cached in %s/ — re-running the same command "
                "renders only the rest (REMOTION_CONCURRENCY=1 lowers memory)."
                % (name(s["k"]), len(segs) - len(stale) + i, len(segs), CACHE_DIR))
            raise


def main(argv=None):
    ap = argparse.ArgumentParser(description="Which beats of a remotion film the next render would redo.")
    ap.add_argument("out_dir")
    ap.add_argument("--plan", action="store_true", help="(the default and only action)")
    ap.add_argument("--vertical", action="store_true", help="plan the render_remotion.py --vertical film")
    ap.add_argument("--reduced-motion", action="store_true", help="plan the --reduced-motion film")
    a = ap.parse_args(argv)
    # THE BOARD AS IT IS NOW, built by the renderer's own function — not the last render's props file,
    # which would report every beat as cached right after an edit.
    import render_remotion as rr
    import storyboard as sb
    data = sb.load(os.path.join(a.out_dir, "storyboard.json"))
    props, slides = rr.film_props(a.out_dir, data, reduced_motion=a.reduced_motion, vertical=a.vertical)
    segs, total = plan(props, a.out_dir, pixel_flags(default_gl()))
    cache = os.path.join(a.out_dir, CACHE_DIR)
    todo = 0
    for s in segs:
        hit = os.path.exists(seg_path(cache, s["key"]))
        todo += not hit
        print("  beat %-4s frames %5d-%-5d %s" % (slides[s["k"]].get("index", s["k"] + 1), s["a"], s["b"],
                                                 "cached" if hit else "RENDER"))
    print("[segments] the next render redoes %d of %d beat(s) (%d frames in the film)" % (todo, len(segs), total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
