#!/usr/bin/env python3
"""rhythm_qa.py — deterministic PRE-render VIDEO-RHYTHM gate on storyboard.json.

The layout-diversity gate (validate.py) checks the deck doesn't LOOK samey; this checks it doesn't
FEEL flat. A deck can pass every per-scene check and still be monotone — all scenes the same length,
no climax, a static image held forever, no attention reset for a minute. This catches that.

Reads storyboard.json (uses each scene's `duration` when tts.py has run, else estimates from narration
length). Advisory by design (pacing is judgment): almost everything is a WARNING. Only ONE egregious,
deterministic defect is an ERROR — a MEASURED static image held past the hard ceiling (an estimate never
gates a render). Everything else, including a missing climax, is a WARNING. Run after tts (real
durations) and before the full render.

    python scripts/rhythm_qa.py <out_dir> [--json]

WHAT IT COVERS, AND WHY THE HEADLINE SAYS SO. The universe is every entry in `storyboard.json`'s `slides`,
parsed from the board. Three things used to leave that universe without a word: an entry that is not an
object was filtered out by an `isinstance` and then COUNTED OUT of `n`, so the headline read as the film;
an empty board returned `ok: True` ("could not measure" wearing the face of "clean"); and the held-frame
ERROR — the only rule here that can block a render — only ever looks at scenes whose `type` is a held
image, so on a deck of `html`/`chart` scenes it inspects nothing while the headline still counts them.
The total seconds mix MEASURED durations with narration ESTIMATES, which is now stated on the headline
rather than only inside whichever warning happened to fire.
"""
import sys, os, json, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storyboard as sb
import _common as _c

# ── thresholds (video-pacing heuristics) ──────────────────────────────────────────────────────
MIN_SCENES_UNIFORMITY = 5        # need a few scenes before "too uniform" means anything
UNIFORMITY_CV_MIN     = 0.15     # coefficient of variation below this = monotone durations
CLIMAX_POS_LO, CLIMAX_POS_HI = 0.65, 0.88   # the payoff belongs ~70-85% through (a little tolerance)
NO_CLIMAX_DURATION    = 75.0     # a video longer than this should have a marked climax
STATIC_IMAGE_SOFT     = 10.0     # a held image beyond this drags (WARN)
STATIC_IMAGE_HARD     = 16.0     # …beyond this it's a defect (ERROR)
RESET_MAX             = 35.0     # go this long with no seam / family change = no attention reset
FINAL_HOLD_RATIO      = 1.25     # last scene's narration vs the median; above = not a sparse hold

_STATIC_TYPES = {"slide"}                              # a held image
_DENSE_TYPES  = {"chart", "keypoints", "compare", "timeline", "html"}


def _stype(s):
    # A remotion beat names its register in `shot` and carries no `type`. Defaulted to "slide" it would be
    # judged as a held still — a warning on every beat over 10s, a blocking ERROR on one over 16s — when it
    # is a register animating on its own clock. It is its own kind, which the held-frame rule reports as a
    # type it does not inspect.
    if s.get("type") is None and s.get("shot"):
        return "shot"
    return s.get("type", "slide")


def _est_seconds(s, meta):
    """Real duration if tts.py has run, else estimate from narration length."""
    d = s.get("duration")
    if isinstance(d, (int, float)) and d > 0:
        return float(d)
    text = (s.get("narration") or "").strip()
    if not text:
        return 3.0
    cjk, words = _script_split(text)
    return max(2.0, cjk / 5.0 + words / 2.5)           # per-SCRIPT sum: ~5 CJK chars/sec + ~2.5 Latin words/sec
                                                       # (the old binary flip made one zh term in an en line
                                                       # count every Latin CHAR as a CJK char — a 3x blowup)


def _cjk_char(c):
    return "　" <= c <= "鿿" or "가" <= c <= "힣"


def _looks_cjk(text):
    return any(_cjk_char(c) for c in text)


def _script_split(text):
    """(cjk_char_count, latin_word_count) — the two speaking-rate populations of a mixed line."""
    cjk = sum(1 for c in text if _cjk_char(c))
    words = len("".join(" " if _cjk_char(c) else c for c in text).split())
    return cjk, words


