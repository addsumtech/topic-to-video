# Remotion2 — Bespoke Shot Library (60 design languages)

Each shot is a **hand-written, deterministic component** (`{default Component, DURATION}`) authored in
1920×1080, driven by `useT()` (0→1) + the shared `runtime/motion.ts` kit. No generic template funnel —
every register is its own file. Renderable standalone: `npx remotion still src/index.ts <Id> out.png --frame=N`.

**Selection contract (for the film's design step):** pick a register per beat by matching the beat's *intent*
to the "use when" below, and vary the FAMILY across the film (never two adjacent shots from the same family).
Every shot accepts overridable copy via constants at the top of its file (wordmark/tagline/labels).

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
26. **AsciiField** — phosphor char field decodes a word. *Use: code / hacker beat.*

## D · Data / technical
27. **ChartLive** — glowing line+area draws, a counter ticks. *Use: a metric / result.*
28. **BlueprintGrid** — Vercel blueprint: grid, dimension lines, crosshair, mono. *Use: spec / precision / local-only.*
29. **KnowledgeGraph** — a node/edge constellation grows. *Use: connected workspace / second brain.*
30. **WireGlobe** — rotating wireframe globe + integration nodes + arcs. *Use: global / connected to everything.*
31. **DataOrrery** — labeled nodes ORBIT a core on tilted rings. *Use: your work in motion / ecosystem.*
52. **OdometerRoll** — a big metric where every digit is a mechanical reel that spins through 0-9 and snaps, staggered. *Use: a single headline number, felt.*
57. **GaugeCluster** — a panel of circular gauges sweep their arcs; the hero gauge's needle rises and its value locks. *Use: live status / health / a KPI panel.*

## E · 3D / material
32. **MaterialHero** — real 3D torusKnot (R3F/WebGL), studio-lit. *Use: a hero object beat.*
53. **CardFlip3D** — a row of cards flip 180° on Y (CSS 3D), a sheen at the seam, the payoff on the back. *Use: question → answer / before → after pairs.*
58. **FractureIn** — 25 tiles fly in from scattered 3D space and lock centre-out into a hero poster, then the title resolves. *Use: many parts → one picture / a bold reveal.*

## F · Fluid / generative / light
33. **AuroraFlow** — Stripe/Vercel flowing gradient blobs + type. *Use: calm premium ambient.*
34. **LiquidMorph** — iridescent blob morphs through ask/draft/done glyphs. *Use: transformation.*
35. **LiquidFill** — gooey vessel fills, % counts, checkmark. *Use: progress / completion.*
36. **ParticleForm** — a point-cloud assembles into a check. *Use: many parts → one result.*
37. **VoiceSignal** — audio-reactive waveform. *Use: voice / listening.*
38. **RadialBurst** — kaleidoscopic radial bloom to a hub. *Use: everything-at-once / celebration.*
39. **LightTrails** — long-exposure neon ribbons trace a checkmark. *Use: "done in one motion" / kinetic flourish.*

## G · Illustrated / craft styles (the "style" axis)
40. **IsometricAssembly** — iso raw block → machine → finished deliverable. *Use: pipeline as objects.*
41. **HandDrawn** — riso ink sketch draws on (You→WorkBuddy→Done). *Use: human / hand-made.*
42. **CartoonPop** — cel-shaded cartoon mascot zaps tasks → DONE! *Use: playful / friendly.*
43. **HalftonePop** — comic Ben-Day pop-art burst "SHIP IT!". *Use: loud fun highlight.*
44. **ClayStack** — soft pastel clay blocks stack + clay check. *Use: tactile approachable build.*
45. **PaperCutout** — layered paper-cutout parallax diorama. *Use: warm storybook.*
46. **SpotlightStage** — theatrical spotlight reveals PLAN→BUILD→SHIP. *Use: dramatic three-step.*
47. **PixelBuild** — 8-bit pixel checkmark assembles + CRT HUD. *Use: retro-game / "level complete".*

## H · Comparison
48. **BeforeAfterSlider** — slider wipes rough draft → board-ready. *Use: quality / transformation.*
54. **QuadSplit** — the frame splits into a 2×2 of micro-panels (each a distinct accent + motif), then one hero panel takes the whole frame. *Use: four angles → the one that matters.*
59. **PositioningMatrix** — a 2×2 axes map; item dots drift to their spots and the hero lands in its quadrant (ring + label). *Use: positioning / where things sit / who leads (qualitative).*

## I · Mechanical / tactile-physical
49. **SplitFlap** — Solari flap board riffles + settles to the message. *Use: status flips to done / announce.*
50. **PhysicsStack** — weighty bars DROP + bounce-settle into a chart. *Use: tactile results / a week of output.*
55. **GearTrain** — interlocking gears mesh and turn in a chain (hubs carry the steps); the last gear locks the payoff. *Use: mechanism / one turn drives the next.*
60. **ConveyorBelt** — items ride a scrolling belt through a stamp press and exit finished (✓). *Use: assembly line / "it just processes everything".*

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
| FocalIsolation | `focalLabel, items` · VelocitySnap `label, metric, unit` · VoiceSignal `phases` |
| SplitFlap `rows` · PhysicsStack `items, label` · CollaborativeCursors `names` · WireGlobe `tagline` |
| HalftonePop | `burstTop, burstBottom, brand` · BrutalistType `titleTop, titleBottom, meta, statement1, statement2` |
| CartoonPop / PixelBuild / ClayStack / LiquidFill / LightTrails / ParticleForm / AsciiField(`message`) | `label` |
| PaperCutout `label, tagline` · RadialBurst `hub, tagline` · CodeCompose `filename` | |
| OdometerRoll `value, label, unit` · CubeRotate `faces[], title` · GearTrain `items[], label, title` | |
| QuadSplit `panels[{label}], heading, hero` · CardFlip3D `items[{front,back}], title` | |
| GaugeCluster `value, unit, label, gauges[{label,fill}], title` · FractureIn `title, tagline, accent` | |
| BentoReveal `title, hero, items[]` · ConveyorBelt `items[], title, doneLabel` | |
| PositioningMatrix `title, xAxis[lo,hi], yAxis[lo,hi], items[{label,x,y,hero}]` | |
| LiquidMorph | *(abstract — no topic text; generalizes as-is)* |

**Faithfulness:** shots carrying a NUMBER (ChartLive, BeforeAfterSlider, VelocitySnap, OdometerRoll, GaugeCluster, BlueprintGrid's counter)
ship an illustrative DEMO default — a real film MUST override it with a sourced figure (the WorkBuddy film passes
`endVal:68, unit:"×"` for the Hy3 surge). Never present a demo number as a real stat (see no-fake-info rule).

---
**Palette spread:** light UI · dark UI · warm-paper · cream-editorial · off-white brutalist · deep-cinematic ·
synthwave · pastel-clay · phosphor-green · navy-blueprint · gradient-aurora · retro-CRT · iridescent-foil —
no single look dominates.
**Motion vocab:** camera-over-world, Z-rush, blur-velocity, draw-on, clip-reveal, gooey-metaball, point-cloud
assembly, parallax depth, squash-&-stretch, radial bloom, orbital motion, spotlight falloff, split-flap decode,
chromatic split/glitch, focus-pull DoF, long-exposure trail, gravity bounce, backdrop-refraction, pixel-assemble.
