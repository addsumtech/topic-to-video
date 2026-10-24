#!/usr/bin/env python3
"""Plan the film's MARKED seams and its MOTIVATED camera moves, and write them into the storyboard.

  python3 scripts/seam_plan.py <out_dir>            # plan and write `transition_in` + `camera` on the beats
  python3 scripts/seam_plan.py <out_dir> --dry-run  # print the plan, change nothing
  python3 scripts/seam_plan.py <out_dir> --no-camera # seams only

WHY THIS EXISTS. The remotion tier already had the whole apparatus: `Film.tsx` implements five kinetic
seams including `carry`, a collapse-to-line match-cut that reads as CONTINUITY rather than a swap;
`render_remotion.py` maps a scene's `transition_in` onto them; `Film.tsx` guards them against a
luminance flash. And a delivered 35-beat film used NONE of it. All 34 of its seams were the default
cross-fade, because nothing in the authoring path ever wrote the field — the storyboard did not contain
the key at all. A capability that never reaches the artifact is indistinguishable from one that was
never built, and this is the second time that exact shape has cost a delivery.

So the intent the storyboard ALREADY carries is translated into seams here. Every beat declares a
`relation` to the one before it; that is the argument, and a cut is a claim about the same relationship:

  new-topic  → `push`      the camera moves on to a different subject — a chapter break (eased, shutter-blurred)
  payoff     → `dissolve`  setup and result share the screen for a moment: THIS became THAT
  close      → `focus`     attention lets go of one thing and settles on the last — continuity in depth

(`clock` and `carry` used to be the new-topic and close words. A benchmark film read both as the cheapest moments
in it: the clock is the stock radial wipe a slideware transition menu offers, and the carry collapses a photograph
to a line like an old TV switching off. Both stay in the vocabulary for an author who means them.)

...and across a dark↔light boundary, where the plane seams are refused, each relation keeps its claim in a
seam that cannot flash: a `payoff` becomes `focus`, a `new-topic` becomes `through-dark` (out through black
and in again, which is what a chapter break is saying), everything else `focus`.

`continuation` is marked only by the one seam that reads as no seam at all — a CONTAINER, when the two beats'
registers draw the same anchor (scripts/carry_anchors.py): the element stays on screen and is re-framed, which is
the strongest continuity claim a cut can make. Otherwise most cuts should be invisible; a marked seam only means
something while it stays rare, which is why the budget is 2 on a short film and 3 on a long one, never per-chapter.

THE ANCHORED SEAMS take precedence where the beats can carry them, each at most once per film (a move mastered,
not a menu) — remotion/src/seams.tsx draws them and references/motion-grammar.md says when each is right:

  shared anchor (A and B draw the same id) → `container`       this IS that, re-framed
  new-topic, A draws a `screen`/`window`   → `through-window`  the next subject is inside this screen
  new-topic, A draws any other anchor      → `grow`            the next subject opens out of this thing
  payoff that is the climax or at `peak`   → `punch`           the one hard landing

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
import copy
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shot_director import shot_luma                                   # noqa: E402

_SHOTLUMA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "remotion", "src", "runtime", "shotLuma.ts")
_GROUND_TOKEN = None

# A film's own shots declare their ground (scripts/workshop.py GROUND) — the renderer merges the same declaration
# (remotion/src/registry.ts), so the planner must too, or it judges their seams on nothing. A film's own
# objects and shots also declare their PROVENANCE, which the push-camera's detail check reads alongside the
# library's own table. Both installed by `install_workshop` — the one door `main` and `shot_director.main`
# both go through — and cleared by `clear_workshop` when the film-scoped work is done.
_EXTRA_GROUNDS = {}
_EXTRA_PROVENANCE = {}


def install_workshop(out_dir):
    """Read this film's workshop declarations (scripts/workshop.py) into the planner's module state. A bare
    ground token normalises to a one-element list, matching `_ground_tokens()`'s own shape; a '#hex' stays a
    string, which `dna_ground_y` resolves with no DNA at all."""
    import workshop as _ws
    _EXTRA_GROUNDS.clear()
    for n, g in _ws.grounds(out_dir).items():
        if isinstance(g, str) and not g.startswith("#"):
            g = [g]
        if g:
            _EXTRA_GROUNDS[n] = g
    _EXTRA_PROVENANCE.clear()
    _EXTRA_PROVENANCE.update(_ws.provenances(out_dir))


def clear_workshop():
    """The other half of `install_workshop` — call from a `finally`, so a film's declarations never outlive
    the run that installed them."""
    _EXTRA_GROUNDS.clear()
    _EXTRA_PROVENANCE.clear()


def _ground_tokens():
    """DNA_GROUND_TOKEN — which DNA token(s) each shot MEASURABLY paints its ground from."""
    global _GROUND_TOKEN
    if _GROUND_TOKEN is None:
        _GROUND_TOKEN = {}
        try:
            body = open(_SHOTLUMA, encoding="utf-8").read().split("DNA_GROUND_TOKEN", 1)[1]
            body = body.split("{", 1)[1].split("};")[0]
            # A '#rrggbb' VALUE IS A GROUND, NOT A TOKEN — PaperSlot prints on its own stock whenever the
            # film's ground is too dark to pass for paper, which is every shipped preset. The old pattern
            # accepted only [a-zA-Z0-9_] inside the quotes, so that entry matched nothing and the shot
            # dropped out of this map silently — and a shot missing here is a seam judged on SHOT_LUMA's
            # three buckets instead of a luminance the table knows exactly.
            for name, val in re.findall(r"(\w+):\s*(\[[^\]]*\]|'#?[a-zA-Z0-9_]+')", body):
                lit = re.fullmatch(r"'(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})'", val)
                if lit:
                    _GROUND_TOKEN[name] = lit.group(1)          # a literal colour
                    continue
                toks = re.findall(r"'([a-zA-Z0-9_]+)'", val)
                if toks:
                    _GROUND_TOKEN[name] = toks
        except Exception:
            _GROUND_TOKEN = {}
    return _GROUND_TOKEN


_DNA_TSX = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "remotion", "src", "runtime", "dna.tsx")
_PRESETS = None


def _resolve_dna(dna):
    """A film's `meta.design_dna` may be a token OBJECT or a PRESET NAME — the renderer accepts both
    (`coerceDna` in runtime/dna.tsx). The planner only handled the object and raised AttributeError on the
    string, so a film on any of the shipped directions fell into the caller's except-branch and silently
    got no seams and no camera at all. Worse than a crash: the renderer WOULD have resolved that preset, so
    treating it as "no DNA" would put the planner back out of step with the guard it exists to mirror.
    Resolved from the same table the renderer reads.
    """
    global _PRESETS
    if isinstance(dna, dict) or dna is None:
        return dna
    if not isinstance(dna, str):
        return None
    if _PRESETS is None:
        import re as _re
        src = open(_DNA_TSX, encoding="utf-8").read()
        consts = {}
        for name, body in _re.findall(r"export const ([A-Z_]+_DNA)[^=]*=\s*\{(.*?)\n\};", src, _re.S):
            consts[name] = {k: v for k, v in _re.findall(r"(\w+):\s*'([^']*)'", body)}
        m = _re.search(r"export const DNA_PRESETS[^{]*\{(.*?)\n\};", src, _re.S)
        _PRESETS = {}
        if m:
            for key, const in _re.findall(r"'?([\w-]+)'?:\s*([A-Z_]+_DNA)", m.group(1)):
                if const in consts:
                    _PRESETS[key] = consts[const]
    return _PRESETS.get(dna)


def _rel_lum(hex_colour):
    """sRGB relative luminance of a #rgb / #rrggbb, or None if it is not a plain colour."""
    import re
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", str(hex_colour or "").strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    def ch(v):
        c = int(v, 16) / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(h[0:2]) + 0.7152 * ch(h[2:4]) + 0.0722 * ch(h[4:6])


