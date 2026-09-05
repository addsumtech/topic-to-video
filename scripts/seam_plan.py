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

_SHOTLUMA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "remotion", "src", "runtime", "shotLuma.ts")
_GROUND_TOKEN = None


def _ground_tokens():
    """DNA_GROUND_TOKEN — which DNA token(s) each shot MEASURABLY paints its ground from."""
    global _GROUND_TOKEN
    if _GROUND_TOKEN is None:
        _GROUND_TOKEN = {}
        try:
            import re
            body = open(_SHOTLUMA, encoding="utf-8").read().split("DNA_GROUND_TOKEN", 1)[1]
            body = body.split("{", 1)[1].split("};")[0]
            for name, val in re.findall(r"(\w+):\s*(\[[^\]]*\]|'[a-zA-Z0-9_]+')", body):
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
    toks = _ground_tokens().get(shot)
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


# the same threshold Film.tsx's pickPresentation judges on
HARSH_GAP = 0.34


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


def plan(slides, dna=None):
    dna = _resolve_dna(dna)
    """→ {beat_index: {"type": ..., "why": ...}} for the beats that should carry a marked seam.

    Beat 0 is never a candidate: there is no seam before the first shot.
    """
    cands = []
    for i in range(1, len(slides)):
        rel = (slides[i].get("relation") or "").strip().lower()
        seam = SEAM_BY_RELATION.get(rel)
        if not seam:
            continue
        crossing = _crosses(slides[i - 1].get("shot"), slides[i].get("shot"), dna)
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

    marks = plan(slides, board.get("meta", {}).get("design_dna"))
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

    cams = {} if "--no-camera" in argv else plan_camera(slides)
    for i, c in sorted(cams.items()):
        sl = slides[i]
        if sl.get("camera"):
            print("  beat %-3d skip camera (authored)" % (i + 1))
            continue
        print("  beat %-3d %s camera %-5s %s" % (i + 1, "would" if dry else "set", c["move"], c["why"]))
        if not dry:
            sl["camera"] = {"move": c["move"]} if CAMERA_AMOUNT is None else \
                {"move": c["move"], "amount": CAMERA_AMOUNT}

    if not dry:
        json.dump(board, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[seam_plan] %d marked seam(s) of %d cut(s), %d moving beat(s) of %d%s"
          % (len(marks), max(0, len(slides) - 1), len(cams), len(slides),
             " (dry run — nothing written)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
