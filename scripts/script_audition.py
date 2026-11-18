#!/usr/bin/env python3
"""SCRIPT AUDITION — hear the narration before anyone approves it.

THE DEFECT THIS EXISTS FOR. A 37-beat Chinese film cleared every voice metric — sentence-length CV 0.45,
antithesis 8%, connectives 38%, aphorism endings 5%, balanced pairs 5% — passed two independent content
critics, and was read end-to-end by the author. The person it was made for watched the rendered film and
said, of the first listen: 「脚本没有人的感觉，读起来也很机器」. Every check in the pipeline READS the
narration. The defect is AUDIBLE. Nothing in the pipeline had ever heard it.

`references/anti-ai-voice.md` had said so in its own opening line the whole time — "the last pass is
always a human read-aloud" — and there was no step, no gate and no artifact for it, which is the same
shape as a capability that is complete and unreached: on screen, indistinguishable from absent.

WHY IT GOES BEFORE THE SCRIPT CHECKPOINT. The workflow's order was write -> critics -> the user approves
the script -> synthesize. So the user approved, by reading, a document whose only destiny is to be heard.
This makes the audio exist first, so the 🔴 checkpoint is a listen rather than a read. It costs seconds:
five beats through the film's OWN voice, not a stand-in.

WHAT IT PICKS, AND WHY THOSE. The beats a film lives or dies on — its hook, its climax, its close — plus
two from the middle, because the failure this caught is a RHYTHM that only shows across consecutive
beats. A single beat always sounds fine; it is the third one in the same shape that gives it away. The
gaps between them are the film's own measured scene pause, so what you hear is the cut's real pacing.

TIER-AGNOSTIC BY CONSTRUCTION. It reads `storyboard.json`'s `slides[].narration` and `meta.voice`, which
both the html tier and the remotion tier carry. Nothing here knows what a register or an HTML page is.
"""
import argparse
import json
import re
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tts as _tts                                                          # noqa: E402

# How many beats to audition. Five is the smallest number that can expose a REPEATED shape: with three
# you hear a device, with five you hear a habit. It is also short enough that nobody skips listening.
AUDITION_BEATS = 5
MIN_BEATS = 2


