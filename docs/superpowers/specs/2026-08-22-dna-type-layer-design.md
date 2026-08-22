# DNA Type Layer — Design

**Date:** 2026-08-22
**Status:** approved (design), spec pending user review
**Related:** `2026-08-22-dna-atoms-design.md` (the atoms layer this mirrors in shape),
`references/remotion-shot-authoring.md` §C2

---

## The finding that motivates this

The Design DNA declares three typographic tokens — `fontDisplay`, `fontMono`, `fontBody`. Two
measurements say they do essentially nothing today.

**1. The declared typefaces have never rendered.** The remotion tier loads no fonts at all: no
`loadFont`, no `@font-face`, no `@remotion/google-fonts`, no font entry in `package.json`. Every
family in every preset is a bare CSS family name that resolves against whatever the rendering
machine happens to have installed. On this machine, verified against the filesystem:

| declared family | installed? | what actually renders |
|---|---|---|
| `JetBrains Mono` | no | `ui-monospace` → SF Mono |
| `Playfair Display` | no | `Georgia` |
| `Space Grotesk` | no | `system-ui` → SF Pro |
| `Baloo 2` | no | `Impact` / `system-ui` |
| `Inter` | no | `system-ui` → SF Pro |

So the "editorial high-contrast serif" seen in every editorial render is Georgia, and the terminal
tier's monospace is SF Mono. `TERMINAL_DNA.uniformType` faithfully injects
`"JetBrains Mono", ui-monospace, monospace` as a global `!important` rule — and that resolves to SF
Mono too.

This is also a **determinism defect**: output depends on the render host's installed fonts, which
violates the tier's determinism norms (fixed seeds, cached clips, pixel gates).

The repository already ships the files. `assets/fonts/` contains `JetBrainsMono-VF.ttf`,
`PlayfairDisplay-VF.ttf`, `SpaceGrotesk-VF.ttf`, `Bangers-Regular.ttf`, declared via `@font-face`
in `assets/html/base.css` — for the HTML tier only.

**2. The presets are barely differentiated.** Six of seven presets declare
`fontBody: 'Inter, system-ui, sans-serif'`; all seven declare the same `fontMono`. Even a perfect
delivery mechanism would therefore leave body text identical across six directions — because the
DNA itself says so.

**3. The tokens reach almost no shots.** `grep -rl "dna?.fontDisplay" shots/` → 4 of 134;
`fontBody` → 3; `fontMono` → 10.

Each of the three findings blocks the next. Fixing (3) alone changes nothing visible while (1) and
(2) hold; fixing (1) alone makes the existing declarations true but leaves six directions sharing
one body face. The work is therefore three ordered layers.

---

## Goals

- Every typeface a DNA names actually renders, identically on any machine.
- The seven directions are typographically distinct — type is a design language's primary carrier,
  not an accessory.
- That typography reaches the library without a 130-shot hand migration and without regressing any
  existing film.
- Chinese text keeps working everywhere.

## Non-goals

- The motion layer (`dna.motion`, 0 shots) — separate work.
- New style-native shot families — separate work.
- Any change to the HTML tier. It already loads these fonts correctly and is untouched.

---

## Layer A — Make the declared type real

**New file: `remotion/src/runtime/fonts.ts`.**

Loads each bundled variable font through `loadFont` from `@remotion/fonts` (v4.0.486, already
present in `node_modules`; signature `loadFont(options: LoadFontOptions): Promise<void>`, options
include `family`, `url`, `weight`, `style`, `format`).

Family names are copied **verbatim** from `assets/html/base.css:8-11`, so the two tiers name the
same faces and no existing DNA declaration changes:

| family | file | weight range | source |
|---|---|---|---|
| `Space Grotesk` | `SpaceGrotesk-VF.ttf` | `300 700` | base.css:8 |
| `Playfair Display` | `PlayfairDisplay-VF.ttf` | `400 900` | base.css:9 |
| `JetBrains Mono` | `JetBrainsMono-VF.ttf` | `100 800` | base.css:10 |
| `Bangers` | `Bangers-Regular.ttf` | `400` | base.css:11 |

Weight ranges are load-bearing: a variable font loaded without its range gets synthesised weights
(faux bold), which is a silent quality regression.

**URL strategy.** Import the `.ttf` files so the bundler emits them as assets:

```ts
import jetbrainsMono from '../../../assets/fonts/JetBrainsMono-VF.ttf';
```

This keeps the fonts inside the bundle and therefore independent of `--public-dir`, which
`render_remotion.py:176` points at the film's `out_dir`. `staticFile()` is **not** usable for this
reason, and a standalone `npx remotion still` (used for per-shot QA) has a different public dir
again.

*Contingency, with its trigger:* if the CLI bundle rejects the `.ttf` import, add a
`webpackOverride` to `remotion.config.ts` registering `asset/resource` for
`/\.(ttf|otf|woff2?)$/`. `remotion.config.ts` is read by the CLI, which is the path
`render_remotion.py` uses. Any future non-CLI `bundle()` caller must pass the same override.

