---
name: topic-to-video
slug: topic-to-video
displayName: Topic to Video
version: 3.0.0
description: >-
  Turn ANY topic — or a slide deck — into a narrated explainer or launch short video,
  automatically: researches the topic, writes the script and lets the user HEAR it and
  pick the voice, designs the film (concepts, hero keyframes, an animatic on the real
  voice for the user to approve), builds it in one look sequence by sequence (with
  lighting, material and 3D where it fits), adds sound, captions and subtitles, and
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

**Full effort, every time** (the user, 2026-11-14: "make the skill never shy away from effort, at any point; use your full potential and creativity"):
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
the current directory). Steps 1-8 run to the finished film. **A film whose folder already has work in it (a run
stopped at a usage limit or a crash) is resumed, never started over:** `python3 scripts/film_status.py <film_dir>`
reads what is done, what is stale (code edited after its frames, frames after the encode, the encode after the check)
and what comes next, with the command for it. The user decides at FOUR moments and nowhere else:
the intake (step 1), the script and voice they HEAR (step 4), the design (step 5) and the animatic (step 5b) — a
small studio's sign-offs, each where the user can actually judge (the user, 2026-11-18: "there should be some info
collection stages to let user decide"). Non-interactive: take the recommended option at each, record it in
`NOTES.md`, and do the checkpoint's own check yourself (listen, look) before going on.

**Design is judgement, not a menu** (the user, 2026-11-17: "design has to be flexible: components, vibe, all of it"). Only a few things
in this file BIND every film: the facts are sourced, every drawn thing is correct, everything is readable and
nothing sits in the caption band, rasters stay within their pixels, real brands stay real, and `film_qc` is clean
(or a red is proved wrong). Everything else (the looks and their palettes, components and kit pieces, accents, the
launch grammar, sequence counts, the craft principles, every example here) is a VOCABULARY: use it, combine it,
bend it, or leave it, by what this subject, this audience and this moment need, and invent what the vocabulary
lacks. A choice that departs from a suggestion here gets one line of why in `NOTES.md`; that is all it needs.

**You are the film's designer** (the user, 2026-11-17: "always remember you are a video designer… create anew on your own… from refined taste and
sharp insight"). The references (looks, craft principles, promo technique) are your technique stack, studied so you can
execute anything; your taste decides what the film should be. Every film carries at least one **signature idea**
that only this subject could have — an aha found by looking hard at the subject itself, not picked from a list: the
diamond's fire rendered from its real dispersion; the sky computed by the physics the film explains; the QR code
decoded on the film's own frames; the one-sentence prompt line that deals out the finished files. Decide it before
building, name it in the plan (`signature`) and in `NOTES.md`, and give it the film's best moment. Learning a
technique is the start: bend it, combine it, invent past it. Train the eye with `references/taste-notes.md` (what
good frames do, seen and judged) and give every frame its ten-second designer's pass.

### 1. Ask — once, plainly, with options

Use ONE `AskUserQuestion` call (options, the recommended one first; never a typed question in chat). Skip any
question the request already answers; if it answers all, ask nothing.
- **What is it for, and who watches?** Explain/teach (popular science) · Launch/promote a product · Show how to do
  something · Other (the audience and where it plays — a homepage, a keynote, a feed — go in Other or follow-up).
