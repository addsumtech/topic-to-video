# Shot Director (remotion bespoke-shot tier)

> **When this runs.** ONLY for a `meta.renderer:"remotion"` film — the bespoke-shot LIBRARY tier. It is the
> remotion analogue of the design-director: the content-planner decided *what* each beat teaches; you decide
> *which hand-written design language renders it*. If the deck is HTML/local, or the legacy
> `meta.renderer:"remotion-legacy"` cinematic tier, this file does NOT apply.

You assign every beat a **shot** — one register from `remotion/LIBRARY.md` (100 hand-written components) — and
its **topic copy** (`shot_props`). You write `scene.shot` (a register id) and `scene.shot_props` (an object) onto
each scene in `storyboard.json`. You do NOT change facts, narration, or beat order.

## Read first
0. **`references/remotion-shot-authoring.md`** — the frame-craft floor (full-bleed / title band / caption band /
   `fitContentSquare` / camera-locked), the MEANING mandate (hide-the-caption test + the anti-pattern catalogue),
   the real-imagery tier, and direction coherence. This is where films fail SILENTLY — read it before authoring.
1. `content_plan.json` — the ordered beats (learning_point, narration_intent, `visual_intent`, `relation`,
   `energy`, `stage`, `climax`/`hold`, and `source_ref`).
2. `remotion/LIBRARY.md` — the 100 registers grouped into FAMILIES (A Product-UI · B Camera/space · C Kinetic
   type & title · D Data/technical · E 3D/spatial · F Fluid/liquid/light · G Illustrated/craft styles · H Comparison ·
   I Mechanical/physical · K Generative · L Editorial/print · M Glitch/digital-decay · N Isometric ·
   O Urban/signage · P Dimensional/experimental type (variable-axis/inflated/elastic) · Q Anti-design/maximalist · R AI/neural ·
   S Scientific/molecular · T Circuit/hardware · U Audio/music · V Cosmic/space · W Organic/botanical ·
   X Weather/atmosphere · Y Fire/energy · Z Textile/fabric), each with a one-line **"use when"** and its
   **props** (the Generalization table). The family set is **OPEN** — A–Z are full, so if a beat wants a bold
   language that fits none of these, add a two-letter family (AA, AB, …).

## Step 0 — the shot-template CONTEST (divergence + selection; the USER picks a DIRECTION)
The full remotion analogue of the html register-contest (SKILL.md 3.55) — **divergence AND selection**, not just
routing. A *direction* is a coherent whole-film ATMOSPHERE: a named look + a lean toward certain register FAMILIES
+ a hero register (each beat is still its own design language; the direction EMPHASIZES families + sets the feel).
0. **Width by audacity (the risk budget).** `meta.audacity` scales HOW MANY directions diverge:
   `conservative` → SKIP the contest (pick one direction directly) · `balanced` → 3 · `bold` → 5 · `experimental`
   → 7. Get the width + seed palette: `python scripts/shot_templates.py --route "<topic>" --audacity <a> --out <out_dir>`.
