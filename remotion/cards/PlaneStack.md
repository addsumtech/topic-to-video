# PlaneStack

**Identity:** the layers a system is made of, drawn as slabs in space seen from slightly above: each plane carries its own name, a gloss and the things that sit on it, and the layer the beat is about lifts out of the stack, sharpens and takes the accent while the rest recede — softer, dimmer and greyer, which is what distance does.

**Use when:** the claim is what a thing is MADE OF, layer by layer, and one of the layers is what this beat is about — interface over service over store, road over pipes over soil, coil over gradient over reconstruction. **Not when:** the layers are a sequence in time (use a timeline register), the claim is about how DEEP something is buried (`StrataColumn` draws a measured section), the layers carry quantities (`PhysicsStack`), or they are peers rather than a stack (`CardStack3D`, `BentoReveal`).

**Motion core:** each plane drops into place in order, top to bottom, staggered over 0.08–0.34 with the step compressed for the count so the last one is settled by t=0.84. When the film names a `focal` layer it lifts out of the stack and the others recede over 0.52–0.70 — the recede runs through `runtime/focus` with both its anchors (blur and desaturation), because without the saturation half layered material reads as stickers flying rather than as depth. With no `focal`, nothing moves after the stack lands and nothing is blurred.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the line above the stack | a few words naming the system; empty draws nothing |
| `layers` | the stack itself, top to bottom: `label`, optional `note`, optional `items` | 2–5. The ORDER is the film's. Every layer is set at ONE size, fitted to the longest label, so no layer reads as ranked above another. A `note` wraps to at most two lines on its plane; `items` are chips across it (0–4) |
| `focal` | which layer this beat is about | an index, or absent for none — and absent is a real answer: the stack is drawn flat-lit with every layer equal. Naming one lifts it, rings it in the accent and pushes the others out of focus. Past the last index it refuses rather than picking by position |
| `note` | one dim line under the stack | its room is taken out of the box BEFORE the stack is fitted, so it never lands on the bottom plane |

**Known traps:**
- The tilt is a trade the register makes for you: -48° reads as slabs and keeps the vertical squash at about 0.67, and the yaw is only -8° because a sheared line's axis-aligned DOM rect is far wider than its glyphs. The CJK sweep's *overlap* rule still reports candidates on this register for that reason — every one of them carries the instrument's own `rot: true` flag, which means the number is inflated by the tilt. The rotation-free instrument (the `leading` rule, which is what would catch a note's two lines colliding) reports nothing.
- Everything on a plane is measured against that plane and SOLVED down to its floor before anything is refused: the label, the note's line count and the chips' total width all shrink together. What it refuses is copy that does not fit at the floor — a sentence used as a `label`, chips that are phrases, or a name plus a note plus items that together need more plane than exists. Each refusal names the two measurements.
- In a portrait zone the layers stand further apart rather than growing: the planes are wide and short, so width is what limits them and the vertical room would otherwise go unused. The layers keep their size and order — only the spacing, which carries no meaning, changes.
- The camera is fitted to the SETTLED stack, lift included, so nothing jumps when the focal layer comes forward. It is fitted to the plane CORNERS (`fitSurfaces`), not to a sphere around each plane's centre: the sphere is far bigger than a wide tilted plane, and fitting it left the first version of this shot sitting small in a mostly empty frame.

**Refuses:** fewer than 2 or more than 5 layers; a layer with no `label`; an empty item; more than 4 items on a layer; a `focal` that is not a layer index or null; a label, note or chip row that will not fit the plane at its floor.

**Reference:** `remotion/src/shots/PlaneStack.tsx`
