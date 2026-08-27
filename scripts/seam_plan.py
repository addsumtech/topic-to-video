#!/usr/bin/env python3
"""Plan the film's MARKED seams — the ~2-3 cuts that mean something — and write them into the storyboard.

  python3 scripts/seam_plan.py <out_dir>            # plan and write `transition_in` on the chosen beats
  python3 scripts/seam_plan.py <out_dir> --dry-run  # print the plan, change nothing

WHY THIS EXISTS. The remotion tier already had the whole apparatus: `Film.tsx` implements five kinetic
seams including `carry`, a collapse-to-line match-cut that reads as CONTINUITY rather than a swap;
`render_remotion.py` maps a scene's `transition_in` onto them; `Film.tsx` guards them against a
luminance flash. And a delivered 35-beat film used NONE of it. All 34 of its seams were the default
cross-fade, because nothing in the authoring path ever wrote the field — the storyboard did not contain
the key at all. A capability that never reaches the artifact is indistinguishable from one that was
never built, and this is the second time that exact shape has cost a delivery.

So the intent the storyboard ALREADY carries is translated into seams here. Every beat declares a
`relation` to the one before it; that is the argument, and a cut is a claim about the same relationship:

  new-topic  → `clock`     the frame opens outward onto a different subject — a chapter break
  payoff     → `dissolve`  setup and result share the screen for a moment: THIS became THAT
  close      → `carry`     the last move reads as continuity, not as one more swap

`continuation` is never marked. Most cuts should be invisible; a marked seam only means something while
it stays rare, which is why the budget is 2 on a short film and 3 on a long one, never per-chapter.

TWO CONSTRAINTS MAKE THE PLAN, NOT TASTE:

  LUMINANCE. `Film.tsx` forces a plain fade across a dark↔light boundary, because a bright frame sliding
  over a dark one is a flash. A kinetic mark placed there is silently discarded — it would look like the
  planner did nothing. `carry` is the documented exception (its neutral bridge line IS the dip), so a
  crossing seam either becomes a carry or is not marked at all.

  SPACING. Two marked seams close together stop reading as punctuation and start reading as a style. They
  are kept at least `MIN_GAP` beats apart.

Deterministic: same storyboard in, same marks out. The shot-director may override any of it by writing
`transition_in` itself — an explicit mark always wins.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shot_director import shot_luma                                   # noqa: E402

# relation → the cut that makes that claim. `continuation` is deliberately absent: it is the one relation
# whose honest cut is no cut at all.
SEAM_BY_RELATION = {
    "new-topic": {"type": "clock"},
    "payoff": {"type": "dissolve"},
    "close": {"type": "carry"},
}
# the seam that is allowed to cross a dark↔light boundary — its bridge line is the luminance dip
CROSSING_SEAM = {"type": "carry"}

MIN_GAP = 5          # beats between two marked seams, so a mark stays punctuation
_LUM_RANK = {"dark": 0, "mid": 1, "light": 2}


def _budget(n):
    """~2 on a short film, 3 on a long one. A mark means something only while it is rare."""
    return 2 if n < 20 else 3


def _crosses(prev_shot, shot):
    """Would Film.tsx force this seam back to a fade? (its luminance guard, mirrored)"""
    a, b = _LUM_RANK.get(shot_luma(prev_shot), 1), _LUM_RANK.get(shot_luma(shot), 1)
    return abs(a - b) >= 2


def plan(slides):
    """→ {beat_index: {"type": ..., "why": ...}} for the beats that should carry a marked seam.

    Beat 0 is never a candidate: there is no seam before the first shot.
    """
    cands = []
    for i in range(1, len(slides)):
        rel = (slides[i].get("relation") or "").strip().lower()
        seam = SEAM_BY_RELATION.get(rel)
        if not seam:
            continue
        crossing = _crosses(slides[i - 1].get("shot"), slides[i].get("shot"))
        if crossing:
            # only the carry survives the luminance guard; anything else would be silently discarded
            seam = dict(CROSSING_SEAM)
            why = "%s across a dark/light boundary — carry is the seam whose bridge line IS the dip" % rel
        else:
            seam = dict(seam)
            why = {"new-topic": "opens outward onto a different subject",
                   "payoff": "setup and result share the screen: this became that",
                   "close": "the last move reads as continuity, not one more swap"}[rel]
        # `close` is the film's ending and always the strongest candidate; then chapter breaks; then payoffs
        rank = {"close": 0, "new-topic": 1, "payoff": 2}[rel]
        cands.append((rank, i, seam, why))

    if not cands:
        return {}

    # Spread the marks: within a rank, prefer the candidates nearest the even division points of the film,
    # so a long film does not put all of its punctuation in one chapter.
    n = len(slides)
    budget = _budget(n)
    targets = [n * (k + 1) / (budget + 1) for k in range(budget)]

    chosen = {}
    for rank, i, seam, why in sorted(cands, key=lambda c: (c[0], min(abs(c[1] - t) for t in targets))):
        if len(chosen) >= budget:
            break
        if any(abs(i - j) < MIN_GAP for j in chosen):
            continue
        chosen[i] = {"type": seam["type"], "why": why}
    return chosen


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[2])
        return 2
    out_dir = argv[0]
    dry = "--dry-run" in argv
    path = os.path.join(out_dir, "storyboard.json")
    board = json.load(open(path, encoding="utf-8"))
    if str(board.get("meta", {}).get("renderer", "")).lower() not in ("remotion", "remotion-bespoke"):
        print("[seam_plan] not a remotion deck — the marked-seam vocabulary is remotion-only")
        return 0

    slides = board.get("slides", [])
    already = [i for i, s in enumerate(slides) if s.get("transition_in") or s.get("transition_style")]
    if already and not dry:
        print("[seam_plan] %d beat(s) already carry an authored seam (%s) — leaving them alone"
              % (len(already), ", ".join(str(i + 1) for i in already)))

    marks = plan(slides)
    if not marks:
        print("[seam_plan] no beat declares new-topic / payoff / close — every seam stays the default cut. "
              "That is a legitimate film (one unbroken argument), but check the `relation` field is set.")
        return 0

    for i, m in sorted(marks.items()):
        s = slides[i]
        tag = "would mark" if dry else "mark"
        if s.get("transition_in") or s.get("transition_style"):
            print("  beat %-3d skip (authored)" % (i + 1))
            continue
        print("  beat %-3d %s %-9s %s" % (i + 1, tag, m["type"], m["why"]))
        if not dry:
            s["transition_in"] = {"type": m["type"]}

    if not dry:
        json.dump(board, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[seam_plan] %d marked seam(s) of %d cut(s)%s"
          % (len(marks), max(0, len(slides) - 1), " (dry run — nothing written)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
