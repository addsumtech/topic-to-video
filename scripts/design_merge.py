#!/usr/bin/env python3
"""MERGE PARALLEL BUILDERS' WORK INTO THE BOARD — the join step of a parallel design pass (SKILL.md 3.6 ②, "Parallel
build").

    python3 scripts/design_merge.py <out_dir> [--dry-run]

WHY. One design agent built a 25-beat film's nine shots one after another: 116 min, of which 58 were the model writing
code — time no render cache can recover. Builders working at once cut that, but the board is ONE file: two agents
editing storyboard.json together lose each other's writes. So a builder never touches the board. It writes its shots
(`workshop/shots/<Name>.tsx`) and ONE part file, `<out_dir>/_design_parts/<builder>.json`:

    {"builder": "b2",
     "shots": ["WeightedWheel", "OddsStatement"],                 # the built shots this builder OWNS
     "beats": {"12": {"shot": "WeightedWheel", "shot_props": {…}, "shot_fit": {"verdict": "build", "why": "…"},
                      "shot_adaptation": {…}}, …},
     "build_list": [{"id": "WeightedWheel", "kind": "shot", "beats": [12, 14], "means": "…", "accept": "…"}, …]}

and the lead merges them here. REFUSED, never guessed — nothing is written unless every part is clean:
  * a beat claimed by two parts, or a shot owned by two;
  * a beat whose `shot` is a built shot its part does not own (a builder setting another's beat);
  * an owned shot with no `workshop/shots/<Name>.tsx`, or a build_list entry for a shot the part does not own;
  * a beat number the board does not have.
What the LEAD decided stays the lead's: a beat's `shot_fit.ideal`, `form` and `composition` (written before any builder
started) are kept; a builder may add `verdict`, `why`, `ref`, `shares`. The board before the merge is kept as
`storyboard.premerge.json`.
"""
import argparse
import glob
import json
import os
import sys

PARTS = "_design_parts"
LEAD_FIT = ("ideal", "form", "composition")


class MergeError(RuntimeError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


def load_parts(out_dir):
    parts = []
    for p in sorted(glob.glob(os.path.join(out_dir, PARTS, "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise MergeError(["%s does not parse: %s" % (os.path.basename(p), e)])
        if not isinstance(d, dict):
            raise MergeError(["%s is not an object" % os.path.basename(p)])
        d.setdefault("builder", os.path.splitext(os.path.basename(p))[0])
        d["_file"] = os.path.basename(p)
        parts.append(d)
    return parts


def check(out_dir, board, parts):
    """The problems that block a merge — [] when every part is clean."""
    probs = []
    n = len(board.get("slides") or [])
    beat_owner, shot_owner = {}, {}
    all_owned = set()
    for part in parts:
        for shot in part.get("shots") or []:
            all_owned.add(shot)
    for part in parts:
        who = part["builder"]
        owned = set(part.get("shots") or [])
        for shot in sorted(owned):
            if shot in shot_owner:
                probs.append("shot %s is owned by both %s and %s" % (shot, shot_owner[shot], who))
            shot_owner[shot] = who
            if not os.path.isfile(os.path.join(out_dir, "workshop", "shots", shot + ".tsx")):
                probs.append("%s owns %s but workshop/shots/%s.tsx does not exist" % (who, shot, shot))
        for k, b in (part.get("beats") or {}).items():
            try:
                i = int(k)
            except (TypeError, ValueError):
                probs.append("%s: beat key %r is not a number" % (who, k))
                continue
            if not 1 <= i <= n:
                probs.append("%s: beat %d is not on the board (1..%d)" % (who, i, n))
                continue
            if i in beat_owner:
                probs.append("beat %d is set by both %s and %s" % (i, beat_owner[i], who))
            beat_owner[i] = who
            shot = (b or {}).get("shot")
            if shot in all_owned and shot not in owned:
                probs.append("%s sets beat %d to %s, which %s owns" % (who, i, shot, shot_owner.get(shot, "another builder")))
        for e in part.get("build_list") or []:
            if isinstance(e, dict) and e.get("kind", "shot") == "shot" and e.get("id") not in owned:
                probs.append("%s lists %s on the build list but does not own it" % (who, e.get("id")))
    return probs


def merge(out_dir, dry_run=False, log=print):
    path = os.path.join(out_dir, "storyboard.json")
    board = json.load(open(path, encoding="utf-8"))
    parts = load_parts(out_dir)
    if not parts:
        raise MergeError(["no part files in %s/ — nothing to merge" % PARTS])
    probs = check(out_dir, board, parts)
    if probs:
        raise MergeError(probs)
    slides = board["slides"]
    changed = []
    for part in parts:
        for k, b in sorted((part.get("beats") or {}).items(), key=lambda kv: int(kv[0])):
            s = slides[int(k) - 1]
            if "shot" in b:
                s["shot"] = b["shot"]
            if "shot_props" in b:
                s["shot_props"] = b["shot_props"]
            if "shot_adaptation" in b:
                s["shot_adaptation"] = b["shot_adaptation"]
            fit = dict(s.get("shot_fit") or {})
            for fk, fv in (b.get("shot_fit") or {}).items():
                if fk in LEAD_FIT and fit.get(fk):
                    continue                              # the lead's decision, written before any builder began
                fit[fk] = fv
            if fit:
                s["shot_fit"] = fit
            changed.append(int(k))
    meta = board.setdefault("meta", {})
    bl = [e for e in (meta.get("build_list") or []) if isinstance(e, dict)]
    by_id = {e.get("id"): i for i, e in enumerate(bl)}
    for part in parts:
        for e in part.get("build_list") or []:
            if e.get("id") in by_id:
                bl[by_id[e["id"]]] = e
            else:
                by_id[e.get("id")] = len(bl)
                bl.append(e)
    meta["build_list"] = bl
    log("[design_merge] %d part(s) from %s · %d beat(s) set: %s · %d build-list entr(ies)"
        % (len(parts), ", ".join(p["builder"] for p in parts), len(changed), sorted(changed), len(bl)))
    if dry_run:
        return board
    pre = os.path.join(out_dir, "storyboard.premerge.json")
    json.dump(json.load(open(path, encoding="utf-8")), open(pre, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    tmp = path + ".tmp"
    json.dump(board, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    log("[design_merge] wrote storyboard.json (the board before the merge: storyboard.premerge.json)")
    log("NEXT: python3 scripts/workshop.py %s check && python3 scripts/seam_plan.py %s && "
        "python3 scripts/shot_proof.py %s" % (out_dir, out_dir, out_dir))
    return board


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        merge(a.out_dir, dry_run=a.dry_run)
    except MergeError as e:
        for p in e.problems:
            print("  REFUSED: %s" % p)
        print("[design_merge] nothing written — fix the parts and run it again")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