**Load timing must be explicit and must fail loudly.** `fonts.ts` wraps the loads in
`delayRender()` / `continueRender()`, and on rejection calls `cancelRender(err)`. A font that fails
to load must abort the render, never silently fall back — this repository has already shipped one
`delayRender` defect (an `Img` crash on a missing logo) and one whole class of silent fallbacks
(this spec's motivating finding).

**Mount point.** `src/Root.tsx` imports `./runtime/fonts` at top level for its side effect, so the
fonts are present for the `Film` composition *and* for every standalone shot composition.

**CJK.** None of these faces covers CJK. Every font string in every preset must end with a CJK
fallback chain plus a generic family. The pattern to copy is already in the codebase at
`Film.tsx:127`:

```
"PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif
```

No preset currently has one. Layer B adds them.

### Gate A1 — the silent-fallback detector

A render that succeeds proves nothing about which face was used; that is exactly how this defect
survived. The only mechanical detector is a **pixel comparison**:

`remotion/src/runtime/__probe_fonts.tsx` renders one row per loaded family. Each row draws the
same fixed string twice: once in the family, once in that family's *generic* fallback only
(`monospace`, `serif`, `sans-serif`). `scripts/font_gate.py` renders the probe once, crops each
row's two halves, and asserts their SHA-256 differ. Identical halves ⇒ the family did not load ⇒
non-zero exit.

### Gate A2 — declared implies loaded

A test parses every quoted family name out of every font string in `dna.tsx` and asserts each one
appears in `fonts.ts`. This is what prevents Layer B from reintroducing the original defect by
naming a face nobody loads.

### Gate A3 — CJK fallback present

A test asserts every preset font string contains at least one CJK family from the known list.

---

## Layer B — Give each direction a typographic identity

**Process, not a table.** The pairings are a taste decision and will be made from rendered
specimens, not chosen in the abstract: once Layer A lands, render specimen frames for candidate
pairings per direction and have the user pick from real frames. Only then are the choices written
into the presets. (This mirrors how the finish layer was decided — and reversed — on real renders.)

**Principles fixed now:**

- `terminal` keeps `uniformType: true` and stays all-monospace. Layer A alone makes it real.
- `editorial` gets a high-contrast serif display *and a genuine text face for body* — continuing to
  set body in the same sans as every other direction is the defect, not the baseline.
- `blueprint` and `data` take a technical family (a grotesque with a matching mono), because their
  identity is instrumentation.
- `retro` needs a real display face; it currently names `Baloo 2`, which is neither bundled nor
  installed.
- `product` and `cinematic` are decided from specimens.

**Candidate slate.** So that an implementation plan can be written, Layer B starts from this
concrete slate. Specimen review may overturn any row; it may not leave a row empty.

| direction | display | body | mono |
|---|---|---|---|
| `terminal` | JetBrains Mono | JetBrains Mono | JetBrains Mono |
| `neutral` | Inter | Inter | JetBrains Mono |
| `editorial` | Playfair Display | Source Serif 4 | JetBrains Mono |
| `product` | Space Grotesk | Inter | JetBrains Mono |
| `blueprint` | JetBrains Mono | IBM Plex Sans | JetBrains Mono |
| `cinematic` | Bodoni Moda | Inter | JetBrains Mono |
| `data` | IBM Plex Sans | IBM Plex Sans | IBM Plex Mono |
| `retro` | Baloo 2 | Baloo 2 | JetBrains Mono |

Six files to add, all SIL OFL: `Inter`, `Source Serif 4`, `IBM Plex Sans`, `IBM Plex Mono`,
`Bodoni Moda`, `Baloo 2`. `Bangers` stays loaded for the shots that name it directly.

**Constraints on any pairing chosen:**

- Every family named must be loaded in `fonts.ts` (Gate A2 enforces this).
- Every font string ends with the CJK chain and a generic family (Gate A3).
- New font files are SIL OFL only, fetched from `github.com/google/fonts`, committed under
  `assets/fonts/` with their `OFL-*.txt` licence beside them — matching the convention already used
  for the four existing faces. Expected: 6 variable font files, roughly 2-5 MB total.
- Files added to `assets/fonts/` are shared with the HTML tier; adding a `@font-face` for them in
  `assets/html/base.css` is optional and out of scope here.

---

## Layer C — Deliver the type to the library

### C1 — Injection contract

`Film.tsx` injects, only when a DNA is active:

```css
.dna-film { --f-display: <dna.fontDisplay>; --f-body: <dna.fontBody>; --f-mono: <dna.fontMono>; }
```

Shots read them with the original list as the variable's **fallback**:

```ts
font: `800 200px/0.9 var(--f-display, Inter, system-ui, sans-serif)`
```

`var()` accepts a comma-containing fallback, so everything after the first comma is the original
family list, unchanged. With no DNA the variables are unset and the declaration resolves to exactly
what it resolved to before — which makes the no-regression claim **pixel-checkable rather than
asserted** (Gate C1 below).

This approach was chosen over the alternative of extending the existing
`useDNA()` + `dna?.fontBody ?? original` hook pattern to ~120 shots. That pattern is correct where
it already exists and those shots are left alone, but applying it library-wide requires inserting a
hook call and an import into every shot — the exact codemod that previously shipped a crash
(`MaterialHero`: hook inserted without its import, and anchored in the wrong component). The CSS
variable path needs no hook, no import, and no component-scope reasoning.

**Interaction with `uniformType`.** Terminal's global `font-family: … !important` rule beats a
`var()` in a `font` shorthand, so terminal behaviour is unchanged. This is intended and must be
stated in the docs.

### C2 — The codemod

`scripts/dna_migrate_type.py` rewrites hardcoded family lists to `var(--f-ROLE, <original>)`.

**Role assignment** is read off the `font:` shorthand the codemod is already parsing:

- family list matches `/mono|JetBrains|Menlo|Consolas|Courier/i` → `--f-mono`
- else font-size ≥ 64px → `--f-display`
- else → `--f-body`

**Exclusions the codemod must respect:**

- Shots that already read `dna.fontDisplay` / `fontBody` / `fontMono` — left alone.
- **SVG presentation attributes.** `font-family="var(--f-body, …)"` does *not* work as an XML
  attribute. Only CSS contexts (`style={{...}}`, `<style>` blocks) may be rewritten; `font-family=`
  attributes must be skipped.
- Any family list passed to `canvas.measureText` or otherwise consumed by JavaScript rather than
  CSS.

The codemod writes an assignment report (file, line, original list, size, assigned role) for
review. See Risk 1.

### C3 — Audit tooling

`scripts/dna_audit.py --type` reports per-shot type reach, the same way the existing audit reports
DNA depth, so the 4/3/10-of-134 numbers in this spec become a tracked metric.

### C4 — Caption typography

`Film.tsx:127` hardcodes `font: '700 44px/1.26 Inter, "PingFang SC", …'`. Only the caption's
*contrast* is DNA-aware (via `dnaGroundLum`); its typography is not. The caption is the one element
present on every frame, so it takes `dna.fontBody` (falling back to the current string) and
`dna.labelSpacing` where applicable. Its existing CJK chain is preserved verbatim.

---

## Testing and gates

| gate | what it proves | kind |
|---|---|---|
| A1 `font_gate.py` | each family actually loaded, not silently substituted | pixel diff |
| A2 declared⇒loaded | no preset names an unloaded face | unit |
| A3 CJK fallback | Chinese text still resolves | unit |
| C1 null-DNA pixel identity | Layer C changed nothing for un-themed films | **pixel diff over ≥20 shots, before vs after** |
| `dna_smoke.py` | all 134 shots render under a themed film | render |
| `keyframe_qa` / overflow gates | new font metrics did not push text out of frame | existing |
| specimen review | the pairings are actually good | human, on real frames |

C1 is a real render-and-hash comparison, not an assertion about colours. The atoms work is the
precedent: all five Critical defects there passed
`test_null_dna_preserves_every_original_colour`, because that test only checked colour
reachability. A type gate that only checks "a var is present" would fail the same way.

---

## Risks

1. **Role misassignment is invisible to every gate.** The heuristic can put a heading on
   `--f-body`; nothing mechanical will complain, because the output is still valid and still
   renders. Mitigation: the codemod's assignment report is reviewed in batches, plus specimen
   renders of a stratified sample of shots (largest text, smallest text, mono-heavy, mixed).
   This is the single largest risk in the plan and it is a review-cost risk, not a correctness one.

2. **New font metrics will change text fitting.** Georgia → Playfair Display and SF Mono →
   JetBrains Mono have different advance widths. Several shots size text from measured or assumed
   ratios — `EdStat` computes `numSize` from `finalLen * 0.6`. Text that fitted may overflow.
   Mitigation: run the existing overflow/keyframe gates across the library after Layer A and fix
   what they surface; treat Layer A's landing as requiring a full-library sweep, not a spot check.

3. **Webpack may reject the `.ttf` import**, requiring the `remotion.config.ts` override named in
   Layer A.

4. **Repository grows** by roughly 2-5 MB of font binaries.

5. **CJK regression.** Any new font string that loses its CJK chain silently breaks Chinese decks.
   Gate A3 covers the presets; the codemod must preserve the tail of every list it rewrites.

---

## Out of scope

The finish/atmosphere layer (proposed, prototyped on real frames, and rejected on 2026-08-22 — the
grain finish does not work on an all-dark-ground library, and the scanline was declined). The
motion layer. New style-native shot families. Migrating `EdFrame`/`TermFrame` onto the `Label` /
`Divider` atoms.
