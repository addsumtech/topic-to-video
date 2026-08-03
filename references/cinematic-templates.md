# Cinematic film TEMPLATES — the bold looks a cinematic deck is BUILT ON

The Remotion cinematic tier is **template-driven**. A `type:"cinematic"` film picks ONE template
(`meta.cinematic_template`) — a whole-film LOOK: a fixed **substrate + silhouette + motion grammar +
beat-semantics**, plus **one re-derived accent** so the SAME template re-colours and re-contents for ANY
topic. Read this when building a cinematic film: the design-director offers 2–4 templates as a contest (see
`agents/design-director.md` "Cinematic template contest"), the user picks, and the film is instantiated in it.

**Why templates, not ad-hoc:** a bespoke concept per film is unrepeatable and drifts. A template is a
*generalisable* grammar — the identity is fixed, only the accent (from the topic/brand hue) and the content
change. That is what makes the tier produce a premium, coherent, on-brand film for an arbitrary product
instead of "moved text on a dark card".

## Choosing a template — topic → template routing

Route by the topic's SUBJECT (the design-director scores the top 2–4 and offers them):

| The topic is… | Template |
|---|---|
| A CLI / dev tool / API / infra / agent framework (a command surface) | **Command Surface** |
| AI / ML / a model / reasoning / embeddings / "formless → ordered" (also sensitive/abstract) | **Liquid Model** |
| Finance / money / revenue / markets / magnitude-as-hero | **Molten Ledger** |
| Analytics / metrics / growth / dashboards / insight-and-momentum | **Aurora Bloom** (a LIGHT film) |
| A bold brand / vision / manifesto / hype launch / POV | **Ignition → Monument** |
| Heritage / luxury / craft / design-led / editorial / culture | **Doorway → Long Gallery** |
| A desire object / device where MATERIAL sells (phone, watch, EV, spirits) | **Rakelight** |
| An engineered multi-part product (laptop, GPU, drone, robotics) | **Exploded Schematic** |
| A system / infra / security / platform (architecture + throughput) | **Defrag** |

Two templates can fit one topic — that's the point of the contest. Offer the strongest 2–4 with the
one-line pitch below; the user's pick becomes `meta.cinematic_template`.

## The GENERALISATION recipe (how one topic re-skins any template)