def dna_ground_y(shot, dna):
    """The shot's ACTUAL ground luminance under this film's DNA — the Python mirror of dnaGroundY.

    SHOT_LUMA describes a register on its OWN default palette, which is the right answer only for a film
    that has no DNA. Every bespoke-shot film HAS one, and under it a register paints from a DNA token: on a
    cream survey direction, thirty registers that ship dark by default all render cream. Judging the seam on
    SHOT_LUMA therefore invented luminance crossings that are not on the screen — and, after the table was
    corrected, changed the plan for a beat where the picture had not changed at all.
    """
    toks = _ground_tokens().get(shot) or _EXTRA_GROUNDS.get(shot)
    # A literal ground resolves with no DNA at all — that is what makes it literal.
    if isinstance(toks, str):
        return _rel_lum(toks)
    if not dna or not toks:
        return None
    ys = [_rel_lum(dna.get(t)) for t in toks]
    if any(y is None for y in ys):
        return None
    return sum(ys) / len(ys)


def ground_gap(a, b):
    """Perceptual (display-encoded) distance between two grounds — the number a seam judges on."""
    if a is None or b is None:
        return None
    return abs(a ** (1 / 2.2) - b ** (1 / 2.2))

# relation → the cut that makes that claim. `continuation` is deliberately absent: it is the one relation
# whose honest cut is no cut at all.
SEAM_BY_RELATION = {
    "new-topic": {"type": "push", "direction": "from-right"},
    "payoff": {"type": "dissolve"},
    "close": {"type": "focus"},
}
# THE SEAMS ALLOWED TO CROSS A DARK↔LIGHT BOUNDARY, and why each is allowed.
#
# `carry` earns it by drawing a neutral bridge line — the line IS the luminance dip, so the eye tracks it
# instead of being flashed. `focus` earns it differently and more cheaply: a rack focus redistributes light
# without adding or removing any, so it cannot flash by construction, whatever the two grounds are.
#
# `focus` is also the only seam in this vocabulary that happens in DEPTH rather than in the plane, which is
# the gap that put it here. Measured against the video-shotcraft library (218 shots, same stack), three of
# its six hand-off recipes are built on depth and this tier had none — every seam we shipped moved pixels
# sideways or faded them, and a film whose cuts are all planar reads as pages replacing pages.
CROSSING_SEAM = {"type": "focus"}
# A CROSSING seam on a `payoff`, where a dissolve would be forced back to a plain fade: the argument lands,
# and the focus carrying from one frame to the next is a stronger claim than a cross-fade anyway.
CROSSING_PAYOFF_SEAM = {"type": "focus"}
# ...and a CROSSING `new-topic`, which used to become the carry along with everything else. A chapter break
# is the one relation that means "we are leaving this behind", and `through-dark` says exactly that in the
# same register the relation is in: the leaving beat recedes and its light goes out, the frame passes
# through black, the next subject comes forward out of it. It earns the crossing exemption the same way the
# other two do and more strongly — the two beats never carry light at the same time, so there is no instant
# where a bright frame is added to a dark one. A bridge line is a claim of CONTINUITY, which is the opposite
# of what a chapter break across a light boundary is claiming.
CROSSING_NEW_TOPIC_SEAM = {"type": "through-dark"}

