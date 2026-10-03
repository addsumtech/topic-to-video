# ObjectPath

**Identity:** one thing the film drew rides a route through named stations — across the frame when it is wide, down it when it is tall — pausing at each; its own clock is its progress along the route, so it can look different at every station. The station it is at is set in the accent.

**Use when:** the beat says "it goes through these, in this order, and becomes this": beans → grounds → puck → espresso; a signal through stages; a parcel through a network — ONE thing whose state is the story. **Not when:** the stations are only labels with nothing travelling (`InOrder`, `ConveyorBelt`); the stages are places on one object (`ObjectStage` with labels); the route is geography (`MapRoutes`, `SectionRoute`).

**Motion core:** the track draws on over 0.04–0.2 and each station's mark and name arrive as the track reaches it. From 0.22 the object dwells at each station and moves between them (eased), arriving at the last by 0.84; its own t is exactly that progress — 0 at the first station, (k−1)/(n−1) at station k, 1 at the last — so the settled frame shows it at the end, in its last state.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `object` | the thing the film drew — `{"id": …, "props": …}`; its `t` is its progress along the route | required in a film; draw its states against `t` (see `pathProgress` in the source) |
| `stations` | 2–5 names, in order | required in a film; wide: named under their marks; tall: beside them |
| `route` | `line` or `arc` | an arc rises across a wide frame and bows left down a tall one — for a route that is a journey, not a conveyor |
| `title` | one line over the route | fitted to one line |
| `kicker` | a spaced label in the title band | follows the DNA's label casing |

**Known traps:**
- The object's size is set by the spacing between stations: five stations across a square frame leave it small. Fewer stations, or `ObjectStage` for the one state that matters.
- The object is placed by its CENTRE on a tall route and by its FOOT on a wide one; an object with empty space at its foot will look like it floats.

**Refuses:** fewer than 2 or more than 5 stations; a station with no name; a `route` other than `line`/`arc`; `stations` that is not a list.

**Reference:** `remotion/src/shots/ObjectPath.tsx`

**Provenance:** motion-graphics (a beat holding an object is judged on the object's own world). **Family:** I.
