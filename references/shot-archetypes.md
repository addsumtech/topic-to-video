# Cinematic shot archetypes — the per-beat DESIGN brain (Remotion tier)

> **When to read this**: authoring ANY `renderer:"remotion"` cinematic deck, BEFORE writing a scene's
> `stage`/`shots`. This is the design-selection layer — it decides what each beat *looks like*. Camera
> mechanics (how it moves) live in `references/shots/shot-vocabulary.md`; this file decides the SET.

## The problem this solves

The camera tier is strong, but left alone it films **one generic glass panel** (kicker→title→sub) on every
topic — so an 8-beat film reads as 8 glass cards at different distances. A real product-launch film gives
**every beat its own bespoke, topic-driven design idea**. That is a SELECTION discipline authored up front,
not a bigger component bin.

**The acceptance test (huashu Pattern C):** *cover the narration — can you still tell which beat, and which
product, this is, from the visuals alone?* If two beats are indistinguishable with the copy hidden, the
design is lazy. Redesign until each beat is visually unmistakable.

## The mechanism: ARCHETYPE × STYLE × CONTENT (they multiply)

Three orthogonal axes, decided in this order:

1. **STYLE** — chosen ONCE per deck (the deck's `meta.style`: editorial / brutalism / glassmorphism /
   terminal / vaporwave / …). It fixes the *skin*: palette, type faces, texture, radius, grain. Do NOT
   change it per beat.
2. **ARCHETYPE** — chosen PER SCENE from the catalogue below. It fixes the *composition + visual concept +
   signature motif + the form the content takes*. This is the axis that must VARY beat to beat.
3. **CONTENT** — the beat's actual data/words.

Because archetype (composition) is decoupled from style (skin), `N archetypes × M styles × content` rarely
collide — the same deck's beats look distinct while sharing one skin. (This is huashu 律九: fix the skin
once, swap the composition every beat.)

## Author a STYLEFRAME first (the atom of bespoke design)

Before tuning any camera, write a one-line **styleframe brief** per scene — a fully-decided still:

```
styleframe: <archetype> · focal: <the ONE subject the eye lands on> · concept: <the visual idea in a phrase>
            · signature: <the 120% move that makes it THIS beat> · motion-verb: <what the camera/elements DO>
```

The camera is then a *consequence* of this still, not a free-floating drift. Author the styleframe, build the
SET to realize it, then frame it.

## The catalogue (pick one per scene; VARY them across the film)

Each archetype = a composition + a FORM source. **Realise it NATIVELY** (stage elements / 3D primitives) —
the cinematic tier is a DISTINCT native-3D style, NOT the HTML tier with a camera bolted on. **Path A**
(author an HTML slide at `<out_dir>/pages/<name>.html`, reference it from a `kind:"card"`/plane `html:` field,
screenshotted onto a plane the camera flies past) is a **DEPRECATED escape hatch** — `validate` WARNS on it,
`design-critic` D12h REVISEs a film that leans on it. Use it ONLY for a genuinely rich designed form with no
native equivalent (a dense scorecard, a 2×2 quadrant); if the WHOLE deck is that kind of designed 2D content,
it belongs on the **HTML tier** (omit `meta.renderer:"remotion"`), not screenshotted into 3D.

