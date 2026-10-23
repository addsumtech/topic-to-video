# CroppedType

**Identity:** one word set far larger than the windows it moves through: two bands across the frame, each a clip the word is too big for, so it is seen cropped top and bottom and sliding past — one band solid in the accent, the other in outline, drifting in opposite directions — over the plain sentence the word stands for.

**Use when:** the claim is SCALE — "this is the big thing" — and one word carries it; the crop is what makes the word read as big rather than merely large type, because the eye completes the letter past the edge. The statement underneath is the line that must be read. **Not when:** the word must be read whole and still (`VariableTypeMorph`), or the beat is a headline (`HeadlineReveal`).

**Motion core:** the letters rise into each band from below its edge (0.045 s apart, 0.9 s, expo.out), the second band a beat later; then the word drifts the whole shot, a tenth of the frame's width over the beat, the two bands in opposite directions, with the type unlock on throughout so it glides rather than stepping a pixel at a time. The bands' hairlines draw in; the statement rises line by line through its masks.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `word` | the one word (or two), repeated along each band | up to 18 characters; the crop is a fifth or so of the letter past each edge (Latin capitals and Han glyphs sized separately) |
| `statement` | the sentence the word stands for — the line that must be read | kept whole on one or two lines where it can be |
| `direction` | which way the solid band drifts; the outline band goes the other way | `left` or `right` |
| `kicker` | a small spaced label | not held to a reading time |

**Known traps:**
- The crop is a WINDOW, which is what the type gates accept: each band is an overflow clip that does not cover the frame, so `text_safe_qa` reads the cut as the author's. The same word cut by the frame edge with no window is a finding, correctly.
- The outline is a stroke under a ground-coloured fill (`paint-order: stroke fill`). A variable face keeps its overlapping contours, and a plain text stroke drew every one of them — lines through the middle of E and R.
- A crop leaves slivers: where a stroke ends a pixel or two inside the band, it reads as a rule along the edge (「更」's top bar did). The band's edges fade over a few pixels, so a sliver disappears and a stroke cut through its body still reads as cut.
- At 1.62x the band the capitals just filled it — 9% a side — and read as large type in a box; it is 1.95x for Latin, 1.5x for Han.

**Refuses:** an empty `word`; a word over 18 characters — a cropped phrase cannot be read by its crop, so the phrase belongs in `statement`.

**Reference:** `remotion/src/shots/CroppedType.tsx`

**Measured:** 12.8% ink (clip median) · 53.7% footprint · 0.0128 motion · reach 0.735 — clears the motion and ink floors. Holds: clean at its own 5.5 s.

**Review:** NOT critic-reviewed — built and looked at by its author (16:9 / 9:16 / 1:1, Latin and Chinese, three DNAs).

**Provenance:** motion-graphics. **Family:** P.
