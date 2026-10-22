"""ONE BEAT'S FINGERPRINT — everything its picture is made of, so a measurement of a beat nothing has touched is reused.

WHY. A film's design stage measures every beat again after every edit: the per-beat design pass on a 25-beat film spent
27.5 min in `energy_skeleton` (9 runs) and 18.6 min in `shot_proof` (8 runs) of its 58 tool minutes, re-rendering 25
beats each time one shot had changed. `energy_skeleton` did cache per beat, but its key hashed EVERY workshop file, so
an edit to one shot re-measured all of them; `shot_proof` cached nothing.

WHAT A KEY COVERS. A beat is rendered from its shot's source and everything that source imports, so the key follows
the IMPORTS, not the folder:
  * the shot's own file (the film's workshop copy when it has one, else the library register) and, transitively, every
    file it imports by a relative path or through the bundler's aliases (`@runtime/`, `@shots/`, `@objects/`), plus the
    kits a promoted register imports;
  * the whole runtime and the renderer's own entry files (Root, registry, Film, index, captions) — every still goes
    through them, and they change rarely;
  * every workshop file that is not code (an image, a font, a data file a shot loads by name), and the names and sizes
    of the renderer's public assets — a shot can reach those by a string the import walk cannot see;
  * the beat's shot, props and duration, the film's DNA / template / aspect / language — and the CALLER's own version
    and source, so editing the instrument re-measures everything it measured.
What it does NOT try to be clever about, and must not: a key that misses an input replays a stale verdict, which is the
one failure a cache may never have. So it is wide where it is cheap (the runtime, every asset) and narrow only where the
saving is (one shot's code instead of every shot's).
"""
import hashlib
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
REMOTION = os.path.normpath(os.path.join(_HERE, "..", "remotion"))
SRC = os.path.join(REMOTION, "src")
_ALIASES = {"@runtime/": os.path.join(SRC, "runtime"), "@shots/": os.path.join(SRC, "shots"),
            "@objects/": os.path.join(SRC, "objects"), "@kits/": os.path.join(SRC, "kits")}
_ENTRY = ("Root.tsx", "registry.ts", "Film.tsx", "index.ts", "captions.ts")
_CODE = (".ts", ".tsx", ".js", ".jsx", ".mjs")
# `import x from '…'`, `import {a} from "…"`, `export … from '…'`, `import '…'`, dynamic `import('…')`
_IMPORT = re.compile(r"""(?:\bfrom\s*|\bimport\s*\(?\s*)['"]([^'"]+)['"]""")


def _resolve(spec, from_dir):
    """The file an import names, or None for a package (react, remotion) — those are pinned by the lockfile."""
    base = None
    if spec.startswith("."):
        base = os.path.abspath(os.path.join(from_dir, spec))
    else:
        for pre, root in _ALIASES.items():
            if spec.startswith(pre):
                base = os.path.join(root, spec[len(pre):])
                break
    if base is None:
        return None
    for cand in (base,) + tuple(base + e for e in _CODE) + tuple(os.path.join(base, "index" + e) for e in _CODE):
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    return base                          # unresolvable: hashed as a missing-file marker, so creating it changes the key


def code_closure(entry):
    """Every source file `entry` reaches through its imports, itself included, sorted."""
    # absolute, so a film named by a relative path keys exactly as the same film named absolutely (the order of the
    # sorted closure — and so the key — would otherwise differ between `../film` and `/…/film`)
    seen, todo = set(), [os.path.abspath(entry)]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        if not os.path.isfile(f):
            continue
        try:
            text = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for spec in _IMPORT.findall(text):
            r = _resolve(spec, os.path.dirname(f))
            if r and r not in seen:
                todo.append(r)
    return sorted(seen)


def _hash_file(h, path, label):
    h.update(("\n%s:" % label).encode("utf-8"))
    try:
        h.update(hashlib.sha256(open(path, "rb").read()).digest())
    except OSError as e:
        h.update(("<missing: %s>" % type(e).__name__).encode())


