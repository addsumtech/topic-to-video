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

### Recordings — the product in motion

`python3 scripts/promo_record.py <dir> <url> --name=<n> --seconds=6 [--script=steps.json] [--setup="js ;;; js"]`
records the page DOING something, with its own animation: a panel opening, a slider dragged, a result arriving.
- After load and `--setup`, the time the page can see (performance.now, Date, timers, requestAnimationFrame) runs
  on a clock the recorder advances exactly one frame per frame, and every CSS transition / animation and
  `element.animate()` is pinned to it. Transform/opacity animations otherwise run on the compositor, on their own
  clock. The page renders in real time, so the same run gives the same frames at any `--fps`.
- The script: `click`, `hover`, `type` (+`into`, `cps`), `scroll` (eased over `dur`, driven frame by frame), `drag`
  (eased over `dur`), `eval`. Each fires at its `t` in seconds.
- **Async work goes in `--setup`, not the script.** `--setup` runs and is awaited before recording (load an image,
  wait for a worker, open the editor). Network or worker work started by a click during the recording finishes in real
  time, so it lands on whatever frame comes next: not frame-exact. A script `eval` is not awaited.
- Writes `caps/<n>.mp4`, `caps/<n>.png` (the poster: first frame) and `caps/<n>.layout.json` (the first frame's
  elements + `events`: each click / drag / scroll / keystroke run with its frame and place).

A page shot names it with `recording: "caps/<n>.layout.json"`. promo_film takes its poster, video and size from it and
lays a cursor over it that does what the recorded hand did, on the same frames. Headless Chrome draws no pointer.
`videoStart` picks the frame of the recording the shot begins on; `cursor: false` turns the cursor off; a shot with
its own `cursor` act keeps it. The camera, acts and overlays work over a recording as over a capture, and the glide
gate judges it the same way.

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

## Staging — the product as objects (the default)

**Why.** Side by side with the showcase films (2026-11-14, `craft_study/showcase_study`), ours lost on the material,
not the polish. They film ONE component at a time — a card, a field, a result — large (60–80 % of the frame), lit,
in a space with depth, and everything in it keeps moving. We filmed the whole web page edge to edge: its type 1–2 %
of the frame, sidebars and ads included, no world of the film's own, a still screenshot between acts. The camera
glided and the sound was placed, and it still read as a screen recording.

So a product film is made mostly of **objects**:
- **Capture components, not pages.** `promo_capture.py ... --parts="panel=css:.settings;result=text:862 kB"` saves
  each part on its own at 4x (`caps/<name>.part.<part>.png`), with its CSS size, corner radius and fill
  (`layout.json` → `parts`). Mark an element during `--eval` (`e.dataset.ttv='panel'`) and name it
  `css:[data-ttv=panel]` when its classes are hashed or its size changes between states.
