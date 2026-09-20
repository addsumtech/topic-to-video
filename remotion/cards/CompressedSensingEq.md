# CompressedSensingEq

**Identity:** the compressed-sensing objective is typeset as one line — min ‖Ψx‖₁ subject to ‖Fx−y‖₂ ≤ ε — and its two terms are annotated one after the other.

**Use when:** the method IS its equation and the beat should show the formula, not a metaphor (compressed sensing / sparse reconstruction). **Not when:** the audience needs the mechanism pictured rather than written (UndersampledKspace, Aliasing), or the method is not compressed sensing — the equation and its annotations are fixed.

**Motion core:** the title fades up over the first quarter; the whole equation fades in as one line (0.08–0.40); the sparse-term annotation appears above it (0.42–0.62), then the data-consistency annotation below it (0.60–0.82); then it holds — QUIET for its last fifth.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the title above the equation | 40px, not fitted; a long title wraps across the full width |
| `accent` | the Ψx term and its annotation | a hex literal, not the film's DNA — pass the film's accent or the term stays cyan |
| `accent2` | the Fx−y term and its annotation | same; default violet |

**Known traps:**
- The equation is fitted by font SIZE against the face that actually renders (read from the DNA), never by `scale()`: a scaled line overflowed its box, sat off-centre at 9:16, and the type gate measured rects nowhere near the ink.
- The annotations are fixed English (`INTRINSIC_TEXT`), so a Chinese film gets English labels here; their boxes sit at fixed fractions of the width (0.2 W and 0.5 W) with fixed pixel widths, not measured from where the terms land.
- Only the ground reads the DNA; the equation's glyph colours are literals.
- Omitting `label` prints 'Compressed sensing'.

**Reference:** `remotion/src/shots/CompressedSensingEq.tsx`
