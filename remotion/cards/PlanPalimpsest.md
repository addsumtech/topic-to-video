# PlanPalimpsest

**Identity:** a survey drawing builds in two layers on the same ground — the filled footprint of what was here (walls and piers, one plane back) draws in bay by bay, then a larger dashed outline of what is here now encloses it in register, with corner crosses and a two-swatch legend underneath.

**Use when:** the claim is "this open space is the shape of something that is gone" — a later thing laid on the SAME ground as an earlier one (a demolished wing under a square, a rerouted line, a deprecated module under its replacement), where both states must stay visible at once. **Not when:** the two states are alternatives to compare side by side (use `VersusSplit`), or one replaces the other in time (use `BeforeAfterSlider`); or the subject is one thing enlarged step by step (use `ProfileGrowth`).

**Motion core:** kicker fades in 0.02–0.16; the lower plan's bays fill left to right 0.10–0.42 (each bay's floor and two piers grow in width in turn, the outer wall growing with them); the dashed upper outline grows across 0.46–0.78 while the four registration crosses fade in; the legend lands 0.74–0.92. Nothing moves after that. The lower plan sits on a plane behind the subject, so a beat camera move drifts the two layers by different amounts.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | the small spaced caps line above the plan | a short phrase reads as a survey heading; omitted, the demo `ON THE SAME GROUND` prints |
| `underLabel` | the filled-swatch legend's name (what was here) | short names sit on one line; omitted, the demo `the earlier plan` prints |
| `underDate` | a mono date line under that name | empty draws no line; a date turns the legend into a dated survey entry |
| `underNote` | a small note under the lower plan's legend entry | one short line keeps the plan large; a long note wraps, the legend reserve grows and the whole plan shrinks to make room |
| `overLabel` | the outline-swatch legend's name (what is here now) | same as `underLabel`; omitted, the demo `the later plan` prints |
| `overDate` | a mono date line under that name | as `underDate` |
| `overNote` | a small note under the upper plan's legend entry | as `underNote` — the taller of the two columns sets the reserve |
| `bays` | how many structural bays the lower footprint is drawn with | clamped to 2–9; few bays read as a broad hall with sparse piers, many as a dense nave rhythm and a finer left-to-right stagger |

**Known traps:**
- The legend used to overflow its reserve and print its last line under the burned subtitle (beat 26 of a delivered film). The reserve is now counted from the lines each string really wraps to, and the block is clamped above the caption band.
- CJK notes run to three or four lines where Latin takes two; the reserve accounts for it, but every extra line comes out of the plan's size.
- The clamp once lifted a long legend 229px off the TOP of the frame; its top is now floored at the content top. Very long legend copy still squeezes the plan — keep labels to a few words and notes to a line.
- Omitting the labels prints generic demo copy (`the earlier plan` / `the later plan`) that names nothing.

**Reference:** `remotion/src/shots/PlanPalimpsest.tsx`
