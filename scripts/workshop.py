#!/usr/bin/env python3
"""A FILM'S WORKSHOP — the objects and shots one film builds for itself — and the only door into the bundle.

    python3 scripts/workshop.py <out_dir> list                       # what it holds, which beats use it
    python3 scripts/workshop.py <out_dir> new-object <Name> --means "<what the viewer must see>"
    python3 scripts/workshop.py <out_dir> new-shot <Name> --means "<the argument no register carries>"
    python3 scripts/workshop.py <out_dir> check                      # type-check, imports, content contract, words
    python3 scripts/workshop.py <out_dir> still <Name> [--props p.json] [--host ObjectStage] [--frame N]

WHY THIS EXISTS. A film that needed a thing the library does not have had two choices: settle for the nearest
register, or write a new register INTO THE SHARED LIBRARY mid-film and pay its full registration and
measurement. register_shot.py records how that went: "the library can grow… in practice it almost never did,
and the reason was friction". The workshop is the third choice. The film builds what it needs in its own
out_dir; every film-scoped render sees it; the library never does; at delivery the USER chooses what is
promoted (scripts/promote.py). Spec: docs/superpowers/specs/2026-09-27-adaptive-build-design.md.

LAYOUT (all optional):
    <out_dir>/workshop/objects/<Name>.tsx   export const <Name>: React.FC<ObjectProps & {...}>; export const META
    <out_dir>/workshop/shots/<Name>.tsx     export const <Name>; DURATION; GROUND; PROVENANCE
    <out_dir>/workshop/objects|shots/*.ts   helper modules, imported relatively
    <out_dir>/workshop/assets/...           imported by the tsx, so the bundler carries them
    <out_dir>/workshop/index.ts             GENERATED here — never hand-edited
    <out_dir>/workshop/.tsconfig.json       GENERATED here, for the type-check
    <out_dir>/workshop/_stills/             `still` writes the settled frames it renders here

ONE WAY IN. Every film-scoped remotion call takes its environment from `prepare(out_dir)`: SLIDES_WORKSHOP set to
this film's workshop (absolute) when it has one; when it has none, the variable REMOVED if this process inherited
it, so a stale export can never put another film's things into this one. Library sweeps never call it. Nothing
here writes outside `<out_dir>/workshop/`.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from onscreen_text_qa import _strip_comments   # the ONE comment stripper  # noqa: E402

SKILL = os.path.dirname(_HERE)
REMOTION = os.path.join(SKILL, "remotion")
LIB_SHOTS = os.path.join(REMOTION, "src", "shots")
LIB_OBJECTS = os.path.join(REMOTION, "src", "objects")
RUNTIME = os.path.join(REMOTION, "src", "runtime")
ROOT_TSX = os.path.join(REMOTION, "src", "Root.tsx")
ENV_VAR = "SLIDES_WORKSHOP"
KINDS = ("objects", "shots")
GENERATED = ("index.ts", ".tsconfig.json", "_stills")
NAME = re.compile(r"^[A-Z][A-Za-z0-9]{2,31}$")
GROUND_TOKENS = ("bg", "bgGrad", "accent", "accent2", "surface")
SCAFFOLD_MARK = "@scaffold"


class WorkshopError(RuntimeError):
    """What is wrong, as sentences; `.problems` holds every one found."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def workshop_dir(out_dir):
    """<out_dir>/workshop, ABSOLUTE: the CLI runs with cwd=remotion/, where a relative path names a different
    folder."""
    return os.path.join(os.path.abspath(out_dir), "workshop")


def _tsx_names(folder):
    return sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(folder, "*.tsx")))


def shot_names(out_dir):
    return set(_tsx_names(os.path.join(workshop_dir(out_dir), "shots"))) if out_dir else set()


def object_names(out_dir):
    return set(_tsx_names(os.path.join(workshop_dir(out_dir), "objects"))) if out_dir else set()


def library_shot_names():
    return set(_tsx_names(LIB_SHOTS))


def library_object_names():
    return set(_tsx_names(LIB_OBJECTS))


def has_items(out_dir):
    return bool(shot_names(out_dir) or object_names(out_dir))


def _safe(name):
    return isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_]+", name) is not None


def shot_source_path(out_dir, name):
    """Where register `name` is defined for THIS film: the library's, else the film's own; None if neither."""
    if not _safe(name):
        return None
    for p in (os.path.join(LIB_SHOTS, name + ".tsx"),
              os.path.join(workshop_dir(out_dir), "shots", name + ".tsx") if out_dir else None):
        if p and os.path.isfile(p):
            return p
    return None


def shot_source(out_dir, name):
    p = shot_source_path(out_dir, name)
    return _read(p) if p else None


