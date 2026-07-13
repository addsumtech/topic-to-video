"""Narration text -> per-slide audio. Default macOS 'say'; cloud optional.

Voice spec in storyboard meta['voice']:
  "say:Samantha"        -> local macOS say, voice Samantha
  "openai:alloy"        -> OpenAI TTS (needs OPENAI_API_KEY); falls back to say
  "edge:<id>"           -> edge-tts neural (free, network); also emits per-word timings
  "minimax:<voice_id>"  -> MiniMax T2A (very natural, esp. zh; needs MINIMAX_API_KEY); falls back
                           to say. "minimax" alone picks a voice by language+gender from the catalog.
"""
import argparse, os
import _common
import storyboard as sb

def _read_key_file(path):
    """Read a single-line API key from `path` (e.g. ~/.minimax_key), or None. Never persisted by us."""
    try:
        return (open(os.path.expanduser(path)).read().strip() or None)
    except OSError:
        return None

def _say(text, out_path, voice, rate=175):
    # say writes AIFF directly; ffprobe reads its real duration later.
    _common.run(["say", "-v", voice, "-r", str(rate), "-o", out_path, text])


def _silence(out_path, seconds=1.2):
    """A REAL short silent clip for a deliberately-silent beat (a section divider, or tts run before the
    script is written). Holds the slide on screen for `seconds` instead of `say ' '` (which yields a
    header-only ~0s AIFF that crashes duration probing and flashes for one frame)."""
    sr = 22050 if out_path.endswith(".aiff") else 24000
    _common.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=mono",
                 "-t", f"{seconds:.2f}", out_path])

def _openai(text, out_path, voice):
    # Optional upgrade. Lazy import so the skill never hard-depends on it.
    import requests
    # accept the key from the env OR ~/.openai_key (parity with minimax) — the docs tell users to put it
    # in the key file, so reading only the env silently fell back to `say` for a paying OpenAI user.
    key = os.environ.get("OPENAI_API_KEY") or _read_key_file("~/.openai_key")
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

# --- MiniMax T2A (cloud, paid, very natural — especially Chinese) ----------------------------
# Endpoint default is the INTERNATIONAL host (GroupId is carried by the key there). On the mainland
# host (api.minimaxi.chat / api.minimax.chat) set meta.minimax_group_id (or MINIMAX_GROUP_ID).
# Two regions with SEPARATE key namespaces — a key only works on the host of the account that
# issued it. We try both automatically (a wrong-region key returns 2049 "invalid api key", which we
# treat as "try the other host"), so the user doesn't have to know or set the region.
MINIMAX_INTL_BASE = "https://api.minimax.io/v1/t2a_v2"      # international accounts
MINIMAX_CN_BASE   = "https://api.minimax.chat/v1/t2a_v2"    # mainland accounts
_MINIMAX_BASE_BY_KEY = {}                                   # cache the working host per key (per run)
MINIMAX_DEFAULT_MODEL = "speech-02-hd"          # natural HD; bump via meta.tts_model (speech-2.6-hd, ...)
# language_boost improves pronunciation (MiniMax wants capitalised language names).
MINIMAX_LANG_BOOST = {
    "zh": "Chinese", "en": "English", "ja": "Japanese", "ko": "Korean", "es": "Spanish",
    "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
    "nl": "Dutch", "hi": "Hindi",
}
# A few curated, professional system voices from MiniMax's current voice library (300+ exist —
# set meta.voice = "minimax:<any voice_id>", list at platform.minimax.io/docs/faq/system-voice-id).
MINIMAX_VOICE_CATALOG = {
    "en": {"female": "English_Graceful_Lady", "male": "English_Trustworth_Man"},
    "zh": {"female": "Chinese (Mandarin)_IntellectualGirl",
           "male": "Chinese (Mandarin)_Reliable_Executive"},
}
MINIMAX_DEFAULT_VOICE = "English_expressive_narrator"   # fallback for languages not in the catalog

