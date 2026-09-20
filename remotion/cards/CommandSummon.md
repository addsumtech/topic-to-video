# CommandSummon

**Identity:** a dark command palette flies up and a plain-language command types itself into its search field, with the first row showing as the match (`↵ run`). Return flashes the frame and the palette lifts and shrinks slightly as the rows spawn as a checklist, ticking off one by one.

**Use when:** the beat is "one instruction → all of it planned and run", with every listed step done. **Not when:** some steps aren't finished (every row ends ticked; `BlockAssembly` has per-item `done`), or there are more steps than fit (group them).

**Motion core:** the palette flies in 0–0.14 with an overshoot; the command types 0.14–0.44; Return fires at 0.46 with a white flash gone by about 0.52; the palette lifts 40px and scales to 0.94 over 0.46–0.62. Row i reveals from 0.50 + i·stepR (each over 0.18) and ticks at 0.66 + i·stepT; the steps shrink with the count so the last row is in and ticked inside the clip. Before Return only the first row shows.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `command` | the instruction typed into the search field | single line (`white-space: pre`), fitted to the palette width up to 46px; a long command types into smaller type |
| `items` | the rows that spawn and tick | one shared size fitted to the palette, up to 38px. Two or three rows tick slowly and deliberately; the maximum (six on a 1080-tall frame) ticks in quick succession. The first row doubles as the pre-Return match |

**Known traps:**
- Every row ends ticked; that's the register's premise, not per-item data. Don't use it when a step isn't done.
- Omitting props prints the demo `Build the Q3 board deck from ~/finance` and five deck-building steps.
- The schedule used to be written for five rows. From the seventh on, the tick fell past the clip's end, and a film ended with two steps apparently not done, chosen only by their position. The spacing now scales with the count.
- The palette used to be a fixed 1180px, wider than any 1080-wide frame, and a Chinese command ran 89px past the edge. The palette is now clamped and the command fitted.
- `↵ run` belongs to the form (`INTRINSIC_TEXT`). The palette surface and tick green are fixed; ground and accent follow the DNA.

**Refuses:** `items` that is empty or not an array; more items than fit above the caption band on the frame (each row takes 78px).

**Reference:** `remotion/src/shots/CommandSummon.tsx`
