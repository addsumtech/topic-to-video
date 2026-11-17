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

**Why this path is the default.** In blind tests (2026-11-16/17) the old per-beat assembly (a shot chosen per beat
from a 227-shot library) never won: rich content, but it read as assembled. The skill's research and content plan,
handed to one director who designs the whole film in one look, with the skill's picture checks on the result, won
or tied every round. The old flow is kept whole as the classic mode (`references/classic-pipeline.md`); its strongest
parts are tools here.

**Full effort, every time** (the user, 2026-11-14: "我要你在skill中确定任何时候你都不要嫌麻烦，发挥你的最大潜力和创意"):
never trade quality for less work. Re-cut, rebuild, re-render when the film needs it.

## Which path

| The request | Path |
|---|---|
| Any topic, an explainer, a launch/promo, a how-to; material given or not (a paper, docs, screenshots, a link, a deck used as SOURCE material) | **Director path** (below) — the default |
| "Voice my deck as-is", "narrate my pptx" with no redesign; designed HTML pages per slide; the user names the Remotion tier, the storyboard, or the shot library | **Classic mode** — `references/classic-pipeline.md` |
| A product promo built as a shot table over real product captures, when the user wants that form | `references/promo-film.md` (`scripts/promo_film.py`) |

If a request is ambiguous between a new film and voicing a deck as-is, ask (one menu, below).

## Tools

Run `python3 scripts/doctor.py` once: it reports missing tools and what each gates. Required: ffmpeg/ffprobe, Python
with PIL/numpy/scipy; for building, headless Chrome or the skill's Remotion project; Blender 5 for real 3D. Free by
default (edge voices, Codex for images); a paid voice or image API only with the user's key and permission.
**`references/director-toolbox.md` has the exact command for everything below** — the voice layer, ingest, capture,
looks and themes, Blender clips and devices, library shots as parts, accents, score and SFX, the checks — every one
verified in a director-path folder. Open it when you build.

## The director path

Work in one folder per film, `<film_dir>` (ask nothing about it; make one next to the user's material or under
the current directory). Steps 1-8 run to the finished film; the user is asked only at step 1 (if needed) and
step 5.

**Design is judgement, not a menu** (the user, 2026-11-17: "设计要灵活，对于组件，vibe等等这些都是"). Only a few things
in this file BIND every film: the facts are sourced, every drawn thing is correct, everything is readable and
nothing sits in the caption band, rasters stay within their pixels, real brands stay real, and `film_qc` is clean
(or a red is proved wrong). Everything else (the looks and their palettes, components and kit pieces, accents, the
launch grammar, sequence counts, the craft principles, every example here) is a VOCABULARY: use it, combine it,
bend it, or leave it, by what this subject, this audience and this moment need, and invent what the vocabulary
lacks. A choice that departs from a suggestion here gets one line of why in `NOTES.md`; that is all it needs.

### 1. Ask — once, plainly, with options

