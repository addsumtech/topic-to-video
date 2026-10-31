# Remotion tier: any drawing style, film-wide — design

## Why
A user asks for a film "in a cartoon style", "like Kurzgesagt", "水墨风", "Ghibli-like". Today the remotion
tier can only answer with a handful of craft registers (HandDrawn, CartoonPop, HalftonePop, ClayStack,
PaperCutout, PixelBuild, RisoPrint, ComicPanels, InflateType, ElasticType, …). Most of them carry a title, not
content, and CartoonPop is product-locked. Every other beat keeps its own drawing and only takes the film's
colours from the DNA.

The DNA (`runtime/dna.tsx`) controls faces, colours, radius, border width, motion personality, decoration,
atoms, motif and finish. It has **no axis for how things are drawn**: line weight, outline, fill mode, shading,
line wobble, texture, animation stepping.

Measured on the 218 shot files (2026-10-31): all 218 read the DNA, but
- 134 write raw `<svg>`;
- 111 set stroke widths themselves;
- 148 hand-roll CSS gradients;
- 72 hand-roll shadows;
- only 19 go through the shared line module (`runtime/draw`).

So there is no single choke point today. Retrofitting registers one style at a time never finishes, and the
next new register would miss it again.

The user's requirement is not a longer style catalogue. It is a **mechanism**: a style the skill has never
seen gets decomposed and applied to every beat and every object, so that next time a user names a new style,
the skill can still do it.

## Decisions (made with the user, 2026-10-31)
1. **General mechanism, not a catalogue.** Cartoon may be tuned as the first case, but nothing may be built
   that only cartoon can use.
2. **Input.** A user gives a style name or description, sometimes reference images or a reference video.
   - With a name only, the skill finds references itself.
   - When the user gives references, the references win over anything the skill found.
3. **How the style is rendered: code first, AI only for texture.**
   - Objects, text, numbers and charts stay code-drawn, so they stay accurate and editable.
   - A style layer controls line, fill, shading, texture and motion.
   - Painterly styles (watercolour, impasto, Ghibli backgrounds) may get an AI-generated texture: paper,
     brush, a backdrop surface. Generation uses the Codex subscription.
   - Without image generation, a procedural texture is used, and the shortfall is **stated** at sample time.
   - A paid image API needs the user's explicit permission for each run (standing rule).
4. **Failure = recolour only.** The user's words: "只换了配色，画法和线条还是原来的样子". Equally a failure (my
   addition, accepted with the direction): some beats restyled and others not, so the film's drawing is
   inconsistent.
5. **Scope: the style layer only.** There is no character system (rigged figures, expressions, walk cycles) in
   this project.
6. **Mandatory style sample.** Every film with a style shows the user 2–3 sample beats beside the references
   **before** the full render. The full render waits for their approval.

## Goals
- A style the skill has never seen becomes a **style spec**: fixed axes, values filled per style.
- One **style engine** applies the spec to every beat at render time, without per-register code. It covers
  the 218 existing shots, workshop objects and future registers.
- A **style gate** measures on rendered frames that the drawing changed as the spec says, and the same way
  across beats. It must catch a recolour-only render.
- A **style sample** step that produces the sign-off sheet and records the approval.

## Non-goals
- A character system.
- The HTML tier. It may reuse the spec later; that is not part of this project.
- Restyling real photographs. Evidence images (PhotoPlate, RealVersus, ScanReconstruct, MuseumLabel, …) are
  the argument, so they are never repainted. They may take the style's frame, border and grade only. *(My
  call; see "Calls I made".)*
- New per-style registers. A style that needs a register to look right means the engine is missing an axis.
  That is recorded as a shortfall, not patched per film.
- AI-generated content. No generated object, diagram, text or number, at any style.

## Anti-goals (works technically, still a failure)
- Only the colours change.
- A style that wobbles, posterizes or textures the **text** until it reads worse. Captions are never
  restyled. Body text is never wobbled, posterized or textured.
- A style that breaks an object's fidelity: a part missing, a part detached, teeth merged into a blob. A style
  may simplify detail and round forms, but the parts and their mounts survive.
- "Exaggeration" applied to facts. Proportions shown as data, counts and numbers are never exaggerated. Only
  silhouettes and motion may be.
- A film with no style behaving differently from today.

