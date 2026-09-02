#!/usr/bin/env python3
"""Author the film's LIGHT as an argument, not a timer — stamp a per-beat ground onto the storyboard.

    python3 scripts/light_plan.py <out_dir>                          # propose an arc, write nothing
    python3 scripts/light_plan.py <out_dir> --write --accept-risk    # stamp it anyway (read below first)

WHAT THIS PASS WAS MEASURED TO DO TO A REAL FILM, and why `--write` now needs a flag someone has to type.
Run on the shipped 30-beat film and rendered, the arc moved the numbers exactly as designed — luminance range
0.079 -> 0.895, light arc 0.0% -> 14.9%, both into the reference band. Then the frames were compared side by
side against the delivered film, and THREE OF SIX SAMPLED BEATS WERE WORSE:

  * the title card went from white type on near-black to black type on a washed pale ground — it lost its
    impact and read as unfinished;
  * a deliberately sparse terminal beat put its single line of type on a large WHITE field, where the
    emptiness is more glaring, not less;
  * a beat whose register title already sat low enough to touch the burned caption became unreadable: two
    whites on near-black are still separable, the same two on a mid-blue ground are mush.

THE CAUSE IS STRUCTURAL, not a tuning problem. This pass assigns a ground from the ARGUMENT (where the
content plan says the film turns) and knows nothing about whether the register on that beat was COMPOSED for
a light ground. `GROUND_FOLLOWS_MEASURED` checks that a declared ground reaches the caption band, the content
field and a fraction of moved pixels — it does not check that the frame still holds together. A register can
follow a ground perfectly and be a worse picture on it.

So this proposes, and a human looks. `--write` alone refuses; `--write --accept-risk` says you have read the
above and will open every re-grounded beat.

WHY THIS EXISTS. `runtime/light.tsx` can re-ground any beat and `render_remotion.py` now forwards the fields,
so a film CAN have light. Nothing made one. A capability nothing reaches is indistinguishable from a
capability that was never built, and this repo has shipped that shape before — which is why the whole library
measured a median luminance range of 0.013 against Apple's 0.270 while every register was working exactly as
designed.

THE ARC FOLLOWS THE ARGUMENT. A change of exposure marks a change of claim: the film re-grounds where the
content plan says it turns (`relation: new-topic`), lifts to its brightest world on the beats it calls
`payoff`, and comes home on `close`. That is the difference between light that means something and light that
is on a rotation — and it is also the difference the delivery gate measures. `film_energy_qa`'s arc axis counts
the fraction of adjacent seconds whose exposure moves, precisely because appending four seconds of a blank
white rectangle to a film once took its luminance RANGE from 0.097 to 0.910 while nothing in it changed.

WHAT IT EMITS. Ground INDICES, not colours: `filmGrounds()` derives [native, opposite key, chroma(accent),
chroma(accent2)] for every film, so 0..3 mean something with zero authoring and stay inside the palette the
film already owns. A director who wants a specific world writes a name or a hex on the beat and this pass
leaves it alone — it fills silence, it never overrules.

WHAT IT REFUSES. A beat whose register does not follow a declared ground (measured, `GROUND_FOLLOWS_MEASURED`
in runtime/shotLuma.ts) is skipped and counted out loud. Stamping one would put a dark subtitle over black
pixels — the register paints its own ground and the caption pick believes the declaration.
"""
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SHOTLUMA = os.path.join(_ROOT, "remotion", "src", "runtime", "shotLuma.ts")

NATIVE, OPPOSITE, CHROMA_A, CHROMA_B = 0, 1, 2, 3
# The rotation a new section walks. It starts on the film's OPPOSITE key so the first turn is the largest
# available step, then moves through the two chromatic grounds; `native` is reserved for home and the close.
SECTION_CYCLE = (OPPOSITE, CHROMA_A, OPPOSITE, CHROMA_B)


def ground_followers():
    """Registers measured to follow a declared ground — PARSED from shotLuma.ts, never restated.

    Fails loud rather than returning an empty set: an empty set would silently skip every beat and report a
    film with no light as "nothing to do", which is the failure this whole pass exists to end.
    """
    src = open(_SHOTLUMA, encoding="utf-8").read()
    m = re.search(r"GROUND_FOLLOWS_MEASURED[^=]*=\s*new Set\(\[(.*?)\]\)", src, re.S)
    if not m:
        raise RuntimeError(
            "GROUND_FOLLOWS_MEASURED not found in %s — this pass decides which beats may be re-grounded from "
            "that measured set, and guessing instead would put dark subtitles over black pixels." % _SHOTLUMA)
    names = set(re.findall(r"'([A-Za-z][A-Za-z0-9_]*)'", m.group(1)))
    if not names:
        raise RuntimeError("GROUND_FOLLOWS_MEASURED parsed as empty — refusing to plan light against nothing")
    return names


