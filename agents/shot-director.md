# Shot Director (remotion bespoke-shot tier)

> **When this runs.** ONLY for a `meta.renderer:"remotion"` film — the bespoke-shot LIBRARY tier. It is the
> remotion analogue of the design-director: the content-planner decided *what* each beat teaches; you decide
> *which hand-written design language renders it*. If the deck is HTML/local, or the legacy
> `meta.renderer:"remotion-legacy"` cinematic tier, this file does NOT apply.

You assign every beat a **shot** — one register from `remotion/LIBRARY.md` (the hand-written components catalogued there) — and
its **topic copy** (`shot_props`). You write `scene.shot` (a register id) and `scene.shot_props` (an object) onto
each scene in `storyboard.json`. You do NOT change facts, narration, or beat order.

## Read first
0. **`references/remotion-shot-authoring.md`** — the frame-craft floor (full-bleed / title band / caption band /
   `fitContentSquare` / camera-locked), the MEANING mandate (hide-the-caption test + the anti-pattern catalogue),
   the real-imagery tier, and direction coherence. This is where films fail SILENTLY — read it before authoring.
1. `content_plan.json` — the ordered beats (learning_point, narration_intent, `visual_intent`, `relation`,
   `energy`, `stage`, `climax`/`hold`, and `source_ref`).
