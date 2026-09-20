# SectionRoute

**Identity:** a measured cross-section — ruled levels with leader labels draw in top to bottom — then a load travels a drawn route through it at constant speed, every climb or drop marked in the second accent with its own ↑↓ tick, and a verdict lands underneath.

**Use when:** the claim is that a process is costly because its ROUTE crosses levels it had no business crossing — or, on its own beat, that a direct route removes those climbs ("why the shortcut was worth digging"). **Not when:** the stages are a plain sequence with no levels (a flow or list register), or the claim is about one thing growing (use `ProfileGrowth`).

**Motion core:** the kicker and the level rules draw 0.04–0.26, each level after the one above; the load travels the whole route 0.30–0.80 at constant speed, the line drawing in behind it; each lift's tick appears once it has been travelled, and each waypoint label fades in as the load passes (the end label arrives with the settle); the verdict and note land 0.80–0.94.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | the small spaced caps line above the section | a heading; omitted, the demo `THE ROUTE` prints |
| `levels` | the section's levels, TOP to BOTTOM, labelled at the left | at least two; more levels make tighter bands between the rules. Must come with `route` |
| `route` | the stops in travel order: `level` (index into `levels`), `x` in 0..1 across the section, optional `label` | at least two stops. Every change of level is a lift; a route that stays on one level is a flat run with no ticks. Labels sit beside their stop on the side away from the route |
| `verdict` | the line under the section — what the route costs or what the shortcut removed | empty draws nothing; one line is what it is placed for |
| `note` | a small dim line under the verdict | empty draws nothing; placed a fixed step below the verdict |
| `markLifts` | whether climbs and drops are called out | default true: lift segments in the second accent with ↑↓ ticks; false draws the whole route in one accent with no ticks — right for a direct route with nothing to call out |

**Known traps:**
- `levels` and `route` used to default independently, so a film that named its levels got the demo's climb-and-drop drawn through them — the register's whole claim, made by nobody. Pass both or neither.
- The last lift used to miss its tick (its travelled fraction landed at 0.9999… in floating point) and the end label never appeared; both are fixed.
- Labels under a stop on the bottom level landed in the verdict's line, and labels centred on a stop sat on the route; they now go above the bottom level and away from the route.
- The note sits a fixed step under the verdict, sized for a one-line verdict: a verdict that wraps runs into the note.
- It draws ONE route. Comparing an indirect route with a direct one takes two beats on the same `levels`.

**Refuses:** `levels` without `route` or `route` without `levels`; fewer than 2 levels; fewer than 2 stops; a stop whose `level` is not an integer index into `levels`, or whose `x` is outside 0..1.

**Reference:** `remotion/src/shots/SectionRoute.tsx`
