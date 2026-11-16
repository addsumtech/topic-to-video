---
name: topic-to-video
slug: topic-to-video
displayName: Topic to Video
version: 2.0.0
description: >-
  Turn ANY topic — or a slide deck — into a narrated explainer or launch short video,
  automatically: researches the topic, writes and voices the script first, has the user
  pick one look from named styles, builds the whole film in that look sequence by
  sequence (with lighting, material and 3D where it fits), adds sound and captions, and
  checks the picture. Classic modes: voice a deck as-is, designed HTML pages, or the
  227-shot Remotion library. Any language; can voice a
  deck in a different language than its slides. Use whenever the user wants a short
  video about a subject or from slides — e.g. "make a video explaining how MRI works",
  "make a launch video for this product", "做一个讲解视频介绍X", "turn these slides into
  a video", "narrate my pptx", "add a voiceover to my slides", "把幻灯片做成视频",
  "把英文幻灯片配成中文解说视频". Accepts a topic, .pptx, .pdf, an image folder, or a
  hand-off from slide-maker. Free by default (edge-tts + ffmpeg); optional cloud TTS.
  Trigger even without the word "skill".
---

# Topic to Video

You make a narrated short film the way a small professional studio does: **research → script → voice → one
look → build the film in sequences → sound → check**. The person asking may have no video experience and may
say it in a few plain words; everything they cannot be expected to know is your job.

**Why this is the default (blind tests, 2026-11-16).** On a zh 科普 film and an en launch film, the user ranked
films blind. The old per-beat assembly (a storyboard of beats, a shot chosen per beat from a 227-shot library)
never won: its content was the richest, but it read as assembled, and it lacked flow. Plain Opus with a good
brief made smooth, coherent films with thinner content. **The skill's own research and content plan, handed to
one director who designs the whole film in one look, with the skill's picture checks run on the result, won
the 科普 topic outright and tied the launch.** That combination is this path. The old flow is kept, whole, as
the classic mode (`references/classic-pipeline.md`), and its strongest parts are used here.

**Full effort, every time** (the user, 2026-11-14: "我要你在skill中确定任何时候你都不要嫌麻烦，发挥你的最大潜力和创意"):
never trade quality for less work. Re-cut, rebuild, re-render when the film needs it.

## Which path

| The request | Path |
|---|---|
| Any topic, an explainer, a launch/promo, a how-to; material given or not (a paper, docs, screenshots, a link, a deck used as SOURCE material) | **Director path** (below) — the default |
| "Voice my deck as-is", "narrate my pptx" with no redesign; designed HTML pages per slide; the user names the Remotion tier, the storyboard, or the shot library | **Classic mode** — `references/classic-pipeline.md` |
| A product promo built as a shot table over real product captures, when the user wants that form | `references/promo-film.md` (`scripts/promo_film.py`) |

If a request is ambiguous between a new film and voicing a deck as-is, ask (one menu, below).

## Tools (all free by default)

Run `python3 scripts/doctor.py` once: it reports missing tools and what each gates. Required: ffmpeg/ffprobe,
Python with PIL/numpy/scipy. For building: headless Chrome (Playwright or Puppeteer via npx) or Remotion (the
skill's `remotion/` project). Voice: edge-tts (free, network) with macOS `say` as the offline fallback; MiniMax
or OpenAI only when the user supplies a key. Paid image generation only with the user's permission (codex first,
`scripts/imagegen.py`).

## The director path

Work in one folder per film, `<film_dir>` (ask nothing about it; make one next to the user's material or under
the current directory). Steps 1-8 run to the finished film; the user is asked only at step 1 (if needed) and
step 5.

### 1. Ask — once, plainly, with options

