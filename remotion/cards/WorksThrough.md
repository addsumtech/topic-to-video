# WorksThrough

**Identity:** the subject is CUT OPEN — a sectioned body, hatched like a mechanical drawing, fills the content zone — and one live path threads THROUGH its parts, widening where a part carries and bending where a part turns it. The path is the only bright thing in the section, so the eye follows the mechanism rather than reading a diagram of it.

**Use when:** the beat's claim is HOW something works — the mechanism that produces the outcome, where the point is that the path passes through THESE parts and not others. **Not when:** the claim is what the thing is made OF (`MadeOf` — that is a partition, and its regions do not carry anything through); not the ORDER of steps (`InOrder` — steps follow one another, they do not act on what passes); not what the thing RESTS on (`RestsOn`); not where it STOPS (`HardBarrier`); not one body being re-apportioned (`SameStuffChanged`).

**Why it is not a flow chart.** Boxes and arrows say "A then B", which is a sequence, and a sequence is the one thing a mechanism is not: the parts are all there at once and the path is in all of them at once. Drawn as a chart, "the requirement is traced to your file and only then written down" reads as three steps a reader could reorder. Drawn here, the path visibly narrows at the part that loses most of it, so the claim survives the caption being hidden — which is the test.

**Motion core:** the path TRAVELS, left to right, and the band is cut flat at wherever it has reached. The section, its hatch and the part labels are already there, so what moves is the one thing the beat is about. Nothing moves after the path lands on the outcome: the settled frame carries the whole claim.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `parts` | the parts the path runs through, in order, 2 to `MAX_PARTS` (5) — each `{label, carries, deflect}` | `carries` is unitless and sets the path's WIDTH across that part — the film's own reading of how much gets through, never printed, so no figure appears that no source supports. `deflect` is -1 (up) .. 1 (down) and is clamped to that range, so a bigger number cannot push the path out of the section it is threading. The order is the film's; the register infers nothing from it |
| `subject` | what is cut open | in the film's words, set into the section's corner |
| `outcome` | what arrives at the far end | sits to the right of the section, where the path lands |
| `kicker` | the spaced label over the section | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the section, in the film's voice | where to say what the mechanism MEANS |

**Known traps:**
- **The path must be CONTINUOUS, and the first version was not.** Each bay held one `y` for its whole width and the polygon put two vertices at the same x on the boundary, so every turn was a vertical segment of ZERO width. The demo's gentle deflections left neighbouring bands overlapping and it read as a path; fed ±0.9 on five parts it rendered as five disconnected rectangles — the opposite of the claim. The centre line now ramps ACROSS the part that deflects it, and `tests/test_works_through.py` measures connectedness column by column on the real render.
- Labels are placed by ROOM — each measures the gap above and below the band **across its whole bay**, since the band slopes — and takes the larger. Reading the band's position at one x put a label under the path it named.
- Fewer than two labelled parts throws (one part is a box with a caption), more than 5 throws (a narrower bay cannot show a deflection, and the deflection is the picture), and a board where nothing carries anything throws.
- Its list props go through `runtime/rows`, so a board that sends a string where a list belongs is told that, by name, instead of dying in `parts.map is not a function`.

**Measured:** 2.9% ink (clip median) · 56.4% footprint · 0.0011 motion · 3.9% ink on the settled frame. Footprint in the library's top fifth, ink at p34 and under the study's 12% floor — this register closes the mechanism gap in the ARGUMENT, not in the density. Cast it for the claim and intercut it with something denser.

**Reference:** `remotion/src/shots/WorksThrough.tsx`

**Provenance:** scientific. **Family:** I. **Ground:** `bg` (`DNA_GROUND_TOKEN`), measured dark.
