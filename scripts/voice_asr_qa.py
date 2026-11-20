#!/usr/bin/env python3
"""voice_asr_qa — does the voice say what the script says, when the captions say it? Heard back by a speech recogniser.

    python3 scripts/voice_asr_qa.py <film_dir> [--model small] [--json]

Transcribes the film's voice track once (audio/voice.wav, else the plan video's audio) with faster-whisper, word
timestamps on, on the film's own clock, and holds every line of timeline.json against what was heard inside its span:
  - DROPPED / MISREAD (red): three or more script words in a row not heard (a skipped clause, a garbled name, a line
    cut short by a trim); fewer is a place to LISTEN (warn): a recogniser mishears single words, a voice rarely drops one;
  - EXTRA (red): three or more words heard that the line does not have (a repeated phrase, a doubled take);
  - DRIFT (red): the line's words heard more than DRIFT s off the times the captions use (median over its matched
    words): captions running ahead of or behind the voice.
Numbers are compared as numbers ("sixty-four million" = "64 million", 六十 = 60, percent = %), and a line's
lexicon.json respelling ({written: spoken}) is accepted as well as its written form.

WHY. No agent can listen: a misread word, a skipped clause or captions drifting from the voice reached the user
unheard (every film's NOTES: "I could not listen to the audio myself"). The recogniser is an ear that writes down what
it heard. Measured on the MRI film (2026-11-20): 127 s of voice transcribed in about 40 s on a laptop CPU.
Needs faster-whisper (`pip install faster-whisper`; the model downloads once). Without it: NOT MEASURED, exit 2, never
a silent pass. Exit 0 clean (listen-warnings printed), 1 red, 2 usage error / not measured.
"""
import difflib
import json
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

DRIFT = 0.35        # s; a caption this far off its word is seen (a recogniser's word times are good to ~0.1-0.2 s)
RUN = 3             # words in a row: a dropped or extra phrase, not a misheard word
HEARD_V = 4         # what a cached result was heard with: a change to how the voice is heard invalidates it
_USAGE = "usage: voice_asr_qa.py <film_dir> [--model small] [--json]"
_CJK = re.compile(r"[㐀-鿿豈-﫿]")
_EN_NUM = set(("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
               "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand "
               "million billion trillion point").split())
_ZH_NUM = set("零〇一二两三四五六七八九十百千万亿点")


def tokens(text, zh):
    """[(token, index of the source word)] — words in English, characters in Chinese; every number one '#'."""
    out = []
    text = text.replace("百分之", " ").replace("%", " " if zh else " percent ")   # 百分之六十 = 60% = sixty percent
    for wi, w in enumerate(text.split()):
        parts = re.findall(r"[㐀-鿿豈-﫿]|[0-9][0-9.,]*|[a-zA-Z]+(?:'[a-z]+)?", w.lower().replace("-", " "))
        sound = _sounds(parts) if zh else parts
        for p, snd in zip(parts, sound):
            num = p[0].isdigit() or p in _EN_NUM or (zh and p in _ZH_NUM)
            tok = "#" if num else (p[:-1] if not zh and len(p) > 3 and p.endswith("s") and not p.endswith("ss") else snd)
            if tok == "#" and out and out[-1][0] == "#":
                continue                                    # "sixty four million" / 六十四 / 64,000: one number
            # "a hundred and twenty" = 120: the article before a number word and the "and" inside one belong to it
            if tok == "#" and out and out[-1][0] in ("a", "and") and (len(out) < 2 or out[-1][0] == "a" or out[-2][0] == "#"):
                out[-1] = ("#", out[-1][1])
                if len(out) >= 2 and out[-2][0] == "#":
                    out.pop()
                continue
            out.append((tok, wi))
    return out


def _sounds(parts):
    """Chinese compared by what is SAID: each character as its toneless pinyin, read in its phrase (多音字 by context).
    A recogniser writes a homophone as often as the script's character (河/和, 蛇/舌, 代/带: 24 false "misheard" words
    on the Shenzhen film), while a real misreading changes the sound (银行 read as 银星). Without pypinyin: the
    characters themselves."""
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return parts
    out, run = list(parts), []
    for i, p in enumerate(parts + [""]):
        if p and _CJK.match(p):
            run.append(i)
            continue
        if run:
            for j, py in zip(run, lazy_pinyin("".join(parts[k] for k in run))):
                out[j] = py
            run = []
    return out


_LATIN = re.compile(r"^[a-z]+$")


def _join_latin(toks, times):
    """In a Chinese line, English heard in fragments ("sk" "ill", "c" "ode" "x") joined into one word, as the script's
    letters are: the recogniser splits a word it hears inside Chinese speech. Pinyin syllables are never joined (a
    character's sound is one token only on the script side)."""
    out, ot = [], []
    for t, tm in zip(toks, times):
        if out and _LATIN.match(t) and _LATIN.match(out[-1]) and not _is_syllable(t) and not _is_syllable(out[-1]):
            out[-1] += t
            continue
        out.append(t)
        ot.append(tm)
    return out, ot


