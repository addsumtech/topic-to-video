# FlightArcs

**Identity:** the film's places on the Earth and great-circle routes between them: each arc lifts off the globe over a dashed ground track, draws from its origin with a bright head travelling it, and lands with a ring at its destination; once landed, a marker keeps flying every route one way, origin to destination.

**Use when:** the claim is that these places are connected and how far apart they really are — a great circle is the shortest path on the sphere, so its length and poleward bulge are the geometry (London to Tokyo crosses Siberia). **Not when:** the connections have no geography (`MapRoutes`, `KnowledgeGraph`), or there is one place (`GlobeFocus`).

**Motion core:** the Earth fades in over 0–0.12; routes draw one after another between 0.14 and 0.70, overlapping, each easing in and out with a glowing tail; a place's dot pops and rings when the first route touching it leaves or arrives, and its label follows; after a route lands, a marker loops along it with a period of 3 s plus a second per 60° of arc.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | one line in the title band | rises through its mask; empty draws nothing |
| `places` | 2–10 places: `label`, sourced `lon`/`lat`, optional `id` | every endpoint and every route's midpoint is fitted into view; labels are placed clear of each other and of every dot |
| `routes` | 1–8 routes `{from, to}`, naming places by `id` or `label` | a long route lifts higher than a short one; routes sharing a place make a hub |
| `view` | `globe`, `flat`, or `auto` (default) | `auto` is the globe when one hemisphere holds every place and route midpoint, else flat Equal Earth centred on the places' circular-mean meridian |
| `note` | a mono line under the map | a source or reading note |

**Known traps:**
- The arc's height is drawn for legibility (4% of the globe radius plus 16% per 180° of arc); it is not an altitude.
- A forced `globe` view refuses places spanning more than 80° from their centre; `auto` switches to flat at 70°.
- On the flat view a route that still crosses the map's own edge (a set spread right round the world) is cut there by d3 rather than drawn across the whole map; recentring on the mean meridian keeps ordinary trans-Pacific routes whole.
- The flat view fits the ROUTES, so two close cities give a regional map; the coastline switches to 1:50m when the map is drawn larger than the frame.
- The demo's three places are labelled only "origin / stop / destination".

**Refuses:** `places` without `routes` or the reverse (either alone would be drawn against the demo's other half); fewer than 2 or more than 10 places; no routes or more than 8; a place without a label or valid coordinates; a route naming a place that was not given, starting and ending at one place, of no length, or between antipodes (no single great circle joins them); labels that cannot all be placed without overlapping.

**Reference:** `remotion/src/shots/FlightArcs.tsx`
