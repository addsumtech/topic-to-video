# ScanReconstruct

**Identity:** a real image in a square plate is uncovered from the centre outward — a grid of dark tiles clears as a faint accent ring expands across it — until the whole picture is showing.

**Use when:** a real image (a scan, a photograph) should arrive as something assembled or computed rather than simply shown — "and this is what comes out". **Not when:** the claim is how reconstruction actually works in frequency space (use `KSpaceToImage` or `KSpaceReal`); or there is no real image (it refuses).

**Motion core:** the label eases up from faint over the first quarter; the reveal front travels from the centre to the corners 0.06–0.90, tiles clearing as it passes and a thin ring marking the front. The finished image holds to the end.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the real image, a path in the film's public dir | required; shown square in the content zone, cropped to fill (cover) |
| `label` | a line at the top of the frame | empty draws nothing; fixed-size light type, wraps when long |
| `credit` | a small licence line at the bottom left (for CC-BY images) | empty draws nothing |
| `accent` | the plate's hairline ring and the reveal-front ring | plumbing — the DNA accent does not replace it |
| `cols` | the grid's resolution (tiles per side; the grid is square) | default 22: fewer gives chunky blocks and a stepped front, more gives a smooth circular wipe. Not validated — 0 or less draws no tiles, so the image shows whole from frame one |

**Known traps:**
- The reveal is SPATIAL: the middle of the picture appears first. That is not what "low frequencies first" looks like (the k-space centre carries the coarse content of the WHOLE image), so don't narrate the reveal as a frequency reconstruction.
- The label, credit and tile colours are fixed dark-theme literals; on a light-ground DNA the label loses its contrast and the unrevealed plate is a black square on a light page.
- A non-square image loses its edges to the square crop.

**Refuses:** a missing or empty `src` (the error says how to fetch a licence-clean image with `scripts/imagefetch.py`).

**Reference:** `remotion/src/shots/ScanReconstruct.tsx`