def _narr_len(s, meta):
    """Relative narration LENGTH in one speaking-time unit (CJK char = 1, Latin word = 2 — a word
    takes ~2 CJK-chars' time), so mixed-script decks compare consistently."""
    cjk, words = _script_split((s.get("narration") or "").strip())
    return cjk + 2 * words


def _is_reset(s, prev, meta):
    """A scene resets attention if it opens a transition seam (a dip through the bg) OR changes the
    visual family. Resolve the EFFECTIVE transition the way the pipeline does — a per-scene value, else
    the meta default (`dip`). NOTE: the audit flagged that the meta-default `dip` makes this gate inert
    (it never accumulates a no-reset run). The tempting fix (count only EXPLICIT seams) is UNSAFE here
    because `_stype` is coarse — every `html` scene shares one type, so it would spuriously flag a
    well-designed all-HTML deck (varied FORMS, one type) as monotone. A correct fix needs form-aware
    scene-typing (read each page's layout family), which is out of scope for a safe minor edit — so the
    conservative meta-default behaviour is kept deliberately until then."""
    tr = sb.normalize_transition(s)[0] or (meta or {}).get("transition", "dip")
    if tr in ("in", "dip", "out"):
        return True
    return prev is not None and _stype(s) != _stype(prev)


def evaluate(data, meta=None):
    meta = meta if meta is not None else (data.get("meta") or {})
    entries = data.get("slides") or []
    universe = len(entries)
    slides = [s for s in entries if isinstance(s, dict)]
    # NAMED, not filtered into silence. A board entry that is not an object is a malformed board, and the
    # position is the only thing that lets anyone find it.
    unreadable = ["scene at position %d: the storyboard entry is a %s, not a scene object — nothing about "
                  "this scene could be read, and it is not in any number below"
                  % (i + 1, type(s).__name__) for i, s in enumerate(entries) if not isinstance(s, dict)]
    errors, warnings = [], []
    n = len(slides)
    if n == 0:
        # NOT ok. An empty board is a board this gate could not measure, and a caller that reads the exit
        # code must not be able to mistake that for a well-paced film.
        return {"ok": False,
                "errors": (unreadable or
                           ["the storyboard holds no scenes — nothing was measured, which is not a pass"]),
                "warnings": [], "scenes": 0, "universe": universe, "measured": 0, "not_measured": unreadable,
                "durations_estimated": 0, "held_frame_scenes": 0, "held_frame_skipped": {}}

    durs = [_est_seconds(s, meta) for s in slides]
    total = sum(durs)
    est_note = "" if all(isinstance(s.get("duration"), (int, float)) for s in slides) else \
        " (estimated from narration — run after tts.py for exact durations)"
    # Video KIND — a NARRATIVE arc builds to a payoff (a paper, a pitch, a story); an EXPOSITORY arc is
    # an even-weight walkthrough (a tutorial, a reference, a survey, a how-to). The persuasive-arc checks
    # (no-climax, final-hold sparsity, and a tighter uniformity floor) only apply to a narrative arc.
    expository = str(meta.get("arc_kind", "narrative")).lower() in (
        "expository", "tutorial", "reference", "survey", "howto", "how-to", "walkthrough")
    cv_floor = 0.10 if expository else UNIFORMITY_CV_MIN

    # 1. duration uniformity — a flat row of equal-length beats is the clearest monotony tell
    if n >= MIN_SCENES_UNIFORMITY:
        mean = total / n
        if mean > 0:
            sd = math.sqrt(sum((d - mean) ** 2 for d in durs) / n)
            cv = sd / mean
            if cv < cv_floor:
                warnings.append(
                    f"durations too uniform (CV={cv:.2f} < {cv_floor}){est_note} — vary the pacing: "
                    f"quick build beats (3-4s), a longer key beat (6-8s), a sparse hold. A flat row of "
                    f"equal beats reads as auto-generated (an expository/reference video may legitimately "
                    f"use even beats — set meta.arc_kind=\"expository\" to relax this).")

    # 2. climax placement — one payoff, ~70-85% through
    cum = 0.0
    climax_positions = []
    for s, d in zip(slides, durs):
        mid = (cum + d / 2) / total if total else 0
        # A shot scene carries the mark ITSELF (`climax: true`): its register's props are `shot_props`, and a
        # flag put there would be handed to the register as copy. energy_skeleton and script_audition read the
        # scene's own field; reading only `props.climax` here told every narrative remotion film it had no
        # payoff while its board declared one.
        if (s.get("props") or {}).get("climax") or s.get("climax"):
            climax_positions.append((s.get("index"), mid))
        cum += d
    if climax_positions:
        for idx, pos in climax_positions:
            if not (CLIMAX_POS_LO <= pos <= CLIMAX_POS_HI):
                warnings.append(
                    f"scene {idx}: climax lands at ~{pos*100:.0f}% of runtime — the payoff reads best at "
                    f"~70-85%. Move the climax beat, or drop `props.climax` here.")
        if len(climax_positions) > 1:
            warnings.append(
                f"{len(climax_positions)} scenes marked `props.climax` — a video has ONE payoff peak; "
                f"keep one climax and let the others be quieter heroes.")
    elif total > NO_CLIMAX_DURATION and not expository:
        warnings.append(
            f"no climax beat in a {total:.0f}s video — mark the payoff/result beat `props.climax:true` (a shot "
            f"scene: `climax: true` on the scene itself) "
            f"so the video builds to a peak. (A tutorial/reference/survey legitimately has no single "
            f"payoff — set meta.arc_kind=\"expository\" to suppress this.)")

    # 3. final hold should be sparse — a NARRATIVE closer is a punchy single line; an EXPOSITORY video may
    #    legitimately close on a denser step-recap / "what's next" summary.
    if n >= 3 and not expository:
        lens = sorted(_narr_len(s, meta) for s in slides)
        med = lens[len(lens) // 2] or 1
        last = slides[-1]
        if _narr_len(last, meta) > FINAL_HOLD_RATIO * med:
            warnings.append(
                f"scene {last.get('index')} (final): narration is denser than the deck median — a "
                f"narrative closer should be a SPARSE hold (a single stat / line). (A tutorial recap may "
                f"legitimately be denser — set meta.arc_kind=\"expository\".)")

    # 4. static image held too long — the ERROR gates a render, so raise it ONLY on a MEASURED duration
    #    (a pre-tts estimate never hard-blocks) AND only on a genuinely DEAD frame. A slide walked by
    #    TIMED callouts (cue/at) has moving attention — each callout is the reset-equivalent of a cut —
    #    so downgrade it to a WARN, however long.
    held_checked, held_skipped = 0, {}
    for s, d in zip(slides, durs):
        if _stype(s) not in _STATIC_TYPES:
            # This rule's universe is NARROWER than the film's, and that has to be reportable: on a deck of
            # html/chart scenes the only ERROR here inspects nothing at all.
            held_skipped[_stype(s)] = held_skipped.get(_stype(s), 0) + 1
        if _stype(s) in _STATIC_TYPES:
            held_checked += 1
            measured = isinstance(s.get("duration"), (int, float)) and s.get("duration") > 0
            timed = any((c or {}).get("cue") or (c or {}).get("at") is not None
                        for c in (s.get("callouts") or []))
            if measured and d > STATIC_IMAGE_HARD and not timed:
                errors.append(
                    f"scene {s.get('index')}: a static image is held {d:.0f}s (> {STATIC_IMAGE_HARD:.0f}s) "
                    f"with no timed callouts — split into shorter cuts or cut it; a dead frame held that "
                    f"long reads as sluggish (a frame walked by timed callouts is exempt).")
            elif d > STATIC_IMAGE_SOFT:
                warnings.append(
                    f"scene {s.get('index')}: a static image is held {d:.0f}s{est_note} — prefer 2 shorter "
                    f"cuts over one long hold (a >10s hold on one frame drags even with Ken Burns).")

    # 5. attention-reset cadence — no seam / family change for too long
    run = 0.0
    run_start = slides[0].get("index")
    prev = None
    for s, d in zip(slides, durs):
        if _is_reset(s, prev, meta) and prev is not None:
            run = 0.0
            run_start = s.get("index")
        run += d
        if run > RESET_MAX:
            warnings.append(
                f"no attention reset for ~{run:.0f}s (from scene {run_start}) — the viewer needs a beat "
                f"to breathe every ~20-30s: a section seam (a `new-topic` transition dip) or a change of "
                f"visual family. Add one around scene {s.get('index')}.")
            run = 0.0
            run_start = s.get("index")
        prev = s

    est_n = sum(1 for s in slides if not (isinstance(s.get("duration"), (int, float)) and s["duration"] > 0))
    if held_skipped and not held_checked:
        warnings.append(
            "the held-frame check — the only ERROR this gate raises — inspected 0 of %d scene(s): it reads "
            "scenes of type %s, and this board holds %s. Nothing here was checked for an over-held frame."
            % (n, "/".join(sorted(_STATIC_TYPES)),
               ", ".join("%s x%d" % (k, v) for k, v in sorted(held_skipped.items()))))
    # A drop with no recorded reason is itself the finding — the same rule the shared coverage printer
    # applies. M comes from the board, so a future silent filter shows up here instead of shrinking M.
    if universe - n > len(unreadable):
        errors.append("%d scene(s) left the measurement with NO recorded reason — a gate that cannot say "
                      "why it lost a scene is reporting over a film it did not read"
                      % (universe - n - len(unreadable)))
    errors = unreadable + errors
    return {"ok": not errors, "errors": errors, "warnings": warnings, "scenes": n,
            "total_seconds": round(total, 1),
            # COVERAGE, carried in the result so --json and any caller sees the same numbers the headline
            # prints. `scenes` is what was measured; `universe` is what the board holds.
            "universe": universe, "measured": n, "not_measured": unreadable,
            "durations_estimated": est_n, "held_frame_scenes": held_checked,
            "held_frame_skipped": held_skipped}


def _unmeasurable(why):
    return {"ok": False, "errors": [why], "warnings": [], "scenes": 0, "universe": 0, "measured": 0,
            "not_measured": [why], "durations_estimated": 0, "held_frame_scenes": 0, "held_frame_skipped": {}}


def check(out_dir):
    path = os.path.join(out_dir, "storyboard.json")
    if not os.path.exists(path):
        return _unmeasurable(f"no storyboard.json in {out_dir}")
    try:
        data = sb.load(path)
    except Exception as e:
        return _unmeasurable(f"storyboard.json unreadable: {e}")
    return evaluate(data)


def main(argv):
    # `--jsonn` used to be dropped on the floor with every other unrecognised flag, so the report the caller
    # asked for simply never appeared and the run still exited 0. Same family as the silent full sweep in
    # `register_energy` — see scripts/_common.argflag.
    _c.refuse_unknown(argv, switches=("json",), usage="usage: rhythm_qa.py <out_dir> [--json]")
    args = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    out_dir = args[0] if args else "."
    r = check(out_dir)
    if as_json:
        os.makedirs(os.path.join(out_dir, "qa"), exist_ok=True)
        with open(os.path.join(out_dir, "qa", "rhythm_qa.json"), "w") as f:
            json.dump(r, f, indent=2)
        print(json.dumps(r, indent=2))
    else:
        # THE HEADLINE STATES COVERAGE. `{scenes} scenes` alone was the count that SURVIVED the isinstance
        # filter, so a 10-entry board with two malformed entries printed "8 scenes" and read as the film.
        est = r.get("durations_estimated") or 0
        held = ("" if r.get("held_frame_scenes") == r.get("measured") else
                f" · held-frame check covered {r.get('held_frame_scenes', 0)}")
        print(f"rhythm_qa: measured {r.get('measured', r['scenes'])} of {r.get('universe', r['scenes'])} "
              f"scene(s), {r.get('total_seconds','?')}s"
              + (f" ({est} duration(s) ESTIMATED from narration — run after tts.py)" if est else "")
              + held)
        for e in r["errors"]:
            print(f"  ERROR: {e}")
        for w in r["warnings"]:
            print(f"  WARN:  {w}")
        if not r["errors"] and not r["warnings"]:
            print("  ok — pacing varies, climax placed, closer sparse, no over-held frame.")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
