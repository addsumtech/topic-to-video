# Remotion2 — Bespoke Shot Library (134 design languages)

Each shot is a **hand-written, deterministic component** (`{default Component, DURATION}`) authored in
1920×1080, driven by `useT()` (0→1) + the shared `runtime/motion.ts` kit. No generic template funnel —
every register is its own file. Renderable standalone: `npx remotion still src/index.ts <Id> out.png --frame=N`.

**Every register reads the film's DESIGN DNA.** All 134 shots call `useDNA()` and paint from the film-wide token
set (`runtime/dna.tsx`), so whichever direction is chosen, the whole film shares one visual system; with NO DNA a
shot renders exactly its original look. Depth varies by shot — `python scripts/dna_audit.py --depth` reports it —
and two families are STYLE-NATIVE, written for one DNA rather than adapted to it: **Term\*** (terminal) and
**Ed\*** (editorial) below. See `references/remotion-shot-authoring.md` §C2 for the three-layer model.
Four shots draw their headline number through the shared content atom `Figure` (`runtime/atoms.tsx`) —
`TermCounter`, `EdStat`, `ChartLive`, `VelocitySnap` — and one, `TermBars`, draws its quantity through `Bar`;
those parts change FORM with the DNA, not just colour. `List`/`Label`/`Divider`/`Marker` have no consumer
yet in this library — they exist for new shots and opportunistic use. See
`references/remotion-shot-authoring.md` §C2 "Content ATOMS" for the mechanism and the full list of shots
deliberately left un-migrated.

**Registering a new shot — every sync point** (a miss is silent; `tests/test_remotion.py` gates the starred ones):
`src/shots/<Id>.tsx` → `src/registry.ts`\* → `src/Root.tsx`\* (standalone preview) → `runtime/shotLuma.ts`\*
(measured ground luminance) → `scripts/shot_director.FAMILY`\* (variety) → this file → then
`python scripts/gen_dna_ground.py` if the shot paints its ground from the DNA\*.

**Selection contract (for the film's design step):** pick a register per beat by matching the beat's *intent*
to the "use when" below, and vary the FAMILY across the film (never two adjacent shots from the same family).
Every shot accepts overridable copy via constants at the top of its file (wordmark/tagline/labels).

**The family set is OPEN-ENDED — grow it.** Families are a variety axis, not a fixed taxonomy: when a bold new
design language doesn't fit an existing bucket, **open a new family letter** (add it here + to
`shot_director.FAMILY`). New families cost nothing mechanically (the variety rule only checks that adjacent
beats differ). Novel and daring beats a clean taxonomy — reach past the obvious register.

## A · Product-UI / SaaS-film — motion of a working interface
1. **CollaborativeCursors** — multiplayer cursors build a deliverable on an aligned grid. *Use: teamwork / "your AI team".*
2. **CommandSummon** — command palette typed → checklist ticks. *Use: "just ask it" / invoke.*
3. **TemporalAccelerate** — task list blurs past, a timer snaps. *Use: speed / time saved.*
4. **VelocitySnap** — UI panels snap into place, "0ms". *Use: instant / responsiveness.*
5. **CursorStory** — one hero cursor + ⌘K chips. *Use: a single guided action.*
6. **ScreenBubble** — app UI + camera bubble walkthrough (Loom). *Use: demo / show-me.*
7. **AnswerStream** — query → streaming answer + source chips (Perplexity). *Use: Q&A / knowledge.*
8. **ChatThread** — chat bubbles + typing indicator. *Use: conversational.*
9. **BlockAssembly** — blocks snap in top-down (Notion). *Use: composing an output/doc.*
10. **CodeCompose** — a live IDE types syntax-highlighted code, runs → ✓ done. *Use: it writes+runs the work.*
11. **LiquidGlass** — Apple-2026 frosted-glass lens glides over a task list, settles → ✓. *Use: premium polish / focus.*
56. **BentoReveal** — a bento grid (hero cell + mixed widgets) whose tiles pop in and assemble into a finished dashboard. *Use: the product surface / "your whole workspace".*

