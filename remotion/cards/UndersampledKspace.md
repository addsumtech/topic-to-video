# UndersampledKspace

**Identity:** a framed Cartesian k-space grid of horizontal phase-encode lines, where every R-th line stays bright while the rest fade away. A counter drops from all lines to the lines actually acquired, beside an `R× undersampled` readout, under a headline and a method line.

**Use when:** the beat explains what undersampling means (skipping measurements to scan faster, then reconstructing from what is left) in an MRI or signal-acquisition film. **Not when:** the method uses variable-density, random or radial sampling, or keeps a fully sampled centre. This register draws only uniform every-R-th Cartesian lines, so it would misdraw those.

**Motion core:** the headline fades up from 40% over the first quarter. Over 0.15–0.75 the skipped lines fade from 0.6 to near-invisible while the kept lines hold, and the acquired counter counts down from the total to the kept count in step. The `scans` figure counts up over 0.20–0.85. The labels are static.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the headline at the top | a fixed 40px centred line. The demo `Reconstruct from far fewer lines` prints if omitted |
| `keep` | the acceleration R: every R-th line is kept, starting from the first | an integer from 2 to `lines`. Higher R leaves a sparser comb and a lower count, and the readout prints exactly `R× undersampled` |
| `lines` | the fully sampled line count drawn | an integer from 2 to 128. More lines give a denser comb with thinner spacing; past 128 the strokes would merge into a block. The count shown as acquired is ceil(lines ÷ R), the number actually drawn |
| `method` | the words on the method line under the headline, before the figure | leaving the demo in place prints `deep network · trained on`, a claim about a method |
| `scans` | the figure at the end of the method line | a string that is exactly one number counts up to the film's text; anything else shows verbatim; `''` draws no figure. Leaving the demo in place prints `167k scans` |
| `accent` | the kept lines, the grid frame and the `/total` | defaults to the film's DNA accent, then to its own cyan |
| `accent2` | the skipped lines and the `R× undersampled` readout | defaults to the film's second accent, then to its own violet |

**Known traps:**
- `method` and `scans` default to one film's claim, "deep network · trained on 167k scans". Omit them and that claim prints on any film. Set both, or pass `''`.
- The factor used to be the literal "~4–8× undersampled" whatever `keep` said, so `keep: 2` showed 21/42 beside "4–8×". The acquired count also used `round`, printing 8 where 9 lines were drawn. Both now come from what is drawn.
- On narrow frames the counter block moves under the grid, and the grid gives up height so the block stays out of the caption band (it once sat 128px inside the band at 1:1).
- The ink is the film's: the counter and the headline take the DNA's `fg`, the axis words and the method line take `dim`. With no DNA every original literal prints as before. Until this was done the grid, the count and the headline drew white on white on a light-ground film (measured median 1.60:1). The axis words (`k-space · phase-encode lines`, `lines acquired`, `× undersampled`) always print in English.

**Refuses:** `lines` that is not an integer from 2 to 128; `keep` that is not an integer from 2 to `lines`.

**Reference:** `remotion/src/shots/UndersampledKspace.tsx`
