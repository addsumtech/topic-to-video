# Director toolbox — the commands and kit behind SKILL.md's director path

SKILL.md says WHAT to do at each step; this file says HOW, with the exact commands. Everything here works in a
director-path film folder (no storyboard) and was verified there on 2026-11-17. None of it is required: it is the
vocabulary SKILL.md's "Design is judgement" refers to. The classic version's other tools are in
`pipeline-scripts.md` (any that takes a film folder or an mp4 is usable here too).

## Material (step 2)
- **A deck, PDF or image folder as source material:** `python3 scripts/ingest.py <deck> <film_dir>/deck` renders every
  page to `deck/frames/` and pulls its text and speaker notes into `deck/storyboard.json` (reading material only).
  Its figures and screenshots can appear in the film.
- **Real geography (a place, a route, a city growing):** `python3 scripts/geo.py place "Shenzhen"` (lat, lon, box);
  `geo.py ne <film_dir> admin_1_states_provinces --scale 10m --bbox W,S,E,N` (Natural Earth, public domain: countries,
  provinces, coastline, rivers_lake_centerlines, populated_places; a 10m layer downloads once per machine, minutes);
  `geo.py osm <film_dir> coast --what coast|roads|water|rail|admin|parks --bbox W,S,E,N` (OpenStreetMap through
  Overpass, several servers with backoff, ~1 min; roads within 0.6 degrees a side). Each writes `geo/<name>.geojson`
  and its record. Draw with `assets/html/geo.js` (copy it beside the page): `P = Geo.fit([W,S,E,N], 1920, 1080)`,
  `Geo.svg([{data, cls}], P)` (Web Mercator SVG paths, sharp under any zoom, `pathLength=1` so a line draws on with
  stroke-dashoffset), `P.xy([lon, lat])` to place a marker or a label, `Geo.inside([lon, lat], land)` before anything
  stands on a place (a land, district or coast-closed layer; null = water or outside it). The credits (© OpenStreetMap contributors,
  ODbL; Natural Earth) go into `<stem>.credits.txt` through film_deliver.
- **A real product page:** `python3 scripts/promo_capture.py <film_dir> <url> --name=<n>` and
  `python3 scripts/capture_page.py <page.html|url> --name <n>` capture at 2x.
- **A real, licensed image of a named subject:** `python3 scripts/imagefetch.py "<query>" img/<name>.jpg` (Wikimedia
  Commons, or `--source nasa`; the record beside it, `<file>.json`, carries the credit). For a real person, place or
  event, look first: `--candidates 12` lists the relevant ones and draws them on `img/<name>.candidates.jpg`; then
  `--pick K`. A crop or treatment of a fetched picture is declared in `<film_dir>/images_ok.json`
  (`{"img/x.png": {"from": "design/refs/x.jpg"}}`; `{"own": why}` for a picture the film computed, `{"generated":
  why}` for atmosphere); `film_qc` ("images") holds every picture the page names to a record, and `film_deliver`
  writes the credits beside the film.

## Writing (step 3)
- `agents/scriptwriter.md` can draft the narration from the plan; one round of `agents/critic-narrative.md` on the draft
  catches what the ear misses. `references/narration-writing.md`, `references/anti-ai-voice.md`.
- `python3 scripts/pace.py --budget <seconds> --lang <lang>`: how much narration a span holds.

