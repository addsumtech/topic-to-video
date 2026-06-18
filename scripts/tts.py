"""Narration text -> per-slide audio. Default macOS 'say'; cloud optional.

Voice spec in storyboard meta['voice']:
  "say:Samantha"        -> local macOS say, voice Samantha
  "openai:alloy"        -> OpenAI TTS (needs OPENAI_API_KEY); falls back to say
"""
import argparse, os
import _common
import storyboard as sb

def _say(text, out_path, voice, rate=175):
    # say writes AIFF directly; ffprobe reads its real duration later.
    _common.run(["say", "-v", voice, "-r", str(rate), "-o", out_path, text])

def _openai(text, out_path, voice):
    # Optional upgrade. Lazy import so the skill never hard-depends on it.
    import requests
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("no OPENAI_API_KEY")
    r = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "gpt-4o-mini-tts", "voice": voice, "input": text},
        timeout=60)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)

def _provider(voice_spec):
    if ":" in voice_spec:
        prov, name = voice_spec.split(":", 1)
    else:
        prov, name = "say", voice_spec
    return prov, name

# A sensible default macOS `say` voice per language, so non-English narration isn't
# read by an English voice (which mangles the pronunciation). These are the common
# built-in voices; if one isn't installed, `say` errors and tts.py falls back to
# Samantha — install the voice via System Settings → Accessibility → Spoken Content.
SAY_VOICE_BY_LANG = {
    "en": "Samantha", "zh": "Tingting", "ja": "Kyoko", "ko": "Yuna",
    "es": "Monica", "fr": "Thomas", "de": "Anna", "it": "Alice",
    "pt": "Luciana", "ru": "Milena", "nl": "Xander", "hi": "Lekha",
}

def _resolve_say_voice(name, language):
    """If the storyboard still carries the default English voice ('Samantha') but the
    narration is in another language, swap in a matching voice. A voice the user picked
    explicitly (anything other than the default) is always respected."""
    lang = (language or "auto").lower().replace("_", "-").split("-")[0]
    if name == "Samantha" and lang not in ("", "en", "auto"):
        v = SAY_VOICE_BY_LANG.get(lang)
        if v and v != name:
            return v, f"[tts] language={lang}: using say voice '{v}' (set meta.voice to override)"
    return name, None

# Curated edge-tts neural voices: language -> accent -> {female, male} -> voice id.
# "_default" names the accent used when none is given. Escape hatch for anything not
# here: `python -m edge_tts --list-voices` and set meta.voice = "edge:<id>" directly.
EDGE_VOICE_CATALOG = {
    "en": {"_default": "US",
           "US": {"female": "en-US-AriaNeural", "male": "en-US-GuyNeural"},
           "UK": {"female": "en-GB-SoniaNeural", "male": "en-GB-RyanNeural"},
           "AU": {"female": "en-AU-NatashaNeural", "male": "en-AU-WilliamNeural"},
           "IN": {"female": "en-IN-NeerjaNeural", "male": "en-IN-PrabhatNeural"}},
    "zh": {"_default": "Mainland",
           "Mainland": {"female": "zh-CN-XiaoxiaoNeural", "male": "zh-CN-YunxiNeural"},
           "HK": {"female": "zh-HK-HiuMaanNeural", "male": "zh-HK-WanLungNeural"},
           "TW": {"female": "zh-TW-HsiaoChenNeural", "male": "zh-TW-YunJheNeural"}},
    "ja": {"_default": "JP", "JP": {"female": "ja-JP-NanamiNeural", "male": "ja-JP-KeitaNeural"}},
    "ko": {"_default": "KR", "KR": {"female": "ko-KR-SunHiNeural", "male": "ko-KR-InJoonNeural"}},
    "es": {"_default": "ES", "ES": {"female": "es-ES-ElviraNeural", "male": "es-ES-AlvaroNeural"}},
    "fr": {"_default": "FR", "FR": {"female": "fr-FR-DeniseNeural", "male": "fr-FR-HenriNeural"}},
    "de": {"_default": "DE", "DE": {"female": "de-DE-KatjaNeural", "male": "de-DE-ConradNeural"}},
    "pt": {"_default": "BR", "BR": {"female": "pt-BR-FranciscaNeural", "male": "pt-BR-AntonioNeural"}},
    "it": {"_default": "IT", "IT": {"female": "it-IT-ElsaNeural", "male": "it-IT-DiegoNeural"}},
    "ru": {"_default": "RU", "RU": {"female": "ru-RU-SvetlanaNeural", "male": "ru-RU-DmitryNeural"}},
    "nl": {"_default": "NL", "NL": {"female": "nl-NL-ColetteNeural", "male": "nl-NL-MaartenNeural"}},
    "hi": {"_default": "IN", "IN": {"female": "hi-IN-SwaraNeural", "male": "hi-IN-MadhurNeural"}},
}