- **Language** of voice and captions (default: the request's language).
- **Length and shape:** about 1 minute · 1-2 minutes (recommended for an explainer) · 2-3 minutes · a vertical
  short (9:16, 30-60 s, for a feed).
- **Material:** none (research it) · files or a folder (then ask the path) · a link.

A second screen only when it applies: **brand assets** (a product or company film: logo + colours · colours only ·
none; then the path) and **music** (a launch or promo: a generated score, recommended · my own track (path) · none).
The voice is NOT asked here: the user picks it at step 4, after hearing it.

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

### 4. Hear the script, choose the voice — then lock the cut

**The script is approved by EAR, not by reading** (a script that passed every metric was called machine-written on
its first listen). `python3 scripts/script_audition.py <film_dir>` speaks five lines (hook, a middle pair, the
payoff, the close) in the film's voice into `audition.mp3`; `python3 scripts/voice_qa.py <film_dir>` marks places to
listen for (advisory). Listen yourself, fix what sounds written, then **checkpoint 1**: show the script and the
audition, and ask (`AskUserQuestion`): **keep this voice** (free, recommended for an explainer) · **MiniMax** (paid,
the most natural, especially Chinese) · **OpenAI** (paid) · Other (an accent, a gender). A paid pick: say how many
characters the full film sends, get the key out of band (never pasted into chat), then for MiniMax ask the gender
and play `scripts/voice_sample.py` candidates; re-audition in the chosen voice with
`script_audition.py <film_dir> --voice minimax:<id> --allow-paid`; the user signs off on the voice they will get.
Never spend before that pick.

Then voice every line with `scripts/say.py` (the skill's voice layer: word timings in the written words, a
pronunciation lexicon for characters with more than one reading and for names, initialisms spelled for a Chinese
voice; a paid or `say` voice, which reports no timings, gets them ALIGNED from the free voice saying the same words —
`scripts/word_align.py`, median error ~10-30 ms; voices and flags in the toolbox). Then hear it back:
`python3 scripts/voice_asr_qa.py <film_dir>` transcribes the voice (faster-whisper, ~30 s for 2 minutes) and holds
every line against the script and its caption times — a dropped or doubled phrase or drifting captions are red, a
single misheard word is a place to listen. Fix a misreading in the lexicon, never in the caption. Trim silences, keep pauses inside a line short and give each sequence seam a breath. Write
`<film_dir>/timeline.json` from the timings: every line's start/end, every word's time, the sequence seams. **This
timeline is the film's clock: every picture is built to it.** Captions are chunked from it.

### 5. Design — concepts, hero moments, keyframes (a dedicated designer; checkpoint 2)

**Understood first, then remembered.** A frame a first-time viewer cannot read in about a second fails however
beautiful it is; a clear film nobody remembers fails too (the user, 2026-11-17: "we don't want mediocre one… avoid the
ordinary"). The order matters: chasing "stunning" first produced a Grok Bot film of tilted screens in an abstract
tower that lost to an older, plainer film whose own characters acted out the product. Design gets its own phase, its
own agent and its own effort, because a single pass that also researches, builds and fixes gates converges on safe
and forgettable.

1. **Dispatch the designer**: `agents/film-designer.md` (`topic-to-video:film-designer` when the plugin registers it;
   otherwise a general-purpose agent given that file as its instructions), **with effort "high"** and a fresh
   context. Give it the brief, `script.json`, `timeline.json`, the purpose and length, the material in `input/`, and
   the user's taught taste (`python3 scripts/taste_ledger.py brief --stage design`, rules in the user's own words);
   nothing about gates. It writes `design/story.md` (the viewer's journey: for a product film, how the product WORKS,
   not only what it made), `design/concepts.md` (three concepts, the first always the product's OWN world, its
   characters, UI and marks, acting the journey out; and the choice), the three **hero moments** rendered as finished
   keyframes (`design/keyframes.jpg`, redesigned until each reads in a second and stays in the memory), a
   `design/treatment.md` with every shot's picture (not only the heroes'), and a draft `shot_plan.json`. If a film on
   this subject already exists, give the designer its path: the new one is judged side by side with it.
2. **Checkpoint 2.** Show the user the three concepts (one line each) and `design/keyframes.jpg`, and ask
   (`AskUserQuestion`): go with this concept, take another of the three, or push it further. **Non-interactive:** one
   round of `agents/keyframe-review.md` (a fresh-eyed reviewer, effort "high") on the keyframes, given each frame's
   spoken line and the baseline film when one exists; the designer revises
   every frame it calls unclear or forgettable, then the build starts. One round, not a loop.
3. **A style the user named** ("a Memphis style", "like a blueprint", "like a documentary") is a constraint on the
   designer's concepts, not a replacement for them. A brand's own colours and logo always apply.

### 5b. The animatic — the film on its real clock, rough (checkpoint 3)

Before the full build, block the WHOLE film in `film.html`: every shot placed on the timeline with its subject,
framing and camera move, the heroes from the keyframes, the rest rough (grey boxes, plain colour) — no polish. Then
`python3 scripts/animatic.py <film_dir> --page film.html` cuts it to the real voice in seconds (`design/animatic.mp4`,
each shot at 20/50/85 %, the line under the picture; `design/boards/<shot>.png` overrides a shot). **Checkpoint 3:**
the user watches it and approves the rhythm, the cuts and what is on screen under each line, or names the shots to
change. Problems found here cost minutes; after the build, a re-render each (a 1.5 s pull from close to wide, a
scribble standing in for an idea, two shots of one framing were all visible in a Grok Bot animatic).
Non-interactive: watch it yourself shot by shot, fix what does not read, then build.

