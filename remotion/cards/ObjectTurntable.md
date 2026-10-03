# ObjectTurntable

**Identity:** a thing the film drew stands on a platter and turns, so its shape in the round is seen; the platter's rim marks the turn (one accent tick rides it), and the object's name sits under the platter.

**Use when:** the beat says "this is what it is like from every side": depth, a hidden face, the relation of a part at the back to one at the front. **Not when:** a front view carries the claim (`ObjectStage`); the object is a real photograph; the turn would show a flat drawing edge-on.

**Motion core:** the platter comes in over 0.02–0.16 while the object draws itself (its t over 0.04–0.4). The turn runs from −sweep/2 to +sweep/2 over 0.08–0.92, eased at both ends; the name lands over 0.42–0.66 and holds while it turns.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `object` | the thing the film drew — `{"id": …, "props": …}` | required in a film; an object whose META sets `turns` is handed the yaw and draws its own 3D (see objects/DemoForm); any other object is turned as a card |
| `sweep` | degrees turned across the beat, 20–360 | a flat object: at most 120 (±60°), past which its back would face the camera — refused, not flattened |
| `title` | what it is, under the platter | fitted to the width |
| `note` | one line under the title | what the turn reveals |
| `kicker` | a spaced label in the title band | follows the DNA's label casing |

**Known traps:**
- A card turn foreshortens the object's words too: keep an object's text off a turntable, or make it a `turns` object that keeps its type facing the camera.
- The object stands on the platter's centre line by its box's foot; an object with empty space at its foot looks like it hovers.
- The object is fitted at its own declared aspect (`META.aspect` — the workshop's `new-object` scaffold defaults it to 1, a square) inside a square room; the platter is sized from that same room, not from the fitted box, so a wide or tall object leaves the room's spare width or height empty and turns on a platter sized as if it still filled the whole square.
- `yaw` only reaches the object when it draws its own 3D (`META.turns`): in RADIANS, via `ObjectProps.yaw`, the same angle a `turns` object runs through `runtime/project3d`. A card's own turn is a CSS `rotateY()` in DEGREES, clamped to ±`MAX_CARD_TURN` (60°) around the whole object from the outside — the object itself never sees `yaw` and cannot read which way it is turned.

**Refuses:** a `sweep` outside 20–360; a sweep over 120 on an object that does not draw its own 3D; an object id nobody defines.

**Reference:** `remotion/src/shots/ObjectTurntable.tsx`

**Provenance:** motion-graphics (a beat holding an object is judged on the object's own world). **Family:** K.
