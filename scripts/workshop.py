#!/usr/bin/env python3
"""A FILM'S WORKSHOP — the objects and shots one film builds for itself — and the only door into the bundle.

    python3 scripts/workshop.py <out_dir> list                       # what it holds, which beats use it
    python3 scripts/workshop.py <out_dir> new-object <Name> --means "<what the viewer must see>"
    python3 scripts/workshop.py <out_dir> new-shot <Name> --means "<the argument no register carries>"
    python3 scripts/workshop.py <out_dir> check                      # type-check, imports, content contract, words
    python3 scripts/workshop.py <out_dir> still <Name> [--props p.json] [--host ObjectStage] [--frame N]
    python3 scripts/workshop.py <out_dir> new-component <Name> --means "<what the viewer must see>"   # HTML tier
    python3 scripts/workshop.py <out_dir> still <Component> [--attrs a.json] [--p 0.9] [--aspect 16:9|9:16]

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
    <out_dir>/workshop/html/<Name>.js|.css  an HTML-tier COMPONENT (a custom element) — see "HTML-TIER COMPONENTS"

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
# What every object is given for free (runtime/objectSlot.tsx SLOT_KEYS) — a beat's own `props` for an object
# may never set one of these, since the slot overrules it silently rather than drawing what the film asked for.
SLOT_KEYS = ("w", "h", "t", "dna", "yaw", "idle")
# A problem sentence ending in this phrase is something this RUN could not measure (the toolchain is missing),
# never a finding about the film's code — a caller sorts on it to report a skip rather than an error.
NOTHING_CHECKED = "nothing was checked"


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
    # glob.glob reads `[...]`/`*`/`?` IN A PATH ARGUMENT as wildcards, not literal characters — a film folder
    # named "film [v2]" or "film*" would have its own shots misread or a sibling's pulled in. os.listdir takes
    # `folder` as a literal path, so the folder's own name can never be read as a pattern.
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


# Tolerates a missing trailing semicolon (ASI) and a trailing `satisfies ObjectMeta` / `as const` (in either
# order) after the object literal — all valid TypeScript a strict `\s*;` alone would miss.
_META = re.compile(r"export const META\b[^=]*=\s*\{(.*?)\}\s*(?:(?:as\s+const|satisfies\s+\w+)\s*)*;?", re.S)


def object_meta(src):
    """An object's META as {aspect, turns, demo, provenance} (only the keys it sets), or None if it has none.
    `aspect` is None when it is DECLARED but unparseable, non-finite or not positive (`1.2.3`, `16 / 0`) — never
    raises; `names_problems`/`check` report a None aspect as a problem instead."""
    m = _META.search(_strip_comments(src or ""))   # every declaration is read from comment-stripped source
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


# ONE anchored parser for DURATION, shared by _problems(), durations() and still() (its host too): an
# unanchored `=\s*(\d+)` would misread `= 6 * 30;` as 6 (the settled frame then judged mid-entry), `= 150.5;`
# as 150, let `= 0;` through to a registry-load crash, refuse a valid `: number = 150;` as "no DURATION", and
# let a commented-out `// export const DURATION = …;` win over a real one below it. On comment-stripped
# source; anything but `export const DURATION = <positive whole number>;` (an optional `: number` type
# annotation allowed) comes back None.
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
    (durations()) or AttributeError (`.group(1)` on no match) reaching a caller directly."""
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
    m = _GROUND.search(_strip_comments(src or ""))   # comment-stripped, like every other declaration
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
    m = _PROVENANCE.search(_strip_comments(src or ""))   # comment-stripped, like every other declaration
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


# `id="…"` can sit on a LATER line of the same `<Composition …>`/`<Still …>` element, so the scan is bounded
# by the NEXT `<` (the start of a sibling element) rather than by `>` — a `=> (...)` arrow inside the same tag
# (e.g. `calculateMetadata`) contains a literal `>` and would end the scan too early.
_COMPOSITION_ID = re.compile(r'<(?:Composition|Still)\b[^<]*?\bid="([A-Za-z0-9_]+)"')
_F_ROW_ID = re.compile(r"\bF\(\s*'([A-Za-z0-9_]+)'")   # spans line breaks: \s* matches \n too


def _root_composition_ids():
    """Every composition id remotion/src/Root.tsx registers directly: `Film` and `StageProbe` as
    `<Composition id="…">` attributes, `TypeSpecimen`, `FontProbe` and the other `*Probe` ids as
    `{F('<Id>', …)}` rows. Read from Root.tsx itself, not a hard-coded list, so a future composition Root.tsx
    adds is covered automatically — but most of what this returns is ALSO a file in src/shots/ or
    src/objects/, which library_shot_names()/library_object_names() already see and report with their own,
    more specific message; a caller that wants only the names those two miss subtracts them itself
    (`_root_composition_ids() - library_shot_names() - library_object_names()` — a name in both would
    otherwise get two problem messages for the one clash). Raises if the result does not contain "Film" —
    Root.tsx's own format changing in a way this parser no longer understands must be loud, not a silently
    incomplete set that under-refuses forever."""
    src = _strip_comments(_read(ROOT_TSX))
    ids = set(_COMPOSITION_ID.findall(src)) | set(_F_ROW_ID.findall(src))
    if "Film" not in ids:
        raise RuntimeError("Root.tsx's own composition ids no longer include \"Film\" — "
                           "_root_composition_ids()'s parser (scripts/workshop.py) needs updating for "
                           "whatever changed there")
    return ids


_SLOT_KEY = re.compile(r"\b([A-Za-z_]\w*)\s*\??\s*:\s*ObjectRef\b")
# A `const|let|var <Name>: ObjectRef = …` is a stage register's own standalone-preview constant, not a prop a
# beat can set — masked out before slot_keys() ever sees it, rather than excluded by name afterwards (the same
# name could ALSO be a real prop elsewhere).
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
    render still refuses a malformed ref either way). A register can reuse a field name for a plain caption at
    one level and type it ObjectRef at a nested one (`object` on a caption prop vs. inside a device's
    `ScreenSrc`) — slot_keys() can't tell those apart by name alone, so for THOSE names only a dict-shaped
    value counts as a found ref; a name the source types ObjectRef and nothing else
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


