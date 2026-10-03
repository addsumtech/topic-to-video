# ObjectCompare

**Identity:** two things the film drew stand at one size on one floor — or one above the other on a tall frame — each named under itself; a ring marks the same point on both, a dashed tie joins the rings, and the one difference is set under the pair.

**Use when:** the beat says "these two differ HERE": one object in two states (loose and tamped, before and after, 1900 and now) or two things with one decisive difference, and the film has built them. **Not when:** the difference is a number (`VersusSplit`, `EdCompare`), two photographs (`RealVersus`, `BeforeAfterSlider`), or more than two things.

**Motion core:** the first object's `t` runs 0→1 over 0.06–0.44, the second's over 0.16–0.54, so they are read in order; their labels follow (0.4–0.62). The rings draw on over 0.58–0.7, the tie over 0.64–0.76, the difference lands over 0.66–0.82.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `first` | the first thing the film drew — `{"id": …, "props": …}` | required in a film; the same object with different `props` in `second` is the commonest compare (one thing, two states) |
| `second` | the second thing | required in a film; arrives a beat after the first |
| `firstLabel` | what the first is, under it | balanced, up to two lines |
| `secondLabel` | what the second is, under it | balanced, up to two lines |
| `difference` | the one difference, in words, under the pair | required in a film; wraps balanced in up to the width of both |
| `at` | `{x, y}` in 0..1 of each object's box — where the difference is | a ring on both at the same relative point, tied with a dashed line; absent: no rings |
| `kicker` | a spaced label in the title band | follows the DNA's label casing |

**Known traps:**
- Two objects of one aspect are drawn at one size on purpose: the register refuses to emphasise one by scale. Objects of different aspects each fit the same room.
- `at` is the SAME fraction on both boxes — it assumes the two objects share a layout (the same object in two states). For two different things, mark nothing, or draw the mark inside each object.

**Refuses:** an object that is not `{id, props?}` or that nobody defines; an `at` that is not `{x, y}` in 0..1; on a tall (stacked) frame, labels and a difference that still do not fit above the caption band at half size — the message names the px they needed and the px the frame had.

**Measured:** 2.2% ink (clip median) · 18.9% footprint · 0.0017 motion · 2.2% ink on the settled frame. Measured on the register's own preview — objects/DemoForm — so the numbers describe the stage with its preview form, not a film's object.

**Reference:** `remotion/src/shots/ObjectCompare.tsx`

**Provenance:** motion-graphics (a beat holding objects is judged on their own world). **Family:** H. **Ground:** `bg` (`DNA_GROUND_TOKEN`), measured light.