Each template is a FIXED grammar + ONE re-derived accent. Instantiation:
1. **Route** the topic → a template (table above).
2. **Pull one deck accent A** — the brand/topic hue (`theme.py --accent`, or sampled). Every palette is a
   **deterministic transform of A** (per the template's colour system below) — so the film is on-brand and a
   different topic/accent yields a different-looking, on-topic film with zero new hand-authoring.
3. **Generate the per-beat colour worlds** with `scripts/cine_palette.py` (accent + template key → the
   per-beat `{bg, blobs, accent}` palettes + the aurora backplane pages). Never hand-author aurora pages.
4. **Fill the beat arc** (below) with the topic's real content (from the content plan) — each beat a
   DIFFERENT archetype (references/shot-archetypes.md), so no two beats look alike.
5. **Bind with the template's SIGNATURE element + TRANSITION grammar** (below).

`meta.cinematic_template` (a key from this catalogue) + `meta.accent` are the only knobs the look needs;
the palette engine + the arc do the rest. Semantic colours (go/info/alert, gain/loss, growth/attention,
warm=raw/cool=resolved) are FIXED per template so the film reads sound-off across any accent.

## The 9 templates

Each: **fit** · **the pitch** (director→user) · **colour system** (accent-derived, generalisable) ·
**beat arc** (archetypes) · **signature** (the through-line) · **transitions** · **buildable now vs later**.

### 1. Command Surface — *"The terminal was secretly a cinema."*
- **Fit:** CLIs, dev tools, APIs/SDKs, infra, agent frameworks — a real command surface.
- **Pitch:** every claim is a command whose result physically GROWS out of the blinking prompt — bars extrude
  from the caret, pipelines stand off the floor — then the world folds back into one glowing cursor.
- **Colour:** fixed graphite substrate (void `#07090B`, surface `#0F1317`, hairline `#1C2228`, dim `#6B7680`,
  bright `#E7EDF3`) + ONE phosphor accent by command-lifecycle: SPINE = accent A, GO = A→`#34D399`, INFO =
  A→cyan `#22D3EE`, ALERT = A's complement `#F0407A`. Topic recolours the spine; go/info/alert stay fixed.
- **Arc:** hero-on-void → metaphor-mechanic(physical-fall) → manifesto-monolith → process-flow →
  data-materializes → hero-on-void(climax) → hero-on-void.
- **Signature:** the blinking caret / prompt line — in the first and last frame, the origin every world
  blooms from and the mechanism every world collapses into.
- **Transitions:** COLLAPSE-TO-LINE → caret holds → APERTURE (match-cut on the cursor). CARRY within an idea;
  DIP only at a chapter seam. No wipes/spins.
- **Build:** mostly now (terminal, collapse-to-line, aperture, aurora, display, 3D bars, Path-A .flow, camera,
  DoF/grade). New: an "output anchored to the prompt baseline" staging helper. skia bloom later.

### 2. Liquid Model — *"Intelligence you can watch think."*
- **Fit:** AI/ML, foundation/generative models, reasoning/agentic, data platforms; also sensitive/abstract.
- **Pitch:** one living iridescent material melts between fluid and crystal — breathes when idle, SNAPS into
  ordered structure the instant a fact lands; the same substance is blob, lattice, split, bars, hero, droplet.
- **Colour:** duotone sheen ramp from A, no fixed substrate — colour IS the material. COOL pole = A pushed to
  high-chroma cyan/blue (order), WARM pole = A's near-complement magenta/amber (formless); void = A
  darkened+desaturated, lit from within. Somber mode: chroma ~40%, one cold accent. warm=raw / cool=resolved.
- **Arc:** hero-on-void → manifesto-monolith → system-map → comparison-split → data-materializes →
  hero-on-void(climax) → quote-testament.
- **Signature:** the ONE living iridescent material, fluid↔crystalline — every beat a different STATE of the
  same substance + a recurring seed droplet.
- **Transitions:** LIQUID DISSOLVE, never a cut — structure melts, flows, re-condenses via rack-defocus;
  silhouette persists (this IS that). Metaphor verbs (converge/diverge) ARE the transitions. Heavy DoF.
- **Build:** approximate now (hero object in void, DoF orbit, rack-focus, aurora, duotone POST grade,
  refracting display type, 3D bars, condense/split verbs; fluid = Path-A displaced-gradient blob
  feTurbulence/feDisplacementMap + bloom/DoF). Later: raymarched metaball/ferrofluid + real fluid↔lattice.

### 3. Molten Ledger — *"Numbers cast in metal."*
- **Fit:** finance, markets, revenue, funding, unit economics, pricing, fintech — money/magnitude as hero.
- **Pitch:** figures forged in molten metal on a black reflective vault floor, each with real mass; every beat
  cools into one hot horizontal ledger line the next magnitude rises from.
- **Colour:** obsidian `#0A0B0F` + ONE molten metal (from A: catch-light `#FFE9B0`-class, core = A, shadow =
  H@L12) + a cold-loss complement (GAIN glows hot; RISK/LOSS chills — desaturate ~40%, shift H→210 steel
  `#5C7A8C`). Never >2 metals on screen.
- **Arc:** terminal/device-focus → hero-on-void → data-materializes → metaphor-mechanic(widening-gap) →
  metric-wall → process-flow → hero-on-void/collapse.
- **Signature:** THE MOLTEN LEDGER LINE — one hot rule every beat resolves INTO and the next rises FROM
  (baseline→axis→track→close); numbers cast as chrome/gold monoliths with mass, never typeset labels.
- **Transitions:** COLLAPSE-TO-LINE between heroes (emitted line = next beat's axis, an authored match-cut);
  one PUSH direction; heavy DIP through obsidian at seams + a 0.3s payoff dip before climax.
- **Build:** now (extruded bars w/ emissive molten cap, terminal ticker, collapse-to-line, widening-gap,
  rasterised-3D monoliths, single-metal aurora, skia bloom, Path-A .scorecard/.flow). Later: reflective chrome
  on 3D text, raymarched molten pooling.

### 4. Aurora Bloom — *"Data drawn in light."* (a LIGHT film)
- **Fit:** analytics, product metrics, growth/retention, dashboards, SaaS KPIs, forecasting — insight & momentum.
- **Pitch:** analytics as luminous atmosphere — crisp ink figures/charts drawn in light bloom open from a line
  onto a breathing pastel aurora, then dissolve to bokeh. The opposite of the dark-terminal cliché.
- **Colour:** pale MIST ground `#F7F8FB`; from A an analogous triad {H0, H0+35, H0−35} at high L (78–88), each
  backplane blends two. Semantic by HUE-SHIFT: GROWTH → cool-fresh neighbour, ATTENTION → warm. Data/numbers
  are near-black INK `#14161C` + one saturated accent stroke — atmosphere generated-feeling, data exact.
- **Arc:** hero-on-void(aperture) → data-materializes(soft) → metaphor-mechanic(filling-vessel) → metric-wall
  → system-map → hero-on-void(blur coda).
- **Signature:** LIGHT AS MEDIUM — data marks in luminous strokes / a filling vessel of light / glowing
  constellation nodes that BLOOM from a line and DISSOLVE to bokeh, numbers stay crisp ink.
- **Transitions:** APERTURE-BLOOM opener + seam; DRIFT ("page breathes away") carries continuations, never
  hard-cuts; one BLUR coda; 0.3s dip through mist before climax.
- **Build:** now (aperture, filling-vessel, display/counter, multi-hue aurora, skia bloom, blur+drift, Path-A
  .chart/.scorecard). Later: GPU bokeh point-cloud; a light-bg DoF bloom preset in Finish.

### 5. Ignition → Monument — *"A manifesto you move through."*
- **Fit:** bold brand/consumer launches, mission/values manifestos, hype reveals, founder-vision, positioning.
- **Pitch:** monumental words stand in a black void, each born from one hot line; the camera flies THROUGH
  them and the accent heats cool→white as the argument is won — colour itself narrates persuasion.
- **Colour:** GROUND constant (void = A desaturated ~7% L, temperature kept), TYPE = warm paper-white
  `#F5F0E8` (never pure). Per-beat aurora ramps COOL→HOT across the arc: stakes = cold smoulder L18; thesis =
  full chroma L45; climax = white-hot L80; close = embers to void.
- **Arc:** manifesto-monolith → metaphor-mechanic → manifesto-monolith → data-materializes → quote-testament
  → manifesto-monolith → hero-on-void.
- **Signature:** THE HOT LINE — a single horizontal filament of accent light; every beat born from it
  (aperture), measured by it (gap rail / bar floor), or returns to it.
- **Transitions:** constant forward PUSH through Z; MATCH-CUT welds ideas (word-baseline→gap-rail) — the
  signature; one FADETHROUGH hands to the human voice; one BLUR coda + dip-to-void close.
- **Build:** essentially fully buildable today (manifesto display, aperture, collapse-to-line, widening-gap,
  3D bars, per-beat aurora, match-cut authored via identical coords).

### 6. Doorway → Long Gallery — *"An explainer staged as an exhibition."*
- **Fit:** heritage/luxury, considered/design-led consumer, founder-story/craft, wellness, culture/archive.
- **Pitch:** each idea is a framed, hung, spot-lit plate on a warm gallery wall; the camera is a visitor
  craning past the works from room to room as a travelling pool of light ignites each plate.
- **Colour:** ACCENT constant (muted one step, "gallery restraint"), GROUND moves (walls = warm neutrals base
  `#EDE6DA` ink `#211C17`, each room a different tone: ochre `#E9DFCC`, grey-green `#DCE0D6`, dark alcove
  `#241F1A`), LIGHT supplies drama.
- **Arc:** hero-on-void → device-focus → manifesto-monolith → metric-wall → metaphor-mechanic → timeline-rail
  → quote-testament → hero-on-void.
- **Signature:** THE FRAME + THE MOVING LIGHT — every idea a framed hung plate; a travelling light-pool is
  attention, igniting each work on arrival.
- **Transitions:** constant WALK (reading direction); WIPE = "next room" (a wall sheet sweeps — the
  architecture moves); LIFT = next wall in a room; DRIFT into a dim space; one MATCH-CUT; one BLUR coda.
- **Build:** now via Path-A + 2.5D depth (framed plates on Z-planes, crane/pull-out, filling-vessel install,
  timeline-rail, wipe/lift/drift). Needs a travelling-spotlight component (CSS radial light-pool now).

### 7. Rakelight — *"Void, then a blade unveils it."*
- **Fit:** hero consumer/luxury objects where DESIRE + MATERIAL sell — phones, watches, headphones, EVs, spirits.
- **Pitch:** total darkness, then a single travelling blade of specular light (the rake) — the only moving
  thing — sweeps across the hero object to reveal it as sculpture above a deep contact-shadow.
- **Colour:** one-light budget — ≥85% neutral obsidian/graphite; colour ONLY where light strikes an edge.
  MATERIAL-ACCENT = A at ~50% chroma at lit-metal value (rim-light + specular + hot bloom edge + wordmark);
  accent2 = material-accent rotated ~160°, cooled, low-intensity backlight. Maps to LightRig product/noir/void.
- **Arc:** hero-on-void → turntable-material → device-focus(macro) → exploded-assemble → metaphor-mechanic →
  metric-wall(object row) → manifesto-monolith(logo).
- **Signature:** the travelling BLADE of specular light + the deep contact-shadow the object floats above.
- **Transitions:** LIGHT is the editor — BLACKOUT-RAKE (fall to black, next rim rakes in), TURNTABLE CARRY,
  MACRO RACK (focusZ dive), LIQUID REFORM. Cuts hidden inside darkness.
- **Build:** now (LightRig product/noir/void moods w/ travelling key+specular+rim, constrained orbit, macro
  rack-focus, selective HDR bloom, kinetic type). Later: GLTF turntable, normal-mapped rake on a curved surface.

### 8. Exploded Schematic — *"Ghost to metal."*
- **Fit:** engineered multi-part products where PRECISION + how-it's-made sell — laptops, GPUs, drones, robotics.
- **Pitch:** a living orthographic drawing that dimensions itself, flies apart along a Z-rail into labelled
  parts, and locks back into solid material — a spec sheet you watch build and unbuild itself.
- **Colour:** schematic skeleton + warm-metal cores + one hot "active" part. Ground = paper `#EEF2F5` OR
  blueprint navy `#0B1A2B`; LINE (structure/dimension/reticle) = A rotated → cyan ~195° low-chroma
  (`#3FA6C4`); GHOST FILL = line @10–14% alpha; METAL CORE = warm neutrals (aluminium `#B8BCC0`, brass
  `#C7A468`); HOT ACTIVE = A full chroma, exactly ONE part/beat with HDR bloom.
- **Arc:** device-focus(schematic) → exploded-assemble → device-focus(closeup) → metric-wall →
  comparison-split → data-materializes → exploded-assemble(reverse).
- **Signature:** a persistent MEASUREMENT SYSTEM — thin cyan reticle + running corner spec-readout HUD that
  re-dimensions every beat — + the exploded Z-rail the camera tracks.
- **Transitions:** mechanical, drawn, snappy — EXPLODE/ASSEMBLE along Z, DIMENSION DRAW-ON (evolvePath),
  PART-SNAP whip, X-RAY PHASE (ghost→solid crossfade). Every seam is a mechanism doing something.
- **Build:** now (Path-A blueprint/FUI/scorecard, counters, terminal boot, 3D bars, x-ray→solid via stacked
  planes + leaf opacity). Needs @remotion/paths+shapes for reticles/leader lines; GLTF assembly later.

### 9. Defrag — *"The HUD locks onto the world."*
- **Fit:** systems, infra, security, data platforms, dev tools, logistics, ops — architecture + throughput.
- **Pitch:** a dark system boots from a wireframe into a living command deck — reticles, horizon grid and
  monospace telemetry hunt, sweep and LOCK onto real data on cue; the camera behaves like a gunsight.
- **Colour:** two-hue cool-structure/warm-alert FUI from A's hue S. bg = HSL(S,45%,5%) `#060A12`; structure =
  HSL(S,90%,60%) `#37E0FF`; grid = structure @8%; focus/warn = warm complement HSL(S+165,95%,58%) `#FFB020`,
  only the ONE element the beat is about. Exactly one alert-hue object on screen at a time.
- **Arc:** hero-on-void+terminal → system-map → metric-wall → data-materializes → comparison-split →
  manifesto-monolith.
- **Signature:** the reticle + horizon-grid + persistent corner status-readout (hero_mark as a callsign); the
  structure-cyan LOCK stroke is the through-line.
- **Transitions:** instrument transitions — BOOT (collapse→aperture powers on), scanline WIPE, whip-PAN carry,
  push/lift page-turns, power-down COLLAPSE at close.
- **Build:** most native-ready (terminal + collapse-to-line + aperture, grid/floor, lens dolly/bird's-eye, 3D
  bars w/ light rig). Needs @remotion/paths reticles; a CRT scanline post later (CSS repeating-gradient now).

## Transition GRAMMAR (named, reusable, motivated — not crossfades)

A cinematic transition is a CLAIM about how two beats relate; pick from this grammar per the template. The
storyboard marks the seam (`transition`/`transition_style`) and, for authored match-cuts, keeps shared
element coordinates across the seam.

- **collapse-to-line** — a world sucks into one glowing caret/rule. **aperture / aperture-bloom** — the next
  world irises open FROM that line; paired they read as a **match-cut on the seam**.
- **match-cut** (shared-element / identical coords) — one shape becomes the next thing; the strongest "this IS
  that", authored in the storyboard, not filtered.
- **liquid dissolve / reform** — structure melts, flows, re-condenses; silhouette persists (rack-defocus).
- **carry** glide · **drift** (page breathes away) · **push-through-Z** (constant forward momentum).
- **wipe** (room-reveal / scanline) · **lift** (vertical page-turn) · **blur coda** (one reserved rack-defocus
  close) · **dip** (fall through the ground colour at a chapter seam + a 0.3s payoff dip before a climax).
- **blackout-rake** (fall to black, next rim rakes in) · **explode/assemble** (parts along a Z-rail) ·
  **x-ray phase** (ghost→solid) · **dimension draw-on / part-snap** · **boot / power-down** · **turntable
  carry / macro rack**.

## Component ROADMAP (what the catalogue needs the tier to grow — build in Phase 2)

Ranked by impact: **GLTF / 3D-model tier** (real object turntable + exploded parts — Rakelight, Exploded
Schematic; today faked with product-photo planes) · **raymarched metaball/ferrofluid + oil-slick iridescence
+ fluid↔lattice morph** (Liquid Model, Molten pooling; today displaced-gradient blobs) · **@remotion/skia
selective bloom** on a separate canvas (real phosphor/hot-metal/climax glow without flattening the CSS-3D
rig) · **travelling spotlight / light-pool** (Doorway) · **@remotion/paths (evolvePath) + @remotion/shapes**
(reticles, dimension/leader lines, wireframe assemble — cheap frame-safe installs) · **reflective chrome on
3D text** (Molten) · **GPU bokeh point-cloud** (Aurora, Liquid) · **CRT/scanline post + wireframe→mesh
material** (Defrag) · **OrthographicCamera** (Exploded) · **an "output-anchored-to-prompt-baseline" staging
helper** (Command Surface). Each degrades gracefully to a Path-A/CSS/light-rig approximation today.
