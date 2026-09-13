# Authoring & judging remotion bespoke shots

Read this **before authoring per-beat shots, before BUILDING a new shot, and when reviewing a rendered film**
(shot-director + shot-critic both name it). It is the hard-won floor for the `meta.renderer:"remotion"` tier —
every rule here comes from a real defect that shipped and had to be fixed. Two axes: **frame-craft** (the shot
must sit in the frame correctly) and **meaning** (the shot must *encode* the idea, not decorate it). A shot can
pass every automated gate and still fail both — these are the judgments the gates can't make.

## A · Frame-craft floor (mechanical — get it right by construction)

The Film composites shots **full-bleed** at 1920×1080 and burns the narration caption in a reserved bottom band.
So each shot owns the whole frame and must keep its own content inside the safe zones. Import the shared numbers
from `src/runtime/layout.ts` — do NOT hand-guess pixel positions.

1. **FULL-BLEED background, always.** The shot's root `AbsoluteFill` background (gradient/solid) must reach all
   four edges, opaque. **Never wrap the shot in a scale to gain a safety margin** — scaling shrinks the shot's
   OWN background and exposes the atmosphere behind it as **black borders on the sides + bottom** (a real
   regression). Edge-safety is a per-ELEMENT contract (keep individual labels/graphics off the edge), not a
   global squish.
2. **Title band.** Put the shot title at `TITLE_Y` (use `titleStyle`); keep real content out of `[0, CONTENT_TOP)`.
3. **Caption band.** The Film burns the caption in the bottom `CAPTION_BAND` px. Keep the shot's own text/labels
   out of `[H - CAPTION_BAND, H]` — the ONLY allowed thing down there is a small `credit` line at `bottom:8`.
   A shot label at `0.9·H` WILL overlap the caption.
   **The band is `captionBand(W, H)`, not the constant.** `CAPTION_BAND = 150` is a legacy landscape number kept
   for compatibility; the live reserve is DERIVED from the caption's own type size — **227px at 1080p landscape,
   298px at 9:16** (a narrow frame wraps the same sentence to an extra line). Take every content bottom edge from
   `captionBand(W, H)` / `contentBottom(W, H)` — never a literal `bottom: N` (the small credit line above is the
   one exception). That rule is the fallout of GROWING the band: a viewer read the caption as part of the content
   above it, and the gap was paid for out of the BAND rather than out of the type — shrinking the type had dropped
   the caption to 3.4% of frame height, under the 5.2% floor that keeps a 1080p film readable in a phone-sized
   window. Run across all 146 registers afterwards, 26 sat inside the band, 13 of them newly — each had safely
   cleared the old 150px. BrutalistType and MagazineSpread were pinned at a literal `bottom:N`; PlanPalimpsest's
   fixed `H*0.11` legend reserve, which used to overflow into empty page, began overflowing under the subtitle. A
   literal that is safe today is a defect the next layout change ships for you. The derived band is a reserve you
   can trust: it is sized on the LATIN lead and the caption fits ITSELF to it (a CJK or over-long caption shrinks
   rather than growing the band), and both `fitContentSquare` and `maxCameraPush` measure from it — so the beat's
   camera cannot push your lowest content into it either.
4. **Center a hero image/panel in the CONTENT ZONE, not the whole frame.** A square centered in the full frame
   rides up UNDER the title (an MRI sized `0.72·H` and centered literally overlapped its title). Use
   `fitContentSquare(W, H, {hFrac, wFrac, bottomReserve})` — it returns `{S, left, top}` centered in
   `[CONTENT_TOP, H - CAPTION_BAND]`. Pass `bottomReserve` when the shot draws its own labels UNDER the image
   (ticks, a note) so the square shrinks and those labels stay above the caption band.
5. **Edge-anchored labels must survive a resize.** Two labels anchored to a panel's left+right edges COLLIDE in
   the middle when the panel shrinks (a real bug after an image was made smaller). Anchor to a stable reference
   (frame-relative x, or one centered line with a separator), not the panel width.
6. **Camera is LOCKED by default; drive animation through `useT`.** Every shot animates itself via `useT` (the
   shared 0→1 driver). A whole-film camera DRIFT on top of that reads as a per-frame **shake** — it is OFF by
   default (opt-in via `meta.camera_drift`). Do not add a per-shot floating/breathing transform to the whole shot
   for "life"; animate the CONTENT, keep the frame still. **Use `useT` (not `useCurrentFrame` directly) so your
   shot respects `meta.reduced_motion`** — under reduced motion `useT` FREEZES at a settled value (0.86), so the
   shot renders a static, fully-revealed frame (the accessibility cut); a shot that reads the frame directly keeps
   animating and won't honor it. **Brand:** a `meta.brand.logo` renders as a persistent corner bug (Film-level),
   so shots must not also draw a logo.
7. **Determinism.** Pure function of `useT()`/frame. No `Date.now()`/`Math.random()`/argless `new Date()` — use
   `hash01(i)` for stable pseudo-randomness. Signed data must render signed; CJK copy must fit; aspect must adapt.
9. **Author in FRACTIONS so the shot reflows to ANY aspect.** The Film Composition is aspect-driven: `meta.aspect`
   (or `--vertical`) renders 16:9 `1920×1080` / 9:16 `1080×1920` / 1:1 / 4:5 / 4:3 (Root.tsx `calculateMetadata` +
   render_remotion pass an `aspect` prop; preview a shot at portrait with `--props '{"aspect":"9:16"}'`). A shot
   reads W/H from `useVideoConfig` and must lay out in **fractions of W/H** — never hardcoded 1920/1080 — so it
   fills the frame at every aspect. Two things break in PORTRAIT and must be handled with `const portrait = W < H`:
   (a) a **multi-column** layout (hero-left + tiles-right) must **STACK** (hero on top, tiles below) — a side-by-side
   grid is unreadable at 1080 wide; (b) a **wide-horizontal** element (a beam, a versus-split, end-anchored boxes)
   overflows or clusters tiny — cap box widths to stay on-frame, or re-lay it vertically. The caption band is
   aspect-aware — reserve `captionBand(W,H)` / `contentBottom(W,H)` from `layout.ts` (a narrow frame needs a taller
   band), not the fixed `CAPTION_BAND`; `fitContentSquare` already widens a hero image in portrait. **On a non-16:9
   film, still-render EVERY chosen shot at that aspect and fix/swap any that don't reflow** — most centered / stacked
   / chart shots are fine; the library's fixed multi-column + wide-horizontal registers need this pass.