## Constraints
- **No `meta.style` → byte-identical render to today.** This is the same null rule as the DNA.
- **Deterministic and seekable.** Every effect is a pure function of the frame. Wobble and boil seeds come from
  the frame via `boilPhase` (`runtime/draw.ts`), never from a clock or `Math.random`.
- **Every existing gate keeps working on the styled render:**
  - text safety, caption contrast, cjk type, keyframe/frame-safe, media resolution (a generated texture is a
    raster: it must meet `media_res_qa`);
  - fidelity sheets, run on the styled render;
  - jitter. Boil is intentional motion of LINES. jitter_qa must not flag it on non-text ink, and must still
    flag any movement of text. Text is exempt from boil, so a jitter finding on text under a style is a real
    defect.
- **Measurement manifests** (ground luma, ground reach, energy, prop reach) are register properties measured
  unstyled. The engine must not invalidate them. If a style changes what they measure in a way that matters
  (energy of a texture overlay, say), the style gate says so; the manifests are not re-measured per style.
- **Cost.** A library-wide sweep costs tens of minutes. Batch runtime changes and sweep once at the end, not
  per change.

## The design

### A. The style spec (`meta.style`)
A fixed set of axes. A new style fills new values; a new style never adds code. Values are in units the
gates can measure. Px are stated at a 1080 px short side, like the other gates.

```
style: {
  name, refs: [{src, from: 'user'|'found', credit?}], notes,   // provenance
  line:    {weight, variance, color, outline, join, wobble, boil_hz},
           // weight px; variance 0..1 = taper/pressure; color 'ink'|'fill-dark'|hex|'none';
           // outline 'none'|'outer'|'all'; wobble px amplitude; boil_hz 0 or 6–12
  fill:    {mode: 'as-drawn'|'flat'|'cel'|'texture', steps, texture},
  shade:   {mode: 'as-drawn'|'none'|'cel'|'soft'|'hatch', light},
  shadow:  {mode: 'as-drawn'|'none'|'hard-offset'|'soft', offset},
  form:    {corner, simplify},          // corner radius scale; simplify 0..1 (detail drop, never parts)
  surface: {kind: 'none'|'paper'|'canvas'|'brush'|'grain'|..., strength, source: 'procedural'|'generated'},
  type:    {display: 'as-dna'|<face>, display_outline},        // body and captions are never restyled
  motion:  {stepping: 1|2|3, easing: 'as-drawn'|'overshoot'|'snappy'|'floaty', squash},
  shortfalls: [{axis, wanted, got, why}]                        // what the engine could not do, stated
}
```

The exact axis list and value sets are the builder's to finalize. The rule that is fixed: **the axes are
general drawing properties.** None is named after a style ("cartoon": no; "line.outline: all": yes).

If a style needs a drawing property no axis has, that is an engine change, made once for every style and
recorded with its reason. It is never a per-film workaround.

`scripts/style_spec.py` validates the spec. validate.py ERRORs on an unknown axis or value, and on
`meta.style` without `refs`.

### B. Decomposition (agent step)
A new step in the remotion pipeline, before the shot-director, run by the design-director:
1. Gather references.
   - User-given references win.
   - Otherwise search (web, Commons) for 4–8 frames that typify the style, and record the source of each.
