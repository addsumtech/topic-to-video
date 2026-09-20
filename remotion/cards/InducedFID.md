# InducedFID

**Identity:** a receive coil sits at the left with a small dot circling above it, and a decaying oscillation draws itself from left to right inside a dotted envelope: the free induction decay, the MR signal as it is actually measured.

**Use when:** showing the real measured MR signal: precessing magnetisation inducing a voltage in a coil, which dies away (T2*). **Not when:** showing a voice or audio waveform (VoiceSignal), the precession itself (LarmorPrecession), or a generic decorative wave. This register replaced a symmetric waveform because that one was decoration.

**Motion core:** the title fades up over the first quarter. The trace is revealed left to right over 0.08–0.92. The dot circles above the coil for the whole clip (three turns). The envelope and labels do not move.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the 40px title at the top, with a fixed "free induction decay" line under it | a short claim sits on one line. Long copy wraps (not fitted) |
| `accent` | the coil, the circling dot, the "T2* decay" label and the faint baseline | recolours the source side of the picture |
| `accent2` | the dotted decay envelope | recolours the guide the trace dies inside |

**Known traps:**
- "coil", "T2* decay" and "free induction decay" are fixed English labels and print on every film.
- The trace has a fixed shape (15 cycles, a fixed decay rate). It is not data, so it cannot back a stated T2* value.
- Leaving `label` unset prints `The induced signal decays`.

**Reference:** `remotion/src/shots/InducedFID.tsx`