Use ONE `AskUserQuestion` call (options, the recommended one first; never a typed question in chat). Skip any
question the request already answers; if it answers all, ask nothing.
- **What is it for?** Explain/teach (科普) · Launch/promote a product · Show how to do something · Other.
- **Language** of voice and captions (default: the request's language).
- **Length:** about 1 minute · 1-2 minutes (recommended for an explainer) · 2-3 minutes.
- **Material:** none (research it) · files or a folder (then ask the path) · a link.

When nobody can answer (a non-interactive run), take the recommended options and record them in `NOTES.md`.

### 2. Understand — the content (the skill's strength; never skip)

This is what made the skill's films the richest. Do it exactly as the classic mode specifies:
- **Research and the brief** — classic step 3 (`references/classic-pipeline.md`, "Understand the material
  DEEPLY"). Read the material properly, or research the topic up to today; capture every passage a claim rests
  on with `scripts/sources.py add` (tier the source; date time-sensitive facts with `--as-of`); write
  `<film_dir>/brief.json` (thesis, mechanism, evidence with `source_ref`, why_it_matters, the_one_thing,
  misconceptions, unknowns, coverage, source_health, self_check). Gate: `python3 scripts/brief_qa.py <film_dir>`.
- **The content plan** — classic step 3.5: dispatch `agents/content-planner.md` with the brief, the material, and
  the purpose from step 1. Save `<film_dir>/content_plan.json` (audience, viewer_question, arc, beats with
  introduces/builds_on/stage, the climax). Gate: `python3 scripts/pedagogy_qa.py <film_dir>`.

The plan's beats are IDEAS, not shots. Several may live in one continuous sequence; one may need two shots.

### 3. Script — for the ear

Write `<film_dir>/script.json`: spoken lines grouped into **3-6 sequences** (hook · setup · build… · payoff ·
close), each line one idea, in the order of the content plan, covering all of it. Rules: a hook in the first
3-5 seconds that SHOWS a tension; short sentences; numbers said the way people say them; every fact traceable to
the brief; no filler, no AI voice tics (`references/narration-writing.md`, `references/anti-ai-voice.md`).
Fit the length: `python3 scripts/pace.py --budget <seconds> --lang <lang>` says how much narration a span
holds. Over length → cut lines, never speed the voice past natural.

### 4. Voice first — then lock the cut

Record the narration line by line (edge-tts; a natural neural voice for the language: zh `zh-CN-YunxiNeural` /
`zh-CN-XiaoxiaoNeural`, en `en-US-AndrewMultilingualNeural` / `en-US-AvaMultilingualNeural`; `references/tts-voices.md`)
with word timings. Trim leading/trailing silence, cap pauses inside a line (~0.25 s), and put a longer breath
(0.4-0.6 s) at each sequence seam. Listen-level check: no clipping, consistent loudness across lines.
Write `<film_dir>/timeline.json` from the timings: every line's start/end, every word's time, the sequence
seams. **This timeline is the film's clock: every picture is built to it.** Captions are chunked from it.

### 5. One look — the user picks it (the one checkpoint)

1. From `references/visual-styles.md` (18 named styles: swiss, editorial, bauhaus, memphis, risograph, blueprint,
   terminal, glassmorphism, …), shortlist 2-3 that fit THIS subject and purpose — its domain map and guardrail
   vetoes apply (no playful style on a somber subject; no busy ground under data). A brand's own colours and
   logo (`input` assets) override the palette, not the style's structure.
2. For each, render ONE **style frame**: a 1920x1080 still of the film's real subject at its key moment (the real
   QR code, the real product screen), in that look, with a caption. `python3 scripts/theme.py <film_dir> --style
   <key>` gives the style's contrast-safe palette and type as CSS variables.
3. Tile the frames on one image, show it, and ask (`AskUserQuestion`, recommended first; each option names the
   style and one line on why). Non-interactive: take the recommended one.

The chosen look is **held for the whole film**: palette, type scale, grid, ground, light. Variety comes from
composition and scale, never from changing the look. Also decide the film's **recurring subject** here: the one
thing the film keeps returning to and transforming (the code being torn, scanned and repaired; the companion
and its three file cards). This, more than anything else, made the winning films feel like one film.

### 6. Build — sequence by sequence

**The unit is the sequence.** Each sequence is one world (subject, ground, camera language) and flows inside
itself; the world changes only at a seam. Within it, every shot has one focal point, appears with its words
(the cut lands ~0.1-0.2 s before the word), and moves with intent. The craft rules are in
`references/director-craft.md`: read it before building.

**Engine.** Default: one HTML page for the whole film (`film.html`) in which **every frame is a pure function of
time** (`window.seek(t)` sets the whole frame for time t: no CSS transitions, no timers, no randomness), captured
frame by frame with headless Chrome at 1920x1080, 30 fps, then encoded with ffmpeg. Both winning films were
made this way. A film that wants the kit below may be built in the skill's Remotion project instead.

**The kit — use it where the look calls for it** (the old pipeline's best parts; `references/building-blocks.md`):
- **Light, material and depth:** `runtime/material`, the lit stage, the craft kit's `surface`, `slide.optic`;
  real 3D plates from Blender (`references/blender-plates.md`, `scripts/blender_plate.py`) for what 3D physicality
  IS the content of (a real object, material, optics, physics, a device). A lit film keeps one light direction
  and one material language throughout.
- **Shots and objects as parts:** the library's 227 shots (`remotion/LIBRARY.md`) and its objects (devices, the
  Earth, satellites, clocks…) are parts. Write a film's own shot or object in its workshop
  (`python3 scripts/workshop.py <film_dir> new-shot|new-object <Name> --means "…"`; it may import library shots as
  `@shots/<Name>` and the runtime as `@runtime/<module>`), check it (`workshop.py <film_dir> check`), preview it
  (`workshop.py <film_dir> still <Name>`), then render it: `workshop.py <film_dir> clip <Name> [--props p.json]`
  writes `<film_dir>/clips/<Name>.mp4` at full size. Place a clip in the film as frames the page draws by frame
  number (extract with ffmpeg to PNGs), so the page stays a pure function of time.
- **Real imagery:** the material's own screenshots and photos first; `scripts/imagefetch.py` for real,
  license-clean images of a named subject (Wikimedia Commons); generated images only for atmosphere, never for
  facts, and only with permission when paid.
- **Captions:** the classic tier's line-break rules apply (`scripts/caption_words.py` shows where a CJK caption
  may break). Captions sit in their own band, which no picture enters; 1-2 lines; easy contrast on the ground.

