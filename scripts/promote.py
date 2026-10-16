#!/usr/bin/env python3
"""PROMOTE a built thing from a delivered film into the library — the user's choice, never automatic.

    python3 scripts/promote.py <out_dir> <Name> --family <X> --use-when "<one line>" --motion "<one line>"   # a shot
    python3 scripts/promote.py <out_dir> <Name>                                                               # an object
    python3 scripts/promote.py <out_dir> <Name>                                                               # an HTML component
    python3 scripts/promote.py <out_dir> <Name> ... --dry-run                                                 # say what it would do

WHY. A film builds what it needs in its own workshop (scripts/workshop.py) and the library stays measured and
unpolluted. When a built thing turns out to be good — the USER says so at delivery — it moves into the library here
and pays what a library register pays: registration at every sync point (register_shot.py), measurement in the order
the device layer taught — ground reach, then both ground-luma emits and the spot-check merge that confirms them in
the committed table, then ground reach again, then energy and prop reach, then CJK type at every aspect (each emit
rewrites the register's own row, which the later measurements hash) — and a card written from its build-list entry
and its props' own comments. An object goes to remotion/src/objects/, into the library's object index and its catalogue section. The
film then uses the library's copy: its workshop copy is removed and its build-list entry marked `promoted`.

REFUSED, never guessed: a film that is not delivered (no out.mp4, or NOT_DELIVERED.md still there with neither a
critic pass nor a review waiver the USER gave for this render with every delivery gate green — that waived film is
promoted, and its library entry says it was never critic-reviewed); an item changed after that render; an item the workshop check fails; an item not on the build list;
a name the library already has; a shot without --family/--use-when/--motion; an import the library cannot resolve (a
workshop helper, an asset); a shot prop with no trailing comment (the card's table is written from them).
If a measurement fails, the register is left registered but not fully measured, and the message names the steps that
remain — `git status` lists every library file promote touched.

AN HTML COMPONENT (workshop/html/<Name>.js + .css) goes to assets/html/components/, gets an entry in
references/html-components.md (what it means, its attributes, a still), and the film's pages are pointed at the library
copy. The library copy is checked again (scripts/workshop.py's contract and runtime checks) before anything else
changes; refused, like the rest, on an undelivered film, a change after the render, a failing check (the component's
own or a page's use of it), a missing build-list entry, or a name the library already has.
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import workshop as ws  # noqa: E402

SKILL = os.path.dirname(_HERE)
REMOTION = os.path.join(SKILL, "remotion")
SHOTS = os.path.join(REMOTION, "src", "shots")
OBJECTS = os.path.join(REMOTION, "src", "objects")
CARDS = os.path.join(REMOTION, "cards")
LIBRARY = os.path.join(REMOTION, "LIBRARY.md")
OBJECTS_ANCHOR = "<!-- OBJECTS (scripts/promote.py appends below) -->"
KITS = os.path.join(REMOTION, "src", "kits")         # helper modules promoted items share (a film's workshop helpers)
HTML_COMPONENTS_DOC = os.path.join(SKILL, "references", "html-components.md")
HTML_COMPONENTS_HEAD = """# HTML components (the page tier's library)