def plan(slides, followers):
    """[{index, shot, relation, energy, ground|key, why}] for the beats this pass would stamp."""
    out, section, cycle_at = [], -1, 0
    for s in slides:
        rel = (s.get("relation") or "").strip().lower()
        energy = (s.get("energy") or "").strip().lower()
        shot = s.get("shot")
        idx = int(s.get("index", 0))
        if rel == "new-topic" or section < 0:
            section += 1
            cycle_at = section
        if s.get("ground") is not None or s.get("key") is not None:
            out.append({"index": idx, "shot": shot, "skip": "the director already authored this beat"})
            continue
        if shot not in followers:
            out.append({"index": idx, "shot": shot,
                        "skip": "register does not follow a declared ground (measured)"})
            continue
        # WHERE THE LIGHT MOVES, and why.
        if rel == "close":
            g, why = NATIVE, "close — the film comes home to its own ground"
        elif rel == "payoff" or energy == "peak":
            g, why = CHROMA_A, "payoff — the brightest world the film owns"
        elif rel == "new-topic":
            g = NATIVE if section == 0 else SECTION_CYCLE[(cycle_at - 1) % len(SECTION_CYCLE)]
            why = "section %d opens — a change of claim gets a change of exposure" % section
        else:
            # A continuation keeps its section's ground: light marks the TURN, and a film whose exposure
            # changes every beat is a rotation, not an argument.
            g = NATIVE if section == 0 else SECTION_CYCLE[(cycle_at - 1) % len(SECTION_CYCLE)]
            why = "continues section %d" % section
        out.append({"index": idx, "shot": shot, "ground": g, "why": why, "section": section})
    return out


def apply(board, rows):
    n = 0
    by = {int(s.get("index", i)): s for i, s in enumerate(board.get("slides") or [])}
    for r in rows:
        if "ground" not in r:
            continue
        s = by.get(r["index"])
        if s is None:
            continue
        s["ground"] = r["ground"]
        n += 1
    return n


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: light_plan.py <out_dir> [--write]")
        return 2
    out_dir = os.path.abspath(argv[0])
    path = os.path.join(out_dir, "storyboard.json")
    board = json.load(open(path, encoding="utf-8"))
    slides = board.get("slides") or []
    followers = ground_followers()
    rows = plan(slides, followers)

    stamped = [r for r in rows if "ground" in r]
    skipped = [r for r in rows if "skip" in r]
    changes = sum(1 for a, b in zip(stamped, stamped[1:]) if a["ground"] != b["ground"])
    print("[light_plan] %d beat(s): %d would be grounded, %d skipped, %d exposure change(s)"
          % (len(rows), len(stamped), len(skipped), changes))
    for r in rows:
        if "skip" in r:
            print("   %2d %-22s SKIP  %s" % (r["index"], r["shot"] or "?", r["skip"]))
        else:
            print("   %2d %-22s ground %d  %s" % (r["index"], r["shot"] or "?", r["ground"], r["why"]))
    print("[light_plan] A PROPOSAL, not a plan. Open every beat above before shipping it: this pass reads "
          "the argument, not the composition, and a register can follow a ground perfectly and be a worse "
          "picture on it.")
    if changes < 2:
        # Said out loud rather than silently accepted: one exposure change is not an arc, and the delivery
        # gate measures the arc, not the range.
        print("[light_plan] WARNING only %d change(s) — that is a re-ground, not an arc. Most beats are "
              "continuations of one section, or their registers do not follow a ground." % changes)
    if "--write" in argv and "--accept-risk" not in argv:
        print("[light_plan] REFUSING to write. Rendered on a real film this arc made three of six sampled "
              "beats WORSE while moving every number the right way (see this file's header). It assigns a "
              "ground from the argument and cannot know whether the register on that beat was composed for "
              "one. Re-run with `--write --accept-risk` and open every beat it re-grounds.")
        return 2
    if "--write" in argv:
        n = apply(board, rows)
        json.dump(board, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("[light_plan] stamped %d beat(s) into %s" % (n, path))
    else:
        print("[light_plan] nothing written — `--write --accept-risk` stamps it, after you have "
              "opened the beats above")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
