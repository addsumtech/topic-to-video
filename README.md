# slides-to-video

Turn a slide deck into a narrated **instruction/explainer video** — each slide shown
full-frame with a voiceover, gentle Ken Burns motion, timed callout highlights, and
burned-in captions. Fully local and free by default (macOS `say` + `ffmpeg`); optional
cloud TTS.

This is an agent **skill** (Agent Skills standard) — your coding agent runs the guided
workflow when you ask (see triggers in `SKILL.md`): interview → ingest → edit script →
sample → render. The `scripts/` below are plain Python and also run standalone.

## Dependencies (all local, no API keys)

| Need | Tool |
|---|---|
| Render `.pptx` | LibreOffice `soffice` (pptx → pdf) |
| Rasterize pages | PyMuPDF `fitz` (pdf → PNG) |
| Speaker notes | `python-pptx` |
| Narration TTS | macOS `say` (cloud OpenAI/ElevenLabs optional) |
| Motion / compose | `ffmpeg` |
| Callouts + captions | `PIL` (captions burned with the bundled `assets/fonts/DejaVuSans.ttf` — **no libass needed**) |

## Quickstart (3 commands)

```bash
PY=/opt/anaconda3/bin/python3
OUT=./myvideo

# 1) Slides -> frames + skeleton storyboard.json  (accepts .pptx, .pdf, or an image folder)
$PY scripts/ingest.py deck.pptx $OUT

# 2) (edit $OUT/storyboard.json: fill each slide's "narration"; tune motion/callouts/captions)

# 3) Narrate, preview one slide, then render the whole thing
$PY scripts/tts.py $OUT
$PY scripts/render.py $OUT --sample 1      # sample.mp4 for style sign-off
$PY scripts/render.py $OUT                  # -> out.mp4 + out.srt   (--vertical for 9:16, --reduced-motion for the accessibility variant)
```

## How it works

Everything flows through one editable artifact, `storyboard.json` (see `SKILL.md` and the
`references/` guides). You edit *text and timing*; the scripts render the media:

`ingest.py` → frames + skeleton · `tts.py` → audio + durations · `render.py` → `out.mp4` + `out.srt`

See `SKILL.md` for the full guided workflow and `references/` for narration, motion,
captions, TTS, ffmpeg, and troubleshooting guides.