## Voice (step 4)
`python3 scripts/say.py --lines script.txt --out-dir <film_dir>/voice --voice edge:zh-CN-YunxiNeural [--speed 1.08]
[--lexicon lexicon.json]` (one line: `say.py "…" --out l01.mp3`). It runs the skill's voice layer (`tts.speak`):
- per-word timings in `<clip>.words.json`, in the WRITTEN words (the caption's spelling);
- a pronunciation lexicon `{written: spoken}` applied for the voice only (多音字, brand names, a misread term);
- initialisms spelled for a Chinese voice (AI as A-I);
- engines: `edge:<id>` (free), `minimax:<id>` / `openai:<id>` only with the user's own key, `say:<name>` offline;
- a transient edge failure retried; any other failure stops with its reason (never a silent different voice).

**The audition and the voice pick (checkpoint 1).** `python3 scripts/script_audition.py <film_dir> [--voice <spec>]
[--allow-paid]` reads `script.json` (hook, the payoff sequence's first line, the close = the last sequence's first
line, a middle pair) and speaks them in the script's voice or `--voice` into `audition.mp3` (a paid voice only with
`--allow-paid`, i.e. after the user picked it); `python3 scripts/voice_qa.py <film_dir>` marks where it sounds written
(advisory). MiniMax candidates: `MINIMAX_API_KEY=… python3 scripts/voice_sample.py <film_dir> --gender female|male
--lang <code> --text "<the hook line>"` -> `voice_samples/` (the key out of band, never in chat or a file). A paid or
`say` voice reports no word timings: `say.py` aligns them from the free edge voice speaking the same words
(`scripts/word_align.py`; measured median 0-18 ms, p90 <= 60 ms, worst ~0.2 s at a line's last word), and stops with
the reason if it cannot (no edge-tts): the timeline is never guessed.

Voices: zh `zh-CN-YunxiNeural` / `zh-CN-XiaoxiaoNeural`; en `en-US-AndrewMultilingualNeural` /
`en-US-AvaMultilingualNeural` (`references/tts-voices.md`). A misreading is fixed in the lexicon, never in the caption.
Editing the clips: trim leading/trailing silence, cap pauses inside a line (~0.25 s), a longer breath (0.4-0.6 s) at
each sequence seam; no clipping, even loudness across lines.

## Look (step 5) and the animatic (step 5b)
- The designer's brief includes the user's taught taste: `python3 scripts/taste_ledger.py brief --stage design`.
- `python3 scripts/animatic.py <film_dir> [--page film.html] [--width 1280]` -> `design/animatic.mp4`: each shot's
  board (`design/boards/<shot>.png`, else the hero keyframes in hero order, else — with `--page` — the page itself at
  20/50/85 % of the shot, else a grey card from the treatment marked BOARD MISSING), the shot id and line in a strip
  under the picture, the voice on the timeline. Seconds to make; the user approves it before the full build.
- `references/video-looks.md` (11 looks, a vocabulary) and `references/visual-styles.md` (palette and type
  sub-registers, with the vetoes).
- `python3 scripts/theme.py <film_dir> --style <key>` writes `theme.css`: the style's contrast-safe palette and type as
  CSS variables; `assets/html/base.css` is a typeset base that reads them.

## Building (step 6)
**Pages.** One `film.html`, every frame a pure function of time (`window.seek(t)`), captured with headless Chrome.
Icons: `references/icons.md` (one inline-SVG line family, Lucide). Captions: `python3 scripts/caption_words.py "…"`
shows where a CJK caption may break; placement and line rules (on the frame's own ground, no strip, nothing else in
the band) are `references/captions.md`. On a director-path page whose picture fills and moves across the frame, the
caption's place is measured: render once with captions hidden (the page's own switch), write `[[t0, t1, text], ...]`,
then `python3 scripts/caption_spots.py <film_dir> --caps caps.json` gives each caption a spot on uniform ground for
its whole time and its ink (`"light"` ground → dark text); the page draws each at its spot (the Numbers film's
`tools/build_page.py` is a worked example).

**The 3D stage** — `assets/html/stage3d.js`, one classic script (three.js 0.169
bundled from `remotion/node_modules` by `scripts/build_stage3d.sh`), so a film page loads it with a plain `<script>`:

    const st = Stage3D.create({canvas, background: '#06070a', fog: {near: 9, far: 22}, dof: {aperture: 0.0016}});
    st.studio();                                   // key + rim + fill + a room environment for reflections
    st.floor({});                                  // dark, slightly glossy: it reflects and grounds the screens
    const hero = st.panel('screens/dash.png', {width: 2.6, x: 2.5, y: 1.4, rotY: -0.55});   // a physical screen
    st.panel('screens/chat.png', {width: 1.8, x: 0.9, y: 1.15, z: -2.2, dim: 0.5});        // a background one
    st.spot(hero, {from: [0.5, 8, 6]});            // the one placed light
    await st.ready();
    window.seek = (t) => st.render({pos: [...], look: [...], fov: 30, focus: 7});           // pure function of t

Screens EMIT their picture (unlit, exact colours, rounded) inside a lit slab body; `dim` darkens a background one.
Use CLEAN screens (crop out any documentation annotations first). `create({pixelRatio: 2})` supersamples: small screen
text and characters' edges stay crisp in the capture (the default 1 read as "low resolution", Grok Bot 2026-11-18).
`dof` blurs with a few taps: anything far from the focus distance turns into offset ghost copies (icons, text), so
keep it off when near objects carry marks or words, or set `focus` on them. Two objects never end in the same place
(coplanar cards flicker through each other): send what has done its job out of frame and hide it.