- **Write the demo state.** `--eval` steps can use `__ttv.fill(selector, text)` (an input, a textarea, an editor:
  typed the way a user's typing is, React sees it) and `__ttv.text(selector, text)`. The film writes its own demo
  content — a short, legible example that tells the story — instead of filming whatever the page shows.
- **`object` shot.** One hero component (and optional ones behind or in front: `z`, `blur` for depth) arriving in 3D
  (`from`: tilt, rise, fade) and then HOLDING, in a `world`: `glow` (near-black, the accent as light, faint outlines
  receding), `paper` (the film's paper and a spotlight) or `pastel` (soft ground, three blooms of the accent's
  neighbours). A `label` beside it is the feature-section device: `{index: "02", kicker: "CRT shader", text:
  "Scanlines, glow,\n*and that curve.*", sub}` — small mono `02 / CRT SHADER`, a claim of one or two lines at
  showcase size (~6 % of the frame height), its accent span inked. Use the same label layout for every feature of
  the film: it is the film's system.
- **Live objects.** An item can be a RECORDING cropped to the component: `{video, vw, vh, crop: {x, y, w, h},
  videoStart, vscale}`. Record it with `promo_record.py --scale=3` when it will be staged large. Acts (count, ring,
  type, pop, callout) sit on an item in its own CSS px, so a figure counts up and a field types, on the object.
- **Show the claim.** A label states a feature; the hero card must then DO it, or the shot is a caption on a
  screenshot. Act the claim out on the card in its own CSS px, timed after the arrival: `focus` the part the claim
  names and rack it along (an explanation read group by group), `ring` stepping row by row (every match, every
  group; no `lift` on a staged card: at 1.06 it covered its neighbours, and even at `z` 30 its settle crept under a
  pixel a frame, which the glide gate failed at 11 % shimmer), `count` the
  figure, `type` the input — or crop a recording of it working. Measure the row bands off the part's own pixels.
  `check` advises on a labelled object shot whose hero has no acts and no recording.
- **Crop what the feature is.** A tile or item that is mostly its own ground reads as an empty card (the regex101
  run's substitution tile was the empty bottom of the test-string input: 1.6 % ink). `check` advises on a part
  under 4 % ink (`ink_density`); real components measured 7.5–60 %.
- **`wall` shot.** Many components on a plane in perspective (`plane`: floor or wall), appearing in a quick cascade,
  with the camera gliding across in one move (`from` → `to`, plane px); the far edge falls into the world; a large
  `label` sits in a corner on a scrim. Use it for breadth (every codec, every template), with components or crops
  as tiles, never shrunken full pages.
- **The staged outro.** An `outro` with a `world` gathers the film's own components (the still parts of its object
  and wall shots, up to 6) in depth round the mark: each arrives from further away to its place in a loose ring,
  softer the deeper it sits, then steps back and dims as the mark lands in a band of light (glow) or a spotlight
  (paper), with the tagline and CTA under it. Give it a `stampAt` of ~30 so the gathering is seen before the mark.
  The round-4 outro was a small mark on an empty ground. The parts are chosen at render (`resolve_outro_objects`:
  film order, each once, near-blank parts left out; an authored `objects` list wins). On a light world they keep
  their ink and step back by depth only, with a contact shadow and a hairline edge: dimming on white faded them to
  ghosts. Size the mark (`markH`) so it outranks the tagline.
- **Layers.** A frame with one object on a void reads empty. Put one or two of the film's other components behind
  the hero (`z` -300..-450, `blur` 3-4, `from: fade`) — depth, and the product's world around its subject.
- **A full-page shot is the exception**: at most one, to establish where we are. Everything else is a component.

Sharpness and stillness hold as for pages. `check` refuses a part shown larger than its pixels, an object is laid
out once at its size at rest and arrives from further away (scale ≤ 1), a landed object holds while its content
moves, and grounds do not crawl. The glide gate judges object and wall shots too.

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

Every `box` is a dict `{"x": .., "y": .., "w": .., "h": ..}` in the capture's CSS px (as in `layout.json`), never a list;
`check` names a list. Shots are numbered from 0 everywhere (check, glide report, sheet).

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
| `count` | the page's own figure counts up to its value in place (over its own digits, on its field's fill) — a number arriving, not a number shown | `box, to, from, decimals, prefix, suffix, at, dur` (42), `fill, color, size, weight, align, font` |

### Every field (what the table accepts)