_SHARED = {}


def shared_hash():
    """The runtime, the renderer's entry files and the public assets' names and sizes — once per process."""
    if "h" in _SHARED:
        return _SHARED["h"]
    h = hashlib.sha256()
    rt = os.path.join(SRC, "runtime")
    for root, dns, files in os.walk(rt):
        dns[:] = sorted(d for d in dns if not d.startswith("."))
        for f in sorted(files):
            if f.endswith(_CODE):
                p = os.path.join(root, f)
                _hash_file(h, p, os.path.relpath(p, SRC))
    for f in _ENTRY:
        _hash_file(h, os.path.join(SRC, f), f)
    pub = os.path.join(REMOTION, "public")
    for root, dns, files in os.walk(pub):
        dns[:] = sorted(d for d in dns if not d.startswith("."))
        for f in sorted(files):
            p = os.path.join(root, f)
            try:
                h.update(("\npublic:%s:%d" % (os.path.relpath(p, pub), os.path.getsize(p))).encode())
            except OSError:
                pass
    _SHARED["h"] = h.hexdigest()
    return _SHARED["h"]


def shot_file(out_dir, shot):
    """The source a beat's shot renders from: the film's workshop copy when it has one, else the library's — or a
    stage component's (remotion/src/stage/, which draws a stage run's beats inside the Film)."""
    if out_dir:
        w = os.path.join(out_dir, "workshop", "shots", shot + ".tsx")
        if os.path.isfile(w):
            return w
    lib = os.path.join(SRC, "shots", "%s.tsx" % shot)
    stage = os.path.join(SRC, "stage", "%s.tsx" % shot)
    return stage if not os.path.isfile(lib) and os.path.isfile(stage) else lib


def _workshop_assets(h, out_dir):
    """Every workshop file that is not code, and every OBJECT's code: an object is placed by NAME through a prop
    (`<ObjectSlot object=…>`), resolved by the registry at render time — no import line leads to it."""
    wdir = os.path.join(out_dir, "workshop") if out_dir else None
    if wdir and os.path.isdir(wdir):
        for root, dns, files in os.walk(wdir):
            dns[:] = sorted(d for d in dns if not d.startswith(".") and d != "_stills")
            in_objects = os.path.relpath(root, wdir).split(os.sep)[0] == "objects"
            for f in sorted(files):
                if f.startswith(".") or (f.endswith(_CODE) and not in_objects):
                    continue
                p = os.path.join(root, f)
                _hash_file(h, p, "workshop:" + os.path.relpath(p, wdir))
    for sub in ("objects", "kits"):
        for root, dns, files in os.walk(os.path.join(SRC, sub)):
            dns[:] = sorted(d for d in dns if not d.startswith("."))
            for f in sorted(files):
                if f.endswith(_CODE):
                    p = os.path.join(root, f)
                    _hash_file(h, p, "lib:" + os.path.relpath(p, SRC))


def beat_key(out_dir, slide, meta, tool, extra=None):
    """The 16-hex fingerprint of one beat for the measurement `tool` (its script path: its own bytes are part of the
    key). `extra` carries anything else the caller's result depends on (a frame number, a probe fraction)."""
    h = hashlib.sha256()
    _hash_file(h, tool, "tool")
    h.update(shared_hash().encode())
    shot = str(slide.get("shot") or "")
    entry = shot_file(out_dir, shot) if shot else None
    if entry:
        for f in code_closure(entry):
            _hash_file(h, f, "code:" + os.path.basename(os.path.dirname(f)) + "/" + os.path.basename(f))
    _workshop_assets(h, out_dir)
    meta = meta or {}
    h.update(json.dumps([shot, slide.get("shot_props"), slide.get("duration"), slide.get("audio_duration"),
                         meta.get("design_dna") or meta.get("shot_template"), meta.get("aspect"),
                         meta.get("language"), extra], sort_keys=True, default=str, ensure_ascii=False).encode())
    return h.hexdigest()[:16]
