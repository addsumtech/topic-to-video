#!/usr/bin/env python3
"""A beat's Blender plate: a 3D render a workshop shot draws under its own overlay.

    python3 scripts/blender_plate.py <out_dir> [--only ID] [--still F] [--yes]

Blender draws what 3D physicality is the content of — a real place or object, a material, a physical process, an
optical effect, a space to move through — and nothing else: words, captions, timing, data and layout stay in
Remotion (docs/superpowers/specs/2026-11-04-blender-plates-design.md, references/blender-plates.md). A plate is
`media/blender/<id>/`: plate.webm (VP9 with alpha), anchors.json, boxes.json, camera.json, plate.json.
"""
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MIN_BLENDER = (5, 0)            # 5.0 renamed EEVEE's engine id to BLENDER_EEVEE and dropped scene.node_tree
_APP_PATHS = ("/Applications/Blender.app/Contents/MacOS/Blender",)


class PlateError(Exception):
    pass


def _runnable(p):
    return bool(p) and os.path.isfile(p) and os.access(p, os.X_OK)


def blender_bin(meta=None):
    """The Blender binary: meta.blender, then $TTV_BLENDER, then the macOS app, then `blender` on PATH; None if none."""
    for p in ((meta or {}).get("blender"), os.environ.get("TTV_BLENDER"), *_APP_PATHS):
        if _runnable(p):
            return p
    return shutil.which("blender")


def _version_line(binary):
    r = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=60)
    return (r.stdout or "").strip().splitlines()[0] if (r.stdout or "").strip() else ""


def blender_version(binary):
    """(major, minor, patch, is_release_candidate) from `blender --version`."""
    line = _version_line(binary)
    m = re.search(r"Blender\s+(\d+)\.(\d+)(?:\.(\d+))?", line)
    if not m:
        raise PlateError("%s --version printed no version line (%r)" % (binary, line[:80]))
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), "release candidate" in line.lower()


def require_blender(meta=None):
    """The binary to run, or PlateError saying why there is none. A release candidate runs, with a WARN."""
    b = blender_bin(meta)
    if not b:
        raise PlateError("Blender not found — install Blender >= %d.%d (blender.org) or set TTV_BLENDER / "
                         "meta.blender to its binary" % MIN_BLENDER)
    v = blender_version(b)
    if v[:2] < MIN_BLENDER:
        raise PlateError("Blender %d.%d.%d at %s is older than %d.%d" % (v[0], v[1], v[2], b, *MIN_BLENDER))
    if v[3]:
        print("[blender_plate] WARN Blender %d.%d.%d is a release candidate — pin a release for delivery" % v[:3])
    return b


# ── the board contract: slide.blender ─────────────────────────────────────────────────────────────────────────
import hashlib  # noqa: E402
import json  # noqa: E402

# What a built plate CONTAINS. Raise it whenever the build writes something new a reader depends on: a plate made by an
# older build is then stale, not "fresh" without it (format 2 kept the ID pass, which plate_qa now reads).
PLATE_FORMAT = 3
BLENDER_WHY = ("real-world", "material", "physics", "optics", "space")
MODES = ("rgba", "env")
ENGINES = ("eevee", "cycles")
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT_DIR = os.path.join(SKILL_ROOT, "blender")


def _inside(root, rel):
    p = os.path.realpath(os.path.join(root, rel))
    return p if p.startswith(os.path.realpath(root) + os.sep) else None


def _strings(v):
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)


