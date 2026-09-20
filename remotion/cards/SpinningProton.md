# SpinningProton

**Identity:** a single glowing proton with a + charge sits at the centre with dipole field loops around it, a magnetic-moment arrow μ pointing up from its pole and a curved spin arrow circling the μ axis above it, among faint water molecules; a title across the top and a small mono line underneath.

**Use when:** the beat explains what a hydrogen nucleus IS for MRI/NMR — a spinning charge that makes a tiny magnet — the mechanism, not a count. **Not when:** the claim is about many spins lining up (use `SpinsAlign`), precession in a field (use `LarmorPrecession`), or chemistry in general (a molecule register).

**Motion core:** the title eases up from faint over the first quarter. For the whole clip the spin arrow (a 250° arc) travels around a fixed ring about μ, counter-clockwise seen from above (the right-hand rule for μ pointing up), passing behind μ on the far side and in front of it on the near side; the field loops sway slightly; the proton, μ and the water stay still. A quiet, looping register.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the title across the top | fixed-size, not fitted: one line reads as the claim; long copy wraps; omitted, the demo `A proton that spins like a tiny magnet` prints |
| `sublabel` | the small mono line under the proton | fitted to the frame width; `''` draws nothing. Omitted, the demo `~70% water · ¹H` prints — a figure |
| `accent` | the proton's colour and the field loops | defaults to the film's DNA accent, and the sphere's dark side is a shade of it; pass a prop to override |
| `accent2` | the spin arrow and the water molecules | defaults to the film's second accent; pass a prop to override |

**Known traps:**
- The line under the proton used to be a hardwired `~70% water · ¹H` that no prop could change (LIBRARY.md advertised a `sublabel` that did not exist). It is a prop now but still defaults to that percentage: omit it and a body-composition figure prints on any film.
- μ's arrowhead used to run through the title's letters; its length now yields to the title band — it is not a quantity.
- The spin arrow used to be an arc rotated in the picture plane (500° over the clip), which is spin about the line of sight: mid-shot it stood on end through the proton and hung upside down. It now travels around a ring that stays horizontal about μ.
- μ starts at the proton's pole; it used to start at the centre and strike through the + charge.
- The ink is the film's: the proton's rim, μ and the title take the DNA's `fg`, the line under the proton and the bulk water take `dim`, and the `+` takes `onAccent` — it is ink ON the sphere's accent body, not on the ground. With no DNA every original literal prints as before. Until this was done the rim, μ and both lines of type drew white on white on a light-ground film (measured median 1.12:1).

**Reference:** `remotion/src/shots/SpinningProton.tsx`