def object_refs(src, props, host_name=None):
    """[(path, value)] for every object reference in a beat's props: each value under a key the register types
    ObjectRef, at any depth (a device's `steps[0].screen.object`, a compare's `left.object`). A key the source
    types ObjectRef and NOTHING else hands back every non-None value under it, well-formed or not — validate.py's
    build check is the one that reports a malformed one (a plain string where a ref belongs), so it must still
    see it here; a key the source ALSO types otherwise elsewhere is ambiguous, and only a dict-shaped value
    under it counts (a register's top-level `object` can be a caption, with a differently-typed `object` field
    nested inside some other type in the same file).

    `host_name`, when given, names `src`'s own exported component. A key `_top_level_object_ref_keys` finds
    typed ObjectRef at brace depth 1 of THAT declaration is a real slot, proven by the declaration itself — so
    at the TOP LEVEL of `props`, every non-None value under such a key is reported regardless of the ambiguity
    heuristic above. A register commonly RENAMES its own top-level prop while destructuring it (`object:
    OBJECT`), which reads, by name alone, exactly like the same field typed a second time and made every value
    under it ambiguous: HudReticle's `object: OBJECT` hid a malformed `"object": "a caption"` from validate.py's
    build check this way, the one `art` already gets. A NESTED occurrence of the same name keeps the ambiguity
    rule either way — a caption `object` at the top level beside a differently-typed `object` nested in some
    other type must still exclude the top-level one."""
    keys, ambiguous, found = slot_keys(src), _ambiguous_slot_keys(src), []
    top = set(_top_level_object_ref_keys(src, host_name)) if host_name else set()

    def walk(v, path):
        if isinstance(v, dict):
            for k, x in v.items():
                p = "%s.%s" % (path, k) if path else str(k)
                if k in keys and x is not None and (
                        (not path and k in top) or isinstance(x, dict) or k not in ambiguous):
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
    of THAT (and only that) type literal — the ones still() can place an object under without knowing the
    host's nested shape (a device's `steps[i].screen.object` is depth 2, and does NOT count).

    Anchored on `export const <host_name>`, never the first `React.FC<{` in the file: a register can declare a
    helper component before its own export (DeviceDemo.tsx's own `DemoPage`, before `export const DeviceDemo`,
    is one) — scanning the first occurrence in the file would read the helper's props literal instead of the
    host's own. Matched by counting braces, not angle brackets: the literal's own body holds arrow functions
    (`=>`), which a naive `<...>` scan would misread as closing the generic early. [] when there is no such
    export, or it does not declare its props as an inline object literal."""
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
    """The props a register says a FILM must set (its standalone preview fills them otherwise). Comment-stripped
    like every other declaration reader — a commented-out `// export const REQUIRED_IN_FILM = [...]` must not
    count as a live requirement."""
    m = _REQUIRED.search(_strip_comments(src or ""))
    return set(re.findall(r"['\"](\w+)['\"]", m.group(1))) if m else set()


def uses(slides, out_dir, refs=None):
    """{shot or object id: [beat numbers]} — a shot by the beats cast on it, an object by the beats whose props
    name it. A beat number is the board's own `index` (its position when a slide has none). `refs`, when given,
    is object_refs(shot_source(out_dir, shot), shot_props) already computed per beat, BY LIST POSITION — a
    caller that needs those same refs for its own per-beat checks (validate.py's _check_build) passes them here
    instead of having this recompute them a second time."""
    out = {}
    for pos, s in enumerate(slides or [], 1):
        num = s.get("index", pos)
        shot = s.get("shot")
        if isinstance(shot, str) and shot:
            out.setdefault(shot, []).append(num)
        beat_refs = (refs[pos - 1] if refs is not None else
                     object_refs(shot_source(out_dir, shot), s.get("shot_props") or {}, shot))
        for _path, ref in beat_refs:
            if isinstance(ref, dict) and isinstance(ref.get("id"), str):
                lst = out.setdefault(ref["id"], [])
                if num not in lst:
                    lst.append(num)
    return out


def _clash_with(name, lib_s, lib_o, comp_ids):
    """None, or why `name` cannot be a workshop item's name because the LIBRARY already has it — a shot
    register, an object, or a composition id Root.tsx registers directly. `lib_s`/`lib_o` are
    library_shot_names()/library_object_names(); `comp_ids` is `_root_composition_ids() - lib_s - lib_o`, so a
    name already caught by one of the first two gets that more specific reason, not also this one (a name can
    be both a library shot file and a Root.tsx composition id at once). The core check `_problems()` (an
    existing file) and `scaffold()` (refuses BEFORE writing one) share — see `_library_or_composition_clash()`
    below for the single-name convenience wrapper `scaffold()` actually calls."""
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
        if entry in KINDS or entry in ("assets", HTML_KIND) or entry in GENERATED or entry.startswith("."):
            continue
        out.append(("workshop/%s: a workshop holds objects/, shots/, assets/ and html/ only" % entry, False))
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
            if os.path.isdir(os.path.join(folder, f)):
                # A HELPER SUBFOLDER IS ALLOWED (source_files: "a helper module may sit in its own subfolder" — it
                # is hashed, import-checked and contract-checked like any helper). This refused every folder, so a
                # film whose shots shared drawing code (the GPS film's satellite parts) had to turn it into an
                # object instead. What is still refused is a folder holding anything but code.
                stray = [os.path.relpath(os.path.join(dp, x), folder) for dp, dn, fn in os.walk(os.path.join(folder, f))
                         for x in fn if not x.startswith(".") and not x.endswith((".ts", ".tsx"))]
                for x in stray:
                    out.append(("workshop/%s/%s: a helper folder holds .ts/.tsx code only (pictures go in assets/)"
                                % (kind, x), False))
                continue
            if not f.endswith((".tsx", ".ts")):
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
            # every declaration check below reads comment-stripped source — EXCEPT the scaffold marker just
            # below, which IS a comment (`// @scaffold …`) and must stay on the raw one.
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
                elif "bgGrad" in (g if isinstance(g, list) else [g]):
                    # A gradient has no single luminance — under every shipped Design DNA preset, 'bgGrad' is a
                    # CSS gradient string, so shot_proof.py's caption-band check (and the render's own caption
                    # ink) can never resolve a claim for it. Syntactically a GROUND token, semantically unusable.
                    out.append(("%s: GROUND %r names bgGrad, a gradient with no single luminance under any "
                                "Design DNA — declare the solid token(s) the caption band actually shows, or a "
                                "'#hex'" % (where, g), False))
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
        # `open(<workshop>/index.ts, "w")` below needs the workshop/ folder to already exist — a raw
        # FileNotFoundError otherwise. A film's own callers only reach here through prepare(), guarded by
        # has_items(), so this matters for write_index()/typecheck() called directly (both public).
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


def env_kwargs(env):
    """`subprocess.run(..., **env_kwargs(env))` — {} leaves a call exactly as it was before workshops. The
    one definition every film-scoped caller shares, so a caller holding an environment it already computed
    (cjk_type_qa's one sweep-long `_RUN_ENV`, remotion_segments' per-segment `env`) does not restate the
    same `{"env": x} if x is not None else {}` ternary."""
    return {"env": env} if env is not None else {}


def run_kwargs(out_dir):
    """`subprocess.run(..., **run_kwargs(out_dir))` — {} leaves a call exactly as it was before workshops."""
    return env_kwargs(prepare(out_dir))


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


def beat_files(out_dir, shot, props):
    """The workshop files ONE beat is built from — its shot when the workshop owns it, every object its props
    reference (object_refs), and everything those files reach by relative import, transitively. The per-beat
    segment cache key hashes exactly these, so editing one built object re-renders only the beats that use it
    (it used to hash the WHOLE workshop into every key: one edit, every beat re-rendered).

    Conservative where a reference is not a prop or an import: a workshop item whose NAME appears as a word in a
    file already reached (an object that mounts another by id) is pulled in too — an over-wide key costs a
    re-render, an under-wide one ships a stale beat."""
    if not out_dir:
        return []
    ws = workshop_dir(out_dir)
    if not os.path.isdir(ws):
        return []
    roots = [os.path.join(ws, d) for d in KINDS + ("assets",)]
    items = {}
    for kind in KINDS:
        for n in _tsx_names(os.path.join(ws, kind)):
            items.setdefault(n, os.path.join(ws, kind, n + ".tsx"))
    todo = []
    if isinstance(shot, str) and shot_source_path(out_dir, shot) == os.path.join(ws, "shots", shot + ".tsx"):
        todo.append(os.path.join(ws, "shots", shot + ".tsx"))
    for _path, ref in object_refs(shot_source(out_dir, shot) if isinstance(shot, str) else None,
                                  props or {}, shot if isinstance(shot, str) else None):
        rid = ref.get("id") if isinstance(ref, dict) else None
        f = os.path.join(ws, "objects", "%s.tsx" % rid) if _safe(rid) else None
        if f and os.path.isfile(f):
            todo.append(f)
    seen = set()
    while todo:
        f = os.path.abspath(todo.pop())
        if f in seen or not os.path.isfile(f):
            continue
        seen.add(f)
        if not f.endswith((".ts", ".tsx", ".js", ".jsx")):
            continue
        text = _strip_comments(_read(f))
        for spec in _IMPORT.findall(text):
            if not spec.startswith("."):
                continue
            base = os.path.normpath(os.path.join(os.path.dirname(f), spec))
            hit = next((base + e for e in ("", ".ts", ".tsx", ".js", ".json", "/index.ts", "/index.tsx")
                        if os.path.isfile(base + e)), None)
            if hit and any((hit + os.sep).startswith(r + os.sep) or hit.startswith(r + os.sep) for r in roots):
                todo.append(hit)
        for n, p in items.items():
            if p not in seen and re.search(r"\b%s\b" % re.escape(n), text):
                todo.append(p)
    return sorted(seen)


def source_files(out_dir):
    """The workshop's code: every .ts and .tsx under objects/ and shots/, at any depth — a helper module may sit
    in its own subfolder. The SAME traversal code_files() uses, so a helper is hashed for the render cache AND
    import/contract/baked-words checked, never just the former. os.walk, not glob.glob, so a folder name with
    `[...]`/`*`/`?` in it is never misread as a wildcard."""
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
    (what code_files() hashes for the render cache key — a file at the workshop root is never reached by a
    render, so editing it would not change the key). Nothing else resolves."""
    pkg = json.loads(_read(os.path.join(REMOTION, "package.json")))
    deps = set(pkg.get("dependencies") or {}) | set(pkg.get("devDependencies") or {})
    ws, lib, probs = workshop_dir(out_dir), library_shot_names(), []
    roots = [os.path.join(ws, d) for d in KINDS + ("assets",)]
    for f in files:
        # workshop_dir() is always absolute; a RELATIVE `f` would make every `target` below relative too, so
        # it could never match the `ws`/roots prefix check and a legitimate "./helper" import would be
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
            elif spec.startswith("@objects/"):
                if spec[len("@objects/"):] not in library_object_names():
                    probs.append("%s imports %s — there is no library object %r" % (rel, spec, spec[9:]))
            elif spec.startswith("."):
                target = os.path.normpath(os.path.join(os.path.dirname(f), spec))
                if not (target + os.sep).startswith(ws + os.sep):
                    probs.append("%s imports %s, outside the film's workshop — film code may use react, remotion, "
                                 "@runtime/…, @shots/… and its own workshop files" % (rel, spec))
                elif not any((target + os.sep).startswith(root + os.sep) for root in roots):
                    # inside the workshop, but not inside objects/, shots/ or assets/ (e.g. the workshop root
                    # itself, or its generated index.ts/_stills/) — code_files() never hashes it.
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
            # content_contract_qa._declared only accepts the TAG in cq._DECL[rule] (cycle->cycles,
            # position/relabel->positional, retype/fallback->fallback, invent->decor, truncate->truncates) —
            # printing `rule` itself would tell an author to write a declaration the checker does not
            # recognise, so the violation would never go away.
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
                             "missing — %s" % NOTHING_CHECKED], "declared": []}
    r = subprocess.run([node, os.path.join(_HERE, "jsx_words.cjs"), tsmod] + code, capture_output=True, text=True)
    if r.returncode != 0:
        return {"problems": ["the baked-words scan failed: %s — %s" % ((r.stderr or r.stdout).strip()[-300:] or
                                                                       "(no output)", NOTHING_CHECKED)], "declared": []}
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
        return ["the type-check could not run: %s is missing (npm install in remotion/) — %s" % (tsc, NOTHING_CHECKED)]
    ws = workshop_dir(out_dir)
    write_index(out_dir)
    cfg = {"extends": os.path.join(REMOTION, "tsconfig.json"),
           "compilerOptions": {
               "noEmit": True,
               "typeRoots": [os.path.join(REMOTION, "node_modules", "@types")],
               "paths": {"@workshop": [os.path.join(ws, "index.ts")],
                         "@runtime/*": [os.path.join(RUNTIME, "*")],
                         "@shots/*": [os.path.join(LIB_SHOTS, "*")],
                         "@objects/*": [os.path.join(LIB_OBJECTS, "*")],
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
    if has_components(out_dir):
        probs += html_problems(out_dir)
    return probs



# ── HTML-TIER COMPONENTS ───────────────────────────────────────────────────────────────────────────────────
#
# The page tier's workshop (docs/superpowers/specs/2026-10-05-html-workshop-design.md). A COMPONENT is a custom
# HTML element — `<espresso-puck packed="1">` — written as one plain JS file plus one CSS file:
#     <out_dir>/workshop/html/<Name>.js    customElements.define('<tag>', class extends HTMLElement {...}) ONCE
#     <out_dir>/workshop/html/<Name>.css   every selector scoped to <tag>, every @keyframes named <tag>-…
# A promoted one lives at assets/html/components/<Name>.js|.css. Pages link both files, the script BEFORE
# seek.js, so the parser-created elements are upgraded (and build their parts) before seek.js freezes every
# animation it finds. Nothing below runs for a film without workshop/html/ and without a custom tag in a page.
HTML_KIND = "html"
ASSETS_HTML = os.path.join(SKILL, "assets", "html")
LIB_COMPONENTS = os.path.join(ASSETS_HTML, "components")
# names the HTML spec reserves (all hyphenated, all SVG/MathML elements) — never a custom element
_RESERVED_TAGS = {"annotation-xml", "color-profile", "font-face", "font-face-src", "font-face-uri",
                  "font-face-format", "font-face-name", "missing-glyph"}
# A 16:9 page's content column (base.css .stage: 1920×1080, padding 120px 150px) and a 9:16 one (vertical.css
# .stage: 1080×1920, padding 150px 80px 300px), each stopped at the burned caption band's top — the box a
# component must fit without overflowing. {aspect: (canvas W, canvas H, column W, column H)}.
def _columns():
    from _caption_band import caption_band_px
    return {"16:9": (1920, 1080, 1920 - 2 * 150, 1080 - 120 - max(120, caption_band_px(1920, 1080))),
            "9:16": (1080, 1920, 1080 - 2 * 80, 1920 - 150 - max(300, caption_band_px(1080, 1920)))}


# Every JS construct a component may not use, and why — matched on comment-stripped source.
_JS_FORBIDDEN = (
    (r"\battachShadow\b", "attachShadow — a component is light DOM only: seek.js, the glide census and "
                          "keyframe_qa's geometry walk the light DOM and cannot see into a shadow root"),
    (r"\bDate\b", "Date — the wall clock; a component is a pure function of its attributes"),
    (r"\bperformance\s*\.\s*now\b", "performance.now — the wall clock"),
    (r"\bsetTimeout\b", "setTimeout — a timer; every animation is CSS keyframes, which seek.js freezes"),
    (r"\bsetInterval\b", "setInterval — a timer; every animation is CSS keyframes, which seek.js freezes"),
    (r"\brequestAnimationFrame\b", "requestAnimationFrame — scripted animation; seek.js cannot freeze it"),
    (r"\bMath\s*\.\s*random\b", "Math.random — every capture must draw the same frame; seed any "
                                "pseudo-randomness from an attribute"),
    (r"\bfetch\s*\(", "fetch — the network; a component draws from its attributes only"),
    (r"\bXMLHttpRequest\b", "XMLHttpRequest — the network; a component draws from its attributes only"),
    (r"\bimport\s*\(", "import() — a dynamic import loads late and over the network"),
    (r"^\s*(?:import|export)\b", "a module statement — the file is a classic script, linked before seek.js"),
    (r"\.\s*animate\s*\(", "el.animate (the Web Animations API) — every animation is CSS keyframes, so "
                           "seek.js can freeze it"),
)


def component_tag(name):
    """The custom element's tag: the kebab form of the PascalCase name (`EspressoPuck` → `espresso-puck`)."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name or "").lower()


def _component_name_problem(name):
    """None, or why `name` cannot name a component (the tag it gives must be a valid custom element name)."""
    if not NAME.match(name or ""):
        return "a name is PascalCase, 3-32 letters and digits"
    tag = component_tag(name)
    if "-" not in tag:
        return ("its tag %r has no hyphen — a custom element's name needs one, so a component's name is two "
                "words or more (EspressoPuck → espresso-puck)" % tag)
    if tag in _RESERVED_TAGS:
        return "its tag %r is a name the HTML spec reserves" % tag
    return None


def _js_names(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f[:-3] for f in os.listdir(folder) if f.endswith(".js") and not f.startswith("."))


def component_names(out_dir):
    """The components this film's workshop holds (workshop/html/<Name>.js)."""
    return set(_js_names(os.path.join(workshop_dir(out_dir), HTML_KIND))) if out_dir else set()


def library_component_names():
    return set(_js_names(LIB_COMPONENTS))


def has_components(out_dir):
    return bool(out_dir) and os.path.isdir(os.path.join(workshop_dir(out_dir), HTML_KIND))


def component_paths(out_dir, name):
    """(js, css) of the film's own component `name`."""
    d = os.path.join(workshop_dir(out_dir), HTML_KIND)
    return os.path.join(d, name + ".js"), os.path.join(d, name + ".css")


def known_components(out_dir):
    """{tag: (Name, js, css, label)} for every component a page of this film may use — its own first, then the
    library's. `label` is how a finding names the file."""
    out = {}
    for n in sorted(library_component_names()):
        out[component_tag(n)] = (n, os.path.join(LIB_COMPONENTS, n + ".js"), os.path.join(LIB_COMPONENTS, n + ".css"),
                                 "assets/html/components/%s" % n)
    for n in sorted(component_names(out_dir)):
        js, css = component_paths(out_dir, n)
        out[component_tag(n)] = (n, js, css, "workshop/html/%s" % n)
    return out


def _strip_js_comments(src):
    """JS source with its comments removed and its string/template literals kept — so `'a // b'` never hides
    the rest of its line, and a `/* … */` never hides code."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "'\"`":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            out.append(" ")
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _css_blocks(css):
    """[(prelude, body, parent at-rule or None)] for every rule in `css` (comments removed): a @media/@supports/
    @container/@layer is descended into; a @keyframes is returned whole."""
    css = re.sub(r"/\*.*?\*/", " ", css or "", flags=re.S)
    out = []

    def walk(s, parent):
        i, n = 0, len(s)
        while i < n:
            j = s.find("{", i)
            if j < 0:
                break
            pre = s[i:j].split(";")[-1].strip()
            depth, k = 1, j + 1
            while k < n and depth:
                depth += {"{": 1, "}": -1}.get(s[k], 0)
                k += 1
            body = s[j + 1:k - 1]
            if re.match(r"@(?:media|supports|container|layer)\b", pre):
                walk(body, pre)
            else:
                out.append((pre, body, parent))
            i = k
    walk(css, None)
    return out


def _split_selectors(pre):
    parts, depth, cur = [], 0, ""
    for ch in pre:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def component_lint(name, js, css, label):
    """The component contract that reading the two files can judge, as sentences ([] when clean)."""
    probs = []
    why = _component_name_problem(name)
    if why:
        return ["%s.js: %s" % (label, why)]
    tag = component_tag(name)
    if not os.path.isfile(css):
        probs.append("%s.css is missing — a component is one JS file plus one CSS file (its parts' look and "
                     "every animation, as CSS keyframes)" % label)
    raw = _read(js)
    src = _strip_js_comments(raw)
    defs = re.findall(r"customElements\s*\.\s*define\s*\(", src)
    lit = re.findall(r"customElements\s*\.\s*define\s*\(\s*(['\"`])([^'\"`]*)\1", src)
    if len(defs) != 1:
        probs.append("%s.js calls customElements.define %d times — exactly once, for <%s>" % (label, len(defs), tag))
    if lit and lit[0][1] != tag:
        probs.append("%s.js defines <%s> — the tag is the kebab form of its name: <%s>" % (label, lit[0][1], tag))
    elif defs and not lit:
        probs.append("%s.js: customElements.define's first argument must be the literal '%s'" % (label, tag))
    if not re.search(r"\bextends\s+HTMLElement\b", src):
        probs.append("%s.js: the class extends HTMLElement (an autonomous custom element)" % label)
    if not re.search(r"\bstatic\s+demo\s*=\s*\{", src):
        probs.append("%s.js: declare `static demo = {attr: value, ...}` — neutral demo attributes (never film "
                     "copy) that `check` renders it with" % label)
    for pat, why in _JS_FORBIDDEN:
        m = re.search(pat, src, re.M)
        if m:
            line = src.count("\n", 0, m.start()) + 1
            probs.append("%s.js:%d uses %s" % (label, line, why))
    if SCAFFOLD_MARK in raw:
        probs.append("%s.js: still the scaffold — draw the real component, then delete the `%s` line"
                     % (label, SCAFFOLD_MARK))
    if os.path.isfile(css):
        text = _read(css)
        if re.search(r"@import\b", text):
            probs.append("%s.css uses @import — a component is its two files, nothing else" % label)
        if re.search(r"url\(\s*['\"]?\s*(?:https?:)?//", text):
            probs.append("%s.css loads a remote url() — the network; pages render offline" % label)
        for pre, _body, _parent in _css_blocks(text):
            if not pre.startswith("@"):
                # the container-type:size SELF-PADDING trap: a query-container's OWN padding (not gap —
                # proven fine) sized in cq units, under base.css's global `*{box-sizing:border-box}`, makes
                # Chrome mis-resolve cq units for every DESCENDANT to near-zero (reproduced: a basket sized
                # 42cqmin/52cqh collapsed to ~2x1px once its espresso-puck parent carried
                # `padding-top:18cqh` — moving that spacing to the child's own margin fixed it outright).
                # `check`'s own harness never catches this: it places the component as a lone flex-centered
                # child, a context the bug does not reproduce in, so a component can read CLEAN here and
                # still render BLANK on the real page the moment it sits inside a grid/row wrapper.
                for sel in _split_selectors(pre):
                    if sel == tag and re.search(r"container-type\s*:\s*[^;]*\bsize\b", _body) and \
                            re.search(r"\bpadding(?:-(?:top|right|bottom|left))?\s*:\s*[^;]*\dcq(?:w|h|i|b|min|max)\b",
                                      _body):
                        probs.append(
                            "%s.css: <%s> sets container-type:size AND its own padding in a cq unit — Chrome "
                            "collapses every descendant's cq-sized box to ~0 under base.css's border-box "
                            "reset; move that spacing onto a CHILD's margin instead (gap is fine, only the "
                            "container's own padding breaks)" % (label, tag))
            if pre.startswith("@"):
                km = re.match(r"@(?:-webkit-)?keyframes\s+([\w-]+)", pre)
                pm = re.match(r"@property\s+(--[\w-]+)", pre)
                if km:
                    if not km.group(1).startswith(tag + "-"):
                        probs.append("%s.css: @keyframes %s — name it %s-… (keyframe names are global: an unprefixed "
                                     "one can replace base.css's own `rise`/`fade` on every page)"
                                     % (label, km.group(1), tag))
                elif pm:
                    if not pm.group(1).startswith("--%s-" % tag):
                        probs.append("%s.css: @property %s — name it --%s-… (registered properties are global)"
                                     % (label, pm.group(1), tag))
                elif not re.match(r"@font-face\b", pre):
                    probs.append("%s.css: %s — a component's CSS holds rules, @keyframes, @media/@supports and "
                                 "@property only" % (label, pre.split()[0]))
                continue
            for sel in _split_selectors(pre):
                if not re.match(r"%s(?![\w-])" % re.escape(tag), sel):
                    probs.append("%s.css: selector %r is not scoped to <%s> — every rule starts with `%s` so the "
                                 "component never restyles the page around it" % (label, sel[:60], tag, tag))
    return probs


# ── runtime: the component rendered on its own, in a harness page ─────────────────────────────────────────

_HARNESS = """<!doctype html><html lang="%(lang)s"><head><meta charset="utf-8">
%(links)s
<script>window.__cmpErrs=[];window.addEventListener('error',function(e){window.__cmpErrs.push(String(e.message||e));});</script>
</head><body>
<div class="stage" id="__host"></div>
<script src="%(js)s"></script>
<script>(function(){try{
  var C=customElements.get(%(tag_js)s);
  if(!C){window.__cmpErrs.push('the script defines no <'+%(tag_js)s+'>');return;}
  var attrs=%(attrs)s||C.demo;
  if(!attrs||typeof attrs!=='object'||!Object.keys(attrs).length){window.__cmpErrs.push('static demo is missing or empty');return;}
  window.__cmpDemo=C.demo||null;
  var el=document.createElement(%(tag_js)s);el.id='__cmp';
  Object.keys(attrs).forEach(function(k){el.setAttribute(k,String(attrs[k]));});
  el.style.width='%(bw)dpx';el.style.height='%(bh)dpx';el.style.flex='none';el.style.alignSelf='center';
  document.getElementById('__host').appendChild(el);
}catch(e){window.__cmpErrs.push(String(e&&e.message||e));}})();</script>
<script src="%(seek)s"></script>
</body></html>"""

# Everything the checks read off the harness at its CURRENT frozen state, in one evaluation.
_PROBE_JS = r"""(function(){
  var el=document.getElementById('__cmp');
  var out={errs:(window.__cmpErrs||[]).slice(),demo:window.__cmpDemo||null,built:!!el};
  if(!el) return JSON.stringify(out);
  var cs0=getComputedStyle(el), r0=el.getBoundingClientRect();
  out.display=cs0.display; out.box=[r0.width,r0.height];
  out.attrs=[]; for(var i=0;i<el.attributes.length;i++){var a=el.attributes[i];
    if(!/^(class|style|id|data-cue|data-cue-index|data-cue-offset)$/.test(a.name)) out.attrs.push(a.value);}
  function vis(e){for(var x=e;x&&x!==document.body;x=x.parentElement){var c=getComputedStyle(x);
    if(c.display==='none'||c.visibility==='hidden'||parseFloat(c.opacity)<0.05)return false;}return true;}
  function desc(e){var c=(typeof e.className==='string'?e.className:(e.getAttribute('class')||''));
    return e.tagName.toLowerCase()+(c?'.'+c.trim().split(/\s+/).join('.'):'');}
  out.text=[];
  var w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT,null),nd;
  out.boxes=[];out.over=[];out.unfrozen=[];
  while((nd=w.nextNode())){var s=(nd.nodeValue||'').trim();if(!s)continue;
    if(vis(nd.parentElement))out.text.push(s);
    var rg=document.createRange();rg.selectNodeContents(nd);var tr=rg.getBoundingClientRect();
    if(tr.width>0&&tr.height>0){var to=Math.max(r0.left-tr.left,r0.top-tr.top,tr.right-r0.right,tr.bottom-r0.bottom);
      if(to>1)out.over.push(['the text "'+s.slice(0,24)+'"',Math.round(to),'outside the component\'s box']);}}
  var all=[el].concat([].slice.call(el.querySelectorAll('*')));
  all.forEach(function(e){
    ['::before','::after'].forEach(function(ps){var c=getComputedStyle(e,ps).content;
      if(c&&c!=='none'&&c!=='normal'&&vis(e)){var m=c.match(/^"(.*)"$/);out.text.push(m?m[1]:c);}});
    var r=e.getBoundingClientRect();
    out.boxes.push([desc(e),r.left,r.top,r.width,r.height]);
    if(e!==el&&(r.width>0||r.height>0)){
      var o=Math.max(r0.left-r.left,r0.top-r.top,r.right-r0.right,r.bottom-r0.bottom);
      if(o>1)out.over.push([desc(e),Math.round(o),'outside the component\'s box']);}
    var cs=getComputedStyle(e);
    // a glyph standing proud of a tight line box (line-height:1) is scroll overflow too, and invisible; a
    // wrapped extra line is a whole line height. Below .35em of the largest type inside it, it is the former.
    var big=parseFloat(cs.fontSize)||16;e.querySelectorAll('*').forEach(function(d){
      big=Math.max(big,parseFloat(getComputedStyle(d).fontSize)||0);});
    var tol=Math.max(1,0.35*big);
    if(e.clientWidth>0&&e.scrollWidth-e.clientWidth>tol)out.over.push([desc(e),e.scrollWidth-e.clientWidth,'wider than its own box']);
    if(e.clientHeight>0&&e.scrollHeight-e.clientHeight>tol)out.over.push([desc(e),e.scrollHeight-e.clientHeight,'taller than its own box']);
    if(cs.animationName&&cs.animationName!=='none'&&cs.animationPlayState!=='paused')out.unfrozen.push(desc(e));
  });
  // the display it has OUTSIDE a flex/grid parent (which blockifies an inline element): a fresh copy in a block
  try{var ph=document.createElement('div');ph.style.cssText='position:absolute;left:-99999px;top:0;display:block;width:400px;height:300px';
    document.body.appendChild(ph);var cp=document.createElement(el.tagName.toLowerCase());ph.appendChild(cp);
    out.display=getComputedStyle(cp).display;ph.remove();}catch(e){}
  return JSON.stringify(out);
})()"""


def _url(path):
    from urllib.parse import quote
    return "file://" + quote(os.path.abspath(path))


def _harness(path, name, js, css, aspect, reduced=False, attrs=None, theme=None, lang="en"):
    """Write the harness page for `name` at `path`: the page tier's own stylesheets (base, the film's theme,
    motifs, vertical at 9:16, reduced-motion when asked) plus the component's, the element built from `attrs`
    (else its static demo) in the aspect's content column, then seek.js — the order a real page uses."""
    W, H, bw, bh = _columns()[aspect]
    css_files = [os.path.join(ASSETS_HTML, "base.css")] + ([theme] if theme and os.path.isfile(theme) else []) + \
        [os.path.join(ASSETS_HTML, "motifs.css")] + ([os.path.join(ASSETS_HTML, "vertical.css")] if aspect == "9:16" else []) + \
        ([css] if os.path.isfile(css) else []) + ([os.path.join(ASSETS_HTML, "reduced-motion.css")] if reduced else [])
    links = "\n".join('<link rel="stylesheet" href="%s">' % _url(c) for c in css_files)
    tag = component_tag(name)
    html = _HARNESS % {"lang": lang, "links": links, "js": _url(js), "tag_js": json.dumps(tag),
                       "attrs": json.dumps(attrs) if attrs else "null", "bw": bw, "bh": bh,
                       "seek": _url(os.path.join(ASSETS_HTML, "seek.js"))}
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path


def _probe(chrome, url, scratch):
    chrome.shot(url, scratch)                                # navigate + wait for load and fonts
    r = chrome._cmd("Runtime.evaluate", {"expression": _PROBE_JS, "returnByValue": True}, chrome.sid)
    return json.loads(r["result"]["result"]["value"])


_CJK_RUN = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿]+")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def _tokens(text):
    """(words casefolded, numbers, CJK runs) in `text`."""
    cjk = _CJK_RUN.findall(text)
    rest = _CJK_RUN.sub(" ", text)
    nums = _NUMBER.findall(rest)
    words = [w.casefold() for w in re.findall(r"[^\W\d_]+", _NUMBER.sub(" ", rest))]
    return words, nums, cjk