2. `remotion/LIBRARY.md` — the registers grouped into FAMILIES (A Product-UI · B Camera/space · C Kinetic
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

## Step 0.5 — DERIVE THE FORM VOCABULARY (do this BEFORE you open the catalogue)

**The single most important step, and the one this tier used to skip.** Step 0 conceives the film's
ATMOSPHERE from the topic — palette, type, motion. But a design language has a second layer, and it is the
one viewers judge as *appropriate* or *not*: the **FORM VOCABULARY**, meaning what kind of OBJECT each frame
is. A dictionary entry. A stratigraphic column. A ledger. A departure board. A score. A docket. A patient
chart. A patent plate.

Until now that layer arrived from `LIBRARY.md`. That is backwards, and it fails in a way nobody catches
without a human: **whatever the catalogue is mostly made of becomes every film's vocabulary.** This library
grew from AI-product films, so a city documentary came out of it speaking developer-tool — six terminal
shots (`$ dig --oudegracht`, `$ diff 1674 1826`, a `<think>` block), a SaaS dashboard under a children's
book character, a factory conveyor belt for people cycling to a station. 16 of 35 beats. Every register
passed its own gates. The defect was the ORDER OF OPERATIONS: shop first, then patch what the reviewer
objects to.

So: derive the vocabulary from the SUBJECT first, and only then ask whether the library happens to hold any
of it.

### How
Read the comprehension brief and answer one question: **how is this subject actually recorded, measured,
argued about and experienced, by the people whose subject it is?** Name **6–10 concrete FORMS**. For each:

```json
{"form": "stratigraphic column",
 "carries": "what lies under this ground, in order — a claim about DEPTH",
 "looks_like": "surface at the top, layers to their own thickness, depths ruled off at the left"}
```

Rules that make this a derivation rather than a shopping list:
1. **Each form must be a real artefact or instrument someone in that world would recognise** — not a generic
   chart type. "A bar chart" is not a form. "A tide gauge", "a docket entry", "a piano roll", "a museum
   label", "an exhibit sticker", "a flight strip", "a knitting chart" are forms.
2. **At least half must be forms this library does NOT already have.** If everything you name is already a
   register, you shopped. Go back to the brief.
3. **Write it to `meta.form_vocabulary`** — the whole list, as the artifact it is.

### Then, per beat
Choose the FORM first, from your own list. Only then ask the catalogue:
* a register already carries that form → use it, adapted (`shot_fit.verdict: "fit"`/`"adapt"`);
* nothing does → **BUILD it** (`"build"`, `scripts/register_shot.py`). This is the normal case on a subject
  the library has not met, not an emergency.
* Record which form the beat realises: **`shot_fit.form` MUST name one of `meta.form_vocabulary`.**
  `validate.py` ERRORS on a beat whose `shot_fit.form` is missing or not in the list — which is what stops
  the catalogue from quietly supplying the vocabulary again.

### What this is not
It is not a licence to build 35 one-offs. A form used once is a one-off; a form used across films is a
register. Build the FORM, give it an argument shape and props, and it joins the library for every later film
— that is how family J (survey: gazetteer entry, map plate, strata column, plan palimpsest, tally ledger,
museum label) came to exist, one film too late.

## Step 0.6 — Extract the Design DNA (the GLOBAL visual system every shot inherits)
The chosen template is **NOT a set of reusable frames — it is the whole film's visual system.** Before authoring a
single shot, expand the template into an explicit **Design DNA** and write it to `meta.design_dna` (a reviewable
artifact, not just a label). The DNA is the *shared grammar* every shot wears; a library register contributes its
STRUCTURE (composition + motion + information hierarchy), the DNA contributes the VISUAL IDENTITY. Required keys
(match `remotion/src/runtime/dna.tsx` `DesignDNA`): `id` · `fontDisplay`/`fontMono`/`fontBody` · `bg`/`bgGrad`/
`fg`/`dim`/`accent`/`accent2`/`onAccent`/`surface`/`surfaceBorder`/`line` · `radius`/`borderWidth` · `motion`
(`type`/`execute`/`smooth`/`mechanical`) · `decoration` (`prompt`/`status`/`breadcrumb`/`cursor`/`scanline`/`grid`/
`line-numbers`) · `uppercaseLabels`/`labelSpacing` · `atoms` (the FORM each content atom speaks — see
`remotion/src/runtime/atoms.tsx`). A **built-in preset** exists for known templates (terminal →
`TERMINAL_DNA`), auto-applied by `render_remotion.py` when you set `meta.shot_template` and author no `design_dna`;
authoring the explicit block is preferred (it's the reviewable Design DNA and lets you tune tokens). **The DNA is
provided to the Film at render (a `DesignDNAContext`) and every migrated register reads it via `useDNA()`**, so one
DNA makes 19 different compositions read as one visual universe — the remotion analogue of the html tier's
`theme.css`. `validate.py` warns when a themed film has neither an explicit `design_dna` nor a preset-mapped template.

**A COMPLETE worked block — copy this shape and retune every value to the topic** (a partial DNA no longer crashes
the render — Film normalises it through the neutral preset — but every key you omit silently borrows a neutral
value, and `validate.py` will name what is missing):

```json
"design_dna": {
  "id": "terminal",
  "fontDisplay": "\"JetBrains Mono\", \"PingFang SC\", \"Hiragino Sans\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", ui-monospace, monospace",
  "fontMono": "\"JetBrains Mono\", \"PingFang SC\", \"Hiragino Sans\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", ui-monospace, monospace",
  "fontBody": "\"JetBrains Mono\", \"PingFang SC\", \"Hiragino Sans\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", ui-monospace, monospace",
  "bg": "#080b11", "bgGrad": "radial-gradient(120% 120% at 50% 0%, #0d141c, #05070b 72%)",
  "fg": "#d7e3ef", "dim": "#5d7186", "accent": "#37d68a", "accent2": "#7ee0ff", "onAccent": "#03130c",
  "surface": "#0d1219", "surfaceBorder": "#1d2a36", "line": "#16202b",
  "radius": 4, "borderWidth": 1,
  "motion": "execute",
  "decoration": ["prompt", "status", "breadcrumb", "cursor", "scanline", "grid"],
  "uppercaseLabels": true, "labelSpacing": "0.12em",
  "uniformType": true,
  "atoms": {"bar":"block","figure":"mono","list":"tree","label":"prompt","divider":"scanline","marker":"caret"}
}
```

`atoms` declares which FORM this system speaks for each content part (see `remotion/src/runtime/atoms.tsx`);
an omitted atom renders its neutral form, so a partial declaration is valid.

**Every family named in `fontDisplay`/`fontMono`/`fontBody` must be one `remotion/src/runtime/fonts.ts` actually
loads** — `Space Grotesk`, `Playfair Display`, `JetBrains Mono`, `Bangers`, `Inter`, `Source Serif 4`, `IBM Plex
Sans`, `IBM Plex Mono`, `Bodoni Moda`, `Baloo 2`. A family outside that list silently falls back to the browser's
generic (a test, `test_every_declared_family_is_actually_loaded`, catches this in the built-in presets, but a
hand-authored `design_dna` is not covered by it). Every stack must also end with the CJK chain shown above plus a
generic family, exactly as `TERMINAL_DNA` does — none of the ten loaded faces covers CJK, so a stack without the
chain silently drops Chinese text to a system default. See `references/remotion-shot-authoring.md` §C3 for how
this reaches the shots.

Two keys are BEHAVIOUR-bearing, not decoration, so choose them deliberately:
- **`id`** selects the film's native SEAM grammar (`terminal` → a console screen-clear sweep · `product`/`apple` →
  a slide push · `editorial`/`blueprint` → a sheet wipe · anything else → the safe cross-fade). Use a known id
  unless you want the neutral seam.
  This reaches EVERY UNMARKED cut, which is nearly all of them, so read Rule 5 before you lean on it: a native
  cut on all of them erases the ~2–3 marked ones, and the plain cross-fade is the CORRECT default for most
  films rather than a decision left unmade. `"seam": {"type": "fade"}` opts a preset id back out.
- **`uniformType`** — `true` forces ONE font across every shot (right for a mono/terminal world; it is the single
  strongest style signal). Leave it out for a MIXED-type system (editorial serif + sans, product geometric), where
  each element picks `fontDisplay`/`fontBody` itself.

All six selectable directions map to a built-in preset (`terminal-technical`, `kinetic-editorial`, `product-demo`,
`cinematic-craft`, `data-story`, `retro-playful`), so `meta.shot_template` alone already themes the film.
**Consistency ≠ repetition:** the DNA does NOT make every frame a terminal window — a beat may be a big metric, a
chart, a diagram; it just inherits the type/palette/container/motion/annotation grammar. Prefer subtle structural
consistency over repetitive decoration (a shot needs 2–3 recognizable DNA cues, not a forced terminal box).

## Step 0.7 — Style Assimilation + the three-layer model (run per shot, for ANY chosen style)
The template is a GRAMMAR, not a layout template — and the trap cuts BOTH ways: too weak = reskin a generic
register (a gauge tinted to the accent); too strong = make EVERY beat the same explicit style CONTAINER (for
terminal, a black window box; for editorial, an identical magazine spread). Split the style into **three layers**
(§C2): **(1) Surface** — only 2-3 ANCHOR beats show the explicit container (terminal window / glass hero /
drawing sheet). **(2) Grammar** — every OTHER beat inherits the DNA (type, palette, the style's syntax/marks,
status/annotation cues) on OPEN canvas, with a layout chosen PER CONTENT so beats don't all look alike. **(3)
Motion** — reveal as the style's native ACTION → RESULT (terminal: `$ cmd` runs → output grows; product: a soft
scale-in; blueprint: a measured draw-on). Then **ASSIMILATE each shot**: translate its content idea into the DNA
across ≥2-3 of {typography, layout, components, motion, transition, narrative-metaphor}, and **reject any shot
that could be dropped unchanged into a different style without anyone noticing.** For terminal use the `Term*`
family + `TermFrame` (default OPEN, `framed` only on anchors); for a style with no family yet, build style-native
shots the same way OR use the library registers reading the DNA tokens — never a reskinned generic component.
This is style-AGNOSTIC: it holds for terminal, editorial, product/apple, blueprint, or any `meta.design_dna`.

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
switch visual worlds every beat). And **audit ALL beats** with the hide-the-caption test, not just flagged ones.