# Which anchors a through-window can go INTO: a surface that shows something, or a WORD (a glyph anchor — the window
# is its letterforms). A card or a figure is a thing, and pushing into a thing is a grow's claim, not a window's.
WINDOW_ANCHORS = ("screen", "window", "word")

MIN_GAP = 5          # beats between two marked seams, so a mark stays punctuation
_LUM_RANK = {"dark": 0, "mid": 1, "light": 2}


def _budget(n):
    """~2 on a short film, 3 on a long one. A mark means something only while it is rare."""
    return 2 if n < 20 else 3


def _harsh_gap():
    """The seam guard's flash threshold, READ from runtime/shotLuma.ts rather than re-typed.

    "The same threshold Film.tsx judges on" was a comment, and a comment is not a mechanism: three files
    carried the literal 0.34 and nothing would have failed if one of them had been tuned. It is one exported
    constant now, and this reads it — so a planner that disagrees with the renderer about what a flash is
    becomes impossible rather than merely unlikely."""
    m = re.search(r"export const HARSH_GROUND_GAP\s*=\s*([0-9.]+)\s*;",
                  open(_SHOTLUMA, encoding="utf-8").read())
    if not m:
        raise SystemExit("[seam_plan] runtime/shotLuma.ts no longer exports HARSH_GROUND_GAP — the seam "
                         "planner cannot mirror a guard whose threshold it cannot read")
    return float(m.group(1))


HARSH_GAP = _harsh_gap()

_FILM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "Film.tsx")


def film_cannot_flash():
    """The seams Film.tsx's luminance guard lets across a dark/light boundary — READ from its CANNOT_FLASH set, so
    the planner and the validator cannot disagree with the guard about which marks survive a crossing."""
    m = re.search(r"const CANNOT_FLASH = new Set\(\[([^\]]*)\]\)", open(_FILM, encoding="utf-8").read())
    if not m:
        raise SystemExit("[seam_plan] Film.tsx no longer declares CANNOT_FLASH — the planner cannot mirror its guard")
    return set(re.findall(r"'([a-z-]+)'", m.group(1)))


def _crosses(prev_shot, shot, dna=None):
    """Would Film.tsx force this seam back to a fade? (its luminance guard, mirrored exactly)

    Perceptual first — resolving each shot's ground through the film's DNA, which is what the renderer
    actually draws — and only falling back to the coarse dark/mid/light bucket when a ground does not
    resolve, which is the same order of preference the renderer uses.
    """
    gap = ground_gap(dna_ground_y(prev_shot, dna), dna_ground_y(shot, dna))
    if gap is not None:
        return gap >= HARSH_GAP
    a, b = _LUM_RANK.get(shot_luma(prev_shot), 1), _LUM_RANK.get(shot_luma(shot), 1)
    return abs(a - b) >= 2


# A GROW IS ITS GROUND. The shape that opens out of the anchor is filled with the arriving beat's ground, so between
# two beats on one ground it is invisible: rendered on the seam probe (two paper beats), the anchor simply faded out
# and the frame sat empty until the next beat rose in. Below this display-encoded difference two grounds are taken
# as one. The number is a floor chosen here, not a measured threshold of visibility — it only has to separate
# "the same token" from "a different ground", and every declared key or ground counts as different outright.
GROW_MIN_GAP = 0.05


def _grounds_differ(prev, cur, dna):
    """Do these two beats stand on visibly different grounds? A beat-level `key`/`ground` that differs decides it;
    otherwise the two registers' own grounds under the film's DNA, as the luminance guard reads them."""
    dk = lambda s: (s.get("key"), json.dumps(s.get("ground"), sort_keys=True))      # noqa: E731
    if (prev.get("key") or prev.get("ground") is not None or cur.get("key") or cur.get("ground") is not None) \
            and dk(prev) != dk(cur):
        return True
    gap = ground_gap(dna_ground_y(prev.get("shot"), dna), dna_ground_y(cur.get("shot"), dna))
    return gap is not None and gap >= GROW_MIN_GAP


def _anchored(prev, cur, rel, crossing, used, exempt, out_dir=None, dna=None):
    """The anchored seam this cut can carry, as (seam, why) — or None. Each word at most once per film (`used`)."""
    import carry_anchors as _ca
    a_shot, b_shot = prev.get("shot"), cur.get("shot")
    if crossing:
        # only a word the guard lets across a dark/light boundary survives one; the rest would render as a fade
        allowed = exempt
    else:
        allowed = {"container", "grow", "through-window", "punch"}
    if "container" in allowed and "container" not in used and rel in ("continuation", "payoff", "close"):
        common = _ca.shared(a_shot, b_shot, out_dir)
        if common:
            return ({"type": "container", "carry": common[0]},
                    "both beats draw the '%s' — it stays on screen and is re-framed: this IS that" % common[0])
    if rel == "new-topic":
        a = _ca.anchors_of(a_shot, out_dir) or {"ids": set()}
        wins = [x for x in WINDOW_ANCHORS if x in a["ids"]]
        if wins and "through-window" in allowed and "through-window" not in used:
            return ({"type": "through-window", "carry": wins[0]},
                    "the next subject is inside the %s — the camera goes through it" % wins[0])
        if a["ids"] and "grow" in allowed and "grow" not in used and _grounds_differ(prev, cur, dna):
            aid = sorted(a["ids"])[0]
            return ({"type": "grow", "carry": aid}, "the next subject opens out of the %s" % aid)
    if rel == "payoff" and "punch" in allowed and "punch" not in used and (
            cur.get("climax") is True or str(cur.get("energy") or "").lower() == "peak"):
        return ({"type": "punch"}, "the climax lands hard — the film's one push cut")
    return None


