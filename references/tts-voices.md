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
