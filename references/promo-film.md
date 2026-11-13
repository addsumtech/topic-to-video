# Promo film — a product film as a shot table over real captures

`scripts/promo_film.py <film_dir>` renders the composition `PromoFilm` (`remotion/src/promo/`) from
`<film_dir>/promo.json`. Use it when the film is a **product promo or launch** and the product has a UI you can
capture. Do not use it for a narrated explainer: that is the beat pipeline.

## Why this is a separate kind of film

The bar is video-shotcraft's showcase films and the brand films they learned from (ClickUp, Notion, Raycast, Linear-style
launches). Measured against them, our narrated films missed on six counts:

1. **The product is shown as itself.** Real 2x captures sit under a 2.5D camera; nothing is redrawn as a mock.
2. **Serif title cards are the breaths.** Each is one statement of 1.6–2.2 s, with its accent word in italic.
3. **One restrained look.** One ground, one paper, ink, and one accent: the product's own colour.
4. **Short shots.** Product shots run 1.5–6 s and every one has an action: arrive, lift, type, click, land.
5. **Flash cuts sit on the hard cuts.** They are never decoration.
6. **Sound is pinned to each action**, and the outro closes on riser → impact → sparkle.

A promo film is music- or SFX-led and may have no narration. Its words are the title cards, the short mono caption
strips and the brand's own lines.

## Captures

- Use **2x screenshots** of the real product, PNG.
  - Web product: a 2x full-page capture of each page (`deviceScaleFactor: 2`). Element boxes come from the DOM, in
    CSS px.
  - Desktop app: 2x window captures (Retina screenshots are already 2x). Measure the boxes on a CSS-px grid.
    `w`/`h` in the table are **pixels / 2**.
- Docs screenshots often carry annotation boxes. Clean them before use (WorkBuddy: red boxes and labels).
  - Interpolate each masked pixel across its shorter span and keep the darker side when both spans agree, so a
    gridline survives.
  - Protect filled disks such as the macOS traffic lights.
  - Look at the result. An annotation that sat across text has lost that text, so keep the camera off it.
- Never zoom past the capture's density. At zoom 2 on a 2x capture, one screen pixel is one texture pixel. Beyond
  that the text goes soft: `check` refuses it and PageCam clamps it.
  - A window narrower than 1920/2 CSS px can't fill the frame at zoom 2. Let its edge show on the ground, or frame
    two panes together.
  - Don't aim the camera past the window's edge for a single pane.

## The table (`promo.json`)

```json
{"look": {"ground", "groundEdge", "paper", "ink", "muted", "accent", "accentInk"},
 "shots": [
  {"kind": "brand", "dur": 84, "mark": "brand/x.svg", "aspect": 2.9, "kicker": "what it is"},
  {"kind": "title", "dur": 56, "text": "Describe it in *one* sentence.", "sub": "optional mono line"},
  {"kind": "page",  "dur": 128, "src": "caps/x.png", "w": 1446, "h": 800,
   "keys": [{"f": 0, "cx": 760, "cy": 330, "zoom": 1.05, "rx": 16, "ry": 12},
            {"f": 36, "cx": 800, "cy": 398, "zoom": 1.62, "ease": "swift"}],
   "layers": [...], "caption": {"text": "...", "at": 10, "dur": 70}, "flash": true},
  {"kind": "outro", "dur": 150, "mark": "...", "aspect": 2.9, "tagline": "...", "stampAt": 48,
   "pieces": [{"src", "pageW", "pageH", "box", "x": 0.2, "y": 0.25, "rot": -4, "scale": 1.6}]}],
 "sfx": [{"f": 120, "cue": "whoosh", "gain": 0.4}]}
```

- **Timing.** Every frame number counts from the start of its own shot.
- **Camera keys.** A key puts page point (cx, cy) at the frame centre at `zoom`, tilted by `rx` (top leans away),
  `ry` (right edge recedes) and `rz` (roll).
  - A key's `ease` is the curve of the move that arrives at it. The names come from `runtime/craftMotion` EASE:
    `swift` for a re-position, `smooth` for a slow drift, `snappy` for an arrival.
- **Cuts.** Shots butt-cut. A flash straddles every cut into a `page` or `outro` shot; set `"flash": false` on a
  shot to drop it.
- **`sfx`.** Omit it and the sound is planned from the table's actions. List it and your list replaces that plan.
  Either way, the cues actually used are written to `promo_sfx.json`.

### Layers (page CSS px, frames from the shot's start)

| kind | what it does | fields |
|---|---|---|
| `pop` | an element lands in its own slot (the slot is blank before it) | `box, at, fill` (the slot's ground), `from: up/left/scale`; `src, srcBox, srcW, srcH` take the element from ANOTHER capture (a state change: a button lit once text is in) |
| `lift` | an element rises toward the camera, a beam laps its edge twice, it settles back | `box, at, until, z, scale, slot` |
| `focus` | everything but one element dims | `box, at, until, dim` |
| `ring` | an accent outline draws round an element | `box, at, until` |
| `type` | text is typed into a field (the placeholder covered by the field's fill) | `box, at, text, cpf` (chars per frame), `size`, `fill` |
| `cursor` | a pointer travels and clicks | `path: [{f, x, y, ease}]`, `clicks: [f]` |
| `note` | a short serif annotation floats beside an element; a marker sweeps under its `*accent*` | `x, y, at, until, text, align` |

## Craft rules

- **Build the timeline in this order.** Brand open, then for each feature a title card followed by 1–3 product shots,
  then the outro.
  - Both wordmark moments (the brand open and the outro stamp) rest fully on for **at least 30 frames**.
  - A burst of motion ends with at least 15 still frames.
- **Use each signature move once as the hero.** That covers the lift-and-beam, the outro stamp and the crane from a
  tilted table view. Shown twice, a move reads as a template.
- **Every product shot does something.** A camera drift alone is a slideshow. Give the shot a landing, a lift, typing
  or a click, as its `layers`.
- **Camera discipline.** Use one move per intention (re-position `swift`, then a slow `smooth` drift), and don't go in
  and back out within one shot.
  - The tilted "table" view (rx 14–24, ry ±8–16) is for arrivals.
  - Re-positions land straight-on, or nearly so, before anything is read.
- **Words.**
  - Every line is sourced from the product's docs or UI, or is the film's own statement. No invented numbers.
  - Numbers the product's own demo shows in its capture are the product as itself, not claims.
  - Caption strips are capitals, short and present-tense.
  - Keep the accent ink at ≥4.5:1 on the paper (`check` enforces it).
- **Sound.**
  - The film is SFX-only unless `--bgm` is given.
  - Whooshes come only on real camera travel, and a burst of pops is one sound per 3 frames, fading.
  - Keys sound under typing, a click on a click, and the outro closes on riser → impact → sparkle.

## The loop

1. Run `promo_film.py <dir> --check`. Errors stop it, by name; advisories don't.
2. Run `--stills=f1,f2,...` at the settled point (~90 %) of each shot. Look at them full-size for sharpness and
   framing.
3. Do a full render.
4. Put it beside the reference films on one page (frames at matched points). The user judges; a metric doesn't.
