# Promo film and real-product beats — the product as itself, in our own language

Two ways in, one craft:
- **A product promo with no narration** is a shot table `promo.json`, rendered by `scripts/promo_film.py <dir>`
  (composition `PromoFilm`, `remotion/src/promo/`). It is SFX-led, or music-led with `--bgm`.
- **Any narrated film** uses the same camera and verbs as library registers:
  - `ProductPage` shows a real capture acting.
  - `ChapterCard` opens a chapter.
  - The beat pipeline gives them voice, cues, captions and the film's DNA.

## What we took from the reference films, and what is ours

The bar is video-shotcraft's showcase films and the brand films they studied (ClickUp, Notion, Raycast and others). We
distilled their **principles**, not their look:
- The product is shown as itself, sharp at every zoom.
- A card is a breath between product shots: one statement.
- There is one restrained look.
- Shots are short (1.5–6 s), and each one does something.
- Brand moments rest a full second.
- Sound is pinned to actions.

**The look is ours:**

| | the references | ours |
|---|---|---|
| title card | serif letterpress, amber italic word, underline | **chapter card**: `01 / 04` + the chapter's name, a progress hairline (the argument made visible), words rise through a mask (CJK by character), the accent span inked in the accent after it lands, words rise out at the end |
| cut | warm flash on hard cuts | **carry**: the leaving shot keeps travelling and smears, the arriving one comes out of the same smear (`cut: 'flash'` / `'hard'` remain) |
| emphasis | warm spotlight pool + dim | **rack focus**: the page goes out of focus and dims, the element stays sharp |
| annotation | floating serif note with marker | **callout**: an accent dot on the element, a leader line, a label (mono kicker + one line rising) |
| lift | perimeter beam laps | the element rises out of an **accent under-glow**, one sheen crosses it |
| outro | page pieces assemble, wordmark stamps | **recall**: the film's own shots return as a live wall that pulls back; the lockup **grows out of an accent dot** |
| brand open | letterpressed wordmark | the accent dot grows into the icon, the wordmark draws out of it |
| words | music-led, captions in mono strips | voice-led films supported: acts land **on the spoken word** (sync), captions on the frame's own ground |

## Captures — the raw material

`python3 scripts/promo_capture.py <dir> <url> --name=<n> [--wait=s] [--eval="js ;;; js"] [--full] [--select=css]`
- Opens the page at deviceScaleFactor 2, waits (bounded) for load, fonts and images, then runs the `--eval` steps
  to reach a state (load a scene, open a dialog).
- Writes `caps/<n>.png` (2x) and `caps/<n>.layout.json`:
  - every element's box in CSS px: controls, fields, cards, media, headings;
  - the page's own `title` and `description` (the product's words, citable).
- Also writes `<n>.boxes.jpg`: the boxes, numbered on a 50 px grid.

`--boxes=<png>` handles a screenshot with no DOM (a desktop app). It finds card-like rectangles (one fill, a visible
edge) and writes the same layout. On WorkBuddy it matched hand-measured boxes within 1–2 px.

`--mark=<png> --box=x,y,w,h` cuts the brand's logo from its own page with the ground keyed to alpha. On a dark film
the lockup sets it on a light plate.

Rules:
- **Captures:**
  - Never zoom past the capture's density: effective zoom ≤ 2 for a 2x capture. `check` refuses it and PageCam
    clamps it.
  - Zoom is authored at a 1920-wide reference, so the cap holds at every aspect.
  - A straight-on view stays inside the page (`contain`, on by default); a tilted view is an object shot and may show
    the ground.
  - For 9:16, prefer a portrait viewport capture (`--width=430 --height=932`). A landscape page in a tall frame
    leaves ground above and below.
- **Docs screenshots** often carry annotation boxes. Clean them, keeping gridlines and traffic lights, and look at the
  result.
- **Credits.** A capture of someone else's page is shown as itself and credited in the film's sources. A capture
  from docs is for review; public distribution needs the product owner's own captures.

## Stillness: the camera must glide, measured

A page under a moving camera that steps or shimmers reads as 抖动, the first thing a viewer notices. The camera is
built so it cannot do either, and `scripts/picture_glide_qa.py` measures both on every render. promo_film runs it; on
a narrated film, run it on the out_dir.

- **Laid out once, moved by one transform.** The page is laid out at the shot's largest zoom, inside one layer, and
  each frame is one 3D transform at zoom/raster ≤ 1. Setting CSS `zoom` per frame re-laid the page out and rounded it
  at every zoom: a staircase.
- **The raster is pinned** with `will-change: transform`. Without it each parallel render tab chose its own raster
  scale, which put a step at every chunk boundary.