The designer draws on `references/video-looks.md` (11 looks), `references/visual-styles.md` (palettes, type and their
vetoes: no playful register on a somber subject, no busy ground under data), `references/taste-notes.md` and
`references/promo-shotcraft.md` as a technique stack. Whatever it chooses is **held for the whole film**: one world,
one light, one **motion voice** (timings and easing from the brand's energy and tone; two voices read as a
patchwork), one **recurring subject** that transforms from first frame to last (the code torn, scanned and repaired;
the logo's cursor that types the task) — the thing that, more than anything else, makes a film feel like one film.

### 6. Build — sequence by sequence

**The unit is the sequence.** Each sequence is one world (subject, ground, camera language) and flows inside
itself; the world changes only at a seam. Within it, every shot has one focal point, appears with its words
(the cut lands ~0.1-0.2 s before the word), and moves with intent. Read `references/director-craft.md` (editing,
teaching, design, motion and sound principles) before building.

**Engine.** Default: one HTML page for the whole film (`film.html`) in which **every frame is a pure function of
time** (`window.seek(t)`: no CSS transitions, no timers, no randomness; canvas text drawn only after its fonts load),
captured frame by frame with `scripts/film_frames.py` (headless Chrome at 1920x1080, 30 fps; it refuses text drawn
before its font and probes that a frame is the same in any page), encoded with ffmpeg. **The hero moments are built first**, from the designer's
keyframes, and every other shot is built to its line in the treatment: the shots between the heroes are where
labels, tilts and filler creep in. **3D where physicality is the content**: the product's characters or mascot as
soft lit bodies that ACT (`assets/html/stage3d.js`: `st.inflate` builds the body with its eyes as separate raised
pieces; `Stage3D.hop` for an arc with anticipation and a volume-keeping squash, `Stage3D.carry` for what it holds,
`Stage3D.blink` and `Stage3D.look` so it is alive between moves), a device, an object; a screen can be a lit panel
there, and settles facing the viewer when it carries something to read. **Devices come from the kit** (`st.phone`, `st.tablet`, `st.laptop`), never made of boxes or a 2D outline (they read as
fake, Grok Bot 2026-11-18), each showing the layout made FOR it (another screen only whole, letterboxed, never cropped);
**app screens are HTML** (`Stage3D.screen`: the browser lays them out and the checks look inside them), each built
from a real reference in the film folder (an official screenshot, measured), never from memory; a terminal program
is CAPTURED (`scripts/term_capture.py`, drawn by `Stage3D.terminal`: an imitated Claude Code read as fake, job-hunt
2026-11-19); a caret is `Stage3D.caret` (one inside the line box made lines jump at each blink); a row of
categories, roles or steps carries one icon each, of one family (`references/icons.md`, Lucide); cards are
`st.card` with the picture's own corners; a mark that frames an object follows its tilt (`st.quad` + `Stage3D.brackets`). All in the toolbox,
"Devices, app screens, cards, marks". Create stages with `pixelRatio: 2`
(supersampled; the default read as low resolution) and no `dof` near words or marks (its few-tap blur ghosts them).
When the MATERIAL is the point of a hero (a product's shell, metal, glass), render that shot in Blender under
`kit.studio.product_light` with a named finish per part (`scripts/blender_clip.py`; references/craft-study.md: lit
surfaces were the measured gap) and place it as frames. A film that stages every
screen as a tilted panel on a dark floor turns into a visible device (rejected on Grok Bot twice, 2026-11-12 and
-17); alternate grounds (light UI shots, dark 3D shots) for rhythm. Commands in the toolbox. Pieces made elsewhere (a
Blender clip, a library shot rendered through the workshop) are placed as frames the page draws by frame number.

**The kit, where the look calls for it** (commands in the toolbox): light and material from the Remotion runtime;
real 3D from Blender (`scripts/blender_clip.py`) for what 3D physicality IS the content of — a real object, a
material, optics, physics, a device (the product's real screen on a lit MacBook); the library's 227 shots and its
objects as parts inside a film's own workshop shot, rendered in the film's look (a FULL palette file; on a light
look, render one frame of it and read every word, since some library shots hard-code light ink); real images (`imagefetch`:
Commons or NASA, `--candidates` to look before `--pick`; a crop of one is declared in `images_ok.json` so its credit
carries over, and `film_qc` holds every picture the page names to a record), page
captures, generated atmosphere (`imagegen --prompt`, never a fact); icons; CJK caption breaks.

**Accents** (a moment made FELT in motion, never an emoji glyph; where, how and how often: `references/director-craft.md`
§4, "Accents"; `assets/html/accents.js`).

**Rules every frame obeys** (each one cost a real film a defect):
- **Every drawn thing is correct.** A cat has four legs, a hand five fingers, a molecule its real bonds, a device its
  real ports; a simplified model is drawn as a simplification OF the real thing, never as a new creature. Before
  building, look at a real reference (a photo, the source's figure) for each recurring drawn subject; label a
  schematic as one, in the film's language.
- Nothing cut off, overlapping or unreadable; nothing in the caption band but the caption.
- **Never draw a raster beyond its native pixels**; a real screenshot is cropped and pushed within its density.
- Time runs one way: a state reached stays reached; nothing replays after a cut; nothing overshoots and shrinks back.
- No slow constant creep on fine detail (hard edges shimmer); a camera move has a job and an end.
- No blank holds: every shot puts its subject on screen from its first frame (lead the cut by ~0.1 s).
- Text on screen is labels, keywords and numbers, never the narration as body text.
- **Text is either read or texture.** Words meant to be read are big enough on a phone: captions ≥ ~56 px at 1080p
  (about 5 % of the frame height; `caption_size_qa` measures it), labels ≥ ~32 px, counted on the rendered frame
  with every scale applied. Small text not meant to be read is visibly softened or dimmed; nothing in between.
- Build each sequence, export its settled frames, look at them, fix, then move on. Before a sequence is handed on
  (each builder's shots, when the build is split), run the checks on its own rendered frames:
  `python3 scripts/film_qc.py <film_dir> --frames A-B` (the same checks on that stretch, about 30 s per 6 s of film).
  A red found there costs one shot; found on the assembled film it costs a re-render, re-encode and re-check of all
  (MRI 2026-11-19: seven checks red across four builders' shots, an hour).
- A Blender shot is settled (framing, move, easing, look) on `--still` frames and a small fast clip
  (`--size 960x540 --samples 8`) before its ONE full render: a full 1080p clip costs minutes per second of film (MRI:
  one 2.8 s shot, 34 min to re-render in a fix round).

**A launch or product film** usually works best with the real product as the hero at size (its real screens large,
or a crop onto the component the voice names, where they READ at that size; where they do not, a phone screenshot or
a small dialog on a big desktop, draw the UI simplified and honest: the real layout and colours, the product's own
words verbatim from the sources; a device with no official screenshot (the desktop app) takes the layout of the
closest one (the iPad app), never an invented one). The DEMO WORLD inside a screen (a fictional company's inbox, a slide
title, a file name, a terminal command) is written as plausible, generic demo content — Acme-style names, never a
statistic or a claim about the real product — and each string is declared in `copy_ok.json` with the reason `demo`;
grey bars only for text too small to read (grey bars at a readable size look like a wireframe, not an app), its own characters acting the steps out when it has any, one persistent hero object, short type beats between product beats,
the real logo early and a closing lockup, one small celebration, and a quick rhythm (the full grammar and its
evidence in the toolbox). Before building one, write `<film_dir>/shot_plan.json` (features → shots, each shot's
job, technique and seam, the motion voice, the signature idea; format in `scripts/shot_plan_qa.py`) and pass
`python3 scripts/shot_plan_qa.py <film_dir>`; `film_qc` then holds the film to it (`seam_qa`: a seam planned as hidden
must not be a bare swap; build the seam the plan names, never a generic cross-dissolve to pass it: a dissolve
between two viewpoints of the same characters double-exposes them (Grok Bot 2026-11-18: two approval cards and two
Bots at once). Where the same subject carries across, plan a `match` cut). An explainer may write one too, and gets the same checks. What lifts one from correct to crafted — the UI
as physical objects in a lit space, the look grown from the product's own design system, each technique the star
once, a focused opening climbing to the close, designed holds, no bare cuts, demos as causal chains — is
`references/promo-shotcraft.md`; read it before building one.

**Render** the frames with `python3 scripts/film_frames.py <film_dir>` (1920x1080, or 1080x1920 when vertical; 30
fps) and write `<film_dir>/_plan.json` (format in the toolbox) with the cut frames computed by **the same rule the
page uses to switch shots**; `python3 scripts/film_deliver.py <film_dir> --encode` makes `final.mp4` (H.264 + AAC
with a fine grain finish: an 8-bit dark gradient otherwise bands after encoding).

### 7. Sound

- **Voice** on the timeline, levelled; master the mix to about -14 LUFS with true peak at or under -2 dBTP.
- **Music follows purpose:** an explainer has none (music under narration costs recall); a launch or promo is scored (`scripts/score.py`, or the
  user's own track), mixed by `scripts/mix.py`: about 20 dB under the voice while it speaks, by measurement (a film's
  own hand-set mix left its score 2 dB under the words, job-hunt 2026-11-19).
- **SFX** on a few real events, short and high-passed (`scripts/sfx.py --cues`: 15 synthesised sounds). Not every cut
  gets a sound. A product film speaks the film vocabulary (whoosh, impact, riser, sparkle) with real foley for
  visible actions, never game-feedback tones (`references/promo-shotcraft.md` §4).

### 8. Check, fix, deliver

1. `python3 scripts/film_qc.py <film_dir>` runs flash, rewind, picture-glide, empty-frame, shake, caption-size, pan-speed,
   (with a film page) word/control overlap, a line cut by the frame's edge, a picture that shows almost nothing, and
   on-screen copy (every word sourced or declared in `copy_ok.json`),
   (on a stage3d page) 3D contact checks against
   `final.mp4` and `_plan.json`, and exits 1 on any red; the checks run side by side (a 2-minute film in a few
   minutes). Fix, re-render only the frames that changed (`film_frames.py --from/--to`), encode once, and re-run just
   the reds (`--only rewind,seams`) until CLEAN. ONE round of this, then step 2 and the user: the QR run spent two hours
   re-checking an already-checked film (the user's review is the judge, not repeated self-review).
   A red you believe is wrong is never silenced and never "fixed" by cutting good content: PROVE it on the frames
   (measure the thing the check claims) and with a CONTROL (the same shot with the suspected cause removed), and
   record both in `NOTES.md` (the checks' known blind spots are in the toolbox).
2. **Look at the real film the way the user will** — every shot at its settled frame (~90 %) on one sheet, AND the
   middle frame of every cut, AND frame by frame through every moving object and camera move (a defect in motion is
   between the settled frames: a card sunk into a head, two Bots double-exposed by a dissolve, an arrow that changed
   shape between render pages were all invisible on a contact sheet). One layout repeated, a frame cut off, a
   caption over a picture, an empty hold, a sequence that drops the look: fix before delivering.
3. **Accuracy, of words AND pictures**: every number, name and quote on screen or in the voice traces to the
   brief's sources; and every drawn subject is checked on a close settled frame against its real reference: count
   its parts (legs, fingers, wheels, keys), check proportions, direction and labels. A wrong drawing is a factual
   error, fixed before delivery like a wrong number.
4. Write `<film_dir>/NOTES.md`: what was made, the look and why, what the checks found and how it was fixed,
   anything not done. `python3 scripts/film_deliver.py <film_dir>` writes `final.srt` and the cover (the final
   film's hero shot, captions hidden — mark the page's caption element `data-caption`) and copies them with the film
   to the Desktop. Say where it is, its length, and the one thing it says. Offer: a vertical cut, a different look, a
   change to any line (re-voice that line, re-time, re-render).
5. **What the user teaches, the skill keeps**: each correction they give on the film goes into
   `python3 scripts/taste_ledger.py add --said "<their words>" --rule "<the rule>" --stage design|build|render`, so
   the next film's designer is briefed with it (step 5).

## Guardrails

- **Never fabricate.** No invented statistics, quotes, dates, features or sources, on screen or in the voice.
  Unsure → say it as reported, keep it qualitative, or cut it. A demo value printed on screen is a claim.
- **Real brand assets only.** A product film uses the product's real logo, colours and screens; never redraw a
  logo, never invent UI. Render a logo and look at it before deriving colours from it.
- **Imagery is faithful:** a generated image never stands in for a real object, place, person or data. A real one
  is shown with its real picture, from the user's material or an open source with its licence on record
  (`imagefetch.py`); the film's credits are written from those records.
- **A somber subject gets a sober look** (the style vetoes in `visual-styles.md`).
- **Ask before spending money** (cloud TTS, paid image generation).
- **Report honestly:** if a check is red and cannot be fixed, say so with its output.

## Classic mode and its references

`references/classic-pipeline.md` holds the full classic workflow, moved there verbatim on 2026-11-16: the deck
tiers (voice-as-is / designed HTML / cinematic Remotion), the storyboard, the interview, the critics, every gate and
its order, the shot library, promotion, and troubleshooting. Follow it whole when the classic mode is chosen.
Other references: `director-toolbox.md` (the director path's commands), `promo-shotcraft.md` (product-film technique), `pipeline-scripts.md` (every script),
`troubleshooting.md`, `engineering-case-law.md` (why the rules are what they are), `motion-grammar.md`,
`launch-film-study.md`, `craft-standard.md`.
