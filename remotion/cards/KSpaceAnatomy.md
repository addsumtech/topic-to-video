# KSpaceAnatomy

**Identity:** a k-space image on the left, marked with a small centre circle and a dashed outer ring. First the centre lights up and an arrow points to a blurry, contrast-only reconstruction ("center = contrast"); then the ring lights up and an arrow points to an edges-only reconstruction ("edges = detail").

**Use when:** teaching how to read k-space, or any transformed space: the centre holds contrast and the periphery holds detail, shown with the film's own three images. **Not when:** showing only the raw k-space (KSpaceReal), the transform happening (KSpaceToImage), or undersampling (UndersampledKspace).

**Motion core:** the title fades up over the first quarter, and "one point = a wave across the whole image" over 0.06–0.3. Phase A (0.12–0.34): the centre circle, its arrow and its labels light up, and the top reconstruction goes from 25% to full opacity. Phase B (0.5–0.72): the same for the ring and the bottom reconstruction. Then the frame holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `srcK` | the k-space image, in a fixed 400px square on the left | the film's own FFT magnitude |
| `srcLow` | the top reconstruction: centre of k-space only | should be the blurry contrast image; it lights in phase A |
| `srcHigh` | the bottom reconstruction: edges of k-space only | should be the outlines-only image; it lights in phase B |
| `label` | the 40px title at the top | a short claim sits on one line. Long copy wraps |
| `credit` | a small line at the bottom-left | the CC-BY credit for the images. Empty prints nothing |
| `accent` | the centre circle, the phase-A arrow and label, the k-space border | colours the "contrast" half of the argument |
| `accent2` | the dashed ring, the phase-B arrow and label | colours the "detail" half |

**Known traps:**
- The images are optional and unchecked. A missing `src*` draws an empty bordered square while the labels still claim contrast and detail. The register does not compute the partial reconstructions; the film supplies them.
- The diagram's labels ("k-space (spatial frequencies)", "center = contrast", "edges = detail", the frequency lines) are fixed English text.
- On portrait, the side labels once ran off the edge, then onto panel two and into the caption band. When there isn't room beside the panels, the labels now drop under them and the column is sized to the content zone.
- Leaving `label` unset prints `Reading k-space`.

**Reference:** `remotion/src/shots/KSpaceAnatomy.tsx`
