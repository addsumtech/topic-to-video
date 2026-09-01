"""Narration text -> per-slide audio. Default macOS 'say'; cloud optional.

Voice spec in storyboard meta['voice']:
  "say:Samantha"        -> local macOS say, voice Samantha
  "openai:alloy"        -> OpenAI TTS (needs OPENAI_API_KEY); falls back to say
  "edge:<id>"           -> edge-tts neural (free, network); also emits per-word timings
  "minimax:<voice_id>"  -> MiniMax T2A (very natural, esp. zh; needs MINIMAX_API_KEY); falls back
                           to say. "minimax" alone picks a voice by language+gender from the catalog.
"""
import argparse, os, re, subprocess
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
    if _re.search("[\u3400-\u9fff\uf900-\ufaff]", txt):   # Han incl. Ext-A + compat ideographs (matches render._HAN) → Chinese
        return "zh"
    return "en"

SCENE_PAUSE_DEFAULT = 0.55      # the silence a viewer should HEAR between two scenes


def _seam_seconds(meta):
    """How much of a scene's tail the RENDERER overlaps with the next scene, in seconds.

    The remotion tier cross-dissolves scene i+1 over the last SEAM_FRAMES of scene i — AUDIO INCLUDED —
    so on that tier the tail pad must cover the dissolve as well, or the pause the viewer hears is
    (pad - dissolve). The html/local tier concatenates clips, so nothing is eaten there.

    SEAM_FRAMES is PARSED from remotion/src/runtime/motion.ts rather than duplicated, so the two cannot
    drift; if it cannot be read, fall back to the value that file has always carried.
    """
    if str((meta or {}).get("renderer", "")).lower() not in ("remotion", "remotion-bespoke"):
        return 0.0
    fps = 30
    try:
        fps = int((meta or {}).get("fps") or 30) or 30
    except (TypeError, ValueError):
        fps = 30
    frames = 12
    try:
        src = open(os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "runtime", "motion.ts"),
                   encoding="utf-8").read()
        m = re.search(r"export const SEAM_FRAMES\s*=\s*(\d+)", src)
        if m:
            frames = int(m.group(1))
    except OSError:
        pass
    return frames / float(fps)


SENTENCE_PAUSE_BREATH = 0.45  # a scene break is the film's own full stop PLUS a breath
MAX_SCENE_PAUSE = 1.5         # ...but never a hold; reading time belongs in tts_speed, not in dead air


def _longest_internal_pause(path):
    """The longest silence INSIDE a clip — its own sentence boundary, as this voice actually renders it.

    Returns None when there is nothing to measure (one short sentence, or no ffmpeg).
    """
    if not _common.have_tool("ffmpeg"):
        return None
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                              "silencedetect=noise=-55dB:d=0.12", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        dur = _common.audio_duration(path) or 0.0
    except Exception:                                       # noqa: BLE001 — never break synthesis over this
        return None
    starts = [float(x) for x in re.findall(r"silence_start: ([-\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([-\d.]+)", out)]
    inner = []
    for st in starts:
        after = [e for e in ends if e > st]
        if not after:
            continue                                        # runs to the end: that is the tail, not a pause
        en = after[0]
        if st > 0.15 and en < dur - 0.15:                    # strictly inside the speech
            inner.append(en - st)
    return max(inner) if inner else None


def _film_sentence_pause(paths):
    """How long THIS voice, in THIS language, at THIS rate holds a FULL STOP — measured on the film.

    Per clip we take its own longest internal pause; across the film we take the 75th percentile of
    those. Why not the median: roughly half the beats are one sentence, so their longest internal pause
    is a comma (~0.2s) and the median lands between the two populations, describing neither. Why not the
    max: one dramatic pause would then set every seam in the film. Returns None when nothing is
    measurable (every beat a single unbroken clause, or no ffmpeg) — the caller falls back to the floor.
    """
    tops = sorted(x for x in (_longest_internal_pause(p) for p in paths) if x)
    if not tops:
        return None
    return tops[min(len(tops) - 1, int(round(0.75 * (len(tops) - 1))))]


