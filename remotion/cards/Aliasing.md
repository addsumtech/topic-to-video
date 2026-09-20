# Aliasing

**Identity:** a square scan plate, with two copies of the same image shifted by half a frame, screen-blended over it as ghosts that strengthen while a dashed fold line crosses its middle; a `ghost:` annotation and a Nyquist note explain the wrap-around.

**Use when:** the beat is the MRI aliasing (wrap-around) artifact itself: undersampling k-space folds a shifted copy of the anatomy back onto the image. **Not when:** the beat is about general corruption or glitch, or about k-space in the abstract (the k-space registers draw that).

**Motion core:** the headline fades from 0.4 to full opacity over the first quarter; the Nyquist note fades in 0.1–0.4; the ghost copies, fold line and annotation grow together 0.2–0.7 (the copies reach 0.6 opacity). Then it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the headline above the plate | a fixed 40px line, centred; short copy sits on one line, and long copy wraps downward toward the plate (it isn't fitted) |
| `src` | the scan image (a path in `public/`) | given: the real scan folds onto itself. Omitted: a drawn, deliberately asymmetric phantom labelled `synthetic phantom` on the plate |
| `accent` | the plate's border, the fold line and the phantom's ink | defaults to cyan, independent of the DNA accent |
| `credit` | a small attribution line, bottom-left | for CC-BY scans; `''` draws nothing |

**Known traps:**
- The annotation words (`ghost:`, `a wrapped copy folds in`, `undersample → Nyquist violated → wrap-around`, `synthetic phantom`) belong to the form and are declared in `INTRINSIC_TEXT`. They print in English on every film, and no prop can reword them.
- Without `src` the picture is drawn, not scanned. The `synthetic phantom` tag is there so the drawing never passes for evidence, so keep it that way. An earlier symmetric phantom read as a cartoon face, and a symmetric one also hides the ghost.
- When there's too little room beside the plate (portrait) the annotation moves under the plate. The square is measured twice so that the note's reserve matches the branch that's used. At 4:5 a single fit once put the Nyquist note in the caption band.
- The headline, annotation and note colours are fixed light tints, while the ground follows the DNA. A light DNA ground would wash them out.

**Reference:** `remotion/src/shots/Aliasing.tsx`
