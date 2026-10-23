# TypeOnPath

**Identity:** the beat's words travel a line that is the subject's own shape — a ring that keeps turning for a cycle, a wave for a signal, a climb for growth, a figure-of-eight for a loop that feeds itself, or the film's own route — each letter turned to the direction of travel, coming to rest on it. The path draws itself on first; a title rises through its mask where the path leaves room (inside the ring).

**Use when:** the SHAPE is the claim: hide the caption and the path alone should say "this repeats", "this oscillates", "this rises" or "this is the route". **Not when:** the content is steps in order (a process register), or one static claim (`HeadlineReveal`). Never pick a shape for looks — a wave under a sentence about growth argues the wrong thing.

**Motion core:** each glyph's centre is placed by ARC LENGTH along the path at its own advance from the phrase's start (so the phrase keeps its kerning where the path bends), rotated to the tangent, lifted slightly off the line. On an open path the phrase travels in (2.2 s, power3.out) and rests centred; on the ring it is repeated round the whole circumference, evenly spaced, and turns once every ~24 s; on the loop it travels on for the whole beat. Glyphs blur in as they enter.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `phrase` | the words that travel the path | fitted to the PATH's length, not the frame's width; on a ring or loop it is texture (`read={false}`), on an open path it is held to its reading time |
| `path` | the subject's shape: `orbit`, `wave`, `rise`, `loop` | orbit = a cycle, wave = a signal, rise = growth, loop = feedback |
| `d` | or the film's own path: absolute commands (M L C Q) in a 0–1000 square, scaled into the frame | for a real route or a measured curve; arcs and relative commands are refused |
| `title` | the one line that must be read | inside the ring, or above the path |
| `kicker` | a small spaced label | not held to a reading time |

**Known traps:**
- The path is walked by the SVG engine itself, never by `@remotion/paths`: measured on this 1710px climb, its `getPointAtLength` went backwards 45 times in 2048 steps (up to 2.3 px) — letters spaced unevenly, one drawn upside down under the line — and its `getTangentAtLength` is reversed on arc commands, which ran the ring backwards, upside down across its top.
- A wave is one wavelength on a narrow frame and one and a half on a wide one, so the steepest tilt a letter takes stays readable.
- The title's room is RESERVED rather than measured: the path sits below it and the phrase is fitted to the path's length, and a path that waited on the title's measured height re-specced the phrase after the first measurement.
- QUIET by construction: measured 0.0024 motion, 7.1% ink (product DNA, the wave) against 0.0037 / 12%. Intercut with a dense register.

**Refuses:** an empty `phrase`; a `path` that is not one of the four; a `d` that is not absolute M/L/C/Q.

**Reference:** `remotion/src/shots/TypeOnPath.tsx`

**Measured:** 7.1% ink (clip median) · 41% footprint · 0.0024 motion · reach 0.767. Holds: clean at its own 6 s.

**Review:** NOT critic-reviewed — built and looked at by its author: wave (16:9 Latin; 9:16 Chinese; product, editorial and terminal DNA), orbit (9:16 and 1:1 Chinese), rise (16:9 Latin), loop (9:16 Chinese).

**Provenance:** motion-graphics. **Family:** P.