**Characters and marks as soft 3D bodies**: `st.inflate('bot.png', {width: 0.9, x, z, front: 0.42, back: 0.3})` turns a
flat character or mark on a TRANSPARENT background into a glossy inflated body standing on its own y = 0, its artwork
redrawn crisp on the face (its own colours), its main colour on the back. Cut the shape out of a screenshot with
`python3 scripts/cutout.py <shot.png> <bot.png> --box x,y,w,h` (flood fill from the edge, so white eyes inside it
stay; refuses a shape the box or a phone frame cuts off). inflate refuses what it would draw wrong: a shape touching
the image edge, transparent holes inside it (a background removed by colour), a shape not star-shaped about its
centre (a crescent, a ring, several parts). **Cast from one official image**: take every character from the same
screenshot that pairs it with its role (a Bot list, a roster) and keep that image's pairs; never pair a role with a
character by colour from another picture (Grok Bot 2026-11-18: round Bots matched by colour, where the app's own
list shows a hexagon, a bean, a triangle). A character is in one place at a time: one that leaves its group is gone
from it. Act with
`const h = Stage3D.hop(u, {height: 0.4}); g.userData.body.position.y = h.y; g.userData.body.scale.set(h.sx, h.sy, h.sx)`
(anticipation, arc, a volume-keeping landing squash). Whatever a character carries rides on it:
`Stage3D.carry(card, bot, {h: cardHeight})` every frame after the pose puts it on the top of the body as posed now
(it rises with the hop, dips with the squash); never a fixed height, which a hopping head sinks into. A face with 1-3
compact marks gets them as separate raised EYES (`g.userData.eyes`; `eyes: false` keeps them painted; a face with
more marks, a logo, keeps them painted and says why in `g.userData.eyeReason`): `Stage3D.blink(g, 0..1)` shuts them
like a lid, `Stage3D.look(g, dx, dy)` moves both together, kept on the face — a character blinks now and then and
looks at what it is about to act on. `create({pixelRatio: 2})` for every stage that carries characters or words. Brand colours stay true with `create({toneMapping: 'neutral'})`. Type stays in the page's DOM over the canvas
(crisp). Capture with Chrome's `--allow-file-access-from-files` (WebGL refuses `file://` images otherwise) or serve the
folder over http. Measured on the first keyframes (2026-11-17): a hand-tuned frame went from "screens floating in a
void" to cinematic only after three render-and-judge rounds — composition is the designer's work, not the kit's.

**Light, material, depth.** In Remotion: `runtime/material`, the lit stage, the craft kit's `surface`, `slide.optic`
(`references/building-blocks.md`). A lit film keeps one light direction and one material language throughout.

**Real 3D (Blender)** for what 3D physicality IS the content of (a real object, a material, optics, physics, a device).
Write a scene script in the plate API (`build(k)` / `pose(k, t)`, `references/blender-plates.md` "The scene-script
API"), using the kit: `studio.world` (the HDRI), `studio.softboxes(<position>)`, `studio.tune_cycles`, `stage.place`,
`materials`. Look at one frame first, then render the clip:

    python3 scripts/blender_clip.py <film_dir> scene.py --seconds S --still F            # one frame to look at
    python3 scripts/blender_clip.py <film_dir> scene.py --seconds S --size 960x540 --samples 8 --name N_draft   # the move, fast
    python3 scripts/blender_clip.py <film_dir> scene.py --seconds S --engine cycles      # alpha PNGs + preview mp4, once

Output: `<film_dir>/clips/<name>/rgba/NNNN.png` (alpha, or opaque with `--env`) and `<name>.mp4`. Glass, gems, water
and metal show only what they refract or mirror: render them in Cycles with the kit's HDRI and soft boxes. In EEVEE
with no world a diamond came out flat grey; with them, a believable stone at 10 s a frame (640x360).

**Devices.** The product's real screen on a lit MacBook, the camera pushing in to what the voice names:
`python3 scripts/blender_clip.py <film_dir> blender/kit/scenes/laptop_screen.py --seconds S --engine cycles --screen
<folder of screen pictures, one per frame> [--params '{"focus": [0.3, 0.2]}']` (the params are in the scene file's
header; about 25 s a 1920x1080 frame).

**The library's shots and objects as parts.** The catalogue is `remotion/LIBRARY.md` (what each of the 227 shots is
and when to use it); the objects (devices, the Earth, satellites, clocks…) are in `references/building-blocks.md`.
Write a film's own shot or object in its workshop and let it wrap any library shot (`@shots/<Name>`, e.g.
`import {ChartRace} from '@shots/ChartRace'`) or runtime module (`@runtime/<module>`):

    python3 scripts/workshop.py <film_dir> new-shot <Name> --means "<what the viewer must see>"
    python3 scripts/workshop.py <film_dir> new-object <Name> --means "<what the viewer must see>"
    python3 scripts/workshop.py <film_dir> check
    python3 scripts/workshop.py <film_dir> still <Name>
    python3 scripts/workshop.py <film_dir> clip <Name> --props p.json --dna film_dna.json    # -> clips/<Name>.mp4
    python3 scripts/workshop.py <film_dir> fidelity <Name>    # a built object against its references (references/object-audit.md)

- **In the film's look:** the DNA file gives the WHOLE palette (`bg`, `fg`, `dim`, `accent`, `accent2`, `onAccent`,
  `surface`, `surfaceBorder`, `line`, and the fonts `fontDisplay`, `fontBody`, `fontMono`); a partial one is filled
  from a DARK default (`runtime/dna.tsx` NEUTRAL_DNA).
