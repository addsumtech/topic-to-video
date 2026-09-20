# KSpaceReal

**Identity:** one square holding the real k-space magnitude image (desaturated, with a soft accent glow) fades in on kx/ky axes. Small labels then mark the bright centre as low frequency and the periphery as detail, with "the image's spatial frequencies — not the image" underneath.

**Use when:** the film has the real transform of its real data and wants it seen for what it is. **Not when:** there is no k-space image (the square stays empty), the beat reads centre against edges with reconstructions (KSpaceAnatomy), or it shows the transform happening (KSpaceToImage).

**Motion core:** the square and axes fade in over 0.08–0.5. "center = low freq" comes in over 0.4–0.6, the periphery label over 0.5–0.7, and the bottom line over 0.55–0.75. Nothing moves after that: a quiet register.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the k-space magnitude image in the square | shown as given: desaturated and screen-blended, so any colour in it is discarded |
| `label` | the 40px title at the top | a short claim sits on one line. Long copy wraps |
| `credit` | a small line at the bottom-left | the CC-BY credit. Empty prints nothing |
| `accent` | the square's border, the glow and the axes | tints the frame around the data, not the data |

**Known traps:**
- `src` must already be the FFT magnitude; the register computes nothing. Pass the anatomy image and it will be labelled "not the image" anyway.
- A missing `src` draws an empty square with a glow, and no error.
- The axis and annotation labels (kx, ky, "center = low freq", "periphery = high freq · detail", the bottom line) are fixed English text.
- When the square was centred on the frame, its own bottom line landed in the caption band. It is now centred in the content zone, at most 42% of the width.
- The type is the film's (`fg` for the title and the centre label, `dim` for the axis names, the two annotation lines and the credit) but the SQUARE keeps its own night: `src` is screen-blended, and screen over paper is paper, so on a light-ground film the k-space would be a blank square with every label around it still perfectly legible. It paints `#05060a` only when the film's ground is light — on a dark film, and with no DNA, the film's ground shows through as before. The kx/ky axes cross the square, so they are lifted to read on that night rather than on the paper (measured median 1.12:1 before this).

**Reference:** `remotion/src/shots/KSpaceReal.tsx`
