# LastLeg

**Identity:** a lit plane full of paragraph-like lines sweeps in from the left and stops hard at a bright edge. Past the edge the ground stays dark, with a dashed road running off the right. The big display word is lit on one side and dark on the other, and the uncovered tail is named.

**Use when:** it gets you most of the way and the rest is yours: an automation that handles nine steps of ten, a funnel that drops at the end, coverage with a hole. **Not when:** carried and uncarried steps are interleaved (it throws; use a register that marks each item on its own), or the claim is simply an ordered procedure (InOrder).

**Motion core:** the display word slides in over 0.04–0.34. The carry advances over 0.10–0.62 (ease-out) and stops between the last carried leg and the first uncarried one; the stop edge and the dashed road fade in with it, and carried leg chips light as it reaches them. Uncarried chips, the gap label and the note fade in over 0.70–0.88. The text lines on the lit ground drift sideways the whole time, alternate blocks in opposite directions.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | small mono label at the bottom-right | a topic tag. It turns to the on-accent ink when the carry reaches the right edge |
| `display` | one big word (28% of the short side, 20% in portrait) | never wraps, and the frame crops it on purpose. The part over the lit ground inverts. One word reads; a phrase loses most of itself off the right edge |
| `legs` | 1–6 `{label, carried}` chips spaced across a lane at the top | the carried legs must come first. Their count sets where the carry stops: all carried runs off the far edge, none carried never leaves the origin |
| `gapLabel` | the large label with a left rule, standing on the dark tail | names what is left to you. Kept inside the frame (between 5% and 74% of the width) |
| `carriedLabel` | a chip at the bottom-left of the lit ground | names the covered stretch |
| `note` | one line at the bottom-left, 62% wide | turns to the on-accent ink when the carry covers it |

**Known traps:**
- Chips used to light by POSITION behind the head, not by their own `carried` flag, so `[false, true, true, true]` drew the wrong legs lit. Each chip now reads its own flag, and a pattern the track can't draw throws.
- `note` (bottom-left) and `kicker` (bottom-right) share one line, so long copy in both collides in the middle.
- With every leg carried, the carry runs off the right and `gapLabel` sits at the right margin, reading as the contradiction it is.
- Leaving out `legs` prints the demo `brief / draft / check / send`.
- The lit plane fades out across the caption band so the subtitle sits on the film's dark ground. Keep that fade if the layout is ever changed.

**Refuses:** 0 or more than 6 legs; a leg with no `label`; a `carried` that is not true or false; no leg saying whether it is `carried`; a carried leg after an uncarried one.

**Reference:** `remotion/src/shots/LastLeg.tsx`