Use ONE `AskUserQuestion` call (options, the recommended one first; never a typed question in chat). Skip any
question the request already answers; if it answers all, ask nothing.
- **What is it for?** Explain/teach (科普) · Launch/promote a product · Show how to do something · Other.
- **Language** of voice and captions (default: the request's language).
- **Length:** about 1 minute · 1-2 minutes (recommended for an explainer) · 2-3 minutes.
- **Material:** none (research it) · files or a folder (then ask the path) · a link.

When nobody can answer (a non-interactive run), take the recommended options and record them in `NOTES.md`.

### 2. Understand — the content (the skill's strength; never skip)

Do it exactly as the classic mode specifies:
- **Research and the brief** — classic step 3 (`references/classic-pipeline.md`, "Understand the material
  DEEPLY"). Read the material properly, or research the topic up to today; capture every passage a claim rests
  on with `scripts/sources.py add` (tier the source; date time-sensitive facts with `--as-of`); write
  `<film_dir>/brief.json` (thesis, mechanism, evidence with `source_ref`, why_it_matters, the_one_thing,
  misconceptions, unknowns, coverage, source_health, self_check). Gate: `python3 scripts/brief_qa.py <film_dir>`.
  A deck, PDF or image folder given as material is read through `scripts/ingest.py` (toolbox).
- **The content plan** — classic step 3.5: dispatch `agents/content-planner.md` with the brief, the material, and
  the purpose from step 1. Save `<film_dir>/content_plan.json` (audience, viewer_question, arc, beats with
  introduces/builds_on/stage, the climax). Gate: `python3 scripts/pedagogy_qa.py <film_dir>`.

The plan's beats are IDEAS, not shots. Several may live in one continuous sequence; one may need two shots.

### 3. Script — for the ear

Write `<film_dir>/script.json`: spoken lines grouped into **3-6 sequences** (hook · setup · build… · payoff ·
close), each line one idea, in the order of the content plan, covering all of it. A hook in the first 3-5 seconds
that SHOWS a tension; short sentences; numbers said the way people say them; every fact traceable to the brief; no
filler, no AI voice tics. Fit the length with `scripts/pace.py --budget`; over length → cut lines, never speed the
voice past natural.

### 4. Voice first — then lock the cut

Voice the lines with `scripts/say.py` (the skill's voice layer: word timings in the written words, a pronunciation
lexicon for 多音字 and names, initialisms spelled for a Chinese voice; voices and flags in the toolbox). Fix a
misreading in the lexicon, never in the caption. Trim silences, keep pauses inside a line short and give each
sequence seam a breath. Write `<film_dir>/timeline.json` from the timings: every line's start/end, every word's
time, the sequence seams. **This timeline is the film's clock: every picture is built to it.** Captions are chunked
from it.

### 5. One look — the user picks it (the one checkpoint)

0. **If the user named a style** ("Memphis 风格", "like a blueprint", "像纪录片那样"), that is the look: render one style
   frame to set it and skip the choice. A brand's colours still apply.
1. **Think about the vibe first**: what should this film FEEL like to its audience (playful, calm, urgent, warm,
   precise, nostalgic, premium…), and what does the subject itself look like? Then shortlist 2-3 GENUINELY
   DIFFERENT looks. `references/video-looks.md` (11 looks: flat illustrated, mathematical, editorial motion
   graphics, kinetic type, product UI, lit 3D, isometric, cut-out collage, documentary, whiteboard, retro registers)
   is a vocabulary, not a menu: blend two, bend one to the subject, or invent the look the subject calls for. Fit
   beats habit. Palette and type come from a sub-register in `references/visual-styles.md` (its vetoes apply: no
   playful register on a somber subject, no busy ground under data); a brand's colours override the palette.
2. For each, render ONE **style frame**: a 1920x1080 still of the film's real subject at its key moment, in that
   look, with a caption. **The frames must differ as LOOKS** (palette, typeface, how the subject itself is drawn,
   ground and texture), not as borders or background colours.
3. Tile the frames, show them, and ask (`AskUserQuestion`, recommended first, one line of why each).
   **Non-interactive:** still render and compare all the frames, take the strongest, and keep the sheet in
   `<film_dir>` so the user can switch later.

The chosen look is **held for the whole film**: palette, type scale, grid, ground, light. Variety comes from
composition and scale, never from changing the look. Also decide the film's **recurring subject** here: the one
thing the film keeps returning to and transforming (the code being torn, scanned and repaired; the companion
and its three file cards). This, more than anything else, made the winning films feel like one film.
Decide its **motion voice** too: one set of timings and easing for every entrance, transition and hold, chosen from
the brand's energy (calm/premium ↔ bold/startup) and tone (serious ↔ playful); two voices in one film read as a
patchwork (presets in `references/promo-shotcraft.md`).

### 6. Build — sequence by sequence

**The unit is the sequence.** Each sequence is one world (subject, ground, camera language) and flows inside
itself; the world changes only at a seam. Within it, every shot has one focal point, appears with its words
(the cut lands ~0.1-0.2 s before the word), and moves with intent. Read `references/director-craft.md` (editing,
teaching, design, motion and sound principles) before building.

**Engine.** Default: one HTML page for the whole film (`film.html`) in which **every frame is a pure function of
time** (`window.seek(t)`: no CSS transitions, no timers, no randomness), captured frame by frame with headless
Chrome at 1920x1080, 30 fps, encoded with ffmpeg. Pieces made elsewhere (a Blender clip, a library shot rendered
through the workshop) are placed as frames the page draws by frame number.

**The kit, where the look calls for it** (commands in the toolbox): light and material from the Remotion runtime;
real 3D from Blender (`scripts/blender_clip.py`) for what 3D physicality IS the content of — a real object, a
material, optics, physics, a device (the product's real screen on a lit MacBook); the library's 227 shots and its
objects as parts inside a film's own workshop shot, rendered in the film's look (a FULL palette file; on a light
look, render one frame of it and read every word, since some library shots hard-code light ink); real images (`imagefetch`), page
captures, generated atmosphere (`imagegen --prompt`, never a fact); icons; CJK caption breaks.

**Accents** — small motion effects (动效) that make a moment FELT, drawn as motion, not as emoji glyphs. Where they
go is your judgement, not a mapping: find the moments the viewer should feel something — an answer landing, a
reveal, a turn in the argument, a number that surprises, the product finishing the job, a joke, the payoff — and
design the motion that fits that moment, subject and look: a burst of confetti with a ring and rays, a sparkle, a
glow pulse, a shockwave, a stroke drawing itself, a number counting up, a short phrase (花字) popping in, or one built
from the subject itself (a torn QR corner scattering as fragments). No effect belongs to a particular element.
Under a second, trailing what it marks; sparing (roughly one per 15-30 s in an explainer, more in a playful or
launch film, none on a somber subject); energy matched to the look; drawn BEHIND what it celebrates so its text
stays readable. `assets/html/accents.js` gives them as pure functions of time, with no overshoot.

**Rules every frame obeys** (each one cost a real film a defect):
- **Every drawn thing is correct.** A cat has four legs, a hand five fingers, a molecule its real bonds, a device its
  real ports; a simplified model is drawn as a simplification OF the real thing, never as a new creature. Before
  building, look at a real reference (a photo, the source's figure) for each recurring drawn subject; label a
  schematic as a schematic (示意).
- Nothing cut off, overlapping or unreadable; nothing in the caption band but the caption.
- **Never draw a raster beyond its native pixels**; a real screenshot is cropped and pushed within its density.
- Time runs one way: a state reached stays reached; nothing replays after a cut; nothing overshoots and shrinks back.
- No slow constant creep on fine detail (hard edges shimmer); a camera move has a job and an end.
- No blank holds: every shot puts its subject on screen from its first frame (lead the cut by ~0.1 s).
- Text on screen is labels, keywords and numbers, never the narration as body text.
- **Text is either read or texture.** Words meant to be read are big enough on a phone: captions ≥ ~56 px at 1080p
  (about 5 % of the frame height; `caption_size_qa` measures it), labels ≥ ~32 px, counted on the rendered frame
  with every scale applied. Small text not meant to be read is visibly softened or dimmed; nothing in between.
- Build each sequence, export its settled frames, look at them, fix, then move on.

**A launch or product film** usually works best with the real product as the hero at size (its real screens large,
or a crop onto the component the voice names), one persistent hero object, short type beats between product beats,
the real logo early and a closing lockup, one small celebration, and a quick rhythm (the full grammar and its
evidence in the toolbox). What lifts one from correct to crafted (`references/promo-shotcraft.md`, studied from a
mature promo-film practice): the product's UI staged as **physical objects in a lit space** (thickness, contact
shadows, one light, 3D angles), not flat screenshots on a gradient; the film's look grown from the **product's own
design system**; every feature mapped to one shot and **each technique the star only once**; a focused opening (one
hero, a complete ≥3 s arc) climbing to the energy peak at the close; **designed holds** (key number or wordmark ≥1 s,
0.5 s after a batch, interactions at human speed); speed from **acceleration**; **no bare cuts** between scenes; and
feature demos as **causal chains** (cursor, press, state change, reward). Read it before building one.

**Render** `<film_dir>/final.mp4`: 1920x1080 (or 1080x1920 when asked for vertical), 30 fps, H.264 + AAC. Write
`<film_dir>/_plan.json` (format in the toolbox) with the cut frames computed by **the same rule the renderer uses to
switch shots**.

### 7. Sound

- **Voice** on the timeline, levelled; master the mix to about -14 LUFS with true peak at or under -2 dBTP.
- **Music follows purpose:** an explainer can do without; a launch or promo is scored (`scripts/score.py`, or the
  user's own track), well under the voice and ducked while it speaks.
- **SFX** on a few real events, short and high-passed (`scripts/sfx.py --cues`: 15 synthesised sounds). Not every cut
  gets a sound. A product film speaks the film vocabulary (whoosh, impact, riser, sparkle) with real foley for
  visible actions, never game-feedback tones (`references/promo-shotcraft.md` §4).

### 8. Check, fix, deliver

1. `python3 scripts/film_qc.py <film_dir>` runs flash, rewind, picture-glide, empty-frame, shake and caption-size checks against
   `final.mp4` and `_plan.json`, and exits 1 on any red. Fix the film, re-render, re-run until CLEAN.
   A red you believe is wrong is never silenced and never "fixed" by cutting good content: PROVE it on the frames
   (measure the thing the check claims) and with a CONTROL (the same shot with the suspected cause removed), and
   record both in `NOTES.md` (the checks' known blind spots are in the toolbox).
2. **Look at the real film**: a contact sheet of every shot's settled frame (~90 % through the shot) on one image.
   One layout repeated, a frame cut off, a caption over a picture, an empty hold, a sequence that drops the look:
   fix before delivering. Then watch transitions at the seams.
3. **Accuracy, of words AND pictures**: every number, name and quote on screen or in the voice traces to the
   brief's sources; and every drawn subject is checked on a close settled frame against its real reference: count
   its parts (legs, fingers, wheels, keys), check proportions, direction and labels. A wrong drawing is a factual
   error, fixed before delivery like a wrong number.
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
Other references: `director-toolbox.md` (the director path's commands), `promo-shotcraft.md` (product-film technique), `pipeline-scripts.md` (every script),
`troubleshooting.md`, `engineering-case-law.md` (why the rules are what they are), `motion-grammar.md`,
`launch-film-study.md`, `craft-standard.md`.
