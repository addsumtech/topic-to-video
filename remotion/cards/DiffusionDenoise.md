# DiffusionDenoise

**Identity:** a square of pure grain thins while the real image fades up beneath it, and eight step ticks fill underneath.

**Use when:** generative reconstruction — an image resolved out of noise (e.g. diffusion-model MRI reconstruction) — and you have that image. **Not when:** there is no real image to pass (the square ends empty), or the image is revealed by a different process (ScanReconstruct, KSpaceToImage).

**Motion core:** the title fades up over the first quarter; from 0.12 to 0.86 the grain thins and the image's opacity rises in step (linear, no easing) while the eight denoising-step ticks fill; it holds after 0.86.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the image under the noise, a path under `public/` | the whole point; without it the grain thins to an empty dark square |
| `label` | the title above | 40px, not fitted; wraps if long |
| `accent` | the square's outline, half the grain, the filled ticks and the "pinned" phrase | defaults to the film's DNA accent, then to its own cyan |
| `credit` | a small line bottom-left | pass it for any CC-BY image |

**Known traps:**
- The line under the ticks is fixed English — "noise → image · denoising steps · pinned to the measured data" — and its last phrase is a data-consistency claim; it prints on every film.
- The "denoising" is a crossfade under thinning grain, and the ticks follow the same clock — they are not a real step count.
- Omitting `label` prints 'Denoise into an image'.
- The type is the film's (`fg` for the title, `dim` for the step line and the credit, `line` for the ticks not yet taken) but the PLATE keeps its own night. It used to hold nothing but the film's ground, so on a light-ground film the register's first second — a square of pure noise, the one thing the beat exists to show — was a blank white square, and no gate could see it because by the frame they measure the noise is gone. It paints `#05060a` only when the film's ground is light; on a dark film, and with no DNA, nothing is painted and the grain keeps its polarity either way (measured median 1.18:1 before this).

**Reference:** `remotion/src/shots/DiffusionDenoise.tsx`
