# BlockAssembly

**Identity:** a Notion-style document builds itself block by block from the top: a title, three placeholder text rules, an info callout, a to-do list (ticked and struck through only where the film says so), and a 3×3 table with a header row over em-dash cells.

**Use when:** the beat is a plan or brief being written up — a named document with a goal and 1–8 to-dos, some of which may be done. **Not when:** the table needs real cell data (its body is always em-dashes), or every step should end ticked (that's `CommandSummon`'s premise).

**Motion core:** five blocks, each sliding up 46px and settling with an overshoot; block i runs 0.14 + i·0.13 → +0.24, so the table, last, lands by about 0.90. Then it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the page title | 92px with balanced wrapping. A long title adds lines, and the whole page scales down as a page to keep everything above the caption band |
| `callout` | the text in the accent-tinted "i" callout | 36px with balanced wrapping; a sentence reads as the goal, a paragraph makes the page scale down |
| `items` | the to-dos: strings, or `{label, done}` | a string or `done`-less item is an open box; `done: true` ticks it and strikes it through in dim ink. Two or three read as a checklist; eight make a long page that scales down |
| `tableHeaders` | the three header cells of the table | the default `['', '', '']` gives an empty header row; only the first three are drawn, and the body rows are always `—` |

**Known traps:**
- The first two to-dos used to be ticked and struck through whatever list the film passed, so steps not yet started shipped as finished and findings shipped as withdrawn. Ticks now come only from `done: true`.
- Omitting props prints the demo `Q3 Board Deck`, the Friday goal callout, and three to-dos (two of them done).
- The page's height used to be a Latin-measured constant, and the Chinese copy pushed the table's em-dash row into the caption band. It's now summed block by block with the constant as a floor. The page scales and never clips.
- The three grey rules are placeholders, never copy. No prop reaches them.

**Refuses:** `items` that is not an array of 1–8 entries; an item with an empty label; `done` that is not `true` / `false`.

**Reference:** `remotion/src/shots/BlockAssembly.tsx`
