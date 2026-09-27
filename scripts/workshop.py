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
    # I2 (task-2-fix-1.md): glob.glob interprets `[...]`/`*`/`?` IN THE PATH ITSELF as wildcards — a film
    # folder named "film [v2]" made a real shot on disk invisible (the bracket expression matched nothing),
    # and one named "film*" pulled a sibling film's shots in. os.listdir treats `folder` as a literal path.
    if not os.path.isdir(folder):
        return []
    return sorted(f[:-4] for f in os.listdir(folder) if f.endswith(".tsx"))


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


# M6 (task-2-fix-1.md): tolerates a missing trailing semicolon (ASI) and a trailing `satisfies ObjectMeta` /
# `as const` (in either order) after the object literal — all valid TypeScript the strict `\s*;` used to miss.
_META = re.compile(r"export const META\b[^=]*=\s*\{(.*?)\}\s*(?:(?:as\s+const|satisfies\s+\w+)\s*)*;?", re.S)


def object_meta(src):
    """An object's META as {aspect, turns, demo, provenance} (only the keys it sets), or None if it has none.
    `aspect` is None when it is DECLARED but unparseable, non-finite or not positive (`1.2.3`, `16 / 0`) — this
    never raises (M5); `names_problems`/`check` report a None aspect as a problem instead."""
    m = _META.search(_strip_comments(src or ""))   # M6: declarations are read from comment-stripped source
    if not m:
        return None
    body, meta = m.group(1), {}
    a = re.search(r"\baspect\s*:\s*([0-9.]+(?:\s*/\s*[0-9.]+)?)", body)
    if a:
        num = a.group(1).replace(" ", "")
        try:
            val = (float(num.split("/")[0]) / float(num.split("/")[1])) if "/" in num else float(num)
            if not (val == val and 0 < val < float("inf")):   # NaN, non-positive or infinite
                val = None
        except (ValueError, ZeroDivisionError):
            val = None
        meta["aspect"] = val
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


# I3 (task-2-fix-1.md): ONE anchored parser for DURATION, shared by _problems(), durations() and still() (its
# host too) — an unanchored `=\s*(\d+)` used to misread `= 6 * 30;` as 6 (the settled frame then judged
# mid-entry), `= 150.5;` as 150, let `= 0;` through to a registry-load crash, refuse a valid `: number = 150;`
# as "no DURATION" (and then KeyError inside still()), and let a commented-out `// export const DURATION = …;`
# win over a real one below it. On comment-stripped source; anything but `export const DURATION = <positive
# whole number>;` (an optional `: number` type annotation allowed) comes back None.
_DURATION = re.compile(r"^export const DURATION\s*(?::\s*number\s*)?=\s*(\d+)\s*;", re.M)
_DURATION_FORM = "export const DURATION = <frames>;` — a positive whole number of frames"


def _duration_of(src):
    """The frames `export const DURATION = <n>;` declares, or None (missing, an expression, a decimal, zero, or
    hidden behind `//` — see _DURATION above)."""
    m = _DURATION.search(_strip_comments(src or ""))
    if not m:
        return None
    n = int(m.group(1))
    return n if n > 0 else None


def _required_duration(src, label):
    """DURATION for `label` (a shot or a host register), or a WorkshopError sentence — never a raw KeyError
    (durations()) or AttributeError (`.group(1)` on no match), both of which still() used to raise directly."""
    d = _duration_of(src)
    if d is None:
        raise WorkshopError(["%s: DURATION must be `%s (the gates find its settled frame from it)"
                             % (label, _DURATION_FORM)])
    return d


def durations(out_dir):
    """{workshop shot: DURATION} — the frame count every film-mode gate needs to find a beat's settled frame."""
    out = {}
    for n in shot_names(out_dir):
        d = _duration_of(_read(os.path.join(workshop_dir(out_dir), "shots", n + ".tsx")))
        if d is not None:
            out[n] = d
    return out


_GROUND = re.compile(r"export const GROUND\b[^=]*=\s*(\[[^\]]*\]|'[^']*'|\"[^\"]*\")")
_PROVENANCE = re.compile(r"export const PROVENANCE\b[^=]*=\s*['\"]([^'\"]*)['\"]")


