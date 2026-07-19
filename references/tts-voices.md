# TTS Voices

## Voice spec format

Set `meta.voice` in `storyboard.json` before running `tts.py`:

```json
"meta": {
  "voice": "say:Samantha"
}
```

Format: `"provider:name"`. Provider is `edge` (preferred, free neural), `say` (offline macOS fallback), `openai`, or `minimax` (cloud, paid).

---

## Local: macOS `say`

No network, no API key. Audio is written as `.aiff`; duration measured via
`ffprobe`.

**Recommended English voices:**

| Voice | Character | Preview command |
|---|---|---|
| `Samantha` | Default, clear American female | `say -v Samantha "This is a test"` |
| `Alex` | American male, natural cadence | `say -v Alex "This is a test"` |
| `Daniel` | British English male | `say -v Daniel "This is a test"` |
| `Karen` | Australian English female | `say -v Karen "This is a test"` |
| `Moira` | Irish English female | `say -v Moira "This is a test"` |

List all voices installed on your system:
```bash
say -v '?'
```

### Non-English voices (multi-language)

The narration language lives in `meta.language` (`en`, `zh`, `ja`, …). When it is non-English
and you leave the default `say:Samantha`, `tts.py` automatically swaps in a matching voice so
the audio isn't read by an English engine. You can always override with an explicit
`meta.voice`.

| `meta.language` | Auto `say` voice | Notes |
|---|---|---|
| `en` | `Samantha` | default |
| `zh` | `Tingting` | Mandarin; `Sinji` (Cantonese), `Meijia` (Taiwan) also exist |
| `ja` | `Kyoko` | Japanese |
| `ko` | `Yuna` | Korean |
| `es` | `Monica` | Spanish; `Paulina` (Mexico) |
| `fr` | `Thomas` | French; `Amelie` (Canada) |
| `de` | `Anna` | German |
| `it` | `Alice` | Italian |
| `pt` | `Luciana` | Portuguese (Brazil) |
| `ru` | `Milena` | Russian |
| `nl` | `Xander` | Dutch |
| `hi` | `Lekha` | Hindi |

If a voice isn't installed, `say` errors and `tts.py` falls back to the language-matched say voice
(e.g. say:Tingting for zh) and prints a notice. Install voices via **System Settings → Accessibility →
Spoken Content → System Voice → Manage Voices**, or run `say -v '?'` to see what you have.

**Cloud TTS is language-agnostic:** OpenAI/ElevenLabs voices speak whatever language the
input text is in, so for `openai:*` you don't need a per-language voice — just write the
narration in the target language.

**Rate:** `say` runs at 175 wpm by default (tts.py hard-codes `-r 175`).
This maps well to the 140–160 wpm speaking target. **CJK note:** `-r` semantics differ for CJK voices
(rate is per-syllable, not wpm) — preview with e.g. `say -v Tingting 你好世界` and judge against the
4–6 chars/sec narration target instead — the synthesizer speaks
slightly faster than natural, which feels natural for voice-over.
To slow down for clarity you can edit the `rate` default in `tts.py`
(`_say` function, `rate=175`).

### Previewing narration before a full render

```bash
say -v Samantha "Your narration text here"
```

Run this for any slide where you're unsure about pacing or pronunciation
before committing to a full TTS pass.

---

## edge-tts (preferred free voice — natural neural, cross-platform)

`edge-tts` uses Microsoft Edge's free online neural voices — far more natural than `say`,
and it runs on any OS (not just macOS). Install once:

```bash
pip install edge-tts
```

Set a voice by accent + gender; the id goes in `meta.voice` as `edge:<id>`:

```json
"meta": { "voice": "edge:en-GB-SoniaNeural" }
```

| Lang | Accent | Female | Male |
|---|---|---|---|
| en | US | en-US-AriaNeural | en-US-GuyNeural |
| en | UK | en-GB-SoniaNeural | en-GB-RyanNeural |
| en | AU | en-AU-NatashaNeural | en-AU-WilliamNeural |
| en | IN | en-IN-NeerjaNeural | en-IN-PrabhatNeural |
| zh | Mainland | zh-CN-XiaoxiaoNeural | zh-CN-YunxiNeural |
| zh | HK | zh-HK-HiuMaanNeural | zh-HK-WanLungNeural |
| zh | TW | zh-TW-HsiaoChenNeural | zh-TW-YunJheNeural |
| ja | — | ja-JP-NanamiNeural | ja-JP-KeitaNeural |
| ko | — | ko-KR-SunHiNeural | ko-KR-InJoonNeural |
| es | — | es-ES-ElviraNeural | es-ES-AlvaroNeural |
| fr | — | fr-FR-DeniseNeural | fr-FR-HenriNeural |
| de | — | de-DE-KatjaNeural | de-DE-ConradNeural |
| pt | — | pt-BR-FranciscaNeural | pt-BR-AntonioNeural |
| it | — | it-IT-ElsaNeural | it-IT-DiegoNeural |
| ru | — | ru-RU-SvetlanaNeural | ru-RU-DmitryNeural |
| nl | — | nl-NL-ColetteNeural | nl-NL-MaartenNeural |
| hi | — | hi-IN-SwaraNeural | hi-IN-MadhurNeural |

