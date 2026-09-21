# GFactorNoise

**Identity:** a small reconstructed tile grows grainier as the acceleration factor R rises along a track that turns red past the usable cap, with R's read-out riding the fill.

**Use when:** why speeding up costs quality — a penalty that grows with the shortcut, parallel imaging's g-factor. **Not when:** there is no cap or penalty to show, or the beat is aliasing itself (Aliasing, UndersampledKspace).

**Motion core:** the title fades up over the first quarter; R rises linearly 0.12–0.80 — the grain thickens with it and, when a `factor` is given, the fill and read-out travel along the track, turning red once past the cap; it holds after 0.80.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `factor` | the measured acceleration — a number or the film's string ("2.5×") | with it: a fill to that R, red exactly past `cap`, and a read-out that settles on the film's string (a bare number gets "×"). Without it: no fill and no read-out; the grain still grows to the cap, as mechanism only |
| `cap` | where the red zone starts | a number > 1; the axis stretches to cover it and the factor (at least 1–5×), and the grain reaches its unusable density at the cap |
| `limit` | the red sentence under the title | a claim about the world; '' removes it |
| `label` | the title | 40px, not fitted |
| `accent` | the tile border, the usable zone and the fill | the film's `accent` unless a hex overrides it |

**Known traps:**
- The track once used three different numbers — the red zone began at 3.4× on its own ticks and the fill turned red at 3.02 — so `factor: 3.2` drew a red bar outside the red zone. Every mark now goes through one axis.
- With no `factor` the fill used to run to 3× anyway, reading as a measured R nobody supplied; now nothing is drawn.
- `limit` defaults to "R = 2–3 max · never beyond the coil count" and does not follow `cap` — move one, rewrite the other.
- The grain once landed outside its tile (drawn with the tile's frame offset), so the tile stayed empty. The tile still holds only grain on a dark square — there is no image prop — and it is a fixed 400×300px.
- The title, the cap sentence, the "g-factor noise →" callout, the read-out and every 1×..5× tick were literals picked for a near-black ground, so on a warm-white film 45.1% of this register's marks measured under 3:1 with a connected hole 1.26% of the frame — the whole reading was gone while the speckle field kept the median at 5.61:1. They read from the DNA now (`fg` for the title and read-out, `fg` pulled 40% toward `dim` for the ticks). The red keeps its hue — it is the viz-semantics, not a palette choice — and only deepens until it clears the 4.5:1 text floor on the film's ground (its most demanding job is two runs of 20–22px mono, not the band; on the ink probe's warm white that is #bf4651 at 4.51:1, and on every dark ground it is the literal, unchanged).
- The TILE is not ink and does not follow the ground: it is a scan viewport whose whole content is white and red speckle, so it keeps its own dark stop and the grain keeps the two literals it was measured for. On a light film the register is a dark tile on paper by design.

**Refuses:** a `cap` that is not a number > 1; a `factor` that is not exactly one number ≥ 1.

**Reference:** `remotion/src/shots/GFactorNoise.tsx`
