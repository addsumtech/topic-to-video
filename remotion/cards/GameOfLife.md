# GameOfLife

**Identity:** Conway's Game of Life evolves across the whole frame from a fixed seed, live cells glowing in the accent, while a wordmark and tagline resolve over a dark centre vignette.

**Use when:** emergence — "simple rules, complex life" — as a title beat. **Not when:** the beat carries items or data (the grid takes none), or the frame is far from 16:9 (see traps).

**Motion core:** the automaton steps 24 generations over the clip, each a hard step with no tween, so the cells change the whole time; the title rises 0.42–0.66, the tagline 0.60–0.82.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the wordmark | fixed 128px, not fitted |
| `tagline` | the tracked mono line under it, in the accent | fixed 30px, not fitted |
| `accent` | the live cells, their glow, the title's glow and the tagline | a hex literal, not the DNA; default green |

**Known traps:**
- The grid is a fixed 64×36 cells stretched to the frame, so away from 16:9 the cells are not square — tall slivers at 9:16.
- The seed is fixed: every film shows the same evolution.
- Title and tagline are not fitted; defaults print 'Emergent' / 'simple rules, complex life'.

**Reference:** `remotion/src/shots/GameOfLife.tsx`
