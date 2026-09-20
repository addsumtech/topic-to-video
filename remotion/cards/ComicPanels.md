# ComicPanels

**Identity:** a comic page on halftone paper. A top row of tilted, ink-bordered action panels snaps in one by one, each with converging speed lines, a big stroked sound-effect word and a panel number. Then a full-width splash panel below bursts in with the payoff word.

**Use when:** the beat is a quick build-up of short beats landing on a payoff, told as comic onomatopoeia (`ZIP!` `WHIRR` `CLICK` → `DONE!`). **Not when:** the panels must show pictures or sentences. They carry one big word each, with no illustration.

**Motion core:** panel i pops in (rising 40px, scaling 0.92→1, with an overshoot) over 0.08 + i·0.13 → 0.34 + i·0.13; the splash bursts in 0.60–0.84. Then it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `panels` | one top-row panel per word, in reading order | all in one row, so the column width divides by the count. Three panels are roomy; more make narrow panels, and the fixed 92px word is clipped at the panel border (panels hide overflow) |
| `splash` | the payoff word in the splash panel | fixed 190px, stroked, not fitted; one short word is the look, and a phrase is clipped at the panel edges |

**Known traps:**
- Omitting props prints the demo `ZIP!`, `WHIRR`, `CLICK` and `DONE!`.
- The words aren't fitted: long captions and Chinese sentences are cut off by the panel borders, not wrapped or shrunk.
- The panels enter 0.13 apart, so an eighth panel only starts on the last frames and later ones never appear.
- `title` used to be declared and never drawn, so a film's copy vanished silently. It was removed; there is nowhere on the page for a title.
- Rows used to be 0.52 of the frame height, which put the splash (`DONE!`) 81px into the caption band at 1:1. The page is now laid out to the content zone.

**Reference:** `remotion/src/shots/ComicPanels.tsx`