def _join_latin_tokens(st):
    out = []
    for tok, wi in st:
        if out and _LATIN.match(tok) and _LATIN.match(out[-1][0]) and not _is_syllable(tok) and not _is_syllable(out[-1][0]):
            out[-1] = (out[-1][0] + tok, out[-1][1])
            continue
        out.append((tok, wi))
    return out


_PINYIN = None


def _is_syllable(t):
    """A toneless pinyin syllable (the sound of one Chinese character), as _sounds writes them."""
    global _PINYIN
    if _PINYIN is None:
        try:
            from pypinyin.constants import PINYIN_DICT
            from pypinyin import lazy_pinyin
            _PINYIN = {lazy_pinyin(chr(c))[0] for c in list(PINYIN_DICT)[:30000]}
        except Exception:
            _PINYIN = set()
    return t in _PINYIN


def _decode(path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                       capture_output=True)
    if p.returncode or not p.stdout:
        raise SystemExit("voice_asr_qa: could not decode the audio of %s" % path)
    return np.frombuffer(p.stdout, np.float32)


_MODELS = {}


def hear(audio, zh, model="small", offset=0.0):
    """[(word, start s)] heard in the audio, on its own clock plus `offset`."""
    from faster_whisper import WhisperModel
    if model not in _MODELS:
        _MODELS[model] = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=max(2, (os.cpu_count() or 4) // 2))
    # a Chinese voice is written down in traditional characters as often as not (這裡 for 这里, 萬 for 万: every one a
    # false "misheard" on the Shenzhen film); a simplified sentence as the prompt keeps it in the script's own script
    segs, _ = _MODELS[model].transcribe(audio, language="zh" if zh else "en", word_timestamps=True, beam_size=5,
                                        condition_on_previous_text=False,
                                        initial_prompt="以下是普通话的句子，使用简体中文。" if zh else None)
    return [(w.word.strip(), float(w.start) + offset) for s in segs for w in (s.words or []) if w.word.strip()]


def judge_line(line, heard, zh, lexicon):
    """{line, ratio, dropped, extra, listen, drift} for one timeline line against the words heard on the clock."""
    a, b = float(line["start"]), float(line["end"])
    # a recogniser starts a phrase's first word early (up to ~0.5 s at a segment's start); the neighbours' words this
    # takes in sit at the window's edges and are not judged
    near = [(w, t) for w, t in heard if a - 0.6 <= t <= b + 0.2]
    script_words = line.get("words") or [{"w": w, "t": a} for w in line["text"].split()]
    variants = [line["text"]]
    spoken = line["text"]
    for k, v in (lexicon or {}).items():
        spoken = spoken.replace(k, v)
    if spoken != line["text"]:
        variants.append(spoken)
    htoks, htimes = [], []
    for w, t in near:
        for tok, _ in tokens(w, zh):
            if not (tok == "#" and htoks and htoks[-1] == "#"):
                htoks.append(tok)
                htimes.append(t)
    if zh:
        htoks, htimes = _join_latin(htoks, htimes)
    best = None
    for vi, text in enumerate(variants):
        st = tokens(text, zh)
        if zh:
            st = _join_latin_tokens(st)
        sm = difflib.SequenceMatcher(None, [x[0] for x in st], htoks, autojunk=False)
        if best is None or sm.ratio() > best[1].ratio():
            best = (st, sm, vi)
    st, sm, vi = best
    wtime = [w["t"] for w in script_words]
    # word times line up with the written words only (a respelling changes the count)
    timed = vi == 0 and line.get("words") is not None and len(line["text"].split()) == len(wtime)
    res = {"line": line.get("id", ""), "text": line["text"], "ratio": round(sm.ratio(), 3), "dropped": [], "extra": [],
           "listen": [], "drift": None}
    ops = sm.get_opcodes()
    offs = []
    for k, (op, i1, i2, j1, j2) in enumerate(ops):
        said = " ".join(x[0] for x in st[i1:i2])
        got = " ".join(htoks[j1:j2])
        if op == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                if timed:
                    offs.append(htimes[j] - wtime[st[i][1]])
            continue
        edge = k == 0 or k == len(ops) - 1          # the window's edges overlap the next line's words
        if op in ("delete", "replace") and i2 - i1 >= RUN:
            res["dropped"].append({"said": said, "heard": got})
        elif op == "insert" and j2 - j1 >= RUN and not edge:
            res["extra"].append(got)
        elif op in ("delete", "replace") or (op == "insert" and not edge):
            res["listen"].append({"said": said, "heard": got})
    if len(offs) >= 3:
        res["drift"] = round(float(np.median(offs)), 3)
    return res


def main(argv):
    _c.refuse_unknown(argv, valued=("model",), switches=("json",), usage=_USAGE)
    model = _c.argflag(argv, "model", "small")
    args = [a for a in argv if not a.startswith("--") and a != model]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    tp = os.path.join(d, "timeline.json")
    if not os.path.isfile(tp):
        print("voice_asr_qa: no timeline.json in %s" % d, file=sys.stderr)
        return 2
    tl = json.load(open(tp, encoding="utf-8"))
    src = os.path.join(d, "audio", "voice.wav")
    if not os.path.isfile(src):
        pp = os.path.join(d, "_plan.json")
        src = os.path.join(d, json.load(open(pp, encoding="utf-8")).get("video", "final.mp4")) if os.path.isfile(pp) else ""
    if not os.path.isfile(src):
        print("voice_asr_qa: no audio/voice.wav and no film video in %s" % d, file=sys.stderr)
        return 2
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        print("[voice_asr_qa] NOT MEASURED — faster-whisper is not installed (pip install faster-whisper)")
        return 2
    text = " ".join(l["text"] for l in tl.get("lines") or [])
    zh = len(_CJK.findall(text)) > 0.3 * max(1, len(re.sub(r"\s", "", text)))
    lp = os.path.join(d, "lexicon.json")
    lexicon = json.load(open(lp, encoding="utf-8")) if os.path.isfile(lp) else {}
    if isinstance(lexicon, dict) and "words" in lexicon and isinstance(lexicon["words"], dict):
        lexicon = lexicon["words"]
    # heard once per voice: the voice is checked at step 4 and rarely changes after, so film_qc's run reads that
    # result instead of transcribing again (the recogniser took half the cores beside picture_glide_qa: +69 s)
    key = [_stamp(src), _stamp(tp), _stamp(lp), model, HEARD_V]
    cp = os.path.join(d, "_voice_qc.json")
    cached = None
    if os.path.isfile(cp):
        try:
            c = json.load(open(cp, encoding="utf-8"))
            cached = c["rows"] if c.get("key") == key else None
        except (ValueError, KeyError):
            cached = None
    rows = cached if cached is not None else _judge_all(d, src, tl, zh, lexicon, model)
    if cached is None:
        with open(cp + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"key": key, "rows": rows}, f, ensure_ascii=False)
        os.replace(cp + ".tmp", cp)
    return _report(rows, argv, cached is not None)