# Curated HUMAN-LIKE candidates per language×gender for the voice-sample picker (voice_sample.py):
# natural, conversational, trustworthy — NOT theatrical/character voices (comedian/anime/robot). The
# user listens to these samples and picks; the first of each list is the catalog default.
MINIMAX_VOICE_CANDIDATES = {
    "en": {
        "female": ["English_Graceful_Lady", "English_CalmWoman", "English_SereneWoman",
                   "English_ConfidentWoman", "English_Upbeat_Woman"],
        "male":   ["English_Trustworth_Man", "English_expressive_narrator", "English_Steadymentor",
                   "English_Gentle-voiced_man", "English_Deep-VoicedGentleman"],
    },
    "zh": {
        "female": ["Chinese (Mandarin)_IntellectualGirl", "Chinese (Mandarin)_Warm_Girl",
                   "Chinese (Mandarin)_Sweet_Lady", "Chinese (Mandarin)_Mature_Woman",
                   "Chinese (Mandarin)_Wise_Women"],
        "male":   ["Chinese (Mandarin)_Reliable_Executive", "Chinese (Mandarin)_Gentleman",
                   "Chinese (Mandarin)_Sincere_Adult", "Chinese (Mandarin)_Radio_Host",
                   "Chinese (Mandarin)_Southern_Young_Man"],
    },
}

def minimax_voice_candidates(language, gender="female"):
    """Curated human-like MiniMax voice_ids to sample for (language, gender); [] if none curated
    (caller can still use any voice_id via meta.voice='minimax:<id>')."""
    lang = (language or "").lower().replace("_", "-").split("-")[0]
    g = gender if gender in ("female", "male") else "female"
    return list(MINIMAX_VOICE_CANDIDATES.get(lang, {}).get(g, []))

def resolve_minimax_voice(language, gender="female"):
    """Map (language, gender) to a curated MiniMax voice_id; falls back to a neutral narrator for
    languages not in the catalog. Any voice_id can be used directly via meta.voice='minimax:<id>'."""
    lang = (language or "").lower().replace("_", "-").split("-")[0]
    g = gender if gender in ("female", "male") else "female"
    tbl = MINIMAX_VOICE_CATALOG.get(lang)
    return tbl[g] if tbl else MINIMAX_DEFAULT_VOICE

def _minimax_bases(meta, key):
    """Ordered hosts to try. An explicit meta.minimax_base / MINIMAX_API_BASE forces exactly one.
    Otherwise try both regions (int'l then mainland), but front-load the host cached as working for
    this key so only the FIRST slide of a run pays the region probe."""
    explicit = (meta or {}).get("minimax_base") or os.environ.get("MINIMAX_API_BASE")
    if explicit:
        return [explicit]
    order = [MINIMAX_INTL_BASE, MINIMAX_CN_BASE]
    cached = _MINIMAX_BASE_BY_KEY.get(key)
    if cached in order:
        order = [cached] + [b for b in order if b != cached]
    return order

def _tts_speed(meta):
    """Narration pace multiplier from `meta.tts_speed` (1.0 = natural). Lets a dense deck land in a
    tighter runtime without cutting content. Clamped to MiniMax's valid [0.5, 2.0] band."""
    try:
        return max(0.5, min(2.0, float((meta or {}).get("tts_speed") or 1.0)))
    except (TypeError, ValueError):
        return 1.0

def _edge_rate(meta):
    """edge-tts `rate` string from meta.tts_speed (1.0 = natural → '+0%'). A dense deck can speed the
    neural voice a touch (edge handles ~±30% naturally) to land a tighter runtime without cutting
    content — the same knob _tts_speed feeds MiniMax, mapped to edge's percentage form."""
    pct = round((_tts_speed(meta) - 1.0) * 100)
    return f"{pct:+d}%"