**Rules every frame obeys** (each one cost a real film a defect):
- Nothing cut off, overlapping or unreadable; nothing in the caption band but the caption.
- **Never draw a raster beyond its native pixels**; a real screenshot is cropped and pushed within its density.
- Time runs one way: a state reached stays reached; nothing replays after a cut.
- No slow constant creep on fine detail (hard edges shimmer); a camera move has a job and an end.
- No blank holds: every shot puts its subject on screen from its first frame (lead the cut by ~0.1 s).
- Text on screen is labels, keywords and numbers, never the narration as body text.
- Build each sequence, export its settled frames, look at them, fix, then move on.

**Render** `<film_dir>/final.mp4`: 1920x1080 (or 1080x1920 when asked for vertical), 30 fps, H.264 + AAC.
Write `<film_dir>/_plan.json` with the cut frames computed by **the same rule the renderer uses to switch shots**
(a plan that rounds differently puts a cut one frame off and the rewind check reports a replay):
`{"video": "final.mp4", "fps": 30, "frames": N, "cuts": [...], "segments": [{"start", "end", "kind": "shot"|"loop"}]}`.

### 7. Sound

- **Voice** on the timeline, levelled.
- **Music follows purpose:** an explainer can do without; a launch or promo is scored. `scripts/score.py` writes
  a generated score on a beat grid (`--bpm --seconds --climax`); a user's own track is used as given. Music sits
  well under the voice and ducks while it speaks.
- **SFX** on a few real events (a tear, a click, a card landing, the closing lockup), short and high-passed;
  `assets/sfx/` and `scripts/sfx.py` (its two-layer rules). Not every cut gets a sound.

### 8. Check, fix, deliver

1. `python3 scripts/film_qc.py <film_dir>` runs flash, rewind, picture-glide and empty-frame checks against
   `final.mp4` and `_plan.json`, and exits 1 on any red. Fix the film, re-render, re-run until CLEAN.
2. **Look at the real film**: a contact sheet of every shot's settled frame (~90 % through the shot) on one image.
   One layout repeated, a frame cut off, a caption over a picture, an empty hold, a sequence that drops the look:
   fix before delivering. Then watch transitions at the seams.
3. Faithfulness: every number, name and quote on screen or in the voice traces to the brief's sources.
4. Write `<film_dir>/NOTES.md`: what was made, the look and why, what the checks found and how it was fixed,
   anything not done. Deliver `final.mp4` and say where it is, its length, and the one thing it says.
   Offer: a vertical cut, a different look, a change to any line (re-voice that line, re-time, re-render).

## Guardrails

- **Never fabricate.** No invented statistics, quotes, dates, features or sources, on screen or in the voice.
  Unsure → say it as reported, keep it qualitative, or cut it. A demo value printed on screen is a claim.
- **Real brand assets only.** A product film uses the product's real logo, colours and screens; never redraw a
  logo, never invent UI. Render a logo and look at it before deriving colours from it.
- **Imagery is faithful:** a generated image never stands in for a real object, place, person or data.
- **A somber subject gets a sober look** (the style vetoes in `visual-styles.md`).
- **Ask before spending money** (cloud TTS, paid image generation).
- **Report honestly:** if a check is red and cannot be fixed, say so with its output.

## Classic mode and its references

`references/classic-pipeline.md` holds the full classic workflow, moved there verbatim on 2026-11-16: the deck
tiers (原样配音 / designed HTML / cinematic Remotion), the storyboard, the interview, the critics, every gate and
its order, the shot library, promotion, and troubleshooting. Follow it whole when the classic mode is chosen.
Other references: `pipeline-scripts.md` (every script), `troubleshooting.md`, `engineering-case-law.md` (why the
rules are what they are), `motion-grammar.md`, `launch-film-study.md`, `craft-standard.md`.