**KEEP THE STYLE, REDESIGN THE REST — never text-swap a register's demo (临场设计优化 — see
`references/remotion-shot-authoring.md` §B2).** A register is a STYLE (its vibe, motion, material, typographic
attitude) wrapped around DEMO scaffolding — placeholder mini-widgets, generic glyphs, demo-length labels, a stock
module count and layout. **Keep the style — and keep any stock module that ALREADY encodes THIS topic's content —
and treat the REST of the demo scaffolding as a mannequin to rebuild.** The DEFAULT
posture on EVERY beat, EVERY topic is to redesign both the CONTENT *and* the register's own MODULES/COMPONENTS so
its structure *represents THIS topic's content* — not merely to change the words. Concretely: swap placeholder
motifs for ones that MEAN the item (a product tile shows that product's glyph, not a random chart); re-shape the
MODULES to the content's real relationship (parallel questions stack — they don't get sequence-arrows; a "loop"
is a cycle, not a row; a hierarchy nests, not lists); add/drop/recompose components so the beat's specific idea
is the thing on screen; and **size for the REAL copy** — long labels overflow a box tuned to short demo words,
offset arrows land on long phrases, a tiny marker vanishes (frame-craft §A.8). Litmus: *would this beat look the
same on a totally different topic with only the words changed?* If yes, you text-swapped — redesign it.
**Judgment, not reflex — don't blindly rewrite what already fits.** If a register's stock module/component ALREADY
expresses THIS beat's content well (its structure genuinely encodes the idea, not just the demo's), KEEP it —
changing it only to look different is as wrong as text-swapping, and wastes the register's proven strengths. Decide
per module: does it carry the DEMO's meaning or THIS topic's? Keep the ones that fit, redesign the ones that don't,
and record BOTH sides in `shot_adaptation` (`kept` = the style + the modules that already fit; `redesigned` = what
you rebuilt). **Building a small in-style variant is the NORMAL move, not a last resort:** whenever the register's stock modules don't
carry the idea, write a variant that keeps its VIBE but is composed around the real content; only when the fix is
a pure demo-length assumption (a fixed label width, an un-padded box) FIX the shared register at the source so
every future film benefits. **Record the redesign per scene in `shot_adaptation` = `{kept, redesigned,
topic_idea}`** — what STYLE you kept, which MODULES/components + content you rebuilt for this topic, and the
topic-specific creative idea the shot now encodes. It is a REQUIRED artifact (validate.py WARNs when it's missing
or `shot_props` is empty; shot-critic S10 checks the note against the rendered frame): writing it forces the
redesign to be a decision, not a reflex. Always still-render a shot with its ACTUAL
props before trusting it (`npx remotion still … --props='<real props>'`). **On a non-16:9 film (`meta.aspect` !=
16:9): still-render EVERY chosen shot AT that aspect** (`--props '{"aspect":"9:16",…}'`) and fix/swap any that don't
reflow — a multi-column layout must STACK in portrait, wide elements must not run off-frame (references/remotion-shot-authoring.md
§A.9); most centered/stacked/chart shots are fine, the fixed multi-column + wide-horizontal ones need this pass.
**BOLDNESS is not optional — it scales with `meta.audacity`.** Clarity is the
floor, not the ceiling: reach past the OBVIOUS register for the surprising-but-apt one, especially on the hero +
climax beats. At `bold`/`experimental`, a mix of safe/expected registers is a FAILURE the shot-critic (S8) sends
back — commit registers that are memorable and unmistakably THIS film. For each beat, briefly note the
`rejected_default` (the obvious register you passed over) so the choice is a decision, not a reflex.

