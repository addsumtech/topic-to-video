# MapPlate

**Identity:** an engraved survey plate draws itself — a double-ruled frame and graticule, a ringed subject mark named at the centre, labelled outer place marks, and, when asked, hairline routes into the centre and a double-banked channel across the plate, a scale bar and a note.

**Use when:** the claim is positional — "where a thing sits, and what that position does to it": a hub, a frontier, a site, a catchment, with up to eight other places at known relative positions. **Not when:** the nouns are systems and integrations (a network register such as KnowledgeGraph speaks that dialect), or the positions are not known — every mark needs coordinates.

**Motion core:** title and plate frame draw over 0.02–0.20 (the frame widening left to right); the graticule lines grow one after another over 0.12–0.40 with the scale bar fading in alongside; a channel draws from its `from` end over 0.30–0.62; the subject ring scales in and its name fades up over 0.34–0.50; outer marks pop in from 0.44, 0.045 apart, and routes draw into the centre from 0.46 on the same stagger; the note fades in over 0.80–0.94; then it holds still.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | a small mono line above the plate's top-left corner, in the accent | uppercased and tracked unless the DNA says otherwise; empty draws nothing |
| `place` | the subject's name under the centre ring | set in the display face in a centred box about a quarter of the frame wide; a long name wraps under the ring |
| `marks` | 0–8 outer places: `label`, `x`, `y` in 0..1 of the plate | none gives a lone subject on an empty plate; 8 crowd the edges. Each label goes on the side with room, is clamped inside the plate, sized to its text up to a third of the plate, wraps to at most two lines, and steps vertically clear of the subject's name |
| `routes` | whether hairlines run from every mark INTO the centre | on, the plate argues convergence on the subject; off (the default for a film) the marks just sit in position |
| `channel` | a double-banked band between two plate points: `from`, `to`, optional `label`, optional `width` (fraction of the plate width) | reads as a river, cut or corridor; a wider `width` makes it a broad waterway. Its label sits a quarter along on the side away from the subject, or above its bank when both quarters would hit the name |
| `scaleLabel` | a four-segment scale bar with this text, bottom-left inside the plate | empty draws no scale bar |
| `note` | a mono line under the plate, the plate's full width | a source or reading note; wraps if long |

**Known traps:**
- This register used to supply positions and relations nobody stated: marks with no coordinates landed on the subject, `routes` defaulted to true (every film "converged"), and a labelled channel with no ends ran the demo diagonal. All of those now throw or need `routes: true` — only the standalone demo (omitting `marks`) still draws its converging compass, and omitting `place` prints `the place`.
- `x`/`y` are fractions of a plate that is 60% of the frame wide and nearly as tall as the content zone, not a map projection — the same marks spread wide and flat at 16:9 and narrow and tall at 9:16.
- The scale bar is always the same four-segment length; `scaleLabel` states a distance only if the film placed the marks to that scale.
- Labels past ~15 characters used to be cut with an ellipsis; they now wrap, but the box is still clamped at two lines, so a label longer than two lines of its box is still cut.

**Refuses:** `marks` not an array or more than 8; a mark whose `x` or `y` is missing or outside 0..1; a `channel` whose `from` or `to` is not `[x, y]` with both in 0..1.

**Reference:** `remotion/src/shots/MapPlate.tsx`