- **On a light look, LOOK at the part before using it:** render one frame in the film's DNA (`workshop.py <film_dir>
  clip <Name> --props p.json --dna film_dna.json --frames 90-90`) and read every word on it. Some library shots were
  built for dark grounds and hard-code light ink; `python3 scripts/ink_contrast_qa.py --only <Name>` catches a shot
  whose ink is mostly near-white, but NOT a few labels beside large coloured shapes: ChartRace passed it while its
  labels vanished on paper (fixed 2026-11-17: it now takes the film's `fg`/`dim`). A part whose words do not read is
  restyled in the workshop or swapped.
- **Placing a clip:** extract it to PNGs and let the page draw frame N at its time, so the page stays a pure function
  of time. Rendering: ChartRace with real rows took 45 s for 4 s.

**Generated imagery** (atmosphere only, never a fact): `python3 scripts/imagegen.py --prompt "…" --out bg.png` draws
through the Codex subscription with the no-text/no-invented-facts tail added; `--key` (the paid API) only after the
user agreed to pay.

**Accents.** `assets/html/accents.js`, each a pure function of (t, seed):
`burst` (confetti), `ring` (an expanding shockwave), `rays` (short radiating lines), `sparkle`, `pop` (arrival, no
overshoot), `drawOn` (a stroke drawing itself), `countUp`, and `drawParticles` for a canvas. A celebration is `burst` +
`ring` + `rays` started on the same frame, drawn BEHIND the element it celebrates. Tuned on a rendered sheet: at the
first defaults the confetti stayed a puff on the card; drawn over the card it crossed the text. Accent lines last 4-10
frames. Never `Math.random` in a film page; never grow past full size and shrink back (rewind_qa reads it as the
picture going back, as on a Memphis film's label pops).

## Devices, app screens, cards, marks (step 6; `assets/html/stage3d/devices.js`, `screens.js`)
    const ph = st.phone(canvas, {width: 0.71, finish: 'black'});      // canvas at 1179x2556's aspect (official phone screenshots fit)
    const tb = st.tablet(canvas, {width: 2.16});                      // 2064x2752 (the App Store's iPad Pro 13 screenshots)
    const lp = st.laptop(canvas, {width: 3.13, open: 1.9});           // 3024x1964; lp.userData.setLid(a), 0 = shut
    ph.userData.refresh();                                            // after drawing on the canvas, every frame it changes
- A film's own `lib/stage3d.js` is a COPY: refresh it from `assets/html/stage3d.js` when you revise a film made with an
  older kit (an old copy has no devices, cards or screens).
- Real proportions in decimetres by default (a desk scene); `finish` natural | black | white | blue (phone),
  silver | space-black (laptop); `off: true` = dark glass; `island: false` when the picture already has the Dynamic
  Island; `glare` the glass's reflectivity (0.06; the glass takes no light highlights: a lit glass washed the display).
- A picture of another aspect is REFUSED (`fit: 'contain'` letterboxes it whole). The phone shows the phone layout.
- `await Stage3D.screen(canvas, markup, {size: [390, 844], css, fonts: {'Inter': 'fonts/Inter.woff2'}, name})`: the
  markup laid out by the browser at `size` (CSS px: a phone's points, a 14" laptop's 1512x982) and drawn at the
  canvas's pixels; images and fonts inlined; same markup = cached. `window.seek` may be async and await it.
  `stage_contacts_qa` lints every shown screen (SCREEN-OVERLAP, SCREEN-CLIPPED, SCREEN-OFF-SCREEN; `data-overlap-ok`
  on a deliberate badge; `data-clip-ok` on a deliberate crop; SCREEN-JITTER: a line that keeps its words and jumps
  back and forth between frames; SCREEN-IMITATED-TERMINAL: a terminal program drawn by hand) and `film_copy_qa` reads
  its words. The page's own words over the stage are followed too (PAGE-JITTER; `data-motion-ok` on a deliberate
  wobble).
- A real reference for every app screen, in the film folder: the official screenshot (measure its sizes, colours and
  type off it) or, for a web page anyone can open, a headless capture of it. The demo world inside is `demo` content.
- A terminal program (Claude Code, Codex, a shell) is captured, not imitated:
      python3 scripts/term_capture.py --out work/cc.json --cols 84 --rows 14 --cwd <a demo folder> --wait 6 \
        --type "the request" --type-at 5 --type-every 0.08 --replace "<path it shows>=>~/job-search" -- claude
  one frame per typed character (Enter is never pressed); answer a first-run question with `--keys '[[5, "3"]]'` (a
  menu number is safer than arrow keys, whose timing can land on another option); it refuses a capture that still
  shows your home path or login name. Crop a frame's rows to what the shot needs (an account's own notices, a tip);
  never add text it did not show. Draw it: `const t = Stage3D.terminal(frame, {px: 16, title: 'job-search — claude —
  84×14'})` -> `{html, css, size}` for `Stage3D.screen` (a canvas of `size`'s aspect); typing = the frames in turn.
- `Stage3D.caret(on, {color, block})` in any screen markup: a caret that cannot move its line (zero-height anchor,
  blinked by opacity, always in the markup). A caret laid out inside the line box, or added and removed as it blinks,
  shifts the line 2-3 px per blink.
- `st.card(src, {width, glow})`: paper, a chip, a note — its outline is its picture's (leave `radius` out; one that
  disagrees with the picture's corners is refused: the slab showed past them); CORNERS in contacts() catches a
  hand-built rounded face on a square backing.
- `st.quad(obj)` -> the object's face corners on screen; `Stage3D.brackets(ctx2d, quad, {grow, arm, lineWidth})` draws a
  scanner's corners along them (grow 1.2 -> 1 to close in).

**Moments.** `assets/html/moments.js` (`examples/moments.html` runs every one), each a pure function of the film's t:
the small exact motions where ONE element keeps its identity while it changes what it means. `choose` (one-frame
press, solid flip, the rest dim to 18 % IN PLACE), `become` (a thing turns into another on one hard frame, holds,
travels to its slot), `demote` (a title steps down into its section's label), `change` (old value held, struck, the new
one in), `slot`/`reel` (the sentence still, the word in its slot cycling), `lead`/`follow` (one word first, the line
forms around it; `x` goes on the whole line), `underline`, `scan` (a constant-speed read; bracketed and named only
after the line passes), `lock`, `lift`/`land`, `type`/`retype`, `list`, `strip`, `carry`. And two built from the
film's own material: **`morph`** — write the product's screen in two states as HTML with `data-k` keys; `snapshot`
both in `filmReady`, `plan(A, B, {at})`, `stage(el, plan)`, then `draw(t, plan)` in seek: leavers dim in place,
survivors travel on one curve, changed text is struck and replaced, newcomers pop (small) or rise (large) — and
**`perform`** — a key word on screen does what it says while it is spoken (`count`, `split`, `join`, `strike`,
`mark`, `rise`, `weigh`), timed by `Moments.wordTime(timeline, word)`. Starting values adapted from video-shotcraft
(NOTICE); judge them on this film's frames.

## Maths that moves (step 6; `assets/html/math.js`)
A derivation is shown as typeset maths that MOVES, never as an image of an equation or Unicode text: the Remotion
tier's MathJax glyph outlines and its tuned moves (`remotion/src/runtime/mathCore.ts`: Write, TransformMatchingTex,
Indicate, the live number), bundled for the page.
1. List every equation in `<film_dir>/math.json`: `{"equations": ["x^2 + 6x + 5 = 0", {"tex": "x", "display": false}]}`.
2. `python3 scripts/mathtex.py <film_dir>` typesets them (offline, deterministic) into `_math/` + `_math/equations.js`
   and removes what the list no longer names; a TeX error stops here with MathJax's own message.
