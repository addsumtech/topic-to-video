# VariableTypeMorph

**Identity:** one enormous word comes alive on its type axes. Letters rise in one by one with an overshoot, then a wave of weight (thin to black) keeps travelling across them while each glyph breathes wider and narrower, over a blurred two-colour field drifting sideways, between a spaced kicker and tagline.

**Use when:** the beat is one word that should feel expressive or alive, such as a brand value, a mood word or a section opener, and typography is the whole design. **Not when:** the content is a phrase or a sentence (it is built for one word), or the word needs explaining.

**Motion core:** the kicker rises in over 0.04–0.20. Letters enter staggered across 0.12–0.52, each over 0.3 with an overshoot, rising and filling out from condensed. The weight wave and the width breath run continuously after entry, and the colour field drifts across the frame for the whole clip. The tagline arrives over 0.62–0.84. It never settles.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `word` | the one enormous word, one glyph box per character | the size (at most 210px) is fitted so the word still fits at the widest moment of its breath (1.12×), so a long word comes out smaller. Letters shade from `accent` to `accent2` across the word. The row cannot wrap. The demo `EXPRESSIVE` prints if omitted |
| `kicker` | the small, widely spaced mono caps above | the demo `type, alive` prints if omitted |
| `tagline` | the spaced mono caps below | the demo `weight · width · in motion` prints if omitted |
| `accent` | the first letter's colour and one half of the field | a prop with a fixed pink default, not the DNA's accent |
| `accent2` | the last letter's colour and the other half of the field | a prop with a fixed blue default |

**Known traps:**
- It used to be a fixed 210px. Under the editorial DNA's serif on a 1080-wide frame, `EXPRESSIVE` was sliced in half at both edges, and the type gate never saw it because it sweeps only one DNA. The fit now accounts for the face and for the breath.
- One word only. Each character is its own inline-block, so a space becomes an empty box and collapses, and a phrase's words would run together.
- The weight wave is real only if the DNA's display face has the weights (a variable font makes it smooth). The width breath is a `scaleX` stretch whatever the face.
- Only the background follows the DNA. The accents are fixed unless passed, and the kicker and tagline inks are light literals, so a light DNA loses them.

**Reference:** `remotion/src/shots/VariableTypeMorph.tsx`
