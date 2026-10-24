# LitMedium

**Identity:** a statement set on the topic's own MEDIUM under one slow light — a letter's paper, a coast's water, a machine's brushed metal, a potter's clay. The surface never moves; a single light drifts across it over the beat, so the tooth, the glints, the brushing or the relief read as a real object in a real room (`runtime/material.tsx` `LitGround`).

**Use when:** the beat is about what something is MADE of or WHERE it lives, and the material itself is part of the claim ("it all started on paper", "milled from one block"). **Not when:** the material is incidental decoration — then it is a texture swatch behind a slide; use a register whose picture encodes the content.

**Motion core:** one point light drifting along the frame's far edge from the type (`finish.light`'s side), over the whole beat; the type is still. A fixed-seed height field, so every render of a frame is the same.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `material` | the medium: `paper`, `water`, `metal`, `clay` | else the film's DNA material (`material.tsx` `dnaMaterial`), else paper |
| `mediumColor` | the medium's base colour, `#rrggbb` | else the medium's own; the ink is re-picked against the lit span of this colour |
| `kicker` | a small label over the title | context, never a second claim |
| `title` | the statement the medium carries | required |
| `note` | one supporting line | optional |

**Known traps:**
- The ink is picked against the material's MEASURED lit span (`MATERIAL_SPAN`, the 2nd–98th percentile of the rendered ground), not its base colour: a lit ground is a range and a reader sees its worst end.
- The ground probe classified it as accent/accent2 by luminance coincidence; its ground token is the literal paper colour in `shotLuma.ts`, and its caption and seams read the medium it actually paints.
- QUIET by construction: measured 0.0007 motion, 7.0% ink, 0.021 light range (product DNA) — a held statement on a surface. Intercut with a dense register.

**Refuses:** an unknown `material`; no `title`; a medium/colour on which no ink reaches 4.5:1 across its lit span (names the best ratio it found).

**Reference:** `remotion/src/shots/LitMedium.tsx`

**Measured:** 7.0% ink (clip median) · 15.4% footprint · 0.0007 motion · 0.021 light range (`remotion/register_energy.json`).

**Review:** NOT critic-reviewed — built and looked at by its author (sheets at 16:9 and 9:16).

**Provenance:** craft-handmade. **Family:** X.
