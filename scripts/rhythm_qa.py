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
"""
import sys, os, json, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storyboard as sb

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
    return s.get("type", "slide")


def _est_seconds(s, meta):
    """Real duration if tts.py has run, else estimate from narration length."""
    d = s.get("duration")
    if isinstance(d, (int, float)) and d > 0:
        return float(d)
    text = (s.get("narration") or "").strip()
    if not text:
        return 3.0
    lang = (meta.get("language") or "").lower()
    if lang[:2] in ("zh", "ja", "ko") or _looks_cjk(text):
        return max(2.0, len(text) / 5.0)               # ~5 chars/sec CJK
    return max(2.0, len(text.split()) / 2.5)           # ~2.5 words/sec


def _looks_cjk(text):
    return any("　" <= c <= "鿿" or "가" <= c <= "힣" for c in text)


def _narr_len(s, meta):
    text = (s.get("narration") or "").strip()
    lang = (meta.get("language") or "").lower()
    return len(text) if (lang[:2] in ("zh", "ja", "ko") or _looks_cjk(text)) else len(text.split())


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
    slides = [s for s in (data.get("slides") or []) if isinstance(s, dict)]
    errors, warnings = [], []
    n = len(slides)
    if n == 0:
        return {"ok": True, "errors": [], "warnings": ["no scenes"], "scenes": 0}

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
        if (s.get("props") or {}).get("climax"):
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
            f"no climax beat in a {total:.0f}s video — mark the payoff/result beat `props.climax:true` "
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
    for s, d in zip(slides, durs):
        if _stype(s) in _STATIC_TYPES:
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

    return {"ok": not errors, "errors": errors, "warnings": warnings, "scenes": n,
            "total_seconds": round(total, 1)}


def check(out_dir):
    path = os.path.join(out_dir, "storyboard.json")
    if not os.path.exists(path):
        return {"ok": False, "errors": [f"no storyboard.json in {out_dir}"], "warnings": [], "scenes": 0}
    try:
        data = sb.load(path)
    except Exception as e:
        return {"ok": False, "errors": [f"storyboard.json unreadable: {e}"], "warnings": [], "scenes": 0}
    return evaluate(data)


def main(argv):
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
        print(f"rhythm_qa: {r['scenes']} scenes, {r.get('total_seconds','?')}s")
        for e in r["errors"]:
            print(f"  ERROR: {e}")
        for w in r["warnings"]:
            print(f"  WARN:  {w}")
        if not r["errors"] and not r["warnings"]:
            print("  ok — pacing varies, climax placed, closer sparse, no over-held frame.")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
