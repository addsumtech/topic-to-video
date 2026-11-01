#!/usr/bin/env python3
"""Phrase steps — WHEN an authored push or pull takes its next step: on the voice's next clause, ~2.4 s apart.

WHY. craft_qa (scripts/craft_qa.py) measured our films holding a frame still for 5.0 s (median longest still) against
2.5 s on 28 published launch films. Located beat by beat on 22 of our films: 89 beats held past 3 s, spread over 30+
registers, the hold starting about a third of the way in and lasting about half the beat — the register has revealed
and the narration is still talking. 80 of the 89 had no camera at all. So the gap is not one register's to fix.

WHAT IS NOT DONE, AND WHY. A continuous drift on every unauthored beat (runtime/depth `bedPan`) was shipped once and
withdrawn: watched, "the type slides sideways all film". A hold is not cured by never resting; it is cured by something
HAPPENING when the voice moves on. So this places EVENTS — a short eased push (Film.tsx PhraseCamera) — on the onsets
of the clauses the voice starts after the beat has settled, and between events the frame rests.

THE RULES (each one a number a test pins):
  * settle   no step before SETTLE_FRAC of the beat + FIRST_AFTER (the measured median hold starts at 31%). A cued
             item's reveal does NOT hold the steps back: measured on espresso's TechnicalPlate, waiting for three cued
             callouts (~20 px labels at 4.2/7.4/9.2 s) put the first step at 12.1 s of a 13.9 s beat and the frame held
             8.9 s. A step lands on the clause that NAMES a part, which is when the part arrives — one event, not two.
  * silence  once the voice has finished, a beat holding on its tail still gets its step at the ideal time: the
             hold the viewer sees does not care whether anyone is talking.
  * where    a step lands on a CLAUSE onset (the first word after , ， 。 ； ： ! ? and their kin) between MIN_GAP and
             MAX_GAP after the last event; failing one, the word onset nearest IDEAL_GAP; with no word times at all,
             IDEAL_GAP after the last event. Landing on the voice is the whole point: the push reads as the camera
             following the sentence, not as a timer.
  * end      none in the last END_GUARD seconds — the seam owns those.
  * who      ONLY a beat whose author asked for a push or a pull (render_remotion.attach_phrases): steps on beats nobody
             gave a camera were built and measured, and withdrawn — every glyph of a register is re-positioned and
             jitter_qa found type trembling up to 0.47 px on registers that had been still (Film.tsx PhraseCamera).
             Nor on a beat whose author FIXED the camera — an explicit hold, a pan, a hand-off — on a register
             that already moves on its own (its measured motion p75 at or over film_energy_qa's floor), on a beat
             shorter than MIN_BEAT, or with the feature switched off (`meta.phrase_camera: false`, per beat
             `"phrase_camera": false`). An authored push or pull IS stepped: spread evenly over a 15-19 s beat it moved
             under what a viewer sees (espresso's push and pull beats held 9.8 s and 8.2 s), so it keeps its direction
             and amount and arrives clause by clause (Film.tsx PhraseCamera).
"""
import re

SETTLE_FRAC = 0.3
FIRST_AFTER = 0.6        # a step the instant the reveal ends only extends the reveal
MIN_GAP = 1.8
IDEAL_GAP = 2.4
MAX_GAP = 3.0
END_GUARD = 1.0
MIN_BEAT = 4.0
MOVING_P75 = 0.0037       # film_energy_qa.MOTION_P75_FLOOR: a register at or over it is not a hold

_CLAUSE_END = re.compile(r"[,，。；;：:!！?？、…—]")


def _clause_onsets(spans, caption):
    """Times of the words that start a clause: the first spoken token after a clause-ending mark."""
    out = []
    last_b = 0
    for s in spans:
        a = int(s.get("a", 0))
        gap = caption[last_b:a] if caption else ""
        if out == [] and last_b == 0:
            pass
        elif _CLAUSE_END.search(gap):
            out.append(float(s["t"]))
        last_b = max(last_b, int(s.get("b", a)))
    return out


def phrase_steps(spans, caption, duration, authored_camera=False, register_p75=None, enabled=True):
    """Sorted seconds (beat clock) at which the camera takes a step; [] when this beat gets none."""
    if not enabled or authored_camera or duration < MIN_BEAT:
        return []
    if register_p75 is not None and register_p75 >= MOVING_P75:
        return []
    settle = SETTLE_FRAC * duration
    end = duration - END_GUARD
    spans = sorted((s for s in (spans or []) if "t" in s), key=lambda s: float(s["t"]))
    onsets = [float(s["t"]) for s in spans]
    clauses = _clause_onsets(spans, caption or "")
    steps = []
    prev = None
    while True:
        if prev is None:
            lo, hi = settle + FIRST_AFTER, min(settle + MAX_GAP, end)
        else:
            lo, hi = prev + MIN_GAP, min(prev + MAX_GAP, end)
        if lo > end:
            break
        pick = None
        if hi >= lo:
            c = [t for t in clauses if lo - 1e-9 <= t <= hi + 1e-9]
            if c:
                pick = c[0]
            elif onsets:
                w = [t for t in onsets if lo - 1e-9 <= t <= hi + 1e-9]
                if w:
                    ideal = (settle if prev is None else prev) + IDEAL_GAP
                    pick = min(w, key=lambda t: abs(t - ideal))
            if pick is None and not onsets:
                pick = min(max((settle if prev is None else prev) + IDEAL_GAP, lo), hi)
        if pick is None:
            # no word in the window: the next word if the voice speaks again before the end, else — the voice has
            # finished and the beat is holding on its tail — the ideal time inside the window
            nxt = [t for t in onsets if t > hi]
            if nxt and nxt[0] <= end:
                pick = nxt[0]
            elif hi >= lo:
                pick = min(max((settle if prev is None else prev) + IDEAL_GAP, lo), hi)
            else:
                break
        steps.append(round(pick, 3))
        prev = pick
    return steps