8. **Size for the REAL content, not the demo.** Registers are tuned to their DEMO copy — short words
   (`PLAN`/`BUILD`/`SHIP`), a fixed element count, a small marker. Real topic copy is longer and breaks that
   tuning in three ways you must check on the RENDERED frame at real length: **text overflows to the frame edge**
   (a 92px label sized for "Plan" runs off the box for "2025 - OpenAI Group PBC" → pad the container + shrink/wrap
   + split long strings, e.g. a year badge + a label line); **elements collide** (connecting arrows offset for
   short words land ON a long phrase → drop the arrows or make the offset adaptive); **a marker is too small to
   read** (a 22px "→" between big cards → size markers to the composition). A shot that renders clean with its
   demo props can still fail here — always still-render it with the ACTUAL props before trusting it.

`text_safe_qa.py` backstops #1–#3 exactly for TYPE (it asks the DOM, so a full-bleed graphic is not a finding and a
cut word always is); `frame_safe_qa.py` adds an advisory palette-outlier read; the rest — especially #8's overflow/
collision/tiny-marker — are eyeballed by the shot-critic (S10). Getting them right structurally (via `layout.ts`
+ sizing for real content) is cheaper than being caught.

## A2 · Depth — planes, only where the beat actually has a foreground and a background

`<Plane depth={DEPTH.behind}>` (`src/runtime/depth.tsx`) separates a shot into parallel planes. `DEPTH` is named
rather than numeric because a bare number says nothing about what the author meant: `lifted` (−1 — above the
ground, casts a shadow), `subject` (0 — what the narration is talking about NOW, always the plane in focus),
`behind`, `context`, `far`.

**It is 2D on purpose**, built only from SIZE, FOCUS, SHADOW and PARALLAX. Measured on this library's own
renderer, on a text-dense shot: glyph edge strength 91 baseline, 86 under a plain 2D `scale` (and that drop is
entirely the glyphs being LARGER, not softer — magnified crops are indistinguishable), and **56 under
`perspective(1200px) translateZ(50px)`: a 38% loss that is plainly fuzzy to the eye**, because a 3D-composited
layer is promoted, rasterized once at layout size and GPU-upscaled, while a 2D transform is repainted at final
resolution every frame. A shot that genuinely needs converging perspective (a receding wall) may still reach for
a 3D transform — but it must not carry text anyone is expected to read.

**A plane must ENCODE the beat.** Near is what the narration is on NOW; far is the context it sits in. Apply the
hide-the-caption test to the ARRANGEMENT: with the words gone, does the stacking still say which is subject and
which is setting? Splitting things across planes for the look of it is decoration. Both live users are structural
claims, not atmosphere:
- **PlanPalimpsest** puts the earlier survey one plane BACK because "two surveys in register on the same ground"
  is that register's whole claim. Flat, it can only assert it — the eye has no reason to read one as under the
  other; a plane's separation gives it one, and when the beat's camera moves the two drift by different amounts,
  which a viewer already knows how to read as distance. Its labels stay on `subject`: they are the film speaking
  ABOUT the plans, not part of either.
- **PhotoPlate** LIFTS its numbered marks off the print. A mark the film added is not part of the photograph, and
  the shadow is the thing that says so.

**Never scale a lifted layer yourself** — `Plane` shrinks planes BEHIND the subject only, and that asymmetry is
load-bearing. Scaling a lifted plane about the frame centre DISPLACES everything on it: measured, a mark pinned
to a point in a photograph moved 29px, about its own width, and stopped pointing at the thing it named — fatal
for the one job an annotation layer has. A lifted plane keeps its registration and carries an alpha-following
`drop-shadow` instead, so each chip, ring and leader gets its own shadow, which is what "these marks are lying on
the print" actually looks like.

Parallax is the only cue that needs the beat's camera to move (`scene.camera` — a storyboard field, not something
a register sets); size, focus and shadow carry the reading on a held beat. So a plane split is worth building
either way, and reads strongest on a beat that also earns a push.

## B · Meaning — every design must ENCODE its beat

The dominant failure mode is a shot that is **dark-and-pretty and vaguely on-topic but encodes nothing specific**.
The test, applied to every beat:

> **Hide the caption. Does the visual still carry THIS idea, and only this one?** If the picture could sit under
> any nearby caption — or reads as generic "science/tech atmosphere" — it DECORATES. Redesign it so its
> *structure* mirrors the content: symmetry, direction, accumulation, sparsity, cause→effect.

Refinement / 高级感 is required too, but **never as a substitute for meaning** — a gorgeous shot that encodes the
wrong thing is worse than a plain one that encodes the right thing.

**Anti-patterns that actually shipped this tier (and the fix each got):**

| Beat idea | Decorative/contradicting design (WRONG) | Encoding design (RIGHT) |
|---|---|---|
| RF pulse tips the magnetization | radial burst "radiating outward" (an RF pulse is a single-frequency resonant field, not outward radiation) | M nutating into the transverse plane driven by a resonant B₁ wave |
| Free-induction decay | a "voice-call" waveform (generic audio) | a decaying oscillation induced in the coil (T2* envelope) |
| Frequency encoding | a scrolling spectrum/ticker (shows neither position nor FFT) | columns pitch-ramped by position → summed → FFT peaks |
| k-space | a kaleido/mandala (pretty, symmetric-ish) | the REAL FFT log-magnitude; then center=contrast / edges=detail via actual partial reconstructions |
| Aliasing | a digital "datamosh" glitch (generic corruption) | the real anatomy WRAPPING onto itself (fold-over ghost) |
| "You can't go faster" | text overflowing decorative boxes | a gradient-speed bar physically capped at the slew-rate + PNS ceilings |
| Compressed sensing | yet another node diagram | the typeset objective `min‖Ψx‖₁ s.t. ‖Fx−y‖₂≤ε`, annotated — **an equation IS a valid encoding** |

**Operating rules that follow:**
- **Build BESPOKE when no library register encodes the specific concept.** Swapping among generic library
  registers hits a ceiling for topic-specific ideas (and often drags in leftover demo copy / mangled numbers).
  When a beat needs a real mechanism shown, write a new `src/shots/*.tsx` (register it in all sync points — see
  the shot-registration note) rather than forcing a near-miss register.
- **Use REAL imagery on concrete topics (the documentary tier), not colored blocks.** Composite a real MRI;
  compute the real k-space and the real center-only / edge-only reconstructions with numpy (`fft2`/`ifft2`);
  fetch a license-clean real photo via `imagefetch.py`. A real image the design ACTS ON (reconstructs, folds,
  denoises) both teaches and looks premium. Keep the design language's VIBE/technique but fill it with real,
  substantive, sourced content — and it must generalize: the image is a `src` prop, so the same shot serves any
  topic. Credit CC-BY on screen. **Take the credit from the sidecar, never from memory** — `imagefetch.py`
  writes a `<file>.json` beside each image naming the real author + licence, and `validate.py` ERRORs when a beat
  shows an image whose sidecar author it does not credit. A shot therefore receives its credit as a PROP (like the
  `src`) and never hardcodes one: a hardcoded credit is both a wrong attribution the moment the image is swapped
  and, since it is a real person's name, a fabricated fact.