3. In `film.html`: `<script src="_math/equations.js"></script><script src="<skill>/assets/html/math.js"></script>`, then
   ```js
   const D = MathFilm.derivation({forms: [...the TeX...], box: {x, y, w, h}, em: 120,   // frame px
     write: [t0, t1],                                      // seconds: Moments.wordTime(timeline, word)
     steps: [[a1, b1], {at: [a2, b2], match: 'fade'}],     // one per later form
     highlight: {term: 'root', at: [a, b]},                // '*' = the whole last form; swell, pad (em) optional
     live: {term: 'live', from: '0', to: '9.81', at: [a, b]}});
   const L = MathFilm.label('\\frac{b}{2a}', {x, y, em: 56, anchor: 'center'});  // inline TeX at a point (baseline)
   // in window.seek(t), one target (<svg> or <g>) per equation:
   MathFilm.render(svgA, D.at(t), {ink: '#1d1f24', accent: '#d9480f'}); MathFilm.render(gLabel, L.at(t), {...});
   ```
**What travels.** `\class{name}{…}` in two forms is the same term: it travels to its new place even when it changes
order, and when it changes sides of the `=` it lifts over it as one piece. Any other shared mark travels only if it
keeps its reading order; a mark that would pass through others fades out and in. Name every term that should be
seen to move; names nest, the innermost one matches, so `\class{root}{x = \class{half}{-b}…}` lets `half` travel and
`root` be highlighted. `match: 'all'` (every shared mark travels) and `'fade'` (nothing does) per step.
**Layout.** One scale for all forms of a derivation (the widest decides it) and one baseline; `align` 'equals' (the
`=` signs on one vertical when the box allows), 'center' or 'left'. A step whose layout must differ starts a new
derivation (`D.pl[i]` and `D.eqs[i]` are the placements and typeset forms, for a hand-off). `\color{…}` in the TeX
keeps its colour; `accent` is what the timeline picks out.
**State.** `D.at(t)` returns `{draws, frame, tex, emPx}`; `MathFilm.core` has the raw moves (`writeState`,
`transformState`, `indicate`, `placeAll`, `matchGlyphs`, …) for a film that composes its own. The settled frame
between steps is exactly the typeset form, and every frame is a pure function of t.
Time each step to the word that names it, hold each settled form long enough to read twice, and keep about four forms
per derivation. The glyphs sit in a `<g data-math="<tex>">`, so `page_overlap_qa` reads an equation as a line and
reports a label laid over it.

## The short promo, told in type and music (steps 3-7)
**Type and finish that read as a company launch** (measured on the film that won the 2026-11-21 blind round, the
user: "字体大小的设置和排布就很好…有公司发布的感觉"; 1080p, rendered px):
- headline 104-124 px, weight ~740, tracking about -0.04 em, line-height ~0.94; never past ~130 px in a 16:9 product
  film (168 px headlines on a full-bleed colour read as a poster, not a launch);