- **No sub-pixel creep.** A sharp page creeping under a pixel a frame is crisp on a whole pixel and soft half-way
  between. Its strokes "breathe" at speed × 30 Hz, and no resampling filter avoids this (bilinear, bicubic and
  Lanczos all measured the same).
  - So a page camera either **holds still** or makes a **decisive move**. A key segment that never moves the picture
    faster than 8 px a frame is collapsed into a hold.
  - A move **lands with linear deceleration**: the velocity is a sine bump, peaking where the named curve does. The
    craft curves' long tails spent 10–15 frames creeping as they landed.
  - **Chapter cards do not push.** A lift does not wobble. A held page's life is its acts.
- **No corners in the camera's path.**
  - Containment is a soft clamp, smooth in the tilt.
  - The narrated-film timeline stretch is smooth.
  - The beat's clock is never warped (`CLOCK = 'own'`).
- **Moving type carries the baseline unlock** (runtime/glide).
- **Measured.** The zh Wikipedia film went from stepping (0.16–0.29 px) and breathing to 0.035–0.056 px with no creep.
  Its held stretches are pixel-still: in a slit-scan each stroke is a straight line of constant ink. The overlay type
  (jitter_qa) went from FAIL to OK.
- **The gate.** It judges position (stepping) and creep (shimmer sustained over at least 12 frames). A shot that fails
  is re-judged on a camera-only render: a sparse page whose texture is its popping elements measures the acts, not
  the camera.

## The table (`promo.json`)

```json
{"aspect": "16:9", "cut": "carry",
 "look": {"accent": "#6965db", "mode": "light"},
 "shots": [
  {"kind": "brand", "dur": 80, "mark": "brand/x.png", "aspect": 5.6, "kicker": "what it is", "markH": 110},
  {"kind": "title", "dur": 56, "kicker": "Sketch", "text": "Diagrams with a *hand-drawn* feel."},
  {"kind": "page", "dur": 132, "src": "caps/scene.png", "w": 1440, "h": 900,
   "keys": [{"f": 0, "cx": 560, "cy": 380, "zoom": 1.5, "ry": -8}, {"f": 90, "cx": 770, "cy": 372, "zoom": 1.85, "ease": "swift"}],
   "layers": [...], "caption": {"text": "...", "at": 8}, "cut": "hard"},
  {"kind": "outro", "dur": 140, "mark": "...", "aspect": 5.6, "tagline": "Sketch it. *Share* it.", "recall": [1, 3]}]}
```

- **`look`.** It can be just `{accent, mode}`. Ground, paper, ink, muted and `accentInk` are derived, with
  `accentInk` walked toward the ink until it reads at 4.5:1 on the paper. Given fields win.
- **Chapter cards** are numbered in order; set `index: false` to leave one unnumbered.
- **`recall`** names the page shots (0-based) the outro wall shows. By default it spreads up to 6 across the film.
- **Timing.** Every frame number counts from the start of its own shot.
- **Keys.**
  - A key puts page point (cx, cy) at the frame centre (`focusY` in a narrated film).
  - `rx` makes the top lean away, `ry` makes the right edge recede, `rz` rolls.
  - A key's `ease` is the curve of the move that arrives at it.

### Acts / layers (page CSS px; frames from the shot's start)

