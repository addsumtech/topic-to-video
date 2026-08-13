# Shot Director (remotion2 bespoke-shot tier)

> **When this runs.** ONLY for a `meta.renderer:"remotion2"` film — the bespoke-shot LIBRARY tier. It is the
> remotion2 analogue of the design-director: the content-planner decided *what* each beat teaches; you decide
> *which hand-written design language renders it*. If the deck is HTML/local, or the legacy
> `meta.renderer:"remotion-legacy"` cinematic tier, this file does NOT apply.

You assign every beat a **shot** — one register from `remotion2/LIBRARY.md` (50 hand-written components) — and
its **topic copy** (`shot_props`). You write `scene.shot` (a register id) and `scene.shot_props` (an object) onto
each scene in `storyboard.json`. You do NOT change facts, narration, or beat order.

## Read first
1. `content_plan.json` — the ordered beats (learning_point, narration_intent, `visual_intent`, `relation`,
   `energy`, `stage`, `climax`/`hold`, and `source_ref`).
2. `remotion2/LIBRARY.md` — the 50 registers grouped into 9 FAMILIES (A Product-UI · B Camera/space · C Kinetic
   type & title · D Data/technical · E 3D · F Fluid/generative · G Illustrated/craft styles · H Comparison ·
   I Mechanical/physical), each with a one-line **"use when"** and its **props** (the Generalization table).

## The mandate
For each beat ask *"what is the clearest hand-written LANGUAGE for THIS idea?"* — match the beat's intent to a
register's "use when", never "which card layout". Then fill that register's props from the beat's own content so
it speaks the topic, not WorkBuddy.

## Rules (all four bind)
1. **Match intent → register.** `statement`→a title/kinetic register (CinematicTitle, FocalIsolation,
   KineticManifesto, LiquidChrome, BrutalistType, SwissEditorial); `sequence`→ExplodedSchematic/TimelineTravel/
   CommandSummon; `structure`→CollaborativeCursors/KnowledgeGraph/MapRoutes/DataOrrery/WireGlobe/BlueprintGrid;
   `list`→BlockAssembly/TemporalAccelerate; `metric`→ChartLive/BlueprintGrid(counter)/PhysicsStack. The `climax`
   beat gets a payoff register (ParticleForm/RadialBurst/LightTrails/SpotlightStage/LiquidFill); the `close`/`hold`
   beat gets a premium title (LiquidChrome/HoloFoil/CinematicTitle/SwissEditorial). Use the "use when" as the map.
2. **Vary the FAMILY across the film — never two ADJACENT beats from the same family.** This is what stops the
   film reading as one look. Spread across ≥6 families in a ≥10-beat film; feature the 3D register (MaterialHero)
   and one illustrated/craft style at most once or twice.
3. **Fill props from the beat, faithfully.** Put the beat's real nouns into the register's props (its wordmark,
   `items`, `hub`, chat `messages`, `nodes`, etc. — see the LIBRARY props table). **Any register that shows a
   NUMBER (ChartLive `endVal`, BeforeAfterSlider `metric`, VelocitySnap `metric`, BlueprintGrid counter) MUST be
   given a SOURCED figure that traces to the beat's `source_ref` — NEVER leave the shot's illustrative demo
   default, and never invent a statistic.** If a beat has no real number, pick a non-number register.
4. **Copy stays in the beat's language** (the deck's language — English or 中文) and stays SHORT (a register's
   label/title is a few words, not the whole narration — the narration is the voiceover + caption).

## Output
Edit `storyboard.json`: set `meta.renderer:"remotion2"` and, on every scene, `shot` (a valid id from
`remotion2/src/shots/*.tsx`) + `shot_props` (an object; `{}` = the register's WorkBuddy-neutral defaults, which
you should usually override with topic copy). Then record your choices for the critic: a short `shot_rationale`
per scene (why this register, which family) is encouraged. `validate.py` errors on a missing/unknown `shot` or a
number-bearing register left on its demo default; `render_remotion.py` renders the chosen shots through the
data-driven `Film`. Keep a family-variety pass at the end: scan the shot sequence and swap any adjacent
same-family pair for an equally-fitting register from a different family.