def _exposure(slide, dna):
    """'light' / 'dark' when a beat's exposure is known from its declaration or the film's DNA, else None. A
    declared `key` is the exposure; a declared `ground` is not resolved here (it may be any colour), so None."""
    k = slide.get("key")
    if k in ("light", "dark"):
        return k
    if slide.get("ground") is not None:
        return None
    y = _rel_lum((dna or {}).get("bg")) if isinstance(dna, dict) else None
    return None if y is None else ("light" if y > 0.18 else "dark")


def crosses_beats(prev, cur, dna=None):
    """`_crosses` for two BEATS: a beat's declared `key` re-lights it whatever its register paints, so two beats on
    opposite keys cross even when their registers would not. Measured on the seam probe: a grow planned from a dark
    beat into a `key: light` beat — `_crosses` reads registers only and called it safe, and Film drew a fade."""
    a, b = _exposure(prev, dna), _exposure(cur, dna)
    if a and b and a != b and (prev.get("key") or cur.get("key")):
        return True
    return _crosses(prev.get("shot"), cur.get("shot"), dna)


def plan(slides, dna=None, out_dir=None):
    dna = _resolve_dna(dna)
    """→ {beat_index: {"type": ..., "why": ..., "carry"?: ...}} for the beats that should carry a marked seam.

    Beat 0 is never a candidate: there is no seam before the first shot.
    """
    try:
        exempt = film_cannot_flash()
    except SystemExit:
        exempt = set()
    cands = []
    for i in range(1, len(slides)):
        rel = (slides[i].get("relation") or "").strip().lower()
        seam = SEAM_BY_RELATION.get(rel)
        if not seam and rel != "continuation":
            continue
        crossing = crosses_beats(slides[i - 1], slides[i], dna)
        if not seam:
            # a CONTINUATION is marked only by a container between two beats that draw the same anchor
            import carry_anchors as _ca
            common = _ca.shared(slides[i - 1].get("shot"), slides[i].get("shot"), out_dir)
            if common and (not crossing or "container" in exempt):
                cands.append((3, i, {"type": "container", "carry": common[0]},
                              "both beats draw the '%s' — it stays on screen and is re-framed: this IS that"
                              % common[0], rel))
            continue
        if crossing:
            # Two seams survive the luminance guard, and they are not interchangeable. A `payoff` is the beat
            # where the argument lands, so the crossing form of it should still say "this became that":
            # `focus` does — the eye rides the focal plane from one frame into the next — and it cannot flash,
            # because racking focus redistributes light rather than adding any. Everything else that crosses
            # becomes the carry, whose bridge line IS the dip. Before this, every crossing seam collapsed to
            # the same carry whatever it was claiming.
            seam = dict({"payoff": CROSSING_PAYOFF_SEAM,
                         "new-topic": CROSSING_NEW_TOPIC_SEAM}.get(rel, CROSSING_SEAM))
            why = {"payoff": "payoff across a dark/light boundary — focus relay carries the eye through the "
                             "cut without a flash",
                   "new-topic": "new-topic across a dark/light boundary — the flight leaves through black, "
                                "which is what a chapter break claims anyway"}.get(
                rel, "%s across a dark/light boundary — carry is the seam whose bridge line IS the dip" % rel)
        else:
            seam = dict(seam)
            why = {"new-topic": "opens outward onto a different subject",
                   "payoff": "setup and result share the screen: this became that",
                   "close": "the last move reads as continuity, not one more swap"}[rel]
        # `close` is the film's ending and always the strongest candidate; then chapter breaks; then payoffs
        rank = {"close": 0, "new-topic": 1, "payoff": 2}[rel]
        cands.append((rank, i, seam, why, rel))

    if not cands:
        return {}

    # Spread the marks: within a rank, prefer the candidates nearest the even division points of the film,
    # so a long film does not put all of its punctuation in one chapter.
    n = len(slides)
    budget = _budget(n)
    targets = [n * (k + 1) / (budget + 1) for k in range(budget)]

    chosen = {}
    used = set()
    for rank, i, seam, why, rel in sorted(cands, key=lambda c: (c[0], min(abs(c[1] - t) for t in targets))):
        if len(chosen) >= budget:
            break
        if any(abs(i - j) < MIN_GAP for j in chosen):
            continue
        if seam["type"] == "container" and "container" in used:
            continue                                   # a continuation container is a once-per-film claim
        # AN ANCHORED SEAM WHERE THE BEATS CAN CARRY ONE, the relation's own word where they cannot
        crossing = crosses_beats(slides[i - 1], slides[i], dna)
        better = None if seam["type"] == "container" else _anchored(
            slides[i - 1], slides[i], rel, crossing, used, exempt, out_dir, dna)
        if better:
            seam, why = better
        used.add(seam["type"])
        chosen[i] = dict(seam, why=why)
    return chosen


