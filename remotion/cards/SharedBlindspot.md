# SharedBlindspot

**Identity:** two panels of the same field of small case-marks; in each, two producers' blind areas expand in as rings (one solid, one dashed, in the warning accent). On the left the rings nearly coincide and their overlap fills as one shared hole of empty outlines; on the right they sit apart, and every case inside a ring lights up because the other producer still catches it.

**Use when:** the claim is CORRELATED versus INDEPENDENT failure — two checks from one source share one blind spot, two independent checks cover each other (self-review vs outside review, same-model vs cross-model checking). **Not when:** the comparison is about amount or score (a chart or versus register), or there is only one producer.

**Motion core:** title and kicker fade in 0.01–0.11 and the panels 0.01–0.14 (the right a beat later); the case-marks appear scattered 0.04–0.31; the first ring expands 0.28–0.41, the second 0.41–0.54; the cases then resolve 0.54–0.79 — caught-once cases grow and light in the accent, cases inside both rings turn into empty warning outlines — while the shared lens fills 0.56–0.70; the notes fade in 0.62–0.76.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | the small line above the title, in the accent | empty draws nothing; omitted, the demo `Correlated vs independent` prints |
| `title` | the headline across the top | fitted to at most two lines (so long copy prints smaller), and the panels start below however many lines it takes; omitted, a demo headline prints |
| `shared` | the correlated (left, or top) panel: `label`, producer names `a` and `b`, `note` | the label is drawn in the warning tone, the two names sit beside a solid and a dashed swatch matching the rings. All labels share one size across both panels, all four names another — one long name shrinks all four (dropping to two lines only when it gets very small). Omitted, demo copy about a draft and its own review prints |
| `independent` | the independent (right, or bottom) panel, same fields | as `shared`, with the label in the accent |
| `cases` | how dense the field of case-marks is | clamped to 40–260 and rounded to a grid (8–18 columns, 5–14 rows), so it sets density, not an exact count: more cases give smaller, finer marks and a more even-looking hole |

**Known traps:**
- The ring positions are a fixed diagram, not data: the left panel always shows a large shared hole and the right none. It argues the mechanism; it measures nothing — don't narrate the hole's size or the case count as a figure.
- The warning tone is the DNA's second accent and "caught" is the first. A DNA whose second accent does not read as a warning weakens the blind/caught split.
- The rings are clamped to stay inside their field, so their separation depends on the field's shape: on a near-square field (1:1) the clamp pulls the independent pair closer together.
- The two panels are peers, so type is sized once per role across both; don't fit each panel separately.

**Reference:** `remotion/src/shots/SharedBlindspot.tsx`