- the line under it 46 px / 600, or body 32 px / 450: a strong HEAVY-LIGHT contrast, not two weights in the middle;
- an eyebrow above, 26 px / 700, uppercase, tracked +0.03 em, in the brand's deep colour or a muted ink;
- section titles 60-64 px; brand lines 34-40 px; machine labels in mono 22-28 px;
- the eyebrow, headline and deck sit as ONE left-aligned block (left margin ~120 px), or as a column beside the
  product (left picture, right type), with a lot of space around it; never centred stacks on every beat;
- the stage is the product's own ground (an app's paper white -> a slightly darker tint, top to bottom) with one soft
  key light and soft, colour-tinted shadows under the UI; film grain (film_deliver adds it) and a faint vignette; the
  brand colour as a signal, a few % of the frame.
`script.json` lines are what the viewer READS (type beats) and `{"id", "text": "", "show": s}` picture beats. Then
`python3 scripts/type_clock.py <film_dir> --seconds 30 --bpm 112` writes `timeline.json` with `"clock": "type"`
(every line long enough to read, every cut on a whole beat; an over-long script is refused with how much to cut);
`python3 scripts/score.py --bpm 112 --seconds <duration> audio/score.wav` scores it on the same grid;
`python3 scripts/mix.py --music audio/score.wav [--sfx audio/sfx.wav] --out audio/mix.wav` masters it with no voice.
film_qc skips the voice check on a type clock.

## Operating steps: a real recording (step 6; `scripts/app_record.py`, `assets/html/screenrec.js`)
Only for a film that TEACHES operating a desktop app (the steps a viewer will repeat). A film that shows a product
uses its screenshots and captures; a terminal program is `term_capture.py`; a web page in motion is `promo_record.py`.
1. Write the steps (`steps.json`, format in `app_record.py`'s header): the app, its window size, then `click` (window
   points) / `click_text` (the words on screen) / `menu` (a path, clicked item by item) / `type` / `key` / `drag` /
   `wait`, each with an optional `label` (what the narration calls it). Prepare the app's document first (demo
   content only, declared in `copy_ok.json` as `demo`), and close anything private on screen.