## Rules (all six bind)
0. **Match the beat to a register — or BUILD one. Judge, per beat, and record the judgement.**
   Before rule 1, ask what the beat is actually ARGUING and whether any register's *structure* already
   carries that shape. Record the answer on the scene as **`shot_fit` = `{verdict, why}`**:
   - **`fit`** — the register's own structure carries this argument as-is.
   - **`adapt`** — the structure carries it; its modules/components get redesigned for this content (§B2).
   - **`build`** — no register's structure carries it, so you AUTHOR A NEW ONE.

   **The line between `adapt` and `build` is structure vs sizing** (`references/remotion-shot-authoring.md`):
   redesigning a register's modules is `adapt`; needing a different *shape of argument* is `build`. The test
   that settles it: could you fit this beat into the register only by **swapping its words**? Then the
   register does not carry the argument — build.

   **Building is one command, and cheap on purpose:**
   ```
   python3 scripts/register_shot.py <Id> <FamilyLetter> --use-when "<one line>"   # stub + all 5 sync points
   # write the shot body, then:
   python3 scripts/measure_ground_luma.py --only <Id>     # sanity-check its ground
   python3 scripts/shot_proof.py <out_dir>                # frame-craft, palette, reuse (rendered by
                                                        # default now; --no-stills for a fast source-only pass)
   ```
   It used to mean editing five files by hand, four of which fail silently — which is exactly why in
   practice nothing was ever built and every beat got matched to the closest existing register instead.

   **A new register must be REUSABLE, not a one-off.** It carries an ARGUMENT SHAPE — "two populations a
   measure cannot separate", "correlated vs independent failure" — with the topic arriving entirely through
   props, so the next film making that kind of claim can reach for it and the library compounds. Its
   DEFAULTS stay generic demo copy. `shot_proof.py` ERRORS if a register hardcodes this film's own prose.
   Give it a family letter; if it fits none of A–Z, open a two-letter one (AA, AB, …) — the set is open.

   **A THIN FAMILY is a build signal, not a menu.** LIBRARY.md opens with a generated family census: nine
   of the twenty-five families hold ONE register. So "vary the family" quietly pushes every film toward the
   four big ones (D, A, C, G), and when a beat's argument wants a thin family there is nothing to choose
   between — its single member either carries the argument or it does not. If it does not, that is the
   clearest build case there is, and settling for the only member is how a beat ends up with a design that
   is merely ADJACENT to its meaning. Notice which of the two reasons put you in a family: because it fits,
   or because it was stocked.

   `validate.py` warns when no beat records `shot_fit` (the judgement was never made, so "no register can
   draw this" could never surface) and when EVERY beat records `fit` (on a topic-specific film, the
   signature of matching the catalogue rather than judging it). `critic_brief.py` reports, to the reviewer,
   whether the film built anything at all and which thin families it leaned on.

