# FlowField

**Identity:** streamlines (150 by default) trace a curling flow field, drawing on in staggered waves in two accent colours, and a large wordmark with a tagline settles at the centre over a dark vignette.

**Use when:** flow, "everything moving as one", an ambient generative hero or title. **Not when:** the beat carries items or data (the field is a fixed function and takes none), or you want soft gradient blobs rather than lines (AuroraFlow).

**Motion core:** each streamline draws on over 0.4 of the clip, starting at a staggered moment between 0.02 and 0.52; the title rises 0.50–0.74, the tagline 0.62–0.84. The field itself does not move; once drawn, lines hold.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the wordmark | fixed 132px, not fitted |
| `tagline` | the tracked mono line under it | fixed 32px, not fitted |
| `accent` | one of the two stroke colours, and the title's glow | a hex literal, not the DNA |
| `accent2` | the other stroke colour | same |
| `lines` | how many streamlines | fewer is sparse, more is dense; silently clamped to 20–220 |

**Known traps:**
- The stroke colours are props with fixed defaults, not the film's DNA: a themed film keeps teal and violet unless it passes its accents. On a film that grounds on PAPER whichever colours are in play are walked along their own black-to-white axis until they clear the legibility floor (exposure only, hue kept) — the default teal measures 1.56:1 on warm white, which is 150 streamlines nobody can see.
- Two things that only bite on a light ground, both fixed here and both worth knowing if you edit this register: the per-line GLOW (`drop-shadow(0 0 3px currentColor)`) is a dark-ground device — on paper it is a halo of the line's own colour, so the line ends up read against itself — and so it is dropped there; and the settled stroke is OPAQUE there, because a line painted at 66% alpha is composited back toward whatever it sits on, which on paper dilutes it to about 2.5:1 however well its colour was solved. The draw-on fade still carries the entrance.
- The wordmark takes the film's ink and the tagline its `dim`. The ground's lit core, the centre wash the wordmark is read against, and its separation shadow all follow the film's own paper on a light film, rather than staying the near-black they are on a dark one.
- Each line is one flat colour picked from the two; nothing shifts along a line.
- The field and every line's start point are fixed, so every film gets the same pattern.
- Title and tagline are not fitted; defaults print 'In flow' / 'everything, moving as one'.

**Reference:** `remotion/src/shots/FlowField.tsx`