def _ground_of(src):
    m = _GROUND.search(_strip_comments(src or ""))   # M6: comment-stripped, like every other declaration
    if not m:
        return None
    raw = m.group(1)
    return re.findall(r"['\"]([^'\"]+)['\"]", raw) if raw.startswith("[") else raw[1:-1]


def _ground_ok(g):
    if isinstance(g, list):
        return bool(g) and all(x in GROUND_TOKENS for x in g)
    return g in GROUND_TOKENS or re.fullmatch(r"#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}", g or "") is not None


def grounds(out_dir):
    """{workshop shot: the ground it declares, or None when it hasn't declared one} — what the caption ink and
    the seam guard judge it on."""
    return {n: _ground_of(_read(os.path.join(workshop_dir(out_dir), "shots", n + ".tsx"))) for n in shot_names(out_dir)}


def _provenance_of(src):
    m = _PROVENANCE.search(_strip_comments(src or ""))   # M6: comment-stripped, like every other declaration
    return m.group(1) if m else None


def provenances(out_dir):
    """{workshop shot or object: the idiom world it declares}."""
    out = {}
    for n in shot_names(out_dir):
        prov = _provenance_of(_read(os.path.join(workshop_dir(out_dir), "shots", n + ".tsx")))
        if prov:
            out[n] = prov
    for n in object_names(out_dir):
        meta = object_meta(_read(os.path.join(workshop_dir(out_dir), "objects", n + ".tsx"))) or {}
        if meta.get("provenance"):
            out[n] = meta["provenance"]
    return out


def _worlds():
    import shot_director
    return list(shot_director.IDIOM_WORLDS)


# M1 (task-2-fix-1.md): `[^<]*?` (not `[^\n]*?`) so `id="…"` is found even on a LATER line of the same
# `<Composition …>`/`<Still …>` element — bounded by the NEXT `<` (the start of a sibling element), which a
# `=> (...)` arrow inside the same tag (e.g. `calculateMetadata`) can never contain, so it can't prematurely
# end the scan the way excluding `>` instead would (an arrow contains a literal `>`).
_COMPOSITION_ID = re.compile(r'<(?:Composition|Still)\b[^<]*?\bid="([A-Za-z0-9_]+)"')
_F_ROW_ID = re.compile(r"\bF\(\s*'([A-Za-z0-9_]+)'")   # already spans line breaks: \s* matches \n too


def _root_composition_ids():
    """Every composition id remotion/src/Root.tsx registers directly (R9): `Film` and `StageProbe` as
    `<Composition id="…">` attributes, `TypeSpecimen`, `FontProbe` and the other `*Probe` ids as
    `{F('<Id>', …)}` rows. Read from Root.tsx itself, not a hard-coded list, so a future composition Root.tsx
    adds is covered automatically — but MOST of what this returns (187 of 202, 2026-09-27) is ALSO a file in
    src/shots/ or src/objects/, which library_shot_names()/library_object_names() already see and report with
    their own, more specific message; a caller wanting the R9-only names subtracts those two sets itself
    (M1: `_root_composition_ids() - library_shot_names() - library_object_names()` — TermTable used to get two
    messages). Raises if the result does not contain "Film" — Root.tsx's own format changing in a way this
    parser no longer understands must be loud, not a silently incomplete set that under-refuses forever."""
    src = _strip_comments(_read(ROOT_TSX))
    ids = set(_COMPOSITION_ID.findall(src)) | set(_F_ROW_ID.findall(src))
    if "Film" not in ids:
        raise RuntimeError("Root.tsx's own composition ids no longer include \"Film\" — "
                           "_root_composition_ids()'s parser (scripts/workshop.py) needs updating for "
                           "whatever changed there")
    return ids


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


_TOP_SLOT_SCAN = re.compile(r"[{}]|" + _SLOT_KEY.pattern)   # the SAME "typed ObjectRef" shape as _SLOT_KEY


