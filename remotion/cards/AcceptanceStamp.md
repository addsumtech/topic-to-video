# AcceptanceStamp

**Identity:** two condition cards slide in from opposite sides and each gets its own tick; the result card below them stays a dashed, empty outline until the second tick lands, then fills, and a rotated stamp lands across its corner.

**Use when:** the claim is a conjunction — "A and B, in no order, and C does not exist unless both hold". **Not when:** the steps happen in sequence or improve on each other (that is a pipeline), there are three or more conditions (use a list register), or only one condition matters.

**Motion core:** condition A enters 0.06–0.26 from the left, B 0.16–0.36 from the right; the ticks draw at 0.30–0.40 and 0.42–0.52; the result can't start filling before the second tick, and fills 0.54–0.68 (dashed outline turns solid accent); the stamp lands 0.66–0.80, scaling down from 1.5× with an overshoot; the note fades in 0.80–0.92. After that it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `conditions` | the two things that must both hold, one per card | shrink-to-fit inside a card sized from the frame's short side, with balanced wrapping; a long condition wraps to two lines and gets smaller rather than overflowing |
| `result` | what exists only when both hold, in the larger card | fitted to the result card's width; a short noun reads as the deliverable, and a sentence shrinks |
| `stamp` | the word on the stamp | fitted to about 0.30 of the short side; one short word (`ACCEPTED`, `APPROVED`) keeps the stamp look, and a phrase shrinks it to a label |
| `note` | an optional line under the result, for the consequence | `''` (default) draws nothing; long text wraps inside the side margins, in dim ink |

**Known traps:**
- Exactly two conditions. With one it used to draw an empty second card, and with three it silently dropped the third. It now throws instead.
- Omitting the props prints demo copy: `Condition one` / `Condition two` / `The deliverable` / `ACCEPTED`.
- The `×` between the cards belongs to the form (it's declared in `INTRINSIC_TEXT`). It means AND, so don't use this register for "then".
- Chinese breaks between any two glyphs, so the cards use `text-wrap: balance`. Otherwise a stray glyph lands on its own line and reads as a typo.
- Every size is a fraction of the short side, so the layout reflows at 9:16 and isn't a landscape layout squeezed to fit.

**Refuses:** `conditions` that is not an array holding exactly two non-empty strings.

**Reference:** `remotion/src/shots/AcceptanceStamp.tsx`