def unsourced_words(texts, attrs):
    """Every visible word, number or CJK run in `texts` that none of the attribute values `attrs` supplies: a
    word must be a word of some value, a number one of the values' numbers, a CJK run part of some value."""
    a_words, a_nums = set(), set()
    for v in attrs:
        w, n, _c = _tokens(v)
        a_words |= set(w)
        a_nums |= set(n)
    bad = []
    for t in texts:
        w, n, c = _tokens(t)
        bad += [x for x in w if x not in a_words]
        bad += [x for x in n if x not in a_nums]
        bad += [x for x in c if not any(x in v for v in attrs)]
    return list(dict.fromkeys(bad))


def _chrome(W, H):
    import _cdp
    import scenes
    binary = scenes._chrome_bin({})
    if not binary:
        raise WorkshopError(["no Chrome for the component checks — %s" % NOTHING_CHECKED])
    try:
        return _cdp.Chrome(binary, W, H)
    except Exception as e:                                    # noqa: BLE001 — reported as a skip, never raised raw
        raise WorkshopError(["Chrome could not start for the component checks (%s) — %s" % (e, NOTHING_CHECKED)])


def component_runtime(name, js, css, label, scratch_dir, theme=None, lang="en", chromes=None):
    """{"problems": [...], "demo": {...} or None} — the component rendered on its own with its demo attributes:
    words only from attributes, no overflow in a 16:9 or a 9:16 content column, every animation frozen by
    seek.js, and under reduced-motion.css no part's box moving. `chromes` ({aspect: Chrome}) lets a caller
    checking several components share two browsers."""
    os.makedirs(scratch_dir, exist_ok=True)
    own = chromes is None
    chromes = {} if own else chromes
    probs, demo = [], None
    shot = os.path.join(scratch_dir, "_probe.jpg")
    try:
        def at(aspect, ps, reduced=False):
            if aspect not in chromes:
                W, H, _bw, _bh = _columns()[aspect]
                chromes[aspect] = _chrome(W, H)
            page = _harness(os.path.join(scratch_dir, "%s.%s%s.harness.html" % (name, aspect.replace(":", "x"),
                                                                                  ".rm" if reduced else "")),
                            name, js, css, aspect, reduced=reduced, theme=theme, lang=lang)
            return [_probe(chromes[aspect], _url(page) + "?p=%s" % p, shot) for p in ps]

        mid, end = at("16:9", (0.5, 1.0))
        demo = end.get("demo")
        errs = list(dict.fromkeys(end.get("errs") or []))
        if errs or not end.get("built"):
            return {"problems": ["%s.js: rendering it threw — %s" % (label, "; ".join(errs[:3]) or "nothing was built")],
                    "demo": demo}
        if end.get("display") in ("inline", "contents", "none"):
            probs.append("%s.css: <%s> is display:%s — give it display:block (or flex/grid) so it fills the box "
                         "its page gives it" % (label, component_tag(name), end["display"]))
        W, H, bw, bh = _columns()["16:9"]
        bx = end.get("box") or [0, 0]
        if abs(bx[0] - bw) > 1 or abs(bx[1] - bh) > 1:
            probs.append("%s: given a %d×%d box it is %d×%d — the element fills the box its page gives it (never "
                         "sets its own width/height)" % (label, bw, bh, round(bx[0]), round(bx[1])))
        if end.get("unfrozen"):
            probs.append("%s.js: %s animate(s) but seek.js did not freeze them — build every part when the element "
                         "is connected (connectedCallback), never later" % (label, ", ".join(end["unfrozen"][:3])))
        bad = unsourced_words((mid.get("text") or []) + (end.get("text") or []), end.get("attrs") or [])
        if bad:
            probs.append("%s: draws %s, which none of its attributes supplies — every word on screen comes from an "
                         "attribute (a number only when it IS an attribute value); the code writes these itself"
                         % (label, ", ".join(repr(b) for b in bad[:6])))
        for aspect, info in (("16:9", end), ("9:16", at("9:16", (1.0,))[0])):
            over = info.get("over") or []
            if over:
                w = max(over, key=lambda o: o[1])
                probs.append("%s overflows at %s (a %d×%d column): %s is %dpx %s%s" % (
                    label, aspect, _columns()[aspect][2], _columns()[aspect][3], w[0], w[1], w[2],
                    " (+%d more)" % (len(over) - 1) if len(over) > 1 else ""))
        rm = at("16:9", (0.0, 0.5, 1.0), reduced=True)
        moved = None
        base = rm[0].get("boxes") or []
        for later in rm[1:]:
            boxes = later.get("boxes") or []
            if len(boxes) != len(base):
                moved = ("its parts change in number", 0)
                break
            for a, b in zip(base, boxes):
                # the baseline unlock (a skewY of 1/1024 while text moves, `none` at rest) tilts a box by
                # width/1024 — a box that only gains that much height has not moved
                skew = max(a[3], b[3]) / 1024.0
                d = max(abs(a[1] - b[1]), abs(a[3] - b[3]),
                        max(abs(a[2] - b[2]), abs(a[4] - b[4])) - skew)
                if d > 0.5:
                    moved = (a[0], d)
                    break
            if moved:
                break
        if moved:
            probs.append("%s moves under reduced motion: %s shifts %.1fpx between p=0 and p=1 with reduced-motion.css "
                         "linked — multiply every movement by var(--motion, 1) (reduced-motion.css sets --motion:0) "
                         "so only opacity changes" % (label, moved[0], moved[1]))
    finally:
        if own:
            for c in chromes.values():
                c.close()
    return {"problems": probs, "demo": demo}