def spec_of(slide, out_dir):
    """The beat's normalised Blender spec, or None when it has none; PlateError listing EVERY problem."""
    b = slide.get("blender")
    if b is None:
        return None
    if not isinstance(b, dict):
        raise PlateError("blender: must be an object {id, scene, why, ...}")
    import workshop as _ws
    bad = []
    pid = b.get("id")
    if not isinstance(pid, str) or not _ID.match(pid):
        bad.append("id %r: lower-case letters, digits and - (up to 40)" % (pid,))
    scene = b.get("scene")
    sp = _inside(os.path.join(out_dir, "blender"), os.path.relpath(os.path.join(out_dir, scene), os.path.join(out_dir, "blender"))) \
        if isinstance(scene, str) and scene.endswith(".py") else None
    if not sp or not os.path.isfile(sp):
        bad.append("scene %r: a .py file under <out_dir>/blender/ that exists" % (scene,))
    if b.get("why") not in BLENDER_WHY:
        bad.append("why %r: one of %s — what 3D physicality IS this beat's content?" % (b.get("why"), ", ".join(BLENDER_WHY)))
    mode, engine = b.get("mode", "rgba"), b.get("engine", "eevee")
    if mode not in MODES:
        bad.append("mode %r: one of %s" % (mode, ", ".join(MODES)))
    if engine not in ENGINES:
        bad.append("engine %r: one of %s" % (engine, ", ".join(ENGINES)))
    lists = {}
    for k in ("cues", "anchors", "objects", "assets"):
        v = b.get(k, [])
        if not _strings(v) and v != []:
            bad.append("%s: a list of non-empty strings" % k)
        lists[k] = list(v) if isinstance(v, list) else []
    for a in lists["assets"] if _strings(lists["assets"]) else []:
        p = _inside(out_dir, a)
        side = (p or "") + ".json"
        if not p or not os.path.isfile(p):
            bad.append("asset %r: a file inside the film" % a)
            continue
        try:
            meta = json.load(open(side, encoding="utf-8"))
        except (OSError, ValueError):
            meta = None
        if not isinstance(meta, dict) or not meta.get("license") or not meta.get("source"):
            bad.append("asset %r has no licence sidecar (%s with license + source)" % (a, os.path.basename(side)))
    if slide.get("shot") not in _ws.shot_names(out_dir):
        bad.append("shot %r: a Blender plate is drawn by a workshop shot (the film's own overlay code)" % slide.get("shot"))
    if bad:
        raise PlateError("blender (beat %s): %s" % (slide.get("index", "?"), "; ".join(bad)))
    return {"id": pid, "scene": scene, "why": b["why"], "mode": mode, "engine": engine, **lists}


def cue_times(out_dir, index, phrases):
    """{phrase: seconds into the beat} from audio/NN.words.json — every phrase must be SPOKEN; none is guessed."""
    if not phrases:
        return {}
    import cues as _cues
    path = os.path.join(out_dir, "audio", "%02d.words.json" % index)
    try:
        words = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        raise PlateError("beat %d has cues %s but no word times (%s) — voice it first (tts.py)" % (index, phrases, path)) from None
    words = words.get("words", words) if isinstance(words, dict) else words
    out, start = {}, 0
    for ph in phrases:
        i = _cues._find(words, ph, start)
        if i < 0:
            i = _cues._find(words, ph, 0)
        if i < 0:
            raise PlateError("cue %r is not spoken in beat %d" % (ph, index))
        out[ph] = round(float(words[i].get("t", 0.0)), 3)
        start = i + 1
    return out


def plate_dir(out_dir, plate_id):
    return os.path.join(out_dir, "media", "blender", plate_id)


def _file_sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _code_sha(p):
    """A .py file's CODE, not its text: comments, docstrings and layout do not change a plate, so editing them must
    not rebuild every plate (a kit docstring edit staled both acceptance plates, 2026-11-04 — 38 GPU minutes).
    A file that does not parse is hashed as bytes (it fails in Blender, loudly, anyway)."""
    import ast
    try:
        tree = ast.parse(open(p, encoding="utf-8").read())
    except (SyntaxError, UnicodeDecodeError, ValueError):
        return _file_sha(p)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    return hashlib.sha256(ast.dump(tree, include_attributes=False).encode("utf-8")).hexdigest()


def kit_files():
    """Every Blender-side file a plate is drawn by (blender/**/*.py), relative to the skill, sorted."""
    out = []
    for d, _n, fs in os.walk(KIT_DIR):
        out += [os.path.relpath(os.path.join(d, f), SKILL_ROOT) for f in fs if f.endswith(".py")]
    return sorted(out)


def scene_imports(scene_path, bdir):
    """The film's own blender/*.py modules a scene reaches by import, transitively, sorted (the scene itself not
    included). A module that does not parse imports nothing we can read — it is hashed, and fails in Blender anyway."""
    import ast
    seen, todo = set(), [scene_path]
    while todo:
        p = todo.pop()
        try:
            tree = ast.parse(open(p, encoding="utf-8").read())
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
            continue
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names.add(node.module.split(".")[0])
        for n in sorted(names):
            q = os.path.join(bdir, n + ".py")
            if os.path.isfile(q) and os.path.realpath(q) != os.path.realpath(scene_path) and q not in seen:
                seen.add(q)
                todo.append(q)
    return sorted(seen)


