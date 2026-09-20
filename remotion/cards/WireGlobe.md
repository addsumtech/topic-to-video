# WireGlobe

**Identity:** a wireframe globe of latitude and longitude lines spins slowly under an atmospheric halo. Six glowing nodes pop onto its surface and fade as they turn to the back, four lifted arcs draw on between them, and a bold tagline ending in an accent full stop rises beneath.

**Use when:** the beat's claim is "global" or "connected" in general (reach, integrations, a worldwide network) and the mood carries it. **Not when:** the film names specific places or connections. The nodes and arcs are fixed texture, not the film's data, so use a map register for real locations.

**Motion core:** the globe rotates steadily for the whole clip. The grid lines fade in over 0.04–0.34. Nodes pop in with an overshoot, staggered over 0.30–0.70, and dim as they rotate away. Arcs draw on, staggered over 0.42–0.84, and are skipped while both ends are behind the globe. The tagline fades in over 0.55–0.80.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `tagline` | the bold line under the globe, always followed by an accent `.` | a fixed 44px, not fitted. It is anchored from the bottom, so a long line wraps upward into the globe. A tagline that already ends in punctuation (or a Chinese line) still gets the Latin full stop. The demo `connected to everything` prints if omitted |

**Known traps:**
- The six nodes and four arcs are hand-set decoration (marked `@decor` in the code); no film item is placed on them. Do not narrate them as real cities or links.
- The line, node and arc colours are a literal cyan, and the back disc and tagline ink are literals too. Only the background follows the DNA, so on a light or warm film the globe stays cold cyan and the tagline loses contrast.
- The globe is a fixed 340px radius, centred on the frame, the same size at every aspect.
- The arcs are quadratic curves through a lifted midpoint ("great-circle-ish" in the code), not true great circles.

**Reference:** `remotion/src/shots/WireGlobe.tsx`
