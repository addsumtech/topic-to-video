# LarmorPrecession

**Identity:** a moment vector μ, tilted off the dashed B₀ axis, precesses around it like a spinning top. Its tip traces a cone with a trailing arc, above the relation `f₀ = γ·B₀` and the film's value for γ.

**Use when:** a steady rotation set by a field: Larmor precession, or the fundamental frequency of a system. **Not when:** electrons orbiting a nucleus (AtomOrbital; this register exists because an orbit shot was standing in for precession), an RF pulse tipping the vector (MagnetizationTip), or spins settling into alignment (SpinsAlign).

**Motion core:** constant from the first frame to the last. The vector makes four full turns across the clip, and the trail follows the tip. The title fades up over the first quarter. There is no build and no settle: it never holds still.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the 40px title at the top | a short claim sits on one line. Long copy wraps |
| `gamma` | the value printed after `≈` in the relation | printed exactly as the film writes it. `''` prints the bare relation `f₀ = γ·B₀`. The line is fitted to the width at up to 24px, so a long value shrinks the whole relation |
| `accent` | the trail, the B₀ axis and the relation's text | the colour of the motion |
| `accent2` | the cone's base ellipse | the colour of the path guide |

**Known traps:**
- The default `gamma` is `42.58 MHz/T`, which is true of ¹H only. It used to be literal text that no prop could reach, so a sodium or phosphorus film was told the hydrogen number. It is a prop now, but omitting it still prints the hydrogen value.
- The tilt and the speed are fixed. Neither is data.
- Leaving `label` unset prints `Larmor precession`.

**Reference:** `remotion/src/shots/LarmorPrecession.tsx`
