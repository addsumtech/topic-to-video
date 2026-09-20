# RealVersus

**Identity:** two real photographs as square plates wipe in from opposite sides — side by side in landscape, stacked in portrait — each with its label under it, and a round `vs` chip lands between them.

**Use when:** the comparison is carried by REAL images — two scans with different contrast, the same result from two methods, a real before and after — and the pictures themselves are the evidence. **Not when:** the two sides are drawn concepts or text (use `VersusSplit`), one image changes into the other over time (use `BeforeAfterSlider`), or there is only one picture (use `PhotoPlate`).

**Motion core:** the title eases up from faint over the first quarter of the clip; the left (top) plate wipes in 0.10–0.50, the right (bottom) plate 0.22–0.62, each sliding in from its own side with its label; the `vs` chip fades in 0.50–0.62. After that the frame holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `srcLeft` | the left (or top) image, a path in the film's public dir | required; shown square, cropped to fill (cover), so a wide or tall image loses its edges |
| `srcRight` | the right (or bottom) image | required, like `srcLeft`; shown square, cropped to fill |
| `labelLeft` | the caption under the left plate | primary-ink bold; a short term reads as the name of one side. Longer labels wrap, and the reserve for them is counted by breaking — every extra line shrinks BOTH plates |
| `labelRight` | the caption under the right plate | as `labelLeft`; the longer of the two sets the reserve |
| `title` | the spaced mono caps line at the top stating the comparison | empty draws nothing; padded to the frame margin and wraps when long |
| `credit` | a small licence line at the bottom (for CC-BY images) | empty draws nothing |
| `accent` | the plates' ring and the chip's border | plumbing; an explicit value wins over the DNA accent |

**Known traps:**
- It used to keep its dark-theme inks on any DNA: on a cream film the title measured 1.20:1 and the labels 1.29:1 against the ground. Every ink now comes from the DNA; don't reintroduce literals.
- Labels that wrap (CJK, or narrow 4:5 panels) used to push the last line into the caption band — once when the reserve assumed one line, again when it was capped at three. It is now settled to a fixed point; long labels cost plate size.
- The deep black drop shadow read as grime on a light ground; the shadow is chosen by the ground's measured luminance.

**Refuses:** a missing or empty `srcLeft` or `srcRight` (the error says how to fetch a licence-clean image with `scripts/imagefetch.py`). `srcRight` used to be unchecked and drew an empty framed plate opposite the photograph.

**Reference:** `remotion/src/shots/RealVersus.tsx`
