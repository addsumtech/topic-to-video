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
- `accent` gets an alpha byte appended for the B₀ axis (`#22d3ee` → `#22d3ee80`), so a named, rgb() or 3-digit colour produces an invalid stroke and the axis disappears. Every preset and every deck-derived DNA writes `#rrggbb`, so the accent it now defaults to is safe; a hand-written prop is the risk.
- The ink is the film's: M, its label and the two headings take the DNA's `fg`, the B₀ and plane labels take `dim`, and `accent`/`accent2` fall back to the film's two accents before their own cyan and violet. A prop still wins, and with no DNA every original literal prints as before. Until this was done the vector and the headline drew white on white on a light-ground film (measured median 1.12:1).
- Omitting `label` prints the default "Resonance tips the magnetization".

**Reference:** `remotion/src/shots/MagnetizationTip.tsx`