# ── THE ROOM THE VOICE IS MISSING ───────────────────────────────────────────────────────────────────────
# TTS is anechoic. A person finishing a sentence in a real room is followed by ~150-250ms of reflections
# decaying away, and that decay is most of what "a sentence ending" sounds like. edge-tts has none: measured
# across a delivered film, the time from -20 dB to -55 dB at the end of a trimmed clip is ZERO milliseconds.
# The last syllable simply stops at full level.
#
# That is why no fade length worked. Short, and the ending is a wall (reported as 戛然而止). Long, and it
# lands on the last character instead, because the syllable runs to the cut with nothing after it (reported
# as 每句话的最后一个字有问题). The knob had no good setting because the material it needed did not exist.
#
# So the tail is SYNTHESISED as early reflections. Measured over 8 delivered clips, against the same clips
# with no room at all:
#   first tap -12 dB @30ms, five taps to 250ms  ->  decay 168ms, +233ms of tail, body -1.2 dB, peak -1.5 dB
#   a stronger room (-7.5 dB @25ms)             ->  decay 125ms: SHORTER, and boxy enough to hear
# The gentle one wins on every axis, which is the usual sign that the loud one was fighting itself.
# `apad` FIRST, because aecho does not extend the stream — without room to write into, the reflections are
# truncated at the input's end and the filter measurably does nothing (the first attempt added 0ms of tail).
ECHO_TAPS = "30|70|120|180|250"
ECHO_GAINS = "0.25|0.16|0.10|0.06|0.035"
ECHO = "apad=pad_dur=0.5,aecho=0.9:0.92:%s:%s" % (ECHO_TAPS, ECHO_GAINS)
# What comes OUT of the breath is the AUDIBLE part of the tail, not its whole length: the room adds 233ms
# of material but only the first ~168ms is above hearing, and the rest still occupies time like any silence.
# Subtracting the full 233 shortened every seam by 65ms and made the printed number wrong again — the exact
# defect fixed one commit earlier, reintroduced from the other side.
ECHO_TAIL = 0.178        # seconds of AUDIBLE decay at a sentence end, MEASURED (-20 dB -> -55 dB) across
                         # the 30 delivered clips: the source's own decay (kept by the -85dB trim) plus the
                         # room. It was 168 when the trim was still deleting the natural half.

def _lead_silence(path):
    """Seconds of silence BEFORE the first word of a clip. Never trimmed — trimming the head would move
    every word time in `NN.words.json` and desync the karaoke caption — so it has to be SUBTRACTED from
    the tail pad instead, or it is added to the pause the viewer hears."""
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                              "silencedetect=noise=-55dB:d=0.05", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
    except Exception:
        return 0.0
    m = re.search(r"silence_start:\s*(-?[\d.]+)[\s\S]*?silence_end:\s*([\d.]+)", out)
    if not m:
        return 0.0
    start, end = float(m.group(1)), float(m.group(2))
    return round(end, 3) if start <= 0.02 else 0.0