2. Write the spec. Every non-default axis value cites what in a reference it was read from ("outline: all —
   every shape in refs 1–3 has a closed dark contour, ~4 px at 1080").
3. Pick the DNA palette and faces to match the references. The existing DNA machinery is unchanged.

The agent prompt (`agents/design-director.md`) and a reference page (`references/style-engine.md`) carry the
procedure and the axis meanings with pictures of each axis value.

### C. The style engine (`remotion/src/runtime/style.tsx`)
Mounted in `Film.tsx` around each beat's register layer. It sits inside the DNA scope and under
`FilmFinishLayer`, next to the existing `.dna-film` font override, which is the precedent for a film-wide CSS
override. The engine acts on what every register finally draws (SVG shapes, CSS boxes, gradients, shadows,
text), not on register code. Four mechanisms, used in this order of preference:

1. **Scoped CSS** for what CSS can override: stroke width, colour, join; box-shadow; border radius; borders
   as outlines.
2. **A deterministic DOM pass** for what CSS cannot reach (inline styles, SVG presentation attributes,
   gradients):
   - flatten a gradient to one colour, or quantize it to `fill.steps` bands;
   - add outlines to filled shapes;
   - classify each element: text, image, canvas, or shape. Text is exempt except display type; images are
     exempt (evidence); canvas is filter-only.

   It runs per frame before capture and must leave the DOM gates (textSafe, labels) measuring the same
   geometry.
3. **SVG filters on the shape layer** for what is per-pixel:
   - line wobble and boil: `feTurbulence` + `feDisplacementMap`, seed from `boilPhase`;
   - posterize for cel shading;
   - an edge-outline fallback for shapes the DOM pass could not outline.

   Text is lifted out of the filtered layer, or the filter is masked off text, so text never wobbles.
4. **A surface layer**: a procedural texture (`feTurbulence` paper or canvas), or a generated tile blended
   over the ground and fills. It follows `surface.kind` and `strength`.

**Motion.**
- `stepping` is film-wide: `BeatClock` quantizes the beat's frame to every 2nd or 3rd frame ("on twos").
  Camera and seams stay on ones unless the spec says otherwise.
- `easing` and `squash` reach registers through the shared motion helpers (`runtime/motion`, `glide`,
  `springAt`). Registers with hand-rolled easing get stepping only. The coverage report says which.

**Deeper hook and exemption.** A register may export `STYLE_HOOKS` (it draws its own version of an axis) or
`STYLE_EXEMPT` (with a reason: canvas, evidence). Today that is 2 canvas shots and 18 shots with images. The
engine reports, per film, which beats each axis reached.

**Workshop objects** are SVG and go through the same engine. The fidelity checks (part outlines closed,
mounts touching) run on the styled render.

### D. The style gate (`scripts/style_qa.py`)
It runs on settled frames (~90%, per the settled-frame rule) of every beat, rendered styled and **unstyled**.
For each axis the spec sets, it measures the change:
- line weight: the distribution of edge thickness, from the DOM stroke widths and from the pixels;
- outline presence: closed dark contours around filled regions;
- fill levels inside shapes (cel steps), and the residual gradient fraction;
- surface: texture energy on flat regions;
- stepping: runs of identical consecutive frames, from a short clip;
- boil: edge displacement between holds, on shapes only;
- text stillness under boil.

**ERROR** when an axis the spec sets measures unchanged against the unstyled render. In particular, an ERROR
when hue is the only thing that changed: the recolour-only detector.

**ERROR** when a beat's measures fall outside the film's own spread, by a tolerance the builder sets from
measured data. This is the consistency check.

It also writes a contact sheet: references beside styled beats, for the agent and the user to look at. A gate
pass is never the verdict on its own; someone looks.

### E. The style sample (`scripts/style_sample.py <out_dir>`)
1. Picks 2–3 representative beats: one diagram or data beat, one object beat (when the film has one), one
   type-led beat.
2. Renders their settled frames plus a ~2 s clip of one of them (so stepping and boil can be seen).
3. Lays the frames beside the references, with the stated shortfalls printed under the sheet.
4. Delivers `~/Desktop/<film> 风格样张.png` and `.mp4` through `deliver.py`.

The user's approval is recorded as `meta.style_signoff: {spec_sha256, sample_sha256, user_ok: true}`.

validate.py ERRORs on a styled board whose sign-off is missing, or whose `spec_sha256` no longer matches the
spec. render_remotion.py refuses the full render without it; a `--sample` render stays allowed.

### F. Texture generation
- `surface.source: 'generated'` asks for a tileable texture through the Codex path in `scripts/imagegen.py`,
  cached under `.assets/`.
- When Codex has no image tool (true as of 2026-10-03: free plan), fall back to procedural and add a
  `shortfalls` entry. The sample sheet shows it.
- Never call a paid API without the user's per-run permission.
- A generated texture is never content: no shapes that read as objects, no text. imagegen's existing
  no-text and no-subject clauses apply.

## Acceptance
1. **Cartoon, end to end.**
   - A self-written test film (not the user's material) in a cel-cartoon style.
   - The sample sheet goes to the user, then the full film.
   - style_qa passes, and the frames are looked at, mid-beat as well as settled.
2. **Held-out styles, zero code changes.** After cartoon is done, the **user picks 2–3 styles** the work was
   never tuned on.
   - Each goes through decomposition → spec → engine → sample sheet with no code change.
   - Report per axis what worked, and every shortfall.
   - A style that needs code is a finding to report, not something to fix silently inside acceptance.
3. **The recolour-only detector works.** A test in which the engine is forced to a no-op must ERROR in
   style_qa. A test in which one beat is left unstyled must ERROR the consistency check.
4. **No regression.**
   - No `meta.style` → byte-identical frames on a fixed corpus of registers.
   - Full suite green.
5. **Coverage.**
   - All 218 registers and the library's workshop objects render under the cartoon spec at 16:9 and 9:16
     without crashing.
   - The coverage report lists, per axis, the beats reached and the exempt ones with reasons.
   - Fidelity sheets of the library objects show no new finding under the style.

## Calls I made (for the user to check)
- **Evidence photographs are never repainted**, only framed and graded. A photo repainted in a style is no
  longer evidence.
- **Captions are never restyled; body text is never wobbled, posterized or textured.** Display type may take
  an outline and the style's face.
- **The held-out styles are chosen by the user at acceptance time, not now**, so I cannot tune toward them.
- **Remotion tier only**; the HTML tier is out of scope.
- **Easing and squash reach only registers that use the shared motion helpers**; the rest get stepping. This
  is reported as coverage, not hidden.

## Settled after the builder check (my calls)
1. **The DOM pass is a pure, idempotent function of the current DOM.**
   - It runs in a layout effect after React's render of each frame, and re-applies every frame, because React
     overwrites its edits.
   - It holds `delayRender` until fonts and images have loaded.
   - It never depends on frame order, because seeks are out of order and run across tabs.
   - **The first build step is a spike** that proves this on ~10 hard registers: raw SVG, inline gradients,
     CSS-3D, camera, labels.
   - **If the spike shows the pass cannot be robust, the fallback is a mechanical codemod** that routes those
     shots' strokes, gradients and shadows through shared primitives. A lint then forbids raw strokes,
     gradients and shadows in new registers.
   - Either way the result is general: no per-style code, and a new register is covered by construction. The
     fallback is a builder decision made from the spike's measurements, and is reported.
2. **No `meta.style` means the engine is not mounted at all.** It is a conditional mount: no wrapper, no
   filter defs. "Byte-identical" means equal frame-PNG pixel hashes on a fixed register corpus, compared
   against the pre-change commit.
3. **The recolour bar.**
   - Every axis the spec sets away from `as-drawn` must measure changed; an axis left `as-drawn` is not
     checked.
   - A spec that sets **no** structural axis away from `as-drawn` is a recolour by definition. validate.py
     WARNs, and the sample sheet says in words: "this style matches the default drawing; only the palette
     changes". The user decides at sign-off. A gate never blocks that case on its own.
4. **Consistency runs over non-exempt beats only.**
   - Exempt beats (evidence photos, canvas) are listed on the sample sheet with their reason.
   - When more than a quarter of a film's beats are exempt, the sheet says so, because the film will read
     mixed.
5. **Text is never moved in z-order.**
   - Filters and outlines go on shape elements and on groups that hold no text. The DOM pass applies them per
     element, not to a whole layer.
   - Text inside a `<canvas>` or a raster is unclassifiable. That shot is exempt from per-pixel filters and
     listed in coverage.
6. **Stepping quantizes the register's clock after the sync warp.** It floors to the step, so the clock
   stays monotone.
   - Captions, audio, seams and camera stay on ones.
   - A cue lands up to `stepping − 1` frames late. The sync gates get that tolerance only when stepping > 1,
     and record it.
7. **The cartoon bar is the user's eye at the sample**, with style_qa passing (decision 6). There is no fixed
   recipe of axes.
8. **No references reachable** (offline, search refused): `refs: []` is allowed only together with
   `refs_missing: "<why>"`. The sample sheet then says in its title that there were no references and asks
   the user for one. validate.py ERRORs on empty refs without that reason.
9. **Phasing.** The development loop uses a small representative corpus (~15 registers plus the library
   objects). The full 218 × {16:9, 9:16} sweep runs once, as the final acceptance step.
10. **Generated texture.**
    - Cartoon acceptance does not need it.
    - The generation path is still built (decision 3), behind the procedural fallback. While the Codex
      account has no image tool, it can only be tested with a stub. That is reported as unverified on real
      generation, not claimed as working.

## Left to the builder
- The exact axis list, value sets and units.
- Filter parameters.
- The DOM-pass implementation, and how it stays out of the way of DOM-measuring gates.
- Tolerances for the consistency check, set from measured spreads.
- How the sample picks its beats.
- File and module names beyond the ones fixed above.
- Test corpus composition.