def pick(slides):
    """The beats a listener judges the film by: hook, climax, close, and two from the middle.

    Returns [(index, narration)]. A board with no `climax`/`hold` marks still gets a spread rather than
    the first five, because the first five of any film are its easiest minute.
    """
    spoken = [s for s in slides if (s.get("narration") or "").strip()]
    if len(spoken) <= AUDITION_BEATS:
        return [(s.get("index", i), s["narration"]) for i, s in enumerate(spoken)]
    want, seen = [], set()

    def take(s):
        if s is not None and id(s) not in seen:
            seen.add(id(s))
            want.append(s)

    take(spoken[0])                                                          # the hook
    take(next((s for s in spoken if s.get("climax")), None))                 # the payoff
    take(next((s for s in reversed(spoken) if s.get("hold")), None) or spoken[-1])   # the close
    # ...and fill from the middle, spread, because a rhythm shows across CONSECUTIVE beats. Adjacent
    # pairs are deliberate: two beats in a row is what exposes a repeated opener. The pair is taken from the
    # CENTRE of the film: from the start it repeated the hook's neighbourhood (a director script auditioned lines
    # 1-4 and nothing of its middle).
    mid = [s for s in spoken[1:-1] if id(s) not in seen]
    step = max(1, len(mid) // max(1, AUDITION_BEATS - len(want)))
    centre = max(0, len(mid) // 2 - 1)
    for s in (mid[centre:] + mid[:centre])[::step]:
        if len(want) >= AUDITION_BEATS:
            break
        take(s)
        nxt = spoken[spoken.index(s) + 1] if spoken.index(s) + 1 < len(spoken) else None
        if nxt is not None and len(want) < AUDITION_BEATS:
            take(nxt)
    want.sort(key=lambda s: s.get("index", 0))
    return [(s.get("index", 0), s["narration"]) for s in want]


def named(slides, beats):
    """[(index, narration)] for the board indices in `beats`, in the order given — or RuntimeError naming the first one
    that is not a beat or has nothing to say (a re-listen to a rewrite must hear exactly the rewritten beats)."""
    by_index = {s.get("index", i): s for i, s in enumerate(slides)}
    out = []
    for b in beats:
        s = by_index.get(b)
        if s is None:
            raise RuntimeError("beat %s is not on the board (its indices run %s..%s)"
                               % (b, min(by_index, default="-"), max(by_index, default="-")))
        if not (s.get("narration") or "").strip():
            raise RuntimeError("beat %s has no narration — there is nothing in it to hear" % b)
        out.append((b, s["narration"]))
    return out


def parse_beats(text):
    """`--beats 9,13,24` -> [9, 13, 24]; ValueError on anything that is not a list of board indices."""
    return [int(x) for x in str(text).replace(" ", "").split(",") if x != ""]


CLIMAX_WORDS = re.compile(r"\b(payoff|pay-off|climax)\b", re.I)   # a sequence NAME carrying it ("payoff · 同一件事")


def load(out_dir):
    """(meta, slides) for the film in out_dir, from EITHER flow: the classic `storyboard.json` (meta + slides), or the
    director path's `script.json` ({voice, language?, sequences: [{name, lines: [{id, text}]}]}). A director line becomes
    a slide numbered 1.. in script order, carrying its `id`; the first line of a sequence named payoff / climax / reveal
    is the climax, the last line the close. Raises RuntimeError when the folder has neither."""
    board = os.path.join(out_dir, "storyboard.json")
    if os.path.isfile(board):
        data = json.load(open(board, encoding="utf-8"))
        return data.get("meta") or {}, data.get("slides") or []
    sp = os.path.join(out_dir, "script.json")
    if not os.path.isfile(sp):
        raise RuntimeError("no storyboard.json or script.json in %s — there is no script to audition" % out_dir)
    sc = json.load(open(sp, encoding="utf-8"))
    slides, n, seqs = [], 0, []
    for seq in sc.get("sequences") or []:
        lines = [ln for ln in seq.get("lines") or [] if (ln.get("text") or "").strip()]
        first = None
        for k, ln in enumerate(lines):
            n += 1
            s = {"index": n, "id": ln.get("id") or "l%02d" % n, "narration": ln["text"]}
            if k == 0:
                first = s
                if CLIMAX_WORDS.search(str(seq.get("name", ""))) and not any(x.get("climax") for x in slides):
                    s["climax"] = True
            slides.append(s)
        if first is not None:
            seqs.append((first, len(lines)))
    if slides and not any(s.get("climax") for s in slides):      # no payoff named: the line ~70 % through
        slides[min(len(slides) - 2, int(len(slides) * 0.7))]["climax"] = True
    if seqs:   # the close: the final sequence's first line (its tagline), not a trailing disclaimer or credit
        last_first, count = seqs[-1]
        (last_first if count > 1 else slides[-1])["hold"] = True
    meta = {"voice": sc.get("voice") or "auto", "language": sc.get("language") or "auto"}
    return meta, slides


def audition(out_dir, beats=None, out_name="audition.mp3", allow_paid=False, voice=None):
    """Synthesize the picked beats through the board's OWN voice and join them with its own pause.

    Returns (path, picked, voice). Raises RuntimeError when no engine can speak — never returns a silent
    file, because a checkpoint that passes on silence is the defect this script exists to prevent.

    THE FILM'S OWN PATH, not a copy of it: the voice comes from `tts.film_voice` and every clip from
    `tts.speak`, the two functions `tts.synthesize` itself uses. The copy this replaced resolved the voice
    without detecting the language (an unset `meta.language` auditioned a Chinese script in the English
    `say:Samantha` while the film spoke edge Xiaoxiao) and skipped the pronunciation layer (the audition
    said "AI" where the film says "A-I" — the one reading a listener here chose BY EAR).

    A PAID engine (OpenAI, MiniMax) is spoken only with `allow_paid=True`: the voice is chosen at this
    checkpoint, and an audition on a key must follow that choice, not a board that merely carries one.
    """
    meta, slides = load(out_dir)
    if voice:                                    # a candidate voice auditioned at the checkpoint, the script untouched
        meta = dict(meta, voice=voice)
    picked = named(slides, beats) if beats else pick(slides)
    if not beats and len(picked) < MIN_BEATS:
        raise RuntimeError("only %d beat(s) carry narration — there is nothing to audition yet" % len(picked))

    prov, name, lang, _note = _tts.film_voice(meta, slides)
    voice = "%s:%s" % (prov, name)
    if prov in _tts.PAID_PROVIDERS and not allow_paid:
        raise RuntimeError(
            "meta.voice is %s, a PAID engine: this audition would synthesize %d beat(s), %d characters, on "
            "the user's key. Re-run with --allow-paid once the user has chosen this voice — do NOT approve "
            "a script nobody heard." % (voice, len(picked), sum(len(t) for _i, t in picked)))
    spoken_meta = dict(meta, language=lang)
    work = os.path.join(out_dir, ".audition")
    os.makedirs(work, exist_ok=True)
    parts = []
    for n, (idx, text) in enumerate(picked):
        p = os.path.join(work, "%02d.%s" % (n, "aiff" if prov == "say" else "mp3"))
        try:
            # the same transient-failure retry the film gets — never a different voice, only a second ask
            _tts.speak_retrying(text, p, spoken_meta, prov, name)
        except Exception as exc:                                             # noqa: BLE001 — name the beat
            raise RuntimeError("%s could not speak beat %s (%s)%s — nothing was auditioned"
                               % (voice, idx, exc, _tts.failure_hint(prov, exc))) from exc
        if not (os.path.exists(p) and os.path.getsize(p) > 0):
            raise RuntimeError("the engine produced no audio for beat %s — nothing was auditioned" % idx)
        parts.append(p)

    gap = _tts._tail_pad(meta)                                               # the film's own seam, not 0
    # DECODED and resampled, then joined (the concat FILTER): the concat demuxer needs every file in one format, and
    # a `say` voice writes AIFF at its own rate — joined to a 48 kHz mp3 gap, the pauses came out as noise (audit
    # 2026-11-15, step 8). Every engine's output is brought to 48 kHz mono first.
    out = os.path.join(out_dir, out_name)
    ins, chain, labels = [], [], []
    for i, p in enumerate(parts):
        ins += ["-i", p]
        chain.append("[%d:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono[p%d]" % (i, i))
        labels.append("[p%d]" % i)
        if i < len(parts) - 1:
            chain.append("anullsrc=r=48000:cl=mono,atrim=0:%.3f,aformat=sample_fmts=fltp[g%d]" % (gap, i))
            labels.append("[g%d]" % i)
    chain.append("%sconcat=n=%d:v=0:a=1[out]" % ("".join(labels), len(labels)))
    subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(chain), "-map", "[out]",
                    "-c:a", "libmp3lame", "-ar", "48000", "-ac", "1", out], check=True)
    return out, picked, voice


