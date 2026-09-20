# RestsOn

**Identity:** a stack of solid bands builds from the bottom up — the broadest reason lands first at the base, each narrower reason settles onto the one below it, and the phenomenon itself, narrowest and on top, lands last — so the frame reads as one thing standing on its causes.

**Use when:** the beat explains MECHANISM — "this happens because of that, which rests on this deeper reason" — with the root cause as the widest, lowest band. **Not when:** the order is a sequence in time (use `InOrder`), or the reasons are parallel and equal rather than deeper and deeper (a list register).

**Motion core:** the kicker fades in 0.02–0.18. Bands arrive bottom-up: the root from 0.08, each level above it 0.13 later, each taking 0.26 and dropping a short way onto what is beneath it; the effect settles last (by about 0.73 with three causes, 0.99 with five). The joint word appears with the immediate reason. Then the frame holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | a small spaced mono line above the stack | empty draws nothing; a few words say what the frame is about |
| `effect` | the phenomenon, in the top (narrowest, accent-toned) band | large display type sized to the band; empty leaves the top band as a bare coloured slab |
| `effectNote` | a smaller line under the effect | empty draws nothing; hidden when the band is too short to hold it |
| `causes` | the reasons, 1–5, `{label, note?}`, IMMEDIATE FIRST and ROOT LAST | one band each below the effect, each wider than the one above. More causes make thinner bands with smaller type (sized from the band's height and width); a note is always drawn, and when label and note do not fit a short band together the type steps down until they do. Omitted, three demo causes (`the immediate reason` … `the root`) print |
| `because` | the joint word on the seam between the effect and the immediate reason | empty draws nothing; a short word ("because", "由于") rides the seam on a chip of the ground colour |

**Known traps:**
- `causes` used to be cut to five without an error — and the root is LAST, so a sixth entry cost the deepest reason. It now refuses a sixth; merge intermediate reasons instead of dropping the root.
- Text is sized to its band's height for ONE line of label and one of note, but the band clips: a label or note long enough to wrap in a thin band is cut off, not moved.
- The joint word used to be printed inside the effect's bottom edge (the bands tile with no gap); it now sits on its own chip on the seam, and only on the first seam.
- Omitting `effect` draws the top band empty; omitting `causes` prints demo reasons.

**Refuses:** no `causes`, or more than five (at five a label and note already set at 37/22px on 16:9 — merge intermediate reasons, never drop the root); a cause with no `label`.

**Reference:** `remotion/src/shots/RestsOn.tsx`
