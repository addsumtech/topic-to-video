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
    # pairs are deliberate: two beats in a row is what exposes a repeated opener.
    mid = [s for s in spoken[1:-1] if id(s) not in seen]
    step = max(1, len(mid) // max(1, AUDITION_BEATS - len(want)))
    for s in mid[::step]:
        if len(want) >= AUDITION_BEATS:
            break
        take(s)
        nxt = spoken[spoken.index(s) + 1] if spoken.index(s) + 1 < len(spoken) else None
        if nxt is not None and len(want) < AUDITION_BEATS:
            take(nxt)
    want.sort(key=lambda s: s.get("index", 0))
    return [(s.get("index", 0), s["narration"]) for s in want]


def audition(out_dir, beats=None, out_name="audition.mp3"):
    """Synthesize the picked beats through the board's OWN voice and join them with its own pause.

    Returns (path, picked, voice). Raises RuntimeError when no engine can speak — never returns a silent
    file, because a checkpoint that passes on silence is the defect this script exists to prevent.
    """
    board = os.path.join(out_dir, "storyboard.json")
    data = json.load(open(board, encoding="utf-8"))
    meta = data.get("meta") or {}
    picked = pick(data.get("slides") or [])
    if len(picked) < MIN_BEATS:
        raise RuntimeError("only %d beat(s) carry narration — there is nothing to audition yet" % len(picked))

    voice = _tts._resolve_voice(meta)
    work = os.path.join(out_dir, ".audition")
    os.makedirs(work, exist_ok=True)
    parts = []
    for n, (idx, text) in enumerate(picked):
        p = os.path.join(work, "%02d.mp3" % n)
        prov, _, name = voice.partition(":")
        if prov == "edge":
            _tts._edge(text, p, name, _tts._edge_rate(meta))
        elif prov == "say":
            _tts._say(text, p.replace(".mp3", ".aiff"), name)
            p = p.replace(".mp3", ".aiff")
        else:                                                                # a cloud engine this run has
            raise RuntimeError(                                              # no key for: say so, loudly
                "meta.voice is %r and this audition only drives edge/say directly. Run tts.py first and "
                "audition from audio/, or set a local voice — do NOT approve a script nobody heard." % voice)
        if not (os.path.exists(p) and os.path.getsize(p) > 0):
            raise RuntimeError("the engine produced no audio for beat %d — nothing was auditioned" % (idx + 1))
        parts.append(p)

    gap = _tts._tail_pad(meta)                                               # the film's own seam, not 0
    lst = os.path.join(work, "list.txt")
    sil = os.path.join(work, "gap.mp3")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=48000:cl=mono", "-t", "%.3f" % gap, sil], check=True)
    with open(lst, "w", encoding="utf-8") as fh:
        for i, p in enumerate(parts):
            fh.write("file '%s'\n" % os.path.abspath(p))
            if i < len(parts) - 1:
                fh.write("file '%s'\n" % os.path.abspath(sil))
    out = os.path.join(out_dir, out_name)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:a", "libmp3lame", "-ar", "48000", "-ac", "1", out], check=True)
    return out, picked, voice


def main():
    ap = argparse.ArgumentParser(
        description="Synthesize a few representative beats so a PERSON can hear the script before "
                    "approving it. Every other voice check reads; this one is the only thing that "
                    "listens.")
    ap.add_argument("out_dir")
    ap.add_argument("--name", default="audition.mp3")
    a = ap.parse_args()
    try:
        path, picked, voice = audition(a.out_dir, out_name=a.name)
    except Exception as exc:                                                 # noqa: BLE001 — report, never skip
        print("[audition] COULD NOT AUDITION — %s" % exc)
        print("[audition] Do not treat the script checkpoint as met: nobody has heard this script.")
        return 2
    print("[audition] %s  ·  %d beat(s) through %s, joined by the film's own %.2fs pause"
          % (path, len(picked), voice, _tts._tail_pad(json.load(
              open(os.path.join(a.out_dir, "storyboard.json"), encoding="utf-8")).get("meta") or {})))
    for idx, text in picked:
        print("   beat %-3d %s" % (idx + 1, text[:54]))
    print("[audition] LISTEN to it, in order, before the script checkpoint. The metrics in voice_qa "
          "measure distribution; they cannot hear that a script is dead.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
