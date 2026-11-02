# WordDust

**Identity:** one word comes apart into its own dust and the SAME dust settles into another word — conservation made visible: this became that. With no `from`, a loose cloud condenses into the word.

**Use when:** the beat's claim is a transformation of one thing into another with nothing added — raw data into an image, many voices into one answer, scattered facts into a conclusion. **Not when:** the two words are unrelated (a cut is honest), the second is a quantity (a number register), or the beat needs its words read for long (the dust is unreadable in flight).

**Motion core:** the first word holds solid, turns to its dust (sampled from its own pixels in the film's display face), the dust drifts on scattered paths with a soft glow and lands exactly on the second word's pixels, paired left-to-right so the flow keeps its sides; the second word settles solid, then the note fades in under it (runtime/particles, runtime/particlesDom).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `from` | the word that dissolves (omit for a cloud) | a short word (1–3 words) keeps a dense, legible dust; a long phrase thins it |
| `to` | the word the dust becomes | its dust is the first word's, so similar lengths read as "the same matter" |
| `note` | one line under the settled word | the plain-language claim; it arrives after the word settles |

**Known traps:**
- The solid words are the very canvas pictures the dust was taken from; drawing them as DOM text put them a pixel or two off their own dust.
- The canvas waits for the face (`document.fonts.load`): sampled from a fallback font, the dust lands in the wrong shape.

**Refuses:** an empty `to`.

**Reference:** `remotion/src/shots/WordDust.tsx`, `remotion/src/runtime/particles.ts`
