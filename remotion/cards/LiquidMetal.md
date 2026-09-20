# LiquidMetal

**Identity:** eight chrome blobs drift in from a wide ring and merge (SVG goo) into one molten-mercury mass at centre, then a chrome wordmark and a spaced-caps tagline rise over it.

**Use when:** a title or brand beat whose whole claim is one name plus a short line, and the feel should be "fluid, premium, alive". **Not when:** the beat has parts, steps or numbers to show — it carries only a word and a line; for one thing taking several named shapes use LiquidMorph.

**Motion core:** the blobs orbit and pulse for the whole clip (never still); they gather from a wide spread to a tight cluster over 0.16–0.55; the title fades up and rises 14px over 0.5–0.74, the tagline fades in over 0.62–0.84.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the chrome wordmark over the metal | one short word reads as a stamped metal logotype; it is a fixed 150px with no fit-to-width, so a phrase wraps into several huge lines over the blob and one long unbroken word runs off the frame |
| `tagline` | the line under the wordmark | always set in uppercase mono with wide tracking in the DNA's dim colour; a few words sit as a quiet caption, a sentence becomes a long spaced strip |

**Known traps:**
- Omitting `title` / `tagline` prints the demo copy `Molten` / `chrome, but alive` on the film.
- The wordmark is never shrunk to fit — keep it to a word or two.
- The metal's silver reflection gradient ignores the DNA on purpose (the header's LEVEL-C note: "chrome IS chrome"); only the ground and the tagline colour follow the film, so it will not take the film's accent.

**Reference:** `remotion/src/shots/LiquidMetal.tsx`
