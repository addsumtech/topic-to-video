# KnowledgeGraph

**Identity:** a hub node pops at the centre, and spokes reach out one by one to a ring of coloured nodes that pop in with their labels. If the film gives links, faint chords then draw between the linked nodes. The whole constellation turns slowly and each node bobs.

**Use when:** many sources wired to one centre (a connected workspace, a "second brain"), with `links` saying which of them also connect to each other. **Not when:** geography matters (MapRoutes), the structure is a hierarchy (TermTree, GrantedTree), or there are more than eight nodes.

**Motion core:** the hub pops over 0.02–0.18, and its label comes in over 0.16–0.3. Spoke `i` draws from 0.1 + 0.06·i over 0.14; its node pops as the spoke lands, and the node's label follows. Chords draw from 0.62, their stagger tightening with the count so the last one finishes before the end. Throughout, the graph turns 0.9 rad and each node bobs on its own period.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | 1–8 node labels, evenly spaced on a ring around the hub | colours cycle through the palette. Labels are 24px pills on one line and are not fitted; eight nodes were sized for labels of a word or two |
| `hub` | the label under the central disc, 34px, one line | names the centre everything connects to |
| `links` | pairs `[a, b]` of node indices or exact labels, drawn as chords | none gives spokes only. Each pair adds one chord; repeats are merged. A chord that would pass under the hub bows around it |

**Known traps:**
- Chords used to come from a fixed index table, so every film wired its first node to its second (a film about organs got the heart linked to the skin). Only the film's `links` are drawn now.
- A chord between opposite nodes ran under the hub and along two spokes, so it drew nothing visible. Such chords now bow out.
- Leaving out `hub` prints the demo `WorkBuddy`, even when the film passes its own items. Leaving out `items` gives the demo nodes and the demo chords.
- The hub's label and the rim on every node were literals picked for a near-black ground, so on a warm-white film the hub had no name and every node lost its edge — 41.6% of this register's marks under 3:1, connected hole 0.29% of the frame (small because those two are the only marks here that touch the ground). Both read from `fg` now.
- Nothing else does, and that was checked against the light probe render rather than assumed: the node LABELS ride dark pills that carry their own ground, the chords are a mid slate that reads on either (`line` would make them invisible on paper — it is a grid token, not an ink one), and the halos are glow. A glow that stops showing on paper costs a reader nothing, because the darkness it separates the node from is not there.

**Refuses:** 0 or more than 8 items; an empty item; `links` that is not an array; a link that is not a pair; a link naming a node that doesn't exist (a bad index, or a label that doesn't match exactly); a link from a node to itself.

**Reference:** `remotion/src/shots/KnowledgeGraph.tsx`
