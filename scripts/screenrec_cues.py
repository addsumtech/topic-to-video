#!/usr/bin/env python3
"""screenrec_cues — the sound of a recorded tutorial: a click on every recorded click, a key on every keystroke,
placed on the film second the EDIT plays it.

    python3 scripts/screenrec_cues.py <film_dir> [--rec clips/rec/rec.json] [--page film.html] [--edit E]
        [--until 40.0] [--skip 0,13] [--out audio/cues.json]
    then: python3 scripts/sfx.py --cues audio/cues.json --seconds <duration> --out audio/sfx.wav
          python3 scripts/mix.py --voice audio/voice.wav --sfx audio/sfx.wav --out audio/mix.wav

WHY (2026-11-25, the Numbers tutorial): "我觉得可以适当加一些点击或者打字的声音特效对于这种类似情景" (add some click and
typing sounds in a film like this). Every click and keystroke in an operating-steps film is a real, visible action:
its foley makes each step land. Only those: no sound for a scroll, a hover or a cut (references/promo-shotcraft.md
§4: real foley for visible actions, never game-feedback tones).

TIMING comes from the edit itself, not from the log: the page's ScreenRec edit (`--edit`, the variable holding
ScreenRec.edit(...), default E) is asked for recAt(t) every 1/120 s, and each logged event lands on the first film
second whose recording time reaches it — a held stretch stays silent, a sped-up one stays in sync. Events: a click
at its logged time - 0.08 s (the log is written just after the release), a second one 0.16 s earlier for a
double-click ("clicks": 2), a drag's press 0.5 s after it starts (app_drive glides there first) and its release at
its end, every typed character evenly over the type step (its "text"; without one, about 10 a second), a key at
its logged time - 0.05 s ("return"/"enter" a little louder). --until drops events after the recording's usable end
(seconds); --skip drops actions by index (one before the film, one the edit never shows).

Exit 0 written, 2 usage error or the page failed.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

_USAGE = ("usage: screenrec_cues.py <film_dir> [--rec clips/rec/rec.json] [--page film.html] [--edit E] [--until S] "
          "[--skip i,j] [--out audio/cues.json]")
STEP = 1 / 120.0
GAIN = {"click": 0.55, "release": 0.35, "key": 0.32, "space": 0.22, "enter": 0.5}


def events(rec, until=None, skip=()):
    """[(recording second, cue, gain, what)] for the actions a viewer sees and hears."""
    out = []
    for a in rec["actions"]:
        if a["i"] in skip or (until is not None and a["t"] >= until):
            continue
        k = a["kind"]
        if k == "click":
            out.append((a["t"] - 0.08, "click", GAIN["click"], a.get("label", "")))
            if a.get("clicks", 1) >= 2:
                out.append((a["t"] - 0.24, "click", GAIN["click"], a.get("label", "") + " (first of two)"))
        elif k == "drag":
            out.append((a["t"] + 0.5, "click", GAIN["click"], "drag: press"))
            out.append((a["t_end"] - 0.05, "click", GAIN["release"], "drag: release"))
        elif k == "type":
            text = a.get("text") or "x" * max(1, round((a["t_end"] - a["t"]) * 10))
            dt = (a["t_end"] - a["t"]) / len(text)
            for i, ch in enumerate(text):
                out.append((a["t"] + i * dt, "key", GAIN["space" if ch == " " else "key"], "type %r" % ch))
        elif k == "key":
            loud = a.get("label", "").lower() in ("return", "enter")
            out.append((a["t"] - 0.05, "key", GAIN["enter" if loud else "key"], a.get("label", "")))
    return sorted(out)


def place(evs, ts, rs):
    """Each event on the first film second whose recording time reaches it; events the film never plays drop."""
    cues = []
    for r, cue, gain, what in evs:
        t = next((ts[i] for i in range(1, len(rs)) if rs[i - 1] < r <= rs[i]), None)
        if t is not None and t >= 0:
            cues.append({"t": round(t, 3), "cue": cue, "gain": gain, "what": what})
    return cues


def main(argv):
    valued = ("rec", "page", "edit", "until", "skip", "out")
    _c.refuse_unknown(argv, valued=valued, usage=_USAGE)
    args = [a for a in argv if not a.startswith("--") and a not in [_c.argflag(argv, v, None) for v in valued]]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    rec = json.load(open(os.path.join(d, _c.argflag(argv, "rec", None) or "clips/rec/rec.json")))
    tl = json.load(open(os.path.join(d, "timeline.json")))
    until = _c.argflag(argv, "until", None)
    skip = {int(v) for v in (_c.argflag(argv, "skip", None) or "").split(",") if v.strip()}
    import _filmpage as _fp
    ts = [round(-0.5 + i * STEP, 4) for i in range(int((tl["duration"] + 0.5) / STEP))]
    port, srv = _fp.serve(d)
    try:
        p = _fp.FilmPage(port, _c.argflag(argv, "page", None) or "film.html")
        try:
            rs = json.loads(p.ev("JSON.stringify(%s.map((t) => %s.recAt(t)))" % (
                json.dumps(ts), _c.argflag(argv, "edit", None) or "E")))
        finally:
            p.close()
    except _fp.PageError as e:
        print("screenrec_cues: %s" % e, file=sys.stderr)
        return 2
    finally:
        srv.shutdown()
    cues = place(events(rec, float(until) if until else None, skip), ts, rs)
    out = os.path.join(d, _c.argflag(argv, "out", None) or os.path.join("audio", "cues.json"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(cues, open(out, "w"), indent=0)
    for c in cues:
        print("%7.2f  %-5s %.2f  %s" % (c["t"], c["cue"], c["gain"], c["what"]))
    print("[screenrec_cues] %d cue(s) -> %s" % (len(cues), out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
