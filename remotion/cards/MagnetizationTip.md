# MagnetizationTip

**Identity:** an MR physics diagram — the magnetization vector M starts up the vertical B₀ axis and, while a resonant RF sine wave pulses on the right, nutates 90° down into a tilted transverse-plane ellipse, spiralling as it precesses and leaving its trace; one headline sits at the top.

**Use when:** an MRI beat whose claim is what the RF pulse actually does — resonant excitation at the Larmor frequency tips M into the transverse plane. **Not when:** the beat is about the signal that follows (use InducedFID), precession on its own (use LarmorPrecession), or anything outside MR physics — the diagram's labels are fixed physics text.

**Motion core:** the headline brightens from 40% to full over the first quarter; the drive runs 0.18–0.9 — the tip angle eases from 0° to 90° while M sweeps two full precession turns, the spiral trace growing behind it, and the RF wave's envelope swells and dies over the same window, peaking mid-way; after 0.9 M rests in the transverse plane with only a slow drift and the wave lies flat.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the headline across the top | a fixed 40px centred line; a short claim sits as a title, a long one wraps into more lines across the full width (no fit) |
| `accent` | the spiral trace, the ring on M's tip, the dashed B₀ axis and the "Larmor frequency" caption | the colour of the motion; must be a 6-digit hex (see traps) |
| `accent2` | the transverse-plane ellipse and the RF wave | the colour of the drive; a hue far from `accent` separates the cause (wave) from the effect (vector) |

**Known traps:**
- The diagram's labels (`RF pulse · B₁`, `at the Larmor frequency`, `transverse plane`, `B₀`, `M`) are fixed English text declared as INTRINSIC_TEXT; no prop reaches them, so a Chinese film still shows them in English.
- `accent` gets an alpha byte appended for the B₀ axis (`#22d3ee` → `#22d3ee80`), so a named, rgb() or 3-digit colour produces an invalid stroke and the axis disappears.
- Only the ground follows the DNA: the vector, its label and all text are fixed light tints and the accents default to cyan/violet, so on a light DNA ground the white vector and headline lose contrast.
- Omitting `label` prints the default "Resonance tips the magnetization".

**Reference:** `remotion/src/shots/MagnetizationTip.tsx`
