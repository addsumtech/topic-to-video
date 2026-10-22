#!/usr/bin/env python3
"""How long will this narration play? — the ONE spoken-length model, calibrated on this skill's own films.

    python3 scripts/pace.py <out_dir>                 # per beat + the film's predicted length against its target
    python3 scripts/pace.py --budget 4 --lang zh      # how much narration a 4 s beat holds

WHY THIS EXISTS. Four places guessed the pace, each its own way — rhythm_qa (5 CJK chars/s), the scriptwriter and
critic-content ("~5 chars/sec CJK"), and the content-planner's `est_seconds`, which counted nothing at all — and none
of them counted what a FILM adds to a SCRIPT: the heard pause after every beat, the opening and closing holds. On
the GPS test film (2026-10-16) the plan said 69 s, the scriptwriter's estimate said 85–92 s, and the film the user
was about to receive was ~100 s; every gate passed on the way. The overhead per beat is ~1.2 s, so a 15-beat film
carries ~18 s of it, and a "4 s beat" holds about 14 Chinese characters, not 20.

THE MODEL, fitted by least squares on 47 measured beats of 7 films (edge-tts zh, `duration` as tts.py wrote it):
    beat seconds = (0.197 · CJK chars + 0.244 · digits + 0.50 · Latin words) / tts_speed
                 + 0.275 · comma + 0.259 · colon/semicolon + 0.767 · full stop inside the line
                 + 1.243 per beat (the heard pause and breath) + 0.554 on the first beat (the opening hold)
Per-beat mean error 0.30 s (worst 1.04 s). Predicting each film's total from the other six: city +3.7%,
espresso −3.1%, jev ±0.2%, launch +2.1%, mri +0.7%, gps −9.0% (its many short beats paused longer). A remotion
film is then shortened by its seam overlaps (render_remotion.SEAM_FRAMES per cut).

ENGLISH, measured 2026-10-17: 40 explainer lines through tts.py (edge en-US-EmmaNeural), the pause terms kept from
the Chinese fit (the pad is the tier's, not the language's) and the spoken terms fitted: 0.296 s/word (~3.4 words/s),
0.175/digit, 0.153/comma, 0.364/colon, 0.365/full stop. Per-beat mean error 0.27 s (worst 0.74 s); each half of the
lines predicted from the other: +1.1% and −4.5%. The default it replaced (~2.6 words/s) said +22.6%.

WHAT IT DOES NOT KNOW. Chinese and English are calibrated. Another language falls back to the English rate (other
CJK to the Chinese one) and SAYS it is uncalibrated; the first film in that language should add its measured beats
to the fit. Once tts.py has run, each beat's real `duration` is used instead, and the output says so.
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _common as _c  # noqa: E402

# least-squares fit, see the docstring; refit with the films' measured beats when a voice or language is added
ZH = {"cjk": 0.197, "digit": 0.244, "latin_word": 0.496, "comma": 0.275, "colon": 0.259, "stop": 0.767,
      "beat": 1.243, "first": 0.554}
# measured on English (see the docstring); the stand-in for every space-separated language until one is measured
EN = dict(ZH, latin_word=0.296, digit=0.175, comma=0.153, colon=0.364, stop=0.365)
LATIN = EN
CALIBRATED = {"zh", "en"}
_CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")
_NUM = re.compile(r"\d+(?:[.,]\d+)?")
# words in any space-separated script come from _common.words (a Latin-only class counted a Russian line as zero
# words and predicted only its pauses)


def _base(lang):
    return str(lang or "zh").lower().replace("_", "-").split("-")[0]


def _coef(lang):
    return ZH if _base(lang) in ("zh", "ja", "ko") else LATIN


def film_language(meta, slides):
    """The narration's language: `meta.language`, or — for "auto", the documented default, which tts.py resolves from
    the text — read from the narration itself. "auto" used to fall to the English rate and print UNCALIBRATED on a
    Chinese film, predicting it ~9% short."""
    lang = _base((meta or {}).get("language") or "auto")
    if lang not in ("auto", ""):
        return lang
    text = " ".join(str(s.get("narration") or "") for s in slides if isinstance(s, dict))
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"
    cjk = len(_CJK.findall(text))
    return "zh" if cjk and cjk >= len(_c.words(text, digits=False)) else "en"


def features(text):
    t = str(text or "")
    nums = _NUM.findall(t)
    body = t.rstrip(" 。.!！?？")
    return {"cjk": len(_CJK.findall(t)), "digit": sum(len(re.sub(r"\D", "", n)) for n in nums),
            "latin_word": len(_c.words(_NUM.sub(" ", t), digits=False)),
            "comma": len(re.findall(r"[，、,]", body)), "colon": len(re.findall(r"[：；:;]", body)),
            "stop": len(re.findall(r"[。！？.!?]", body))}


def beat_seconds(text, lang="zh", speed=1.0, first=False):
    """Predicted seconds of one beat's clip — the spoken line PLUS the pause the film adds after it."""
    c, f, sp = _coef(lang), features(text), max(0.5, float(speed or 1.0))
    spoken = (c["cjk"] * f["cjk"] + c["digit"] * f["digit"] + c["latin_word"] * f["latin_word"]) / sp
    return spoken + c["comma"] * f["comma"] + c["colon"] * f["colon"] + c["stop"] * f["stop"] + c["beat"] + \
        (c["first"] if first else 0.0)