def plate_key(spec, out_dir, frames, fps, w, h, cue_t, blender_version, folder_wide=False):
    """What a plate is a function of: its scene, the kit, its assets, the cue times it uses, its frame and engine."""
    h_ = hashlib.sha256()
    def put(*parts):
        for p in parts:
            h_.update(str(p).encode("utf-8"))
            h_.update(b"\0")
    put("scene", spec["scene"], _code_sha(os.path.join(out_dir, spec["scene"])))
    # a scene may import helpers beside it (two plates sharing one satellite): the helpers IT imports, transitively —
    # not every .py under blender/ (the ANC film: one edit to explode.py rebuilt all three plates, ~11 min, twice)
    bdir = os.path.join(out_dir, "blender")
    if folder_wide:                                       # the key as it was before 2026-11-05 (key_matches reads it)
        helpers = [os.path.join(d, f) for d, _n, fs in sorted(os.walk(bdir)) for f in sorted(fs) if f.endswith(".py")]
    else:
        helpers = scene_imports(os.path.join(out_dir, spec["scene"]), bdir)
    for p in helpers:
        put("scene-dir", os.path.relpath(p, bdir), _code_sha(p))
    for rel in kit_files():
        put("kit", rel, _code_sha(os.path.join(SKILL_ROOT, rel)))
    for a in spec["assets"]:
        put("asset", a, _file_sha(os.path.join(out_dir, a)))
    for k in sorted(cue_t):
        put("cue", k, "%.3f" % cue_t[k])
    put("frame", frames, fps, w, h, spec["engine"], spec["mode"], "|".join(spec["anchors"]), "|".join(spec["objects"]))
    put("blender", blender_version)
    put("format", PLATE_FORMAT)
    return h_.hexdigest()


def key_matches(stored, spec, out_dir, frames, fps, w, h, cue_t, blender_version, suffix=""):
    """Is a stored key the key of these inputs? Either today's (the scene and what it imports) or the folder-wide key a
    plate built before 2026-11-05 carries — the same plate, so it is not rebuilt for a change in what keys cover."""
    a = (spec, out_dir, frames, fps, w, h, cue_t, blender_version)
    return stored in (plate_key(*a) + suffix, plate_key(*a, folder_wide=True) + suffix)


def _frame_facts(out_dir, board, i):
    """(frames, fps, w, h) of slide i as the Film renders it: its scene's durF and the film's frame."""
    import render_remotion as rr
    props, slides = rr.film_props(out_dir, board)
    k = next(n for n, s in enumerate(slides) if s is board["slides"][i] or s.get("index") == board["slides"][i].get("index"))
    from _caption_band import aspect_table
    w, h = aspect_table().get(str((board.get("meta") or {}).get("aspect") or "16:9"), (1920, 1080))
    return int(props["scenes"][k]["durF"]), int(props.get("fps", 30)), int(w), int(h)


def _blender_version_str(meta, binary=None):
    v = blender_version(binary or require_blender(meta))
    return "%d.%d.%d%s" % (v[0], v[1], v[2], "-rc" if v[3] else "")


def current_key(out_dir, board, i):
    slide = board["slides"][i]
    spec = spec_of(slide, out_dir)
    frames, fps, w, h = _frame_facts(out_dir, board, i)
    cue_t = cue_times(out_dir, slide.get("index", i + 1), spec["cues"])
    return plate_key(spec, out_dir, frames, fps, w, h, cue_t, _blender_version_str(board.get("meta")))


def _key_args(out_dir, board, i):
    slide = board["slides"][i]
    spec = spec_of(slide, out_dir)
    frames, fps, w, h = _frame_facts(out_dir, board, i)
    cue_t = cue_times(out_dir, slide.get("index", i + 1), spec["cues"])
    return dict(spec=spec, out_dir=out_dir, frames=frames, fps=fps, w=w, h=h, cue_t=cue_t,
                blender_version=_blender_version_str(board.get("meta")))


def plate_state(out_dir, board, i):
    """'missing' | 'stale' | 'fresh' | 'preview' | 'layout': is slide i's built plate the one its board, scene and voice ask for now?"""
    spec = spec_of(board["slides"][i], out_dir)
    pj = os.path.join(plate_dir(out_dir, spec["id"]), "plate.json")
    try:
        built = json.load(open(pj, encoding="utf-8"))
    except (OSError, ValueError):
        return "missing"
    if built.get("preview"):
        return "preview"
    if built.get("layout"):
        return "layout"
    return "fresh" if key_matches(built.get("key"), **_key_args(out_dir, board, i)) else "stale"


_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".exr", ".hdr", ".webp")
EDGE_DIFF = 40          # mean |difference| (0-255) between an edge column and its neighbour that reads as a line
EDGE_FLAT = 6.0         # ...when the edge column itself is nearly one colour (a border, not the picture)


