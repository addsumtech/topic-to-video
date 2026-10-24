# GrowingFigure

**Identity:** one figure that BECOMES the next. The first state's outline draws on and its body fills; each later state is reached by a true shape morph — both outlines resampled to the same points by arc length and aligned (same winding, least travel), so a circle never spins or turns inside out on its way into a square — and a state with more pieces shares the pieces before it, so one cell drawn twice over itself parts into two. The state just left lingers as a faint dashed ghost over the new shape. A rail names every stage; its marker rides to the current one as the shape changes.

**Use when:** continuity of ONE thing through its stages — a cell that stretches and divides, a point that becomes a segment, a triangle, a square; a shape the film draws itself (`d`). Hide the caption and the sequence still says "this became that"; the rail says what each stage is called. **Not when:** the items are different things (a grid / list register), two separate objects compared (an H register), or a quantity growing (a chart).

**Motion core:** draw-on t 0.05–0.24 (stroke), body rising t 0.13–0.28. Each later state gets an equal slot to t 0.90: held for 40%, then morphed (cubic in-out) over the rest. The ghost of the state just left fades over the following hold. The rail's spine draws on with the first state; its rows enter staggered and the active row takes the foreground ink.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | a small label over the figure | context, never a second claim |
| `states` | 2–4 `{label, shape?, count?, d?}` | `shape`: `dot`, `circle`, `ellipse`, `square`, `triangle`, `diamond`, `pentagon`, `hexagon`, `star`, `line`, `ring`; `count` 1–6 repeats it side by side (a division is `circle` then `circle ×2`); `d` is the film's own outline in a 0–1000 square, any SVG commands |
| `filled` | body on (default) or outline only | outline-only reads as a diagram, filled as a thing |
| `title`, `kicker` | the heading | the demo's title belongs to the demo's states |

**Known traps:**
- `@remotion/paths`' interpolatePath pairs SEGMENTS: measured half-way through circle→triangle in a 400 px box its signed area collapses to 4,932 (endpoints 125,686 and 57,288) — the shape folds through itself — and it refuses one piece into two outright. The morph here keeps 90,848.
- A split draws the one cell twice over itself: stroked piece by piece, the copies' outlines crossed inside the body and read as two overlapping rings, not a cell parting. Each piece's stroke is masked by the OTHER pieces' interiors, so only the union's edge is drawn; the body is one path, so its fill is laid once.
- A line has no body: a morph from a line to a closed shape is planned as an open path (the closed side opened at its start), so a segment unfolds into the shape rather than snapping shut.

**Refuses:** fewer than 2 or more than 4 states; a state with no `label`; a state with neither `shape` nor `d`; an unknown `shape`; `count` outside 1–6.

**Reference:** `remotion/src/shots/GrowingFigure.tsx` · runtime `pathMorph` / `pathCore`

**Measured:** 3.7% ink (clip median) · 39.7% footprint · 0.0008 motion · reach 0.550 (product DNA, the demo at its own 9 s). QUIET: one figure and a rail; intercut with a dense register.

**Review:** NOT critic-reviewed — built and looked at by its author: 16:9 Latin (the division), 9:16 Chinese (dot → line → triangle → square), mid-morph frames at each.

**Provenance:** scientific. **Family:** S.
