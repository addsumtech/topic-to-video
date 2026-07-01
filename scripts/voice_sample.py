"""Audition MiniMax voices before committing. Synthesizes a short sample for each curated human-like
candidate (per language + gender) into <out_dir>/voice_samples/ so the user can listen and pick the
one they like, then set meta.voice = "minimax:<voice_id>".

Usage:
  MINIMAX_API_KEY=... python scripts/voice_sample.py <out_dir> [--gender female|male]
                                                     [--lang en] [--text "..."] [--model speech-2.8-hd]

Reads meta.language / meta.tts_model from <out_dir>/storyboard.json when present. Never persists the key.
"""
import argparse, os, re, json
import tts
import _common


def _safe(voice_id):
    return re.sub(r"[^A-Za-z0-9]+", "_", voice_id).strip("_")


def _sample_text(out_dir, lang):
    """A representative line to speak — the deck's first real narration if available, else a default."""
    try:
        d = json.load(open(os.path.join(out_dir, "storyboard.json")))
        for s in d.get("slides", []):
            n = (s.get("narration") or "").strip()
            if len(n) >= 12:
                return n
    except (OSError, ValueError):
        pass
    return ("你好,这是语音样例,用来挑选最自然、最像真人的声音。" if lang == "zh"
            else "Hi — this is a short sample so you can pick the voice that sounds most natural to you.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--gender", choices=["female", "male"], default=None)
    ap.add_argument("--lang", default=None)
    ap.add_argument("--text", default=None)
    ap.add_argument("--model", default=None)
    a = ap.parse_args()

    meta = {}
    try:
        meta = json.load(open(os.path.join(a.out_dir, "storyboard.json"))).get("meta", {})
    except (OSError, ValueError):
        pass
    lang = a.lang or meta.get("language", "en")
    gender = a.gender or meta.get("voice_gender", "female")
    model = a.model or meta.get("tts_model") or tts.MINIMAX_DEFAULT_MODEL
    text = a.text or _sample_text(a.out_dir, lang)

    cands = tts.minimax_voice_candidates(lang, gender)
    if not cands:
        print(f"No curated candidates for language={lang} gender={gender}. "
              f"Pick any voice_id from platform.minimax.io/docs/faq/system-voice-id.")
        return
    sdir = os.path.join(a.out_dir, "voice_samples")
    os.makedirs(sdir, exist_ok=True)
    m = {"language": lang, "tts_model": model}
    print(f"Synthesizing {len(cands)} {gender} {lang} samples (model {model}) into {sdir}/ …")
    ok = []
    for vid in cands:
        out = os.path.join(sdir, f"{_safe(vid)}.mp3")
        try:
            tts._minimax(text, out, vid, m)
            dur = _common.audio_duration(out)
            print(f"  ✓ {vid:42s} -> {os.path.basename(out)}  ({dur:.1f}s)")
            ok.append(vid)
        except Exception as e:
            print(f"  ✗ {vid:42s} FAILED: {repr(e)[:120]}")
    print(f"\nListen (e.g. `open {sdir}`), then set  meta.voice = \"minimax:<voice_id>\"  for the one you like.")
    if ok:
        print("Candidates:", " · ".join(ok))


if __name__ == "__main__":
    main()
