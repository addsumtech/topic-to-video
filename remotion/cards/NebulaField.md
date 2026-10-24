# NebulaField

**Identity:** a glowing cloud of gas in deep space — runtime/volume's domain-warped emission, hydrogen red turning [O III] teal toward the hot star that ionises it, dust lanes in front absorbing it, stars in and behind it — under a slow push about the star; the type sits on the cloud's quiet side.

**Use when:** where stars are born, gas lit by a star, the scale and slowness of space; the subject IS a nebula or interstellar gas. `star` places the ionising star, and the colour is graded from it (teal near, red far) — the relation of an H II region, drawn because the film named the star. **Not when:** the beat is about a star system or orbits (an orbital register), or a real telescope image should carry it (credited PhotoPlate).

**Motion core:** the cloud fades up over the first 0.3; title 0.1–0.32, note 0.28–0.5; a 6% push about the star across the beat; the gas evolves slowly throughout.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the statement, top left | — |
| `kicker` | a mono line above it | — |
| `note` | a quieter line under it | — |
| `colors` | `[outer, inner]` #rrggbb | default H-alpha and [O III] (display approximations of the lines) |
| `star` | where the ionising star sits `[u, v]` | moves the teal core and the push's fixed point |
| `seed` | which cloud | — |

**Known traps:**
- The keep-out follows the push into the canvas's own coordinates, so the gas stays thin under the words on every frame.
- No sound of its own: a nebula is silent and slow.

**Refuses:** colors that are not one or two #rrggbb; a title and note that do not fit above the caption band; no WebGL context.

**Reference:** `remotion/src/shots/NebulaField.tsx`, `remotion/src/runtime/volume.tsx`
