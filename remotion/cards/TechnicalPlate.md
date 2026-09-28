# TechnicalPlate

**Identity:** an ordinary object is drawn stroke by stroke — or as a drawing the film built — as a flat technical elevation inside a ruled sheet. Numbered callout dots then throw leader lines out to a parts key in the margins, and the object's name is set under the plate like a caption.

**Use when:** the claim is "this everyday thing IS the mechanism", where an unremarkable object does the load-bearing work (a bicycle as a station's last mile, a valve as the safety case, a form as the policy) and the parts the argument names can be pointed at. Ghost strokes let it also argue what is missing. **Not when:** the object has no clean flat elevation — neither hand-drawn strokes nor a drawing the film built read as one — or the parts are a process in sequence rather than places on one object.

**Motion core:** the sheet border draws across over 0.02–0.18 with the kicker and plate number. The strokes then draw in array order, each in an equal slice of 0.14–0.62: lines extend from their start point, circles scale up and fade in, bars grow in width. From 0.60 the callouts follow, staggered by up to 0.10 each, with the dot appearing and the leader running out to the margin. Object name and note land over 0.66–0.88.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | small spaced caps top-left | leaving the demo `PLATE` prints it on any film |
| `object` | the object's name, set centred under the sheet | a short name reads as a plate caption. Long or CJK names wrap, and the caption block is measured and lifted to stay out of the caption band. Leaving the demo in place prints `the object` |
| `plateNo` | the sheet's own number, top-right | like "FIG. 3". Empty draws nothing |
| `strokes` | the object in square unit space (0..1): `circle {x,y,r}`, `line {x,y,x2,y2}`, `bar {x,y,w,h,fill?}`, each optionally `ghost` | the drawing keeps its proportions at any aspect and is centred in the sheet. More strokes means each draws faster. `ghost: true` draws the stroke dashed and dim, as a part that is not there. On a circle or line `w` is a stroke-weight multiplier; on a bar `w` is its width |
| `art` | a drawing the FILM made (an object from its workshop, `{"id": …, "props": …}`), in place of `strokes` — drawn in its OWN square in the drawing field, capped above the plate's caption, on the plate's drawing phase (its t runs 0→1 over 0.14–0.62) | the parts' `x,y` are fractions of THAT square — the art's own, not the full field — so the callouts still land on the drawing even where the caption has capped it smaller than the field; one drawing per plate |
| `parts` | 0–6 numbered callouts, `{n?, label, x, y, side?}` | `x,y` put the dot on the drawing. `side` (default `right`) sends the leader to that margin, where the label wraps in a column about a sixth of the frame wide. `n` defaults to the part's position. Parts on the same side at similar heights overprint, which is why six is the cap |
| `note` | a smaller dim line under the object's name | wraps in the sheet's width and is measured into the caption block |

**Known traps:**
- `strokes` and `parts` are one claim, so pass both or neither. They used to default separately: a film's own parts got numbered on the demo bicycle ("1 知识库" pointing at a wheel), and a film's own drawing got the demo callouts pinned to bicycle coordinates on top of it. For a drawing with no callouts, pass `parts: []`.
- A part without `x`/`y` used to sit silently at the drawing's centre, and parts past the fourth faded in at t ≥ 1, so they were never seen. Both are fixed; `x` and `y` are now required.
- The demo callouts once read 'the last mile' / 'no timetable', the copy of the beat this register was written during. The neutral demo `kicker` and `object` still print if omitted.
- Unit space is a square centred in the sheet (which is up to 1.45:1). A wide object drawn inside 0..1 leaves the sheet's spare width empty, or its spare height in portrait. Callout labels live outside the sheet, in the margins.
- `art` replaces `strokes` and still needs `parts` (or `parts: []`): the demo callouts would otherwise point at the film's drawing. An object is a designed drawing sized to its square — see references/object-authoring.md.
- An `art` object with its own `META.aspect` is fit into its square by LETTERBOXING (`ObjectSlot`'s `fitAspect`), not stretched: a wide object becomes a band across the square's middle, a tall one a band down its middle. The parts' `x,y` still map through the WHOLE square, not the letterboxed band inside it — a callout placed outside the object's own drawn band (`y` near 0 or 1 on a wide object) lands on blank sheet, not on the art.
- `art`'s own square shrinks — from the bottom, re-centred — when the plate's caption (the object's name, and a note) needs more room than a full-height square leaves below it: a two-line name and a two-line note can otherwise rise into a square that reaches the field's own bottom (16:9, 4:3). `strokes` never asked for more than the full square and is unaffected.

**Refuses:** `parts` given without `strokes`, or `strokes` without `parts`; `strokes` empty or not an array; a stroke of unknown `kind` or missing a coordinate its kind needs; `parts` not an array or more than 6; a part without numeric `x` and `y`; `art` together with `strokes`; `art` without `parts`.

**Reference:** `remotion/src/shots/TechnicalPlate.tsx`