def object_source(out_dir, name):
    if not _safe(name):
        return None
    for p in (os.path.join(workshop_dir(out_dir), "objects", name + ".tsx") if out_dir else None,
              os.path.join(LIB_OBJECTS, name + ".tsx")):
        if p and os.path.isfile(p):
            return _read(p)
    return None


_META = re.compile(r"export const META\b[^=]*=\s*\{(.*?)\}\s*;", re.S)


def object_meta(src):
    """An object's META as {aspect, turns, demo, provenance} (only the keys it sets), or None if it has none."""
    m = _META.search(src or "")
    if not m:
        return None
    body, meta = m.group(1), {}
    a = re.search(r"\baspect\s*:\s*([0-9.]+(?:\s*/\s*[0-9.]+)?)", body)
    if a:
        num = a.group(1).replace(" ", "")
        meta["aspect"] = (float(num.split("/")[0]) / float(num.split("/")[1])) if "/" in num else float(num)
    for flag in ("turns", "demo"):
        f = re.search(r"\b%s\s*:\s*(true|false)" % flag, body)
        if f:
            meta[flag] = f.group(1) == "true"
    p = re.search(r"\bprovenance\s*:\s*['\"]([^'\"]*)['\"]", body)
    if p:
        meta["provenance"] = p.group(1)
    return meta


def demo_objects():
    """Library objects that are a stage's own preview (META.demo) — never a film's picture."""
    return {n for n in library_object_names() if (object_meta(_read(os.path.join(LIB_OBJECTS, n + ".tsx"))) or {}).get("demo")}


def durations(out_dir):
    """{workshop shot: DURATION} — the frame count every film-mode gate needs to find a beat's settled frame."""
    out = {}
    for n in shot_names(out_dir):
        m = re.search(r"export const DURATION\s*=\s*(\d+)", _read(os.path.join(workshop_dir(out_dir), "shots", n + ".tsx")))
        if m:
            out[n] = int(m.group(1))
    return out


_GROUND = re.compile(r"export const GROUND\b[^=]*=\s*(\[[^\]]*\]|'[^']*'|\"[^\"]*\")")
_PROVENANCE = re.compile(r"export const PROVENANCE\b[^=]*=\s*['\"]([^'\"]*)['\"]")


def _ground_of(src):
    m = _GROUND.search(src or "")
    if not m:
        return None
    raw = m.group(1)
    return re.findall(r"['\"]([^'\"]+)['\"]", raw) if raw.startswith("[") else raw[1:-1]


def _ground_ok(g):
    if isinstance(g, list):
        return bool(g) and all(x in GROUND_TOKENS for x in g)
    return g in GROUND_TOKENS or re.fullmatch(r"#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}", g or "") is not None


def grounds(out_dir):
    """{workshop shot: the ground it declares} — what the caption ink and the seam guard judge it on."""
    return {n: _ground_of(_read(os.path.join(workshop_dir(out_dir), "shots", n + ".tsx"))) for n in shot_names(out_dir)}


def provenances(out_dir):
    """{workshop shot or object: the idiom world it declares}."""
    out = {}
    for n in shot_names(out_dir):
        m = _PROVENANCE.search(_read(os.path.join(workshop_dir(out_dir), "shots", n + ".tsx")))
        if m and m.group(1):
            out[n] = m.group(1)
    for n in object_names(out_dir):
        meta = object_meta(_read(os.path.join(workshop_dir(out_dir), "objects", n + ".tsx"))) or {}
        if meta.get("provenance"):
            out[n] = meta["provenance"]
    return out


def _worlds():
    import shot_director
    return list(shot_director.IDIOM_WORLDS)


_COMPOSITION_ID = re.compile(r'<Composition\b[^\n]*?\bid="([A-Za-z0-9_]+)"')
_F_ROW_ID = re.compile(r"\bF\(\s*'([A-Za-z0-9_]+)'")


def _root_composition_ids():
    """Every composition id remotion/src/Root.tsx registers directly (R9): `Film` and `StageProbe` as
    `id="…"` Composition attributes, `TypeSpecimen`, `FontProbe` and the other `*Probe` ids as `{F('<Id>', …)}`
    rows. None of these is a file in src/shots/ or src/objects/, so library_shot_names()/library_object_names()
    cannot see a workshop name collide with one — and unrefused, that collision would hit Remotion's generic
    duplicate-composition error instead of a specific one naming the file to rename. Read from Root.tsx itself,
    not a hard-coded list, so a future composition Root.tsx adds is covered automatically."""
    src = _strip_comments(_read(ROOT_TSX))
    return set(_COMPOSITION_ID.findall(src)) | set(_F_ROW_ID.findall(src))


