# AtomOrbital

**Identity:** an atom builds out from a single glowing nucleus with an overshoot. Given `shells`, electrons race around concentric orbits in one slowly tilting plane, with exactly the stated count on each shell. Without `shells`, the three-ring atom emblem carries soft lights sliding along its rings and no electrons. A title and tagline rise in beneath.

**Use when:** the beat names an element or is about atomic/physical structure, and (in `shells` mode) the electron configuration is a fact the film states. Also use it as a general "science / the core of things" emblem with no counts. **Not when:** the beat needs a molecule or bonds, or a nucleus composition (proton and neutron counts aren't drawn).

**Motion core:** the orbits and core scale in 0.06–0.44 with an overshoot; electrons circle continuously, outer shells more slowly; in `shells` mode the orbit plane tilts from −22° to +4° over the clip; the title rises 0.52–0.76 and the tagline 0.62–0.84. In emblem mode the rings keep fixed tilts and only the lights move.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big line under the atom | fixed 104px, not fitted. An element name sits as a caption plate, and a long title wraps across the frame |
| `tagline` | the spaced mono line under the title | fixed 30px with 0.18em tracking, not fitted |
| `shells` | electrons per shell, inner to outer (carbon `[2, 4]`, sodium `[2, 8, 1]`) | `null` (default) gives the emblem with nothing to count. 1–7 shells draw concentric rings (more shells means tighter spacing), and electrons shrink as the count grows so a full shell stays countable rather than fusing into a band |

**Known traps:**
- Every atom used to have seven nucleus spheres and seven electrons on shells of 2/3/2, whatever the title said: a film titled "Carbon" showed an arrangement no element has. Counts now come only from `shells`.
- Omitting the props prints `Elemental` / `the core of everything`.
- The emblem's soft lights are continuous, layered strokes on purpose. Drawn as segments they came out beaded, like countable dots, which is the one thing that mode must not look like.
- The geometry is in fixed pixels (the outer shell radius is 400, the emblem rings about 340). The ring colours are no longer fixed cyan, pink and violet: a shell's colour only says "this ring is not that ring", so the palette is the film's, derived from its two accents. The nucleus's amber is kept on any ground — it is the one colour here that means something — and only its exposure moves.
- An atom is a diagram, not a light, so on a film that grounds on paper the title takes the film's ink, the tagline its metadata ink, and every hue is walked along its own black-to-white axis until it clears the floor. Measured on a light film before that: 26.3% of the register's ink under 3:1 — all of it the tagline — and the title read only because the ground's fixed `#101430` core was painting a dark pool under it.
- The orbit's stroke is drawn at 0.35 alpha on a dark ground and nearly solid on a light one: a third of a bright hue still glows on black and is a third of the way to the page on paper. The nucleus bloom and the electron glows are dark-ground devices and are dropped on a light film.

**Refuses:** `shells` that is not an array of 1–7 entries, or any entry that is not a whole number from 1 to 32.

**Reference:** `remotion/src/shots/AtomOrbital.tsx`
