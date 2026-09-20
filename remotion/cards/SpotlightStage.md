# SpotlightStage

**Identity:** a warm spotlight with a cone of light sweeps across a black stage, lighting up a row of words one at a time as it lands on each; then it returns to centre and widens to light the whole row, arrows appear between the words, and a spaced wordmark fades in below.

**Use when:** a dramatic, premium reveal of a short CHAIN — 1–5 words that follow one from the next (plan → build → ship), each deserving its own moment. **Not when:** the words are unordered (the arrows assert a sequence), long phrases, or more than five (use a timeline or list register).

**Motion core:** the light travels from word to word 0.08–0.56 (each leg eased), words brightening from near-black to cream as it nears them; it slides back to centre 0.56–0.74, then widens 0.76–0.94 until every word is lit. The arrows fade in 0.80–0.95 and the wordmark 0.84–0.98.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | the words on the stage, in order | 1–5, one shared size — the largest that leaves room for an arrow in every gap and keeps the outer words on frame. More or longer words set everything smaller; below the minimum size it refuses. Omitted, the demo `PLAN / BUILD / SHIP` prints |
| `wordmark` | the widely spaced mono line under the row, shown at the widen | a brand or sign-off; fixed size, not fitted; omitted, the demo product name `WORKBUDDY` prints |

**Known traps:**
- The arrows used to be exactly two at fixed offsets: with two words a stray reversed arrow crossed the last word, with four or five the chain stopped halfway, and even the demo's arrows ran through PLAN and BUILD. The light likewise never visited a fourth word. Now there are *n* − 1 arrows edge to edge and the light visits every word.
- The arrows appear whatever the words are, so the frame always asserts word 1 → word 2 → …; don't hand it items with no order.
- The stage is built for black: the lit/unlit word ramp, the warm light and the vignette are fixed; only the ground follows the DNA.
- Omitting `wordmark` prints a real product name.

**Refuses:** fewer than 1 or more than 5 items; an empty item; words too long to fit one line with arrows between them at this aspect.

**Reference:** `remotion/src/shots/SpotlightStage.tsx`
