---
name: slides-to-video
description: >-
  Turn a slide deck into a narrated instruction/explainer VIDEO — each slide shown
  full-frame with voiceover, gentle Ken Burns motion, timed callout highlights, and
  optional burned-in captions. Works in ANY language, and can voice a deck in a
  DIFFERENT language than its slides (e.g. a Chinese voice-over for an English deck).
  Use whenever the user wants to make a video / voiceover / narrated walkthrough /
  explainer FROM slides or a deck — e.g. "turn these slides into a video", "narrate my
  pptx", "make an explainer video from this deck", "add a voiceover to my slides",
  "video walkthrough of this presentation", "把幻灯片做成视频", "make a Chinese
  voice-over from my English slides", "把英文幻灯片配成中文解说视频".
  Accepts .pptx, .pdf, an image folder, or a hand-off from slide-maker. Local & free by
  default (macOS say + ffmpeg); optional cloud TTS. Generates an editable storyboard,
  lets the user edit the script, renders one sample slide for sign-off, then the full
  video. Trigger even without the word "skill".
---

# Slides to Video

You turn slides into a narrated video. Source of truth is `storyboard.json` — you edit
text/timing; the scripts render the media.

## Tools (all local & free; verify with `scripts/_common.have_tool`)
`soffice` (pptx→pdf), PyMuPDF `fitz`, `python-pptx`, macOS `say`, `ffmpeg`, PIL.
Captions burn via PIL + a bundled font (no libass needed). Optional: OpenAI/ElevenLabs
TTS if the user gives an API key.

## Pipeline scripts
- `scripts/ingest.py <input> <out_dir>` — pptx/pdf/image-folder → `frames/` + skeleton `storyboard.json` (pulls speaker notes from pptx).
- `scripts/tts.py <out_dir> [--only N]` — narration → `audio/` + real durations.
- `scripts/render.py <out_dir> [--sample N] [--only N] [--vertical]` — storyboard → `out.mp4` + `out.srt`.

## Workflow (follow in order)

1. **Interview** (one compact AskUserQuestion): the deck/PDF/image-folder to narrate;
   **source material to ground the narration** — the paper PDF, the code repo, a report or
   notes (slides alone rarely say enough to narrate *well*); audience & goal; **video
   language**; voice (local `say` vs cloud); captions on/off; aspect (16:9 default / 9:16);
   target pace (a seconds-per-slide ceiling). If the user has no material, tell them you'll
   web-research the topic to ground the script instead.
   - **Language**: default the narration to the **slides' own language** (detect it from the
     ingested text), but always confirm it as an option — users often want a video in a
     *different* language than the deck (e.g. Chinese slides, English voice-over for an
     international audience). Whatever they pick, set `meta.language` to its code (`en`, `zh`,
     `ja`, `ko`, `es`, `fr`, `de`, …). This drives the **caption font** (CJK needs a system
     font — the bundled Latin one tofus) and the **default TTS voice**, so getting it right
     here prevents mojibake captions and mispronounced audio downstream.
2. **Ingest** — run `ingest.py`. Report slide count and whether speaker notes were found.
3. **Understand the material DEEPLY — never narrate from the slides alone.** A good
   voice-over explains *why*, connects ideas, and is precise — that requires real
   understanding the bullets don't carry. This step is what makes the script good.
   - **Material provided** → read it properly, not skimmed: a paper end-to-end (intro →
     method → *every* results figure/table → conclusion); a codebase via its README + the
     key modules; a doc in full. Then write a short **comprehension brief**: the
     one-sentence message, the key contributions, the method essence, and — per slide —
     what it is *really* showing and the point to land. Narrate from this brief.
   - **No material** → `WebSearch`/`WebFetch` the topic to ground and enrich: confirm the
     facts, numbers, names and framing the slides imply, and fold in current context. Treat
     it as a **fact-check**, not flavour — with no source, you are the only thing standing
     between a confident-sounding wrong claim and the viewer.
   - **Either way, stay faithful:** every claim and number in the narration must trace to the
     material or a verified source — never invent results, numbers, or citations the
     slide/paper doesn't support. A forward-looking aside is fine only if flagged as your
     own addition.
4. **Author narration** — read `references/narration-writing.md`. Write spoken-style
   narration into each slide's `narration`, grounded in the comprehension brief (seed from
   `notes`/material; never bullet-recite). The on-screen **captions are auto-derived from
   the narration**, so the words you write are also the subtitle.
5. **Critic — narration + subtitle (REQUIRED, not optional).** Dispatch the critic
   (`agents/critic.md`) on the storyboard **plus the comprehension brief / source material**,
   so it can check facts, not just style. It strictly verifies (a) the narration is
   **precise and faithful** — no wrong, vague, or invented facts/numbers — and (b) the
   resulting **subtitles are correct** — they match the spoken words, segment into clean
   readable lines, fit on screen, and contain no typos or garbled/again-truncated text.
   Apply its required EDITS and re-dispatch until it returns **PASS**. THEN:
   🔴 **CHECKPOINT · 🛑 STOP:** present the full, critic-passed script and get the user's
   edits/approval BEFORE any TTS. Do not synthesize audio until they sign off.
