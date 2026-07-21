#!/usr/bin/env python3
"""Deterministic PRE-render PEDAGOGY gate — the video-teaching complement to validate/rhythm_qa.

Walks the concept-dependency DAG in <out_dir>/content_plan.json and catches a concept USED BEFORE IT
IS INTRODUCED (a term in `builds_on` that no earlier beat `introduces` and that isn't in
meta.assumed_known) — the pure set-membership check an LLM critic (critic-content's prerequisite gate)
does unreliably. Also advises on cognitive load (an `introduces` that is a list) and scaffold shape
(no `ground` beat before the first `build`; a `build` with no `why`/`land` within one beat).

Mirrors validate.py: a pure evaluate(data) core + a check(out_dir) IO wrapper + main() that prints a
summary and exits non-zero on any ERROR. NO-OPs cleanly when content_plan.json is absent (a simple
deck may not persist one). Run at step 9 alongside validate.py / rhythm_qa.py.
"""
import argparse, json, os, re, sys


def _norm(c):
    # Normalize a concept name so 'the Fourier transform' == 'Fourier transform' and 'k-space' == 'k space'
    # — an exact string match wrongly ERRORed "used before introduced" on these harmless variants.
    if not isinstance(c, str):
        return ""
    s = c.strip().lower()
    s = re.sub(r"^(the|a|an)\s+", "", s)     # drop a leading article
    s = re.sub(r"[-\s]+", " ", s).strip()    # collapse hyphens/whitespace
    return s


def evaluate(data):
    """Pure check over a content plan dict: {meta:{assumed_known:[]}, beats:[{introduces, builds_on, stage}]}."""
    errors, warnings = [], []
    meta = data.get("meta") or {}
    beats = data.get("beats") or data.get("slides") or []
    # assumed_known lives top-level in the content plan (meta.assumed_known also accepted)
    assumed = data.get("assumed_known") or meta.get("assumed_known") or []
    introduced = {_norm(c) for c in assumed if _norm(c)}
    seen_ground = False
    first_build = False
    for i, b in enumerate(beats):
        tag = f"beat {b.get('index', i + 1)}"
        stage = _norm(b.get("stage"))
        intro = b.get("introduces")
        builds = b.get("builds_on") or []
        # cognitive load — one NEW concept per beat: `introduces` is a single concept or null, not a list
        if isinstance(intro, list):
            warnings.append(f"{tag}: `introduces` is a list of {len(intro)} — a beat should teach ONE new concept; "
                            f"split into a build + a why beat")
            intro_items = [x for x in intro if _norm(x)]
        else:
            intro_items = [intro] if _norm(intro) else []
        # prerequisite gate — every dependency must already be known
        for dep in (builds if isinstance(builds, list) else [builds]):
            if _norm(dep) and _norm(dep) not in introduced:
                errors.append(f"{tag}: builds_on '{dep}' is used before it is introduced — introduce it in an "
                              f"earlier ground/build beat, or resequence")
        # scaffold shape — ground before the first build
        if stage == "ground":
            seen_ground = True
        if stage == "build" and not first_build:
            first_build = True
            if not seen_ground:
                warnings.append(f"{tag}: the first `build` beat has no `ground` beat before it — anchor the topic "
                                f"in something the audience already knows before the first new idea")
        for x in intro_items:                             # only NOW is this beat's concept known to later beats
            introduced.add(_norm(x))
    # build -> why adjacency: a new idea's consequence must land before the next new idea.
    # A beat can also land its OWN consequence — one page that reveals the idea and then its
    # implication is a legitimate (often better) structure than splitting them across two pages.
    # `stage` is a single label and cannot say that, so a beat says it directly: `lands_within`,
    # or a `points` list whose second entry IS the consequence. Reading only the stage label would
    # flag exactly the beats that scaffold best — the gate must measure the landing, not the tag.
    for i, b in enumerate(beats):
        if _norm(b.get("stage")) != "build":
            continue
        if b.get("lands_within") or len(b.get("points") or []) > 1:
            continue
        nxt = [_norm(beats[j].get("stage")) for j in (i + 1, i + 2) if j < len(beats)]
        if "why" not in nxt and "land" not in nxt:
            warnings.append(f"beat {b.get('index', i + 1)}: a `build` beat is not followed within one beat by a "
                            f"`why`/`land` — show the new idea's consequence before introducing the next one")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "beats": len(beats)}


def check(out_dir):
    path = os.path.join(out_dir, "content_plan.json")
    if not os.path.exists(path):
        return {"ok": True, "errors": [], "warnings": [], "beats": 0, "skipped": "no content_plan.json"}
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"ok": False, "errors": [f"content_plan.json unreadable: {e}"], "warnings": [], "beats": 0}
    return evaluate(data)


def main():
    ap = argparse.ArgumentParser(description="Pedagogy DAG gate over content_plan.json")
    ap.add_argument("out_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = check(a.out_dir)
    if a.json:
        print(json.dumps(r, indent=2))
    elif r.get("skipped"):
        print(f"[pedagogy_qa] {r['skipped']} — nothing to check")
    else:
        for e in r["errors"]:
            print(f"  ERROR: {e}")
        for w in r["warnings"]:
            print(f"  warn:  {w}")
        print(f"[pedagogy_qa] {'OK' if r['ok'] else 'FAIL'}  {r['beats']} beat(s), "
              f"{len(r['errors'])} error(s), {len(r['warnings'])} warning(s)")
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