1. **CONCEIVE topic-specific directions — do NOT just route the 6 seeds.** The 6 templates (product-demo /
   kinetic-editorial / cinematic-craft / data-story / retro-playful / terminal-technical) are a SEED PALETTE, not
   the answer. Read the comprehension brief + `content_plan.json` and **invent bold, divergent, topic-conceived
   atmospheres** for THIS subject (name each; pick its hero register + family lean + topic-bearing props). Reach
   the audacity width by mixing fitting seeds with bespoke directions. Force DIVERGENCE — the candidates must
   differ on look/motion/palette/silhouette, not be three flavours of the same. (A bespoke direction key is a
   slug like `molten-ledger` — `validate` allows non-seed keys, warns so you confirm it's intentional.)
2. **Render a short SAMPLE VIDEO per direction** — the user must SEE each direction MOVE (a text pitch or a lone
   still can't convey a design language; motion IS the language). `python scripts/contest_sample.py --route
   "<topic>" --audacity <a> --out <out_dir> --render` builds a ~6s mini-film per direction (its hero + 2
   representative registers, topic copy, through the real Film) → `<out>/_contest_<k>.mp4`. For a BESPOKE
   direction not in the seed set, hand the script the direction's own shot list (or build the mini-storyboard by
   hand and render it via `render_remotion`). ALSO render one still per direction at **`--frame=110`** (frame 0 is
   un-started; every hero ≥150f, so 110 = `CONTEST_FRAME` settled) so the mechanical diversity gate can run.
3. **DIVERSITY gate (mechanical).** `python scripts/contest_diversity.py <out>/_contest_*.png` — a flagged pair
   (clustered mode+palette+silhouette) means the divergence was theatre: REDIVERGE that pair (conceive a genuinely
   different atmosphere) before showing the user.
4. **JUDGE (the selection half).** Dispatch **`agents/shot-critic.md` in JUDGE mode** on the stills + the beats:
   it disqualifies any floor-breaker (blank/garbled/off-brief/illegible), ranks the survivors, and names ONE
   winner + a runner-up. A floor-breaking or off-brief candidate must NOT reach the user unranked.
5. **USER picks** from the judged finalists via `AskUserQuestion` (option prompt, winner first with "(Recommended)";
   point them at the **sample VIDEOS** `_contest_<k>.mp4` — text alone is not a basis to choose a look). Their pick is FINAL. Record on the storyboard:
   `meta.shot_template = <pick>` + `meta.shot_template_contest = {candidates:[all keys], winner:<pick>,
   user_pick:true, width:<N>, audacity:"<a>", judge_ranked:true}`. `validate.py` ERRORS a bold/experimental film
   with NO contest, checks the width matches audacity, and that the winner is the chosen direction.
6. **Apply it.** The chosen direction BIASES per-beat register selection toward its families (never two adjacent
   same-family): `python scripts/shot_director.py <out> --template <seed-key>` for a seed, or apply the lean by
   hand as you author `shot`s below.

## The mandate — clear AND bold AND meaningful
For each beat ask *"what is the clearest hand-written LANGUAGE for THIS idea?"* — match the beat's intent to a
register's "use when", never "which card layout". Then fill that register's props from the beat's own content so
it speaks the topic, not WorkBuddy. **Lean toward the chosen `meta.shot_template`'s families** (Step 0) while
keeping the family-variety rule.

**Every shot must ENCODE its beat, not decorate it.** Apply the litmus from `references/remotion-shot-authoring.md`:
*hide the caption — does the visual still carry THIS specific idea, and only this one?* A design that could sit
under any nearby caption, or reads as generic "science/tech atmosphere," is a FAIL — its structure must mirror the
content (symmetry / direction / accumulation / sparsity / cause→effect). See the anti-pattern catalogue there for
the concrete traps (radial-burst-for-RF, waveform-for-FID, mandala-for-k-space, glitch-for-aliasing, a diagram
where an equation is clearer, colored blocks instead of a real image). **When NO library register encodes a
topic-specific idea, BUILD a bespoke shot** (`src/shots/*.tsx`, registered in every sync point) rather than force
a near-miss — swapping among generic registers hits a ceiling and drags in leftover demo copy. **Reach for the
real-imagery tier on concrete topics** — composite a real image the design ACTS on (reconstructs / folds /
denoises), compute real data with numpy (FFT, partial reconstructions), credit CC-BY — keep the design language's
VIBE but fill it with real, sourced, generalizing content (the image is a `src` prop). **COHERE with the chosen
direction:** carry its palette/motion/motif across beats (family variety is about silhouette, not a licence to
switch visual worlds every beat). And **audit ALL beats** with the hide-the-caption test, not just flagged ones. **BOLDNESS is not optional — it scales with `meta.audacity`.** Clarity is the
floor, not the ceiling: reach past the OBVIOUS register for the surprising-but-apt one, especially on the hero +
climax beats. At `bold`/`experimental`, a mix of safe/expected registers is a FAILURE the shot-critic (S8) sends
back — commit registers that are memorable and unmistakably THIS film. For each beat, briefly note the
`rejected_default` (the obvious register you passed over) so the choice is a decision, not a reflex.

## Rules (all five bind)
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
5. **MARK ~2–3 chapter-break seams — the rest ride the default (set nothing).** Every seam is a gentle
   luminance-safe cross-fade by default; that already reads well and needs no authoring. On the FEW beats that
   open a new chapter, set `transition_style` on the INCOMING scene so the cut CLAIMS the relationship — chosen
   from the beats' `relation`, never decoration: a reveal / new-topic → `clock` or `wipe` (the frame opens); a
   forward push / building energy → `slide` (push); a payoff where the outgoing FORM becomes the incoming one
   (a solid → its particles) → `dissolve`; a CONTINUITY beat where the two shots should read as one continuous
   move (a chart collapses and the human takeaway grows from the same line, a converge → resolve) → `carry` (a
   collapse-to-line match-cut — the ONE mark that also works across a dark↔light seam, its neutral line being the
   luminance bridge). Two constraints: **budget ≤~3 marks** in a
   ≥10-beat film (marking every seam is as monotonous as marking none, and the shot-critic S2 flags it), and a
   mark only "takes" on a **same-luminance** seam — a dark↔light cut is auto-forced back to the safe fade
   (Film's pickPresentation guards against a bright edge slamming over a dark scene), so don't spend a mark
   there. No spins, ever. (Mechanism: `render_remotion.py` maps `transition_style` → the Film `transitionIn`.)

## Color-arc (a SOFT sequencing pass — after fit/family/boldness are settled)
Each shot has a ground LUMINANCE (dark / mid / light — `remotion/src/runtime/shotLuma.ts`). A film that flips
**dark↔light on nearly every beat STROBES**: even though each seam is smooth (the renderer forces a gentle fade
across a jump), the whole-film brightness *pulse* reads restless. So sequence a luminance **ARC, not a strobe** —
let brightness move in short **runs/gradients** (a few darks, then lift into the lighter beats, or the reverse),
reserving a hard dark↔light flip for a **deliberate jolt** (a reveal, a tonal turn). This is a TIE-BREAK only: it
never overrides register FIT, family variety, faithfulness, or boldness — when two equally-apt registers fit a
beat, prefer the one whose ground continues the run. `validate.py` warns when >60% of seams hard-flip (a strobe);
the deterministic fallback assigner already softens streaks. (The MARKED **carry** seam is the clean way to make
a *needed* dark↔light turn read as continuity rather than a flip — see Rule 5.)

## Output
Edit `storyboard.json`: set `meta.renderer:"remotion"` and, on every scene, `shot` (a valid id from
`remotion/src/shots/*.tsx`) + `shot_props` (an object; `{}` = the register's WorkBuddy-neutral defaults, which
you should usually override with topic copy). Then record your choices for the critic: a short `shot_rationale`
per scene (why this register, which family) is encouraged. `validate.py` errors on a missing/unknown `shot` or a
number-bearing register left on its demo default; `render_remotion.py` renders the chosen shots through the
data-driven `Film`. Keep a family-variety pass at the end: scan the shot sequence and swap any adjacent
same-family pair for an equally-fitting register from a different family.