def _minimax(text, out_path, voice, meta):
    """Synthesize via MiniMax T2A v2. Bearer auth; response `data.audio` is HEX-encoded mp3.
    Key from MINIMAX_API_KEY env or ~/.minimax_key (never persisted). Region is auto-detected: a
    wrong-region key returns 2049 ("invalid api key"), so we transparently try the other host. No
    per-word timings, so HTML reveals use the paced fallback (use edge-tts for exact audio-sync)."""
    import requests
    meta = meta or {}
    key = os.environ.get("MINIMAX_API_KEY") or _read_key_file("~/.minimax_key")
    if not key:
        raise RuntimeError("no MINIMAX_API_KEY")
    group = meta.get("minimax_group_id") or os.environ.get("MINIMAX_GROUP_ID")
    lang = (meta.get("language") or "auto").lower().replace("_", "-").split("-")[0]
    body = {
        "model": meta.get("tts_model") or MINIMAX_DEFAULT_MODEL,
        "text": text,
        "stream": False,
        "language_boost": MINIMAX_LANG_BOOST.get(lang, "auto"),
        "output_format": "hex",
        "voice_setting": {"voice_id": voice, "speed": _tts_speed(meta), "vol": 1.0, "pitch": 0},
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    bases = _minimax_bases(meta, key)
    last = None
    for i, base in enumerate(bases):
        url = f"{base}?GroupId={group}" if group else base
        more = i < len(bases) - 1
        try:
            r = requests.post(url, headers=headers, json=body, timeout=120)
            r.raise_for_status()
            j = r.json()
        except Exception as e:                      # network/HTTP: try the other host if we have one
            last = e
            if more:
                continue
            raise
        br = j.get("base_resp") or {}
        code = br.get("status_code")
        if code == 2049 and more:                   # wrong-region key — try the other host
            last = RuntimeError(f"2049 invalid api key @ {base}")
            continue
        if code not in (0, None):
            hint = ""
            if code == 2049:
                hint = (" — wrong-region key: an international key uses api.minimax.io, a mainland "
                        "key uses api.minimax.chat (tried both). Check the key.")
            elif code == 1008:
                hint = " — the MiniMax account has no balance; add credits in the console."
            raise RuntimeError(f"minimax error {code}: {br.get('status_msg')}{hint}")
        audio_hex = (j.get("data") or {}).get("audio")
        if not audio_hex:
            raise RuntimeError(f"minimax: no audio in response (status {br.get('status_msg')})")
        if not ((meta or {}).get("minimax_base") or os.environ.get("MINIMAX_API_BASE")):
            _MINIMAX_BASE_BY_KEY[key] = base        # remember the working host for the rest of the run
        with open(out_path, "wb") as f:
            f.write(bytes.fromhex(audio_hex))
        return
    raise RuntimeError(f"minimax: all hosts failed ({last})")

def _words_from_boundaries(chunks):
    """Pure: list of edge WordBoundary chunks -> [{'w':word,'t':start_seconds}]. offset is in 100ns ticks."""
    out = []
    for c in chunks:
        if c.get("type") == "WordBoundary":
            out.append({"w": c.get("text", ""), "t": round(c.get("offset", 0) / 1e7, 3)})
    return out

def _edge(text, out_path, voice, rate="+0%"):
    # edge-tts neural voice via its Python API: streams audio + per-word boundaries in one pass.
    # asyncio.run at this leaf keeps the rest of the pipeline synchronous. `rate` (e.g. '+25%') speeds
    # or slows the voice — the word-boundary times scale with it, so cued reveals stay in sync.
    import asyncio, json, edge_tts
    async def _go():
        audio = bytearray(); chunks = []
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        async for ch in comm.stream():
            if ch["type"] == "audio":
                audio.extend(ch["data"])
            elif ch["type"] == "WordBoundary":
                chunks.append(ch)
        return bytes(audio), chunks
    audio, chunks = asyncio.run(_go())
    with open(out_path, "wb") as f:
        f.write(audio)
    try:
        words = _words_from_boundaries(chunks)
        if words:
            with open(os.path.splitext(out_path)[0] + ".words.json", "w") as f:
                json.dump(words, f)
    except Exception as e:
        print(f"[tts] word-timing capture failed for {out_path}: {e}")

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
        # expand a bare "minimax" / "minimax:auto" to a concrete catalog voice for the language
        if spec in ("minimax", "minimax:auto"):
            return f"minimax:{resolve_minimax_voice(lang, meta.get('voice_gender', 'female'))}"
        return spec
    if _have_edge():
        vid = resolve_edge_voice(lang, gender="female")
        if vid:
            return f"edge:{vid}"
    name, _ = _resolve_say_voice("Samantha", lang)
    return f"say:{name}"

def _detect_language(slides):
    """Best-guess narration language from the script when meta.language is 'auto' — otherwise a
    non-English deck gets voiced by the English default. Covers the CJK scripts (the headline
    cross-language flow); Latin scripts default to English (an explicit meta.language still wins)."""
    txt = " ".join((s.get("narration") or "") for s in (slides or []))[:4000]
    import re as _re
    if _re.search(r"[぀-ヿ]", txt):   # kana → Japanese
        return "ja"
    if _re.search(r"[가-힣]", txt):   # hangul → Korean
        return "ko"
    if _re.search(r"[一-鿿]", txt):   # Han → Chinese
        return "zh"
    return "en"

def synthesize(out_dir, only=None):
    path = os.path.join(out_dir, "storyboard.json")
    data = sb.load(path)
    audio_dir = os.path.join(out_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    if (data["meta"].get("language") or "auto") in ("", "auto"):   # fill it so voice selection is right
        data["meta"]["language"] = _detect_language(data["slides"])
    prov, name = _provider(_resolve_voice(data["meta"]))
    if prov == "say":
        name, note = _resolve_say_voice(name, data["meta"].get("language", "auto"))
        if note:
            print(note)

    for s in data["slides"]:
        if only is not None and s["index"] != only:
            continue
        text = (s.get("narration") or "").strip()
        ext = "aiff" if prov == "say" else "mp3"
        rel = os.path.join("audio", f"{s['index']:02d}.{ext}")
        dest = os.path.join(out_dir, rel)
        if not text:
            # a deliberately-silent beat (divider / pre-script ingest): a real short silent clip so the
            # slide HOLDS, and NO tts call (say ' ' crashes duration probing) — degrade this ONE slide only.
            _silence(dest)
            wj = os.path.join(audio_dir, f"{s['index']:02d}.words.json")
            if os.path.exists(wj):
                os.remove(wj)
            s["audio"] = rel
            s["duration"] = round(max(1.0, _common.audio_duration(dest)), 3)
            continue
        try:
            if prov == "openai":
                _openai(text, dest, name)
            elif prov == "edge":
                _edge(text, dest, name, _edge_rate(data["meta"]))
            elif prov == "minimax":
                _minimax(text, dest, name, data["meta"])
            else:
                _say(text, dest, name)
        except Exception as e:
            # Fall back to the LANGUAGE-MATCHED say voice — not a hardcoded English one,
            # or a non-English project (e.g. zh) would get garbled English audio.
            fb, _ = _resolve_say_voice("Samantha", data["meta"].get("language", "auto"))
            print(f"[tts] {prov} failed ({e}); falling back to say:{fb}")
            rel = os.path.join("audio", f"{s['index']:02d}.aiff")
            dest = os.path.join(out_dir, rel)
            _say(text, dest, fb)
            wj = os.path.join(out_dir, "audio", f"{s['index']:02d}.words.json")
            if os.path.exists(wj):
                os.remove(wj)   # drop stale per-word timings — say has none; a leftover would mis-cue render_html
        s["audio"] = rel
        s["duration"] = round(_common.audio_duration(dest), 3)
        # Only edge-tts emits per-word timings. For any other provider (say/openai/minimax) drop a
        # leftover words.json from a PRIOR edge run — otherwise render_html would cue reveals off
        # stale timings that don't match this audio. (The fallback branch above also handles it.)
        if rel.endswith(".aiff") or prov != "edge":
            wj = os.path.join(audio_dir, f"{s['index']:02d}.words.json")
            if os.path.exists(wj):
                os.remove(wj)

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