def main():
    ap = argparse.ArgumentParser(
        description="Synthesize a few representative beats so a PERSON can hear the script before "
                    "approving it. Every other voice check reads; this one is the only thing that "
                    "listens.")
    ap.add_argument("out_dir")
    ap.add_argument("--name", default="audition.mp3")
    ap.add_argument("--beats", type=parse_beats, default=None,
                    help="audition exactly these board indices, in this order (e.g. 9,13,24 — the beats you rewrote); "
                         "default: hook, climax, close and two from the middle")
    ap.add_argument("--allow-paid", action="store_true",
                    help="speak through a paid engine (OpenAI/MiniMax) — only once the user has chosen it")
    ap.add_argument("--voice", default=None,
                    help="audition THIS voice (edge:<id> | minimax:<id> | openai:<voice> | say:<name>) without changing "
                         "the script: the candidates at the voice checkpoint")
    a = ap.parse_args()
    try:
        path, picked, voice = audition(a.out_dir, beats=a.beats, out_name=a.name, allow_paid=a.allow_paid, voice=a.voice)
    except Exception as exc:                                                 # noqa: BLE001 — report, never skip
        print("[audition] COULD NOT AUDITION — %s" % exc)
        print("[audition] Do not treat the script checkpoint as met: nobody has heard this script.")
        return 2
    print("[audition] %s  ·  %d beat(s) through %s, joined by the film's own %.2fs pause"
          % (path, len(picked), voice, _tts._tail_pad(load(a.out_dir)[0])))
    ids = {s["index"]: s.get("id") for s in load(a.out_dir)[1]}
    for idx, text in picked:
        print("   beat %-3s %s%s" % (idx, "(%s) " % ids[idx] if ids.get(idx) else "", text[:54]))   # board index / line id
    print("[audition] LISTEN to it, in order, before the script checkpoint. The metrics in voice_qa "
          "measure distribution; they cannot hear that a script is dead.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
