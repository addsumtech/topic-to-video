# CollaborativeCursors

**Identity:** a camera flies over a dotted design canvas of white artboards. One name-tagged cursor per collaborator, each in its own colour, glides in and rests on its board. A selection box in that colour appears while the board's placeholder deliverable builds (chart skeleton, doc lines, slide, table), a ✓ appears only where the film says done, and the camera settles on the whole grid.

**Use when:** the beat is "many people or agents working in parallel, each on their own piece", with 1–6 named workstreams. **Not when:** the deliverables need real content: a chart here is equal placeholder bars and a doc is placeholder lines. It's also wrong when the work is sequential.

**Motion core:** board i arrives at 0.14 + i·pitch (at most 0.11, shrinking with the count so the last cursor leaves by 0.94). Its cursor glides in over the 0.30 before arrival, the build runs for 0.34 after it, the selection box lasts the build plus 0.14, and the ✓ appears after the build. The camera holds wide 0–0.20, sweeps down-right and pushes in to 0.60, and settles on the whole grid by 1.0. The clip is 6 s, longer than most.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `names` | the boards: a name, or `{name, kind?, done?}` | a name alone gives a clean artboard. `kind` (`chart`, `doc`, `slide`, `table`) adds that placeholder build, and `done: true` earns the ✓. The grid is three across (two in portrait) with a short last row centred; one to three boards read spacious, six fill the canvas |

**Known traps:**
- Deliverables, emphasis and completion used to be decided by position: the first two names got charts, a pastry chef built a bar chart, the fourth bar was highlighted, every board got a ✓, and the camera ended on the fifth board. All of it now comes from each board's own fields.
- Omitting `names` prints six demo departments (`Market Research`… `Data Cleanup`), all marked done.
- The names aren't fitted: 22px on a 380px board, and the cursor tag is `nowrap`, so long names spill past the board.
- During the sweep the canvas is larger than the frame and crops boards (`data-bleed`); only the settled frame shows every board.
- The collaborator colours are a fixed six-colour palette, which is each board's identity; canvas, panels and ink follow the DNA.

**Refuses:** `names` that is not an array of 1–6 entries; a board with no name; `kind` other than `chart` / `doc` / `slide` / `table`; `done` that is not `true` / `false`.

**Reference:** `remotion/src/shots/CollaborativeCursors.tsx`
