# RisoPrint

**Identity:** a risograph wordmark on paper — two ink layers of the same word start badly misregistered, then snap into registration with a small overshoot and a residual wobble, over halftone dots and grain, with registration marks in the corners and a spaced tagline rising in below.

**Use when:** a warm, hand-printed title or closing wordmark — craft, analog, "made by people" (family G). **Not when:** the copy is long or must carry content; or the beat is sober or technical.

**Motion core:** the two ink layers pull together from a large offset to a near-registered one 0.16–0.62 (with an overshoot), the corner registration marks fading in as they do; from 0.62 to the end a slight print wobble keeps it alive. The tagline rises and fades in 0.58–0.82.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the wordmark, printed twice in the two inks | huge fixed-size heavy type, not fitted: a word or two is a poster; a longer title wraps into several huge lines; omitted, the demo `PRINT IT` prints |
| `tagline` | the spaced uppercase mono line under it | a short phrase; omitted, the demo `analog warmth, on purpose` prints |

**Known traps:**
- The blend follows the ground's measured luminance — multiply on a light ground, screen on a dark one. Branching on "is there a DNA" once gave a cream film the dark-ground blend and its closing wordmark measured 1.13:1: invisible for the last five seconds of the film.
- The inks are the DNA's two accents (pink and blue without a DNA); if the film's two accents are alike, both layers print in one colour and the misregistration stops reading.
- The layers never register exactly — a small offset remains by design; it is not a rendering fault.

**Reference:** `remotion/src/shots/RisoPrint.tsx`