_SLOT_KEY = re.compile(r"\b([A-Za-z_]\w*)\s*\??\s*:\s*ObjectRef\b")
# R10 (task-2-fix-1.md): a `const|let|var <Name>: ObjectRef = …` is a stage register's own standalone-preview
# constant (later stage registers have exactly these), not a prop a beat can set — masked out before slot_keys()
# ever sees it, rather than excluded by name afterwards (the same name could ALSO be a real prop elsewhere).
_SLOT_DECL = re.compile(r"\b(?:const|let|var)\s+[A-Za-z_]\w*\s*:\s*ObjectRef\b")


def _slot_scan_src(src):
    return _SLOT_DECL.sub("", _strip_comments(src or ""))


def slot_keys(src):
    """Every prop name a register types `ObjectRef`, in any of its types — nested ones included."""
    return set(_SLOT_KEY.findall(_slot_scan_src(src)))


def _ambiguous_slot_keys(src):
    """The subset of slot_keys(src) the same (comment-stripped) source ALSO annotates otherwise — some other
    `name:`/`name?:` not immediately followed by ObjectRef, detected generously (an object-literal property
    counts too, since erring toward "ambiguous" only loses object_refs()'s early hand-validation below; the
    render still refuses a malformed ref either way). R10 (task-2-fix-1.md): a register can reuse a field name
    for a plain caption at one level and type it ObjectRef at a nested one (`object` on TechnicalPlate's own
    props vs. inside a device's `ScreenSrc`) — slot_keys() can't tell those apart by name alone, so for THOSE
    names only a dict-shaped value counts as a found ref; a name the source types ObjectRef and nothing else
    hands back every non-None value, malformed ones included, for a caller like validate.py to report."""
    src = _slot_scan_src(src)
    keys = set(_SLOT_KEY.findall(src))
    amb = set()
    for k in keys:
        for m in re.finditer(r"\b%s\s*\??\s*:\s*(\w*)" % re.escape(k), src):
            if m.group(1) != "ObjectRef":
                amb.add(k)
                break
    return amb


def object_refs(src, props):
    """[(path, value)] for every object reference in a beat's props: each value under a key the register types
    ObjectRef, at any depth (a device's `steps[0].screen.object`, a compare's `left.object`). A key the source
    types ObjectRef and NOTHING else hands back every non-None value under it, well-formed or not (R10:
    validate.py's build check is the one that reports a malformed one — a plain string where a ref belongs — so
    it must still see it here); a key the source ALSO types otherwise elsewhere is ambiguous, and only a
    dict-shaped value under it counts (the brief's own test: a register's top-level `object` is a caption)."""
    keys, ambiguous, found = slot_keys(src), _ambiguous_slot_keys(src), []

    def walk(v, path):
        if isinstance(v, dict):
            for k, x in v.items():
                p = "%s.%s" % (path, k) if path else str(k)
                if k in keys and x is not None and (isinstance(x, dict) or k not in ambiguous):
                    found.append((p, x))
                else:
                    walk(x, p)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, "%s[%d]" % (path, i))

    if keys:
        walk(props or {}, "")
    return found


_REQUIRED = re.compile(r"export const REQUIRED_IN_FILM\b[^=]*=\s*\[([^\]]*)\]")


def required_in_film(src):
    """The props a register says a FILM must set (its standalone preview fills them otherwise)."""
    m = _REQUIRED.search(src or "")
    return set(re.findall(r"['\"](\w+)['\"]", m.group(1))) if m else set()


def uses(slides, out_dir):
    """{shot or object id: [beat numbers]} — a shot by the beats cast on it, an object by the beats whose props
    name it. A beat number is the board's own `index` (its position when a slide has none)."""
    out = {}
    for pos, s in enumerate(slides or [], 1):
        num = s.get("index", pos)
        shot = s.get("shot")
        if isinstance(shot, str) and shot:
            out.setdefault(shot, []).append(num)
        for _path, ref in object_refs(shot_source(out_dir, shot), s.get("shot_props") or {}):
            if isinstance(ref, dict) and isinstance(ref.get("id"), str):
                lst = out.setdefault(ref["id"], [])
                if num not in lst:
                    lst.append(num)
    return out


