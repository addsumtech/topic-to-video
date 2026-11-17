"""shot_plan_qa — is a film's craft plan sound BEFORE it is built? Reads <film_dir>/shot_plan.json.

    python3 scripts/shot_plan_qa.py <film_dir> [--json]

The plan is the director's commitment to HOW each moment is made (references/promo-shotcraft.md §2, "the method"):
{
  "kind": "product" | "explainer",
  "motion_voice": {"preset": "trusted|refined|bold|playful|calm|friendly|<own>", "main_frames": 21,
                   "easing": "cubic-bezier(0,0,0.2,1)", "overshoot": 1.0},
  "signature": {"idea": "the one visual idea only this subject could have", "shot": "s05"},
  "features": ["One-sentence tasks", "Plans the steps", ...],          # product films: every feature to show
  "shots": [{"id": "s01", "start": 0.0, "end": 3.6, "job": "open|line|show|demo|camera|data|emphasis|rhythm|close",
             "technique": "spotlight-hero", "hero": true, "features": ["One-sentence tasks"],
             "hold": 1.0, "seam_out": "travel|flash|whip|occlusion|light|line-carry|push|match|beat-cut|state|fade|end"}]
}
("state": a UI state change inside one window, a hard change by design; "match": a match cut. scripts/seam_qa.py then
checks the film keeps these promises: a seam planned as hidden must not measure as a bare swap.)

ERRORS (the plan breaks the method):
  - a product film's feature that no shot shows (a core feature with no shot is a hole);
  - one technique the hero of two shots (each technique is the star once);
  - the opening shorter than 3 s (one hero needs a complete arc), or the closing hold under 1 s (the brand holds);
  - a shot boundary with no seam named, or "cut" between scenes (no bare cuts; "beat-cut" is the deliberate
    percussion exception);
  - no motion voice, or shots that overlap / leave gaps in time;
  - no signature idea, or one placed in a shot the plan does not have (SKILL.md "You are the film's designer").
WARNINGS: two adjacent shots with the same job and technique (sameness); more than 3 "beat-cut"/whole-frame hits.
Exit 0 clean (warnings allowed), 1 on any error, 2 on a usage error or a missing / unreadable plan.
"""
import json
import os
import sys

import _common as _c

JOBS = {"open", "line", "show", "demo", "camera", "data", "emphasis", "rhythm", "close"}
SEAMS = {"travel", "flash", "whip", "occlusion", "light", "line-carry", "push", "match", "beat-cut", "state", "fade", "end"}
_USAGE = "usage: shot_plan_qa.py <film_dir> [--json]"


def evaluate(plan):
    err, warn = [], []
    mv = plan.get("motion_voice") or {}
    if not (mv.get("preset") and mv.get("main_frames") and mv.get("easing")):
        err.append("no motion voice (preset, main_frames, easing): one voice must govern every entrance and transition")
    shots = plan.get("shots") or []
    if not shots:
        return err + ["no shots"], warn
    sig = plan.get("signature") or {}
    if not str(sig.get("idea", "")).strip():
        err.append("no signature idea: name the one visual idea only this subject could have, and the shot it owns")
    elif sig.get("shot") not in {s.get("id") for s in shots}:
        err.append("the signature idea is placed in shot %r, which the plan does not have" % sig.get("shot"))
    for s in shots:
        if s.get("job") not in JOBS:
            err.append("%s: job %r is not one of %s" % (s.get("id"), s.get("job"), sorted(JOBS)))
        if not s.get("technique"):
            err.append("%s: no technique named" % s.get("id"))
    t = 0.0
    for s in shots:
        a, b = float(s.get("start", -1)), float(s.get("end", -1))
        if abs(a - t) > 0.05 or b <= a:
            err.append("%s: runs %.2f-%.2f s, but the film is at %.2f s there (shots must tile the film with no gap or "
                       "overlap)" % (s.get("id"), a, b, t))
        t = b
    first, last = shots[0], shots[-1]
    if float(first["end"]) - float(first["start"]) < 3.0:
        err.append("%s: the opening runs %.1f s; one hero needs a complete arc of at least 3 s"
                   % (first.get("id"), float(first["end"]) - float(first["start"])))
    if float(last.get("hold", 0)) < 1.0:
        err.append("%s: the closing hold is %.1f s; the brand / final line holds still at least 1 s"
                   % (last.get("id"), float(last.get("hold", 0))))
    heroes = {}
    for s in shots:
        if s.get("hero"):
            heroes.setdefault(s.get("technique"), []).append(s.get("id"))
    for tech, ids in heroes.items():
        if len(ids) > 1:
            err.append("technique %r is the hero of %s: each technique is the star once (make one a quieter variant)"
                       % (tech, ", ".join(ids)))
    for s in shots[:-1]:
        seam = s.get("seam_out")
        if seam == "cut" or seam is None:
            err.append("%s: the cut out of it is bare (seam_out %r); hide it (flash, whip, occlusion, light), travel into "
                       "the next scene, carry a line, push, match, or mark it a deliberate beat-cut" % (s.get("id"), seam))
        elif seam not in SEAMS:
            err.append("%s: seam_out %r is not one of %s" % (s.get("id"), seam, sorted(SEAMS)))
    if plan.get("kind") == "product":
        shown = {f for s in shots for f in (s.get("features") or [])}
        for f in plan.get("features") or []:
            if f not in shown:
                err.append("feature %r has no shot: a core feature with no shot is a hole" % f)
        if not plan.get("features"):
            err.append("a product film lists no features: list them and map each to a shot")
    for x, y in zip(shots, shots[1:]):
        if x.get("job") == y.get("job") and x.get("technique") == y.get("technique"):
            warn.append("%s and %s: same job and technique back to back (reads as one shot twice)" % (x["id"], y["id"]))
    hits = sum(1 for s in shots if s.get("seam_out") == "beat-cut")
    if hits > 3:
        warn.append("%d beat-cuts: whole-frame hits read as shaking beyond about 3 per film" % hits)
    return err, warn


def main(argv):
    _c.refuse_unknown(argv, valued=(), switches=("json",), usage=_USAGE)
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(_USAGE, file=sys.stderr)
        return 2
    path = os.path.join(args[0], "shot_plan.json")
    try:
        plan = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("shot_plan_qa: cannot read %s (%s)" % (path, e), file=sys.stderr)
        return 2
    err, warn = evaluate(plan)
    if "--json" in argv:
        print(json.dumps({"errors": err, "warnings": warn}, ensure_ascii=False))
    else:
        for e in err:
            print("ERROR  " + e)
        for w in warn:
            print("WARN   " + w)
        print("[shot_plan_qa] %s  %d error(s), %d warning(s)" % ("OK" if not err else "RED", len(err), len(warn)))
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
