# InOrder

**Identity:** the content zone is cut into one band per step, edge to edge. The band the frame is on widens while the others narrow; finished bands fill solid and pending ones stay outlines. The focus either walks through the whole sequence or rests on one step.

**Use when:** the order is the claim: a procedure, a handoff chain, a lifecycle, what happens between A and B. Use `at` for a beat that narrates one step. **Not when:** there are more than six steps, the steps are dated history (EdTimeline), or the process stops short and the remainder is the point (LastLeg).

**Motion core:** the bands grow in from the leading edge over 0.04–0.30. With no `at`, the focus walks from the first step to the last over 0.10–0.92 (easing in and out); each band widens as the focus passes and turns "done" once it has passed. With `at`, the focus is pinned and only the entrance moves. On a portrait frame the bands stack top to bottom instead of left to right.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | small spaced mono label, top-left in the title band | a topic tag above the process name |
| `whole` | the process name, large display type under the kicker | a short name sits in the title band. Not fitted: a name long enough to wrap runs down onto the bands |
| `steps` | 1–6 `{label, note}`, one band each, numbered 01, 02, … | the focused band takes 62% of the axis with 1–2 steps, 46% with 3–4, and 38% with 5–6. A band narrower than 12% of the frame's short side hides its label and shows only its number. `note` appears only on the live band |
| `at` | the 0-based step the frame rests on | omitted, the focus walks the sequence. Set, the frame holds on that step, with the steps before it drawn as done |
| `doneLabel` | the mark that replaces the number on finished bands | e.g. `✓`. Left empty, finished bands keep their numbers |

**Known traps:**
- Steps used to be cut to six without a word, which stated the wrong count. More than six now throws: group the steps into stages, or split the process across two beats.
- An out-of-range `at` is clamped, not refused: `at: 9` on five steps rests on step 5 with no error.
- Leaving out `steps` prints the placeholder `first / second / third / last` with their notes.

**Refuses:** 0 or more than 6 steps; a step with no `label`.

**Reference:** `remotion/src/shots/InOrder.tsx`
