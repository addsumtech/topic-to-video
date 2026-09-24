# SameStuffChanged

**Identity:** ONE body, re-apportioned. Each stage's cells are normalised to the same total area and matched by position, so a cell that splits is SEEN splitting rather than cross-fading into two new ones; whatever LEAVES at a stage is drawn as a hatched part of that same body, struck through rather than silently dropped. Nothing arrives from off-frame, because the claim is that nothing arrives at all.

**Use when:** the beat's claim is that a process does not move a thing between stages but CHANGES one thing continuously — the same material, arranged differently, and the interesting part is what the re-arranging costs. **Not when:** the stages are separate steps acting in turn (`InOrder`); not a static partition of what something is made of (`MadeOf` — one stage is a partition, and that register already draws it); not two states held up against each other (`BeforeAfterSlider`); not a path through parts (`WorksThrough`).

**Why it is not a pipeline.** A pipeline draws boxes with arrows between them, and an arrow says the thing moved from here to there — which is precisely the misunderstanding the beat exists to correct. Drawn that way, "these are the same jobs, counted differently" reads as three different populations. Drawn here, the body never leaves and never grows: the viewer watches one quantity get cut up, and the write-off is visibly part of what was there.

**Motion core:** the re-forming is the motion, and it has to be SEEN happening — the register runs 6.5s for that reason, and the stage's own name sits on the body rather than in a legend. Area is conserved on every frame, not only on the two settled ones: the widths are interpolated and the positions laid out from them, so the drawn total is the sum of the lerped widths and cannot drift.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `stages` | the stages in order, 2 to `MAX_STAGES` (4) — each `{label, cells, lost, lostLabel}` | each stage is a whole reading of the same material. `cells` holds that stage's parts, up to `MAX_CELLS` (8), as `{name, share}`; `share` is unitless and normalised per stage, so the areas are the film's proportions and no figure is printed. `lost` (0..0.95) is the share that LEAVES here, drawn hatched over a ghost of the material's own fill — quieter than the material that stays — and `lostLabel` names it in words rather than a number |
| `kicker` | the spaced label over the body | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the body, in the film's voice | where to say what the re-forming MEANS |

**Known traps:**
- **Conservation is the claim, so it is enforced arithmetically.** The first version lerped each cell's `x` and its `w` from independent endpoints, and two lerped edges only meet at the endpoints: mid-split the cells overlapped and the drawn body measured 1301px of 1652 — 21% of the material off the frame while the narration said none of it went anywhere. Both settled frames were exact, which is why reading the code and checking the ends both missed it. `tests/test_same_stuff_changed.py` measures the drawn span mid-re-forming.
- **A label is drawn only where its box can hold it**, via `layout.fitsBox` — every box here changes width for the whole shot, so a fixed floor is a floor for one string and nothing else. At `w > U * 0.05` a 70px sliver kept its seven-glyph name and the browser set it one glyph per line.
- Fewer than two stages throws, more than 4 throws (past that each re-forming is too brief to be seen happening, and being seen to happen is the whole picture), and more than 8 cells in a stage throws.
- Its list props go through `runtime/rows`, so a board that sends a string where a list belongs is told that, by name. Dropping the bad value silently was the first repair and it was worse: the register then refused with a message about the stage COUNT, sending the reader after data that was present in the wrong wrapper.

**Measured:** 2.9% ink (clip median) · 54.1% footprint · 0.0031 motion · 16.9% ink on the settled frame. The clip median is low for a reason that is the register's own argument: it OPENS as one undivided block and gains structure only as it re-forms. The settled frame clears the study's 12% floor; the first stage is honestly empty and the last one is not.

**Reference:** `remotion/src/shots/SameStuffChanged.tsx`

**Provenance:** scientific. **Family:** I. **Ground:** `bg` (`DNA_GROUND_TOKEN`), measured dark.