def asset_warnings(spec, out_dir):
    """Defects a real asset carries that no gate sees on the plate: an equirectangular map (2:1) whose first or last
    column is a flat band unlike its neighbour draws a bright or dark MERIDIAN where the map wraps round a sphere.
    NASA's 24k Blue Marble on Commons has a white last column (measured 2026-11-04) — fix a copy, record it in the
    copy's sidecar (derived_from + change), and point the scene at the copy."""
    from PIL import Image, ImageStat
    Image.MAX_IMAGE_PIXELS = None
    out = []
    for a in spec.get("assets") or []:
        p = os.path.join(out_dir, a)
        if not a.lower().endswith(_IMAGE_EXT) or not os.path.isfile(p):
            continue
        try:
            with Image.open(p) as im:
                w, h = im.size
                if not (1.9 <= w / max(1, h) <= 2.1) or w < 8:
                    continue
                im = im.convert("L")
                for edge, nb in ((0, 1), (w - 1, w - 2)):
                    col = im.crop((edge, 0, edge + 1, h))
                    nxt = im.crop((nb, 0, nb + 1, h))
                    from PIL import ImageChops
                    diff = ImageStat.Stat(ImageChops.difference(col, nxt)).mean[0]
                    if diff >= EDGE_DIFF and ImageStat.Stat(col).stddev[0] <= EDGE_FLAT:
                        out.append("blender: asset %s — column %d is a flat band unlike its neighbour (mean diff %.0f): "
                                   "wrapped round a sphere it draws a line along a meridian; fix a copy (copy the "
                                   "neighbouring column over it) and record the change in that copy's sidecar" % (a, edge, diff))
        except OSError as e:
            out.append("blender: asset %s could not be read as an image (%s)" % (a, e))
    return out


def validate_blender(board, out_dir):
    """(errors, warns) for every beat carrying slide.blender: a valid spec, unique ids, a plate built and fresh."""
    errors, warns, seen = [], [], {}
    for i, slide in enumerate(board.get("slides") or []):
        if "blender" not in slide:
            continue
        try:
            spec = spec_of(slide, out_dir)
            if spec["id"] in seen:
                errors.append("blender: plate id %r is used twice (beats %s and %s)" % (spec["id"], seen[spec["id"]], slide.get("index")))
                continue
            seen[spec["id"]] = slide.get("index")
            st = plate_state(out_dir, board, i)
        except PlateError as e:
            errors.append(str(e))
            continue
        warns.extend(asset_warnings(spec, out_dir))
        if st == "missing":
            errors.append("blender (beat %s): plate %r is not built — run scripts/blender_plate.py %s" % (slide.get("index"), spec["id"], out_dir))
        elif st == "preview":
            errors.append("blender (beat %s): plate %r is a PREVIEW (half size, %d samples) — build it full before delivery: "
                          "scripts/blender_plate.py %s --only %s" % (slide.get("index"), spec["id"], PREVIEW_SAMPLES, out_dir, spec["id"]))
        elif st == "layout":
            errors.append("blender (beat %s): plate %r is a LAYOUT pass (the objects' silhouettes, no picture) — build it "
                          "for delivery: scripts/blender_plate.py %s --only %s" % (slide.get("index"), spec["id"], out_dir, spec["id"]))
        elif st == "stale":
            errors.append("blender (beat %s): plate %r is stale (its scene, kit, assets, cue times or beat length changed) — "
                          "rebuild it: scripts/blender_plate.py %s --only %s" % (slide.get("index"), spec["id"], out_dir, spec["id"]))
    return errors, warns


# ── the build ─────────────────────────────────────────────────────────────────────────────────────────────────
# Measured on an Apple M4 (10-core GPU), 2026-11-04 (spec §8): EEVEE 4.6 s a 1080p frame on the first plate (a
# satellite and a 24k Earth), Cycles 13-19 s on the GPU alone at 64 spp, the ID pass 0.72 s, Blender's start 10 s.
SEC_PER_FRAME = {"eevee": 4.6, "cycles": 16.0}
ID_SEC_PER_FRAME = 0.72
LAYOUT_SEC_PER_FRAME = 0.09  # measured: a layout pass alone (half-size Workbench IDs), orbit-gain 351 f in 22-31 s past start
START_SECONDS = 10.0
DEFAULT_BUDGET_MIN = 60
RUNNER = os.path.join(KIT_DIR, "runner.py")
ID_TOLERANCE = 8
FULL_SAMPLES = 64          # EEVEE TAA samples / Cycles samples of a delivered plate
PREVIEW_SAMPLES = 16       # --preview: half the frame each way, a quarter of the samples (spec §5) — never delivered


class BlenderMissing(PlateError):
    pass


class OverBudget(PlateError):
    pass


PREVIEW_FACTOR = 0.31      # measured: two glass previews (Cycles) ran 0.31 and 0.21 of the full-build model; the slower one


