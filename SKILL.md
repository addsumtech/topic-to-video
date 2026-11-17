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

0. **If the user named a style** ("Memphis 风格", "like a blueprint", "像纪录片那样"), that is the look: map it to
   its look and sub-register, render one style frame to set it, and skip the choice. A brand's colours still apply.
1. **Think about the vibe first**: what should this film FEEL like to its audience (playful, calm, urgent, warm,
   precise, nostalgic, premium…), and what does the subject itself look like? Then shortlist 2-3 GENUINELY
   DIFFERENT looks. `references/video-looks.md` is a vocabulary, not a menu: its 11 looks (flat illustrated,
   mathematical, editorial motion graphics, kinetic type, product UI, lit 3D, isometric, cut-out collage,
   documentary, whiteboard, retro registers) and its choosing map are starting points. Blend two (risograph inks on
   real archival photos), bend one to the subject, or invent a look the subject calls for, and say why in a line.
   Fit beats habit: a blueprint is a fine look and still the wrong one for a cat's playful physics (the user,
   2026-11-17). For each, take the palette and type from a sub-register in
   `references/visual-styles.md` (its guardrail vetoes apply: no playful register on a somber subject, no busy
   ground under data). A brand's own colours and logo override the palette, not the look's technique.
2. For each, render ONE **style frame**: a 1920x1080 still of the film's real subject at its key moment (the real
   QR code, the real product screen), in that look, with a caption. `python3 scripts/theme.py <film_dir> --style
   <key>` gives the style's contrast-safe palette and type as CSS variables. **The frames must differ as LOOKS**:
   palette, typeface, how the subject itself is drawn (lit and photographic, flat and graphic, inked, printed…),
   ground and texture. The same picture with a different border or background colour is one look, not three
   (the first end-to-end run, 2026-11-16, offered exactly that, which made the choice meaningless).
3. Tile the frames on one image, show it, and ask (`AskUserQuestion`, recommended first; each option names the
   style and one line on why). **Non-interactive** (nobody can answer): still render and tile all the frames —
   comparing finished frames is how the strongest look is found (two runs of the same request on 2026-11-16/17
   chose very different looks; the one that skipped the frames chose without ever comparing) — then take the
   strongest and keep the sheet in `<film_dir>` so the user can switch later.

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

**Everything the classic version built is yours to use** where it serves this film (none of it is required):
- **Writing:** `agents/scriptwriter.md` can draft the narration from the plan; one round of `agents/critic-narrative.md`
  on the draft catches what the ear misses. `scripts/pace.py` for length.
- **Real material:** `scripts/promo_capture.py <film_dir> <url> --name=<n>` and `scripts/capture_page.py` capture a
  real product page at 2x; `scripts/imagefetch.py` fetches real, licensed images of a named subject.
- **Pictures:** the kit above (lit stage, materials, Blender plates, objects such as devices and the Earth, the 227
  library shots inside a workshop shot, rendered with `workshop.py <film_dir> clip`); `scripts/theme.py --style`
  for a contrast-safe palette; `scripts/caption_words.py` for where a CJK caption may break.
- **Sound:** `scripts/score.py` (a generated score on a beat grid), `scripts/sfx.py` and `assets/sfx/`.
- **Checks:** everything in `film_qc.py`; any other script in `references/pipeline-scripts.md` that takes a film
  folder or an mp4.

**Accents** — small motion effects (动效) that make a moment FELT, drawn as motion, not as emoji glyphs. Where they
go is your judgement, not a mapping: read the script and the cut and find the moments the viewer should feel
something — an answer landing, a reveal, a turn in the argument, a number that surprises, the product finishing the
job, a joke, the payoff — then design the motion that fits that moment, that subject and that look. The vocabulary
is open: a burst of confetti with a ring and short rays, a sparkle, a glow pulse, a shockwave from an impact, a
stroke drawing itself (underline, circle, arrow, tick), a number counting up, a short phrase (花字) popping in, or
one you build from the subject itself (the torn corner of a QR code scattering as fragments, light rays fanning from
a lens). No effect belongs to a particular element: a celebration may mark a cat landing as well as a file being
ready, and a ticked box needs none if the moment is not one to feel.
- **Earned, brief, sparing**: under a second (accent lines 4-10 frames), trailing what it marks by a few frames; the
  text stays still. As a rough measure, one every 15-30 s in an explainer, more in a playful or launch film, none
  on a somber subject; a moment that does not move the viewer gets none. Energy matches the look: a calm look gets
  a quiet stroke or glow, a playful one can take confetti.
