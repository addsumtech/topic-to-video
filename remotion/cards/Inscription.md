# Inscription

**Identity:** a stone tablet opens across the frame, and lines of text are cut into it: each glyph is painted three times (shadow, highlight, ink) so it reads as a V-cut groove. Then a larger date lands in the accent, with a small mono line under the stone.

**Use when:** a date or moment somebody meant to be remembered: a founding, a dedication, a treaty, a launch. The act of commemorating is the point. **Not when:** the date is one entry in a chronology (EdTimeline), or the beat defines what a name means (GazetteerEntry).

**Motion core:** the face widens left to right over 0.02–0.22. The lines are cut in one after another, 0.11 apart, from 0.24. The date and the foot line land over 0.74–0.92 (quick ease-out). Then the frame holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `lines` | the cut text, one row each, 0–4 | 1–2 rows are set at 4.4% of the frame width, 3–4 rows at 3.6%; when the rows plus the date would be taller than the face inside its chamfer (four rows and a date at 16:9), rows and date shrink together until they clear it. The text is used as written (nothing uppercases it) and is not fitted to the WIDTH: with 0.10em tracking, a long line runs past the face (at most 62% of the width) |
| `date` | the line the beat turns on, 7% of the width, in the accent | lands last and largest. Empty means no date row |
| `foot` | a small mono line under the stone, in the film's own voice | a source or context note. It lands with the date |
| `face` | the stone's tone | empty uses a darker cut of the DNA's surface. Any colour re-stones the tablet, and the shadow and highlight follow it |

**Known traps:**
- Leaving out `lines` prints the placeholder `THE WORDS CUT HERE / AND WHAT THEY MARK`. The default was once `THE FIRST STONE`, copy taken from one film, which the demo-default check could not tell from a film's own.
- Keep lines short. This is stone: neither the rows nor the date are fitted to the face's width (only the stack's height is).

**Refuses:** more than four `lines` (the fourth row finishes cutting as the date lands; a fifth would still be cutting when the date should land last — move the rest to `foot`); an empty line; no lines and no `date`.

**Reference:** `remotion/src/shots/Inscription.tsx`
