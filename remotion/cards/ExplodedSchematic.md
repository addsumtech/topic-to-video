# ExplodedSchematic

**Identity:** a blueprint: wireframe part boxes start clustered, then explode apart along an axis into numbered parts joined by forward arrows, with a spec readout in the top-right corner.

**Use when:** how it works — a system as its parts in order, input to deliverable, optionally with one key stage. **Not when:** the parts are steps with states or progress (InOrder), or there are more than six.

**Motion core:** the parts appear clustered (from 0.06, staggered 0.03, by 0.30); the explode runs 0.14–0.62; each connector draws forward once there is room for it; the numbered leader labels fade in from 0.40 (staggered 0.05) to 0.70; then it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one part each, in order | 1–6. Each box is sized to the slot its count leaves and every label shares one size (the largest that fits all), so more parts means smaller type. The axis is the frame's long one — across at 16:9, down in portrait — unless labels along it would fall under 24px, when the other axis is taken |
| `hot` | the index of the key part | that part glows in the accent; omitted = every part alike |
| `label` | the first word of the corner readout | the readout reads `label · <count> unit` |
| `unit` | the word after the count | names what the count counts |
| `caption` | the readout's second line | fixed 28px mono, not fitted; right-aligned, so a long line grows leftward |

**Known traps:**
- `hot` used to be hardwired to the third part, so a checkout film's payment step glowed as the heart of the system for no reason but its position. It is the film's index now.
- Fixed 260px boxes on a fixed axis used to overlap at 9:16, and the connectors pointed backwards; boxes and type are now sized per count and axis so every arrow runs forward.
- The readout defaults ('SYSTEM', 'STAGES', 'ONE PROMPT → DELIVERED') print unless replaced — `caption` was once declared and never read.
- The ground and grid are fixed blueprint navy; only the accent and line colours follow the DNA.

**Refuses:** fewer than 1 or more than 6 items; an empty item; a `hot` that is not an index into the items.

**Reference:** `remotion/src/shots/ExplodedSchematic.tsx`