# ── pages: which components they use, and whether they link them right ───────────────────────────────────

_CUSTOM_TAG = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*(?:-[a-zA-Z0-9]*)+)(?=[\s/>])")


def _markup(html):
    """A page's markup with its comments and its <script>/<style> CONTENTS removed (their tags kept)."""
    html = re.sub(r"<!--.*?-->", "", html or "", flags=re.S)
    return re.sub(r"(<(script|style)\b[^>]*>).*?(</\2\s*>)", r"\1\3", html, flags=re.S | re.I)


def page_custom_tags(html):
    """Every custom element tag a page's markup uses, lower-cased, in first-use order."""
    return list(dict.fromkeys(t.lower() for t in _CUSTOM_TAG.findall(_markup(html))
                              if t.lower() not in _RESERVED_TAGS))


def _resolve(ref, page_path):
    """The local file a page's src/href names, or None for a remote/data URL."""
    from urllib.parse import unquote, urlsplit
    ref = (ref or "").strip()
    if ref.startswith("file://"):
        return os.path.realpath(unquote(urlsplit(ref).path))
    if re.match(r"^[a-zA-Z][\w+.-]*:", ref) or ref.startswith("//"):
        return None
    return os.path.realpath(os.path.join(os.path.dirname(page_path), unquote(ref.split("?")[0].split("#")[0])))


