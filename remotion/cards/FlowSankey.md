# FlowSankey

**Identity:** the film's stages as columns of slim nodes and its flows as ribbons whose widths ARE their values on one scale, drawn on stage by stage left to right, coloured from the node they leave to the node they reach, with a soft band of light travelling each ribbon once it is drawn.

**Use when:** the claim is where a whole goes and that it is conserved — a budget by programme, an energy balance, a funnel, a supply chain — and the split and the rejoin are the argument. **Not when:** it is parts of one whole with no stages (`MadeOf`), a ranking (`RankRace`, `ChartRace`), or connections with no quantity (a network register).

**Motion core:** the title rises at 0.02; each stage's nodes grow from their centres over 0.10 of the clip and its ribbons draw on from left to right, stage after stage, between 0.10 and ~0.68; each node's label fades in as its stage lands; once drawn, light crosses every ribbon about every five seconds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | one line in the title band | empty draws nothing |
| `nodes` | 3–14 nodes: `id`, `label`, optional `display` (the figure the node prints, as written) | the first stage is labelled on its left, the last on its right, middle stages beside their node on a chip; a node prints a figure only with `display` |
| `links` | 2–24 flows `{from, to, value}` | widths share one scale set by the tightest stage; a stage's column is its longest path from a source and sinks sit in the last column |
| `focus` | a node id to emphasise | its flows stay lit and the rest recede to 12%; default none |
| `note` | a mono line under the diagram | a source or reading note |

**Known traps:**
- Conservation is enforced: every node with both inflow and outflow must balance to within 1e-9 of its flow. A loss, a leak or a residual is a node the film names ("Losses") with its own link.
- A node's height is the SUM of its links. That sum is never printed — pass `display` with the film's own figure, or the node shows its label only.
- Hues tell nodes apart and mean nothing else; under a DNA they are the DNA's palette.
- A middle label too wide for the room between two stages (a long Chinese name at 9:16) is set smaller, down to 70%, before it is refused.
- Many small flows in one stage shrink the vertical scale for the whole diagram (one scale everywhere is the point); merge small flows.

**Refuses:** `nodes` without `links` or the reverse (either alone would be drawn against the demo's other half); fewer than 3 or more than 14 nodes; fewer than 2 or more than 24 links; duplicate ids; a link to a node that does not exist, into itself, or with a value that is not a number > 0; a loop; a node with no link; a node whose inflow and outflow differ; labels in a stage that cannot all be set without overlapping; a middle label wider than the room before the next stage even at 70% of the label size (it shrinks first); outer labels that leave no room for the flow.

**Reference:** `remotion/src/shots/FlowSankey.tsx`