def _problems(out_dir):
    """[(sentence, blocking)] for the workshop's layout and declarations. BLOCKING problems stop an index from being
    written (a name that is not an identifier, a shadowed library name, a component or DURATION the index cannot
    wire); the rest — a scaffold still in place, a missing provenance or GROUND — are reported by `check` and by
    validate.py, but a work-in-progress object can still be rendered and looked at."""
    ws = workshop_dir(out_dir)
    if not os.path.isdir(ws):
        return []
    out = []
    for entry in sorted(os.listdir(ws)):
        if entry in KINDS or entry == "assets" or entry in GENERATED or entry.startswith("."):
            continue
        out.append(("workshop/%s: a workshop holds objects/, shots/ and assets/ only" % entry, False))
    for n in sorted(shot_names(out_dir) & object_names(out_dir)):
        out.append(("workshop: %s is both a shot and an object — one name, one thing" % n, True))
    lib_s, lib_o, worlds, comp_ids = library_shot_names(), library_object_names(), _worlds(), _root_composition_ids()
    for kind in KINDS:
        folder = os.path.join(ws, kind)
        if not os.path.isdir(folder):
            continue
        for f in sorted(os.listdir(folder)):
            if f.startswith("."):
                continue
            if os.path.isdir(os.path.join(folder, f)) or not f.endswith((".tsx", ".ts")):
                out.append(("workshop/%s/%s: only .tsx items and .ts helpers belong here (pictures go in assets/)"
                            % (kind, f), False))
        for n in _tsx_names(folder):
            where = "workshop/%s/%s.tsx" % (kind, n)
            if not NAME.match(n):
                out.append(("%s: a name is PascalCase, 3-32 letters and digits" % where, True))
                continue
            if n in lib_s:
                out.append(("%s: %s is already a library register — rename it (the render refuses a shadowed name)"
                            % (where, n), True))
            if n in lib_o:
                out.append(("%s: %s is already a library object — rename it" % (where, n), True))
            if n in comp_ids:
                out.append(("%s: %s is already a library composition — rename it (Root.tsx registers it directly)"
                            % (where, n), True))
            src = _read(os.path.join(folder, n + ".tsx"))
            if not re.search(r"export const %s\b" % re.escape(n), src):
                out.append(("%s: export the component as `export const %s`" % (where, n), True))
            if SCAFFOLD_MARK in src:
                out.append(("%s: still the scaffold — draw the real %s, then delete the `%s` line"
                            % (where, kind[:-1], SCAFFOLD_MARK), False))
            if kind == "shots":
                if not re.search(r"export const DURATION\s*=\s*\d+", src):
                    out.append(("%s: export `DURATION` (frames at 30 fps) — the gates find its settled frame from it"
                                % where, True))
                g = _ground_of(src)
                if g is None:
                    out.append(("%s: export `GROUND` — the DNA token its ground is painted from (%s) or a '#hex'; "
                                "the burned caption picks its ink from it" % (where, ", ".join(GROUND_TOKENS)), False))
                elif not _ground_ok(g):
                    out.append(("%s: GROUND %r is not a DNA ground token (%s), a list of them, or a '#hex'"
                                % (where, g, ", ".join(GROUND_TOKENS)), False))
                pm = _PROVENANCE.search(src)
                if not pm or not pm.group(1):
                    out.append(("%s: export `PROVENANCE` — the idiom world its look comes from (%s)"
                                % (where, ", ".join(worlds)), False))
                elif pm.group(1) not in worlds:
                    out.append(("%s: PROVENANCE %r is not one of %s" % (where, pm.group(1), ", ".join(worlds)), False))
            else:
                meta = object_meta(src)
                if meta is None:
                    out.append(("%s: export `META: ObjectMeta` — {aspect, provenance}" % where, False))
                    continue
                if not meta.get("provenance"):
                    out.append(("%s: META.provenance names the idiom world its look comes from (%s)"
                                % (where, ", ".join(worlds)), False))
                elif meta["provenance"] not in worlds:
                    out.append(("%s: META.provenance %r is not one of %s"
                                % (where, meta["provenance"], ", ".join(worlds)), False))
                if meta.get("demo"):
                    out.append(("%s: `demo` marks a stage's own preview object; a film's object is never one" % where,
                                False))
    return out


def names_problems(out_dir):
    """Every layout and declaration problem, as sentences."""
    return [p for p, _blocking in _problems(out_dir)]


def index_blockers(out_dir):
    """The problems an index cannot be written around."""
    return [p for p, blocking in _problems(out_dir) if blocking]


