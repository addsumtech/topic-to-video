# WordTunnel

**Identity:** the beat's phrases stand at their own depths down a dark corridor, alternating sides, and the camera travels it. Each phrase grows out of the far dark, sweeps outward past the lens and is gone, until the last phrase, centred and in the accent, grows into a held block. Speed lines stretch from the vanishing point.

**Use when:** the beat's points arrive one after another with weight and their **order** is the argument ("first… then… finally…"), where a list would flatten them into peers. **Not when:** the points must be read together or compared (a list or table register), or there are more than six (it refuses).

**Motion core:** the camera travels over 0–0.94 (easeInOutCubic) and stops with the last phrase held in front of the lens at about 1.4×. A phrase fades in as it becomes readable. Passing phrases are dropped the moment they would cross the frame edge or the caption band, rather than being clipped. A nearer phrase hides any farther one its box overlaps. The tail line fades in over 0.74–0.82, once every passing phrase is behind the lens, so it is on the settled frame (0.86).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `phrases` | the points in order, 1–6 | the passing ones are single lines, fitted to 82% of the width and then scaled by nearness, so short phrases fly big. The last phrase may wrap into a block fitted to 86% of the width and about half the content zone, so it can carry a longer sentence. More phrases means each passes faster. Leaving the demo in place prints `First` / `Then` / `And then` / `Finally` |
| `tail` | a closing line near the bottom of the content zone | appears only once the corridor is behind (from 0.74), fitted to one line. Empty draws nothing |

**Known traps:**
- There are six hand-set lanes. Past six phrases the rest used to be dropped with no error, and empty phrases were silently filtered out; both now refuse.
- The tail used to start at t > 0.86 — the exact t reduced motion freezes at and the settled frame every gate reads — so on that frame, and under reduced motion always, the film's closing line was never drawn. It now arrives from 0.74.
- The final phrase once stood on a side lane, swept out just as it should have landed, and left the last fifth of the shot on an empty frame. It is now centred and held.
- Fitted to the bare frame and then magnified, the held phrase came out 40% too wide. At 1:1 in Chinese it was culled and the shot ended on an empty frame, which no type gate saw, because type that is never drawn is never cut off. Only `cjk_type_qa --aspect=1:1` caught it. Check the ending at every aspect.
- Type is drawn flat, not on the z plane (glyph edge strength measured 91 flat vs 56 under `translateZ`). Only the speed lines may ride z.
- The camera must drive z down the corridor. With the sign reversed it backs out and every phrase shrinks into one clump in the middle.

**Refuses:** no `phrases`, more than six, or an empty phrase.

**Reference:** `remotion/src/shots/WordTunnel.tsx`
