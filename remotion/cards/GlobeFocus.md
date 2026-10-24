# GlobeFocus

**Identity:** an orthographic Earth — Natural Earth land and borders, a hairline graticule, an atmosphere rim, a light from the upper left — turns the short way round to the place the film names, pushes in until that place fills the frame, lights it in the accent, and lands the film's own points on it with labels that never collide.

**Use when:** the claim is WHERE, at the scale that makes it legible: a country, a coast, two cities in one corridor — and the viewer should watch the position rather than be told it. **Not when:** the claim is a route between places (`FlightArcs`), the places have no geography between them (a list register), or the map is an engraved or imagined plate (`MapPlate`).

**Motion core:** the planet fades in already turning (0–0.10); the turn eases over 0.02–0.50 (longitude the short way round); the push-in starts at 0.20 and ends at 0.60, the radius moving exponentially so the zoom reads at one rate; the regions light over 0.48–0.64; marks pop from 0.58 and their labels from 0.62, 0.04 apart; the note rises at 0.66; then a slow ring breathes round each mark (3.2 s period).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | one line in the title band | rises through its mask with the planet; empty draws nothing |
| `regions` | 1–6 regions to light: `name` (Natural Earth's, or an ISO 3166-1 numeric code) and the `label` the frame prints | one region frames on its main body; several frame on all their main bodies. A region big enough on screen carries its label inside itself, on its own land; a small one is labelled beside it with a leader |
| `marks` | 0–6 points: `label`, `lon`, `lat` — the film's sourced coordinates | each gets a dot, a breathing ring and a chip placed clear of every other chip and dot |
| `from` | where the turn starts (`lon`, `lat`) | staging only; default a quarter-turn west of the aim, so the planet visibly travels |
| `zoom` | the share of the content zone the settled view gives what is named, 0.3–0.9 (default 0.62) | lower keeps more of the globe's limb in frame; higher fills the frame with the region |
| `note` | a mono line under the globe | a source or reading note |

**Known traps:**
- Region names are Natural Earth's own spellings ("United States of America", "Dem. Rep. Congo" at 1:110m but full names at 1:50m — lookups use the 1:50m names). An unknown name throws with the nearest names the atlas has.
- Natural Earth draws de facto boundaries. A film naming a disputed region should say in its note whose boundary is shown.
- An overseas part (French Guiana for France, the Canaries for Spain) is LIT but not framed: framing follows each region's main body and parts of at least 5% of its area within 30° of it.
- The coastline is 1:110m when the settled globe fits the frame and 1:50m when it is pushed in past ~0.9 of the frame's short side; at very small countries 1:50m is still coarse.
- With no `regions` and no `marks` the demo lights one region labelled "the region the film names" — a film must pass its own; a film that passes only `marks` lights no region.

**Refuses:** more than 6 regions or 6 marks; neither regions nor marks; a mark without a label or with coordinates missing or out of range; `zoom` outside 0.3–0.9; a set of places spanning more than 80° of arc from their centre (one side of a globe cannot show them — use `FlightArcs` with `view: "flat"`); labels that cannot all be placed without overlapping.

**Reference:** `remotion/src/shots/GlobeFocus.tsx`