def resolve_edge_voice(language, accent=None, gender="female"):
    """Map (language, accent, gender) to a concrete edge-tts voice id, or None if the
    language isn't in the curated catalog. Accent falls back to the language's default;
    gender falls back to female. Language/accent matching is case-insensitive."""
    lang = (language or "").lower().replace("_", "-").split("-")[0]
    table = EDGE_VOICE_CATALOG.get(lang)
    if not table:
        return None
    by_key = {k.lower(): k for k in table if k != "_default"}
    key = by_key.get((accent or "").lower(), table["_default"])
    g = gender if gender in ("female", "male") else "female"
    return table[key][g]

def _have_edge():
    """True if the edge-tts package is importable (no network check)."""
    import importlib.util
    return importlib.util.find_spec("edge_tts") is not None

def _resolve_voice(meta):
    """Turn meta.voice into a concrete 'provider:name'. The 'auto' sentinel prefers
    edge-tts (language + default accent + female) when available, else the language-
    matched macOS say voice. Any explicit 'edge:/say:/openai:' spec passes through."""
    spec = meta.get("voice", "auto")
    lang = meta.get("language", "auto")
    if spec and spec != "auto":
        return spec
    if _have_edge():
        vid = resolve_edge_voice(lang, gender="female")
        if vid:
            return f"edge:{vid}"
    name, _ = _resolve_say_voice("Samantha", lang)
    return f"say:{name}"

def synthesize(out_dir, only=None):
    path = os.path.join(out_dir, "storyboard.json")
    data = sb.load(path)
    audio_dir = os.path.join(out_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    prov, name = _provider(data["meta"].get("voice", "say:Samantha"))
    if prov == "say":
        name, note = _resolve_say_voice(name, data["meta"].get("language", "auto"))
        if note:
            print(note)

    for s in data["slides"]:
        if only and s["index"] != only:
            continue
        text = (s.get("narration") or "").strip() or " "
        ext = "aiff" if prov == "say" else "mp3"
        rel = os.path.join("audio", f"{s['index']:02d}.{ext}")
        dest = os.path.join(out_dir, rel)
        try:
            if prov == "openai":
                _openai(text, dest, name)
            else:
                _say(text, dest, name)
        except Exception as e:
            print(f"[tts] {prov} failed ({e}); falling back to say:Samantha")
            rel = os.path.join("audio", f"{s['index']:02d}.aiff")
            dest = os.path.join(out_dir, rel)
            _say(text, dest, "Samantha")
        s["audio"] = rel
        s["duration"] = round(_common.audio_duration(dest), 3)

    sb.save(data, path)
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--only", type=int, default=None)
    a = ap.parse_args()
    data = synthesize(a.out_dir, a.only)
    total = sum(s["duration"] or 0 for s in data["slides"])
    print(f"Synthesized {len(data['slides'])} clips, ~{total:.1f}s total.")

if __name__ == "__main__":
    main()