# ── the camera ──────────────────────────────────────────────────────────────────────────────────────────
# A camera move needs a CAUSE. The tier's previous camera was a film-wide sinusoidal drift with no
# relationship to anything being said, and motion with no cause reads as a wobble the moment a viewer
# notices it — which is what happened, and why it was switched off entirely. Switching it off was an
# over-correction: the fix for noise is removing the noise, not removing the camera.
#
# So a move is derived from what the beat is FOR, and only for the beats that are for something:
#
#   payoff  -> push   the beat where the argument lands. Look closer at what is on screen.
#   close   -> pull   the last beat. Here is the whole of it.
#   opener  -> pull   the establishing beat, for the same reason, from the other end of the film.
#
# Everything else gets the BED, not a hold. This comment used to read "everything else HOLDS — a film where
# the camera is always moving has no camera at all", and that absolutism conflated two different things.
# What kills punctuation is uniform AMPLITUDE, not uniform presence: the reference launch films' cameras
# are never dead, and their marked moves still read, because the ever-present layer sits far below them.
# So the hierarchy is now explicit — Film.tsx gives every unauthored beat a barely-perceptible lateral
# drift (depth.tsx bedPan: monotone, edge-safe, caption-bounded, 45% of the cap against a move's 75%,
# themed films only, `meta.camera_bed: false` to refuse), and THIS planner still owns the moves that mean
# something. The budget below stays small for exactly that reason: these are the punctuation.
CAMERA_BY_RELATION = {"payoff": "push", "close": "pull"}
# NO AMOUNT. The planner used to write 0.045 on every move — a number chosen once at 16:9 and then clamped
# everywhere else, so the same authored intent was 45% of the available headroom at 16:9 and 96% of it at
# 9:16. Left unset, SceneCamera derives three-quarters of whatever the caption band can absorb at THIS
# aspect and THIS drift, which is the same gesture everywhere. An author who wants a specific amount still
# sets one and it still wins.
CAMERA_AMOUNT = None
CAMERA_MIN_GAP = 4             # beats between two moving beats