def measured_sec_per_frame(out_dir, spec):
    """Seconds a frame this plate's LAST full build really took (start cost taken off), reuse included — or None
    when there is no full build on record. The ANC film: the whole-frame model said 61 min, the builds took 12.7."""
    def rate(path, engine=None):
        try:
            pj = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if pj.get("preview") or pj.get("layout") or not pj.get("frames") or not pj.get("seconds"):
            return None
        if engine and pj.get("engine", engine) != engine:
            return None
        return max(0.0, float(pj["seconds"]) - START_SECONDS) / float(pj["frames"])
    own = rate(os.path.join(plate_dir(out_dir, spec["id"]), "plate.json"))
    if own is not None:
        return own
    # a plate never built borrows the median rate of this film's other plates on the same engine
    root = os.path.join(out_dir, "media", "blender")
    rates = sorted(r for r in (rate(os.path.join(root, d, "plate.json"), spec.get("engine", "eevee"))
                               for d in (os.listdir(root) if os.path.isdir(root) else []) if d != spec["id"])
                   if r is not None)
    return rates[len(rates) // 2] if rates else None


def estimate_seconds(spec, frames, preview=False, layout=False, measured=None):
    """The cost of a build. With `measured` (measured_sec_per_frame: this plate's own last build, reuse and all) it
    is that rate; without one, the cost of rendering every frame whole — an upper bound, frames that did not change
    are not rendered."""
    if layout:
        return START_SECONDS + frames * LAYOUT_SEC_PER_FRAME
    if measured is not None and not preview:
        return START_SECONDS + frames * measured
    per = SEC_PER_FRAME[spec["engine"]] + (ID_SEC_PER_FRAME if spec.get("objects") else 0.0)
    return START_SECONDS + frames * per * (PREVIEW_FACTOR if preview else 1.0)


def assemble(work, frames_meta, layout=False):
    """rgba/ and ids/ for EVERY frame, from the runner's full frames and patches (run.json `frames`): a copy is the
    last frame again, a patch is pasted over it. A layout pass has no picture: _encode makes its video from ids/."""
    from PIL import Image
    for d, pd_, k in (("rgba", "patch", 1), ("ids", "idpatch", 2)):
        if not os.path.isdir(os.path.join(work, d)) or (d == "rgba" and layout):
            continue
        for i, fm in enumerate(frames_meta, 1):
            dest = os.path.join(work, d, "%04d.png" % i)
            kind = fm["kind"]
            if d == "ids" and fm.get("ids") == "full":
                kind = "full"                            # a patched picture's ID pass is rendered whole
            if kind == "full":
                if not os.path.isfile(dest):
                    if d == "ids" and not os.listdir(os.path.join(work, "ids")):
                        break                                # a plate that names no objects has no ID pass
                    raise PlateError("the runner left no %s frame %04d (a full frame)" % (d, i))
                continue
            if i == 1:
                raise PlateError("frame 1 is a %s, but there is nothing before it" % kind)
            before = os.path.join(work, d, "%04d.png" % (i - 1))
            if kind == "copy":
                shutil.copyfile(before, dest)
                continue
            x0, y0, x1, y1 = [v // k for v in fm["rect"]]
            with Image.open(before) as b, Image.open(os.path.join(work, pd_, "%04d.png" % i)) as p:
                if p.size != (x1 - x0, y1 - y0):
                    raise PlateError("patch %s/%04d is %dx%d, its rectangle %dx%d" % (pd_, i, p.size[0], p.size[1], x1 - x0, y1 - y0))
                im = b.convert("RGBA")
                im.paste(p.convert("RGBA"), (x0, y0))
                im.save(dest)


def boxes_from_ids(ids_dir, colors, frames, scale=2):
    """{object: [[x0, y0, x1, y1] | None per frame]} in FRAME pixels (x1, y1 exclusive) from the half-size ID pass."""
    from PIL import Image, ImageChops
    out = {n: [] for n in colors}
    want = {n: tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for n, c in colors.items()}
    for f in range(1, frames + 1):
        p = os.path.join(ids_dir, "%04d.png" % f)
        if not os.path.isfile(p):
            raise PlateError("the ID pass has no frame %s (%s)" % ("%04d" % f, p))
        im = Image.open(p).convert("RGBA")
        r, g, b, a = im.split()
        solid = a.point(lambda v: 255 if v > 0 else 0)
        for n, (cr, cg, cb) in want.items():
            m = solid
            for ch, c in ((r, cr), (g, cg), (b, cb)):
                m = ImageChops.multiply(m, ch.point(lambda v, c=c: 255 if abs(v - c) <= ID_TOLERANCE else 0))
            bb = m.getbbox()
            out[n].append([bb[0] * scale, bb[1] * scale, bb[2] * scale, bb[3] * scale] if bb else None)
    return out


def _run_blender(cmd, log):
    with open(log, "w", encoding="utf-8") as fh:
        return subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode


def _encode(work, dest, fps, mode, layout=False):
    """The plate's VP9 video. A LAYOUT plate's is its half-size ID pass, doubled in the encoder and encoded fast: nobody
    watches it (validate refuses it for delivery), the census only needs it to play, and upscaling 351 PNGs then
    encoding them at delivery quality was 48 s of an 84 s layout pass (orbit-gain, 2026-11-05)."""
    tmp = dest + ".part.webm"
    pix = "yuva420p" if mode == "rgba" else "yuv420p"
    src = os.path.join(work, "ids" if layout else "rgba", "%04d.png")
    how = (["-vf", "scale=iw*2:ih*2:flags=neighbor", "-crf", "40", "-deadline", "realtime", "-cpu-used", "8"] if layout
           else ["-crf", "12"])
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", src, "-c:v", "libvpx-vp9",
                        "-pix_fmt", pix, *how, "-b:v", "0", "-auto-alt-ref", "0", tmp], capture_output=True, text=True)
    if r.returncode != 0:
        raise PlateError("ffmpeg could not encode the plate: %s" % r.stderr.strip()[-300:])
    if mode == "rgba":
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", tmp], capture_output=True, text=True).stdout
        if "alpha_mode=1" not in probe.lower().replace("tag:", ""):
            raise PlateError("the encoded plate lost its alpha (no alpha_mode=1): %s" % tmp)
    os.replace(tmp, dest)


