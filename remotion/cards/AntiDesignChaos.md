# AntiDesignChaos

**Identity:** a deliberately "wrong" maximalist collage. Sticker shapes and hand-drawn scribble arrows scatter across a loud flat ground, the item words pop in askew in mismatched fonts and colours, then a huge tilted, outlined headline bounces into the centre and a tag chip lands bottom-left.

**Use when:** the beat is rebellion, rule-breaking, noise, or "loud on purpose", and the words are short exclamations. **Not when:** the items have to be read, compared or ordered: the placement is hashed, words overlap each other and the headline, and nothing is a list.

**Motion core:** nine stickers pop in from 0.10 + i·0.05 (each over 0.24); four arrows draw from 0.30 + i·0.08 (each over 0.30); the words pop, rotating as they land, from 0.16 + i·0.07 (each over 0.24); the headline scales in with an overshoot 0.30–0.56; the tag fades in 0.70–0.90. Placement comes from a hash, not a random seed, so it's deterministic.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the loud tilted headline | fitted to 90% of the width and to the content zone (the −6° tilt counts toward the fit), up to 300px, with balanced wrapping; short shouts hit the cap, and sentences shrink and stack |
| `items` | the scattered words | each gets a hashed size (roughly 60–150px), shrunk to fit the frame and clamped horizontally so the whole word lands. A few words look sparse and several look properly chaotic; fonts cycle through five families |
| `tagline` | the reversed-out mono chip, bottom-left | fixed 34px with tracking and no fit; long copy wraps inside the chip |

**Known traps:**
- Omitting props prints the demo copy: `RULES?`, `no grid`, `more!`, `why not`, `LOUD`, `oops`, `yes.`, `break it on purpose`.
- The words enter 0.07 apart. From the 10th on they're still settling on the last frame, and a 13th starts after the clip ends, so it never appears.
- Word sizes used to come straight from the hash, with `nowrap`, and a long Chinese word ran 801px off the right edge at 1:1. Words are now fitted and clamped, and their box stops above the caption band.
- A flat 300px Chinese headline once drew 280px inside the caption band. The title is fitted to the zone with the tilt included and balanced, so a single glyph never strands on its own line.
- The stickers and arrows are hashed over the whole frame, with no caption-band reserve, so they can sit under the subtitle.

**Reference:** `remotion/src/shots/AntiDesignChaos.tsx`
