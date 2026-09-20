# GrantedTree

**Identity:** an indented tree of rows fades in from top to bottom; then a drawn bracket closes around each granted branch, a chip names the grant beside it, and every row outside the brackets greys back.

**Use when:** a permission or scope boundary has to be seen: what it can touch and what it can't (a scoped token, a folder an agent may write to, an org unit a policy covers, a repo path a CI job may change). **Not when:** nothing is granted (the tree is drawn plain, with no boundary), or the claim is only "here is the structure" (TermTree).

**Motion core:** rows fade in one after another, 0.035 of the clip apart, starting at 0.06. The bracket draws itself downward over 0.40–0.62. The grant chip and the note come in over 0.60–0.76. The withheld rows dim over 0.66–0.86, only after the edge exists.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | small spaced mono caps in the accent, top-left | a topic tag. Room is reserved only when it is set |
| `root` | a dim first row above the nodes | names the tree's root and takes one row's height |
| `nodes` | the rows: `{label, depth, granted}` | `depth` is the indent, i.e. the tree's structure. Granted rows are bold with an accent dot. Each contiguous granted run gets its own bracket. From 1 to 8 rows; more rows mean shorter rows and smaller type, so the tree still fits between kicker and note |
| `grantLabel` | the accent chip beside the first granted run | shown only when something is granted. Not fitted: it starts about 60% across the frame, and long copy runs toward the right edge |
| `denyLabel` | a quiet label beside a withheld row | sits beside the first withheld row after the first granted run. Omitted when no row is withheld |
| `note` | one line under the tree | wraps to the tree's width. Its height comes out of the rows' share |

**Known traps:**
- One bracket from the first granted row to the last used to enclose a denied row between them. Now there is one bracket per run, so a scattered grant draws several brackets, and the chip labels only the first.
- Nodes past the eighth used to be cut off without a word. Now that throws: collapse the rest into one sibling ("everything else").
- Forget `granted` on every node and there is no error: the tree is drawn with equal treatment (no bracket, no dimming, no labels), and the boundary claim goes missing.
- Leaving out `nodes` prints the demo tree (`Documents / Work / reports / data / Personal / Photos`).

**Refuses:** 0 or more than 8 nodes; a node with no `label`; a `depth` that is not an integer ≥ 0.

**Reference:** `remotion/src/shots/GrantedTree.tsx`