def budget_chars(seconds, lang="zh", speed=1.0, first=False):
    """How many characters (CJK) or words (Latin) a beat of `seconds` holds, with one comma in it."""
    c = _coef(lang)
    room = seconds - c["beat"] - c["comma"] - (c["first"] if first else 0.0)
    per = c["cjk"] if c is ZH else c["latin_word"]
    return max(0, int(room * float(speed or 1.0) / per))


def _seam_seconds(meta, tier):
    if tier != "remotion":
        return 0.0
    try:
        sys.path.insert(0, _HERE)
        import render_remotion as rr
        return rr._REMOTION2_TR / float((meta or {}).get("fps") or 30)
    except Exception:                                         # noqa: BLE001 — fall back to the documented 12 frames
        return 12 / 30.0


def film(board):
    """{beats: [{index, predicted, measured, chars}], total, measured_total, target, calibrated, lang}."""
    meta = board.get("meta") or {}
    slides = [s for s in board.get("slides") or [] if isinstance(s, dict)]
    lang, speed = film_language(meta, slides), meta.get("tts_speed") or 1.0
    tier = "remotion" if meta.get("renderer") in ("remotion", "remotion-bespoke") else "html"
    rows = []
    for i, s in enumerate(slides):
        text = s.get("narration") or ""
        d = s.get("duration")
        rows.append({"index": s.get("index", i + 1), "predicted": beat_seconds(text, lang, speed, first=(i == 0)),
                     "measured": float(d) if isinstance(d, (int, float)) and d > 0 else None,
                     "chars": features(text)["cjk"] or features(text)["latin_word"]})
    import stage_runs as _sr                    # a beat continuing a stage run has no seam before it
    cuts = max(0, len(rows) - 1) - sum(_sr.joined_flags(slides)[1:]) if len(rows) == len(slides) else max(0, len(rows) - 1)
    seams = _seam_seconds(meta, tier) * cuts
    total = sum(r["measured"] if r["measured"] is not None else r["predicted"] for r in rows) - seams
    measured = all(r["measured"] is not None for r in rows) and bool(rows)
    tgt = meta.get("target_seconds")
    return {"beats": rows, "total": total, "measured": measured, "target": tgt, "lang": lang,
            "calibrated": _base(lang) in CALIBRATED, "seams": seams}


def overrun_warning(board, tolerance=0.15):
    """A sentence for validate when the predicted film misses meta.target_seconds by more than `tolerance`, else None."""
    f = film(board)
    tgt = f["target"]
    if not isinstance(tgt, (int, float)) or tgt <= 0 or not f["beats"]:
        return None
    if abs(f["total"] - tgt) <= tolerance * tgt:
        return None
    worst = sorted(f["beats"], key=lambda r: -(r["measured"] or r["predicted"]))[:3]
    return ("length: the film %s %.0f s against meta.target_seconds %d (%+.0f%%)%s — every beat carries ~%.1f s of "
            "pause the script does not show. Cut words or beats (longest: %s), or set the target the film needs. "
            "`python3 scripts/pace.py <out_dir>` lists every beat." % (
                "measures" if f["measured"] else "is predicted at", f["total"], tgt, 100.0 * (f["total"] / tgt - 1),
                "" if f["calibrated"] or f["measured"] else " (pace UNCALIBRATED for %r — a default rate)" % f["lang"],
                _coef(f["lang"])["beat"],
                ", ".join("beat %s %.1f s" % (r["index"], r["measured"] or r["predicted"]) for r in worst)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--budget", type=float, help="seconds of one beat: print how much narration it holds")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args(argv)
    if a.budget:
        n = budget_chars(a.budget, a.lang, a.speed)
        unit = "Chinese characters" if _coef(a.lang) is ZH else "words"
        print("[pace] a %.1f s beat holds about %d %s of narration (with one comma; ~%.1f s of it is the pause after "
              "the beat)%s" % (a.budget, n, unit, _coef(a.lang)["beat"],
                               "" if _base(a.lang) in CALIBRATED else " — UNCALIBRATED for %r" % a.lang))
        return 0
    if not a.out_dir:
        ap.print_help()
        return 2
    board = json.load(open(os.path.join(a.out_dir, "storyboard.json"), encoding="utf-8"))
    f = film(board)
    for r in f["beats"]:
        print("  beat %-3s %4d chars  predicted %5.1f s%s" % (r["index"], r["chars"], r["predicted"],
              "   measured %5.1f s" % r["measured"] if r["measured"] is not None else ""))
    tgt = f["target"]
    print("[pace] film %s %.1f s%s%s" % ("MEASURED" if f["measured"] else "predicted", f["total"],
          (" against target %s s (%+.0f%%)" % (tgt, 100.0 * (f["total"] / tgt - 1))) if tgt else "",
          "" if f["calibrated"] or f["measured"] else " — UNCALIBRATED for %r: a default rate" % f["lang"]))
    w = overrun_warning(board)
    if w:
        print("[pace] WARN " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