def _top_level_object_ref_keys(host_src, host_name):
    """Prop names `host_src`'s OWN `export const <host_name>: React.FC<{…}>` types `ObjectRef` at brace depth 1
    of THAT (and only that) type literal (I4, task-2-fix-1.md; anchored on the export's own name — fix round
    2's Important finding) — the ones still() can place an object under without knowing the host's nested shape
    (TechnicalPlate's `art`; a device's `steps[i].screen.object` is depth 2, and does NOT count).

    Anchored on `export const <host_name>`, not the first `React.FC<{` in the file: 35 of the 187 library
    registers declare a HELPER component before their export (DeviceDemo.tsx's own `DemoPage`, before
    `export const DeviceDemo`) — scanning the first occurrence read the helper's props literal instead of the
    host's own, so injecting a slot into DeviceDemo's real export was read as [] (DemoPage's shape, not
    DeviceDemo's). Matched by counting braces, not angle brackets: the literal's own body holds arrow functions
    (`=>`), which a naive `<...>` scan would misread as closing the generic early. [] when there is no such
    export, or it does not declare its props as an inline object literal (186 of 187 library registers that DO
    export this way do)."""
    src = _strip_comments(host_src or "")
    m = re.search(r"export const %s\s*:\s*React\.FC<\s*\{" % re.escape(host_name), src)
    if not m:
        return []
    depth, keys = 1, []
    for tm in _TOP_SLOT_SCAN.finditer(src, m.end()):
        tok = tm.group()
        if tok == "{":
            depth += 1
        elif tok == "}":
            depth -= 1
            if depth == 0:
                break
        elif depth == 1 and tm.group(1):
            keys.append(tm.group(1))
    return keys


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


def _clash_with(name, lib_s, lib_o, comp_ids):
    """None, or why `name` cannot be a workshop item's name because the LIBRARY already has it — a shot
    register, an object, or (R9) a composition id Root.tsx registers directly. `lib_s`/`lib_o` are
    library_shot_names()/library_object_names(); `comp_ids` is `_root_composition_ids() - lib_s - lib_o` (M1,
    task-2-fix-1.md: a name already caught by one of the first two gets that more specific reason, not also
    this one — TermTable is both a library shot file and an {F('TermTable', …)} row). The core `_problems()`
    (an existing file) and `scaffold()` (M2: refuses BEFORE writing one) share — see `_library_or_composition_
    clash()` below for the single-name convenience wrapper `scaffold()` actually calls."""
    if name in lib_s:
        return "%s is already a library register — rename it (the render refuses a shadowed name)" % name
    if name in lib_o:
        return "%s is already a library object — rename it" % name
    if name in comp_ids:
        return "%s is already a library composition — rename it (Root.tsx registers it directly)" % name
    return None


def _library_or_composition_clash(name):
    """`_clash_with(name, ...)` for a caller that checks a single name per call (scaffold()) — computes its own
    library_shot_names()/library_object_names()/_root_composition_ids() rather than taking them as arguments.
    `_problems()` computes those three ONCE and calls `_clash_with` directly across its whole loop instead, so
    a workshop with several items does not re-read the library and Root.tsx once per item."""
    lib_s, lib_o = library_shot_names(), library_object_names()
    return _clash_with(name, lib_s, lib_o, _root_composition_ids() - lib_s - lib_o)


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
    worlds = _worlds()
    lib_s, lib_o = library_shot_names(), library_object_names()
    comp_ids = _root_composition_ids() - lib_s - lib_o   # read the library/Root.tsx ONCE, not once per item
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
            clash = _clash_with(n, lib_s, lib_o, comp_ids)
            if clash:
                out.append(("%s: %s" % (where, clash), True))
            src = _read(os.path.join(folder, n + ".tsx"))
            # M6 (task-2-fix-1.md): every declaration check below reads comment-stripped source — EXCEPT the
            # scaffold marker just below, which IS a comment (`// @scaffold …`) and must stay on the raw one.
            if not re.search(r"export const %s\b" % re.escape(n), _strip_comments(src)):
                out.append(("%s: export the component as `export const %s`" % (where, n), True))
            if SCAFFOLD_MARK in src:
                out.append(("%s: still the scaffold — draw the real %s, then delete the `%s` line"
                            % (where, kind[:-1], SCAFFOLD_MARK), False))
            if kind == "shots":
                if _duration_of(src) is None:
                    out.append(("%s: DURATION must be `%s" % (where, _DURATION_FORM), True))
                g = _ground_of(src)
                if g is None:
                    out.append(("%s: export `GROUND` — the DNA token its ground is painted from (%s) or a '#hex'; "
                                "the burned caption picks its ink from it" % (where, ", ".join(GROUND_TOKENS)), False))
                elif not _ground_ok(g):
                    out.append(("%s: GROUND %r is not a DNA ground token (%s), a list of them, or a '#hex'"
                                % (where, g, ", ".join(GROUND_TOKENS)), False))
                prov = _provenance_of(src)
                if not prov:
                    out.append(("%s: export `PROVENANCE` — the idiom world its look comes from (%s)"
                                % (where, ", ".join(worlds)), False))
                elif prov not in worlds:
                    out.append(("%s: PROVENANCE %r is not one of %s" % (where, prov, ", ".join(worlds)), False))
            else:
                meta = object_meta(src)
                if meta is None:
                    out.append(("%s: export `META: ObjectMeta` — {aspect, provenance}" % where, False))
                    continue
                if "aspect" in meta and meta["aspect"] is None:
                    out.append(("%s: META.aspect must be a positive number (optionally `a / b`) — the slot fits "
                                "the object to it" % where, False))
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
    if not os.path.isdir(workshop_dir(out_dir)):
        # M5 (task-2-fix-1.md): `open(<workshop>/index.ts, "w")` below needs the workshop/ folder to already
        # exist — a raw FileNotFoundError otherwise. A film's own callers only reach here through prepare(),
        # guarded by has_items(), so this is for write_index()/typecheck() called directly (both public).
        raise WorkshopError(["%s has no workshop yet — nothing to index" % workshop_dir(out_dir)])
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
    """The workshop's code: every .ts and .tsx under objects/ and shots/, at any depth — a helper module may sit
    in its own subfolder. M4 (task-2-fix-1.md): the SAME traversal code_files() uses, so a helper is hashed for
    the render cache AND import/contract/baked-words checked, never just the former. (I2: os.walk, not
    glob.glob, so a folder name with `[...]`/`*`/`?` in it is never misread as a wildcard.)"""
    ws, out = workshop_dir(out_dir), []
    for kind in KINDS:
        for dp, dn, fn in os.walk(os.path.join(ws, kind)):
            dn[:] = sorted(d for d in dn if not d.startswith("."))
            out += [os.path.join(dp, f) for f in fn if not f.startswith(".") and f.endswith((".ts", ".tsx"))]
    return sorted(out)