- **Audit ALL beats, not just the ones flagged.** When one shot is found decorative, re-run the hide-the-caption
  test on EVERY beat (举一反三) — the same reflex usually produced several. Fix the whole class.
- **No fabricated data.** A number-bearing shot must carry a SOURCED figure (traces to `source_ref`), never its
  demo default and never an invented stat.

## B2 · Adapt the register to the topic — don't text-swap the demo

A register ships with **demo scaffolding**: placeholder mini-widgets, generic glyphs, a demo-length label set, a
fixed element count, a stock layout. **That scaffolding is a mannequin, not your content.** The lazy move —
picking a register and only changing the text while keeping its demo furniture — produces a beat that is
on-topic in words but generic in design, and it is a REVISE. Per the user's rule: *keep ONLY the design
language's STYLE (its framework, vibe, motion, material), and re-design both the CONTENT **and the register's own
MODULES/COMPONENTS** so the design actually represents THIS topic's content.* This is "临场设计优化" — adapt the
language to the subject on the spot, every time, for every topic. **Rebuilding the components to fit the subject
is the DEFAULT, not a special case** — the words changing is the *least* of it. **But it is a judgment call, not a
blanket rewrite:** if a register's stock module/component ALREADY encodes THIS topic's content well, KEEP it —
changing what already fits just to look different is as wrong as text-swapping, and throws away the register's
proven strengths. Decide per module — does it carry the DEMO's meaning or THIS topic's? — keep the ones that fit,
redesign the ones that don't. (This is why `shot_adaptation.kept` records the modules you kept, not just "style".)

**Record the redesign, per scene, in `shot_adaptation` = `{kept, redesigned, topic_idea}`** (a REQUIRED field on
every remotion scene): the STYLE you kept, the MODULES/components + content you rebuilt for this topic, and the
topic-specific creative idea the shot now encodes. `validate.py` WARNs when it is missing or `shot_props` is empty
(a raw text-swap); the shot-critic (S10) reads the note and checks it against the rendered frame. Writing it is
what makes the redesign a decision instead of a reflex — a note you cannot fill honestly is a beat you have not
actually adapted.

**The litmus:** *would this beat look the same on a completely different topic with only the words swapped?* If
yes, you text-swapped a template — redesign the content. Concretely:
- **Replace placeholder motifs with meaningful ones.** A "product surfaces" bento that renders a RANDOM bar
  chart / ring / sparkline per tile encodes nothing — each tile must carry a glyph that MEANS its item (API → `{ }`
  braces, a video product → a play-frame, a coding agent → a code block, a browser agent → a cursor-on-window).
  A tile's picture should be decodable as *that* thing with the label hidden.
- **Match the layout to the content's SHAPE.** A register built for a short SEQUENCE with connecting arrows
  (`PLAN → BUILD → SHIP`) is wrong for three PARALLEL open questions — the arrows assert an order that isn't
  there and collide with the long text. Re-lay it out (stack them, drop the arrows) so the layout states the
  right relationship. A "loop" must read as a CYCLE, not a linear row; a hierarchy as nesting, not a list.
- **Build an in-style variant whenever the stock modules don't carry the idea — that's the NORMAL move, not a
  last resort.** Don't reserve it for when the structure obviously "fights" the topic; reach for it any time the
  register's stock modules don't already *encode* this beat's content. Write a small bespoke shot that keeps the
  register's VIBE (the bento pop, the interrogation light, the mechanical coupling) but whose modules/components
  are composed around the real content. This is the line between *using* a design language and *reskinning a
  demo*. (This session added `PlatformSurfaces` from
  BentoReveal and `OpenQuestions` from SpotlightStage for exactly this reason; `TensionScale` for the mission
  tension; and fixed CubeRotate/CardFlip3D's demo-length assumptions in place.)
- **Prefer editing the shared register when the fix generalises.** A demo-length assumption (a fixed 92px label,
  a 22px marker, an un-padded box, arrows offset for short words) is a BUG in the register, not just this beat —
  fix it at the source (pad + wrap + split long strings; size the marker; make the arrow offset adaptive) so
  every future film benefits. Build a NEW shot only when the *structure* differs, not merely the sizing.

Both the shot-director (when authoring) and the shot-critic (S10) apply this — a beat that kept its register's
demo scaffolding is flagged and redesigned, not shipped.

## C · Coherence — shots must fit the chosen DIRECTION

The user picks ONE whole-film direction from the contest (`meta.shot_template`). The per-beat shots are each
their own language, but they must read as **one film in that direction's tone**, not a random stack of unrelated
languages:
- **Palette + motion + motif continuity.** Carry the direction's accent/ground and motion personality through
  the beats (pass consistent `accent`/`accent2`; keep the motion character — e.g. a "precise/technical" direction
  animates with measured reveals, not bouncy squash). Family variety is about SILHOUETTE, not a licence to switch
  visual worlds every beat.
- **The direction's hero carries the opener/climax**, and the majority of beats sit in its family lean (a
  `data-story` film shows charts/graphs; a `terminal-technical` film shows code/schematics). shot-critic S7 gates
  this; it's a lean, not a straitjacket (S2 variety still wins).

## C2 · Design DNA — the GLOBAL visual system (reuse the STRUCTURE, not the visual identity)

The selected template is **NOT a set of reusable frames — it is the film's whole visual system.** A library
register bundles two separable things: its **STRUCTURE** (composition + motion + information hierarchy — the
reusable asset) and its **VISUAL IDENTITY** (typography, palette, container/border, decoration — hardcoded in the
.tsx). The DNA architecture **pulls the identity OUT of the register into one film-wide `DesignDNA`** (`remotion/
src/runtime/dna.tsx`) that every migrated register reads via **`useDNA()`**, so the SAME structure (a bar race, a
gauge, a card stack) wears the film's system — "different compositions, one visual universe" (the remotion
analogue of the html tier's `theme.css`). Reuse the structural idea, **never** copy the original visual identity.

- **How it flows.** The shot-director expands the template into `meta.design_dna` (an explicit token artifact;
  a built-in preset like `TERMINAL_DNA` auto-applies when only `meta.shot_template` is set). `render_remotion.py`
  passes it to the `Film`, which provides a `DesignDNAContext`; each register reads `useDNA()`. **Backward-compatible
  by construction:** a migrated register reads `dna?.token ?? <its original value>`, so with NO DNA it renders
  byte-for-byte as before (the WorkBuddy default + un-themed films are untouched).
