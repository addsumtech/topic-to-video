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

## In a narrated film

`ProductPage` takes `{src, w, h, keys, acts, nominal}`, and `ChapterCard` takes `{text, kicker, index, total}`. They
take their look from the film's design DNA (`lookFromDna`).
- **Timing.** The beat's length stretches the authored timeline, keeping the entrances at their speed. An act whose
  `text` the narration speaks is cued to the word (`acts.<i>`).
- **Captions.** The camera frames the zone above the caption band, and the page fades into the ground under it, so
  the caption sits on the frame's own ground.

## Craft rules

- **Structure.**
  - The timeline runs brand open, then per feature a chapter card and 1–3 product shots, then the recall outro.
  - Both lockups rest at least 30 frames.
  - A burst of motion ends with at least 15 still frames.
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
- **Sound (SFX-only unless `--bgm`).**
  - Air through each carried cut, and a whoosh only on real camera travel.
  - A burst of pops is one sound per 3 frames, fading.
  - Keys under typing, a click on a click, a tick when an accent fill or callout lands.
  - The close is swell → bell → chime.

## The loop

1. Run `promo_film.py <dir> --check`. Errors stop it, by name; advisories don't.
2. Run `--stills=` at the settled point (~90 %) of each shot and look at them full-size.
3. Do a full render.
4. Put it beside the reference films on one page (`compare.html`) for the user. The user's eye is the judge.

Tested on:
- WorkBuddy: desktop docs screenshots, cleaned and box-found; 16:9 light.
- Excalidraw: a web app captured live in three states; 16:9 light and 9:16 dark.
- A zh 科普 beat pair over a Wikipedia capture inside the narrated pipeline (TTS, cues, karaoke captions).