def _plates_on(board, out_dir):
    for i, s in enumerate(board.get("slides") or []):
        if "blender" in s:
            yield i, s, spec_of(s, out_dir)


def write_plates_ts(out_dir):
    """workshop/assets/plates.ts — every built plate on the board, with its file paths quoted IN FULL (the form
    remotion_segments ships and keys a beat on, so a rebuilt plate re-renders the beat that draws it)."""
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    rows = []
    for _i, _s, spec in _plates_on(board, out_dir):
        pd = plate_dir(out_dir, spec["id"])
        try:
            pj = json.load(open(os.path.join(pd, "plate.json"), encoding="utf-8"))
            an = json.load(open(os.path.join(pd, "anchors.json"), encoding="utf-8"))
            bx = json.load(open(os.path.join(pd, "boxes.json"), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        row = {"id": spec["id"], "src": "media/blender/%s/plate.webm" % spec["id"], "w": pj["w"], "h": pj["h"], "fps": pj["fps"],
               "frames": pj["frames"], "mode": pj["mode"], "anchors": an.get("anchors", {}), "boxes": bx}
        rows.append("  %s: %s," % (json.dumps(spec["id"]), json.dumps(row, ensure_ascii=False, separators=(",", ":"))))
    d = os.path.join(out_dir, "workshop", "assets")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "plates.ts")
    text = "\n".join(["// GENERATED by scripts/blender_plate.py — every Blender plate this film's shots draw. Do not edit:",
                      "// rebuild the plate (scripts/blender_plate.py <out_dir>) and this is rewritten.",
                      "import type {Plate} from '@runtime/blenderPlate';",
                      "export const PLATES: Record<string, Plate> = {", *rows, "};", ""])
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def build(out_dir, only=None, yes=False, still=None, preview=False, layout=False, ids=None):
    """Build every stale plate on the board (or the one named `only`); a report per plate. Over the film's budget
    (meta.blender_budget_min, default 60) nothing is built unless `yes` — the agent asks the user first."""
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = board.get("meta") or {}
    try:
        binary = require_blender(meta)
    except PlateError as e:
        raise BlenderMissing(str(e)) from None
    version = _blender_version_str(meta, binary)
    todo, reports = [], []
    for i, slide, spec in _plates_on(board, out_dir):
        if (only and spec["id"] != only) or (ids is not None and spec["id"] not in ids):
            continue
        frames, fps, w, h = _frame_facts(out_dir, board, i)
        if preview:
            w, h = max(2, w // 2 // 2 * 2), max(2, h // 2 // 2 * 2)
        cue_t = cue_times(out_dir, slide.get("index", i + 1), spec["cues"])
        if layout and not spec["objects"]:
            continue                                      # nothing for a layout to judge: no named objects
        key = plate_key(spec, out_dir, frames, fps, w, h, cue_t, version) + ("-preview" if preview else "") \
            + ("-layout" if layout else "")
        pj = os.path.join(plate_dir(out_dir, spec["id"]), "plate.json")
        try:
            fresh = key_matches(json.load(open(pj, encoding="utf-8")).get("key"), spec, out_dir, frames, fps, w, h, cue_t,
                                version, suffix=("-preview" if preview else "") + ("-layout" if layout else ""))
        except (OSError, ValueError):
            fresh = False
        if fresh and still is None:
            reports.append({"id": spec["id"], "state": "fresh"})
            continue
        todo.append((slide, spec, frames, fps, w, h, cue_t, key))
    est = sum(estimate_seconds(t[1], 1 if still else t[2], preview, layout, measured_sec_per_frame(out_dir, t[1]))
              for t in todo)
    budget = float(meta.get("blender_budget_min", DEFAULT_BUDGET_MIN)) * 60
    if todo and est > budget and not yes:
        raise OverBudget("%d plate(s) to build, estimated %.0f min — over this film's budget of %.0f min "
                         "(meta.blender_budget_min). Ask the user, then re-run with --yes"
                         % (len(todo), est / 60, budget / 60))
    import progress as _pg
    for n_done, (slide, spec, frames, fps, w, h, cue_t, key) in enumerate(todo):
        _pg.write(out_dir, "layout" if layout else "plates", n_done, len(todo), spec["id"])
        pd = plate_dir(out_dir, spec["id"])
        os.makedirs(pd, exist_ok=True)
        work = os.path.join(pd, (".still-" if still else ".work-") + key[:12])
        for d in os.listdir(pd):
            if d.startswith(".work-") and os.path.join(pd, d) != work:
                shutil.rmtree(os.path.join(pd, d), ignore_errors=True)    # a partial of an OLDER key: never mixed in
        os.makedirs(work, exist_ok=True)
        cmd = [binary, "-b", "--factory-startup", "--python-exit-code", "1", "--python", RUNNER, "--",
               "--scene", os.path.join(out_dir, spec["scene"]), "--out", work, "--frames", str(frames),
               "--fps", str(fps), "--w", str(w), "--h", str(h), "--engine", spec["engine"], "--mode", spec["mode"],
               "--cues", json.dumps(cue_t, ensure_ascii=False), "--anchors", ",".join(spec["anchors"]),
               "--objects", ",".join(spec["objects"]), "--samples", str(PREVIEW_SAMPLES if preview else FULL_SAMPLES)] \
            + (["--still", str(still)] if still else []) + (["--layout"] if layout else [])
        import time as _time
        t0 = _time.time()
        log = os.path.join(work, "runner.log")
        rc = _run_blender(cmd, log)
        if rc != 0:
            tail = open(log, encoding="utf-8", errors="replace").read()[-1500:] if os.path.exists(log) else ""
            raise PlateError("Blender failed on plate %r (exit %d); its log %s ends:\n%s" % (spec["id"], rc, log, tail))
        if still:
            reports.append({"id": spec["id"], "state": "still", "path": os.path.join(work, "still_%04d.png" % still)})
            continue
        run = json.load(open(os.path.join(work, "run.json"), encoding="utf-8"))
        assemble(work, run.get("frames") or [{"kind": "full"}] * frames, layout)
        _encode(work, os.path.join(pd, "plate.webm"), fps, spec["mode"], layout)
        boxes = boxes_from_ids(os.path.join(work, "ids"), run.get("ids") or {}, frames) if spec["objects"] else {}
        with open(os.path.join(pd, "boxes.json"), "w", encoding="utf-8") as fh:
            json.dump(boxes, fh)
        for f in ("anchors.json", "camera.json"):
            shutil.copyfile(os.path.join(work, f), os.path.join(pd, f))
        # the ID pass stays: the objects' SILHOUETTES, which plate_qa judges type against (a box has empty corners)
        shutil.rmtree(os.path.join(pd, "ids"), ignore_errors=True)
        if spec["objects"]:
            shutil.move(os.path.join(work, "ids"), os.path.join(pd, "ids"))
        secs = round(_time.time() - t0, 1)
        with open(os.path.join(pd, "plate.json"), "w", encoding="utf-8") as fh:
            json.dump({"key": key, "frames": frames, "fps": fps, "w": w, "h": h, "mode": spec["mode"],
                       "engine": spec["engine"], "why": spec["why"], "blender": version, "seconds": secs, "ids": run.get("ids") or {},
                       "estimate": round(estimate_seconds(spec, frames, preview, layout), 1), "cues": cue_t, "assets": spec["assets"], "preview": bool(preview),
                       "layout": bool(layout), "reuse": run.get("reuse"), "reuse_off": run.get("reuse_off")},
                      fh, ensure_ascii=False, indent=1)
        shutil.rmtree(work, ignore_errors=True)
        reports.append({"id": spec["id"], "state": "built", "seconds": secs, "estimate": round(estimate_seconds(spec, frames, preview, layout), 1),
                        "reuse": run.get("reuse"), "reuse_off": run.get("reuse_off"), "layout": layout})
    if not still:
        write_plates_ts(out_dir)
    return reports


# ── layout first ──────────────────────────────────────────────────────────────────────────────────────────────
# THE EXPENSIVE PASS RUNS ONCE. The first acceptance plates were built whole three times (106 GPU minutes for 17 s of
# film), and the last rebuild only moved the Earth because plate_qa — which needs the plate — found type over it. The
# layout pass (the ID pass and the anchors, no picture: 0.72 s a frame) is enough for plate_qa, so a full build first
# builds the layout of every plate whose layout has not passed, judges the film, and renders pictures only when the
# layout is clean. A passed layout is recorded against the plate's key (layout.json): the same inputs never pay twice.
LAYOUT_RECORD = "layout.json"


def layout_passed(out_dir, board, i):
    spec = spec_of(board["slides"][i], out_dir)
    try:
        rec = json.load(open(os.path.join(plate_dir(out_dir, spec["id"]), LAYOUT_RECORD), encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return key_matches(rec.get("key"), **_key_args(out_dir, board, i))


def layout_gate(out_dir, only=None, yes=False):
    """(ok, lines): build the layout pass of every stale plate whose layout has not passed, and judge the film with
    plate_qa. Nothing expensive has been rendered when this says no."""
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    need = {}
    for i, _s, spec in _plates_on(board, out_dir):
        if (only and spec["id"] != only) or not spec["objects"]:
            continue
        if plate_state(out_dir, board, i) == "fresh" or layout_passed(out_dir, board, i):
            continue
        need[spec["id"]] = i
    if not need:
        return True, []
    t0 = __import__("time").time()
    build(out_dir, yes=yes, layout=True, ids=set(need))
    import plate_qa
    r = plate_qa.scan_film(out_dir)
    word, code = plate_qa.verdict(r)
    lines = ["[blender_plate] layout pass of %s: %.0f s, plate_qa %s" % (", ".join(sorted(need)), __import__("time").time() - t0, word)]
    lines += ["[plate_qa] ERROR " + e for e in r["errors"]] + ["[plate_qa] NOT MEASURED: " + u for u in r["unmeasured"]]
    if code != 0:
        return False, lines + ["[blender_plate] NOT BUILT — fix the layout (move the type, or stage.place the object) "
                               "and re-run; no picture was rendered. --skip-layout builds anyway."]
    for pid, i in need.items():
        with open(os.path.join(plate_dir(out_dir, pid), LAYOUT_RECORD), "w", encoding="utf-8") as fh:
            json.dump({"key": current_key(out_dir, board, i), "plate_qa": word, "warns": r["warns"]}, fh, ensure_ascii=False)
    return True, lines + ["[plate_qa] WARN  " + w for w in r["warns"]]


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Build a film's Blender plates (slide.blender).")
    ap.add_argument("out_dir")
    ap.add_argument("--only", help="build only this plate id")
    ap.add_argument("--still", type=int, help="render one frame of each plate to look at (no plate is written)")
    ap.add_argument("--yes", action="store_true", help="build although the estimate is over meta.blender_budget_min")
    ap.add_argument("--layout", action="store_true", help="the ID pass and anchors only (no picture), to judge "
                    "the layout with plate_qa; validate refuses it for delivery")
    ap.add_argument("--skip-layout", action="store_true", help="build pictures without first passing the layout")
    ap.add_argument("--preview", action="store_true", help="half size, %d samples: to look at motion and layout; "
                    "validate refuses it for delivery" % PREVIEW_SAMPLES)
    a = ap.parse_args(argv)
    try:
        if not (a.still or a.preview or a.layout or a.skip_layout):
            ok, lines = layout_gate(a.out_dir, only=a.only, yes=a.yes)
            for ln in lines:
                print(ln)
            if not ok:
                return 4
        reps = build(a.out_dir, only=a.only, yes=a.yes, still=a.still, preview=a.preview, layout=a.layout)
    except BlenderMissing as e:
        print("[blender_plate] NOT BUILT — %s" % e)
        return 2
    except OverBudget as e:
        print("[blender_plate] OVER BUDGET — %s" % e)
        return 3
    except PlateError as e:
        print("[blender_plate] FAILED — %s" % e)
        return 1
    for r in reps:
        if r["state"] == "built" and r.get("layout"):
            print("[blender_plate] %s: layout pass in %.0f s (estimated %.0f s): the ID pass only, no picture"
                  % (r["id"], r["seconds"], r["estimate"]))
        elif r["state"] == "built":
            ru = r.get("reuse") or {}
            print("[blender_plate] %s: built in %.0f s (estimated %.0f s rendering every frame whole; %d whole, "
                  "%d copied, %d patched%s)" % (r["id"], r["seconds"], r["estimate"], ru.get("full", 0), ru.get("copy", 0),
                                                 ru.get("patch", 0), "; reuse off: %s" % r["reuse_off"] if r.get("reuse_off") else ""))
        elif r["state"] == "still":
            print("[blender_plate] %s: still -> %s" % (r["id"], r["path"]))
        else:
            print("[blender_plate] %s: fresh" % r["id"])
    if not reps:
        print("[blender_plate] no beat carries slide.blender%s" % (" with id %r" % a.only if a.only else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