## B · Camera / space — a world larger than the frame
12. **InfiniteCanvas** — deep zoom across a canvas (Miro). *Use: big-picture → detail.*
13. **TimelineTravel** — pan a horizontal timeline. *Use: process / sequence.*
14. **MapRoutes** — glowing routes hub→spokes on a night map. *Use: integrations / reach.*
15. **ExplodedSchematic** — a pipeline explodes into labeled parts. *Use: how-it-works.*
51. **CubeRotate** — content on the four faces of a 3D cube; the camera orbits and holds each face. *Use: one subject, several sides / a loop.*
62. **CrashZoom** — a wide overview grid holds, then the camera PUNCHES in on one target tile (speed lines) until it fills the frame. *Use: overview → the one that matters / zoom to the detail.*
100. **TerrainFly** — a 3D wireframe heightmap terrain scrolls toward the viewer in perspective (hills drift from the horizon), grid coloured by elevation, fog + horizon glow. *Use: a landscape / journey / "new ground ahead".*

## C · Kinetic type & title
16. **KineticManifesto** — phrases rush the Z-axis. *Use: manifesto / values.*
17. **FocalIsolation** — blur everything but the key phrase. *Use: one emphasis.*
18. **SwissEditorial** — flush-left word snaps WORK→SHIP→DONE + marquee ticker. *Use: bold editorial brand.*
19. **BrutalistType** — raw grotesque + RGB-glitch + hard blocks. *Use: aggressive / anti-slick statement.*
20. **LiquidChrome** — flowing liquid-metal wordmark + chromatic fringe. *Use: premium hero title.*
21. **HoloFoil** — iridescent holographic-foil wordmark + sheen + sparkle. *Use: playful-luxe brand.*
22. **CinematicTitle** — letterboxed film title, lens-flare sweep, dust. *Use: open / close title.*
23. **BokehPull** — cinematic focus-pull from bokeh haze to a crisp wordmark. *Use: reveal / "in focus".*
24. **NeonGrid** — synthwave perspective grid + neon wordmark. *Use: energetic launch hero.*
25. **AnalogTape** — VHS/CRT title (RGB split, scanlines, OSD). *Use: nostalgic / authentic.*
26. **AsciiField** — an AMBER phosphor char field that DECODES a word in place. *Use: code / hacker beat.* (amber + static decode — vs **CodeRain** M's green FALLING rain.)

## D · Data / technical
27. **ChartLive** — glowing line+area draws, a counter ticks. *Use: a metric / result.*
28. **BlueprintGrid** — Vercel blueprint: grid, dimension lines, crosshair, mono. *Use: spec / precision / local-only.*
29. **KnowledgeGraph** — a node/edge constellation grows. *Use: connected workspace / second brain.*
30. **WireGlobe** — rotating wireframe globe + integration nodes + arcs. *Use: global / connected to everything.*
31. **DataOrrery** — labeled nodes ORBIT a core on tilted rings. *Use: your work in motion / ecosystem.*
90. **ChartRace** — horizontal bars grow at different rates and RE-RANK as they overtake (smooth soft-rank slide), counters ticking, leader glowing. *Use: who pulls ahead over time / a ranking race.* (number-bearing)
52. **OdometerRoll** — a big metric where every digit is a mechanical reel that spins through 0-9 and snaps, staggered. *Use: a single headline number, felt.*
57. **GaugeCluster** — a panel of circular gauges sweep their arcs; the hero gauge's needle rises and its value locks. *Use: live status / health / a KPI panel.*
65. **HudReticle** — a sci-fi FUI: corner brackets snap around a subject, a dashed scan ring rotates, readouts type in, then LOCK (goes green). *Use: targeting / analysing / "locked on".*

### D · terminal-NATIVE family (`Term*`) — the console idioms themselves
Written FOR the terminal DNA (they read `TermFrame`, which defaults to an OPEN canvas — a window only on the 2-3
anchor beats you pass `framed`). Do not stack them: they share family D so the adjacency rule already spaces them.
124. **TermBars** `title, rows[{label,pct,tag}]` — a block-bar readout `[███░░] 90% PASS`. *Use: a metric/benchmark, natively.*
125. **TermTree** `root, items[]` — an `ls`/tree listing that types itself out. *Use: structure / what's inside.*
126. **TermLog** `lines[{t,text,level}]` — a build/run log streaming with levels. *Use: a process happening now.*
127. **TermGitLog** `entries[{hash,msg,tag}]` — a commit history. *Use: lineage / how it evolved.*
128. **TermCounter** `label, value, note` — a huge mono figure counting up after a command. *Use: one headline number.*
129. **TermTable** `cols[], rows[][]` — a mono comparison table drawing row by row. *Use: A vs B on several axes.*
130. **TermDiff** `title, minus[], plus[]` — `-`/`+` gutters, red/green. *Use: before → after / what changed.*
131. **TermThink** `prompt, thoughts[], answer` — a `<think>` stream resolving into an answer. *Use: reasoning made visible.*

## E · 3D / material
32. **MaterialHero** — real 3D torusKnot (R3F/WebGL), studio-lit. *Use: a hero object beat.*
53. **CardFlip3D** — a row of cards flip 180° on Y (CSS 3D), a sheen at the seam, the payoff on the back. *Use: question → answer / before → after pairs.*
58. **FractureIn** — 25 tiles fly in from scattered 3D space and lock centre-out into a hero poster, then the title resolves. *Use: many parts → one picture / a bold reveal.*
61. **CardStack3D** — cards spring up into a pile, then fan out into a 3D arc (tone-edged), labels facing camera. *Use: a deck of capabilities → laid out in hand.*
66. **DataMonolith** — a nighttime skyline of glowing data towers rises from a perspective grid floor (caps + reflections), the hero tower pulsing. *Use: data as architecture / scale / growth.*
74. **MorphForms** — a rotating 3D point-cloud morphs sphere → cube → torus → sphere, depth-shaded (pure math, no WebGL). *Use: one idea, many shapes / an abstract kinetic hero.*

## F · Fluid / liquid / light — physical-feeling liquids & light (vs K = computed algorithmic fields)
33. **AuroraFlow** — Stripe/Vercel flowing gradient blobs + type. *Use: calm premium ambient (soft gradient BLOBS — cf. FlowField's discrete streamlines).*
34. **LiquidMorph** — iridescent blob morphs through ask/draft/done glyphs. *Use: transformation.*
35. **LiquidFill** — gooey vessel fills, % counts, checkmark. *Use: progress / completion.*
36. **ParticleForm** — a point-cloud assembles into a check. *Use: many parts → one result.*
38. **RadialBurst** — kaleidoscopic radial bloom to a hub. *Use: everything-at-once / celebration.*
39. **LightTrails** — long-exposure neon ribbons trace a checkmark. *Use: "done in one motion" / kinetic flourish.*
76. **MetaballMerge** — gooey liquid blobs orbit, MERGE into one mass and split through the classic SVG goo filter, a wordmark on the fluid. *Use: liquid-glass / fluid / "many drops, one flow".*
84. **InkBloom** — a drop of ink DIFFUSES in water: feathery tendrils radiate + soft clouds spread (turbulence-displaced), blooming behind a wordmark on a pale ground. *Use: it spreads / reach / organic growth.*
95. **LiquidMetal** — a chrome/mercury blob flows + merges (goo filter) with a banded reflection gradient, on a soft lavender/icy/beige palette, chrome wordmark on top. *Use: premium "liquid chrome, alive" hero (2026).*

## G · Illustrated / craft styles (the "style" axis)
41. **HandDrawn** — riso ink sketch draws on (You→WorkBuddy→Done). *Use: human / hand-made.*
42. **CartoonPop** — cel-shaded cartoon mascot zaps tasks → DONE! *Use: playful / friendly.*
43. **HalftonePop** — comic Ben-Day pop-art burst "SHIP IT!". *Use: loud fun highlight.*
44. **ClayStack** — soft pastel clay blocks stack + clay check. *Use: tactile approachable build.*
45. **PaperCutout** — layered paper-cutout parallax diorama. *Use: warm storybook.*
46. **SpotlightStage** — theatrical spotlight reveals PLAN→BUILD→SHIP. *Use: dramatic three-step.*
47. **PixelBuild** — 8-bit pixel checkmark assembles + CRT HUD. *Use: retro-game / "level complete".*
64. **RisoPrint** — a risograph wordmark on cream paper: pink + blue ink channels start misregistered and snap into registration (grain + halftone). *Use: warm hand-printed craft / a LIGHT-ground title.*
85. **ComicPanels** — a comic page: action panels (speed-lines + burst captions) snap in one by one, building to a full-width SPLASH payoff panel. *Use: a process as a comic beat / playful sequence.*

## H · Comparison
48. **BeforeAfterSlider** — slider wipes rough draft → board-ready. *Use: quality / transformation.*
54. **QuadSplit** — the frame splits into a 2×2 of micro-panels (each a distinct accent + motif), then one hero panel takes the whole frame. *Use: four angles → the one that matters.*
59. **PositioningMatrix** — a 2×2 axes map; item dots drift to their spots and the hero lands in its quadrant (ring + label). *Use: positioning / where things sit / who leads (qualitative).*
63. **VersusSplit** — a head-to-head split screen: two contenders slide in across a diagonal seam, a VS badge slams, the winner side glows. *Use: A vs B / this beats that (qualitative).*

## I · Mechanical / tactile-physical
49. **SplitFlap** — Solari flap board riffles + settles to the message. *Use: status flips to done / announce.*
50. **PhysicsStack** — weighty bars DROP + bounce-settle into a chart. *Use: tactile results / a week of output.*
55. **GearTrain** — interlocking gears mesh and turn in a chain (hubs carry the steps); the last gear locks the payoff. *Use: mechanism / one turn drives the next.*
60. **ConveyorBelt** — items ride a scrolling belt through a stamp press and exit finished (✓). *Use: assembly line / "it just processes everything".*

*(J · Experimental type — RETIRED: its one shot folded into P; the letter J is free for a future language.)*

## K · Generative — computed fields, not gradients
68. **FlowField** — hundreds of streamlines trace a static curl field and draw on in waves, revealing an ambient generative field with a centred wordmark. *Use: flow / everything moving as one / ambient hero.*
71. **LowPolyForm** — a jittered low-poly triangle mesh assembles centre-out, colour-graded across a duotone, with a wordmark over it. *Use: faceted crystalline hero / "many facets, one form".*
83. **KaleidoMandala** — an N-fold mirror-symmetric kaleidoscope of shapes blooms + rotates with a colour cycle, settling behind a wordmark. *Use: order out of many / an ornate ambient hero.*
88. **RidgeField** — stacked ridgeline curves (the "Unknown Pleasures" plot): peaked lines each filled to occlude those behind, rippling as a wave passes, revealing bottom-up. *Use: patterns in the noise / a data-landscape hero.*
98. **GameOfLife** — Conway's cellular automaton evolves from a fixed seed (recomputed to the current generation each frame — deterministic + seekable), living cells glowing, a wordmark over the emergent order. *Use: simple rules → complex life / emergence.*

## L · Editorial / print — designed page systems
(see also **RisoPrint** in G — a riso print title.)
69. **MagazineSpread** — a designer editorial cover sets itself: serif masthead, hairline rule, hero colour block, a word-by-word feature headline, deck + column rules. *Use: an editorial section opener (LIGHT ground).*
70. **RansomZine** — a punk cut-out ransom-note collage: each letter a torn paper scrap in a different colour + typeface, taped down askew, with a marker scrawl. *Use: loud DIY / anti-slick statement.*

### L · editorial-NATIVE family (`Ed*`) — the print idioms themselves
Written FOR the editorial DNA (they read `EdFrame`: a kicker + hairline accent rule + serif body, eased reveals;
`framed` turns the ruled surface on for an anchor beat).
132. **EdStat** `kicker, value, unit, caption` — a magazine pull-stat: a huge serif figure (width-aware, so a big number stays in frame) under a kicker + rule. *Use: one headline number, in print. (number-bearing)*
133. **EdTimeline** `kicker, entries[{date,title,note}]` — a ruled dated chronology. *Use: lineage / how it evolved.*
134. **EdCompare** `kicker, left{head,body}, right{head,body,hero}` — a two-column spread, a dimmed foil vs a hero column. *Use: this vs that / the divide.*

## M · Glitch / digital-decay
72. **GlitchDatamosh** — a word tears out of digital noise: RGB-split channels drift, displacement bands stutter, scanlines + block noise flicker, then the signal RESOLVES clean. *Use: digital / disruption / noise → clarity.*
91. **CodeRain** — Matrix-style digital rain: glyph columns fall with a bright head + fading phosphor trail, a message resolving on a darkened core. *Use: "in the machine" / decode / a data stream.*

## N · Isometric — dioramas & worlds
73. **IsoWorld** — an isometric diorama builds: a tiled ground draws in, then labelled iso-cube buildings rise in an outward ripple. *Use: your world / workspace-as-a-city / a system laid out.*
89. **VoxelBuild** — an isometric object assembles VOXEL by voxel: shaded cubes drop in (staggered by depth) and stack into a 3D form (default: a checkmark). *Use: built block-by-block / a thing coming together.*
40. **IsometricAssembly** — iso raw block → machine → finished deliverable (moved from G so all iso shots live in N). *Use: pipeline as objects.*

## O · Urban / signage
75. **NeonTickerWall** — a night-city wall of signage: stacked LED tickers scroll at different speeds, neon flickers, a central marquee holds the message. *Use: launch / announcement / electric energy.*

## P · Dimensional / experimental type — type as living/physical material (variable-axis · inflated · elastic)
67. **VariableTypeMorph** — one enormous word alive on its axes: a WEIGHT wave travels the letters while the word breathes on the WIDTH axis, over a duotone field. *Use: a bold expressive title / "type, alive".* (folded in from the retired J family)
77. **InflateType** — big puffy 3D BALLOON letters inflate in with an over-bounce (glossy shaded fills + specular + soft shadows), then breathe. *Use: playful bold hero / soft-dimensional title.* (2026 inflated-3D-type)
78. **ElasticType** — jelly letters DROP in and jiggle with a damped elastic squash-stretch, then a gummy wobble. *Use: springy playful title / "alive" copy.* (2026 elastic-type)

## Q · Anti-design / maximalist
79. **AntiDesignChaos** — a deliberately "wrong" maximalist collage: a huge clashing headline, scattered mismatched words, stickers, hand-drawn arrows + scribbles, on a loud ground. *Use: rebellious / youthful / disruptive statement.* (2026 anti-design)

## R · AI / neural
80. **NeuralField** — a neural network THINKS: layered nodes + edges light up as an activation front sweeps left→right until the output locks. *Use: AI reasons / a model at work / "it thinks".*

## S · Scientific / molecular
81. **DNAHelix** — a rotating double helix: two sine-phased strands of nodes with base-pair RUNGS, depth-shaded, assembling top-down. *Use: the blueprint / biotech / "encoded".*
94. **AtomOrbital** — a nucleus of protons/neutrons with electron SHELLS: tilted elliptical orbits, electrons RACING with motion trails, the atom turning. *Use: fundamentals / "the core of it" / physics.* (electrons streak — vs **DataOrrery** D's slow labelled-node orrery.)
99. **MoleculeBallStick** — a ball-and-stick molecule (a hex ring + outer atoms) rotates in 3D: depth-sorted bond sticks + element-coloured spheres. *Use: chemistry / composition / "what it's made of".*

## T · Circuit / hardware
82. **CircuitTrace** — a PCB comes alive: copper traces route (Manhattan bends) and draw on, signal pulses race to a central chip that lights up. *Use: hardware / a system wired together / infrastructure.*

## U · Audio / music
86. **SpectrumPulse** — a circular audio spectrum: a ring of frequency bars dance to a synth beat (kick every 0.5s scales + brightens), wordmark pulsing at the core. *Use: music / rhythm / audio-reactive energy.* (deterministic visual, not tied to the real VO)
37. **VoiceSignal** — an audio-reactive waveform through phases (moved from F; it's audio, not fluid — cf. SpectrumPulse). *Use: voice / listening / speech.*

## V · Cosmic / space
87. **StarfieldWarp** — stars accelerate outward into a hyperspace streak, then DECELERATE as a wordmark blooms from the core light. *Use: launch / "the next era" / into the future.*

## W · Organic / botanical
92. **FractalTree** — a recursive tree GROWS from the ground, branches splitting depth by depth, then blossoms bloom at the tips. *Use: grow / branch out / "from one root, everything" (techno-natural).*

## X · Weather / atmosphere
93. **RainGlass** — a message behind a rain-blurred glass pane: droplets slide + streak while the soft-focus scene SHARPENS and the title resolves. *Use: a moody, atmospheric, material interlude.*

## Y · Fire / energy
96. **EmberFlame** — a wordmark forged in fire: flame licks flicker at the base, embers rise + fade, heat-glow blooms, the title glowing white-hot → red. *Use: passion / launch / "built with fire".*

## Z · Textile / fabric
97. **ClothWave** — a silk flag ripples on a travelling wave, strips shaded by slope for a sheen, the wordmark riding the ripple. *Use: soft power / elegance / a tactile fabric hero.*

*(the single-letter families A–Z are full; add two-letter families AA+ when a new bold language needs one.)*

---
## Generalization — every shot is topic-driven via props (defaults = the WorkBuddy demo)

A design language is NOT tied to WorkBuddy: each shot reads its copy/data from **props with defaults**, so a
new topic just passes different strings (proven by re-skinning 8 shots to "MealMate" with zero code changes).
Standard prop vocabulary: `title` / `tagline` / `kicker` (headline set) · `items: string[]` (a list/labels) ·
`hub` (a centre node) · `label` (a single caption) · `accent` (primary colour) · plus shot-specific fields.
Pass via `--props='{...}'` (CLI, ASCII only — a multibyte `·` in CLI props breaks the arg) or as React props
in the film wrapper. Per-shot props:

| Shot | props |
|---|---|
| CinematicTitle | `kicker, title, tagline` |
| LiquidChrome / HoloFoil | `word, tagline` |
| AnalogTape / NeonGrid / BokehPull | `title, tagline` |
| MaterialHero | `title` · MapRoutes/KnowledgeGraph/InfiniteCanvas `items, hub` (Map also `accent`) |
| SwissEditorial | `items, ticker` · SpotlightStage `items, wordmark` · KineticManifesto `phrases` · AuroraFlow `lines` |
| ExplodedSchematic / HandDrawn / CursorStory / TemporalAccelerate / IsometricAssembly | `items` |
| ChatThread `messages` · AnswerStream `query, answer, sources` · CommandSummon `command, items` | |
| BlockAssembly | `title, callout, items` · BlueprintGrid `unit, tag, spec1, spec2, metricLabel` |
| ChartLive | `endVal, unit, label` · BeforeAfterSlider `heading, metric, sub, beforeLabel, afterLabel` |
| ScreenBubble | `appTitle, nav` · LiquidGlass `items, title` · TimelineTravel `nodes` · DataOrrery `items, hub` |
| KSpaceToImage | `accent, accent2, label` — k-space→image inverse-FFT sweep (bespoke) · FocalIsolation | `focalLabel, items` · VelocitySnap `label, metric, unit` · VoiceSignal `phases` |
<!-- MRI-physics bespoke family: each ENCODES a specific physics step (meaningful, not decorative), image-driven shots take a real `src`+`credit` and generalise via props. -->
| SpinsAlign `accent,accent2,label` — random spins→net M₀ · LarmorPrecession `accent,accent2,label` — μ precesses B₀ at f₀=γB₀ · MagnetizationTip `accent,label` — resonant RF tips M into transverse |
| InducedFID `accent,label` — decaying FID oscillation in the coil · GradientTilt `accent,accent2,label,cols` — field tilts, position→frequency · FrequencyEncode `accent,label` — columns pitch-ramp→FFT peaks |
| PhaseEncodeStep `accent,label` — gradient blip fills k-space lines · KSpaceReal `src,label` — real FFT log-magnitude, kx/ky axes · SpeedLimit `accent,label` — gradient bar capped at slew-rate+PNS |
| Aliasing `src,label,credit` — undersample→anatomy wraps (ghost) · GFactorNoise `accent,label` — R rises to cap, g-factor noise · UndersampledKspace `accent,label` — k-space lines removed |
| CompressedSensingEq `accent,label` — typeset min‖Ψx‖₁ s.t.‖Fx−y‖₂≤ε · DiffusionDenoise `src,label,credit` — noise→real MRI, pinned to data · ScanReconstruct `src,label,credit,cols` — image rebuilds center-out |
| MRIPipeline `src,label` — signal→encode→k-space→image · RealVersus `srcLeft,srcRight,labelLeft,labelRight,title,credit` — two real scans compared |
| KSpaceAnatomy `srcK,srcLow,srcHigh,label,credit` — center=contrast / edges=detail, proven by center-only & edge-only partial reconstructions |
<!-- General-purpose registers added for content-fit (adapt-not-text-swap) — each keeps a vibe but is designed around real content. -->
| TensionScale `title,leftLabel,leftSub,rightLabel,rightSub,note,accent,accent2` — a balance held in PERMANENT equilibrium (two named forces, neither wins); use for a sustained unresolved tension, not a winner |
| PlatformSurfaces `title,subtitle,tiles[{label,note,glyph}],accent,accent2` — a bento of product surfaces where each tile carries a MEANINGFUL glyph (chat/api/video/code/cursor), not a reused mini-chart; use for "one platform, many surfaces" |
| OpenQuestions `kicker,questions[],footer,accent` — parallel open questions stacked under a descending scan-light + an unresolved caret (no arrows, no sequence); use for genuine open/unanswered questions |
| SplitFlap `rows` · PhysicsStack `items, label` · CollaborativeCursors `names` · WireGlobe `tagline` |
| HalftonePop | `burstTop, burstBottom, brand` · BrutalistType `titleTop, titleBottom, meta, statement1, statement2` |
| CartoonPop / PixelBuild / ClayStack / LiquidFill / LightTrails / ParticleForm / AsciiField(`message`) | `label` |
| PaperCutout `label, tagline` · RadialBurst `hub, tagline` · CodeCompose `filename` | |
| OdometerRoll `value, label, unit` · CubeRotate `faces[], title` · GearTrain `items[], label, title` | |
| QuadSplit `panels[{label}], heading, hero` · CardFlip3D `items[{front,back}], title` | |
| GaugeCluster `value, unit, label, gauges[{label,fill}], title` · FractureIn `title, tagline, accent` | |
| BentoReveal `title, hero, items[]` · ConveyorBelt `items[], title, doneLabel` | |
| PositioningMatrix `title, xAxis[lo,hi], yAxis[lo,hi], items[{label,x,y,hero}]` | |
| CardStack3D `items[], title` · CrashZoom `items[], label, target, title` · RisoPrint `title, tagline` | |
| VersusSplit `left{label,points[]}, right{label,points[]}, winner, title` · HudReticle `target, readouts[], title` | |
| VariableTypeMorph `word, kicker, tagline, accent, accent2` · FlowField `title, tagline, accent, accent2, lines` | |
| MagazineSpread `title, headline, deck, issue, accent` · RansomZine `word, tagline` · DataMonolith `items[], title, hero` | |
| LowPolyForm `title, tagline, accent, accent2` · GlitchDatamosh `word, tagline, accent` · MorphForms `title, tagline` | |
| IsoWorld `items[], title` · NeonTickerWall `headline, tickers[], accent` | |
| MetaballMerge `title, tagline, accent, accent2` · InflateType `word, tagline` · ElasticType `word, tagline` | |
| AntiDesignChaos `title, items[], tagline` · NeuralField `title, input, output` | |
| DNAHelix `title, tagline` · CircuitTrace `title, chip, nodes[]` · KaleidoMandala `title, tagline, accent, accent2` | |
| InkBloom `title, tagline, ink` · ComicPanels `panels[], splash, title` | |
| SpectrumPulse `title, tagline, accent, accent2` · StarfieldWarp `title, tagline, accent` · RidgeField `title, tagline, accent` | |
| VoxelBuild `title, tagline, accent` · ChartRace `data[{label,value,delay}], title, unit` | |
| CodeRain `title, tagline` · FractalTree `title, tagline, branch, blossom` · RainGlass `title, tagline, accent` | |
| AtomOrbital `title, tagline` · LiquidMetal `title, tagline` | |
| EmberFlame `title, tagline` · ClothWave `title, tagline, accent, accent2` · GameOfLife `title, tagline, accent` | |
| MoleculeBallStick `title, tagline` · TerrainFly `title, tagline` | |
| LiquidMorph | *(abstract — no topic text; generalizes as-is)* |

**Faithfulness:** shots carrying a NUMBER (ChartLive, BeforeAfterSlider, VelocitySnap, OdometerRoll, GaugeCluster, ChartRace, BlueprintGrid's counter)
ship an illustrative DEMO default — a real film MUST override it with a sourced figure (the WorkBuddy film passes
`endVal:68, unit:"×"` for the Hy3 surge). Never present a demo number as a real stat (see no-fake-info rule).

---
**Palette spread:** light UI · dark UI · warm-paper · cream-editorial · off-white brutalist · deep-cinematic ·
synthwave · pastel-clay · phosphor-green · navy-blueprint · gradient-aurora · retro-CRT · iridescent-foil —
no single look dominates.
**Motion vocab:** camera-over-world, Z-rush, blur-velocity, draw-on, clip-reveal, gooey-metaball, point-cloud
assembly, parallax depth, squash-&-stretch, radial bloom, orbital motion, spotlight falloff, split-flap decode,
chromatic split/glitch, focus-pull DoF, long-exposure trail, gravity bounce, backdrop-refraction, pixel-assemble.
