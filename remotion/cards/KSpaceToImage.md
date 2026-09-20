# KSpaceToImage

**Identity:** a lattice of frequency dots, brightest at the centre, fills the frame. A glowing vertical line sweeps from left to right, and behind it the reconstructed image appears in a square frame: the film's own scan, or a structure-free glow if none is given.

**Use when:** a transform made meaningful: raw frequency data becoming a picture. **Not when:** the k-space must be the real data (this lattice is drawn, not computed; KSpaceReal shows a real one), or an image is revealed by the process that produces it (ScanReconstruct).

**Motion core:** the title fades up. Pure k-space holds until 0.1, then the sweep crosses the frame over 0.1–0.86 (easing in and out), with the image fading in just behind its front. The dots twinkle throughout. After the sweep the frame holds on the image.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the scan in the centred square (about 46% of the frame's short side) | cropped to cover the square, so a non-square scan loses its edges. Without it, the square holds a soft glow and nothing that reads as a body part |
| `label` | the 40px title, with a fixed "k-space → image" line under it | a short claim sits on one line. Long copy wraps |
| `accent` | most of the dots, the sweep's glow, the image frame and the subtitle | the dominant colour of the frequency side |
| `accent2` | every fifth dot | a sparse second colour in the lattice |

**Known traps:**
- With no `src`, the fallback used to be a drawn brain, so a knee film's k-space resolved into a head. It is now a glow. A demo render can't be told apart from a film that forgot `src`, so check that the film passes it.
- The lattice is illustrative (30×18 dots with a fixed falloff), not the scan's real k-space.
- "k-space → image" is fixed English text.
- Leaving `label` unset prints `inverse Fourier transform`.

**Reference:** `remotion/src/shots/KSpaceToImage.tsx`
