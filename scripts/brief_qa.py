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


def evaluate(data, out_dir=None):
    errors, warnings = [], []
    for k in _REQUIRED:
        if k not in data or _empty(data.get(k)):
            errors.append(f"brief.json missing/empty required key: `{k}`")

    ot = data.get("the_one_thing")
    if isinstance(ot, list):
        errors.append("`the_one_thing` is a list — it must be a SINGLE sentence the viewer leaves with")
    elif isinstance(ot, str) and ot.strip() and \
            len(re.findall(r"(?<!\d)[.!?](?!\d)|[。！？]",
                           re.sub(r"(?<=\w)\.(?=\w)", "",
                                  re.sub(r"\b(?:e\.g|i\.e|etc|vs|Dr|Mr|Mrs|Ms|Prof|No|Fig|approx)\.", " ",
                                         ot.strip())))) > 1:
        # count SENTENCE terminators only: mask the '.' inside a decimal/version ("3.5x", "v1.2"),
        # a FILENAME/token ("SKILL.md", "index.html" — letter.letter), and common abbreviations
        # ("e.g.", "vs.") — each wrongly tripped a blocking ERROR on a one-sentence takeaway.
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

    # A source_ref that points at nothing is a citation in name only. When `sources/` has been
    # captured (scripts/sources.py), resolve every ref against the text that was actually read —
    # this is the one place a WRONG INPUT would otherwise produce a fully-green output: the gates
    # check the brief's internal consistency, the plans inherit it, and every beat carries the error.
    try:
        import sources as _src
        _have_sources = bool(out_dir) and bool(_src.load(out_dir))
    except Exception:
        _src, _have_sources = None, False
    if _have_sources:
        for ev in (data.get("evidence") or []):
            if not isinstance(ev, dict):
                continue
            ref = ev.get("source_ref")
            if _empty(ref):
                continue
            ok, detail = _src.resolve(out_dir, ref)
            if not ok:
                errors.append(f"evidence source_ref does not resolve: {detail}")
            elif "no anchor given" in detail:
                warnings.append(f"evidence source_ref '{ref}' names a source but pins no passage — "
                                f"add '#<a literal quote from the extract>' so the claim is checkable")

    for ev in (data.get("evidence") or []):
        if isinstance(ev, dict) and _empty(ev.get("source_ref")):
            warnings.append("an evidence item has no `source_ref` — tie each claim to the figure/number that proves it")
            break

    # COVERAGE — what was READ vs SAMPLED vs SKIPPED. `unknowns` records what could not be
    # determined; coverage records what was never looked at. The second is the more dangerous of
    # the two because it is invisible: nothing in the brief reveals that chapter 7 was skipped.
    cov = data.get("coverage")
    if cov is None:
        warnings.append("brief has no `coverage` — record what you read IN FULL, what you only "
                        "SAMPLED, and what you SKIPPED. `unknowns` covers what you could not "
                        "determine; it does not reveal what you never opened")
    elif isinstance(cov, dict) and not any(str(cov.get(k) or "").strip() or cov.get(k)
                                           for k in ("read_in_full", "sampled", "skipped")):
        warnings.append("`coverage` is present but empty — name at least what was read in full")

    th = data.get("thesis")
    if isinstance(th, str) and th.strip():
        # the verb set is ENGLISH — only apply the heuristic to a confidently-English thesis, else every
        # Chinese/Japanese/other-language brief gets a spurious "no verb" warning.
        _letters = [c for c in th if c.isalpha()]
        _ascii_ratio = (sum(1 for c in _letters if c.isascii()) / len(_letters)) if _letters else 1.0
        _englishish = _ascii_ratio > 0.6 and not re.search(r"[　-ヿ㐀-鿿가-힣]", th)
        toks = {t.lower().strip(".,;:!?()\"'") for t in th.split()}
        if _englishish and not (toks & _VERBS):
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
    return evaluate(data, out_dir)


def main():
    ap = argparse.ArgumentParser(description="Comprehension-brief floor gate over brief.json")
    ap.add_argument("out_dir")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--target-seconds", type=float, default=None)
    a = ap.parse_args()
    ts = a.target_seconds
    if ts is None:      # read from the storyboard meta so the missing-brief >60s gate actually fires on a normal run
        try:
            _sb = json.load(open(os.path.join(a.out_dir, "storyboard.json"), encoding="utf-8"))
            ts = (_sb.get("meta") or {}).get("target_seconds")
        except (OSError, ValueError):
            ts = None
    r = check(a.out_dir, target_seconds=ts)
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
