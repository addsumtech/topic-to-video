# LivingMap

**Identity:** ONE structure for the whole film — a pipeline, a system, a family of ideas — laid out once over every node the film will show, built up beat by beat while the camera moves through it. Each beat's last frame is the next map beat's first, so the cut between them is invisible; a beat with no focus pulls back to everything built so far.

**Use when:** the film's argument IS one structure and its beats walk through it — signal → k-space → image, a supply chain, a decision tree, the parts of a system and how they feed each other. Name the map once in `meta.maps[id] = {nodes: [{id, label, note?}], edges: [[from, to]]}` and give each beat `shot_props: {map, add, focus}`; between map beats other registers may come and go, and the map picks up where it left off. **Not when:** the beats are separate ideas (a map with one node per beat and no edges is a slideshow), or the structure has more than ~16 nodes (split it).

**Motion core:** each added node pops in on the word that names it (runtime/cue `nodes.<i>`, matched by its label; a node the voice never names comes in its turn, the defaults spread LATE — to t ~0.86 — because a cue only moves an entrance earlier) at the place it will always keep; the camera travels from the first arrival to the last (scale blended in log space, the world point at the centre on a straight line), so the frame moves while the map grows; edges draw on once both ends are there; focus moves to the beat's nodes (out-of-focus nodes dim when the focus is a part); nodes the camera leaves behind fade out before the frame's edge. (A fixed 0.30–0.48 window for every node left a 3 s still tail on the test film.) Layout: layered left to right by longest path, two barycentre sweeps, a source placed just before what it feeds (runtime/graphLayout).

The board writes `{map, add, focus}`; `render_remotion.expand_living_maps` turns them into the register's props:

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `nodes` | the WHOLE map's nodes `{id, label, note?}` (from `meta.maps`) | 5–10 nodes read as a system; 16 is the most a frame can hold |
| `edges` | the map's `[from, to]` pairs | a chain reads as a pipeline; side inputs (a source feeding the middle) read as "and this too" |
| `before` | what is on screen when the beat starts (the last map beat's `after`) | — set by the expansion, never by hand |
| `after` | what is on screen when it ends: `before` plus this beat's `add` | 1–3 added per beat keeps each beat one idea |
| `focusFrom` | where the camera starts (the last map beat's focus, or this beat's own after another register) | — set by the expansion |
| `focusTo` | what the camera frames: the beat's `focus`, else everything shown | a close focus reads the notes; the whole map shows labels only |
| `title` | an optional label over the map | short; most map beats need none |

**Known traps:**
- One label size for the map: fitting per node made short words larger than their neighbours.
- A node's `note` shows only while the camera is close enough for it to fit at the type floor — in the whole-map view it overflowed.
- A source drawn in column 0 ran its edge across the whole map; sources sit one column before what they feed.
- Two map beats in a row are never given a planned seam (seam_plan treats them as joined) and render as a hard cut — a dissolve would cross-fade a picture with itself while the camera starts.

**Refuses:** a map the film does not define; an `add`/`focus` id not in the map; a first beat that adds nothing; a framing whose scale drops under 0.7 (labels would fall under the floor — focus a part, or split the map); fewer than 2 or more than 16 nodes.

**Reference:** `remotion/src/shots/LivingMap.tsx`, `remotion/src/runtime/graphLayout.ts`, `scripts/render_remotion.py` `expand_living_maps`
