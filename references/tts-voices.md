# TTS Voices

## Voice spec format

Set `meta.voice` in `storyboard.json` before running `tts.py`:

```json
"meta": {
  "voice": "say:Samantha"
}
```

Format: `"provider:name"`. Provider is `say` (local macOS) or `openai` (cloud).

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

If a voice isn't installed, `say` errors and `tts.py` falls back to `Samantha` (which will
mispronounce non-English text). Install voices via **System Settings → Accessibility →
Spoken Content → System Voice → Manage Voices**, or run `say -v '?'` to see what you have.

**Cloud TTS is language-agnostic:** OpenAI/ElevenLabs voices speak whatever language the
input text is in, so for `openai:*` you don't need a per-language voice — just write the
narration in the target language.

**Rate:** `say` runs at 175 wpm by default (tts.py hard-codes `-r 175`).
This maps well to the 140–160 wpm speaking target — the synthesizer speaks
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
back to macOS `say`.

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
limit), `tts.py` automatically falls back to `say:Samantha` and logs:

```
[tts] openai failed (<reason>); falling back to say:Samantha
```

The fallback slide gets an `.aiff` file instead of `.mp3`. Rendering continues
normally — `ffprobe` measures the actual duration from whichever file was
produced.

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