def film_pages(out_dir):
    """Every page of the film, relative to out_dir: the board's html scenes, then any other pages/*.html."""
    rels = []
    for s in _board(out_dir).get("slides") or []:
        p = (s.get("props") or {}).get("html") if isinstance(s, dict) and isinstance(s.get("props"), dict) else None
        if isinstance(p, str) and p and p not in rels:
            rels.append(p)
    pd = os.path.join(out_dir, "pages")
    if os.path.isdir(pd):
        rels += [r for r in ("pages/" + f for f in sorted(os.listdir(pd)) if f.endswith(".html")) if r not in rels]
    return rels


def page_component_problems(out_dir, page_rel, known=None, only=None):
    """What is wrong with how one page uses components: a custom tag nothing defines, or a component whose
    script is missing, deferred or linked after seek.js, or whose stylesheet is missing. `only` (a set of tags)
    limits the findings to those components."""
    known = known_components(out_dir) if known is None else known
    path = os.path.join(out_dir, page_rel)
    try:
        html = _read(path)
    except OSError:
        return []
    tags = [t for t in page_custom_tags(html) if only is None or t in only]
    if not tags:
        return []
    scripts = [(m.start(), m.group(1)) for m in re.finditer(r"<script\b([^>]*)>", html, re.I)]
    srcs = [(pos, attrs, _resolve((re.search(r"""\bsrc\s*=\s*["']([^"']+)["']""", attrs) or [None, ""])[1], path))
            for pos, attrs in scripts]
    seek = next((pos for pos, _a, p in srcs if p and os.path.basename(p) == "seek.js"), None)
    hrefs = {_resolve(h, path) for h in re.findall(r"""<link\b[^>]*\bhref\s*=\s*["']([^"']+)["']""", html, re.I)}
    probs = []
    for tag in tags:
        if tag not in known:
            probs.append("%s uses <%s>, which neither this film's workshop/html/ nor assets/html/components/ "
                         "defines — build it (python3 scripts/workshop.py <out_dir> new-component <Name> --means "
                         "\"...\") or fix the tag" % (page_rel, tag))
            continue
        name, js, css, label = known[tag]
        mine = [(pos, attrs) for pos, attrs, p in srcs if p and p == os.path.realpath(js)]
        if not mine:
            probs.append("%s uses <%s> but does not link its script %s.js — link it before seek.js"
                         % (page_rel, tag, label))
        else:
            pos, attrs = mine[0]
            if re.search(r"\b(?:defer|async)\b|type\s*=\s*[\"']?module", attrs, re.I):
                probs.append("%s links %s.js deferred/async/as a module — it must run before seek.js, so link it "
                             "as a plain <script src=…>" % (page_rel, label))
            if seek is None:
                probs.append("%s uses <%s> but links no seek.js — the capture cannot freeze it" % (page_rel, tag))
            elif pos > seek:
                probs.append("%s links %s.js AFTER seek.js — seek.js freezes only the animations that exist when it "
                             "runs; link the component's script before it" % (page_rel, label))
        if os.path.realpath(css) not in hrefs:
            probs.append("%s uses <%s> but does not link its stylesheet %s.css" % (page_rel, tag, label))
    return probs


