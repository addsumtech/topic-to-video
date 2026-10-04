# ExtractionFlow

**Identity:** two to four columns, one per setting of the same thing, all started at the same instant: each holds the thing the film drew in that case's state, the stream it lets through, the vessel that stream fills, a time bar on a scale every column shares, and where its result lands between two named ends. The slow column is still running when the fast one has finished — the setting decides the time, and the time decides the result.

**Use when:** one setting decides how long something takes, and how long it takes decides the result — a grind and its extraction, a dose and its time to effect, a filter and its throughput — and the film has drawn the thing. **Not when:** the cases differ in one visible point rather than in time (`ObjectCompare`), or the comparison is a number on an axis (`EdCompare`, `VersusSplit`).

**Motion core:** every column starts at the same instant; each object runs its own clock at its case's pace (the slowest finishes at 0.74 of the beat) while its stream fills its vessel and its time bar grows, and its time, verdict and result dot land as it finishes.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `object` | the thing in every column — `{"id": …, "props": …}`, an object the film drew | required in a film; each case's own `props` are merged over its props, so one object shows every setting |
| `cases` | 2–4 columns, left to right: `label`, that case's object `props`, `pace`, `lean`, `time`, `verdict`, `target` | required in a film; `pace` is the case's duration relative to the slowest, (0.05, 1]; `lean` (0..1) is where its result sits between the two ends and how strong its vessel is drawn; `target` frames the column the film recommends |
| `lowLabel` | the result scale's low end | short — it is set beside every column's scale |
| `highLabel` | the result scale's high end | short — it is set beside every column's scale |
| `title` | the claim, in the title band | fitted to 84% of the width |
| `kicker` | a small spaced label above the title | follows the DNA's label spacing |

**Known traps:**
- `pace` is a ratio between the cases, not a duration: the slowest case finishes at 0.74 of the beat whatever its length, so a real figure belongs in that case's `time`, as words.
- Each object is handed its own clock: it settles over the first 0.12 of the beat, then runs the rest of its clock at its case's pace. An object that draws its process over its clock (a flow, a fill) shows the difference itself; a static one leaves the bars to show it.
- The vessel's strength runs from the film's pale end to its deep end (`runtime/light` `paleEnd`/`deepEnd`), so a strong result is the darker one on a dark film and on a paper one alike.
- Promoted from the film 一台意式咖啡机是怎么萃取出一杯浓缩咖啡的 (three espresso pucks ground coarse to fine: sour, balanced at about 25 s, bitter), where it was judged against: 遮住字幕：看得出三块粉饼颗粒从粗到细，下面三只杯子装满的先后不同，计时条一短一中一长，味道尺上的点从酸的一端移到苦的一端，咖啡颜色从浅到深. The first film that meets a trap here writes it down.

**Refuses:** fewer than 2 or more than 4 cases; a `pace` outside (0.05, 1] or a `lean` outside 0..1; an object nobody defines.

**Measured:** 4.2% ink (clip median) · 36.4% footprint · 0.0005 motion. Measured on the register's own preview — three of objects/DemoForm with one setting (`layers` 2, 3, 4) stepped across them — so the numbers describe the preview, not a film's object.

**Reference:** `remotion/src/shots/ExtractionFlow.tsx`

**Provenance:** industrial (a beat holding objects is judged on their own world). **Family:** H. **Ground:** `bg` (`DNA_GROUND_TOKEN`), measured light; it follows the film's ground across the frame.