def _film_lead_silence(paths):
    """The film's own median leading silence — one number, so every seam is corrected by the same amount."""
    leads = [_lead_silence(p) for p in paths if os.path.exists(p)]
    leads = [x for x in leads if x > 0]
    if not leads:
        return 0.0
    leads.sort()
    return round(leads[len(leads) // 2], 3)


def _tail_pad(meta, ref=None, lead=0.0):
    """Seconds of silence to append to a clip after its dead air is trimmed.

    MEASURED, on a delivered 37-beat remotion film with the old flat 0.42s pad: every one of the 36 scene
    seams carried 0.15-0.24s of silence (mean 0.18) while the narration's own WITHIN-sentence comma pauses
    ran to 0.55s. The pause between two scenes was shorter than the pause between two clauses — backwards,
    and it reads as the next scene cutting in before the sentence has landed. The cause was that the pad
    and the 12-frame cross-dissolve were the same length, so the dissolve consumed the whole breath.

    `meta.scene_pause` is therefore the AUDIBLE pause, and each tier converts it into a pad. An explicit
    `meta.audio_breath` still means the RAW pad (unchanged behaviour for boards that set it deliberately).
    """
    raw = (meta or {}).get("audio_breath")
    if raw is not None:
        try:
            return max(0.0, min(2.5, float(raw)))
        except (TypeError, ValueError):
            return SCENE_PAUSE_DEFAULT
    try:
        pause = float((meta or {}).get("scene_pause", SCENE_PAUSE_DEFAULT))
    except (TypeError, ValueError):
        pause = SCENE_PAUSE_DEFAULT
    pause = max(0.0, min(MAX_SCENE_PAUSE, pause))
    # SELF-CALIBRATING. A fixed number cannot know how long THIS voice, in THIS language, at THIS rate
    # leaves at a full stop — and a scene break that is barely longer than a sentence break inside a beat
    # reads as one continuous read. Measured on a delivered film: the seam was 0.72s against a 0.57s
    # in-beat sentence pause, only 27% longer, for a change of picture AND argument. So meta.scene_pause
    # is the FLOOR and the target is what this voice actually does at a full stop, PLUS a breath.
    # An INCREMENT, not a multiple, and that distinction is load-bearing. The first version multiplied by
    # 1.7, tuned on a Chinese voice whose full stop runs 0.57s -> 0.97s, which sounded right. Then an
    # English voice measured 0.90s at a full stop and the same rule asked for 1.53s: a multiple compounds
    # whatever the base already is, so a voice that pauses generously got a scene break that reads as the
    # film stopping. A breath is a fixed thing a listener needs on top of the stop they just heard, and it
    # lands at 1.02s / 1.35s for those two voices -- the first unchanged, the second no longer a hold.
    # The reference is FILM-WIDE on purpose: derived per clip, a two-sentence beat would get a 1.0s seam
    # and a one-sentence beat 0.55s — the seam would vary for a reason no viewer can perceive.
    if ref:
        pause = max(pause, min(MAX_SCENE_PAUSE, ref + SENTENCE_PAUSE_BREATH))
    # SUBTRACT THE NEXT CLIP'S LEADING SILENCE. The pause a viewer hears runs from the last word of one
    # beat to the first word of the next, and every TTS clip opens with a little silence of its own — the
    # head is deliberately never trimmed, because moving it would shift every word time in words.json and
    # desync the karaoke caption. That silence was simply never counted: measured on a delivered 30-beat
    # film, the pipeline printed "scene pause 0.75s audible" while the film's seams ran 0.98-1.00s, because
    # each clip opened with 0.191s of its own. The printed number was not the number, on every film this
    # skill has made. A floor keeps two clips from butting up against each other if a voice ever opens
    # with a very long lead.
    # The room tail is real sound that now occupies the first ~233ms of what used to be dead air, so it
    # comes OUT of the breath. Without this the seam simply grows by the length of the tail and the film
    # gets 7s longer for no reason a viewer could name.
    pad = pause + _seam_seconds(meta) - max(0.0, lead) - ECHO_TAIL
    return round(min(2.5, max(0.15 + _seam_seconds(meta), pad)), 3)


def audible_pause(meta, ref=None, lead=0.0):
    """The silence a viewer actually HEARS between two beats — the one number this file is trying to set.

    It is not the pad, and every term that separates the two has been got wrong once: the renderer eats
    `_seam_seconds` of the tail under the cross-dissolve; the NEXT clip opens with its own untrimmed lead;
    and the room tail now fills the first `ECHO_TAIL` of what used to be dead air with decaying sound. Each
    of those was discovered by measuring a delivered film against the number this pipeline printed.

    So it lives here once. The print statement and the tests both call it — they had a copy each, and the
    copies were what went stale the moment a term was added.
    """
    return _tail_pad(meta, ref=ref, lead=lead) - _seam_seconds(meta) + lead + ECHO_TAIL


def _master(path, meta=None, ref=None, lead=0.0):
    """Loudness-normalise + trim TRAILING dead-air of a SPEECH clip, in place. Two problems at once:
    (1) raw TTS ships at wildly different loudness across providers/scenes with no master, so a
    carefully-placed climax has no consistent sonic level; (2) the trailing tail (esp. say/openai/
    minimax) inflates the ffprobe duration, so the pacing gate + clip length are computed against dead
    air. loudnorm (EBU R128, I=-14) fixes level; a REVERSED silenceremove trims only the TAIL —
    leading & internal timing are untouched, so edge-tts `audio/NN.words.json` stays aligned (word
    times are relative to the start, which never moves) and karaoke/cues keep syncing. A fixed 0.12s
    pad keeps a uniform short breath so scene-edge dips never clip a word. The render re-encodes every
    clip to aac/48000/mono anyway, so this never touches sample-rate uniformity or the -c copy concat.
    Best-effort + deterministic: any ffmpeg failure keeps the original clip untouched. meta.audio_master
    == False opts out."""
    if meta is not None and meta.get("audio_master") is False:
        return
    if not _common.have_tool("ffmpeg"):
        return
    tmp = path + ".master" + os.path.splitext(path)[1]
    breath = _tail_pad(meta, ref=ref, lead=lead)
    # THE TAIL IS A DECAY, NOT A CLIFF — and the trim threshold is what decides whether one survives.
    #
    # -45dB removed the whole natural decay and apad spliced absolute silence onto the cut: a clip went
    # from -11dB to -99dB inside one 20ms window. Lowering it to -58 was supposed to fix that, and did not:
    # measured through each stage on the same clip, loudnorm leaves a proper tail (... -64 -75 -78 -76 -81)
    # and the -58 trim then deletes 0.57s of it, ending the clip at -22dB. Across engines the decay a
    # source actually HAS was being thrown away:
    #     edge zh  55ms -> 5ms      edge en 130ms -> 10ms      edge ja  ~ -> 45ms      say zh 35ms -> 0ms
    # At -85dB the same clips keep it (60 / 70 / 100 / 0 ms) and finish at -75 to -78dB instead of -23.
    # The cost is 48ms of retained noise floor per clip — 1.5s across a 30-beat film — against a decay that
    # is REAL rather than synthesised, on every engine and language tested.
    #
    # The synthesised room below still earns its place: `say` has no decay to preserve at any threshold
    # (0ms even at -85), so the room is the floor for engines that simply stop dead. With both, measured
    # with the fade in place: edge zh 190ms / -73dB, edge en 215 / -71, edge ja 200 / -72, say zh 180 / -76
    # — every source better than either half alone.
    # Two changes, both needed: trim at a lower threshold so more of the real decay survives, and fade the
    # last moments into the silence so there is no discontinuity left at all. The fade is applied in the
    # REVERSED domain (a fade-IN at the reversed start == a fade-out on the tail), which needs no
    # knowledge of the clip's length.
    af = ("loudnorm=I=-14:TP=-1.5:LRA=11," + ECHO + ","
          "areverse,silenceremove=start_periods=1:start_duration=0.06:"
          "start_threshold=-85dB:detection=peak,"
          # d=0.06, EXPONENTIAL — and the DURATION is the whole story here, twice over.
          #
          # 0.10 shipped and the endings were heard as 戛然而止, stopping dead. Widening to 0.18 fixed that
          # and broke something worse: measured across the film, the final syllable's body reaches the
          # trimmed clip's end (28 of 30 clips end above -50 dB — the trim cuts the syllable, it does not
          # find a decay to preserve), so an 0.18s fade lands ON the last character. Median 52% of the
          # final syllable sat inside it, and on four clips 100% did. The viewer's next report was exactly
          # that: 每句话的最后一个字有问题.
          #
          # So the window has to end before the syllable's body does. Measured on 12 delivered clips, as
          # attenuation applied 60ms from the end (where the character still is) against the level the clip
          # actually finishes at:
          #   0.06 exp —   0.0 dB at 60ms, ends -99 dB, 12/12 clips inaudible   <- the only one that does both
          #   0.08 exp — -21.3 dB at 60ms: already eating the character
          #   0.18 exp — -78.1 dB at 60ms: the character is gone
          #   0.06 tri / 0.06 qsin — 0.0 dB at 60ms, but finish at -52/-48 dB, so the splice to silence is
          #                          still a step; only the exponential reaches true silence in this window
          # The residual is that all the attenuation happens inside the last 60ms, where the signal is
          # already the syllable's tail rather than its body. That is the trade this file can make; the
          # deeper fix is a trim that stops cutting into the syllable, which needs the source audio to have
          # a decay to keep — and 28 of 30 edge-tts clips simply do not.
          "afade=t=in:st=0:d=0.06:curve=exp,"
          f"areverse,apad=pad_dur={breath}")
    try:
        _common.run(["ffmpeg", "-y", "-i", path, "-af", af, "-map_metadata", "-1", tmp])
        # only adopt the mastered clip if it's a real, non-degenerate result (guards the pathological
        # case where a near-silent clip gets trimmed to ~nothing — keep the original instead)
        if os.path.getsize(tmp) > 0 and _common.audio_duration(tmp) >= 0.3:
            os.replace(tmp, path)
        elif os.path.exists(tmp):
            os.remove(tmp)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)


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

    fell_back = []        # indices that dropped to the say fallback (a cloud/edge failure)
    used_primary = []     # indices that actually used the requested non-say provider
    pending = []          # (slide, path) awaiting mastering — the tail pad is a film-wide measurement
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
        ok_primary = False
        try:
            if prov == "openai":
                _openai(text, dest, name)
            elif prov == "edge":
                _edge(text, dest, name, _edge_rate(data["meta"]))
            elif prov == "minimax":
                _minimax(text, dest, name, data["meta"])
            else:
                _say(text, dest, name)
            ok_primary = prov != "say"
        except Exception as e:
            # Fall back to the LANGUAGE-MATCHED say voice — not a hardcoded English one,
            # or a non-English project (e.g. zh) would get garbled English audio.
            fb, _ = _resolve_say_voice("Samantha", data["meta"].get("language", "auto"))
            print(f"[tts] {prov} failed ({e}); falling back to say:{fb}")
            rel = os.path.join("audio", f"{s['index']:02d}.aiff")
            dest = os.path.join(out_dir, rel)
            _say(text, dest, fb)
            fell_back.append(s["index"])
            wj = os.path.join(out_dir, "audio", f"{s['index']:02d}.words.json")
            if os.path.exists(wj):
                os.remove(wj)   # drop stale per-word timings — say has none; a leftover would mis-cue render_html
        if ok_primary:
            used_primary.append(s["index"])
        s["audio"] = rel
        pending.append((s, dest))   # mastered below, once the film's own sentence pause is known
        # Only edge-tts emits per-word timings. For any other provider (say/openai/minimax) drop a
        # leftover words.json from a PRIOR edge run — otherwise render_html would cue reveals off
        # stale timings that don't match this audio. (The fallback branch above also handles it.)
        if rel.endswith(".aiff") or prov != "edge":
            wj = os.path.join(audio_dir, f"{s['index']:02d}.words.json")
            if os.path.exists(wj):
                os.remove(wj)

    # MASTER LAST. Level + tail-trim must happen before we measure a duration (pacing must see speech,
    # not dead air), but the tail PAD is derived from the whole film's sentence pause — so the clips wait
    # here until every one of them exists to be measured. On a --only re-synth the already-delivered
    # clips still supply the reference (their pause is internal; the pad sits past it).
    ref = _film_sentence_pause([os.path.join(out_dir, s["audio"]) for s in data["slides"]
                                if s.get("audio") and os.path.exists(os.path.join(out_dir, s["audio"]))])
    lead = _film_lead_silence([os.path.join(out_dir, s["audio"]) for s in data["slides"]
                               if s.get("audio") and os.path.exists(os.path.join(out_dir, s["audio"]))])
    for s, dest in pending:
        _master(dest, data["meta"], ref=ref, lead=lead)
        s["duration"] = round(_common.audio_duration(dest), 3)
    if pending:
        print("[tts] scene pause %.2fs audible (film full-stop %s + %.2fs breath, floor %.2f; "
              "next clip's own lead %.2fs subtracted)"
              % (audible_pause(data["meta"], ref=ref, lead=lead),
                 ("%.2fs" % ref) if ref else "unmeasurable", SENTENCE_PAUSE_BREATH,
                 float(data["meta"].get("scene_pause", SCENE_PAUSE_DEFAULT)), lead))

    # MIXED-VOICE guard: a cloud/edge run that fell back to `say` on SOME (not all) scenes ships an
    # INCONSISTENT narration voice (and mixed sample rates the render must normalize). This happens on a
    # systemic mid-run failure (MiniMax 1008 insufficient-balance, an expired key, a network outage) that
    # succeeds early then fails for the rest. It used to ship silently — surface it LOUDLY + actionably.
    if only is None and prov != "say" and fell_back and used_primary:
        print(f"[tts] ⚠️  MIXED-VOICE RUN — {len(used_primary)} scene(s) used {prov}, "
              f"{len(fell_back)} fell back to say (indices {fell_back}). The narration voice is "
              f"INCONSISTENT across the deck. Fix {prov} (e.g. top up MiniMax balance / check the key / "
              f"network) and re-run `tts.py`, OR set meta.voice to 'edge:<id>' (free, consistent) or "
              f"'say:<voice>' so every scene uses ONE engine. Do NOT ship this as-is.")
        data["meta"]["_tts_mixed_voice"] = {"provider": prov, "fell_back": fell_back}
    elif data["meta"].pop("_tts_mixed_voice", None):
        pass   # a clean re-run clears a prior mixed-voice flag

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