def write_index(out_dir):
    """Regenerate <workshop>/index.ts from the two folders and return its path. A BLOCKING problem raises
    WorkshopError — an index is never written around a name the render would refuse; the rest wait for `check`."""
    probs = index_blockers(out_dir)
    if probs:
        raise WorkshopError(probs)
    shots, objs = sorted(shot_names(out_dir)), sorted(object_names(out_dir))
    L = ["// GENERATED by scripts/workshop.py from shots/ and objects/ — do not edit; rewritten before every render.",
         "import type React from 'react';",
         "import type {ObjectEntry} from '@runtime/objectSlot';",
         "import type {GroundSpec} from '@runtime/shotLuma';"]
    L += ["import * as S_%s from './shots/%s';" % (n, n) for n in shots]
    L += ["import * as O_%s from './objects/%s';" % (n, n) for n in objs]
    L += ["", "export const WORKSHOP_SHOTS: Record<string, {C: React.FC<any>; d: number; ground: GroundSpec}> = {"]
    L += ["  %s: {C: S_%s.%s, d: S_%s.DURATION, ground: S_%s.GROUND as GroundSpec}," % (n, n, n, n, n) for n in shots]
    L += ["};", "export const WORKSHOP_OBJECTS: Record<string, ObjectEntry> = {"]
    L += ["  %s: {C: O_%s.%s, meta: O_%s.META}," % (n, n, n, n) for n in objs]
    L += ["};", ""]
    text = "\n".join(L)
    path = os.path.join(workshop_dir(out_dir), "index.ts")
    if not (os.path.isfile(path) and _read(path) == text):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return path


def prepare(out_dir):
    """The environment for a remotion call scoped to this film — or None when nothing needs to change.

    A film with a workshop: its index regenerated, SLIDES_WORKSHOP set to it (absolute). A film without one:
    None — unless this process inherited SLIDES_WORKSHOP, in which case a copy of the environment WITHOUT it."""
    if out_dir and has_items(out_dir):
        write_index(out_dir)
        return dict(os.environ, **{ENV_VAR: workshop_dir(out_dir)})
    if ENV_VAR in os.environ:
        return {k: v for k, v in os.environ.items() if k != ENV_VAR}
    return None


def run_kwargs(out_dir):
    """`subprocess.run(..., **run_kwargs(out_dir))` — {} leaves a call exactly as it was before workshops."""
    env = prepare(out_dir)
    return {"env": env} if env is not None else {}


def code_files(out_dir):
    """Every workshop file a render is built from (objects/, shots/, assets/) — for the segment cache key. The
    generated files are left out: the index is a function of these names, and the names are hashed."""
    if not out_dir:
        return []
    ws, out = workshop_dir(out_dir), []
    for sub in KINDS + ("assets",):
        for dp, dn, fn in os.walk(os.path.join(ws, sub)):
            dn[:] = sorted(d for d in dn if not d.startswith("."))
            out += [os.path.join(dp, f) for f in fn if not f.startswith(".")]
    return sorted(out)


def source_files(out_dir):
    """The workshop's code: every .tsx and .ts in objects/ and shots/."""
    ws = workshop_dir(out_dir)
    return sorted(p for kind in KINDS for p in glob.glob(os.path.join(ws, kind, "*.ts*"))
                  if p.endswith((".ts", ".tsx")))


_IMPORT = re.compile(r"""(?:\bfrom\s+|\bimport\s*\(\s*|^\s*import\s+)['"]([^'"]+)['"]""", re.M)


def import_problems(out_dir, files):
    """A workshop may import react, remotion (and the project's other dependencies), the runtime as
    @runtime/<module>, library registers as @shots/<Name>, and its own files. Nothing else resolves."""
    pkg = json.loads(_read(os.path.join(REMOTION, "package.json")))
    deps = set(pkg.get("dependencies") or {}) | set(pkg.get("devDependencies") or {})
    ws, lib, probs = workshop_dir(out_dir), library_shot_names(), []
    for f in files:
        rel = os.path.relpath(f, os.path.dirname(ws))
        for spec in _IMPORT.findall(_strip_comments(_read(f))):
            if spec.startswith("@runtime/"):
                mod = spec[len("@runtime/"):]
                if not any(os.path.isfile(os.path.join(RUNTIME, mod + e)) for e in ("", ".ts", ".tsx", ".json")):
                    probs.append("%s imports %s — there is no runtime module %r (references/building-blocks.md "
                                 "lists them)" % (rel, spec, mod))
            elif spec.startswith("@shots/"):
                if spec[len("@shots/"):] not in lib:
                    probs.append("%s imports %s — there is no library register %r" % (rel, spec, spec[7:]))
            elif spec.startswith("."):
                target = os.path.normpath(os.path.join(os.path.dirname(f), spec))
                if not (target + os.sep).startswith(ws + os.sep):
                    probs.append("%s imports %s, outside the film's workshop — film code may use react, remotion, "
                                 "@runtime/…, @shots/… and its own workshop files" % (rel, spec))
                elif not any(os.path.exists(target + e) for e in ("", ".ts", ".tsx", ".json", "/index.ts")):
                    probs.append("%s imports %s, which does not exist" % (rel, spec))
            else:
                name = "/".join(spec.split("/")[:2]) if spec.startswith("@") else spec.split("/")[0]
                if name not in deps:
                    probs.append("%s imports %r, which is not a dependency of remotion/package.json — a workshop "
                                 "cannot add packages" % (rel, spec))
    return probs