6. **Motion** — read `references/motion-grammar.md`. Default motion is a gentle centered
   zoom `from:[0.5,0.5,1.0] → to:[0.5,0.5,1.12]` (keep zoom delta ≤0.20). **Callouts are OFF
   by default** — do NOT add emphasis boxes. They are easy to mis-place and a translucent
   box over a dark slide reads as a muddy coloured blob; the slide already shows the content.
   Add a callout ONLY if the user explicitly asks to emphasise a named region — then exactly
   one, tightly placed on that region, and confirm its position from the rendered sample.
7. **TTS** — run `tts.py` (use `--only N` while iterating on one slide).
8. **Sample sign-off** — `render.py <out_dir> --sample N`. Show `sample.mp4`, and **re-run
   the critic's subtitle check on the rendered sample** — view the burned-in captions and
   confirm they are legible, correct, and aligned with the speech (this is the only way to
   catch a caption that renders wrong even when the script reads fine).
   🔴 **CHECKPOINT · 🛑 STOP:** get explicit approval of the style (voice/pace/motion/
   captions) BEFORE the full render. Iterate on the sample until they approve — never
   batch-render all slides unsigned-off.
9. **Full render** — `render.py <out_dir>` (add `--vertical` for 9:16). Deliver `out.mp4`,
   `out.srt`, and the editable `storyboard.json`.
10. **Iterate** — any change = edit `storyboard.json`, then re-run render (the per-slide
    clip cache re-renders only changed slides) and tts (`--only N`). Never hand-edit the video.

## Guardrails
- `duration` always comes from rendered audio (tts.py sets it) — never guess timings.
- Set `meta.voice` (`say:Samantha` or `openai:alloy`), `meta.captions`, and `meta.language`
  in the storyboard, not via flags.
- **Language is set once, in `meta.language`** — write the narration in that language, and
  let `meta.voice` match it. tts.py auto-picks a matching `say` voice when the language is
  non-English and you left the default (see `references/tts-voices.md` for the per-language
  table). render.py auto-swaps to a system CJK font for Chinese/Japanese/Korean captions;
  if a glyph still tofus, set `meta.font` to a `.ttc`/`.ttf` that covers the script. Confirm
  the captions look right on the rendered **sample** (step 8) — that's where mojibake shows.

## When a step fails (if → then → still-failing)

| Trigger | First fix | If it still fails |
|---|---|---|
| `ingest.py`: `soffice` missing / hangs | Kill stale `soffice`; ask user to export the deck to PDF and feed the `.pdf` | Feed a folder of exported slide PNGs instead |
| pptx has no speaker notes | Generate narration from visible slide content + any source docs | Ask the user for the deck's intent per section |
| `tts.py`: cloud voice errors / no `OPENAI_API_KEY` | It auto-falls back to `say:Samantha` and prints a notice — continue | Set `meta.voice` to an explicit local `say:` voice |
| `render.py`: concat `-c copy` errors (codec/timestamp) | Re-encode the concat (`-c:v libx264 -c:a aac`) — see `references/ffmpeg-recipes.md` | Render per-slide with `--only N` and report the failing slide |
| Captions/text look wrong or font missing | render.py falls back to PIL's default font (still draws) | Confirm `assets/fonts/DejaVuSans.ttf` exists |
| Captions show tofu boxes / □□□ (non-Latin language) | Set `meta.language` so render.py picks a system CJK font (zh→PingFang, ja→Hiragino, ko→AppleSDGothicNeo) | Set `meta.font` to an explicit `.ttc`/`.ttf` that covers the script |
| Narration mispronounced / wrong-language voice | Set `meta.language`; tts.py auto-picks a matching `say` voice (zh→Tingting, ja→Kyoko, …) when you left the English default | Set `meta.voice` explicitly to an installed voice for that language (`say -v '?'` lists them) |
| Narration overruns the seconds-per-slide ceiling | Tighten wording (`references/narration-writing.md`) | 🔴 STOP and propose splitting the dense slide |
| A/V out of sync | Never guess timing — `duration` comes from ffprobe; re-run `tts.py --only N` | Re-render that slide with `--only N` |
| Slide "shivers"/jitters during the zoom | zoompan runs supersampled (`meta.motion_ss`, default 2) then downscales; a `scale` filter must precede zoompan or the frame shrinks. Keep ss≥2 | Raise `motion_ss` to 3 (smoother, slower) |
| Caption is one static line per slide | Captions auto-derive from `narration` — split into sentence chunks timed across the slide; a single full-span entry in `captions` is overridden by the narration track | For custom timing, supply a multi-segment `captions` array |

For anything else, read `references/troubleshooting.md` before guessing.

## Red lights — never do this

- ❌ Render audio/video before the user signs off script/sample (honor the 🔴 checkpoints).
- ❌ Narrate from the slides alone, or invent facts/numbers — ground in the material (or a
  web fact-check) and stay strictly faithful (step 3).
- ❌ Skip the critic — the narration + subtitle critic (step 5) is REQUIRED; ship only on PASS.
- ❌ Read slide bullets aloud verbatim — write *spoken* narration (`references/narration-writing.md`).
- ❌ Guess a slide's `duration` — it must come from ffprobe via `tts.py`.
- ❌ Hand-edit `out.mp4`; change `storyboard.json` and re-render (`--only N`).
- ❌ Add callouts/emphasis boxes by default — they're OFF unless the user asks; never stack them.
