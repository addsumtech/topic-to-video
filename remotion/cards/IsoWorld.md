# IsoWorld

**Identity:** an isometric city builds itself on a 7×7 tiled ground. Tiles appear in a wave from the back corner to the front, blocks rise with overshoot, and a floating chip names each labelled building; the unlabelled filler blocks stay lower.

**Use when:** your world, the workspace as a city, a system laid out as a set of places (1–9). **Not when:** the items carry sizes or numbers (every labelled building is the same height on purpose), the items connect to each other (KnowledgeGraph), or there are more than nine.

**Motion core:** the title fades in over 0.03–0.16. Ground tiles appear on a diagonal wave from the back corner to the front (0.06 to about 0.54). Blocks rise with overshoot in the same order (0.2 to about 0.77). Chips fade in behind them (0.5 to about 0.87).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one labelled building per item, on a fixed spread of lattice cells for that count | 1 item stands alone in the middle; 9 fill a 3×3 lattice. All chips share one size (up to 26px), shrunk so the longest label fits 250px, so one long label makes every chip smaller. Chips never wrap |
| `title` | spaced mono caps at the top | a short heading. Not fitted: long copy wraps |

**Known traps:**
- Building heights used to come from a hash, so labelled buildings ranged from 0.98 to 1.37 and suggested sizes the list never claimed. Every labelled building is now the same height, with the filler below it.
- Labels used to go to hashed cells: a 14th item was dropped, the first five sat in the back rows, and chips collided. Each count now has its own fixed slots.
- Leaving the props unset prints the demo `Docs / Chat / Data / Code / Team` and `Your world, built`.

**Refuses:** 0 or more than 9 items; an empty item.

**Reference:** `remotion/src/shots/IsoWorld.tsx`