**⚠️ TWO native renderers, NEVER mixed in one beat.** The native forms split across two mutually-exclusive
render paths, and a scene dispatches to exactly ONE (a scene with `planes` renders NO stage elements, and
vice-versa — the other tier's forms silently DROP):
- **PLANE tier** (`scene.planes`, rendered by ThreeScene): `bars` · `stack` · `particles` · `surface` ·
  `glyphrain` · `device` · a rasterized `text` plane · `image` planes.
- **STAGE tier** (`scene.stage` + `shots`, rendered by SceneStage): `display` · `metaphor` · `terminal` ·
  `hud` · `spotlight` · `connector` · `textblock` · `panel` · `card` (Path-A) · `image`.
So a beat's realization must draw ALL its forms from ONE tier. Do NOT combine e.g. `bars` (plane) with a
`connector`/`spotlight` divide (stage) — only the plane renders and the divide vanishes. There is no
plane-tier connector today; a divide/rail/flow-arrow is a STAGE-tier composition (`display` groups +
`connector`/`spotlight`).

| Archetype | Use when the beat is… | Composition / signature | NATIVE form — pick ONE tier (Path-A = escape hatch) | Camera that suits it |
|---|---|---|---|---|
| **hero-on-void** | a thesis / one hero number / a manifesto line | ONE object in vast negative space; the void IS the design | `display` hero (stage) OR a single `bars` stat (plane) | slow push-in, long static hold |
| **manifesto-monolith** | a bold claim / value proposition | GIANT display type as the set, staged in Z | `display` element (stage; `attitude`: rise / tracking-in / blur-in) — full-strength kinetic type, not a 9% watermark | dolly THROUGH the words |
| **data-materializes** | a metric / trend / magnitude | numbers with real mass — extruded 3D that grows | `bars`/`stack`/`particles`/`surface` (plane; + value labels) | craning orbit reveal |
| **metric-wall** | 3–4 standout KPIs | a grid of proof tiles | a row of `display` KPIs (stage) OR `bars` (plane); Path-A `.scorecard` only if a rich tiled layout is essential | pan across, then push into one KPI |
| **process-flow** | a sequence / pipeline / workflow | stepped arrow of progress, a focal step lit | `connector` arrows + `display` steps (all STAGE-tier); Path-A `.flow` = escape hatch | pan along the steps → push the focal step |
| **comparison-split** | a contrast (before/after, v1/v2, us/them) | a hard divide, two worlds | two `display` groups split in X + a `spotlight`/`connector` divide (all STAGE-tier); Path-A `.split` = escape hatch | whip-pan or rack between the two sides |
| **system-map** | a structure / architecture / relationship | a constellation; centre + peers | `hud` + `connector` hub/spokes (all STAGE-tier); Path-A `.hubspoke` = escape hatch | pull-OUT reveal of the whole system |
| **timeline-rail** | a history / roadmap / dated milestones | a throughline with nodes | `connector` rail + `display` nodes (all STAGE-tier); Path-A `.timeline` = escape hatch | travel along the rail |
| **quadrant-position** | two axes / a market position | a map with a focal cell | (weak native) Path-A `.quadrant` escape hatch, or route this beat to the HTML tier | push into the focal cell |
| **metaphor-mechanic** | an abstract idea needing a concrete image | the idea made PHYSICAL — a verb you can see | **`metaphor` verb** (stage; below) — the idea as a physical CHANGE the camera watches | motion that ENACTS it (the fill rises, the token falls) |
| **device-focus** | showing the actual product UI | the real thing, framed | **`device`** volume (plane; chassis + glossy screen + UI cards at real z), or an `image` plane | turntable orbit, push into the screen |
| **world-immersion** | a terminal / dev / infra / code space | the viewer stands INSIDE the world | **`glyphrain`** falling code (PLANE-tier) OR a `terminal`+`hud` set (STAGE-tier) — one tier, not both | dolly THROUGH the space |
| **quote-testament** | a verbatim customer voice / claim | the human voice, alone | native `display`/`text` (the words ARE the set) | static hold, a breath of push |
| **exploded-assemble** *(reserve)* | a composed system revealed by its parts | parts fly apart / assemble | native 3D planes (future) | orbit while parts assemble |
| **turntable-material** *(reserve)* | a single hero product / logo | the object as sculpture, lit | native 3D + light rig (future) | slow turntable + light sweep |

### Native materialized-metaphor verbs (`kind:"metaphor"`, `concept:<verb>`)

A stage element `{kind:"metaphor", concept, values:[…], label?, unit?, valueLabels?, verbSpan?}` renders a
frame-driven primitive whose MOTION enacts the meaning as the camera arrives (the number counts as the verb
plays; digits use the lining number face). Prefer a native verb over a Path-A card when the meaning is a
physical CHANGE the camera can WATCH:

| concept | values → meaning | verb |
|---|---|---|
| `filling-vessel` | `[level]` (0..1 or 0..100) = adoption / progress / capacity | FILL — a vessel fills |
| `widening-gap` | `[baseline, with]` → the gap = loss / divergence / lead | DIVERGE — two tracks separate |
| `physical-fall` | `[before, after]` → the drop = the cliff | FALL — a token drops off a shelf (accelerating) |
| `diverging-pair` | `[a, b]` end-heights from one origin | SPLIT |
| `converging-scatter` | `[total]` scattered → one = consolidation | CONVERGE |

**metaphor-mechanic is the highest-yield novelty engine** (huashu 律八 物化+过程感): map the beat's MEANING
to a visual PROPERTY that only THIS subject would use — *the widening white gap between two bars IS the
compounding loss; a filling vessel IS adoption; the small tip above the waterline IS the visible 10%*. A
film full of metaphor-mechanic beats could ONLY be about this product. Reach for it on any abstract beat.

## Selection procedure (per deck)

1. **Find the core metaphor of the whole product** (what is it fundamentally *like*?). It biases which
   archetypes recur as the film's motif.
2. **Assign an archetype to each beat** by the content's shape (the table's "use when" column). Pick the form
   the content WANTS, never default to hero-on-void/panel.
3. **Force variety** (the gate enforces this): no single archetype on >45% of beats; ≥3 distinct archetypes
   in a ≥4-beat film; **≥1 metaphor-mechanic or signature beat**; never two consecutive beats on the same
   archetype. If a beat can only be a plain panel, it probably should have been an HTML-tier slide, not a
   cinematic shot.
4. **Build a bespoke energy arc**: open calm (hero-on-void / establishing), give the single most important
   beat the slowest, most-staged treatment, place the climax at ~75–85% (not the end), resolve wide.
5. **Write the styleframe** per scene, build the SET (native elements or a Path A form page), then frame it
   with `shots` per `shot-vocabulary.md`.

## The continuity spine (so variety reads as ONE film, not an anthology)

Aggressively varying each beat's design risks the opposite failure — a grab-bag of unrelated shots. Two
cheap anchors hold it together as one film: (1) **a persistent hero mark** — set `meta.hero_mark` to a short
brand wordmark and it renders as a small, CONSTANT top-left lockup on every scene (it never transitions or
resets), the through-line the eye tracks across all the variety; (2) **morph, don't cut, between related
beats** — when beat B is the payoff of beat A, carry a shared element across the seam (a shape becomes the
next object) rather than a naked cut. Budget: never a naked cut between two designed beats — a marked seam
rides the audio breath (see `references/motion-grammar.md` "Transition STYLE").

## The distinctiveness rule (why Remotion, not HTML)

Spend the cinematic tier's unique budget where an HTML page CANNOT follow: real depth, a camera that
reveals, physical motion (a fall, an assembly, a path drawn in space), light as a character, and sound.
**If a cinematic beat could have been a static HTML page, it should have been one.** Path A lets a beat
REUSE an HTML form, but the reason to put it in the cinematic tier is the camera move / depth / continuity
that a still page can't express — otherwise author it as an `html` slide on the local tier.
