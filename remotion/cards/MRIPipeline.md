# MRIPipeline

**Identity:** four stage boxes light up left to right — a decaying signal trace, a gradient-encoding ramp, a k-space dot lattice, and the real reconstructed MR image — joined by arrows, under a one-line headline.

**Use when:** an MRI recap whose claim is the chain itself — "signal → encoding → k-space → image: always computed". **Not when:** the pipeline is any other process (the four stage names and pictures are fixed; use a general flow register), or the film has no reconstructed image to show at the end.

**Motion core:** the headline brightens from 40% to full over the first quarter; stage i fades up over 0.1 + 0.14·i to 0.35 + 0.14·i (the image stage over 0.52–0.77), the signal's amplitude growing with its stage and each arrow appearing with the stage it points to; after ~0.77 the frame holds still.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the reconstructed image in the last box (a path under `public/`) | a real MR slice cropped to fill the box; without it the last box is an empty outline labelled "image" |
| `label` | the headline across the top | a fixed 40px centred line; long text wraps across the full width |
| `accent` | box outlines, the gradient lines, the arrows and most k-space dots | the pipeline's colour; must be a 6-digit hex (see traps) |
| `accent2` | every fourth k-space dot | a second tint in the lattice; close to `accent` it disappears |

**Known traps:**
- The stage names (`signal`, `encoding`, `k-space`, `image`) and their pictures are fixed English furniture; no prop changes them.
- The payoff only exists with `src` — the header's "culminating in the REAL reconstructed MRI" holds only when the film passes an image.
- The unlit box strokes append an alpha byte to `accent` (`${accent}66`), so a named, rgb() or 3-digit colour gives those outlines an invalid stroke.
- The headline, all four stage names and the three arrows were literals picked for a near-black ground, so on a warm-white film 33.0% of this register's marks measured under 3:1 with a connected hole 0.52% of the frame: four boxes on paper with no names under them and nothing joining them. The median stayed at 16.67:1 only because the boxes themselves are most of the ink and never moved. An arrow is the "→" in "signal → encoding → k-space → image", so it is a claim as much as a word is; all of it reads from the DNA now (`fg` for the headline and the stage names, `accent` for the arrows).
- The four BOXES are not ink and do not follow the ground: they hold a signal trace, a gradient encode, a k-space lattice and a real MR slice, so they keep their own night, the trace inside box one keeps its literal, and the gradient lines and k-space dots are lifted to read against that night rather than against paper. On a light film the register is four dark boxes on paper by design.
- Omitting `label` prints "Always computed".

**Reference:** `remotion/src/shots/MRIPipeline.tsx`