1. **Match intent → register.** `statement`→a title/kinetic register (CinematicTitle, FocalIsolation,
   KineticManifesto, LiquidChrome, BrutalistType, SwissEditorial); `sequence`→ExplodedSchematic/TimelineTravel/
   CommandSummon; `structure`→CollaborativeCursors/KnowledgeGraph/MapRoutes/DataOrrery/WireGlobe/BlueprintGrid;
   `list`→BlockAssembly/TemporalAccelerate; `metric`→ChartLive/BlueprintGrid(counter)/PhysicsStack. The `climax`
   beat gets a payoff register (ParticleForm/RadialBurst/LightTrails/SpotlightStage/LiquidFill); the `close`/`hold`
   beat gets a premium title (LiquidChrome/HoloFoil/CinematicTitle/SwissEditorial). Use the "use when" as the map.

   **A CONCRETE topic can want a real PHOTOGRAPH as the register itself, not as a texture behind one.** When the
   beat's claim is *look at the actual thing*, reach for **PhotoPlate** (LIBRARY 171): the photograph IS the
   frame, and the film's own numbered marks sit at points IN it, arriving as the narration names them — so the
   picture carries the argument instead of illustrating it. The library's other image registers answer different
   questions: **ScanReconstruct** = revealed by its own process · **MuseumLabel** = the object beside its
   catalogue label · **RealVersus** = A against B. Decide this HERE, at register selection: on a delivered film
   about a physical city, with license-clean photographs available, real images occupied 5.3% / 8.5% / 16.3% of
   the frame — the evidence shipped as a footnote to a drawing of itself. Fetch with `python3
   scripts/imagefetch.py "<subject>" <out_dir>/media/<name>.jpg` (license-clean Wikimedia; it writes the sidecar
   `<name>.jpg.json` beside the file, naming the real author + licence). **Take the credit FROM that sidecar —
   never type one from memory** (`imagefetch.attribution_line()` builds it): `validate.py` ERRORS on a beat
   showing an image whose sidecar author it does not credit, because a wrong CC-BY line credits someone else's
   photograph to a stranger.
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

   **The film's NATIVE cut is OPT-IN, and NOT setting it is the right answer for most films.**
   `meta.design_dna.seam` — and a preset `meta.design_dna.id`, Step 0.6 — replaces every UNMARKED cut with the
   design system's own move. Measured on a delivered film: it turned 31 of 34 cuts kinetic, so the 3 deliberate
   marks read exactly like the 31 that meant nothing — the film LOST its punctuation to the feature meant to give
   it a voice. A plain cross-fade on the unmarked cuts is the CORRECT default and a finished decision, not a
   missing one. Declare a `seam` only for a world with a genuine native ACTION (a terminal clearing its screen);
   on a preset id whose world has none, opt back out with `"seam": {"type": "fade"}`. `validate.py` warns when a
   declared seam swamps the marks.

   **Mark by MEANING — completeness is not your problem.** `python3 scripts/seam_plan.py <out_dir>` runs after
   you, as a verify-and-fill pass: it derives marks from each beat's `relation`, and SKIPS any beat you already
   marked (an explicit mark always wins, so it never competes with you). It exists because a delivered 35-beat
   film used none of the vocabulary — all 34 seams the anonymous default — and it mirrors the renderer's
   luminance guard: on a dark↔light seam it marks the `carry` instead, the one cut whose bridge line survives
   that guard, rather than a kinetic mark Film.tsx would silently downgrade to a fade.

