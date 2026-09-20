# CartoonPop

**Identity:** a cel-shaded cartoon: a sky with drifting flat clouds, a sun and a grassy hill. A pile of paper sheets pops in, a little robot drops in stretched and then bobs, the papers poof into puffs, and a spiky starburst bursts beside the robot with a big, ink-outlined word while confetti flies and falls.

**Use when:** the beat is a playful "task cleared / done!" moment and the film wants a light, cartoon register. **Not when:** the story isn't "a helper clears a pile of work and celebrates". The picture is fixed and only the word changes.

**Motion core:** the papers pop in 0.06–0.24; the robot drops in 0.22–0.42 (stretched while entering) and bobs 0.42–0.90; the papers poof 0.50–0.62; the starburst scales in 0.60–0.78 while spinning; the word and its motion lines land 0.70–0.90; confetti bursts 0.62–1.0 under gravity. The clouds, blinking eyes and waving hand never stop.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the word on the burst | fixed 130px in a 400px box, with balanced wrapping and no fit. One short exclamation (`DONE!`) is the look; anything longer wraps into several giant lines around the burst |

**Known traps:**
- The robot, the papers and the "cleared" story are always drawn, so whatever the label says, the frame shows a helper finishing paperwork. Only `label` is the film's.
- `label` defaults to `DONE!`, a completion claim that prints on any film that omits the label.
- Latin punch leading (0.9) made two wrapped Chinese lines crash into each other. The leading rises for CJK only.
- The positions are fixed pixel offsets from the centre (papers −360, burst +260), sized for a landscape frame.
- The squash-and-stretch comment says the robot squashes at contact, but that term is multiplied by `0.0`; only the entry stretch, and a slight squash from the ease's overshoot, remain.

**Reference:** `remotion/src/shots/CartoonPop.tsx`