_IMPORT = re.compile(r"""(?:\bfrom\s+|\bimport\s*\(\s*|^\s*import\s+)['"]([^'"]+)['"]""", re.M)


def import_problems(out_dir, files):
    """A workshop may import react, remotion (and the project's other dependencies), the runtime as
    @runtime/<module>, library registers as @shots/<Name>, and its own files under objects/, shots/ or assets/
    (M4: what code_files() hashes for the render cache key — a file at the workshop root is never reached by a
    render, so editing it would not change the key). Nothing else resolves."""
    pkg = json.loads(_read(os.path.join(REMOTION, "package.json")))
    deps = set(pkg.get("dependencies") or {}) | set(pkg.get("devDependencies") or {})
    ws, lib, probs = workshop_dir(out_dir), library_shot_names(), []
    roots = [os.path.join(ws, d) for d in KINDS + ("assets",)]
    for f in files:
        # M3 (task-2-fix-1.md): workshop_dir() is always absolute; a RELATIVE `f` made every `target` below
        # relative too, so it could never match the `ws`/roots prefix check and every "./helper" import was
        # wrongly reported as outside the workshop.
        f = os.path.abspath(f)
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
                elif not any((target + os.sep).startswith(root + os.sep) for root in roots):
                    # M4: inside the workshop, but not inside objects/, shots/ or assets/ (e.g. the workshop
                    # root itself, or its generated index.ts/_stills/) — code_files() never hashes it.
                    probs.append("%s imports %s — a workshop file may only import its own files under objects/, "
                                 "shots/ or assets/ (what code_files() hashes for the render cache key); "
                                 "nothing else in the workshop is reached by a render" % (rel, spec))
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
            # I1 (task-2-fix-1.md): content_contract_qa._declared only accepts the TAG in cq._DECL[rule]
            # (cycle->cycles, position/relabel->positional, retype/fallback->fallback, invent->decor,
            # truncate->truncates) — printing `rule` itself told an author to write a declaration the checker
            # does not recognise, so it never went away.
            probs.append("%s:%d [%s] %s — every status, emphasis or quantity it shows must come from the film "
                         "(declare `// @%s: <why>` only when it is genuinely not a claim)"
                         % (os.path.relpath(f, os.path.dirname(ws)), line, rule, text.strip()[:100],
                            cq._DECL.get(rule, rule)))
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
    else:
        clash = _library_or_composition_clash(name)   # M2: the SAME check _problems() refuses an item with
        if clash:
            probs.append(clash)
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


