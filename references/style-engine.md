# Style engine — any drawing style, film-wide

A user asks for a film "in a cartoon style", "水墨风", "like Kurzgesagt", "像宫崎骏那样", sometimes with a screenshot.
The skill does not keep a list of styles. It **decomposes** the style into values on fixed drawing axes
(`meta.style`), and one engine (`remotion/src/runtime/style.tsx`) applies them to everything every register draws:
218 shots, the workshop objects, and any register written later. A style nobody has asked for before is new values,
never new code.

- The failure this exists to prevent is the one the user named: **只换了配色，画法和线条还是原来的样子** — only the
  colours changed.
- `scripts/style_qa.py` fails exactly that.
- Design: `docs/superpowers/specs/2026-10-31-style-engine-design.md`.
- Measurements: `references/style-engine-spike.md`.
- Every value on one register: `references/style-axes.jpg` (regenerate with `scripts/style_axis_gallery.py`).

## The procedure (remotion tier; the shot-director's Step 0.65)

1. **References first.**
   - When the user gave images, those ARE the references: save them under `<out_dir>/style_refs/`.
   - Otherwise find 4–8 frames that typify the style (web search, Commons), save them there, and record where each
     came from.
   - No search possible: `refs: []` with `refs_missing: "<why>"`. The sample sheet then says in its title that there
     were none and asks the user for one. validate ERRORs on empty refs without the reason.
2. **Decompose.** Look at the references and write `meta.style`.
   - Every value away from the default gets a note in `notes` naming what in which reference it was read from,
     e.g. "line.outline all: every shape in refs 1–3 has a closed dark contour, ~4 px at 1080".
   - A spec that leaves every axis as drawn is a recolour: say so to the user, or decompose it properly.
3. **Palette and faces** come from the same references, through the DNA (`meta.design_dna`) as before. The style
   draws; the DNA colours.
4. `python3 scripts/style_spec.py <out_dir>` validates the spec. Unknown axis or value: ERROR.
5. **The sample, before the full render.** Run `python3 scripts/style_sample.py <out_dir>`.
   - It picks 2–3 beats (an object, a diagram, a type-led beat), renders them beside the references, adds a 2 s clip,
     and delivers both to the Desktop.
   - Show the user. Run `--signoff` **only after they say yes**.
   - `render_remotion.py` refuses the full render of a styled film without a sign-off, or with one for a spec that has
     changed since.
6. **Delivery gate:** `python3 scripts/style_qa.py <out_dir>` (also in `critic_brief --gates` for a styled film).
   **Look at its sheet.** It has passed broken pictures before; each time, the fix became a check.

## The axes

Px are at a 1080 px short side. Defaults mean "as the register drew it".

| axis | values | what it does |
|---|---|---|
| `line.weight` | number 0–24, `as-drawn` | the MAIN line's weight; lighter lines keep their proportion to it (floor ¼) — a hairline grid stays lighter than the series |
| `line.variance` | 0–1 | per-stroke weight variation (a hand's pressure) |
| `line.color` | `as-drawn`, `ink`, `fill-dark`, `none`, `#hex` | `ink`: whichever of the film's fg/bg contrasts with the fill it bounds (or the ground behind a line), black/white below 3:1; `fill-dark`: the fill, darkened. A line that carries HUE (a data series) keeps it |
| `line.outline` | `none`, `outer`, `all` | `all`: every filled shape gets an outline, drawn under its fill so the visible line outside the edge is the weight; `outer`: one ring around each drawing's silhouette |
| `line.join` | `as-drawn`, `round`, `miter` | corners and caps of every line |
| `line.wobble` | px 0–12 | the line redrawn by a hand (displacement) |
| `line.boil_hz` | 0, 6–12 | the wobble redrawn on the animator's clock: 3 drawings cycled, never per-frame noise |
| `fill.mode` | `as-drawn`, `flat`, `cel`, `texture` | OPAQUE gradients: mean colour, or `fill.steps` hard bands. `texture` = flat, painted with the medium (needs `surface.kind`) |
| `fill.steps` | 2–5 | bands under `cel` |
| `shade.mode` | `as-drawn`, `none`, `cel`, `soft`, `hatch` | LIGHT — translucent gradients (glows, vignettes, fades): `none` removes a full-frame one and flattens the rest; `cel` steps them; `hatch` steps them and lays ink lines where the drawing is in shade |
| `shadow.mode` | `as-drawn`, `none`, `hard-offset`, `soft` | each drawing casts one (not the frame, not a glint) |
| `shadow.offset` | px 0–40 | |
| `form.corner` | scale 0–4 | rect and box corner radii ×; above 1 also rounds square corners |
| `form.simplify` | 0–1 | drops decorative hairlines below `simplify × 2 px`; never a fidelity part |
| `surface.kind` | `none`, `paper`, `canvas`, `brush`, `grain` | the medium as GRAIN: dark specks multiplied on a light ground, light specks screened on a dark one; never a tone shift (style_qa TONE_MAX) |
| `surface.strength` | 0–1 | |
| `surface.source` | `procedural`, `generated` | `generated`: one tile through Codex at sample time; when it cannot, procedural + a recorded shortfall |
| `type.display` | `as-dna` or a face | display type only (≥ 6% of the short side, or `data-type-role="display"`) |
| `type.display_outline` | bool | an ink outline on display type |
| `motion.stepping` | 1, 2, 3 | the register's clock on ones, twos or threes, after the sync warp; captions, voice, camera and seams stay on ones; never under reduced motion |
| `motion.easing` | `as-drawn`, `overshoot`, `snappy`, `floaty` | bends the shared easings 180 registers use; `style_coverage.py --motion` lists the 37 that roll their own |
| `motion.squash` | 0–1 | a helper (`runtime/styleMotion.squashAt`); no register adopts it yet, so it does nothing visible |

**Provenance:**
- `name` (the user's words);
- `refs` [{src, from: user|found, credit?}];
- `refs_missing`;
- `notes`;
- `shortfalls` [{axis, wanted, got, why}]: what the engine could not draw, printed on the sample sheet. Never hide one.

## The rules the engine keeps (any style)

- **Type** keeps its glyphs: never wobbled, textured or posterized, and never moved. A line that crosses type keeps
  its drawn weight and colour. Captions are outside the layer. Display type may take an outline and a face.
- **Photographs and canvases** keep their pixels: they are evidence, or beyond the DOM. Their frames take the style.
  `style_coverage.py <out_dir>` lists such beats; more than a quarter of the film exempt draws a warning.
- **Translucent is light, not paint.**
  - A see-through gradient follows `shade`, not `fill`.
  - A shape under 60% alpha (a glint, a halo) gets no outline and no shadow.
  - A full-frame vignette is never flattened into a veil.
- **Grounds go flat, never banded.** Edge-to-edge bands (a letterbox) are frame furniture: no ring.
- **No style, nothing mounts:** the tree and every pixel are what they were. The shared easings are exact without a
  style, extrapolation included.

## Shortfalls a style can hit today (say them, do not work around them)

- A register drawn on a canvas (`MaterialHero`, `PortRail`) or around a photograph keeps its picture.
- Easing reaches 180 registers; the 37 listed by `--motion` move as drawn (stepping still reaches them).
- `motion.squash` has no adopter.
- A gradient-stroked line (KnowledgeGraph's edges) is not seen as a hued line and takes ink.
- Generated textures are unverified while the Codex account has no image tool.
- A style that needs a drawing property no axis has is an ENGINE change, made once for every style, never a
  per-film workaround.