2. `python3 scripts/app_record.py <film_dir> steps.json --name rec`, outside Claude Code's command sandbox (inside it
   the app's windows are invisible to Accessibility). It needs macOS Screen Recording and Accessibility for the terminal, and stops with where to turn them on if either is missing (ask the user; never imitate the app
   instead). The real cursor is moved at a human pace by `app_drive.swift`; the window is recorded at its own pixels
   into `clips/rec/` (rec.mp4, frames/, rec.json with every action's time and place).
3. In `film.html`: `<div id="rec"><img><svg></svg></div>` and `<script src="<skill>/assets/html/screenrec.js">`, then
   ```js
   const E = ScreenRec.edit(REC /* clips/rec/rec.json */, {base: 'clips/rec/frames/', box: {x, y, w},  // frame px
     start, end, anchors: [{action: 2, at: Moments.wordTime(timeline, '图表')}, ...],
     zoom: [{at: 3, z: 1}, {at: 5, z: 1.6}], maxSpeed: 3});
   // in window.seek(t): return ScreenRec.draw(document.getElementById('rec'), E.at(t), {accent});
   ```
   Each anchored action lands on its word: the recording plays its result at real speed, then holds until the voice
   reaches the next action, or runs up to `maxSpeed` when the voice is quicker (beyond that it is refused, with the
   time it would need). The close-up follows the anchored actions (the Remotion tier's `focusTrack`, refused when it
   would whip) and is refused past the recording's own pixels; a ring marks each anchored click.
Check the click rings against the frames once (the log is aligned to the video by the picture's own changes).
4. Sound: `python3 scripts/screenrec_cues.py <film_dir> --until <the take's usable end> --skip <actions before the
   film>` puts a click on every click and a key on every keystroke at the second the edit plays it, then
   `sfx.py --cues audio/cues.json --seconds <duration> --out audio/sfx.wav` and `mix.py --voice … --sfx …`.

Set the take up so the film can teach from it (a fresh review of the first Numbers cut, 2026-11-25, found each of
these missing):
- A window tall enough that nothing the steps create makes the app scroll by itself (a chart inserted under a table
  scrolled the sheet; its sticky header then hid a row for half the film, and later points in window coordinates
  missed). Start the sheet at its top.
- Start from the state the viewer is in: a sidebar or panel the film teaches opening starts closed (Format), and every
  control the voice names is clicked on screen, never already open or already selected (a click on the active 2D tab
  showed nothing).
- Type what the viewer must read slowly (`"cps": 4` for a value) and wait about 0.6 s after a double-click before
  typing and before a Return, so the ring, the keycap and the result each have their moment.
- End on a clean state: deselect, so the last frames (and an end card made from them) show the result, not a
  stray selection and a parked cursor.
- Say every step the picture shows (a drag of the new chart played in silence and read as a mistake).
- Show what a recording cannot: `E.keys(t)` keycaps (a held Shift, Return) and a halo on `E.cursor(t)` (the real
  pointer is small at film scale); a tutorial ends on a card with the result and its numbered, labelled steps.

What the first real tutorial (Numbers 14.5, 2026-11-25) taught:
- Record a tutorial with `"capture": "avfoundation"` (ffmpeg, a steady 30 fps, the region cropped after): the default
  screencapture writes a frame only when something redraws, so the pointer froze on the Chart button while the open
  popover held the window still, and the click on the popover showed with no pointer at it. screencapture also always
  draws the pointer (-C or not).
- Rehearse first, in the real app, step by step with a capture after each (`screencapture -l<window id>` sees a window
  on another Space without switching to it); then reset the document by script and record the whole take.
- Run outside Claude Code's command sandbox, and only while the user is away (the system idle time, `ioreg -c
  IOHIDSystem` HIDIdleTime): the recording drives the real mouse and keyboard.
- Numbers ignores a synthetic drag-SELECT (a drag over cells selects only the last one), while dragging an object
  works: select a range with a click and `"mods": "shift"` on the last cell, and say Shift-click in the voice (the
  viewer cannot see a held key). A click on an already-selected cell then a drag MOVES its contents.
- An app may scroll by itself (inserting a chart scrolled the sheet 40 pt): later points in window coordinates then
  miss. `{"scroll": 10}` brings the view back before them.
- The automatic sync can be wrong on a take full of cursor motion (+1.10 s at 12 % agreement): measure two or three
  unmistakable events on the frames (a popover appearing, a bar changing) and set the offset by hand.
- screencapture can stop writing frames after a still stretch and only add the last one at the end (the Numbers take
  froze from its 4.5 s wait to the end): end the edit at the last good frame (`rec.n`), and keep waits short.

## Launch and product films (step 6)
A starting point measured on 20 official launch films (`references/craft-standard.md` "A product film",
`references/launch-film-study.md`); the WorkBuddy blind rounds (2026-11-16/17) chose the film that followed it:
- the real product is the hero, at size: its real screens fill most of the frame (about 55 % of the width or more), or
  a crop pushes onto the exact component the voice names, within the screenshot's pixel density, when the screen reads
  at that size; when it cannot (its pixels are too few), the UI is drawn simplified from it, honest: its layout, colours
  and sourced words; the demo world inside it (another app's inbox, a slide, a file list) as plausible generic demo
  content declared `demo` in copy_ok.json, grey bars only below reading size (at a readable size they read as a
  wireframe: the user, 2026-11-18);
- one hero object persists: the product's window stays, and the beats are its states, not new scenes;
- type rides with the product: one short display line beside or over the real screen, on the product's own ground
  (the problem, the promise, the payoff), the key word in the brand accent; a type card that leaves the product for a
  flat brand-colour fill lost the 2026-11-21 blind round to a film that stayed in the real UI;
- the brand early (the real logo within ~10 s) and a closing lockup (mark + line);
- one small celebration (a task completing) and a quick rhythm: few shots hold still past 1 s.

## Sound (step 7)
- Score: `python3 scripts/score.py --bpm 112 --seconds S [--climax T] score.wav` (a generated score on a beat grid).
- SFX: `python3 scripts/sfx.py --cues cues.json --seconds S --out sfx.wav`, cues `[{"t": s, "cue": name, "gain": 0..1}]`
  from 15 synthesised, deterministic sounds (`sfx.py --list`: click, key, tick, focus, whoosh, pop, riser, impact,
  sparkle, strike, chime, swell, settle, reveal); recorded takes in `assets/sfx/kenney/` (click, select, drop, glass:
  UI-game timbres; a product film prefers real-world foley, `promo-shotcraft.md` §4).
- Mix: `python3 scripts/mix.py --voice audio/voice.wav --music audio/score.wav --sfx audio/sfx.wav --out audio/mix.wav`.
  The music follows the voice: 20 dB under it while it speaks (`--under`; WCAG 1.4.7's floor, mixers use 18-24),
  8 dB up between lines (`--lift`, never above 6 dB under the voice), down before each line starts; SFX high-passed;
  mastered in two passes to -14 LUFS, true peak <= -2 dBTP. It prints the separation it reached and exits 1 when a
  tenth of the speech has less than 17 dB. Never a fixed music gain under a sidechain: one sat the score 2 dB under
  the words. film_qc's `mix` check holds a film with a music stem in `audio/` (score*, music*, bgm*, bed*) to the mix
  this script made and measured (`audio/mix.mix.json`).

## Rendering and delivery (steps 6 and 8)
- Frames: `python3 scripts/film_frames.py <film_dir> [--from A --to B] [--workers 4] [--probe 6]` -> `work/frames/`
  (every frame written; refuses canvas text drawn before its font loaded; the probe compares K moments in two fresh
  pages). A film page MUST draw canvas text only after `await document.fonts.load(...)` (in `filmReady`), and mark its
  caption element `data-caption` (the cover hides it). A vertical page declares its size in its `<head>`:
  `<meta name="film-size" content="1080x1920">`; without it the page is opened at 1920x1080 and a 9:16 film is
  captured as its top half.
- `python3 scripts/film_deliver.py <film_dir> --encode [--grain 3]`: the frames + `audio/mix.wav` -> `final.mp4`
  (CRF 17, aq-mode 3, a fine temporal luma grain against banding), `final.srt` (the classic caption chunker on the
  timeline's words, 0.1 s lead), `out.cover.png` (the final film's first hero shot, captions hidden), and the copy to
  the Desktop (`--no-copy` to skip).

## Checks (step 8)
`python3 scripts/film_qc.py <film_dir>` (each check's own doc in `references/pipeline-scripts.md`): flash, rewind (against `_plan.json`'s cuts), picture glide, empty frames,
shake, overlaps (`page_overlap_qa`: words or controls colliding on `film.html` over time, judged per line
fragment; mark a deliberate stack `data-overlap-ok`) and caption size (`caption_size_qa`: the burned caption line ≥ 4.6 % of the frame height in glyph ink, i.e. a
~54-56 px font at 1080p) on `final.mp4`; exit 1 on any red. `_plan.json`:
`{"video": "final.mp4", "fps": 30, "frames": N, "cuts": [...], "segments": [{"start", "end", "kind": "shot"|"loop"}]}`,
the cuts computed by the same rule the renderer uses to switch shots (a plan that rounded differently put a cut one
frame off and rewind_qa reported a replay). Known blind spot of picture_glide_qa: a sky or light whose colours change
with nothing moving, and a fast move over a near-textureless gradient (proved on the sky film, 2026-11-16); and
captions changing inside a shot under a slow push read as extra motion (the diamond film, 2026-11-17: 0.128 px with
captions, 0.080 without). A turning object that repeats by design is a `kind: "loop"` segment in `_plan.json`, with
the seam proved (the wrap frame differs no more than consecutive frames).
Content moving over much of the frame under a camera move (tops spinning, films playing in windows, a line being typed)
reads as stepping: MRI s13 0.126 px, topic-to-video s04 0.134 and s08 0.400 (2026-11-19); the two topic-to-video
shots passed with their content frozen (0.059 / 0.094), MRI s13 split into its stretches (0.101). A field fitted more robustly did not separate them (s13 rose to 0.285), so prove such a red the
documented way: the same move with the content held, recorded in `NOTES.md`. The delivery grain lifts the reading too
(the same frames encoded without grain: Shenzhen s04 0.140 -> 0.073, MRI s13 0.126 -> 0.107, topic-to-video s04 0.134
-> 0.105), and so does a 3D stage's own per-frame noise (dither, particles); reading the raw frames instead was mixed
across six films (some reds gone, one new), so it was not kept. A glide control is therefore encoded WITHOUT grain.
Re-calibrating this check on a labelled corpus of stepping and gliding shots is open work.
picture_glide_qa is slow when several films render at once; on a busy machine run it per shot (`--clip --from --to`).
**Before the film is assembled**, a builder checks its own shots: `film_qc.py <film_dir> --frames A-B` encodes frames
A..B-1 of `work/frames` as the film will be (into `work/qc_A-B/`, the plan and shot plan cut to that stretch) and runs
every check that can judge a stretch; the page checks step through those seconds only (`--frames` on
page_overlap_qa, film_copy_qa, stage_contacts_qa). Repetition, mix and the shot plan wait for the whole film, which
is still checked once at the end (a stretch is encoded on its own, so a borderline glide reading can differ a little).
Also in film_qc: edge cuts in `overlaps` (a readable line held across the frame's edge; `data-bleed-ok` for deliberate
bleed type), pictures (`picture_legibility_qa`: a picture or stage panel on screen that shows almost nothing, a black or
white block; `data-blank-ok` / `userData.blankOk` for an intended blank), copy (every word shown sourced or in `copy_ok.json` with a reason), contacts (stage3d: nothing inside
anything, no coplanar stacks), pan speed (no whip over 48 px/frame), repetition (advisory: one staging as the film's
device), banding (CAMBI > 5 on a shot: encode with the grain finish), shot plan and seams (a plain cross-dissolve
passed off as a planned seam fails). An advisory finding prints as WARN; a check this machine cannot run prints
WARN (not measured), never OK.

## Why these rules (the incidents behind SKILL.md)
- Style frames must differ as looks: the first end-to-end run (2026-11-16) offered one picture with three borders.
- Non-interactive runs still compare frames: two runs of the same sky request chose very different looks; the one
  that skipped the frames chose without ever comparing.
- Every drawn thing is correct: a Memphis film drew the physics model's two body halves as two cats' worth of legs.
- Fit beats habit: a blueprint cat film was well made and still the wrong look for a cat's playful physics (the user).
