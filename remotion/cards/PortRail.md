# PortRail

**Identity:** real WebGL — one machined rail under product lighting, and modules that travel down their own axis one at a time and SEAT onto it with a spring, a visible pin crossing the closing gap; each module's name appears as it lands, and the camera keeps pushing in slowly across the whole shot.

**Use when:** several things fit ONE standard and nothing is configured — interoperability, connectors, integrations said as a physical fit. With `groups`, "these come in N kinds" is carried by spacing and a name under each cluster. **Not when:** the parts combine into one whole (use `MaterialHero`), the claim is about relations between them (a graph register), or they are product surfaces (use `PlatformSurfaces`).

**Motion core:** the title fades in 0.02–0.16; module *i* starts seating at 0.08 + 0.52·*i*/*n* on a spring (mass, not a fixed overshoot), so the row fills left to right (top to bottom when stood up); a label fades in only once its module is most of the way home; group names fade in 0.50–0.70 and the note 0.66–0.84. Throughout, a slow push-in and a faint yaw breath keep the frame alive after the last module seats.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `standard` | the name of the rail, set large under it | width-fitted: a short name stays big, a long one comes down in size; omitted, the demo `One standard` prints |
| `items` | one module per entry | 1–6, the rail is laid out per count and every label shares ONE size fitted to the measured spacing between modules, so more modules means smaller type. Omitted, six demo app names print |
| `groups` | named kinds, each `{label, items[]}` — replaces `items` when given | the modules are spaced with a wider gap wherever the kind changes, and each group's label sits under its own cluster in dim mono; all modules keep the same mark. The six-module cap applies to the flattened run, and every group needs at least one item |
| `note` | a dim line under the title | fades in late as a qualifier; long copy wraps; empty draws nothing |

**Known traps:**
- In portrait or square frames (width/height under 1.25) the rail stands up: modules seat from the side, labels sit beside them, and the list reads top to bottom. A horizontal row there ran modules off both edges.
- On the standing rail (frames narrower than 5:4) the group gaps come out of the same 2.6-unit rail, so six grouped modules sit flush against their group neighbours and read as blocks of two or three; the labels still separate.
- Colour does not carry grouping: three attempts to key groups by tone each failed on the delivered frame (too alike, or invisible on the module face). Every module wears the same tone bar; don't reintroduce per-group colours or a swatch legend.
- The type is DOM placed by projection, not texture in the scene — CJK on a texture is mush and dims with the lighting. Labels are clamped to the content zone, and the title block is measured before the camera is fitted so it can't print across the rail.
- A still of the final frame is not a check: an earlier lift left waiting modules cut by the top edge for the first third of the shot while the last frame looked perfect.

**Refuses:** more than six modules (flattened across groups — a seventh touches its neighbours on the standing rail); an empty `items` entry or group member; a group with no items; `groups` given but empty (it used to fall back to `items`, demo names included); no modules at all.

**Reference:** `remotion/src/shots/PortRail.tsx`