def _stamp(p):
    return [os.path.getmtime(p), os.path.getsize(p)] if os.path.isfile(p) else None


def _judge_all(d, src, tl, zh, lexicon, model):
    audio = _decode(src)
    heard = hear(audio, zh, model)
    lex = lexicon if isinstance(lexicon, dict) else {}
    rows = []
    for l in tl.get("lines") or []:
        r = judge_line(l, heard, zh, lex)
        # a recogniser running over the whole film can skip a stretch it did hear (whisper dropped the end of a line and
        # all of the next on the job-hunt film, both voiced at -23 dB): a line found short is heard again on its own
        # before it is called dropped
        if r["dropped"] or r["extra"]:
            a0 = max(0.0, float(l["start"]) - 0.6)
            again = hear(audio[int(a0 * 16000):int((float(l["end"]) + 0.3) * 16000)], zh, model, offset=a0)
            r2 = judge_line(l, again, zh, lex)
            if len(r2["dropped"]) + len(r2["extra"]) < len(r["dropped"]) + len(r["extra"]):
                r = r2
        rows.append(r)
    return rows


def _report(rows, argv, cached):
    red = [r for r in rows if r["dropped"] or r["extra"] or (r["drift"] is not None and abs(r["drift"]) > DRIFT)]
    if "--json" in argv:
        print(json.dumps({"lines": rows, "red": [r["line"] for r in red]}, ensure_ascii=False))
        return 1 if red else 0
    for r in rows:
        for x in r["dropped"]:
            print("DROPPED  %-5s said %r, heard %r" % (r["line"], x["said"], x["heard"] or "nothing"))
        for x in r["extra"]:
            print("EXTRA    %-5s heard %r, not in the line" % (r["line"], x))
        if r["drift"] is not None and abs(r["drift"]) > DRIFT:
            print("DRIFT    %-5s the voice is %+.2f s off its captions" % (r["line"], r["drift"]))
        for x in r["listen"]:
            print("WARN listen %-5s said %r, heard %r (a recogniser mishears single words: listen before changing)"
                  % (r["line"], x["said"], x["heard"] or "nothing"))
    drifts = [r["drift"] for r in rows if r["drift"] is not None]
    print("[voice_asr_qa] %s  %d line(s), %d red; median match %.2f; caption offset median %+.2f s%s"
          % ("OK" if not red else "RED", len(rows), len(red), float(np.median([r["ratio"] for r in rows])) if rows else 0,
             float(np.median(drifts)) if drifts else 0.0, " (the voice, timeline and lexicon unchanged since it was heard)" if cached else ""))
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
