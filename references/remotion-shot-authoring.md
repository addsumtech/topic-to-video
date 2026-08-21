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

`frame_safe_qa.py` backstops #1–#3 partially (edge-bleed + palette-outlier); the rest — especially #8's overflow/
collision/tiny-marker — are eyeballed by the shot-critic (S10). Getting them right structurally (via `layout.ts`
+ sizing for real content) is cheaper than being caught.

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
  topic. Credit CC-BY on screen.
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
  them. **C — rebuild:** only when the structure fundamentally clashes (a serif cinematic flare, a chrome word) —
  restyle it into the DNA (e.g. mono title + green-tinted chrome) or swap to a DNA-native register. **Watch for a
  TDZ:** put `const dna = useDNA()` + any derived palette BEFORE the first use (a `const NODES = …PALETTE…` above
  it breaks).
- **Consistency ≠ repetition.** The DNA does NOT make every frame a terminal window — a metric/chart/diagram beat
  inherits the type + palette + motion + 2–3 cues, it does NOT become a black-green box. Record the cues in
  `shot_adaptation.theme_cues`; **shot-critic S11** audits per-frame coverage + the FINAL TEST (remove the obvious
  themed shots — can a viewer still infer the design language? if no, the DNA hasn't propagated deeply enough).
- **TWO UNIVERSAL mechanisms carry the DNA across EVERY shot with no per-shot edits (Film.tsx) — use these before
  hand-editing 100 registers:** (1) **Global type** — Film injects `.dna-film * { font-family: <dna.fontMono>
  !important }`, so a terminal film reads as MONOSPACE everywhere (overrides each shot's inline font-family, keeps
  size/weight; scoped so captions keep their own font). Mono is the single strongest terminal signal and needs
  ZERO per-register work. Do NOT try to swap fonts per-shot via a `${UI}` const — it breaks in a shot's nested
  sub-components (they don't see the const → ReferenceError). (2) **Terminal chrome** — a per-scene
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
  open canvas). A terminal-native shot uses `TermFrame` and provides its content; DEFAULT to open.
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
  - **Style-native component family** — terminal ships `Term*` (TermBars/Tree/Log/GitLog/Think/Counter/Table/
    Diff) as the exemplar of "the metric/list/lineage/contrast idea, rebuilt in the style." For a style with NO
    family yet, either build one the same way, OR use the library registers reading the DNA tokens + the
    three-layer discipline — never a reskinned generic component (that fails the reject rule).

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

## E · The gates still bind

None of the above relaxes the floor. Before delivery: `validate.py` (structure/faithfulness), `check_av.py`
(A/V sync), `keyframe_qa_remotion.py` (no blank frames), `frame_safe_qa.py` (edge-bleed + palette outlier), and
the shot-critic (S1–S11). Meaning + frame-craft (S10), direction-adherence (S7), and design-system coverage
(S11 — the Design DNA runs through EVERY frame, per §C2) are gates, not nice-to-haves. `validate.py` also warns
when a themed film has no `design_dna`/preset or a scene has no `theme_cues`.
