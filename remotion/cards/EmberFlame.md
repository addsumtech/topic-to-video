# EmberFlame

**Identity:** flame licks flicker up from the lower frame, embers rise and fade, and a fire-gradient wordmark glows over the heat with a tracked tagline under it.

**Use when:** passion, a launch, "built with fire" — an energy title. **Not when:** the beat carries items or numbers (it takes none), or the film's palette cannot take orange fire — the flames ignore the DNA.

**Motion core:** never still: the flames flicker and the embers rise for the whole clip; the title rises 0.28–0.56 and breathes slightly with the flicker; the tagline rises 0.62–0.84.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the fire-filled wordmark | fixed 168px, not fitted — a long title is not shrunk and can run past the frame |
| `tagline` | the tracked uppercase mono line under it | fixed 32px, not fitted |

**Known traps:**
- Only the ground's base colour reads the DNA; the flames, embers, heat glow and the title's gradient are fixed fire colours.
- Neither line is fitted; keep the title to a word.
- The flame and ember geometry is fixed pixels around the frame's centre.
- Defaults print 'Ignite' / 'built with fire'.

**Reference:** `remotion/src/shots/EmberFlame.tsx`
