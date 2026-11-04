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


def kit_files():
    """Every Blender-side file a plate is drawn by (blender/**/*.py), relative to the skill, sorted."""
    out = []
    for d, _n, fs in os.walk(KIT_DIR):
        out += [os.path.relpath(os.path.join(d, f), SKILL_ROOT) for f in fs if f.endswith(".py")]
    return sorted(out)


def plate_key(spec, out_dir, frames, fps, w, h, cue_t, blender_version):
    """What a plate is a function of: its scene, the kit, its assets, the cue times it uses, its frame and engine."""
    h_ = hashlib.sha256()
    def put(*parts):
        for p in parts:
            h_.update(str(p).encode("utf-8"))
            h_.update(b"\0")
    put("scene", _file_sha(os.path.join(out_dir, spec["scene"])))
    for rel in kit_files():
        put("kit", rel, _file_sha(os.path.join(SKILL_ROOT, rel)))
    for a in spec["assets"]:
        put("asset", a, _file_sha(os.path.join(out_dir, a)))
    for k in sorted(cue_t):
        put("cue", k, "%.3f" % cue_t[k])
    put("frame", frames, fps, w, h, spec["engine"], spec["mode"], "|".join(spec["anchors"]), "|".join(spec["objects"]))
    put("blender", blender_version)
    return h_.hexdigest()


def _frame_facts(out_dir, board, i):
    """(frames, fps, w, h) of slide i as the Film renders it: its scene's durF and the film's frame."""
    import render_remotion as rr
    props, slides = rr.film_props(out_dir, board)
    k = next(n for n, s in enumerate(slides) if s is board["slides"][i] or s.get("index") == board["slides"][i].get("index"))
    from _caption_band import aspect_table
    w, h = aspect_table().get(str((board.get("meta") or {}).get("aspect") or "16:9"), (1920, 1080))
    return int(props["scenes"][k]["durF"]), int(props.get("fps", 30)), int(w), int(h)


def _blender_version_str(meta):
    v = blender_version(require_blender(meta))
    return "%d.%d.%d%s" % (v[0], v[1], v[2], "-rc" if v[3] else "")


def current_key(out_dir, board, i):
    slide = board["slides"][i]
    spec = spec_of(slide, out_dir)
    frames, fps, w, h = _frame_facts(out_dir, board, i)
    cue_t = cue_times(out_dir, slide.get("index", i + 1), spec["cues"])
    return plate_key(spec, out_dir, frames, fps, w, h, cue_t, _blender_version_str(board.get("meta")))


def plate_state(out_dir, board, i):
    """'missing' | 'stale' | 'fresh': is slide i's built plate the one its board, scene and voice ask for now?"""
    spec = spec_of(board["slides"][i], out_dir)
    pj = os.path.join(plate_dir(out_dir, spec["id"]), "plate.json")
    try:
        built = json.load(open(pj, encoding="utf-8")).get("key")
    except (OSError, ValueError):
        return "missing"
    return "fresh" if built == current_key(out_dir, board, i) else "stale"


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
        if st == "missing":
            errors.append("blender (beat %s): plate %r is not built — run scripts/blender_plate.py %s" % (slide.get("index"), spec["id"], out_dir))
        elif st == "stale":
            errors.append("blender (beat %s): plate %r is stale (its scene, kit, assets, cue times or beat length changed) — "
                          "rebuild it: scripts/blender_plate.py %s --only %s" % (slide.get("index"), spec["id"], out_dir, spec["id"]))
    return errors, warns
