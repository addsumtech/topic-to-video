# DiffusionDenoise

**Identity:** a square of pure grain thins while the real image fades up beneath it, and eight step ticks fill underneath.

**Use when:** generative reconstruction — an image resolved out of noise (e.g. diffusion-model MRI reconstruction) — and you have that image. **Not when:** there is no real image to pass (the square ends empty), or the image is revealed by a different process (ScanReconstruct, KSpaceToImage).

**Motion core:** the title fades up over the first quarter; from 0.12 to 0.86 the grain thins and the image's opacity rises in step (linear, no easing) while the eight denoising-step ticks fill; it holds after 0.86.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the image under the noise, a path under `public/` | the whole point; without it the grain thins to an empty dark square |
| `label` | the title above | 40px, not fitted; wraps if long |
| `accent` | the square's outline, half the grain, the filled ticks and the "pinned" phrase | a hex literal, not the DNA — pass the film's accent |
| `credit` | a small line bottom-left | pass it for any CC-BY image |

**Known traps:**
- The line under the ticks is fixed English — "noise → image · denoising steps · pinned to the measured data" — and its last phrase is a data-consistency claim; it prints on every film.
- The "denoising" is a crossfade under thinning grain, and the ticks follow the same clock — they are not a real step count.
- Omitting `label` prints 'Denoise into an image'.

**Reference:** `remotion/src/shots/DiffusionDenoise.tsx`
