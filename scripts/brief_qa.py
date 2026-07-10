#!/usr/bin/env python3
"""Deterministic PRE-plan BRIEF floor — no hollow comprehension brief reaches the content-planner.

Reads <out_dir>/brief.json (the structured comprehension brief written at step 3) and ERRORs on a
missing/empty required key, a non-singular `the_one_thing`, or a `source_health:contradictory` with no
resolved conflicts; WARNs on an evidence item with no `source_ref` or a verbless (topic-label) thesis.
The SEMANTIC depth check (is the mechanism actually understood, not paraphrased) stays with
critic-content C0 — this is only the structural floor that a brief can't be skipped or hollowed out.

Run at step 3.5 BEFORE dispatching the planner. Exits non-zero on any ERROR.
"""
import argparse, json, os, re, sys

_REQUIRED = ["thesis", "mechanism", "evidence", "why_it_matters", "the_one_thing", "source_health"]
# a small verb set — a thesis with none reads as a bare topic label ("about X") not a claim ("X cuts Y")
_VERBS = {"is", "are", "was", "cuts", "reduces", "increases", "improves", "enables", "causes", "makes",
          "lets", "turns", "shows", "proves", "beats", "raises", "lowers", "removes", "adds", "replaces",
          "predicts", "learns", "uses", "avoids", "prevents", "speeds", "slows", "drops", "grows",
          "shrinks", "outperforms", "yields", "converts", "maps", "links", "drives", "hides", "reveals",
          "means", "allows", "requires", "needs", "gives", "costs", "saves", "closes", "opens", "breaks"}


def _empty(v):
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, (list, dict, tuple, set)):
        return len(v) == 0
    return False


def evaluate(data):
    errors, warnings = [], []
    for k in _REQUIRED:
        if k not in data or _empty(data.get(k)):
            errors.append(f"brief.json missing/empty required key: `{k}`")

    ot = data.get("the_one_thing")
    if isinstance(ot, list):
        errors.append("`the_one_thing` is a list — it must be a SINGLE sentence the viewer leaves with")
    elif isinstance(ot, str) and ot.strip() and \
            len(re.findall(r"(?<!\d)[.!?](?!\d)|[。！？]", ot.strip())) > 1:
        # count SENTENCE terminators, not the '.' inside a decimal/version ("3.5x", "v1.2") — those wrongly
        # tripped a blocking ERROR on a legitimate one-sentence takeaway that contains a number.
        errors.append("`the_one_thing` has >1 sentence — collapse it to ONE takeaway")

    sh = data.get("source_health")
    status = sh.get("status") if isinstance(sh, dict) else sh
    if status == "contradictory":
        conflicts = sh.get("conflicts") if isinstance(sh, dict) else None
        if not conflicts:
            errors.append("source_health is 'contradictory' but no conflicts are recorded — name + resolve each "
                          "(primary source wins), or STOP and ask the user")
        else:
            for c in conflicts:
                if isinstance(c, dict) and _empty(c.get("resolution")):
                    errors.append("a source_health conflict has no `resolution` — resolve it (primary source wins) "
                                  "or flag it; never narrate over an unresolved contradiction")
                    break

    for ev in (data.get("evidence") or []):
        if isinstance(ev, dict) and _empty(ev.get("source_ref")):
            warnings.append("an evidence item has no `source_ref` — tie each claim to the figure/number that proves it")
            break

    th = data.get("thesis")
    if isinstance(th, str) and th.strip():
        toks = {t.lower().strip(".,;:!?()\"'") for t in th.split()}
        if not (toks & _VERBS):
            warnings.append("thesis has no recognizable verb — it reads as a topic label, not a claim "
                            "('X cuts Y by Z via M', not 'about X')")
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def check(out_dir, target_seconds=None):
    path = os.path.join(out_dir, "brief.json")
    if not os.path.exists(path):
        if target_seconds and float(target_seconds) > 60:
            return {"ok": False, "warnings": [],
                    "errors": ["brief.json missing — write the structured comprehension brief before planning "
                               "(required once the video is > 60s)"]}
        return {"ok": True, "errors": [], "warnings": [], "skipped": "no brief.json"}
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"ok": False, "errors": [f"brief.json unreadable: {e}"], "warnings": []}
    return evaluate(data)


def main():
    ap = argparse.ArgumentParser(description="Comprehension-brief floor gate over brief.json")
    ap.add_argument("out_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = check(a.out_dir)
    if a.json:
        print(json.dumps(r, indent=2))
    elif r.get("skipped"):
        print(f"[brief_qa] {r['skipped']} — nothing to check")
    else:
        for e in r["errors"]:
            print(f"  ERROR: {e}")
        for w in r["warnings"]:
            print(f"  warn:  {w}")
        print(f"[brief_qa] {'OK' if r['ok'] else 'FAIL'}  {len(r['errors'])} error(s), {len(r['warnings'])} warning(s)")
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
