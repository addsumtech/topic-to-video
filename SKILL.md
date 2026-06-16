---
name: slides-to-video
description: >-
  Turn a slide deck into a narrated instruction/explainer VIDEO — each slide shown
  full-frame with voiceover, gentle Ken Burns motion, timed callout highlights, and
  optional burned-in captions. Use whenever the user wants to make a video / voiceover
  / narrated walkthrough / explainer FROM slides or a deck — e.g. "turn these slides
  into a video", "narrate my pptx", "make an explainer video from this deck", "add a
  voiceover to my slides", "video walkthrough of this presentation", "把幻灯片做成视频".
  Accepts .pptx, .pdf, an image folder, or a hand-off from slide-maker. Local & free by
  default (macOS say + ffmpeg); optional cloud TTS. Generates an editable storyboard,
  lets the user edit the script, renders one sample slide for sign-off, then the full
  video. Trigger even without the word "skill".
---

# Slides to Video

You turn the user's slides into a narrated instruction video. The single source of
truth is `storyboard.json`; you edit text/timing, and the scripts render the media.

## Tools (all local & free; verify with `scripts/_common.have_tool`)
`soffice` (pptx→pdf), PyMuPDF `fitz`, `python-pptx`, macOS `say`, `ffmpeg`, PIL.
Captions are burned with PIL + a bundled font, so NO libass build of ffmpeg is needed.
Optional upgrade: OpenAI/ElevenLabs TTS if the user provides an API key.

## Pipeline scripts
- `scripts/ingest.py <input> <out_dir>` — pptx/pdf/image-folder → `frames/` + skeleton `storyboard.json` (pulls speaker notes from pptx).
- `scripts/tts.py <out_dir> [--only N]` — narration → `audio/` + real durations.
- `scripts/render.py <out_dir> [--sample N] [--only N] [--vertical]` — storyboard → `out.mp4` + `out.srt`.

## Workflow (follow in order)

1. **Interview** (one compact AskUserQuestion): input file(s)/folder; audience & goal;
   voice (local `say` voice vs cloud); captions on/off; aspect (16:9 default / 9:16);
   target pace (a seconds-per-slide ceiling).
2. **Ingest** — run `ingest.py`. Report slide count and whether speaker notes were found.
3. **Author narration** — read `references/narration-writing.md`. Write spoken-style
   narration into each slide's `narration` field (seed from `notes` when present).
   🔴 **CHECKPOINT · 🛑 STOP:** present the FULL script as text and get the user's edits/
   approval BEFORE running any TTS. Do not synthesize audio until they sign off.
4. **Motion & callouts** — read `references/motion-grammar.md`. Set conservative
   `motion`/`callouts` per slide. Only highlight a region the narration actually refers to.
5. **TTS** — run `tts.py` (use `--only N` while iterating on one slide).
6. **Sample sign-off** — `render.py <out_dir> --sample 1`. Show `sample.mp4`.
   🔴 **CHECKPOINT · 🛑 STOP:** get explicit approval of the style (voice/pace/motion/
   captions) BEFORE the full render. Iterate on the sample until they approve — never
   batch-render all slides unsigned-off.
7. **Full render** — `render.py <out_dir>` (add `--vertical` for 9:16). Deliver `out.mp4`,
   `out.srt`, and the editable `storyboard.json`.
8. **Iterate** — any change = edit `storyboard.json`, then re-run tts (`--only N`) and/or
   render (`--only N`). Never hand-edit the video.

## Optional quality pass
Read `agents/critic.md` and dispatch it on the script + sample if the user wants an
automated narration/pacing review before the full render.

## Guardrails
- `duration` always comes from rendered audio (tts.py sets it) — never guess timings.
- If `soffice` is missing, ask the user to export the deck to PDF (see
  `references/troubleshooting.md`).
- Keep narration within the user's seconds-per-slide ceiling; warn and suggest splitting
  dense slides.
- Set `meta.voice` (e.g. `say:Samantha` or `openai:alloy`) and `meta.captions` in the
  storyboard rather than via flags.

## When a step fails (if → then → still-failing)

| Trigger | First fix | If it still fails |
|---|---|---|
| `ingest.py`: `soffice` missing / hangs | Kill stale `soffice`; ask user to export the deck to PDF and feed the `.pdf` | Feed a folder of exported slide PNGs instead |
| pptx has no speaker notes | Generate narration from visible slide content + any source docs | Ask the user for the deck's intent per section |
| `tts.py`: cloud voice errors / no `OPENAI_API_KEY` | It auto-falls back to `say:Samantha` and prints a notice — continue | Set `meta.voice` to an explicit local `say:` voice |
| `render.py`: concat `-c copy` errors (codec/timestamp) | Re-encode the concat (`-c:v libx264 -c:a aac`) — see `references/ffmpeg-recipes.md` | Render per-slide with `--only N` and report the failing slide |
| Captions/text look wrong or font missing | render.py falls back to PIL's default font (still draws) | Confirm `assets/fonts/DejaVuSans.ttf` exists |
| Narration overruns the seconds-per-slide ceiling | Tighten wording (`references/narration-writing.md`) | 🔴 STOP and propose splitting the dense slide |
| A/V out of sync | Never guess timing — `duration` comes from ffprobe; re-run `tts.py --only N` | Re-render that slide with `--only N` |

For anything not listed, read `references/troubleshooting.md` before guessing.