Anything not listed: `python -m edge_tts --list-voices` and use any id as `edge:<id>`.

**Notes:** needs network (it's a free, unauthenticated cloud endpoint — an unofficial Edge
service, stable for years but not contractual). When edge-tts is unavailable, tts.py falls
back to macOS `say`. edge-tts also writes `audio/NN.words.json` (per-word start times) alongside
the `.mp3`; when present, `render_html` uses these timings to reveal each cued HTML point exactly
when its anchor phrase is spoken (audio-synced reveals).

---

## Cloud: OpenAI TTS

```json
"meta": {
  "voice": "openai:alloy"
}
```

Requires:
```bash
export OPENAI_API_KEY="sk-..."
```

Model used: `gpt-4o-mini-tts`. Audio is returned as `.mp3`.

**Available OpenAI voices:** `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`.

`alloy` and `nova` work well for technical presentations. `onyx` is a deeper
male voice. Preview at: https://platform.openai.com/docs/guides/text-to-speech

### Fallback behavior

If the OpenAI call fails for any reason (missing key, network error, rate
limit), `tts.py` automatically falls back to the language-matched say voice (e.g. say:Tingting for zh)
and logs:

```
[tts] openai failed (<reason>); falling back to say:Tingting for zh
```

The fallback slide gets an `.aiff` file instead of `.mp3`. Rendering continues
normally — `ffprobe` measures the actual duration from whichever file was
produced.

---

## Cloud: MiniMax T2A (most natural — especially Chinese)

MiniMax's neural voices sound markedly more human than edge-tts, and its Mandarin is excellent.
Paid (per-character), needs an API key. Pick it when naturalness matters more than the free tier.

```json
"meta": {
  "voice": "minimax:Chinese (Mandarin)_IntellectualGirl",
  "language": "zh"
}
```

Or let the skill choose a curated voice for the language + gender:
```json
"meta": { "voice": "minimax", "language": "zh", "voice_gender": "female" }
```

Key (never persisted — request fresh each run):
```bash
export MINIMAX_API_KEY="..."        # or put it in ~/.minimax_key
```

**Region — auto-detected, nothing to set.** MiniMax has two account regions with separate key
namespaces (international `api.minimax.io`, mainland `api.minimax.chat`); a key only works on its own
region's host. `tts.py` tries both automatically — a wrong-region key returns `2049 "invalid api key"`,
which the skill treats as "try the other host" — then caches whichever works for the rest of the run.
So an international **or** mainland key just works. To pin one host explicitly, set
`"minimax_base": "https://api.minimax.chat/v1/t2a_v2"` (this disables the auto-retry). If a mainland
setup returns a group error, add `"minimax_group_id": "<your GroupId>"`.

**Model:** `meta.tts_model` (default `speech-02-hd`; bump to `speech-2.6-hd` / `speech-2.8-hd` for the
latest if your account has them). Audio comes back hex-encoded and is written as `.mp3`.

**Curated voices (the skill's catalog):**

| language | female | male |
|---|---|---|
| `zh` | `Chinese (Mandarin)_IntellectualGirl` | `Chinese (Mandarin)_Reliable_Executive` |
| `en` | `English_Graceful_Lady` | `English_Trustworth_Man` |

Any of MiniMax's 300+ system voices works — set `meta.voice` to `minimax:<voice_id>`. Other good
picks: `English_expressive_narrator`, `Chinese (Mandarin)_News_Anchor`. Full list:
https://platform.minimax.io/docs/faq/system-voice-id

The **auto catalog covers `en` and `zh`** (used by a bare `"minimax"`). For any other language, pass an
**explicit** `minimax:<voice_id>` — MiniMax has `Japanese_*`, `Korean_*`, `Spanish_*`, … voices; a bare
`"minimax"` outside en/zh falls back to a neutral English narrator, which won't pronounce that language
well. Tip: list your account's exact voices with a POST to `/v1/get_voice` (`{"voice_type":"system"}`).

**Tradeoff — no per-word timings.** Unlike edge-tts, MiniMax (like OpenAI/say) does not emit
`audio/NN.words.json`. HTML reveals then use **text-position-estimated cues**: each point reveals at
(its `data-cue` anchor's char position in the narration ÷ length) × scene duration — so reveals still
track the narration's pacing (a good approximation), not a blind stagger. It assumes a ~uniform
speaking rate, so it's close but not word-exact. Use **edge-tts** when you need word-exact
`data-cue` sync; use **MiniMax** for the most natural voice with text-estimated reveals.

### Fallback behavior

If the MiniMax call fails (missing key, network, bad `voice_id`/`tts_model`, quota), `tts.py` falls
back to the language-matched `say` voice and logs `[tts] minimax failed (<reason>); falling back to
say:<voice>`. That slide gets an `.aiff`; rendering continues.

---

## Changing voice mid-project

1. Edit `meta.voice` in `storyboard.json`.
2. Re-run `tts.py`:
   ```bash
   python scripts/tts.py out/
   ```
   This re-synthesizes all slides and updates `audio` + `duration` fields.
3. Re-run `render.py` to pick up the new audio.

To re-synthesize only one slide (e.g., index 3):
```bash
python scripts/tts.py out/ --only 3
```