- **Deterministic, no overshoot**: `assets/html/accents.js` (burst, ring, rays, sparkle, pop, drawOn, countUp) gives
  each as a pure function of time and seed; a celebration is `burst` + `ring` + `rays` started together. Never `Math.random` in a film page; never grow past full size and shrink back (rewind_qa
  reads it as the picture going back).
- **Behind, not over**: a celebration (confetti, ring, rays) is drawn BEHIND the element it celebrates, so its text
  stays readable while the burst plays; an underline or circle sits on its word, never across the next line.
- **Sound**: an accent may get a short sound (a click, select or drop from `assets/sfx/kenney/`), quiet under the
  voice; not every accent needs one.

**Rules every frame obeys** (each one cost a real film a defect):
- **Every drawn thing is correct.** A cat has four legs, a hand five fingers, a molecule its real bonds, a device its
  real ports; a simplified model is drawn as a simplification OF the real thing, never as a new creature (a Memphis
  film drew the physics model's two body halves as two cats' worth of legs: eight, 2026-11-17). Before building,
  look at a real reference (a photo, the source's figure) for each recurring drawn subject; label a schematic as a
  schematic (示意). For a built object in the kit, `workshop.py <film_dir> fidelity <Name>` compares it to its
  references (`references/object-audit.md`).
- Nothing cut off, overlapping or unreadable; nothing in the caption band but the caption.
- **Never draw a raster beyond its native pixels**; a real screenshot is cropped and pushed within its density.
- Time runs one way: a state reached stays reached; nothing replays after a cut.
- No slow constant creep on fine detail (hard edges shimmer); a camera move has a job and an end.
- No blank holds: every shot puts its subject on screen from its first frame (lead the cut by ~0.1 s).
- Text on screen is labels, keywords and numbers, never the narration as body text.
- Build each sequence, export its settled frames, look at them, fix, then move on.

**A launch or product film** usually works with this grammar (a starting point measured on 20 official launch films, `references/craft-standard.md`
"A product film"; `references/launch-film-study.md`). The WorkBuddy blind round showed what happens without it: the
film that kept the real product large matched one that redrew the product as icons on empty paper.
- **The real product is the hero, at size.** Its real screens fill most of the frame (about 55 % of the width or
  more), or a crop pushes onto the exact component the voice names, within the screenshot's pixel density. A
  redrawn icon, card or device outline is a stand-in: use one only where no real screen shows the idea.
- **One hero object persists**: the product's window stays, and the beats are its states, not new scenes.
- **Type beats alternate with product beats.** A type beat is one short display line on the brand ground (the
  problem, the promise, the payoff), the key word in the brand accent.
- **The brand early and at the end**: the real logo within the first ~10 s, and a closing lockup (mark + line).
- **One small celebration** (a task completing, a toast) and a quick rhythm: few shots hold still past 1 s.

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

1. `python3 scripts/film_qc.py <film_dir>` runs flash, rewind, picture-glide, empty-frame and shake checks against
   `final.mp4` and `_plan.json`, and exits 1 on any red. Fix the film, re-render, re-run until CLEAN.
   A red you believe is wrong is never silenced and never "fixed" by cutting good content: PROVE it on the frames
   (measure the thing the check claims, e.g. the moving edge's position per frame) and with a CONTROL (the same
   shot with the suspected cause removed), and record both in `NOTES.md`. Known blind spot of picture_glide_qa:
   a sky or light whose colours change with nothing moving, and a fast move over a near-textureless gradient.
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
Other references: `pipeline-scripts.md` (every script), `troubleshooting.md`, `engineering-case-law.md` (why the
rules are what they are), `motion-grammar.md`, `launch-film-study.md`, `craft-standard.md`.
