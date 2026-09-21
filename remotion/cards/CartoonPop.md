# CartoonPop

**Identity:** a cel-shaded cartoon: a sky with drifting flat clouds, a sun and a grassy hill. A pile of paper sheets pops in, a little robot drops in stretched and then bobs, the papers poof into puffs, and a spiky starburst bursts beside the robot with a big, ink-outlined word while confetti flies and falls.

**Use when:** the beat is a playful "task cleared / done!" moment and the film wants a light, cartoon register. **Not when:** the story isn't "a helper clears a pile of work and celebrates". The picture is fixed and only the word changes.

**Motion core:** the papers pop in 0.06–0.24; the robot drops in 0.22–0.42 (stretched while entering) and bobs 0.42–0.90; the papers poof 0.50–0.62; the starburst scales in 0.60–0.78 while spinning; the word and its motion lines land 0.70–0.90; confetti bursts 0.62–1.0 under gravity. The clouds, blinking eyes and waving hand never stop.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the word on the burst | fixed 130px in a 400px box, with balanced wrapping and no fit. One short exclamation (`DONE!`) is the look; anything longer wraps into several giant lines around the burst |

**Known traps:**
- A daylight cartoon cannot be drawn with a night palette. The cloud and the paper sheets were `mix(dna.fg, dna.bg, k)` — "mostly ink, a little ground", which is white on all eight (dark) presets and BLACK on a film grounded on paper. It is high-contrast, so no ink gate reports it; it was found by reading the register. Both now take the film's PALE end (`runtime/light.paleEnd`), and on a light film the sky takes a wash of the accent so there is room above it for a white cloud to sit.
- The clouds are outlined like every other shape here. Drawn bare on a pale sky they were the one shape a reader had to find rather than see; the outline is a silhouette UNDER the fills, because stroking three overlapping ellipses puts arcs through the cloud's middle.
- The robot, the papers and the "cleared" story are always drawn, so whatever the label says, the frame shows a helper finishing paperwork. Only `label` is the film's.
- `label` defaults to `DONE!`, a completion claim that prints on any film that omits the label.
- Latin punch leading (0.9) made two wrapped Chinese lines crash into each other. The leading rises for CJK only.
- The positions are fixed pixel offsets from the centre (papers −360, burst +260), sized for a landscape frame.
- The squash-and-stretch comment says the robot squashes at contact, but that term is multiplied by `0.0`; only the entry stretch, and a slight squash from the ease's overshoot, remain.
- The robot's face plate was `shade(BODY, 0.72)` — a dark screen, which is right only while the outline has inverted to a light one. On a light film the ink stays dark, so the eyes and the smile were drawn at the screen's own value: 11.1% of the register's ink under 3:1 on a warm-white ground, largest region 0.47% of the frame, and that region was the face. The plate takes whichever side of `BODY` the outline is not now. The starburst's inner highlight is untouched — its spike tips overhang the burst onto the paper and measure low there, but it is a 0.6-opacity gloss on a shape whose fourteen dark spikes carry it.
- The sky furniture is still derived from `fg` on the assumption that `fg` is the light end — clouds `mix(fg, bg, 0.16)`, the task sheets `mix(fg, bg, 0.12)`, the sun in the third palette tone — so on a light film the clouds and the sheets come out dark. They read (high contrast against the paper) and the sheets are gone by the settled frame, so the ink sweep does not report them; it is a daylight cartoon drawn with a night palette, not an invisible one.

**Reference:** `remotion/src/shots/CartoonPop.tsx`