def html_layout_problems(out_dir):
    """[(sentence, blocking)] for workshop/html/: only <Name>.js + <Name>.css pairs, valid names, no clash."""
    d = os.path.join(workshop_dir(out_dir), HTML_KIND)
    if not os.path.isdir(d):
        return []
    out = []
    names = component_names(out_dir)
    lib = library_component_names()
    remotion = shot_names(out_dir) | object_names(out_dir)
    for f in sorted(os.listdir(d)):
        if f.startswith("."):
            continue
        base, ext = os.path.splitext(f)
        if os.path.isdir(os.path.join(d, f)) or ext not in (".js", ".css"):
            out.append(("workshop/html/%s: only <Name>.js and <Name>.css belong here" % f, False))
        elif ext == ".css" and base not in names:
            out.append(("workshop/html/%s has no %s.js beside it" % (f, base), False))
    for n in sorted(names):
        why = _component_name_problem(n)
        if why:
            out.append(("workshop/html/%s.js: %s" % (n, why), True))
        if n in lib:
            out.append(("workshop/html/%s.js: %s is already a library component (assets/html/components/) — "
                        "rename it" % (n, n), True))
        if n in remotion:
            out.append(("workshop/html/%s.js: %s is also a shot or object in this workshop — one name, one thing"
                        % (n, n), True))
    return out


def html_problems(out_dir, names=None, runtime=True):
    """Every component problem in this film, as sentences: workshop/html/'s layout, each component's lint and
    runtime checks, and every page's use of components. `names` limits it to those components (and the pages'
    use of their tags). [] for a film with no workshop/html/ and no custom tag in any page."""
    probs = [p for p, _b in html_layout_problems(out_dir)
             if names is None or any("/%s." % n in p for n in names)]
    comps = sorted(component_names(out_dir) if names is None else set(names) & component_names(out_dir))
    if comps:
        theme = os.path.join(out_dir, "theme.css")
        lang = str((_board(out_dir).get("meta") or {}).get("language") or "en")
        scratch = os.path.join(workshop_dir(out_dir), "_stills")
        chromes = {}
        try:
            for n in comps:
                js, css = component_paths(out_dir, n)
                label = "workshop/html/%s" % n
                probs += component_lint(n, js, css, label)
                if runtime and not _component_name_problem(n):
                    try:
                        probs += component_runtime(n, js, css, label, scratch, theme=theme, lang=lang,
                                                   chromes=chromes)["problems"]
                    except WorkshopError as e:
                        probs += e.problems
                        runtime = False                       # no browser: say so once, not once per component
        finally:
            for c in chromes.values():
                c.close()
    known = known_components(out_dir)
    only = None if names is None else {component_tag(n) for n in names}
    for rel in film_pages(out_dir):
        probs += page_component_problems(out_dir, rel, known, only)
    return probs


