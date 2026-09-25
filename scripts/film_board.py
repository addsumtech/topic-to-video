#!/usr/bin/env python3
"""THE FILM'S BOARD — where each beat sits, so the film can say "we are back where we were".

WHY THIS EXISTS, AND WHY IT IS THIS SMALL. Measured against the peer library, the one capability this tier
genuinely lacked was a camera with SPACE: theirs poses cards in 3D and flies between them, ours pushes and
pulls. Three things in this repo decide what the honest answer to that is, and all three are already
measured or written down:

  * TYPE MUST NOT RIDE Z. `runtime/depth.tsx` measured it on this renderer: glyph edge strength 91 flat,
    56 under `perspective(1200px) translateZ(50px)` — a 38% loss that is plainly fuzzy, because a
    3D-composited layer is rasterized once at layout size and upscaled. A camera that flies through beats
    in true 3D softens every word in the film.
  * A MARK MEANS SOMETHING ONLY WHILE IT IS RARE. `seam_plan` budgets ~2-3 marked seams per film and
    `motion-grammar` refuses the novelty half of any transition list outright, on the recorded ground that
    the audience then notices the mechanism instead of the content. So a space expressed at EVERY cut is
    the thing this library has already decided not to ship.
  * A SPACE NOBODY REVISITS IS UNOBSERVABLE. If a film never comes back to a place, its layout exists only
    in the code. A viewer cannot see a map they are never shown twice; that is decoration by definition.

Put together, the observable core of "one continuous space" is exactly one claim, and it is one no seam in
this vocabulary can make: **this beat is the place we were at beat N.** `carry` carries an ELEMENT across a
cut, which is a different claim (that thing is still here, not this place is the same place). So the board
is derived for the whole film, and expressed only where a beat declares a return.

HOW THE POSITIONS ARE DERIVED. From the `relation` each beat already declares — no new authoring burden,
which matters because a layout somebody has to hand-maintain is a layout that goes stale (this session
retired two hand-written rosters for exactly that reason). Reading `relation` as the relationship to the
PREVIOUS beat:

    continuation / payoff / close   one step along the current row — the argument is still going
    new-topic                       a new row, back at the left — a chapter break is a move, not a step
    return                          the beat TAKES the position of the beat it returns to; it IS that place

A film with no `relation` anywhere is one unbroken row, which is a true picture of that film, and a return
in it still works.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# A RETURN TRAVELS EXACTLY ONE FRAME, ALONG ONE AXIS, AND THE REASON IS GEOMETRY RATHER THAN TASTE.
#
# The first build made the distance mean something: a return reaching back five cells travelled further than
# one reaching back two, capped so it never smeared. Rendered and measured, that is impossible. Two
# full-frame pictures offset by V leave a strip exactly |V| wide that neither of them covers — measured at
# left-edge luminance 9.5 against a centre of 74.6, a hard dark band sweeping across the frame, which reads
# as a curtain and not as a camera. `slide`/`push` escape it for one reason only: their separation is
# EXACTLY one frame, so the two tile. A diagonal does not tile either — offset by (W, H) and two corners are
# bare — so the direction quantises to the dominant board axis.
#
# What survives is the part that was always the claim: WHICH WAY the remembered place lies. The distance is
# not expressible in 12 frames between two pictures that are not tiles of one image, and pretending
# otherwise would have shipped the band.
def _rel(slide):
    return str((slide or {}).get("relation") or "").strip().lower()


def positions(slides):
    """[(col, row)] for every beat. Pure, total, and never raises on a malformed board."""
    out = []
    col, row = 0, 0
    for i, sl in enumerate(slides or []):
        rel = _rel(sl)
        if i == 0:
            out.append((0, 0))
            continue
        if rel == "return":
            tgt = _target_index(sl, i, len(slides or []))
            if tgt is not None and tgt < len(out):
                out.append(out[tgt])          # it IS that place — the same cell, not a neighbouring one
                col, row = out[tgt]
                continue
            # a malformed return still has to land somewhere; `validate` is what refuses it loudly
            col += 1
            out.append((col, row))
            continue
        if rel == "new-topic":
            col, row = 0, row + 1
        else:
            col += 1
        out.append((col, row))
    return out


def _target_index(slide, i, n):
    """The 0-based beat a return points at, or None when it is not a usable reference.

    `returns_to` is written 1-based because every other beat reference a film author writes is (the board's
    own numbering, the critic's findings, the keyframe files). Off-by-one here would be silent — the travel
    would simply go to the wrong place — so the conversion happens in ONE function and the tests probe its
    edges.
    """
    raw = (slide or {}).get("returns_to")
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    tgt = raw - 1
    if tgt < 0 or tgt >= i:                  # must point strictly BEFORE this beat
        return None
    return tgt


def refusals(slides):
    """[(beat_number, why)] — everything wrong with this board's returns, in the film author's numbering.

    Separated from the travel computation on purpose: the renderer must never be the thing that decides a
    board is invalid, or a bad board renders as a quiet no-op. `validate.py` calls this and errors.
    """
    out = []
    slides = slides or []
    pos = positions(slides)
    for i, sl in enumerate(slides):
        rel = _rel(sl)
        has = "returns_to" in (sl or {})
        if rel == "return" and not has:
            out.append((i + 1, "relation 'return' with no `returns_to` — a return has to name the beat it "
                               "returns to, or the seam has no place to travel towards"))
            continue
        if has and rel != "return":
            out.append((i + 1, "`returns_to` on a beat whose relation is %r — the field only means "
                               "something on a 'return', and a board that sets it elsewhere is saying "
                               "something the film will not draw" % (rel or "continuation")))
            continue
        if not has:
            continue
        raw = sl.get("returns_to")
        if isinstance(raw, bool) or not isinstance(raw, int):
            out.append((i + 1, "`returns_to` must be a beat NUMBER (1-based), got %r" % (raw,)))
            continue
        if raw - 1 < 0 or raw - 1 >= i:
            out.append((i + 1, "`returns_to: %d` does not point at an earlier beat (this is beat %d); a "
                               "film cannot return to a place it has not been" % (raw, i + 1)))
            continue
        if i == 0:
            out.append((1, "the first beat cannot be a return"))
            continue
        if pos[i] == pos[i - 1]:
            out.append((i + 1, "`returns_to: %d` is the place this film is already in (beat %d sits in the "
                               "same cell), so nothing would travel — a return to where you are is not a "
                               "return" % (raw, i)))
    return out


def travels(slides):
    """{beat_index: (dx, dy)} — the direction a return pans, as a UNIT step along one axis.

    `(1, 0)` means the content moves one frame RIGHT, which is what looking left at a place on the left
    looks like from behind the lens. Only beats declaring a usable return appear. The magnitude is not a
    free parameter: see the note above the constants.
    """
    slides = slides or []
    pos = positions(slides)
    out = {}
    for i, sl in enumerate(slides):
        if i == 0 or _rel(sl) != "return":
            continue
        tgt = _target_index(sl, i, len(slides))
        if tgt is None:
            continue
        cx, cy = pos[i - 1]
        tx, ty = pos[tgt]
        ddx, ddy = tx - cx, ty - cy
        if ddx == 0 and ddy == 0:
            continue                          # refused by `refusals`; never silently drawn as a jump
        # THE DOMINANT AXIS, and columns win a tie. A board step is one column or one row, and a return that
        # crosses both is mostly a horizontal reach: rows only advance on a chapter break, so a tie means
        # "one chapter back and one beat left", where the beat-level move is the one a viewer was following.
        if abs(ddx) >= abs(ddy):
            out[i] = (-1 if ddx > 0 else 1, 0)
        else:
            out[i] = (0, -1 if ddy > 0 else 1)
    return out


def describe(slides):
    """One line per return, for a human reading a plan. Never part of a gate's verdict."""
    pos, tv = positions(slides), travels(slides)
    lines = []
    for i in sorted(tv):
        tgt = _target_index(slides[i], i, len(slides))
        dx, dy = tv[i]
        where = {(1, 0): "rightward (the place is to the LEFT)", (-1, 0): "leftward (the place is to the RIGHT)",
                 (0, 1): "downward (the place is ABOVE)", (0, -1): "upward (the place is BELOW)"}[(dx, dy)]
        lines.append("beat %d returns to beat %d at cell %s (from %s) — the film pans %s"
                     % (i + 1, tgt + 1, pos[i], pos[i - 1], where))
    return lines


if __name__ == "__main__":
    import json
    board = json.load(open(sys.argv[1], encoding="utf-8"))
    sl = board.get("slides") or []
    bad = refusals(sl)
    for n, why in bad:
        print("  beat %d: %s" % (n, why))
    for line in describe(sl):
        print("  " + line)
    print("[film_board] %d beat(s), %d return(s), %d refusal(s)" % (len(sl), len(travels(sl)), len(bad)))
    sys.exit(1 if bad else 0)