Custom elements a film built in its own workshop (`scripts/workshop.py new-component`) and the user chose to keep
(`scripts/promote.py`). A page uses one by linking `assets/html/components/<Name>.css` and, BEFORE `seek.js`,
`assets/html/components/<Name>.js`, then writing the tag with its attributes. The contract every one of them meets is
in `references/html-pages.md` ("Building a component"). Every word a component draws comes from its attributes.
"""


class PromoteError(RuntimeError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _write(p, text):
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


def user_waived(out_dir):
    """The render id when the USER chose to ship this film without a critic (`meta.review` tier `none`, or the older
    review_waiver) and `critic_ledger.py --final` passes on it as it is now — the pin matches the current render and
    every delivery gate is recorded green for it. None otherwise."""
    import critic_ledger as cl
    wv, wprobs = cl.waiver(out_dir)
    if wv is None or wprobs:
        return None
    errs, _w = cl.validate(out_dir, final=True)
    return None if errs else cl.render_id(out_dir)


def delivery_problems(out_dir):
    """Why this film does not count as delivered for promotion ([] when it does). PROMOTION IS THE USER'S CHOICE
    (SKILL.md 9f), and so is `none` at the review question: a film the user watched and shipped without a critic used
    to be refused here because its NOT_DELIVERED.md is REWRITTEN rather than removed (a waiver is not a PASS), so the
    two user decisions contradicted each other on the GPS test film. It is accepted when that waiver holds for the
    current render and every delivery gate is recorded green — and the library entry then says it was never reviewed."""
    if not os.path.exists(os.path.join(out_dir, "NOT_DELIVERED.md")):
        return []
    if user_waived(out_dir):
        return []
    return ["NOT_DELIVERED.md is still there — the film is not delivered: no critic passed it, and no review waiver "
            "the user gave holds for this render with every delivery gate green (critic_ledger.py --final says which)"]


def _unreviewed_note(out_dir):
    rid = user_waived(out_dir) if os.path.exists(os.path.join(out_dir, "NOT_DELIVERED.md")) else None
    return (" · NOT critic-reviewed: the user waived the review of render %s" % rid[:12]) if rid else ""


def preconditions(out_dir, name):
    """(kind, source path, build-list entry, board) — or PromoteError naming EVERY reason it may not be promoted."""
    probs = []
    mp4 = os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(mp4):
        probs.append("the film has no out.mp4 — promote from a delivered film")
    probs += delivery_problems(out_dir)
    kind = "shot" if name in ws.shot_names(out_dir) else ("object" if name in ws.object_names(out_dir) else None)
    if kind is None:
        raise PromoteError(probs + ["%s is not in this film's workshop" % name])
    src = os.path.join(ws.workshop_dir(out_dir), kind + "s", name + ".tsx")
    if os.path.isfile(mp4) and os.path.getmtime(src) > os.path.getmtime(mp4):
        probs.append("%s changed after the film was rendered — re-render and re-review the film before promoting"
                     % os.path.relpath(src, out_dir))
    if name in ws.library_shot_names() or name in ws.library_object_names() or \
            os.path.exists(os.path.join(SHOTS, name + ".tsx")) or os.path.exists(os.path.join(OBJECTS, name + ".tsx")):
        probs.append("the library already has %s" % name)
    probs += [p for p in ws.check(out_dir) if ("/%s.tsx" % name) in p]
    board = json.loads(_read(os.path.join(out_dir, "storyboard.json")))
    entry = next((e for e in (board.get("meta") or {}).get("build_list") or []
                  if isinstance(e, dict) and e.get("id") == name), None)
    if entry is None:
        probs.append("%s is not on this film's meta.build_list — only a built thing with a stated purpose is promoted"
                     % name)
    if probs:
        raise PromoteError(probs)
    return kind, src, entry, board


def _resolve(base_dir, spec):
    p = os.path.normpath(os.path.join(base_dir, spec))
    for ext in ("", ".tsx", ".ts"):
        if os.path.isfile(p + ext):
            return p + ext
    return None


def _classify(out_dir, path):
    """('shot'|'object', Name) for a workshop ITEM (a top-level .tsx in shots/ or objects/), else ('helper', None)."""
    wsd = ws.workshop_dir(out_dir)
    for kind in ws.KINDS:
        folder = os.path.join(wsd, kind)
        if os.path.dirname(path) == folder and path.endswith(".tsx"):
            return kind[:-1], os.path.basename(path)[:-4]
    return "helper", None


def _aliases(text, kind):
    rel = {"shot": ("../runtime/", "./", "../objects/"), "object": ("../runtime/", "../shots/", "./"),
           "kit": ("../runtime/", "../shots/", "../objects/")}[kind]
    for alias, to in zip(("@runtime/", "@shots/", "@objects/"), rel):
        text = text.replace("'" + alias, "'" + to).replace('"' + alias, '"' + to)
    return text


def _relink(text, src_dir, out_dir, here, name, batch, kits, probs):
    """Rewrite one file's RELATIVE imports for its library home (`here`: 'shot' | 'object' | 'kit'). A promoted or
    library ITEM keeps a relative path into its own folder; a workshop HELPER is collected into `kits` and imported
    from src/kits/; anything else is refused by name."""
    lib_items = ws.library_shot_names() | ws.library_object_names()
    out = text
    for spec in sorted(set(ws._IMPORT.findall(text)), key=len, reverse=True):
        if not spec.startswith("."):
            continue
        target = _resolve(src_dir, spec)
        if target is None:
            probs.append("%s imports %r — nothing in the film's workshop answers it" % (name, spec))
            continue
        tkind, tname = _classify(out_dir, target)
        if tkind == "helper":
            stem = os.path.splitext(os.path.basename(target))[0]
            if kits.get(stem) not in (None, target):
                probs.append("%s: two different workshop helpers are both called %r — rename one" % (name, stem))
                continue
            kits[stem] = target
            new = ("./%s" if here == "kit" else "../kits/%s") % stem
        elif tname in batch or tname in lib_items:
            folder = "shots" if tkind == "shot" else "objects"
            new = ("./%s" % tname) if here == tkind else ("../%s/%s" % (folder, tname))
        else:
            probs.append("%s imports %r — a workshop %s that is not in this promotion and not in the library; promote "
                         "it in the same batch (promote.py <out_dir> --batch <spec.json>)" % (name, spec, tkind))
            continue
        out = out.replace("'%s'" % spec, "'%s'" % new).replace('"%s"' % spec, '"%s"' % new)
    return out


def library_source(text, kind, name, out_dir=None, src_dir=None, batch=frozenset(), kits=None):
    """The workshop source as library code: `@runtime/`, `@shots/` and `@objects/` become relative imports. A RELATIVE
    import names a workshop file: a promoted-in-this-batch or library ITEM keeps a relative path (the library's
    folders mirror the workshop's), a workshop HELPER goes to src/kits/ (`kits` collects it), and anything else is
    refused by name. On the GPS test film three shots shared `./orbitKit` and imported `../objects/GpsSatellite`, and
    each was refused one at a time. A shot's GROUND and PROVENANCE declarations (and the comment lines directly above
    them) are dropped: the library MEASURES the ground, and the provenance goes to shot_director."""
    probs = []
    for spec in ws._IMPORT.findall(text):
        if spec.startswith("@runtime/"):
            mod = spec[len("@runtime/"):]
            if not any(os.path.isfile(os.path.join(ws.RUNTIME, mod + e)) for e in ("", ".ts", ".tsx", ".json")):
                probs.append("%s imports %s — there is no runtime module %r" % (name, spec, mod))
        elif spec.startswith("@shots/"):
            if spec[len("@shots/"):] not in ws.library_shot_names() | set(batch):
                probs.append("%s imports %s — there is no library register %r" % (name, spec, spec[len("@shots/"):]))
        elif spec.startswith("@objects/"):
            if spec[len("@objects/"):] not in ws.library_object_names() | set(batch):
                probs.append("%s imports %s — there is no library object %r" % (name, spec, spec[len("@objects/"):]))
        elif spec.startswith(".") and (out_dir is None or src_dir is None):
            probs.append("%s imports %r — a workshop file or asset the library cannot resolve; inline it, or promote "
                         "it first" % (name, spec))
    out = text
    if out_dir is not None and src_dir is not None:
        out = _relink(out, src_dir, out_dir, kind, name, set(batch), kits if kits is not None else {}, probs)
    out = _aliases(out, kind)
    if kind == "shot":
        out = re.sub(r"(?:^[ \t]*//[^\n]*\n)*^export const (?:GROUND|PROVENANCE)\b[^\n]*\n", "", out, flags=re.M)
    return out, probs


def kit_sources(out_dir, kits, batch):
    """{library kit path: source} for every collected helper, its own imports relinked (and any helper IT imports
    collected in turn), plus the problems — a kit the library already holds with DIFFERENT code is refused."""
    done, out, probs = set(), {}, []
    while set(kits) - done:
        for stem in sorted(set(kits) - done):
            done.add(stem)
            src = kits[stem]
            text = _relink(_read(src), os.path.dirname(src), out_dir, "kit", stem, set(batch), kits, probs)
            text = _aliases(text, "kit")
            dest = os.path.join(KITS, stem + os.path.splitext(src)[1])
            if os.path.isfile(dest) and _read(dest) != text:
                probs.append("the library already has a kit %s with different code — rename the film's helper %r"
                             % (os.path.relpath(dest, REMOTION), stem))
            out[dest] = text
    return out, probs


def prop_docs(src, name):
    """({prop: type}, {prop: (what it sets, feel of turning it)}) from the trailing comment on each prop."""
    import demo_copy_qa as dq
    types = dq._declared_types(src, name) or {}
    docs = {}
    for ln in src.splitlines():
        m = re.match(r"\s*(\w+)\??\s*:[^/\n]*;\s*//\s*(.+?)\s*$", ln)
        if m and m.group(1) in types:
            what, _sep, feel = m.group(2).partition(" — ")
            docs[m.group(1)] = (what.strip(), feel.strip() or "—")
    return types, docs


def measurements(name):
    """The order a new register is measured in: every emit that rewrites its own row before what hashes it, and
    the one write path a spot measurement has into the COMMITTED ground-luma table — `record_spot` — sitting
    right after both emits print their classification and before anything hashes the row. `--only ... --emit`
    only classifies and prints; it never touches the committed table (a bare spot check overwriting the whole
    library's table once cost it a wholesale loss), so without this merge a promoted register would stay
    reported as a declaration nobody ever measured, forever.

    GROUND REACH IS MEASURED TWICE. The luma rows hash the follows-membership ground reach writes, so it runs
    first; but a register that reaches runtime/shotLuma.ts (through runtime/light, say) hashes its OWN rows there,
    which the two luma emits then rewrite from the placeholder to the measured ground — so it runs again once
    they have. Both tables' staleness checks close the run."""
    py = sys.executable
    reach = [py, "scripts/measure_ground_reach.py", "--only", name, "--emit"]
    return [list(reach),
            [py, "scripts/measure_ground_luma.py", "--only", name, "--luma", "--emit"],
            [py, "scripts/measure_ground_luma.py", "--only", name, "--emit"],
            [py, "-c", "import sys; sys.path.insert(0, 'scripts'); import measure_ground_luma as g; "
                       "g.record_spot(['%s'])" % name],
            list(reach),
            [py, "scripts/register_energy.py", "--only", name],
            [py, "scripts/prop_reach.py", "--only", name],
            [py, "scripts/cjk_type_qa.py", "--only", name, "--all-aspects"],
            [py, "scripts/measure_ground_reach.py", "--stale"],
            [py, "scripts/measure_ground_luma.py", "--stale"]]


def _register(name, family, use_when, provenance):
    import register_shot as rs
    rs.register(name, family, use_when=use_when, provenance=provenance)
    # register_shot's own command rewrites the catalogue's family census and its "(N design languages)"
    # headline after every registration; both are counted from the files on disk, so a promotion that
    # registers through the module and skips the refresh leaves the catalogue one register short.
    if not rs.refresh_family_census():
        raise PromoteError(["register_shot could not refresh LIBRARY.md's family census and headline count "
                            "after registering %s — the catalogue would report one register fewer than it holds"
                            % name])
    missing = rs.check(name)
    if missing:
        raise PromoteError(["register_shot left %s unregistered in %s" % (name, ", ".join(missing))])


def _run(cmd, log=print):
    import subprocess
    log("[promote] $ " + " ".join(cmd[1:]))
    r = subprocess.run(cmd, cwd=SKILL)
    if r.returncode != 0:
        raise PromoteError(["`%s` exited %d" % (" ".join(cmd[1:]), r.returncode)])


def _measured_line(name):
    row = (json.loads(_read(os.path.join(REMOTION, "register_energy.json"))).get("registers") or {}).get(name)
    if not row:
        raise PromoteError(["register_energy.json has no row for %s after its measurement" % name])
    return ("**Measured:** %.1f%% ink (clip median) · %.1f%% footprint · %s motion. Measured on the register's own "
            "defaults." % (row["ink_median"] * 100, row["footprint"] * 100, row["motion_p75"]))


def _card(name, entry, use_when, motion, types, docs, provenance, family, film):
    rows = "\n".join("| `%s` | %s | %s |" % (p, docs[p][0], docs[p][1]) for p in sorted(types))
    return ("# %s\n\n**Identity:** %s\n\n**Use when:** %s.\n\n**Motion core:** %s\n\n"
            "| Prop | What it sets | Feel of turning it |\n|---|---|---|\n%s\n\n"
            "**Known traps:**\n- Promoted from the film %s, where it was judged against: %s. The first film that meets "
            "a trap here writes it down.\n\n**Reference:** `remotion/src/shots/%s.tsx`\n\n"
            "**Provenance:** %s. **Family:** %s.\n"
            % (name, entry["means"], use_when.rstrip("."), motion, rows, film, entry["accept"], name, provenance, family))


def _index_object(name):
    p = os.path.join(OBJECTS, "index.ts")
    s = _read(p)
    imports = list(re.finditer(r"^import .*;$", s, re.M))
    at = imports[-1].end() if imports else 0
    s = s[:at] + "\nimport * as O_%s from './%s';" % (name, name) + s[at:]
    m = re.search(r"export const LIBRARY_OBJECTS[^=]*=\s*\{\n", s)
    if not m:
        raise PromoteError(["objects/index.ts has no LIBRARY_OBJECTS map to add %s to" % name])
    end = s.index("};", m.end())
    _write(p, s[:end] + "  %s: {C: O_%s.%s, meta: O_%s.META},\n" % (name, name, name, name) + s[end:])


def _catalogue_shot(name, entry, use_when, types, film, note=""):
    s = _read(LIBRARY)
    m = re.search(r"^(\d+)\. \*\*%s\*\* — .*$" % re.escape(name), s, re.M)
    if not m:
        raise PromoteError(["register_shot wrote no LIBRARY.md entry for %s" % name])
    # the note goes BEFORE "built for the film": validate reads the film's title from the end of this line
    line = "%s. **%s** — %s *Use: %s.* `%s`%s · built for the film %s." % (
        m.group(1), name, entry["means"], use_when.rstrip("."), ", ".join(sorted(types)), note, film)
    _write(LIBRARY, s[:m.start()] + line + s[m.end():])


def _catalogue_object(name, entry, props, film, note=""):
    s = _read(LIBRARY)
    if OBJECTS_ANCHOR not in s:
        raise PromoteError(["LIBRARY.md has no objects section (%s)" % OBJECTS_ANCHOR])
    line = "- **%s** — %s *Built for the film %s.*%s%s" % (
        name, entry["means"], film, (" `%s`" % ", ".join(sorted(props))) if props else "", note)
    _write(LIBRARY, s.rstrip("\n") + "\n" + line + "\n")


def _component_preconditions(out_dir, name):
    """(js, css, build-list entry, board) for promoting the film's component `name` — or PromoteError naming EVERY
    reason it may not be."""
    probs = []
    mp4 = os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(mp4):
        probs.append("the film has no out.mp4 — promote from a delivered film")
    probs += delivery_problems(out_dir)
    js, css = ws.component_paths(out_dir, name)
    if os.path.isfile(mp4):
        for f in (js, css):
            if os.path.isfile(f) and os.path.getmtime(f) > os.path.getmtime(mp4):
                probs.append("%s changed after the film was rendered — re-render and re-review the film before "
                             "promoting" % os.path.relpath(f, out_dir))
    if name in ws.library_component_names():
        probs.append("the library already has the component %s (assets/html/components/)" % name)
    probs += ws.html_problems(out_dir, names=[name])
    board = json.loads(_read(os.path.join(out_dir, "storyboard.json")))
    entry = next((e for e in (board.get("meta") or {}).get("build_list") or []
                  if isinstance(e, dict) and e.get("id") == name), None)
    if entry is None or entry.get("kind") != "component":
        probs.append("%s is not on this film's meta.build_list as a component — only a built thing with a stated "
                     "purpose is promoted" % name)
    if probs:
        raise PromoteError(probs)
    return js, css, entry, board


def _component_doc_entry(name, entry, demo, film):
    tag = ws.component_tag(name)
    attrs = ", ".join("`%s`" % k for k in (demo or {})) or "(none)"
    example = " ".join('%s="%s"' % (k, str(v).replace('"', "&quot;")) for k, v in (demo or {}).items())
    return ("\n## %s — `<%s>`\n\n**Means:** %s\n\n**Attributes:** %s. Demo: `<%s %s>`\n\n"
            "**Judged against:** %s *(built for the film %s)*\n\n"
            "**Files:** `assets/html/components/%s.js`, `assets/html/components/%s.css`\n\n"
            "![%s](../assets/html/components/%s.png)\n"
            % (name, tag, entry.get("means", ""), attrs, tag, example, entry.get("accept", ""), film,
               name, name, name, name))


def _repoint_pages(out_dir, name, js, css, lib_js, lib_css, log=print):
    """Rewrite every film page's link to the workshop copy of `name` (src= or href=, absolute or relative) to the
    library copy. Returns the pages changed."""
    targets = {os.path.realpath(js): lib_js, os.path.realpath(css): lib_css}
    changed = []
    for rel in ws.film_pages(out_dir):
        path = os.path.join(out_dir, rel)
        try:
            html = _read(path)
        except OSError:
            continue

        def sub(m):
            local = ws._resolve(m.group(3), path)
            if local in targets:
                return "%s%s%s%s" % (m.group(1), m.group(2), ws._url(targets[local]), m.group(2))
            return m.group(0)
        new = re.sub(r"""(\b(?:src|href)\s*=\s*)(["'])([^"']+)\2""", sub, html)
        if new != html:
            _write(path, new)
            changed.append(rel)
    return changed


def promote_component(out_dir, name, dry_run=False, log=print):
    js, css, entry, board = _component_preconditions(out_dir, name)
    film = (board.get("meta") or {}).get("title") or os.path.basename(os.path.abspath(out_dir))
    lib_js = os.path.join(ws.LIB_COMPONENTS, name + ".js")
    lib_css = os.path.join(ws.LIB_COMPONENTS, name + ".css")
    plan = {"kind": "component", "to": lib_js, "measure": []}
    if dry_run:
        log("[promote] would copy %s (component) into %s, check the library copy, add it to %s and point the "
            "film's pages at it" % (name, ws.LIB_COMPONENTS, HTML_COMPONENTS_DOC))
        return plan
    import shutil
    os.makedirs(ws.LIB_COMPONENTS, exist_ok=True)
    shutil.copyfile(js, lib_js)
    shutil.copyfile(css, lib_css)
    label = "assets/html/components/%s" % name
    try:
        probs = ws.component_lint(name, lib_js, lib_css, label)
        rt = ws.component_runtime(name, lib_js, lib_css, label, os.path.join(ws.workshop_dir(out_dir), "_stills"))
        probs += rt["problems"]
        if not probs:
            ws.component_still(name, lib_js, lib_css, os.path.join(ws.LIB_COMPONENTS, name + ".png"),
                               attrs=None, p=1.0, aspect="16:9")
    except ws.WorkshopError as e:
        probs = e.problems
    if probs:
        for f in (lib_js, lib_css, os.path.join(ws.LIB_COMPONENTS, name + ".png")):
            if os.path.exists(f):
                os.remove(f)
        raise PromoteError(["the library copy failed its check (nothing was changed): %s" % p for p in probs])
    doc = _read(HTML_COMPONENTS_DOC) if os.path.isfile(HTML_COMPONENTS_DOC) else HTML_COMPONENTS_HEAD
    _write(HTML_COMPONENTS_DOC, doc.rstrip("\n") + "\n" + _component_doc_entry(name, entry, rt.get("demo"), film))
    pages = _repoint_pages(out_dir, name, js, css, lib_js, lib_css, log=log)
    import storyboard as sb
    os.remove(js)
    os.remove(css)
    for e in board["meta"]["build_list"]:
        if isinstance(e, dict) and e.get("id") == name:
            e["promoted"] = True
    sb.save(board, os.path.join(out_dir, "storyboard.json"))
    log("[promote] %s is in the library (%s); %d page(s) now link it. NEXT: python3 -m pytest tests -q -p "
        "no:cacheprovider" % (name, lib_js, len(pages)))
    plan["pages"] = pages
    return plan


def promote(out_dir, name, family=None, use_when=None, motion=None, dry_run=False, log=print, batch=None,
            keep_workshop=False):
    if name in ws.component_names(out_dir) and name not in ws.shot_names(out_dir) | ws.object_names(out_dir):
        return promote_component(out_dir, name, dry_run=dry_run, log=log)
    kind, src_path, entry, board = preconditions(out_dir, name)
    film = (board.get("meta") or {}).get("title") or os.path.basename(os.path.abspath(out_dir))
    note = _unreviewed_note(out_dir)
    src = _read(src_path)
    dest_dir = SHOTS if kind == "shot" else OBJECTS
    kits = {}
    text, probs = library_source(src, kind, name, out_dir=out_dir, src_dir=os.path.dirname(src_path),
                                 batch=frozenset(batch or ()), kits=kits)
    kit_files, kit_probs = kit_sources(out_dir, kits, batch or ())
    probs += kit_probs
    types, docs = prop_docs(src, name)
    # A PROP'S DOCUMENTATION MAY LIVE ON THE BUILD LIST: `props_doc: {prop: "what it sets — the feel of turning it"}`.
    # Writing it into the source after the render would make the source newer than the film and refuse the item
    # ("changed after the film was rendered"); the board is not part of the render.
    for p_, d_ in ((entry or {}).get("props_doc") or {}).items():
        if p_ in types and p_ not in docs and str(d_).strip():
            what, _sep, feel = str(d_).partition(" — ")
            docs[p_] = (what.strip(), feel.strip() or "—")
    provenance = ws.provenances(out_dir).get(name)
    if kind == "shot":
        for flag, v in (("--family", family), ("--use-when", use_when), ("--motion", motion)):
            if not str(v or "").strip():
                probs.append("a shot needs %s — its catalogue entry and card are written from it" % flag)
        for p in sorted(set(types) - set(docs)):
            probs.append("`%s` has no trailing comment in %s's props type and no `props_doc` entry on its build list — "
                         "the card's table is written from them (`%s?: T;   // what it sets — the feel of turning it`, or "
                         "build_list[…].props_doc.%s)" % (p, name, p, p))
    if probs:
        raise PromoteError(probs)
    plan = {"kind": kind, "to": os.path.join(dest_dir, name + ".tsx"), "kits": sorted(kit_files),
            "measure": measurements(name) if kind == "shot" else []}
    if dry_run:
        log("[promote] would move %s (%s) into %s%s" % (name, kind, plan["to"],
            "; then register and measure it" if kind == "shot" else "; then index and catalogue it"))
        return plan
    for dest, ktext in kit_files.items():
        if not os.path.isfile(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            _write(dest, ktext)
    _write(plan["to"], text)
    if kind == "shot":
        _register(name, family, use_when, provenance)
        _catalogue_shot(name, entry, use_when, types, film, note)
        for i, cmd in enumerate(plan["measure"]):
            try:
                _run(cmd, log=log)
            except PromoteError as e:
                # by position: the same command can appear twice (ground reach), and the first copy has run
                left = [" ".join(c[1:]) for c in plan["measure"][i:]]
                every = [" ".join(c[1:]) for c in plan["measure"]]
                raise PromoteError(e.problems + [
                    "%s is registered but NOT fully measured; run, in order: %s — or, if the fix is an edit to "
                    "the register, every row measured so far describes the old source: run them all, in order: %s"
                    % (name, "; ".join(left), "; ".join(every))])
        _write(os.path.join(CARDS, name + ".md"),
               _card(name, entry, use_when, motion, types, docs, provenance, family, film)
               .replace("**Provenance:**", _measured_line(name) + ("\n\n**Review:**%s." % note.replace(" · ", " ")
                                                                    if note else "") + "\n\n**Provenance:**"))
    else:
        _index_object(name)
        _catalogue_object(name, entry, sorted(k for k in types if k not in ("w", "h", "t", "dna", "yaw", "idle")), film,
                          note)
    # the film now uses the library's copy (a batch removes its copies once every item is in)
    import storyboard as sb
    if not keep_workshop:
        os.remove(src_path)
    for e in board["meta"]["build_list"]:
        if isinstance(e, dict) and e.get("id") == name:
            e["promoted"] = True
    sb.save(board, os.path.join(out_dir, "storyboard.json"))
    log("[promote] %s is in the library (%s). NEXT: python3 -m pytest tests -q -p no:cacheprovider" % (name, plan["to"]))
    return plan


def _promoted_from(out_dir, name, film):
    """True when the library already holds `name` AS this film's promotion — its catalogue line says it was built for
    this film. That is how a batch that stopped part-way resumes: what it already moved is not moved twice."""
    in_lib = os.path.isfile(os.path.join(SHOTS, name + ".tsx")) or os.path.isfile(os.path.join(OBJECTS, name + ".tsx"))
    if not in_lib or not os.path.isfile(LIBRARY):
        return False
    pat = r"\*\*%s\*\* — .*?[Bb]uilt for the film %s\b" % (re.escape(name), re.escape(film))
    return re.search(pat, _read(LIBRARY)) is not None


def _finish(out_dir, paths, objs, log):
    """The film follows its promoted things: their workshop copies go, and any workshop file still importing one by
    a relative path imports the library's (`@objects/X`, `@shots/X`)."""
    for p in paths.values():
        if os.path.exists(p):
            os.remove(p)
    relinked = []
    targets = {os.path.splitext(p)[0] for p in paths.values()} | set(paths.values())
    for f in ws.source_files(out_dir):
        text = _read(f)
        new = text
        for spec in set(ws._IMPORT.findall(text)):
            if not spec.startswith("."):
                continue
            stem = os.path.splitext(os.path.basename(spec))[0]
            if stem in paths and os.path.normpath(os.path.join(os.path.dirname(f), spec)) in targets:
                alias = "@objects/" if stem in objs else "@shots/"
                new = new.replace("'%s'" % spec, "'%s%s'" % (alias, stem)).replace('"%s"' % spec, '"%s%s"' % (alias, stem))
        if new != text:
            _write(f, new)
            relinked.append(os.path.relpath(f, out_dir))
    return relinked


def promote_batch(out_dir, specs, dry_run=False, log=print):
    """Promote several of one film's built things together — objects first, then shots — so items that import each
    other, and the helpers they share, move as one. Every item is checked before anything is written; then each is
    promoted with its workshop copy kept until the last is in; then the copies go and any workshop file that still
    imports a promoted item is pointed at the library (`@objects/X`, `@shots/X`).

    A BATCH THAT STOPS PART-WAY LEAVES THE FILM WORKING AND RESUMES. On the GPS test film the library's measuring
    sweep refused the third item after two objects were in: the library and the film's workshop then both held them,
    and the clash would have stopped the film rendering. Whatever reached the library is now finished for the film
    (copies removed, imports relinked) before the error is raised, and running the same batch again skips every item
    the library already holds as this film's promotion."""
    names = [str(sp.get("name")) for sp in specs]
    objs = ws.object_names(out_dir)
    board = json.loads(_read(os.path.join(out_dir, "storyboard.json")))
    film = (board.get("meta") or {}).get("title") or os.path.basename(os.path.abspath(out_dir))
    wsd = ws.workshop_dir(out_dir)
    path_of = {n: os.path.join(wsd, ("objects" if n in objs else "shots"), n + ".tsx") for n in names}
    already = [n for n in names if _promoted_from(out_dir, n, film)]
    order = [sp for sp in specs if sp.get("name") in objs] + [sp for sp in specs if sp.get("name") not in objs]
    todo = [sp for sp in order if sp["name"] not in already]
    probs = []
    for sp in todo:
        try:
            promote(out_dir, sp["name"], sp.get("family"), sp.get("use_when"), sp.get("motion"), dry_run=True,
                    log=lambda *_a: None, batch=names)
        except PromoteError as e:
            probs += e.problems
    if probs:
        raise PromoteError(probs)
    if dry_run:
        log("[promote] would promote, in order: %s%s" % (", ".join(sp["name"] for sp in todo) or "nothing",
            " (already in the library: %s)" % ", ".join(already) if already else ""))
        return todo
    done = list(already)
    try:
        for sp in todo:
            try:
                promote(out_dir, sp["name"], sp.get("family"), sp.get("use_when"), sp.get("motion"), log=log,
                        batch=names, keep_workshop=True)
                done.append(sp["name"])
            except PromoteError:
                if _promoted_from(out_dir, sp["name"], film):
                    done.append(sp["name"])          # registered, measurement unfinished: the library holds it now
                raise
    except PromoteError as e:
        relinked = _finish(out_dir, {n: path_of[n] for n in done}, objs, log)
        left = [sp["name"] for sp in todo if sp["name"] not in done]
        raise PromoteError(e.problems + ["the batch stopped: %s %s in the library (the film now uses %s%s); not yet "
                                         "promoted: %s — fix the cause and run the same batch again; it resumes"
                                         % (", ".join(done) or "nothing", "is" if len(done) == 1 else "are",
                                            "them" if done else "nothing", "; relinked " + ", ".join(relinked)
                                            if relinked else "", ", ".join(left) or "none")])
    relinked = _finish(out_dir, {n: path_of[n] for n in done}, objs, log)
    log("[promote] batch done: %s in the library%s" % (", ".join(names), ("; the film's %s now import them from the "
        "library" % ", ".join(relinked)) if relinked else ""))
    return order


def main(argv=None):
    ap = argparse.ArgumentParser(description="Promote a delivered film's built thing into the library.")
    ap.add_argument("out_dir")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--batch", help="a JSON list [{name, family?, use_when?, motion?}] promoted together")
    ap.add_argument("--family")
    ap.add_argument("--use-when")
    ap.add_argument("--motion")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.batch:
            promote_batch(a.out_dir, json.load(open(a.batch, encoding="utf-8")), a.dry_run)
            return 0
        if not a.name:
            ap.error("give a NAME, or --batch <spec.json>")
        promote(a.out_dir, a.name, a.family, a.use_when, a.motion, a.dry_run)
        return 0
    except PromoteError as e:
        for p in e.problems:
            print("  REFUSED: " + p)
        return 1


if __name__ == "__main__":
    sys.exit(main())