def contract_problems(out_dir, files):
    """The content contract (scripts/content_contract_qa.py) over the workshop's code."""
    import content_contract_qa as cq
    ws, probs = workshop_dir(out_dir), []
    for f in files:
        name = os.path.basename(f).rsplit(".", 1)[0]
        for line, rule, text in cq.violations(_read(f), name):
            probs.append("%s:%d [%s] %s — every status, emphasis or quantity it shows must come from the film "
                         "(declare `// @%s: <why>` only when it is genuinely not a claim)"
                         % (os.path.relpath(f, os.path.dirname(ws)), line, rule, text.strip()[:100], rule))
    return probs


_RULE_WORDS = {"jsx-text": "text written in the JSX", "jsx-literal": "a literal drawn as text",
               "word-attr": "a literal handed to a words prop", "default-copy": "a default that prints when "
               "the film passes nothing", "cjk-literal": "Chinese written into the code"}


def baked_words(out_dir, files):
    """{"problems": [...], "declared": [...]} — words a viewer would read that no prop supplies (jsx_words.cjs)."""
    node = shutil.which("node")
    tsmod = os.path.join(REMOTION, "node_modules", "typescript")
    code = [f for f in files if f.endswith((".tsx", ".ts"))]
    if not code:
        return {"problems": [], "declared": []}
    if not node or not os.path.isdir(tsmod):
        return {"problems": ["the baked-words scan could not run: node or remotion/node_modules/typescript is "
                             "missing — nothing was checked"], "declared": []}
    r = subprocess.run([node, os.path.join(_HERE, "jsx_words.cjs"), tsmod] + code, capture_output=True, text=True)
    if r.returncode != 0:
        return {"problems": ["the baked-words scan failed: %s" % ((r.stderr or r.stdout).strip()[-300:] or
                                                                  "(no output)")], "declared": []}
    got = json.loads(r.stdout or "{}")
    base = os.path.dirname(workshop_dir(out_dir))
    probs = ["%s:%d words written into the code (%s): %r — every word on screen comes from a prop; a word that "
             "is genuinely part of the form (a unit symbol, an axis letter) is declared with "
             "`// @fixed-text: <why>`" % (os.path.relpath(h["file"], base), h["line"],
                                          _RULE_WORDS.get(h["rule"], h["rule"]), h["text"])
             for h in got.get("hits") or []]
    return {"problems": probs, "declared": list(got.get("declared") or [])}