- **Migrating a register (three levels — most shots are A+B, not C).** **A — swap tokens:** replace hardcoded
  font/palette/radius/border with `dna?.fontMono/bg/bgGrad/accent/surface/... ?? original` (use the shadow trick:
  rename a module `const ACC='…'` → `ACC0`, add `const dna = useDNA(); const ACC = dna?.accent ?? ACC0;` so every
  downstream use inherits it). **B — add DNA cues:** render 2–3 shared grammar cues from `runtime/dna.tsx`
  (`Caret`, `Breadcrumb`, `ScanGrid`, `StatusTag`, a `▸` prompt on the heading) — inert unless the DNA declares
  them. **C — rebuild:** when the structure fundamentally clashes (a serif cinematic flare, a chrome word) OR the
  shot is a LIGHT-ground register (the codemod skips those) — restyle it into the DNA or swap to a DNA-native
  register. The level-C pattern for a light-ground shot is **flip the WHOLE palette together**: derive `bg`/`fg`/
  `accent`/`surface`/`onAccent` (+ `dim`/`line`) from the DNA with the originals as fallbacks, and route EVERY
  ground, panel, ink and on-accent-text through them — so on a dark DNA the shot becomes a coherent dark version
  (readable) instead of light-ink-on-light-ground (the level-A inversion), and null DNA is byte-for-byte the
  original. Worked examples: `SwissEditorial.tsx` (a cream/ink/red poster → a dark editorial poster; the red ticker
  band's text uses `onAccent`) and `ChatThread.tsx` (a light chat → a dark chat; the "you" bubble is `accent` with
  `onAccent` text, the assistant bubble is `surface` with `fg` text — and the module-scope `Bubble` subcomponent
  reads `useDNA` itself), `BlueprintGrid.tsx` (white graph paper → a dark engineering drawing; `paper→bg`, `ink→fg`,
  `grid→line`; the `Draw` subcomponent reads `useDNA` and derives its default stroke INSIDE — a param default can't
  reference the renamed const), and `RisoPrint.tsx` (its look is `multiply`-on-paper, which goes black-on-black on a
  dark DNA — so it switches the blend to `screen` (ink ADDS light on the dark ground) with the two DNA accents as
  the channels: when a shot's LOOK depends on a blend mode or a light ground, level-C adapts the TECHNIQUE, not just
  the tokens). **Watch for a TDZ:** put `const dna = useDNA()` + any derived palette BEFORE the first use
  (a `const NODES = …PALETTE…` above it breaks).