## The camera — a move needs a CAUSE (per beat, budget 2–4)
A scene may carry **`camera` = `{move: "push"|"pull"|"hold", amount: 0.045}`**. This is not a Ken Burns drift:
the tier's earlier camera was a film-wide sinusoidal wander with no relationship to anything being said, and
motion with no cause reads as a wobble the moment a viewer notices it — which is why it was switched off
entirely, an over-correction. So derive the move from what the beat is FOR:
- **`payoff` → `push`** — the beat where the argument lands: look closer at what is here.
- **`close`, and the OPENING beat → `pull`** — here is the whole of it, from either end of the film.
- **everything else HOLDS** (set nothing). Budget **2–4 moving beats in a whole film, spaced apart** — a film
  whose camera always moves has no camera, exactly as a film that marks every seam has no punctuation.

**Spend a push only on a frame that HOLDS something to look closer AT.** A shot reveals over roughly t 0.05–0.45,
which is why the move runs 0.28–0.88 — it rides `useT()`, so it never runs over a cut and it lands on SETTLED
content, and `amount` is clamped to what the caption band can absorb. A push into two rows of text magnifies
nothing; a push into a photograph, a plate, a schematic with detail in it is the beat worth spending on. Check
what the beat's shot actually holds before marking it. `seam_plan.py` fills these on the same rule and skips any
beat you authored.

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
`remotion/src/shots/*.tsx`) + `shot_props` (an object of TOPIC copy — never leave it `{}`, which ships the
register's demo mannequin) + **`shot_adaptation` = `{kept, redesigned, topic_idea, theme_cues}`** (REQUIRED — the
style AND any stock modules that ALREADY fit the topic that you kept, the modules/components + content you rebuilt
for this topic, the topic-specific idea the shot now encodes, and — on a DNA-themed film — **`theme_cues`: the 2-3
concrete cues that tie THIS shot to the global visual system** (e.g. `["mono heading","▸ prompt","terminal grid",
"green accent"]`) so the Design DNA verifiably runs through every frame; per the KEEP-THE-STYLE-REDESIGN-THE-REST
rule above — keep what fits, redesign what doesn't, don't blindly change everything). Also set **`shot_fit` = `{verdict: "fit"|"adapt"|"build", why}`** per scene (rule 0) — the judgement of
whether a register's structure actually carries the beat's argument, and the ONLY thing that can surface
"nothing in the library can draw this". On the FEW beats that earn them, also set `transition_style` (Rule 5) and `camera` (the camera section); `python3 scripts/seam_plan.py <out_dir>` then fills the beats you left and skips every one you authored. Then record your choices for the critic: a short
`shot_rationale` per scene (why this register, which family) is encouraged. `validate.py` errors on a
missing/unknown `shot` or a number-bearing register left on its demo default, and WARNs on empty `shot_props` or a
missing `shot_adaptation` (a raw text-swap); `render_remotion.py` renders the chosen shots through the data-driven
`Film`. Keep a family-variety pass at the end: scan the shot sequence and swap any adjacent same-family pair for
an equally-fitting register from a different family.