| where | field | meaning |
|---|---|---|
| film | `aspect`, `cut` (carry/flash/hard/through/morph), `look` ({accent, mode} or the full set), `sfx` (a list replacing the plan) | |
| every shot | `kind`, `dur` (frames), `cut` (into this shot) | |
| brand | `mark`, `aspect` (the mark's w/h, printed by `--mark`), `kicker`, `markH` | |
| title | `text` (`*accent*`), `kicker`, `index` (false = unnumbered), `size` | |
| page | `src`, `w`, `h`, `keys`, `layers` (or `acts`), `caption` {text, at, dur, pos}, `contain` (default true), `maxZoom` (2), `radius` | the caption strip sits in a corner: `pos` bl (default), br, tl, tr; left out, it moves off type by itself |
| page (recording) | `recording` (a promo_record layout; sets src/video/w/h), `videoStart` (frame), `cursor` (false = none) | the recording plays under the camera |
| outro | `mark`, `aspect`, `tagline`, `cta`, `stampAt` (default 46), `markH`, `recall` (page-shot indices, from 0), `world` (staged: the film's components gather round the mark) | |
| statement | `text` (`*accent*`), `ground` (paper/accent/ink), `size`, `sub` | one line of type, word by word out of a blur, then still |
| compare | `a`, `b` (regions: {src, w, h, box}), `labelA`, `labelB`, `at`, `sweep` | the same region of two captures, a divider sweeping across |
| montage | `items` (regions), `every` (frames each, 8-18), `full` | the product's own crops in quick succession, each landing and holding |
| object | `world` (glow/paper/pastel), `items` [{`src`, `w`, `h`, `radius`, `bg`, `x`, `y` (centre, frame shares), `width` (share of the frame width), `rx`, `ry`, `rz`, `z`, `blur`, `at`, `from` (tilt/rise/fade/none), `acts`; or `video`, `vw`, `vh`, `crop`, `videoStart`, `vscale`}], `label` {`index`, `kicker`, `text` (`\n` between lines, `*accent*`), `sub`, `side` (left/right), `at`} | components as objects in the film's world, a feature label beside them |
| wall | `world`, `tiles` [{`src`, `w`, `h`, `radius`, `bg`, `acts`; or `video`, `crop`, ...}], `cols` (4), `tile` (plane px, 560), `gap`, `plane` (floor/wall), `from`/`to` ({x, y} plane px), `label` {`text`, `sub`, `at`} | many components on a plane in perspective, the camera gliding across |
| any shot | `say` (the voice's line), `throughAt` ({x, y} in frame shares, for a `through` cut), `morphFrom` ({x, y, w, h} in frame shares, for a `morph` cut) | |
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
| count | `box, to` (a number: the page's own), `from` (0), `decimals, prefix, suffix, at, dur, fill, color, size, weight, align, font` | |

- **Layering.** Page content (pop, lift, focus, type, deal, write) is drawn IN the page. Annotation (callout, note,
  ring, cursor, count) is drawn on a layer of its own ABOVE the page and its macros, at the close-up's raster, so a callout
  on a 4x close-up is sharp and visible.
- **Report numbering.** The glide report numbers shots as the table does, from 0. `promo_film.py` exits 1 when a
  camera fails (the film is still written).
- **`--sheet`** writes `_sheet.jpg`: one frame per shot at 90 %, labelled with its index.

### Known limits of the capture

- **Third-party content is not the product.** Ads, cookie banners, chat widgets, release toasts and geo-targeted
  promos are removed with an `--eval` step before the capture. Anchor on their TEXT when ids and classes are hashed:
  `[...document.querySelectorAll('a,span')].filter(e => /ads via|sponsored/i.test(e.innerText)).forEach(e =>
  e.closest('section,aside,div[class]')?.remove())`. Dismiss toasts with their own button
  (`document.querySelector('button[aria-label=Dismiss]')?.click()`). A broad selector (`[class*=ad]`) also matches
  `header`. An ad network rotates between loads, so check every capture, not only the first.
- **Hover and focus are cleared** after the `--eval` steps (the pointer leaves the page, focus is dropped), so a
  scripted click leaves no tooltip or focus ring in the picture.
- **`--hires` items** are `text:<words>` (the smallest element holding them), `css:<selector>`, a box `x,y,w,h`, or an
  element id. Ids are numbered per capture and SHIFT between states, so prefer `text:`. Each item prints what it
  resolved to.
- **The layout lists the acting elements** (controls, fields, cards, media, headings). A container the story needs
  that is not one (a code editor's lines, an export frame) is added with `--select="#export-container,.CodeMirror-code"`.
- **`.boxes.jpg` draws over the page.** Read text (a field's value) off the PNG, not the overlay.

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
The check prints a film's structure as a word (`BCPPCPO`, `PSVMSO+vo`; every render records it in
`~/.topic-to-video/promo_skeletons.json`, outside the film folder) and advises when it repeats a film you made
before.

1. **Find this product's story before choosing a block.** Write down, from the captures and the product's own words:
   - its ONE surprising truth: what someone would repeat;
   - its PROOF: the moment on screen that shows that truth (a number dropping, a document writing itself, a thing done
     in one click);
   - its WHY-NOW tension: what the viewer struggles with without it;
   - its PAYOFF: the frame you would end on.
2. **Shape the arc from those four, not from the block list.** Film the product as OBJECTS (§ Staging): each feature
   is an `object` shot of its component with a feature label, breadth is a `wall`, and a full page appears once at
   most.
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
   - **Choose cuts by cause.** Use `morph` when a thing on screen BECOMES the next shot (a thumbnail opening into
     its editor: `morphFrom` is that thing's box on the frame; the next shot starts scaled into it and grows to the
     frame on an in-out curve, over the last 16 frames). Use `through` when one thing opens into the next, `carry` when travelling on,
     `hard` when the beat changes, `flash` rarely.
3. **Voice is a per-film choice.** (edge-tts needs network. Offline, each line is voiced by macOS `say` in the
   film's `language`, and the run says so: no word timings, so subtitles are timed by length.)
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
  - Keys under typing, a click on a click, a tick when an accent fill or callout lands. A RECORDING is heard the
    same way, from its own events: keys under its typing, a press and a soft release on a drag, and air on a long
    scroll. Its clicks sound once, whether or not a cursor is drawn.
  - UI sounds are RECORDED takes (Kenney Interface Sounds, CC0: click, key, drop, deal, select, glass). The
    noise-built cues (whoosh, swell, impact) are synthesised, and no synthesised tone, bell or chime is used.
  - The close is swell → impact as the lockup lands.
  - **Stereo, placed by the picture** (scripts/stereo.py). A cue is heard where its cause is on the frame: the
    camera's position at that frame turns the act's page x into a pan, at most 70 % to a side. A click on the left
    is heard left, and dealt cards land left to right in sound too. A whoosh on camera travel sweeps the way the PAGE
    moves (opposite to the camera). A push, the outro's swell and impact, and the brand's landing are wide (two
    decorrelated short rooms, no Haas delay, so mono stays intact). The score's bed is wide and its pulse and the
    voice are centred. `sfx` entries take an optional `pan` (a number, `[p0, p1]`, `"wide"`). The plan with its
    places is written to `promo_sfx.json`.
  - Every mix prints its field read back from the file: L/R correlation, mono fold-down loss and balance. It refuses
    a mix that is out of phase (corr < 0.2), lopsided (> 2 dB) or loses > 3 dB in mono. Measured: a music-led film
    read corr 0.89 with a 0.2 dB fold-down loss, a voice-led one 0.98 with 0.1 dB.
  - The mix is normalised toward -15 LUFS (single-pass: measured -14.4 to -15.7 on delivered films) under a -1.5 dBTP
    ceiling. `--remix` re-mixes over the picture already rendered.

## The loop — from a product to a delivered film, with no hand-holding

Run it start to finish. Stop only for a decision that is the user's (which product state to show when the product
needs a login; a paid asset), never to ask "shall I continue". **On a run with no one to ask**, show only what anyone
can open for free, and name in the delivery note any headline feature left out because it is behind a login or a
paywall.

1. **Folder.** `mkdir -p <film_dir>/caps`. Everything below writes into it.
2. **Explore before capturing.** Capture the landing state (`promo_capture.py <dir> <url> --name=home`), then open
   `caps/home.boxes.jpg` and `caps/home.layout.json` and read what the product IS from its own title, description
   and UI. Ask the page with `--eval` (`JSON.stringify([...document.querySelectorAll('button,a')].map(e =>
   e.innerText).filter(Boolean))`) rather than guessing selectors. Capture each STATE the story needs (an opened
   editor, a result, a settings panel) as its own capture, reaching it with `--eval` steps, and write the film's demo
   content into it (`__ttv.fill`). Take the COMPONENTS each feature will be staged with as `--parts` (§ Staging), and a
   `--mark` cut of the logo from the product's own page.
3. **Record the proof, if it moves.** (any `--fps`; the recording keeps its rate and the film times it in film
   frames) When the product's proof is something HAPPENING (a slider dragged, a result
   arriving, a panel opening), record it: `promo_record.py <dir> <url> --name=proof --seconds=4-6 --setup="<reach
   the state, async OK>" --script=steps.json` with click / drag / type / scroll steps at their seconds. Look at a
   frame grid of the mp4 before using it. If a click starts network or worker work, put it in `--setup`.
4. **Write the four** (§ Design the film's own arc): the surprising truth, its proof, the why-now tension and the
   payoff, each in the product's own words with the capture it comes from. Then choose the arc and voice from them,
   and write the structure down as a word before building (`PSVSPPPMSO`).
5. **Write the table with a script, not by hand.** Write `compose.py` in the film folder. It reads each
   `*.layout.json` and picks boxes BY TEXT or role (`next(e for e in L['elements'] if 'Compress' in e['text'])`), so
   no box is measured off a picture. It writes `promo.json`. A box guessed off a grid is an element landing beside
   its slot. Make camera keys with `promo_film.key(f, cx, cy, zoom, L["w"], L["h"], aspect)` (`sys.path.insert` the
   skill's `scripts/`): it aims at the element and keeps the view on the page. **Length and aspect** come from the
   interview's ④ (`aspect` in the table; the shots' `dur` add up to the length). Without one, a launch runs 25-40 s
   at 16:9, and a 9:16 film uses portrait captures (`--width=430 --height=932`).
6. **Check.** `promo_film.py <dir> --check`: fix every ERROR. Read every ADVISORY; a repeat-skeleton advisory means
   the arc is a template, so redesign it.
7. **Stills.** `--check` already advises when a caption or the voice's subtitle lands on the page's OWN text at
   that frame (read from the capture's layout, placed by the camera). Lift the text out of the bottom band with the
   key's `cy`, or move the caption. Measured: it named all four such frames on the narrated Squoosh film, the hero
   "↓69%" under a subtitle among them, and none on a film without them. `--stills=` at ~90 % of each shot, plus the frames where acts land and cuts happen. Look at them
   full-size: every word legible, nothing landing beside its slot, no empty frame, the hook readable in its first
   2 s. Fix and repeat. This is the cheap loop; the full render is not.
8. **Render.** `promo_film.py <dir> --sheet` (tracked in the background). It must end with the glide gate OK and the
   stereo line printed. Then measure loudness: `ffmpeg -i out.mp4 -af ebur128=peak=true -f null -` (I ≈ -15 LUFS).
9. **Deliver.** Copy the film and `_sheet.jpg` to `~/Desktop/<product>_promo/`, with a one-page `index.html` that
   plays it and names what to look at. When there is a previous version, put it beside the new one, with a side-by-side
   still sheet. The user's eye is the judge; do not run critic loops in its place.

Tested on:
- WorkBuddy: desktop docs screenshots, cleaned and box-found; 16:9 light.
- Excalidraw: a web app captured live in three states; 16:9 light and 9:16 dark.
- A zh 科普 beat pair over a Wikipedia capture inside the narrated pipeline (TTS, cues, karaoke captions).