COMPONENT_JS_SCAFFOLD = """// COMPONENT · %(name)s <%(tag)s> — %(means)s
// A film-local HTML component (scripts/workshop.py; references/html-pages.md "Building a component"). It ENCODES
// its beat: hide the caption and it still carries the idea. Light DOM only; built ONCE from its attributes when it
// is connected; every animation is CSS keyframes in %(name)s.css; no Date, timers, Math.random or network; every
// word and number it draws is one of its attribute values. Pages link this script BEFORE seek.js.
// @scaffold — replace this body with the real drawing, then delete this line.
customElements.define('%(tag)s', class extends HTMLElement {
  // neutral demo attributes `workshop.py check` renders it with — never film copy
  static demo = {label: 'Demo label', value: '3'};

  connectedCallback() {
    if (this._built) return;            // build ONCE: a re-attach must not duplicate the parts
    this._built = true;
    const part = (cls, text) => {
      const e = document.createElement('div');
      e.className = '%(tag)s__' + cls;
      if (text != null) e.textContent = text;
      this.appendChild(e);
      return e;
    };
    part('value', this.getAttribute('value') || '');
    part('label', this.getAttribute('label') || '');
  }
});
"""

COMPONENT_CSS_SCAFFOLD = """/* %(name)s — sized by its box (container units: cqw/cqh/cqmin), animated by CSS keyframes only. Every rule starts
   with %(tag)s and every @keyframes is named %(tag)s-…. Multiply every movement by var(--motion, 1):
   reduced-motion.css sets --motion:0, so under it every part rests at its end state and only opacity changes.
   Moving text carries the baseline unlock matrix(1,.0009765625,0,1,0,0) while it moves. */
%(tag)s{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2cqmin;
  container-type:size;position:relative;color:var(--fg)}
%(tag)s .%(tag)s__value{font:700 18cqmin/1 var(--font-display,system-ui,sans-serif);
  font-variant-numeric:lining-nums tabular-nums;color:var(--accent);opacity:0;
  transform:translateY(calc(4cqmin * var(--motion, 1))) matrix(1,.0009765625,0,1,0,0);
  animation:%(tag)s-rise .8s cubic-bezier(.2,.7,.2,1) .2s forwards;animation-play-state:paused}
%(tag)s .%(tag)s__label{font:600 6cqmin/1.2 var(--font-body,system-ui,sans-serif);color:var(--muted);opacity:0;
  animation:%(tag)s-fade .6s ease-out .5s forwards;animation-play-state:paused}
@keyframes %(tag)s-rise{99.9%%{opacity:1;transform:translateY(0) matrix(1,.0009765625,0,1,0,0)}to{opacity:1;transform:none}}
@keyframes %(tag)s-fade{to{opacity:1}}
"""


def scaffold_component(out_dir, name, means):
    """Write workshop/html/<Name>.js + .css with the contract's skeleton and return the JS path."""
    probs = []
    why = _component_name_problem(name)
    if why:
        probs.append("%r: %s" % (name, why))
    elif name in library_component_names():
        probs.append("%s is already a library component (assets/html/components/)" % name)
    elif name in component_names(out_dir) | shot_names(out_dir) | object_names(out_dir):
        probs.append("%s is already in this film's workshop" % name)
    if not str(means or "").strip():
        probs.append("--means: say what the viewer must see — it heads the file and the build-list entry")
    if probs:
        raise WorkshopError(probs)
    js, css = component_paths(out_dir, name)
    os.makedirs(os.path.dirname(js), exist_ok=True)
    fill = {"name": name, "tag": component_tag(name), "means": " ".join(str(means).split())}
    with open(js, "w", encoding="utf-8") as fh:
        fh.write(COMPONENT_JS_SCAFFOLD % fill)
    with open(css, "w", encoding="utf-8") as fh:
        fh.write(COMPONENT_CSS_SCAFFOLD % fill)
    return js


def component_still(name, js, css, out_png, attrs=None, p=0.9, aspect="16:9", theme=None, lang="en"):
    """Render `name` in its aspect's content column, frozen at progress `p`, to the PNG `out_png`."""
    if aspect not in _columns():
        raise WorkshopError(["--aspect is 16:9 or 9:16 (got %r)" % (aspect,)])
    W, H, _bw, _bh = _columns()[aspect]
    outd = os.path.dirname(os.path.abspath(out_png))
    os.makedirs(outd, exist_ok=True)
    page = _harness(os.path.join(outd, "%s.still.harness.html" % name), name, js, css, aspect, attrs=attrs,
                    theme=theme, lang=lang)
    chrome = _chrome(W, H)
    try:
        info = _probe(chrome, _url(page) + "?p=%s" % float(p), os.path.join(outd, "_probe.jpg"))
        if info.get("errs") or not info.get("built"):
            raise WorkshopError(["the still of %s failed: %s" % (name, "; ".join(info.get("errs") or [])
                                                                 or "nothing was built")])
        import base64
        data = chrome._cmd("Page.captureScreenshot", {"format": "png"}, chrome.sid)["result"]["data"]
        with open(out_png, "wb") as fh:
            fh.write(base64.b64decode(data))
    finally:
        chrome.close()
    return out_png


def still_component(out_dir, name, attrs=None, p=0.9, aspect=None):
    """`still` for a component: workshop/_stills/<Name>.png (<Name>.9x16.png at 9:16)."""
    board = _board(out_dir)
    aspect = aspect or (board.get("meta") or {}).get("aspect") or "16:9"
    if name in component_names(out_dir):
        js, css = component_paths(out_dir, name)
    elif name in library_component_names():
        js, css = os.path.join(LIB_COMPONENTS, name + ".js"), os.path.join(LIB_COMPONENTS, name + ".css")
    else:
        raise WorkshopError(["%s is not a component in this film's workshop or the library" % name])
    png = os.path.join(workshop_dir(out_dir), "_stills", name + (".9x16" if aspect == "9:16" else "") + ".png")
    return component_still(name, js, css, png, attrs=attrs, p=p, aspect=aspect,
                           theme=os.path.join(out_dir, "theme.css"),
                           lang=str((board.get("meta") or {}).get("language") or "en"))


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
// (import {X} from '@shots/X'). Each word that enters on its own takes its window through `cue.win('<prop path>',
// a, b, reach)` (runtime/cue.ts): the render then starts it early enough to read when the voice says it — the one
// thing the beat's time warp cannot do when the narration names things in a different order from the frame.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '@runtime/motion';
import {CONTENT_TOP, contentBottom} from '@runtime/layout';
import {useDNA} from '@runtime/dna';
import {useCues, REACH_CUBIC} from '@runtime/cue';

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
  const cue = useCues();
  const {width: W, height: H} = useVideoConfig();
  const on = easeOutCubic(clamp01(seg(t, ...cue.win('title', 0.05, 0.3, REACH_CUBIC))));
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
        clash = _library_or_composition_clash(name)   # the SAME check _problems() refuses an existing item with
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


def direction_dna(arg):
    """`--dna` → the look a still renders in: a preset name, a DNA object file, or `<directions.json>#<key>` — one
    direction of the contest file `contest_sample.py --conceived` reads. A hero judged in the stock fallback
    palette is not the hero the contest will show."""
    if not arg:
        return None
    path, _, key = str(arg).partition("#")
    if not os.path.exists(path):
        if key or os.sep in path or path.endswith(".json"):
            raise WorkshopError(["--dna %s: no such file" % path])
        return path                                     # a preset name; the Film resolves it or says it cannot
    try:
        data = json.loads(_read(path))
    except ValueError as e:
        raise WorkshopError(["--dna %s: not valid JSON (%s)" % (path, e)]) from None
    if isinstance(data, dict) and not key:
        return data.get("dna") if isinstance(data.get("dna"), (dict, str)) else data
    dirs = [d for d in (data if isinstance(data, list) else []) if isinstance(d, dict)]
    keys = [str(d.get("key")) for d in dirs]
    if not key and len(dirs) == 1:
        key = keys[0]
    pick = [d for d in dirs if str(d.get("key")) == key]
    if not pick:
        raise WorkshopError(["--dna %s: name a direction as %s#<key> — its keys: %s"
                             % (arg, path, ", ".join(keys) or "(none; expected a list of directions)")])
    if not isinstance(pick[0].get("dna"), (dict, str)):
        raise WorkshopError(["--dna %s: direction %r has no `dna`" % (arg, key)])
    return pick[0]["dna"]


def _board(out_dir):
    try:
        return json.loads(_read(os.path.join(out_dir, "storyboard.json")))
    except (OSError, ValueError):
        return {}


# The registers whose screen is a step of a script prepared from the narration (scripts/device_script.py): their
# own render refuses a script nobody prepared, so an object on their screen is previewed through a beat.
DEVICE_HOSTS = ("DeviceDemo", "DeviceHero")