def plan_camera(slides):
    """→ {beat_index: {"move": ..., "why": ...}} for the beats that should move."""
    n = len(slides)
    if n < 6:
        return {}
    cands = []
    for i, sl in enumerate(slides):
        rel = (sl.get("relation") or "").strip().lower()
        move = CAMERA_BY_RELATION.get(rel)
        if move is None and i == 0:
            move, rel = "pull", "opener"          # the establishing beat opens outward
        if not move:
            continue
        why = {"push": "the beat where the argument lands — look closer at what is on screen",
               "pull": "here is the whole of it"}[move]
        cands.append(({"close": 0, "opener": 1, "payoff": 2}.get(rel, 3), i, move, why))

    # A PUSH NEEDS SOMETHING TO PUSH INTO. The planner used to rank on relation and beat index alone, so a
    # "look closer" push could land on a beat whose frame is two ruled rows of text — magnifying nothing,
    # which is a move a viewer reads as a wobble rather than as attention. A register's PROVENANCE says
    # what world its form comes from, and the image-, drawing- and instrument-bearing worlds are the ones
    # that reward being looked at closely; an editorial or product-UI frame is already as legible as it
    # will get. A pull is unaffected — pulling back to show the whole of something works on any frame.
    DETAIL = {"photographic", "survey-archive", "scientific", "industrial", "natural-world",
              "craft-handmade", "data-viz"}

    def _rewards_a_push(shot):
        # A WORKSHOP SHOT'S OWN PROVENANCE, before the library's table — `shot_director.PROVENANCE` only
        # ever knew the library's registers, so a push onto a film-built shot always fell back to "unknown
        # provenance is not a reason to refuse the move" and got the detail-bearing budget for free.
        if shot in _EXTRA_PROVENANCE:
            return _EXTRA_PROVENANCE[shot] in DETAIL
        try:
            from shot_director import PROVENANCE
            return PROVENANCE.get(shot) in DETAIL
        except Exception:
            return True                      # unknown provenance is not a reason to refuse the move

    # A LONG BEAT HOLDS, AND A HOLD IS WHERE A MOVE BELONGS. Ranking on `relation` alone never asked whether
    # a beat actually needed one: measured on a delivered film, 25% of its running time was a frozen picture,
    # and not one of the eight longest-held beats had a camera. A register finishes revealing well before a
    # long beat ends, so DURATION relative to the film's own median is the signal available before a render.
    # It ranks BELOW the argument-driven moves — a push still means "look closer", not "this beat was long" —
    # and only spends budget the relations did not.
    durs = sorted(float(sl.get("duration") or 0) for sl in slides)
    med = durs[len(durs) // 2] if durs else 0
    if med > 0:
        for i, sl in enumerate(slides):
            if i == 0 or any(c[1] == i for c in cands):
                continue
            if float(sl.get("duration") or 0) >= med * 1.35 and _rewards_a_push(sl.get("shot")):
                cands.append((3, i, "push", "a long hold on a frame with something to look closer at"))

    budget = max(2, min(5, round(n / 8)))
    chosen = {}
    # within a rank, a push onto a detail-bearing frame outranks a push onto a text one
    cands.sort(key=lambda c: (c[0], 0 if (c[2] != "push" or _rewards_a_push(slides[c[1]].get("shot"))) else 1, c[1]))
    for rank, i, move, why in sorted(cands, key=lambda c: (c[0], 0 if (c[2] != "push" or _rewards_a_push(slides[c[1]].get("shot"))) else 1, c[1])):
        if len(chosen) >= budget:
            break
        if any(abs(i - j) < CAMERA_MIN_GAP for j in chosen):
            continue
        chosen[i] = {"move": move, "why": why}
    return chosen


def plan_handoffs(slides, cams, marks):
    """The planned moves that should HAND OFF across their cut (Film.tsx HandoffCamera) → [beat_index].

    A push that comes to rest before every cut is a camera that stops for each edit, and across a CONTINUATION —
    the same thought, one more beat of it — that stop is the seam showing. So a planned push or pull hands its
    velocity to the next beat when that beat continues the thought, plans no move of its own and authors none (one
    camera channel per beat), sits across an UNMARKED cut (a marked seam moves the frame itself), and neither beat
    is a stage (which moves its own camera)."""
    import stage_runs as _sr
    out = []
    for i, c in sorted(cams.items()):
        if c.get("move") not in ("push", "pull") or i + 1 >= len(slides):
            continue
        a, b = slides[i], slides[i + 1]
        if (str(b.get("relation") or "").strip().lower() != "continuation" or (i + 1) in cams or b.get("camera")
                or a.get("camera") or (i + 1) in marks or b.get("transition_in") or b.get("transition_style")
                or _sr.run_id(a) or _sr.run_id(b) or a.get("camera_pan")):
            continue
        out.append(i)
    return out


# ── the hard cuts ───────────────────────────────────────────────────────────────────────────────────────
# EVERY UNMARKED SEAM USED TO BE A 12-FRAME CROSS-DISSOLVE (or the DNA's native whip), and three benchmark films
# made with this skill (2026-10-24) named that the strongest "this is slides" signal in them: a 1:1 type film cut on
# a 105.88 BPM grid still dissolved on every cut, and a 9:16 launch film cut ~14 times a minute, all soft, against the
# 27.8 a minute measured on Apple's launch film (references/launch-film-study.md). motion-research §2: "hard cut by
# default". So an UNMARKED seam is planned as the `cut` seam (remotion/src/seams.tsx: the picture changes on the
# seam's middle frame, the audio keeps the seam's overlap) on a film whose ENERGY asks for it:
#
#   kinetic  a launch or promo (meta.purpose), or meta.intensity "bold" — every unmarked seam is a cut
#   scored   a film with music (beatgrid.music_requested) — half its seams hard, the cut landing on the beat the
#            pads are snapped to; a seam into a LOW-energy beat or into the close keeps its dissolve
#   calm     everything else (a teach / howto / research explainer with no score) — no planned cuts: a dissolve
#            is the calm film's breath, and the pace caveat in references/motion-grammar.md is about exactly that
#
# `meta.cuts: "kinetic" | "scored" | "calm"` names the tempo outright. The shares are this planner's choice (U), not
# a published number: what a published number exists for is the RATE, and the rate a board can reach is set by its
# beat lengths, which a seam planner cannot change — `cut_report` measures both from the board and says which bound.
#
# A planned cut is written `{"type": "cut", "by": "seam_plan"}`, so a re-run can tell its own cuts from an author's
# (an author's cut has no `by`) and re-plan them; the renderer reads only `type`.
CUT_TEMPOS = ("kinetic", "scored", "calm")
CUT_SHARE = {"kinetic": 1.0, "scored": 0.5, "calm": 0.0}
# ...and the share under which validate.py says so. A kinetic film's marks, hand-offs and returns stay soft by design,
# so its floor sits below its plan: 2-3 marks on an 8-beat film leave 4-5 of 7 seams to cut (0.57-0.71).
CUT_WARN_BELOW = {"kinetic": 0.5, "scored": 0.4, "calm": 0.0}
REFERENCE_CUTS_PER_MIN = 27.8          # Apple's launch film, measured (references/launch-film-study.md)
PLANNED_BY = "seam_plan"
_ENERGY_RANK = {"peak": 0, "high": 1, "medium": 2, "": 3, "low": 4}
_REL_RANK = {"continuation": 0, "new-topic": 1, "payoff": 2}


def film_tempo(meta):
    """(tempo, basis) — how hard this film cuts, from what the board already says about it."""
    m = meta if isinstance(meta, dict) else {}
    forced = str(m.get("cuts") or "").strip().lower()
    if forced in CUT_TEMPOS:
        return forced, "meta.cuts"
    try:
        import tier_advice as _ta
        purpose = _ta.canonical_purpose(m.get("purpose"))
    except Exception:                                  # noqa: BLE001 — no purpose reader, no purpose
        purpose = None
    if purpose in ("launch", "promo"):
        return "kinetic", "purpose:%s" % purpose
    if str(m.get("intensity") or "").strip().lower() == "bold":
        return "kinetic", "intensity:bold"
    try:
        import beatgrid as _bg
        if _bg.music_requested(m):
            return "scored", "music (bgm %r)" % m.get("bgm")
    except Exception:                                  # noqa: BLE001
        pass
    return "calm", "purpose:%s, no music" % (purpose or "unknown")


def is_planned_cut(slide):
    """A `cut` this planner wrote (and may re-plan), as opposed to an author's."""
    ti = (slide or {}).get("transition_in")
    return isinstance(ti, dict) and ti.get("type") == "cut" and ti.get("by") == PLANNED_BY


def strip_planned_cuts(slides):
    """Remove this planner's own earlier cuts (they are re-planned from the board as it is now) → their beat indexes."""
    out = []
    for i, s in enumerate(slides):
        if is_planned_cut(s):
            del s["transition_in"]
            out.append(i)
    return out


def _cut_eligible(slides, i, marks, handoffs):
    """Why seam i cannot be a planned cut, or None when it can."""
    import stage_runs as _sr
    a, b = slides[i - 1], slides[i]
    if _sr.joined(a, b):
        return "inside a stage run (no seam)"
    if i in marks:
        return "marked"
    if b.get("transition_in") or b.get("transition_style"):
        return "authored"
    if (i - 1) in handoffs or (a.get("camera") or {}).get("handoff"):
        return "a camera hand-off carries it (the push IS that cut's motion)"
    if str(b.get("relation") or "").strip().lower() == "return":
        return "a return (the seam is the pan back across the board)"
    if a.get("match_cut"):
        return "a match_cut (the container by declared rects)"
    return None


def plan_cuts(slides, meta=None, marks=None, handoffs=None):
    """→ (tempo, basis, {beat_index: why}) — the UNMARKED seams to cut hard, by the film's tempo (see above)."""
    marks, handoffs = marks or {}, set(handoffs or ())
    tempo, basis = film_tempo(meta)
    n = len(slides)
    seams = [i for i in range(1, n) if not _joined(slides, i)]
    if tempo == "calm" or not seams:
        return tempo, basis, {}
    elig = [i for i in seams if _cut_eligible(slides, i, marks, handoffs) is None]
    if tempo == "scored":
        def rel(i):
            return str(slides[i].get("relation") or "").strip().lower()
        elig = [i for i in elig if rel(i) != "close"
                and str(slides[i].get("energy") or "").strip().lower() != "low"]
        already = sum(1 for i in seams if _hard(slides[i], marks.get(i)))
        want = max(0, int(math.ceil(CUT_SHARE[tempo] * len(seams) - 1e-9)) - already)
        elig = sorted(elig, key=lambda i: (_ENERGY_RANK.get(str(slides[i].get("energy") or "").strip().lower(), 3),
                                           _REL_RANK.get(rel(i), 3), i))[:want]
    why = {"kinetic": "a %s film cuts hard on its unmarked seams" % tempo,
           "scored": "the cut lands on the beat the pads are snapped to"}[tempo]
    return tempo, basis, {i: why for i in sorted(elig)}


def _joined(slides, i):
    import stage_runs as _sr
    return _sr.joined(slides[i - 1], slides[i])


def _hard(slide, mark=None):
    """Is this seam a hard cut once the plan is applied — a `cut`, or the `punch` (a hard cut with a lean and a flash)?"""
    t = (mark or {}).get("type")
    if t is None:
        import render_remotion as _rr
        ti = _rr._transition_in(slide)
        t = (ti or {}).get("type")
    return t in ("cut", "punch")


def cut_report(slides, fps=30, tr=None):
    """The hard-cut RATE measured from the board as it stands: {'seams', 'hard', 'share', 'film_s', 'per_min',
    'max_per_min'} — `per_min` counts hard cuts, `max_per_min` every seam (what the beat lengths allow at most).
    `film_s`/rates are None when the beats carry no durations yet (before tts.py)."""
    if tr is None:
        import beatgrid as _bg
        tr = _bg.seam_frames()
    n = len(slides)
    seams = [i for i in range(1, n) if not _joined(slides, i)]
    hard = [i for i in seams if _hard(slides[i])]
    durs = [s.get("duration") for s in slides]
    film_s = None
    if n and all(isinstance(d, (int, float)) and d > 0 for d in durs):
        film_s = sum(max(1, int(round(float(d) * fps))) for d in durs) / float(fps) - len(seams) * tr / float(fps)
    per = (lambda k: round(60.0 * k / film_s, 1)) if film_s and film_s > 0 else (lambda k: None)
    return {"seams": len(seams), "hard": len(hard), "hard_beats": [i + 1 for i in hard],
            "share": round(len(hard) / float(len(seams)), 3) if seams else 0.0,
            "film_s": round(film_s, 3) if film_s else None, "per_min": per(len(hard)), "max_per_min": per(len(seams))}


def cut_shortfall(slides, meta):
    """A sentence when the board's hard-cut share is under its tempo's target, else None (validate.py repeats it)."""
    tempo, basis = film_tempo(meta)
    rep = cut_report(slides)
    floor = CUT_WARN_BELOW[tempo]
    if not rep["seams"] or floor <= 0 or rep["share"] + 1e-9 >= floor:
        return None
    rate = (" (%.1f hard cuts a minute; its beat lengths allow %.1f; Apple's launch film cuts %.1f)"
            % (rep["per_min"], rep["max_per_min"], REFERENCE_CUTS_PER_MIN)) if rep["per_min"] is not None else ""
    return ("%d of %d seams are hard cuts%s on a %s film (%s) — every other seam is a 12-frame dissolve, the strongest "
            "\"this is slides\" signal three benchmark films found. Run `python3 scripts/seam_plan.py <out_dir>` to "
            "plan the cuts, or set `meta.cuts` if this film is meant to breathe." % (rep["hard"], rep["seams"], rate,
                                                                                      tempo, basis))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if argv else 2
    out_dir = argv[0]
    dry = "--dry-run" in argv
    path = os.path.join(out_dir, "storyboard.json")
    board = json.load(open(path, encoding="utf-8"))
    if str(board.get("meta", {}).get("renderer", "")).lower() not in ("remotion", "remotion-bespoke"):
        print("[seam_plan] not a remotion deck — the marked-seam vocabulary is remotion-only")
        return 0

    # FILM-SCOPED STATE, RESTORED ON THE WAY OUT. `install_workshop` sets the module-level grounds and
    # provenances this run's `plan`/`plan_camera` read; leaving them set after `main` returns (or raises)
    # would have the NEXT film planned in the same process read THIS one's workshop.
    # A BOARD BUILT WITHOUT THE PLAN'S FIELDS plans nothing: every seam stays a default cut, and this used to say only
    # that no beat declared a relation. When content_plan.json still maps beat-for-beat, take them from it (the plan
    # is where `relation` is decided) and say so; a board that has diverged from the plan is left alone.
    try:
        import storyboard as _sb
        _plan = json.load(open(os.path.join(out_dir, "content_plan.json"), encoding="utf-8"))
        _miss = _sb.plan_fields_missing(board.get("slides") or [], _plan)
        if _miss:
            for s, b in zip(board["slides"], _plan["beats"]):
                for k in _sb.PLAN_FIELDS:
                    if k in b and k not in s:
                        s[k] = b[k]
            print("[seam_plan] took %s from content_plan.json (the board did not carry them)"
                  % ", ".join("%s on %d beat(s)" % kv for kv in sorted(_miss.items())))
    except (OSError, ValueError):
        pass
    install_workshop(out_dir)
    try:
        return _plan_film(argv, out_dir, dry, path, board)
    finally:
        clear_workshop()


def _plan_film(argv, out_dir, dry, path, board):
    if dry:
        board = copy.deepcopy(board)                  # a dry run plans on a copy and writes nothing
    slides = board.get("slides", [])
    # this planner's OWN earlier cuts are re-planned from the board as it is now; an author's cut has no `by`
    replanned = strip_planned_cuts(slides)
    already = [i for i, s in enumerate(slides) if s.get("transition_in") or s.get("transition_style")]
    if already and not dry:
        print("[seam_plan] %d beat(s) already carry an authored seam (%s) — leaving them alone"
              % (len(already), ", ".join(str(i + 1) for i in already)))

    marks = plan(slides, board.get("meta", {}).get("design_dna"), out_dir)
    # A BEAT THAT CONTINUES A STAGE RUN has no cut before it (scripts/stage_runs.py): nothing to mark there
    import stage_runs as _sr
    for i in [i for i in marks if i > 0 and _sr.joined(slides[i - 1], slides[i])]:
        print("  beat %-3d skip (continues stage run %r — no cut)" % (i + 1, _sr.run_id(slides[i])))
        del marks[i]
    if not marks:
        print("[seam_plan] no beat declares new-topic / payoff / close — no seam is marked. "
              "That is a legitimate film (one unbroken argument), but check the `relation` field is set.")
        _plan_cut_seams(board, slides, {}, set(), replanned, dry)
        if not dry:
            json.dump(board, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 0

    for i, m in sorted(marks.items()):
        s = slides[i]
        tag = "would mark" if dry else "mark"
        if s.get("transition_in") or s.get("transition_style"):
            print("  beat %-3d skip (authored)" % (i + 1))
            continue
        print("  beat %-3d %s %-9s %s" % (i + 1, tag, m["type"], m["why"]))
        s["transition_in"] = {k: v for k, v in m.items() if k != "why"}

    cams = {} if "--no-camera" in argv else plan_camera(slides)
    for i in [i for i in cams if _sr.run_id(slides[i])]:
        del cams[i]                                    # a stage moves its own camera
    handoffs = set(plan_handoffs(slides, cams, marks))
    for i, c in sorted(cams.items()):
        sl = slides[i]
        if sl.get("camera"):
            print("  beat %-3d skip camera (authored)" % (i + 1))
            continue
        hand = " — runs into the cut, beat %d inherits it" % (i + 2) if i in handoffs else ""
        print("  beat %-3d %s camera %-5s %s%s" % (i + 1, "would" if dry else "set", c["move"], c["why"], hand))
        if not dry:
            sl["camera"] = {"move": c["move"]} if CAMERA_AMOUNT is None else \
                {"move": c["move"], "amount": CAMERA_AMOUNT}
            if i in handoffs:
                sl["camera"]["handoff"] = True

    _plan_cut_seams(board, slides, marks, handoffs, replanned, dry)
    if not dry:
        json.dump(board, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[seam_plan] %d marked seam(s) of %d cut(s), %d moving beat(s) of %d%s"
          % (len(marks), max(0, len(slides) - 1), len(cams), len(slides),
             " (dry run — nothing written)" if dry else ""))
    return 0


def _plan_cut_seams(board, slides, marks, handoffs, replanned, dry):
    """Plan and write the hard cuts (plan_cuts), then print the rate measured from the board."""
    meta = board.get("meta", {})
    tempo, basis, cuts = plan_cuts(slides, meta, marks, handoffs)
    for i, why in sorted(cuts.items()):
        print("  beat %-3d %s cut       %s" % (i + 1, "would" if dry else "cut", why))
        slides[i]["transition_in"] = {"type": "cut", "by": PLANNED_BY}
    rep = cut_report(slides)
    rate = (", %.1f a minute (every seam would be %.1f; Apple's launch film %.1f)"
            % (rep["per_min"], rep["max_per_min"], REFERENCE_CUTS_PER_MIN)) if rep["per_min"] is not None else ""
    print("[seam_plan] tempo %s (%s): %d of %d seam(s) hard%s%s"
          % (tempo, basis, rep["hard"], rep["seams"], rate,
             "; re-planned %d earlier planned cut(s)" % len(replanned) if replanned else ""))
    return cuts


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