def typecheck(out_dir):
    """tsc over the workshop, with the project's own settings and the three aliases. [] when it is clean."""
    tsc = os.path.join(REMOTION, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        return ["the type-check could not run: %s is missing (npm install in remotion/) — nothing was checked" % tsc]
    ws = workshop_dir(out_dir)
    write_index(out_dir)
    cfg = {"extends": os.path.join(REMOTION, "tsconfig.json"),
           "compilerOptions": {
               "noEmit": True,
               "typeRoots": [os.path.join(REMOTION, "node_modules", "@types")],
               "paths": {"@workshop": [os.path.join(ws, "index.ts")],
                         "@runtime/*": [os.path.join(RUNTIME, "*")],
                         "@shots/*": [os.path.join(LIB_SHOTS, "*")],
                         "*": [os.path.join(REMOTION, "node_modules", "*"),
                               os.path.join(REMOTION, "node_modules", "@types", "*")]}},
           "include": [os.path.join(ws, "objects"), os.path.join(ws, "shots"), os.path.join(ws, "index.ts"),
                       os.path.join(REMOTION, "src", "*.d.ts")]}
    path = os.path.join(ws, ".tsconfig.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=1)
    r = subprocess.run([tsc, "-p", path], cwd=REMOTION, capture_output=True, text=True)
    errs = [ln.strip() for ln in (r.stdout + r.stderr).splitlines() if "error TS" in ln]
    if r.returncode != 0 and not errs:
        return ["the type-check failed without naming an error: %s" % ((r.stdout + r.stderr).strip()[-300:] or
                                                                        "(no output)")]
    return ["type error: %s" % e for e in errs]


def check(out_dir):
    """Every problem in this film's workshop, as sentences — [] when it is clean or there is none."""
    if not os.path.isdir(workshop_dir(out_dir)):
        return []
    probs = names_problems(out_dir)
    files = source_files(out_dir)
    probs += import_problems(out_dir, files)
    probs += contract_problems(out_dir, files)
    probs += baked_words(out_dir, files)["problems"]
    if not index_blockers(out_dir) and has_items(out_dir):
        probs += typecheck(out_dir)
    return probs


OBJECT_SCAFFOLD = """// OBJECT · %(name)s — %(means)s
// A film-local object (scripts/workshop.py). It ENCODES its beat: hide the caption and it still carries the idea.
// Every word it draws comes from a prop; it sizes to its box (w × h); it is a pure function of t (0 → 1, then
// held) — no Math.random, no Date. Read references/object-authoring.md before drawing it and
// references/building-blocks.md for what to draw it with. It goes into a register with a slot for one (a prop
// typed ObjectRef): ObjectStage, ObjectCompare, ObjectPath, ObjectTurntable, TechnicalPlate `art`, HudReticle
// `object`, or a device's screen.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01, seg, easeOutCubic} from '@runtime/motion';

// provenance: the idiom world this object's look comes from — one of shot_director.IDIOM_WORLDS.
export const META: ObjectMeta = {aspect: 1, provenance: ''};

// @scaffold — replace this body with the real drawing, then delete this line.
export const %(name)s: React.FC<ObjectProps> = ({w, h, t, dna}) => {
  const ink = dna?.fg ?? '#1c2230', acc = dna?.accent ?? '#3563e9';
  const on = easeOutCubic(clamp01(seg(t, 0, 1)));
  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      <rect x={w * 0.1} y={h * 0.1} width={w * 0.8 * on} height={h * 0.8} fill="none" stroke={acc}
        strokeWidth={Math.max(2, w * 0.006)} />
      <line x1={w * 0.1} y1={h * 0.9} x2={w * 0.9} y2={h * 0.9} stroke={ink} strokeWidth={Math.max(1, w * 0.003)} />
    </svg>
  );
};
"""

SHOT_SCAFFOLD = """// SHOT · %(name)s — %(means)s
// A film-local register (scripts/workshop.py): a template this film needs because no library register's STRUCTURE
// carries this beat. Every word on screen comes from a prop; content stays inside the content zone (above
// contentBottom); colours come from the Design DNA with fallbacks; it is a pure function of the frame. Read
// references/remotion-shot-authoring.md (the frame-craft floor) and references/building-blocks.md. It may hold
// objects (a prop typed ObjectRef drawn with <ObjectSlot object=… box=…/>) and may wrap a library register
// (import {X} from '@shots/X').
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '@runtime/motion';
import {CONTENT_TOP, contentBottom} from '@runtime/layout';
import {useDNA} from '@runtime/dna';

export const DURATION = 150;
// the DNA token this shot paints its ground from ('bg', 'bgGrad', 'surface', 'accent', 'accent2') or a '#hex' —
// the burned caption picks its ink from it, and scripts/shot_proof.py measures the claim
export const GROUND = 'bg';
// the idiom world its look comes from — one of shot_director.IDIOM_WORLDS
export const PROVENANCE = '';

// @scaffold — replace this body with the real design, then delete this line.
export const %(name)s: React.FC<{title?: string}> = ({title = ''}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const on = easeOutCubic(clamp01(seg(t, 0.05, 0.3)));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? '#0a0f16', color: dna?.fg ?? '#e8eef6'}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: (CONTENT_TOP + contentBottom(W, H)) / 2,
        textAlign: 'center', opacity: on,
        font: `700 ${Math.round(W * 0.03)}px/1.2 var(--f-display, system-ui, sans-serif)`}}>{title}</div>
    </AbsoluteFill>
  );
};
"""


def scaffold(out_dir, kind, name, means):
    """Write a new object or shot into the workshop and return its path; refuse a bad or taken name."""
    folder = {"object": "objects", "shot": "shots"}.get(kind)
    if folder is None:
        raise WorkshopError(["kind is object or shot (got %r)" % (kind,)])
    probs = []
    if not NAME.match(name or ""):
        probs.append("%r: a name is PascalCase, 3-32 letters and digits" % (name,))
    elif name in library_shot_names() or name in library_object_names():
        probs.append("%s is already in the library — pick another name, or use the library's" % name)
    elif name in shot_names(out_dir) | object_names(out_dir):
        probs.append("%s is already in this film's workshop" % name)
    if not str(means or "").strip():
        probs.append("--means: say what the viewer must see — it heads the file and the build-list entry")
    if probs:
        raise WorkshopError(probs)
    d = os.path.join(workshop_dir(out_dir), folder)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name + ".tsx")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write((OBJECT_SCAFFOLD if kind == "object" else SHOT_SCAFFOLD)
                 % {"name": name, "means": " ".join(str(means).split())})
    return path


def _board(out_dir):
    try:
        return json.loads(_read(os.path.join(out_dir, "storyboard.json")))
    except (OSError, ValueError):
        return {}


def still(out_dir, name, props=None, host="ObjectStage", frame=None, aspect=None):
    """Render `name`'s settled frame on its own into <workshop>/_stills/<name>.png and return that path — a shot
    as its own composition (props: the given ones, else its first beat's), an object on `host` (props: the
    object's own)."""
    import render_remotion as rr
    board = _board(out_dir)
    meta = board.get("meta") or {}
    if name in shot_names(out_dir):
        comp = name
        payload = dict(props) if props is not None else {}
        if props is None:
            beat = next((s for s in board.get("slides") or [] if s.get("shot") == name), None)
            payload = rr.film_shot_props(beat, out_dir) if beat else {}
        dur = durations(out_dir)[name]
    elif name in object_names(out_dir) or name in library_object_names():
        comp = host
        payload = {"object": dict({"id": name}, **({"props": props} if props else {}))}
        src = shot_source(out_dir, host)
        if src is None:
            raise WorkshopError(["%s is not a register with a slot this film can use" % host])
        dur = int(re.search(r"export const DURATION\s*=\s*(\d+)", src).group(1))
    else:
        raise WorkshopError(["%s is not in this film's workshop or the library's objects" % name])
    dna = meta.get("design_dna") or meta.get("shot_template")
    if dna:
        payload.setdefault("dna", dna)
    if aspect or meta.get("aspect"):
        payload.setdefault("aspect", aspect or meta["aspect"])
    frame = int(round(rr.frame_at_t(dur, rr.SETTLED_T))) if frame is None else int(frame)
    outd = os.path.join(workshop_dir(out_dir), "_stills")
    os.makedirs(outd, exist_ok=True)
    pf = os.path.join(outd, name + ".props.json")
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    png = os.path.join(outd, name + ".png")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", comp, png, "--frame=%d" % frame, "--gl=angle",
                        "--log=error", "--props=" + pf, "--public-dir=" + os.path.abspath(out_dir)],
                       cwd=REMOTION, capture_output=True, text=True, **run_kwargs(out_dir))
    if r.returncode != 0 or not os.path.exists(png):
        import cjk_type_qa
        raise WorkshopError(["the still of %s failed: %s" % (name, cjk_type_qa._why_it_refused(r.stdout + r.stderr))])
    return png