def _prepared_device_beat(slide, out_dir, src, host):
    """A device beat's props as the film plays them: cues resolved, the step script prepared. A beat that has no
    duration yet (before tts) is laid out on the host's own length, its cues placed by the narration's text."""
    import render_remotion as rr
    try:
        if slide.get("duration"):
            return rr.film_shot_props(slide, out_dir)
        secs = _required_duration(src, host) / 30.0
        narration = slide.get("narration") or ""
        p = rr.resolve_cue_props(dict(slide.get("shot_props") or {}), out_dir, None, narration, secs, 30)
        return rr._prepared_device_props(slide, p, out_dir, secs, 30)
    except SystemExit as e:                       # a refusal the film itself would print, kept as a sentence
        raise WorkshopError([str(e)]) from None


def _device_still_props(board, out_dir, name, host, src, props):
    """An object on a device's screen, previewed from the beat that shows it — with `props`, the beat whose own
    shot_props are exactly those; without, the first beat that shows `name` on `host`. Props no beat carries are
    prepared on the host's own length, where a cue has no narration to land on and is refused by name."""
    for s in board.get("slides") or []:
        if s.get("shot") != host:
            continue
        sp = s.get("shot_props") or {}
        if props is not None and sp != props:
            continue
        if any(isinstance(ref, dict) and ref.get("id") == name for _p, ref in object_refs(src, sp, host)):
            return _prepared_device_beat(s, out_dir, src, host)
    if props is None:
        raise WorkshopError(["no beat shows %s on %s, whose screen is a step of its script — pass --props with the "
                             "host's full props (a script whose screen step holds {\"object\": {\"id\": \"%s\"}})"
                             % (name, host, name)])
    return _prepared_device_beat({"shot": host, "narration": "", "shot_props": props}, out_dir, src, host)


def still(out_dir, name, props=None, host="ObjectStage", frame=None, aspect=None, slot=None, dna=None):
    """Render `name`'s settled frame on its own into <workshop>/_stills/<name>.png and return that path — a shot
    as its own composition (props: the given ones, else its first beat's), an object on `host`.

    An object's `props`, when given, is tried FIRST as the host's own full props with the object already
    placed somewhere in them (object_refs() finds a ref to `name`) — how a device screen is previewed; used
    as given, unchanged. Otherwise it is the object's OWN sub-props, and the object goes under `slot` (a
    top-level ObjectRef slot of the host) if given, else the host's single one; refused
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
        dur = _required_duration(shot_source(out_dir, name), name)   # a sentence, never a raw KeyError
    elif name in object_names(out_dir) or name in library_object_names():
        comp = host
        src = shot_source(out_dir, host)
        if src is None:
            raise WorkshopError(["%s is not a register with a slot this film can use" % host])
        placed = any(isinstance(ref, dict) and ref.get("id") == name for _p, ref in object_refs(src, props or {}))
        if host in DEVICE_HOSTS and (props is None or placed):
            payload = _device_still_props(board, out_dir, name, host, src, props)
        elif placed:
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
    # `dna` (a contest direction's look, resolved by `direction_dna`) wins over the board's: before a direction is
    # chosen the board has none, and the still fell back to a stock dark ground the film would never have.
    dna = dna or meta.get("design_dna") or meta.get("shot_template")
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
    for n in sorted(component_names(out_dir)):
        rows.append(("component", n))
        tag = component_tag(n)
        pages = [r for r in film_pages(out_dir) if tag in page_custom_tags(_read_or_empty(os.path.join(out_dir, r)))]
        print("  %-9s %-24s pages %-24s %s" % ("component", n, ", ".join(pages) or "-",
                                                "on the build list" if n in listed else "NOT on the build list"))
    if not rows:
        print("  (empty) — python3 scripts/workshop.py %s new-object <Name> --means \"...\"" % out_dir)
    return 0


def _read_or_empty(path):
    try:
        return _read(path)
    except OSError:
        return ""


def main(argv=None):
    ap = argparse.ArgumentParser(description="A film's workshop: the objects and shots it builds for itself.")
    ap.add_argument("out_dir")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("check")
    for k in ("new-object", "new-shot", "new-component"):
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
    p.add_argument("--attrs", help="a component's attributes, as a JSON object file (default: its static demo)")
    p.add_argument("--p", type=float, default=0.9, help="a component's progress to freeze at, 0..1 (default 0.9)")
    p.add_argument("--dna", help="the look to render in, before the board has one: a preset name, a DNA JSON file, "
                                  "or <directions.json>#<key> (a contest direction)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "list":
            return _list(a.out_dir)
        if a.cmd == "check":
            probs = check(a.out_dir)
            for x in probs:
                print("  PROBLEM: " + x)
            print("[workshop] %s — %d problem(s)" % ("CLEAN" if not probs else "NOT CLEAN", len(probs)))
            _b = _board(a.out_dir)
            _rend = str((_b.get("meta") or {}).get("renderer") or "")
            # the contest is the REMOTION tier's; an html film (or a board that says so) goes on to validate
            if not probs and not _rend.startswith(("local", "html")) and not component_names(a.out_dir) and \
                    not any(isinstance(sl, dict) and (sl.get("shot") or sl.get("type") == "html")
                            for sl in _b.get("slides") or []):
                # the contest stage: directions are being designed, and no beat has a shot for validate to read yet
                # (a board made from the content plan exists by then — the compound test followed this line into
                # "slide 1: remotion tier requires a `shot`")
                print("NEXT: python3 scripts/contest_sample.py --route \"<topic>\" --out %s --conceived "
                      "<directions.json> --render" % a.out_dir)
            elif not probs:
                print("NEXT: python3 scripts/validate.py %s" % a.out_dir)
            return 1 if probs else 0
        if a.cmd == "new-component":
            path = scaffold_component(a.out_dir, a.name, a.means)
            print("[workshop] wrote %s and its .css" % path)
            print("NEXT: add its meta.build_list entry (kind \"component\", slot \"page\"), draw it "
                  "(references/html-pages.md \"Building a component\"), then python3 scripts/workshop.py %s still %s"
                  % (a.out_dir, a.name))
            return 0
        if a.cmd == "still" and (a.name in component_names(a.out_dir) or
                                 (a.name in library_component_names() and a.name not in object_names(a.out_dir)
                                  and a.name not in library_object_names())):
            attrs = None
            if a.attrs:
                try:
                    attrs = json.loads(_read(a.attrs))
                except OSError as e:
                    raise WorkshopError(["--attrs %s: %s" % (a.attrs, e.strerror or str(e))]) from None
                except ValueError as e:
                    raise WorkshopError(["--attrs %s: not valid JSON (%s)" % (a.attrs, e)]) from None
                if not isinstance(attrs, dict) or not attrs:
                    raise WorkshopError(["--attrs %s: a JSON object of attribute: value" % a.attrs])
            if not 0.0 <= a.p <= 1.0:
                raise WorkshopError(["--p is a progress between 0 and 1 (got %s)" % a.p])
            png = still_component(a.out_dir, a.name, attrs=attrs, p=a.p, aspect=a.aspect)
            print("[workshop] %s" % png)
            print("NEXT: open it and LOOK — does it carry its build-list entry's `means` with the caption hidden?")
            return 0
        if a.cmd in ("new-object", "new-shot"):
            path = scaffold(a.out_dir, a.cmd[4:], a.name, a.means)
            print("[workshop] wrote %s" % path)
            # new-shot and new-object each point at their own authoring reference — a shot's structure and an
            # object's drawing are different guides.
            doc = "object-authoring.md" if a.cmd == "new-object" else "remotion-shot-authoring.md"
            print("NEXT: draw it (references/%s), then python3 scripts/workshop.py %s still %s"
                  % (doc, a.out_dir, a.name))
            return 0
        if a.props:
            # a missing or unreadable --props file is a sentence, not a raw traceback — OSError/ValueError are
            # not WorkshopError, so they would otherwise escape the except clause below.
            try:
                props = json.loads(_read(a.props))
            except OSError as e:
                raise WorkshopError(["--props %s: %s" % (a.props, e.strerror or str(e))]) from None
            except ValueError as e:
                raise WorkshopError(["--props %s: not valid JSON (%s)" % (a.props, e)]) from None
        else:
            props = None
        png = still(a.out_dir, a.name, props, host=a.host, frame=a.frame, aspect=a.aspect, slot=a.slot,
                    dna=direction_dna(a.dna))
        print("[workshop] %s" % png)
        print("NEXT: open it and LOOK — does it carry its build-list entry's `means` with the caption hidden?")
        return 0
    except WorkshopError as e:
        for x in e.problems:
            print("  PROBLEM: " + x)
        return 1


if __name__ == "__main__":
    sys.exit(main())
