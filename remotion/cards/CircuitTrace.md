# CircuitTrace

**Identity:** on a dark PCB with a faint grid of pads, a central chip pops in and labelled satellite pads pop in on a ring around it. Copper L-shaped traces draw from each pad to the chip, glowing signal pulses race along them into the chip, and the chip lights up.

**Use when:** the beat is "these parts are wired into one core": hardware, systems, or integrations, with a hub and 2–6 short-named connections. **Not when:** the connections have direction, order or labels of their own (the traces are anonymous), or there are more than six nodes.

**Motion core:** the title fades 0.03–0.16; the chip scales in 0.10–0.32 with an overshoot; pad i pops 0.12 + i·0.06 → +0.22; trace i draws 0.18 + i·0.07 → 0.50 + i·0.07; once a trace is drawn, its pulse runs 0.52 + i·0.05 → 0.92, along the vertical leg first and then the horizontal; the chip's glow turns on at t > 0.5.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the spaced mono title at the top | fixed 30px, uppercased, 0.3em tracking, not fitted |
| `chip` | the word on the central chip | fixed 56px in a 260×200 chip, not fitted; one short word (`CORE`, `API`) fits, and a phrase spills |
| `nodes` | the pad labels, 1–6, spaced evenly around the ring by the number given | one shared size fitted to the 116px pads (up to 26px). Short codes (`IN`, `MEM`) sit large, and long names shrink every pad. The ring's vertical radius shrinks so the lowest pad clears the caption band |

**Known traps:**
- Omitting props prints the demo `Wired together`, `CORE`, `IN`, `MEM`, `I/O`, `NET`, `PWR`.
- A Chinese node name used to wrap out of its pad, and the lowest label landed 90px in the caption band at 1:1. It's now fitted, and the ring yields.
- Pads in the same half of the ring route their L-traces along a shared vertical, so at six nodes the upper and lower side pads read as one bus into the chip.
- The copper and signal greens keep their hue on every ground, but anything drawn straight onto the film's ground — the traces, the pad grid, the chip's pins, the signal dots, and the pad and chip edges — is exposed for it on a light film, and the traces are drawn nearly solid there rather than at half alpha. The pad grid is a fixed 28×16 array laid out for 1920×1080.
- Most of this register already reads on paper: measured on a light film the median mark is 11.79:1, because the pads and the chip carry their own dark board under mint type, and those fills are left alone. What failed was the title (a fixed pale mint on the bare ground, now the film's ink) and the copper on the page.
- The mint glows — the chip's outer bloom, the pads' halo, the pulse's — are dark-ground devices and are dropped on a light film. On paper the chip's bloom was a pale wash that the gate was reading the chip's own rim against.

**Refuses:** no `nodes`, or more than six (a seventh trace finishes drawing just as the pulses stop, so its signal never reaches the chip — group the parts or use a graph register); an empty node name.

**Reference:** `remotion/src/shots/CircuitTrace.tsx`
