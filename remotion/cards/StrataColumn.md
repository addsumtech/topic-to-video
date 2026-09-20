# StrataColumn

**Identity:** a stratigraphic column draws downward band by band beside a depth scale. Each layer is labelled at its own level, and the layer the beat is about is filled in the accent, so the viewer descends with the shot instead of being handed a finished cross-section.

**Use when:** the claim is about what lies underneath, and depth is the point: sediment, infrastructure under a street, versions under a codebase, one buried thing at the level it actually sits. **Not when:** the layers are just a sequence in time with no "under" to them (use a timeline register), or their sizes are meant to be compared as quantities (a bar register).

**Motion core:** the kicker fades in over 0.03–0.18. Bands grow downward one after another between 0.12 and 0.80, each over an equal slice with a short overlap, and its depth, leader tick and label fade in with it. In a measured column a ruler line grows down the left over 0.10–0.80 and the foot depth appears at 0.74–0.90. When layers were cut, a dashed open foot appears at 0.72–0.92. The note arrives last, at 0.82–0.96.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | small spaced caps above the column | a category line. Leaving the demo `BELOW THE SURFACE` prints it on any film |
| `layers` | the layers top (surface) to bottom: `{label, depth?, note?, find?}` | 2–3 layers give tall, calm bands and 6 give thin ones. At most six are drawn; past six the column ends in a dashed open foot meaning "continues below". `find: true` fills that band with the accent and sets its label larger and bold in the accent. A layer `note` adds a smaller dim line under its label. `depth` is copy ('3.8 m', 'street') printed at the boundary; its first number is what gets measured |
| `base` | the depth at the foot of the column | the switch between the two columns. If every drawn layer's depth holds a number, `base` does too, all intervals run the same way, and every band is still tall enough for its label, then band heights follow the depths, a continuous ruler line is drawn and `base` is printed at the foot. If any of that fails, the bands are equal, separated by dashed section-break gaps, with no ruler and no foot figure |
| `note` | a mono line under the column | a source or caveat. It fades in last |

**Known traps:**
- Band heights used to come from the array index while numerals beside them claimed to be depths. On the Utrecht film that read off the frame as a 1.9 m fill and a fort floor at 5.7 m, two figures that were in no storyboard. A true-scale column now needs a numeric depth on every layer **and** a `base`; otherwise you get the broken, not-to-scale column by design.
- Very uneven depths (0.1 m next to 30 m) fall back to equal bands, because a band squeezed under its own label would lie worse than an honest diagram.
- The depth parser takes the first number in the string: '1,200 m' reads as 1200 and '2,5 m' as 2.5, but a range like '5–6 m' reads as 5.
- Layers past the sixth are still not drawn. The dashed open foot is the only sign they exist.

**Reference:** `remotion/src/shots/StrataColumn.tsx`