def _list(out_dir):
    board = _board(out_dir)
    used = uses(board.get("slides") or [], out_dir)
    listed = {e.get("id") for e in (board.get("meta") or {}).get("build_list") or [] if isinstance(e, dict)}
    print("[workshop] %s" % workshop_dir(out_dir))
    rows = [("shot", n) for n in sorted(shot_names(out_dir))] + [("object", n) for n in sorted(object_names(out_dir))]
    for kind, n in rows:
        print("  %-6s %-24s beats %-12s %s" % (kind, n, ", ".join(map(str, used.get(n) or [])) or "-",
                                               "on the build list" if n in listed else "NOT on the build list"))
    if not rows:
        print("  (empty) — python3 scripts/workshop.py %s new-object <Name> --means \"...\"" % out_dir)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="A film's workshop: the objects and shots it builds for itself.")
    ap.add_argument("out_dir")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("check")
    for k in ("new-object", "new-shot"):
        p = sub.add_parser(k)
        p.add_argument("name")
        p.add_argument("--means", required=True)
    p = sub.add_parser("still")
    p.add_argument("name")
    p.add_argument("--props", help="a JSON file: the shot's props, or the object's own props")
    p.add_argument("--host", default="ObjectStage")
    p.add_argument("--frame", type=int)
    p.add_argument("--aspect")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "list":
            return _list(a.out_dir)
        if a.cmd == "check":
            probs = check(a.out_dir)
            for x in probs:
                print("  PROBLEM: " + x)
            print("[workshop] %s — %d problem(s)" % ("CLEAN" if not probs else "NOT CLEAN", len(probs)))
            if not probs:
                print("NEXT: python3 scripts/validate.py %s" % a.out_dir)
            return 1 if probs else 0
        if a.cmd in ("new-object", "new-shot"):
            path = scaffold(a.out_dir, a.cmd[4:], a.name, a.means)
            print("[workshop] wrote %s" % path)
            print("NEXT: draw it (references/object-authoring.md), then python3 scripts/workshop.py %s still %s"
                  % (a.out_dir, a.name))
            return 0
        props = json.loads(_read(a.props)) if a.props else None
        png = still(a.out_dir, a.name, props, host=a.host, frame=a.frame, aspect=a.aspect)
        print("[workshop] %s" % png)
        print("NEXT: open it and LOOK — does it carry its build-list entry's `means` with the caption hidden?")
        return 0
    except WorkshopError as e:
        for x in e.problems:
            print("  PROBLEM: " + x)
        return 1


if __name__ == "__main__":
    sys.exit(main())
