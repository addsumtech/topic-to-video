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

REFUSED, never guessed: a film that is not delivered (no out.mp4, or NOT_DELIVERED.md still there — the critic has
not passed it); an item changed after that render; an item the workshop check fails; an item not on the build list;
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


def preconditions(out_dir, name):
    """(kind, source path, build-list entry, board) — or PromoteError naming EVERY reason it may not be promoted."""
    probs = []
    mp4 = os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(mp4):
        probs.append("the film has no out.mp4 — promote from a delivered film")
    if os.path.exists(os.path.join(out_dir, "NOT_DELIVERED.md")):
        probs.append("NOT_DELIVERED.md is still there — the critic has not passed this film "
                     "(critic_ledger.py --final removes it when the review passes)")
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


def library_source(text, kind, name):
    """The workshop source as library code: `@runtime/` and `@shots/` become relative imports. A relative import
    in workshop code names a workshop file or asset, which the library cannot resolve — refused by name, as is an
    alias naming nothing. A shot's GROUND and PROVENANCE declarations (and the comment lines directly above them)
    are dropped: the library MEASURES the ground, and the provenance goes to shot_director."""
    probs = []
    for spec in ws._IMPORT.findall(text):
        if spec.startswith("@runtime/"):
            mod = spec[len("@runtime/"):]
            if not any(os.path.isfile(os.path.join(ws.RUNTIME, mod + e)) for e in ("", ".ts", ".tsx", ".json")):
                probs.append("%s imports %s — there is no runtime module %r" % (name, spec, mod))
        elif spec.startswith("@shots/"):
            if spec[len("@shots/"):] not in ws.library_shot_names():
                probs.append("%s imports %s — there is no library register %r" % (name, spec, spec[len("@shots/"):]))
        elif spec.startswith("."):
            probs.append("%s imports %r — a workshop file or asset the library cannot resolve; inline it, or promote "
                         "it first" % (name, spec))
    shots_rel = "./" if kind == "shot" else "../shots/"
    out = text.replace("'@runtime/", "'../runtime/").replace('"@runtime/', '"../runtime/')
    out = out.replace("'@shots/", "'" + shots_rel).replace('"@shots/', '"' + shots_rel)
    if kind == "shot":
        out = re.sub(r"(?:^[ \t]*//[^\n]*\n)*^export const (?:GROUND|PROVENANCE)\b[^\n]*\n", "", out, flags=re.M)
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


def _catalogue_shot(name, entry, use_when, types, film):
    s = _read(LIBRARY)
    m = re.search(r"^(\d+)\. \*\*%s\*\* — .*$" % re.escape(name), s, re.M)
    if not m:
        raise PromoteError(["register_shot wrote no LIBRARY.md entry for %s" % name])
    line = "%s. **%s** — %s *Use: %s.* `%s` · built for the film %s." % (
        m.group(1), name, entry["means"], use_when.rstrip("."), ", ".join(sorted(types)), film)
    _write(LIBRARY, s[:m.start()] + line + s[m.end():])


def _catalogue_object(name, entry, props, film):
    s = _read(LIBRARY)
    if OBJECTS_ANCHOR not in s:
        raise PromoteError(["LIBRARY.md has no objects section (%s)" % OBJECTS_ANCHOR])
    line = "- **%s** — %s *Built for the film %s.*%s" % (
        name, entry["means"], film, (" `%s`" % ", ".join(sorted(props))) if props else "")
    _write(LIBRARY, s.rstrip("\n") + "\n" + line + "\n")


def _component_preconditions(out_dir, name):
    """(js, css, build-list entry, board) for promoting the film's component `name` — or PromoteError naming EVERY
    reason it may not be."""
    probs = []
    mp4 = os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(mp4):
        probs.append("the film has no out.mp4 — promote from a delivered film")
    if os.path.exists(os.path.join(out_dir, "NOT_DELIVERED.md")):
        probs.append("NOT_DELIVERED.md is still there — the critic has not passed this film "
                     "(critic_ledger.py --final removes it when the review passes)")
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


def promote(out_dir, name, family=None, use_when=None, motion=None, dry_run=False, log=print):
    if name in ws.component_names(out_dir) and name not in ws.shot_names(out_dir) | ws.object_names(out_dir):
        return promote_component(out_dir, name, dry_run=dry_run, log=log)
    kind, src_path, entry, board = preconditions(out_dir, name)
    film = (board.get("meta") or {}).get("title") or os.path.basename(os.path.abspath(out_dir))
    src = _read(src_path)
    dest_dir = SHOTS if kind == "shot" else OBJECTS
    text, probs = library_source(src, kind, name)
    types, docs = prop_docs(src, name)
    provenance = ws.provenances(out_dir).get(name)
    if kind == "shot":
        for flag, v in (("--family", family), ("--use-when", use_when), ("--motion", motion)):
            if not str(v or "").strip():
                probs.append("a shot needs %s — its catalogue entry and card are written from it" % flag)
        for p in sorted(set(types) - set(docs)):
            probs.append("`%s` has no trailing comment in %s's props type — the card's table is written from them "
                         "(`%s?: T;   // what it sets — the feel of turning it`)" % (p, name, p))
    if probs:
        raise PromoteError(probs)
    plan = {"kind": kind, "to": os.path.join(dest_dir, name + ".tsx"), "measure": measurements(name) if kind == "shot" else []}
    if dry_run:
        log("[promote] would move %s (%s) into %s%s" % (name, kind, plan["to"],
            "; then register and measure it" if kind == "shot" else "; then index and catalogue it"))
        return plan
    _write(plan["to"], text)
    if kind == "shot":
        _register(name, family, use_when, provenance)
        _catalogue_shot(name, entry, use_when, types, film)
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
               .replace("**Provenance:**", _measured_line(name) + "\n\n**Provenance:**"))
    else:
        _index_object(name)
        _catalogue_object(name, entry, sorted(k for k in types if k not in ("w", "h", "t", "dna", "yaw")), film)
    # the film now uses the library's copy
    import storyboard as sb
    os.remove(src_path)
    for e in board["meta"]["build_list"]:
        if isinstance(e, dict) and e.get("id") == name:
            e["promoted"] = True
    sb.save(board, os.path.join(out_dir, "storyboard.json"))
    log("[promote] %s is in the library (%s). NEXT: python3 -m pytest tests -q -p no:cacheprovider" % (name, plan["to"]))
    return plan


def main(argv=None):
    ap = argparse.ArgumentParser(description="Promote a delivered film's built thing into the library.")
    ap.add_argument("out_dir")
    ap.add_argument("name")
    ap.add_argument("--family")
    ap.add_argument("--use-when")
    ap.add_argument("--motion")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        promote(a.out_dir, a.name, a.family, a.use_when, a.motion, a.dry_run)
        return 0
    except PromoteError as e:
        for p in e.problems:
            print("  REFUSED: " + p)
        return 1


if __name__ == "__main__":
    sys.exit(main())
