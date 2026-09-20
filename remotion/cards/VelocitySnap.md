# VelocitySnap

**Identity:** a UI assembles in a blink. Six blank panels fly in from different directions and snap into place with a micro-bounce and a motion-blur streak, the accent panel carries a big word, a small pulse ripples through the assembled layout, and a large figure fades in at the top right.

**Use when:** the claim is raw speed ("instant", "done in a blink") and one word plus, optionally, one sourced figure carries it. **Not when:** the screens' content matters — the panels are blank blocks, so they cannot show a real product (use `SurfaceCarousel` for real screens).

**Motion core:** the panels arrive staggered from 0.06 to 0.30, each over 0.14 with an overshoot, blurred in proportion to their speed. At 0.44 a short decaying pulse scales the whole assembly. The figure fades in over 0.40–0.55. After that it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the word in the accent panel | a fixed 66px heavy white word in a 500px panel, not fitted. One short word or a word and a full stop reads best. Omitting it prints `Done.` |
| `metric` | the big figure, printed exactly as written | sized to fit the width above the panels (40–120px), so a long string ("不到 1 秒") shrinks. With no `metric` there is no figure, except in the standalone preview (nothing passed at all), which shows an illustrative `0ms` |
| `unit` | the unit after the figure | printed exactly as given and never supplied for you. Omitted means no unit |

**Known traps:**
- `metric` and `unit` used to default separately, so a film passing only `label` shipped a big "0ms", and `metric: '1.2 秒'` printed "1.2 秒ms". The `0ms` now appears only when no prop at all is passed.
- `label` still defaults on its own: pass a `metric` without a `label` and the panel reads `Done.`.
- The layout is fixed pixels for a 1920×1080 frame (panels from x=130 and y=300, a top bar 1240px wide). Nothing scales to the frame, so at 1080 wide the bar runs off the right edge.
- The panel fills and borders were dark literals — this is where "a light, paper-toned film breaks it" came from — and are the film's `surface` and `surfaceBorder` now, so a paper film gets pale cards instead of five navy blocks on the page. A panel is a surface, not a dark world: it follows the film's exposure.
- The figure was drawn in a literal white, so on a warm-white film the whole value read 1.06:1 and all that was left of the metric was its unit, in the accent, beside nothing (60% of the register's marks under 3:1, `scripts/ink_contrast_qa.py`). It is the film's `fg` now; the unit stays the accent.
- The word on the accent panel is the film's `onAccent`, not white: across the eight presets white measures 1.77–3.51:1 on their own accents and `onAccent` 3.20–5.01:1 even at the deep end of the panel's gradient. That gradient's second stop was a hardcoded indigo, which overrode a themed film's hue across half the one panel that carries the word; it is derived from the film's two hues now.

**Reference:** `remotion/src/shots/VelocitySnap.tsx`