def still(out_dir, name, props=None, host="ObjectStage", frame=None, aspect=None, slot=None):
    """Render `name`'s settled frame on its own into <workshop>/_stills/<name>.png and return that path — a shot
    as its own composition (props: the given ones, else its first beat's), an object on `host`.

    An object's `props`, when given, is tried FIRST as the host's own full props with the object already
    placed somewhere in them (object_refs() finds a ref to `name`) — how a device screen is previewed; used
    as given, unchanged. Otherwise it is the object's OWN sub-props, and the object goes under `slot` (a
    top-level ObjectRef slot of the host — I4, task-2-fix-1.md) if given, else the host's single one; refused
    when the host has none or several, naming them either way — never silently hard-coded to "object", which
    only ever happened to be right for ObjectStage."""
    import render_remotion as rr
    board = _board(out_dir)
    meta = board.get("meta") or {}
    if name in shot_names(out_dir):
        comp = name
        payload = dict(props) if props is not None else {}
        if props is None:
            beat = next((s for s in board.get("slides") or [] if s.get("shot") == name), None)
            payload = rr.film_shot_props(beat, out_dir) if beat else {}
        dur = _required_duration(shot_source(out_dir, name), name)   # I3: a sentence, never a raw KeyError
    elif name in object_names(out_dir) or name in library_object_names():
        comp = host
        src = shot_source(out_dir, host)
        if src is None:
            raise WorkshopError(["%s is not a register with a slot this film can use" % host])
        placed = any(isinstance(ref, dict) and ref.get("id") == name for _p, ref in object_refs(src, props or {}))
        if placed:
            payload = dict(props)
        else:
            top = _top_level_object_ref_keys(src, host)
            if slot is not None:
                if slot not in top:
                    raise WorkshopError(["%s has no top-level object slot %r — its own are: %s"
                                         % (host, slot, ", ".join(top) if top else "(none)")])
                use_slot = slot
            elif len(top) == 1:
                use_slot = top[0]
            elif not top:
                raise WorkshopError(["%s has no object slot of its own — use a host that has one, e.g. "
                                     "ObjectStage, or pass props that place the object" % host])
            else:
                raise WorkshopError(["%s has several: %s — pass --slot" % (host, ", ".join(top))])
            payload = {use_slot: dict({"id": name}, **({"props": props} if props else {}))}
        dur = _required_duration(src, host)
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
    p.add_argument("--props", help="a JSON file: the shot's props, or the object's own props "
                                    "(or the host's full props with the object already placed in them)")
    p.add_argument("--host", default="ObjectStage")
    p.add_argument("--frame", type=int)
    p.add_argument("--aspect")
    p.add_argument("--slot", help="which of the host's top-level object slots to use, when it has more than one")
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
            # M8 (task-2-fix-1.md): new-shot used to print the OBJECT guide too.
            doc = "object-authoring.md" if a.cmd == "new-object" else "remotion-shot-authoring.md"
            print("NEXT: draw it (references/%s), then python3 scripts/workshop.py %s still %s"
                  % (doc, a.out_dir, a.name))
            return 0
        if a.props:
            # M5 (task-2-fix-1.md): a missing or unreadable --props file is a sentence, not a raw traceback —
            # OSError/ValueError are not WorkshopError, so they used to escape the except clause below.
            try:
                props = json.loads(_read(a.props))
            except OSError as e:
                raise WorkshopError(["--props %s: %s" % (a.props, e.strerror or str(e))]) from None
            except ValueError as e:
                raise WorkshopError(["--props %s: not valid JSON (%s)" % (a.props, e)]) from None
        else:
            props = None
        png = still(a.out_dir, a.name, props, host=a.host, frame=a.frame, aspect=a.aspect, slot=a.slot)
        print("[workshop] %s" % png)
        print("NEXT: open it and LOOK — does it carry its build-list entry's `means` with the caption hidden?")
        return 0
    except WorkshopError as e:
        for x in e.problems:
            print("  PROBLEM: " + x)
        return 1


if __name__ == "__main__":
    sys.exit(main())