| kind | what it does | fields |
|---|---|---|
| `pop` | an element lands in its own slot (blank before) | `box, at, fill, from: up/left/scale`; `src, srcBox, srcW, srcH` = the element from ANOTHER capture (a state change) |
| `lift` | rises out of an accent under-glow (2D: rise + scale + shadow, the page stays one layer), one sheen, settles back | `box, at, until, z, scale, slot` |
| `focus` | rack focus: the page softens and dims, the element stays sharp | `box, at, until, dim, blur` |
| `ring` | an accent outline draws round an element | `box, at, until` |
| `type` | text typed into a field (placeholder covered by the field's fill) | `box, at, text, cpf, size, fill` |
| `cursor` | a pointer travels and clicks | `path: [{f, x, y, ease}]`, `clicks: [f]` |
| `callout` | dot on the element, leader line, label — kept on the frame: its side and clamp are decided once from the camera at the frame it lands | `x, y` (the point), `lx, ly` (the label), `at, until, kicker, text` |
| `macro` | a 4x capture of ONE element (promo_capture `--hires`) drawn on its own layer, so the camera may push past the page's 2x onto it — the subject sharp, the page around it softening like a background out of the lens's depth | `box, src, scale` (4), `at` |
| `deal` | the page's own cards start as one stack and fly out to their slots one by one along a lifted arc, settling flat | `boxes` (from the layout / `--boxes`), `at, every, dur, from, fill` |
| `write` | a block of the capture's own text appears line by line behind an accent caret (the document writing itself, in its own words) | `box, at, lineH, every, fill` |

### Every field (what the table accepts)

| where | field | meaning |
|---|---|---|
| film | `aspect`, `cut` (carry/flash/hard/through), `look` ({accent, mode} or the full set), `sfx` (a list replacing the plan) | |
| every shot | `kind`, `dur` (frames), `cut` (into this shot) | |
| brand | `mark`, `aspect` (the mark's w/h, printed by `--mark`), `kicker`, `markH` | |
| title | `text` (`*accent*`), `kicker`, `index` (false = unnumbered), `size` | |
| page | `src`, `w`, `h`, `keys`, `layers` (or `acts`), `caption` {text, at, dur}, `contain` (default true), `maxZoom` (2), `radius` | |
| outro | `mark`, `aspect`, `tagline`, `cta`, `stampAt` (default 46), `markH`, `recall` (page-shot indices, from 0) | |
| statement | `text` (`*accent*`), `ground` (paper/accent/ink), `size`, `sub` | one line of type, word by word out of a blur, then still |
| compare | `a`, `b` (regions: {src, w, h, box}), `labelA`, `labelB`, `at`, `sweep` | the same region of two captures, a divider sweeping across |
| montage | `items` (regions), `every` (frames each, 8-18), `full` | the product's own crops in quick succession, each landing and holding |
| any shot | `say` (the voice's line), `throughAt` ({x, y} in frame shares, for a `through` cut) | |
| film (voice) | `narrate`, `voice` (edge voice id), `voice_rate` | |
| key | `f`, `cx`, `cy`, `zoom` (at a 1920-wide reference), `rx`, `ry`, `rz`, `persp`, `ease` | |
| pop | `box, at, fill, radius, dur, from` (up/left/scale), `src, srcBox, srcW, srcH` (from another capture), `cover` | |
| lift | `box, at, until, z, scale, radius, slot, sheen` | |
| focus | `box, at, until, dim, blur, radius` | |
| ring | `box, at, until, radius, pad` | |
| type | `box, at, text, cpf, size, fill, color, weight` | |
| cursor | `path [{f, x, y, ease}]`, `clicks [f]`, `size` | |
| callout / note | `x, y, lx, ly` (note: `x, y` only), `at, until, kicker, text, size` | |
| macro | `box, src, scale` (4), `at`, `radius` | |
| deal | `boxes, at, every, dur, from {x, y}, fill, radius` | |
| write | `box, at, lineH, every, fill` | |

- **Layering.** Page content (pop, lift, focus, type, deal, write) is drawn IN the page. Annotation (callout, note,
  ring, cursor) is drawn on a layer of its own ABOVE the page and its macros, at the close-up's raster, so a callout
  on a 4x close-up is sharp and visible.
- **Report numbering.** The glide report numbers shots as the table does, from 0. `promo_film.py` exits 1 when a
  camera fails (the film is still written).
- **`--sheet`** writes `_sheet.jpg`: one frame per shot at 90 %, labelled with its index.

### Known limits of the capture

- **`--full` captures the DOCUMENT's scroll height.** An app that scrolls an inner container captures only the
  viewport. Scroll that container with an `--eval` step and capture each state.
- **`--mark` keys ONE flat ground colour.** A logo over a pattern or animation keeps it. Isolate the logo first with
  an `--eval` step (lift it onto a plain overlay), then cut.
- **The layout lists every visible box, including ones an overlay hides.** Look at `.boxes.jpg` before using a box.
- **An `--eval` step's return value** is printed and kept in the layout (`eval`). Ask the page a question
  (`JSON.stringify([...document.querySelectorAll('button')].map(b => b.innerText))`) instead of guessing selectors.
- **A `--hires` close-up** is compared with its box in the 2x capture and refused if the page redrew differently at
  4x.

## In a narrated film

`ProductPage` takes `{src, w, h, keys, acts, nominal}`, and `ChapterCard` takes `{text, kicker, index, total}`. They
take their look from the film's design DNA (`lookFromDna`).
- **Timing.** The beat's length stretches the authored timeline, keeping the entrances at their speed. An act whose
  `text` the narration speaks is cued to the word (`acts.<i>`).
- **Captions.** The camera frames the zone above the caption band, and the page fades into the ground under it, so
  the caption sits on the frame's own ground.

## Design the film's own arc (no fixed structure)

There is NO default sequence. "Brand open → chapter card → product shots → chapter card → recall outro" is ONE possible
arc and the one most likely to read as a template: two films built on it are the same film with different pictures.
The check prints a film's structure as a word (`BCPPCPO`, `PSVMSO+vo`) and advises when it repeats a film you made
before.

1. **Find this product's story before choosing a block.** Write down, from the captures and the product's own words:
   - its ONE surprising truth: what someone would repeat;
   - its PROOF: the moment on screen that shows that truth (a number dropping, a document writing itself, a thing done
     in one click);
   - its WHY-NOW tension: what the viewer struggles with without it;
   - its PAYOFF: the frame you would end on.
2. **Shape the arc from those four, not from the block list.**
   - **The hook is the first 2 s.** It can be the proof itself (open on the result, then show how), a tension line, a
     detail macro, or the brand. Whatever it is, it is chosen for this product.
   - **Each block earns its place.**
     - A chapter card belongs only where the argument has chapters.
     - A statement is a beat of type when a line must land alone.
     - A compare is used when the story is before/after.
     - A montage shows breadth (many connectors, many templates) where one shot shows depth.
     - The outro may recall the film, land on a statement, or end on the product itself with the CTA.
   - **Vary the rhythm.** Montage cuts run 0.3–0.8 s. A demo holds 4–8 s while the UI acts. A beat of stillness comes
     before the payoff.
   - **Choose cuts by cause.** Use `through` when one thing opens into the next, `carry` when travelling on,
     `hard` when the beat changes, `flash` rarely.
3. **Voice is a per-film choice.**
   - A film that explains how something works usually speaks: `say` on the shots, and the voice sets their length,
     the subtitles and the ducked bed. One line per shot, ≤ ~19 words (~9 s), the product's own claims only.
   - A mood, brand or one-gesture piece usually does not.
   - `narrate` states it outright.
4. **Examples of arcs. These are not templates; they are here to show the range.**
   - **Proof first.** A macro of the result, a statement of the claim, then the two shots that produce it, then the CTA.
   - **Tension → product.** Two statements of the problem in the user's words, the product arriving with a through-cut,
     its three moves, then a payoff statement.
   - **Before | after.** A compare carries the film, framed by the UI that makes the change.
   - **One continuous take.** No cards at all: the camera travels the product, and through-cuts join its screens.
   - **Type-led.** Statements set the beat and the product appears in short montage bursts between them.
   - Mix them, or find the one this product suggests.

## Craft rules

- **Rests.** Both lockups (if the film has them) rest at least 30 frames. A burst of motion ends with at least 15
  still frames.
- **Every product shot does something**, through its acts. A camera drift alone is a slideshow.
- **Use each signature move once as the hero** (the lift, the tilted arrival, the recall). Shown twice, a move reads
  as a template.
- **Camera.**
  - Use one decisive move per intention, then HOLD. A slow drift is collapsed into a hold, because a creeping page
    shimmers.
  - Never go in and back out within one shot.
  - Tilted views are for arrivals; land straight-on before anything is read.
- **Words.**
  - Use the product's own words (its layout `title`/`description`, its UI) or the film's own statement.
  - No invented numbers. The product's own demo data in its capture is the product as itself.
- **Close-ups.** A hero moment pushes to 3-4x onto a `macro` (capture it with `--hires=<element id or box>`). The
  check refuses a zoom past 2x anywhere a macro does not cover the camera's centre.
- **Moves.** Fast moves carry motion blur by themselves (PageCam, up to 10 px at the peak). There is no click ring: a
  click shows by what it changes, on the same frame.
- **End card.** The lockup lands in the last 5-10 %. `cta` sets the product's real address or command as a button,
  held to the end. Use only an address the captures or docs show.
- **Sound (a generated score under the cues by default; `--bgm=none` for SFX only).**
  - Air through each carried cut, and a whoosh only on real camera travel.
  - A burst of pops is one sound per 3 frames, fading.
  - Keys under typing, a click on a click, a tick when an accent fill or callout lands.
  - UI sounds are RECORDED takes (Kenney Interface Sounds, CC0: click, key, drop, deal, select, glass). The
    noise-built cues (whoosh, swell, impact) are synthesised, and no synthesised tone, bell or chime is used.
  - The close is swell → impact as the lockup lands.
  - The mix is normalised to -15 LUFS and -1.5 dBTP. `--remix` re-mixes over the picture already rendered.

## The loop

1. Run `promo_film.py <dir> --check`. Errors stop it, by name; advisories don't.
2. Run `--stills=` at the settled point (~90 %) of each shot and look at them full-size.
3. Do a full render.
4. Put it beside the reference films on one page (`compare.html`) for the user. The user's eye is the judge.

Tested on:
- WorkBuddy: desktop docs screenshots, cleaned and box-found; 16:9 light.
- Excalidraw: a web app captured live in three states; 16:9 light and 9:16 dark.
- A zh 科普 beat pair over a Wikipedia capture inside the narrated pipeline (TTS, cues, karaoke captions).
