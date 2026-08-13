# Shot Director (remotion bespoke-shot tier)

> **When this runs.** ONLY for a `meta.renderer:"remotion"` film — the bespoke-shot LIBRARY tier. It is the
> remotion analogue of the design-director: the content-planner decided *what* each beat teaches; you decide
> *which hand-written design language renders it*. If the deck is HTML/local, or the legacy
> `meta.renderer:"remotion-legacy"` cinematic tier, this file does NOT apply.

You assign every beat a **shot** — one register from `remotion/LIBRARY.md` (50 hand-written components) — and
its **topic copy** (`shot_props`). You write `scene.shot` (a register id) and `scene.shot_props` (an object) onto
each scene in `storyboard.json`. You do NOT change facts, narration, or beat order.

## Read first
1. `content_plan.json` — the ordered beats (learning_point, narration_intent, `visual_intent`, `relation`,
   `energy`, `stage`, `climax`/`hold`, and `source_ref`).
2. `remotion/LIBRARY.md` — the 75 registers grouped into FAMILIES (A Product-UI · B Camera/space · C Kinetic
   type & title · D Data/technical · E 3D/spatial · F Fluid/generative · G Illustrated/craft styles · H Comparison ·
   I Mechanical/physical · J Experimental type · K Generative · L Editorial/print · M Glitch/digital-decay ·
   N Isometric · O Urban/signage), each with a one-line **"use when"** and its **props** (the Generalization
   table). The family set is **OPEN** — if a beat wants a bold language that fits none of these, a new register
   in a NEW family is fair game (add the letter).

## Step 0 — the shot-template CONTEST (the user picks a DIRECTION)
This is the remotion analogue of the html register-contest (SKILL.md 3.55). Before assigning per-beat shots,
offer the user a **whole-film direction** to choose from — a *direction* is a coherent lean toward certain
register FAMILIES (each beat is still its own design language; the template only EMPHASIZES families + sets the
overall feel). The catalogue is `scripts/shot_templates.py` (product-demo · kinetic-editorial · cinematic-craft ·
data-story · retro-playful · terminal-technical).
1. **Route** the topic → 3 fitting candidates: `python scripts/shot_templates.py --route "<topic>" --out <out_dir>`.
   Each candidate has a `pitch`, a HERO register, and a printed **copy-pasteable still command**.
2. **Render one representative still per candidate** so the user compares REAL topic-bearing frames (never abstract
   defaults): run the printed command for each — `cd remotion && npx remotion still src/index.ts <hero_id>
   <out>/_contest_<k>.png --frame=110 --props='<json>'` — then montage the three. **`--frame=110` is REQUIRED:**
   `remotion still` defaults to frame 0, where an animated shot is UN-STARTED (a blank command palette, a
   half-formed wordmark); every hero is ≥150f so frame 110 (`shot_templates.CONTEST_FRAME`) is the settled zone.
   The still carries the topic (the wordmark / label / filename IS the topic), so the frames differ by look, not
   by placeholder.
3. **User picks** one via AskUserQuestion (option prompt, never free-text). Record `meta.shot_template` = the pick
   and `meta.shot_template_contest = {candidates:[the 3 keys], winner:<pick>, user_pick:true}` on the storyboard —
   `validate.py` errors on an unknown direction or a malformed contest, and warns if a template is set with no
   contest trace.
4. **Apply it.** The chosen direction BIASES per-beat register selection toward its families (still never two
   adjacent same-family): `python scripts/shot_director.py <out> --template <pick>` runs the deterministic
   assigner with the bias, or apply the same lean by hand as you author `shot`s below.

## The mandate
For each beat ask *"what is the clearest hand-written LANGUAGE for THIS idea?"* — match the beat's intent to a
register's "use when", never "which card layout". Then fill that register's props from the beat's own content so
it speaks the topic, not WorkBuddy. **Lean toward the chosen `meta.shot_template`'s families** (Step 0) while
keeping the family-variety rule — the direction colours the film without making it monotone.

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
Edit `storyboard.json`: set `meta.renderer:"remotion"` and, on every scene, `shot` (a valid id from
`remotion/src/shots/*.tsx`) + `shot_props` (an object; `{}` = the register's WorkBuddy-neutral defaults, which
you should usually override with topic copy). Then record your choices for the critic: a short `shot_rationale`
per scene (why this register, which family) is encouraged. `validate.py` errors on a missing/unknown `shot` or a
number-bearing register left on its demo default; `render_remotion.py` renders the chosen shots through the
data-driven `Film`. Keep a family-variety pass at the end: scan the shot sequence and swap any adjacent
same-family pair for an equally-fitting register from a different family.