- **Migration tooling + the gates that make gaps non-silent.** The library is now **fully migrated — all 134
  registered shots read the DNA** (`python scripts/dna_audit.py`), so the tools below are a gate on NEW shots and a
  depth report, not a backlog. Five tools:
  (1) **`python scripts/dna_audit.py`** — self-updating (greps the shots for `useDNA`) worklist of which registered
  shots are DNA-aware vs still hardcoded, grouped by family; never a manual manifest that rots. (2) **`validate.py`
  lint** — on a DNA-THEMED film (a `design_dna` or a preset `shot_template`), every scene whose `shot` never reads
  `useDNA` WARNs (renders its own palette, breaking the global system) — so a gap surfaces instead of shipping
  wrong. (3) **`python scripts/dna_migrate.py <ShotId>…`** — a CONSERVATIVE shadow-trick codemod for the CLEAN
  pattern (named module colour consts + a single top-level component); it SKIPS anything it can't do safely
  (module-scope sibling subcomponents, computed/inline-only palettes, style-locked registers like a synthwave
  scene) and leaves those byte-identical for hand migration. It does LEVEL A only — after it, RENDER each migrated
  shot under a themed DNA and LOOK (a green codemod is not a correct look; level-A recolours named tokens but a
  shot with many inline hardcoded colours or an accent-as-prop-default needs a level-B hand pass). **The codemod
  only migrates DARK-ground shots (`shotLuma` == 'dark').** Mechanically recolouring a LIGHT/mid-ground shot onto a
  dark DNA INVERTS its contrast — it maps ink→`fg` (now light) while the usually-inline light ground stays put, so
  text renders light-on-light (invisible). Light-ground registers (a chat UI, a swiss/editorial spread, a blueprint
  on white paper, a riso/halftone print) are level-C HAND rebuilds — flip the whole ground + panels together (all
  of the library's light-ground registers have been). **New style-
  native family shots + Term*/Ed* must also be added to `runtime/shotLuma.ts` (ground luminance) and
  `shot_director.FAMILY` (variety) — a `tests/test_remotion.py` gate fails if either is missing.**
- **Deriving a whole PALETTE from the DNA (illustration registers).** A cartoon, a clay stack, a cut-paper diorama,
  a comic page, a maximalist collage — their look is carried by a multi-hue palette, which no token swap can serve.
  `runtime/dna.tsx` exports colour utilities for exactly this: `mix(a,b,f)`, `tint(c,f)`, `shade(c,f)`,
  `rotate(c,deg)` (HSL hue rotation) and **`dnaPalette(dna, n)`** — n distinct, film-coherent hues grown from the
  DNA's two accents (and `null` when there is no DNA, so `dnaPalette(dna,6) ?? ORIGINAL` keeps the original set).
  All of them PASS THROUGH anything unparseable (a gradient string, `rgba()`), so they can never paint black by
  accident. The rule for these shots: **keep the TECHNIQUE, re-hue the world** — thick ink outlines still read as
  cel shading when the ink inverts to light on a dark ground (CartoonPop), clay is still clay when base/highlight/
  shade are `tint`/`shade` of a DNA hue (ClayStack), a cut-paper diorama keeps its depth logic when each plane is
  `mix(accent, bg, f)` a step deeper (PaperCutout). Colour that is SEMANTIC or identity — CPK element colours,
  MRI physics vectors, syntax highlighting, per-collaborator cursors — must survive the theme untouched.
- **The PRODUCT itself — `runtime/uiSurface.tsx` + `runtime/pageCam2D.tsx`.** For a beat that is *about a
  piece of software*, this library used to have nothing: no window chrome outside the terminal, no sidebar in
  any register. `<UiSurface page="cards|chart|table|form" W H dna content />` draws an application window from
  the DNA — chrome, nav rail, and one of four page shapes — and it takes CONTENT (the topic's own nav, card
  titles, rows), because a frame of anonymous grey bars fails the decodability rule by construction. Bars are
  the per-element FALLBACK and the rule is a size one: an element draws type only where its own type would
  clear a legibility floor, so the same surface holds up filling the frame and 250px wide in a carousel. It
  invents nothing — the chart plots `series` as given and draws no line without it. `uiCardRects(W, H)` gives
  back the rectangles it will draw, so a camera can aim at "the third card" instead of at a number written
  twice. `PageCam2D` moves a lens over a page bigger than the frame, and — the half that matters —
  `pageToScreen(cam, ...)` says where a page point LANDED, so a cursor, a label or a ripple can be ordinary
  DOM welded to the thing it points at. `clampToPage` keeps a close-up from showing the void beside the page.
  Worked examples: `SurfaceCarousel` (a queue of screens) and `PointerTour` (one screen, one camera, a cursor
  walking it).

- **PHYSICS instead of a curve — `springAt` / `useSpringAt` in `runtime/motion.ts`.** An eased ramp always
  arrives; a spring OVERSHOOTS and settles, which is what reads as weight. Three presets name the three jobs:
  `SPRING_LAND` (something arriving), `SPRING_SEAT` (something taking its place in a row — heavier, less
  overshoot), `SPRING_POP` (something appearing — sharp, deliberately past 1.0). They are driven by `useT`'s
  window, not by the raw frame: `useAnimSpan()` is how many frames the shot's own 0→1 actually spans, so a
  spring is settled across the frames the cross-dissolve runs over, exactly like every eased register. Use the
  pure `springAt(t, span, fps, delay, config)` inside a stagger loop — hooks cannot be called per item.
  Worked examples: `SourceDeal` (pills dealt onto a rail) and `PortRail` (modules seating into a frame).

- **DEPTH as a signal — `runtime/focus.ts`.** `focusAt(distance, U)` returns the one recession every shot
  should share: opacity, blur, brightness and scale together, because a neighbour that is paler but just as
  bright reads as translucent rather than as further away. `focusFilter(f)` returns `undefined` when the thing
  IS in focus — never `blur(0px)` — so sharp type is not promoted to its own compositing layer and resampled.
  The blur is a fraction of the frame's short side, not a literal: the 2.2px that looks right on a 480-wide
  design stage is invisible at 1920. `focusDist(dist, spread)` normalises a distance and returns 0, not NaN,
  when a shot has only one object. Worked example: `SurfaceCarousel`'s corridor.

- **The FILM'S OWN VOICE — `runtime/voice.tsx`.** `<Voice samples={n}>{({bars, level, live}) => …}</Voice>`
  hands a register the beat's real narration, analysed with `@remotion/media-utils`: `Film.tsx` provides the
  scene's mp3 through `NarrationContext`, so nothing has to be authored per beat. It is a render prop and not
  a hook because `useAudioData` throws on a falsy src and hooks cannot be conditional — standalone stills and
  the energy sweep have no narration and get a deterministic SYNTHETIC voice with the same shape, gaps
  included. Levels are normalised against the CLIP's peak, so silence reads as silence and a 20 dB quieter
  recording draws the same picture, and tilt-compensated across frequency the way any spectrum analyser
  is — without that, a voice's rolloff draws three tall bars and a flat line, which is a bass meter, not
  a picture of speech; a per-frame normalisation would make a pause as tall as a shout, which is
  precisely how `VoiceSignal` spent months claiming to be audio-reactive while drawing three sines of the
  frame number. Worked examples: `VoiceSignal` (a mirrored bank) and `SpectrumPulse` (a ring).

- **Content ATOMS — the same part, a different form per DNA.** Colour tokens make a themed film coherent;
  they do not make a register *look like another style*, because the components stay identical. The atoms
  close that gap: `runtime/atoms.tsx` exports `Bar`, `Figure`, `List`, `Label`, `Divider`, `Marker`, and
  the DNA declares which FORM it speaks for each (`dna.atoms.bar: 'block' | 'solid' | 'ruled' | 'pixel' |
  'dimension'`). A shot writes `<Bar value={0.88} label="Alpha" tag="PASS" />` and never names a form —
  the same declaration renders as `████░` on a terminal system, a ruled scale on an editorial one and a
  dimensioned measure on a blueprint. Every atom resolves its form in ONE order, TOTAL and never throwing:
  **the DNA's own declared form for that atom → `fallbackForm` → the atom's NEUTRAL form.** A DNA that
  declares a form always wins — `fallbackForm` only fills the gap when the DNA has no opinion. It exists so
  a **migrated** shot can keep its OWN pre-atoms look (`TermCounter` passes `fallbackForm="mono"`, `EdStat`
  `"serif"`) under a truly un-themed film, without weakening a themed DNA's authority over an un-migrated
  shot — a shot that never passes `fallbackForm` reaches the atom's plain neutral form under no DNA, same
  as before atoms existed. `fallbackFamily` is `fallbackForm`'s typeface counterpart on `Figure`, needed
  only because `NEUTRAL_DNA`'s own face doesn't always match a migrated shot's original one. They are also
  PURE (no remotion hooks; anything time-varying, a count-up or a blink, stays in the shot and arrives as a
  value or a `phase` prop, so the atom cannot break a shot's timing). Use them for a new shot's bars,
  figures and lists. They are NOT for the generative, 3D, fluid and illustration registers — a metaball
  field does not decompose into bars, and forcing it would destroy what makes it that register.

  In practice only `Figure` and `Bar` found real consumers. Four shots draw their headline number through
  `Figure`: `TermCounter` (the `mono` reference), `EdStat` (the `serif` reference), `ChartLive` (its
  headline metric only) and `VelocitySnap`. `Bar` has one shot, `TermBars`, which is its own `block`
  reference implementation and has no other consumer. `List` has no consumer at all in the current
  library. Six shots were deliberately NOT migrated, each kept whole rather than damaged to fit:
  `OdometerRoll` (its mechanical digit reel IS its design language), `GaugeCluster` (a 270° arc, not a
  bar), `BeforeAfterSlider` (its little column chart is decorative furniture inside a mock slide, not the
  shot's content atom), `TermTree` (a columnar `ls` listing whose items are padded to a name column, not a
  list), `ChartRace` (reverted during review: the atom contributed only a rectangle while label, value,
  position and ranking stayed in the shot, and the migration cost it its gradient and leader glow under
  every DNA) and `BlockAssembly` (reverted during review: `List` per row contributed nothing but a
  `display:flex`, which turned its strike-through rule pure black). The governing principle: **an atom must not damage the
  register it is applied to.** Reach for the atoms when a shot's part really is a quantity, a figure or an
  enumeration; leave a register whole when its form IS its meaning.

  **The null-DNA colour test cannot see this defect class.**
  `tests/test_remotion.py::test_null_dna_preserves_every_original_colour` checks only that a shot's
  original hex colours are still REACHABLE in its source. It cannot see a lost gradient, a lost
  box-shadow, changed spacing, a changed typeface, a changed size, or an element that was added or
  removed. Every one of the five Critical defects found while migrating shots onto the atoms passed that
  test. So: **when you migrate a shot onto an atom, render it with NO `template` and NO `dna` at all, and
  compare against the same shot before your change — and do it with non-default props**, because a default
  that happens to be empty (an empty `unit`, an empty label) hides the very layout the atom changes.
- **Ground luminance is a RUNTIME property, and WHICH TOKEN carries it is MEASURED.** Captions contrast-pick
  against the frame's ground and the seam guard judges cuts on it, so the measured `SHOT_LUMA` constant — the
  shot on its OWN palette — is only half the answer. `runtime/shotLuma.ts` exports `DNA_GROUND_TOKEN`: which
  DNA token (or which PAIR, for a gradient flood) each register paints its ground from, read off 160 renders
  under a probe DNA by `scripts/measure_ground_luma.py`. `dnaGroundLum(shot, bgLum, dna)` and `dnaGroundY`
  resolve through it. **Change a register's GROUND and re-run `python3 scripts/measure_ground_luma.py
  --check`** — the table is a claim about pixels, and a claim nobody re-measures is a declaration.
  (Its predecessor `gen_dna_ground.py` is RETIRED and exits 2. It wrote a BOOLEAN "grounds on the DNA", which
  was read as "…so its luminance is luminance(dna.bg)" — false for KineticManifesto's accent flood, which
  therefore reported DARK while rendering BRIGHT and got a seam gap of zero across a measured 20.8 -> 149.3
  jump.)
- **A GROUND THAT IS NOT A DNA TOKEN IS WRITTEN AS A LITERAL, and then your ink cannot come from the DNA
  either.** A register may refuse the film's ground — `PaperSlot` prints on its own `#efe9dd` stock unless
  `dna.bg` is light enough to pass for paper, and all eight shipped presets are dark. Declare that in
  `DNA_GROUND_TOKEN` as the colour (`PaperSlot: '#efe9dd'`), not as `'bg'`: declared `'bg'`, the caption HUD
  resolved the film's near-black and drew #ffffff on that paper at **1.22:1**, and the register's own title
  took `dna.fg` — a LIGHT ink chosen for a dark ground — at **1.19:1**. Both from the same slip: the flag
  that decided the ink asked "is the paper light?" (true in both branches) instead of "did we ADOPT the
  film's ground?". And never ink text with a token your own ground is painted from — `KineticManifesto`
  floods `accent -> accent2` and set its hero word `accent2`, which is 1.00:1 exactly where the gradient
  reaches it. `tests/test_remotion.py` asks that of all 160 registers, using the measured table.
- **`python scripts/dna_smoke.py [--template <direction>]` renders EVERY registered shot once, in one film.** Static
  tools cannot see a hook inserted into the wrong SCOPE (`dna is not defined`), and the bundler strips types without
  checking them; only a render catches it. Run it after any bulk shot change, and under at least two DNAs.
- **Consistency ≠ repetition.** The DNA does NOT make every frame a terminal window — a metric/chart/diagram beat
  inherits the type + palette + motion + 2–3 cues, it does NOT become a black-green box. Record the cues in
  `shot_adaptation.theme_cues`; **shot-critic S11** audits per-frame coverage + the FINAL TEST (remove the obvious
  themed shots — can a viewer still infer the design language? if no, the DNA hasn't propagated deeply enough).
- **TWO UNIVERSAL mechanisms carry the DNA across EVERY shot with no per-shot edits (Film.tsx) — use these before
  hand-editing 100 registers:** (1) **Global type** — Film injects `.dna-film * { font-family: <dna.fontMono>
  !important }`, so a terminal film reads as MONOSPACE everywhere (overrides each shot's inline font-family, keeps
  size/weight; scoped so captions keep their own font). Mono is the single strongest terminal signal and needs
  ZERO per-register work. Do NOT try to swap fonts per-shot via a `${UI}` const — it breaks in a shot's nested
  sub-components (they don't see the const → ReferenceError; see §C3 for the CSS-variable mechanism that carries a
  MIXED-type style's `fontDisplay`/`fontBody`/`fontMono` per-shot with no such scope problem). (2) **Terminal chrome** — a per-scene
  `chrome:{path,status}` frames each beat with a command-path breadcrumb (top-left) + a live status + caret
  (top-right) via `runtime/dna.tsx` `TerminalChrome` (rendered by Film in each Sequence, inert unless the DNA has
  `breadcrumb`). Author a DISTINCT path/status per beat (`~/hermes ▸ eval/tools` · `● 90% / 84%`) so it's the "one
  terminal session" frame, NOT a repeated decoration. Per-register token migration (bg/accent) then only has to
  handle the shot's OWN salient colours; type + chrome are already global.
- **THE THREE-LAYER MODEL — style is a GRAMMAR, not a layout template (this is the #1 trap).** The failure mode
  is BOTH directions: too weak = reskin the original component (a gauge tinted green); too strong = make EVERY
  frame the same explicit terminal WINDOW (a black panel with `● ● ●` + `$ cmd` + a box). Both are wrong. Split
  the style into three layers: **(1) Surface** — only 2-3 ANCHOR beats show an explicit terminal window (a boot,
  a code editor, an ending `$ ready_`). **(2) Visual grammar (the important one)** — EVERY other beat inherits the
  terminal DNA *without* a window box: mono type, a `$`/`❯` command line, cursor `▋`, `~/ ./ [01]` syntax, tree/
  indent/`-`/`+`/box-drawing, CLI status — on the OPEN dark canvas, with a layout chosen PER CONTENT (a hero
  number on void, an open bar readout, an open diff, an open timeline), so beats don't all look the same. **(3)
  Motion grammar** — reveal via `command → execute → result`: a `$ eval` line types + runs, THEN the figure/chart/
  diagram grows out as the OUTPUT (the output need NOT be in a box). The shared `runtime/dna.tsx` **`TermFrame`**
  implements this: `framed` = the explicit window (anchors only), default = OPEN (typed command line → result on
  open canvas). A terminal-native shot uses `TermFrame` and provides its content; DEFAULT to open. **The motion
  layer also lives in the SEAMS + the reveal CHARACTER (built in Film.tsx / dna.tsx):** an UNMARKED cut becomes the
  DNA's native action via `dnaDefaultSeam` (terminal → a `screenClear` — a bg dip + an accent scanline sweep, i.e.
  the console redrawing; product → a push; editorial/blueprint → a page/sheet wipe), luminance-safe, with explicit
  chapter marks still winning; and `dna.motion` (`type`/`execute`/`smooth`/`mechanical`) sets the reveal CHARACTER
  (terminal results POP out, product eases, blueprint steps). So a themed film's cuts + reveals belong to its
  world, not a generic fade — the analogue of the surface/grammar split, for TIME.
- **STYLE ASSIMILATION gate (run per shot before implementing).** Take the shot's content idea and deliberately
  TRANSLATE it into the active DNA across ≥2-3 of: typography · layout (style logic, not a generic slide) ·
  components (panels/labels/dividers/status primitives) · motion (enter/transform per the motion grammar) ·
  transition · narrative metaphor (can the content be *expressed through* the design concept?). **Reject any shot
  that could be dropped unchanged into a completely different style without anyone noticing.** Consistency does
  NOT mean every frame looks the same — it means every frame FEELS designed by the same system.
- **THIS ALL GENERALISES TO ANY STYLE — terminal is just the worked example.** The pipeline is style-agnostic:
  *pick a template → extract its DNA → design each shot for its CONTENT → assimilate the shot into the DNA
  (three-layer: a few explicit "container" frames, the rest inherit the grammar on open canvas, motion reveals
  as the style's native action) → validate (S11 + the reject rule).* Only the REALIZATION differs per style:
  - **DNA tokens** — `runtime/dna.tsx` ships presets for `terminal` · `editorial` · `product`/`apple` ·
    `blueprint` (+ `neutral`); `dnaFromTemplate` maps a `shot_template` to one, or author `meta.design_dna`
    explicitly. `uniformType:true` (terminal) → Film forces one font; a MIXED-type style (editorial serif+sans)
    leaves it off and registers pick `fontDisplay`/`fontBody` per element.
  - **Surface container** — terminal's is `TermFrame` (a window / an open `$` command line). Another style's is
    its own: editorial = a kicker + hairline rule + column; product = a glass hero panel; blueprint = a
    crop-marked drawing sheet. Use the explicit container on only 2-3 anchor beats.
  - **Session chrome** — terminal's is `TerminalChrome` (a `~/path ▸` breadcrumb, gated on the DNA's
    `breadcrumb` decoration so it's inert for other styles). Another style may have its own persistent frame
    element (a running header / a page-number) or none.
  - **Style-native component family** — a small set of shots that rebuild "the metric / list / lineage / contrast
    idea" natively in the style. TWO families ship as worked exemplars, and they are the pattern to copy:
    - **terminal → `Term*`** (TermBars/Tree/Log/GitLog/Think/Counter/Table/Diff) on `TermFrame` — a value counts up
      as a command *executes*, a list is a `tree`/`ls`, a diff is `+/-` gutters.
    - **editorial → `Ed*`** (EdStat / EdTimeline / EdCompare) on `EdFrame` — the SAME ideas as a magazine feature:
      a pull-stat is a huge serif figure + kicker + rule; a lineage is a ruled dated chronology; a contrast is a
      two-column spread with a dimmed foil vs a hero column. Reveals *ease* (never type/execute).
    Building a new family = the same recipe: one `<Style>Frame` (its surface + open-canvas grammar + DNA-keyed
    reveal character) + 2-4 shots reading `useDNA()`, each the native rebuild of a content shape — see EdStat/
    EdTimeline/EdCompare (`src/shots/Ed*.tsx`) as the reference implementation. A **display shot that shows a big
    number must be WIDTH-AWARE** (size the figure by its final string length; EdStat learned this when 5,000,000
    ran off-frame) so it holds for real values, not just the short demo default. For a style with NO family yet,
    build one this way OR use the library registers reading the DNA tokens + the three-layer discipline — never a
    reskinned generic component (that fails the reject rule).

## C3 · Type — a shot's face comes from the DNA, never a bare family name

Every one of the eight Design DNA directions declares its own `fontDisplay` / `fontBody` / `fontMono` — real,
loaded typefaces, distinct per direction (an editorial serif display + text-serif body reads nothing like a
terminal all-monospace system or a blueprint technical-grotesque). `Film.tsx` publishes them as three CSS custom
properties, scoped to `.dna-film`, **only when a DNA is active**:

```css
.dna-film { --f-display: <dna.fontDisplay>; --f-body: <dna.fontBody>; --f-mono: <dna.fontMono>; }
```

**A shot must read its face through the variable, never write a bare family name:**

```tsx
font: `800 200px/0.9 var(--f-display, Inter, system-ui, sans-serif)`
fontFamily: 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)'
fontFamily="var(--f-body, Inter, sans-serif)"   // JSX/SVG presentation attribute — var() resolves here too
```

**There is a SECOND sanctioned mechanism, and 14 shots use it instead.** A shot that already calls
`useDNA()` may read the face directly in JS — `const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif'`
— and interpolate it. The `Term*` family (8 shots), the `Ed*` family, `SwissEditorial`, `CinematicTitle`
and `ConveyorBelt` all do this, with zero `var()`. It is equally valid: `dna_audit.py --type` counts both
toward reach, and the regression test is named
`test_every_shot_reads_the_type_variables_or_the_dna_directly` precisely because either satisfies it.

Which to use: reach for the **variable** when the shot does not otherwise need the DNA object — it needs no
hook, no import, and no component-scope reasoning. Reach for the **direct read** when the shot already holds
`dna` and wants the face in JS (to measure it, to branch on it, or to pass it into a helper). What is NOT
allowed is the third option: a bare family name that reads the DNA not at all.

The text after the comma is the **fallback list** — the shot's own original hardcoded family list, unchanged.
With no DNA active the variable is unset and the declaration resolves to exactly what an un-themed film rendered
before this layer existed: this is what makes the no-regression claim pixel-checkable (`scripts/
null_dna_pixel_gate.py`, 27 shots, currently passing), not merely asserted. Never drop the fallback list to save
characters — it is the shot's entire un-themed identity.

**A `uniformType: true` DNA (`terminal`) overrides all three variables by design.** Its global rule,
`.dna-film, .dna-film * { font-family: <dna.fontMono> !important; }`, beats any `var()` inside a `font`/
`fontFamily` value — so a terminal film is all-monospace regardless of what any individual shot's variable would
otherwise resolve to. This is intended (terminal's whole identity IS one uniform face) and means a terminal render
is a poor choice for VISUALLY verifying that the `--f-*` variables themselves are wired correctly — pick a
MIXED-type direction (`editorial`, `blueprint`, …) for that check instead.

**Four shapes actually carry a font family in this library — a shot may use any of them, but each must resolve
through a variable:** the `font:` shorthand (single-, double-, or back-quoted), the `fontFamily:` CSS property, the
JSX/SVG presentation attribute `fontFamily="…"` (17 shots / 62 declarations — `var()` resolves there too, confirmed
on a real `npx remotion render`), and a module- or function-level `const` interpolated later (`const MONO =
'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)'`, then `` font: `600 24px/1 ${MONO}` `` — the `var(--f-`
must live INSIDE the const itself, since a codemod or reviewer scanning for `${` treats the interpolation site as
already-dynamic without ever looking at what the const holds). A per-letter randomized font array
(`AntiDesignChaos`, `RansomZine` — each letter of a maximalist/ransom-note collage deliberately picks a different
typeface) is the one legitimate exception: it must stay dynamic and is never wired to a single `--f-` variable.

**Tooling:** `scripts/font_gate.py` (every declared face actually loads, not a silent fallback to its generic),
`scripts/dna_migrate_type.py` (the codemod that rewrote 355 declarations across ~122 shots onto these variables),
`scripts/null_dna_pixel_gate.py` (proves an un-themed render is pixel-identical before/after), `scripts/
type_specimens.py` (renders a per-direction specimen sheet for a human to confirm the eight directions actually
read as different typographic systems, not just different colours), and `scripts/dna_audit.py --type` (per-role
reach report — how many of the 134 shots read `--f-display`/`--f-body`/`--f-mono`, the same tracked-metric
discipline `dna_audit.py`'s DNA-awareness report already uses). `tests/test_remotion.py::
test_every_shot_reads_the_type_variables_or_the_dna_directly` is the regression gate: it checks all four shapes
above, not only the `font:` shorthand, so a future edit that reintroduces a hardcoded family in ANY of them fails
the suite.

## D · Selecting the direction — show VIDEO samples, not text or a single still

A direction is defined by its MOTION and feel; a text pitch (and even a single still) can't convey it — the user
must SEE it move. So the contest surfaces a short **sample video per direction**:

```
python scripts/contest_sample.py --route "<topic>" --audacity <a> --out <out_dir>   # builds a mini-storyboard per direction
# then render each printed command → <out_dir>/_contest_<key>.mp4 (a ~6s narrated-silent sample of that direction's look+motion)
```

Each sample sequences that direction's hero + a couple of representative registers, carrying the TOPIC copy, run
through the real `Film` (real transitions, captions, motion). Montage/present the samples via `AskUserQuestion`
(winner first, "(Recommended)"), let the user PICK from what they can actually watch, then record
`meta.shot_template` + `meta.shot_template_contest` as before. A single still remains the cheap fallback only when
the Node render budget is tight; default to samples.


## Icons — the default for category content, not a garnish

This tier had none. A register with a list drew an abstract mark per row — QuadSplit's `bars`/`ring`/
`dots`/`wave`, CardStack3D's numbered chip — and the mark was chosen by INDEX, so the same shapes appeared
in the same order on every film whatever the labels said. A viewer reads 「开表格」 beside a ring and learns
nothing from the ring. That is furniture that happens to be on the frame.

`runtime/icons.tsx` is one coherent line family — same 24-unit grid, 2-unit stroke, round caps as the html
tier's set, so a film reads as one identity system across both. Import `Icon` and `IconName`; an unknown
name THROWS, because a silently-missing icon leaves a hole the layout still reserves.

**The rule, carried over from `references/icons.md`:** an icon must answer **what is this · what does it do ·
why pay attention** BEFORE the viewer reads the text. If it answers none, cut it. Pick by the ROLE the row
plays, not by the picture its word suggests.

**Icons are the DEFAULT for a labelled list**, so their ABSENCE is what needs a reason. `shot_proof` warns
on a labelled list of 2+ entries passed to an icon-capable register with no `icon` on them. The reasons that
survive that warning are categorical, not "it looked fine": a headline FIGURE is the focal point and an icon
beside it competes; a motif-dominant frame where the register's own form is the content; a frame where the
icon would be larger than its title. Never emoji.

Which registers can take one is READ from the source — a register that imports `runtime/icons` is
icon-capable — so wiring a new one brings it under the gate the same day.

## E · The gates still bind

None of the above relaxes the floor. Before delivery: `validate.py` (structure/faithfulness), `check_av.py`
(A/V sync), `keyframe_qa_remotion.py` (no blank frames), `text_safe_qa.py` (no type cut by the canvas — note it can only see ink that EXISTS; for a string
the register declined to draw at all, `cjk_type_qa.py --all-aspects` is the only audit that reports it),
`film_energy_qa.py` (the film moves, is dense, and has light — floors from four measured launch films;
`frame_safe_qa.py` is advisory only), and
the shot-critic (S1–S11). Meaning + frame-craft (S10), direction-adherence (S7), and design-system coverage
(S11 — the Design DNA runs through EVERY frame, per §C2) are gates, not nice-to-haves. `validate.py` also warns
when a themed film has no `design_dna`/preset or a scene has no `theme_cues`.

## Before you commit a change to this library — walk the case law

`references/engineering-case-law.md` is the E-numbered case law for whoever EDITS the renderer, the runtime
or a gate: each rule is an executable sentence, the commit that repaired the incident behind it, and a
question you can only answer by looking at something. It is the engineering half of what
`agents/shot-critic.md` is for a finished film, and it exists because this repository's hardest-won
knowledge lived in its commit messages, where no reviewer walks it.

Walk the rules your change touches and report `En ✓` / `En ✗ (where)`. A deliberate violation is written
down, not silently taken. The rules the register work below runs into most often are **E1** (a reserve is
arithmetic about a layout the browser performs), **E2** (an advance is a property of the face), **E8** (a
constant where a measurement belongs) and **E12** (render it and look).

## Width is a constraint, not a given

Twenty-three registers cut type at 9:16 because a size was chosen for the text and the frame it was authored
on. The rules that came out of fixing all of them:

- **Fixed px is a bet on one frame.** Derive from `W` (and the content zone) or wrap in
  `Math.min(authored, fitted)`. `layout.ts` has the primitives: `fitTextPx(text, W, base, {track})` for a
  display line (CJK counts at full width; tracking counts), `bottomInset`/`bottomTextY` for closing lines,
  `contentBottom`/`CONTENT_TOP` for the zone.
- **Stack when the side room is gone, and decide by the ROOM, not by naming aspects**
  (`const under = W - (panelRight + gap) < needed;`). A portrait frame is tall exactly where it is narrow.
- **The face that renders is the DNA's font, not your fallback stack's** — never tune an advance to a face
  the film will not ship.
- **Scale a composed scene as a whole** (IsometricAssembly, BlockAssembly) rather than nudging one element
  away from the group it belongs to — and MEASURE the scene's extent off a render before scaling; two
  guessed extents cost real density before the ruler came out.

## `t` is not seconds

`useT()` returns 0→1 across the whole clip. Every constant written against it is therefore a TOTAL, not a
rate, and this is the single most repeated defect in the library — nine registers shipped an oscillator that
never completed one cycle, each authored as "this keeps breathing" and each rendering as a slow one-way
drift.

- **A period goes in SECONDS**: `radians(t, durationInFrames, fps, periodS, phase)` for an angle,
  `life(t, durationInFrames, fps, periodS, phase)` for a 0→1 modulator. Both throw below a 3s period, so a
  caller cannot tune their way into a vibration.
- **`clamp01(t * k)` is fine** — a saturating fade-in is a reveal, not an oscillator.
- **Run `python3 scripts/clock_qa.py`** after adding a register. It cross-references the scan with the
  measured sweep, so it names a symptom and a cause together.
- **Correcting a clock is a fidelity fix, not a motion fix.** Where the driven element is small the measured
  motion barely moves; render before and after and revert the edit if the number does not.

