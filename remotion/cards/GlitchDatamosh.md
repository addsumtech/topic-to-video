# GlitchDatamosh

**Identity:** one word tears out of digital noise — red and cyan copies of it split apart, horizontal strips of it jump sideways, block flecks and scanlines flicker — then the tearing dies away to a clean word, and a glowing mono tagline comes up underneath.

**Use when:** the beat turns on noise becoming signal: a disruption, a corrupted input made clean, "cut through the noise". **Not when:** the word has to be readable from the first second (for the first half of the clip the word is mid-glitch), or the statement should stay loud all the way through (BrutalistType).

**Motion core:** the glitch starts strong and pulses in bursts, then fades to nothing across 0.55–0.9 of the clip. Strips and flecks re-roll on a stepped clock (14 steps across the clip), so the stutter jumps instead of flowing. The tagline fades up 0.7–0.9. The red and cyan copies never fully merge: a 4px fringe stays when the word is at rest.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `word` | the word, 240px heavy display type, centred | one short word is the form. Several words wrap into stacked 240px lines. A single long word is not fitted and runs past both edges of the frame |
| `tagline` | the mono caps line near the bottom, in the accent with a glow | a short phrase reads as a signal readout. Long copy wraps across the full width |
| `accent` | the cyan channel, the tagline colour, half of the flecks | changes the cool half of the split. The red channel stays fixed at `#ff004c` |

**Known traps:**
- Leaving `word` / `tagline` unset prints the demo copy `SIGNAL` / `noise, then clarity`.
- The word has no width fit (a fixed 240px), so a long word is cut off by the frame, most of all at 9:16.
- The DNA reaches only the background, and only while that background is dark (see below). The channel colours come from `accent` (default cyan) and the fixed red, so a themed film keeps cyan and red unless it passes `accent`.
- **This is a dark world (`@dark-world`).** The tear is two offset copies of the word composited with `mixBlendMode: 'screen'` — additive light, and screen over white is arithmetically nothing, so on a warm-white film the red and the cyan channel ceased to exist and the frame was blank paper with a ghost outline of the word on it (median 1.11:1, 100% of its marks under 3:1, `scripts/ink_contrast_qa.py`). It therefore takes the film's ground while the film's ground is dark — every preset, and no DNA at all — and keeps its own near-black when the film's is light. A paper-toned film gets one deliberately dark beat here rather than an empty page, and it still cannot be handed a declared `ground`.
- Because it keeps its own night on a light film, an `accent` picked to read on that film's paper will be a dark colour on this register's black. On a light film either leave the default cyan or pass an accent that reads on night.

**Reference:** `remotion/src/shots/GlitchDatamosh.tsx`
