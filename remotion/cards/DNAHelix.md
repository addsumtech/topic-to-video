# DNAHelix

**Identity:** a double helix of glowing nodes and coloured base-pair rungs assembles top to bottom and spins, depth-shaded front to back, with a big title and a tagline resolving over it.

**Use when:** the blueprint / "encoded" / biotech idea as a title beat. **Not when:** the beat carries items or data — the helix takes none, and its rung colours alternate by position and encode nothing — or the title is long.

**Motion core:** the helix builds level by level from the top down (between 0.05 and ~0.60) while spinning for the whole clip; the title rises 0.50–0.74 and the tagline 0.62–0.84.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big word over the helix | fixed 128px, not fitted — a long title is not shrunk and can run past the frame |
| `tagline` | the tracked mono line under it | fixed 32px with wide tracking, not fitted |

**Known traps:**
- Neither line is fitted to the frame; keep the title to a word or two.
- Only the ground's base colour reads the DNA; the strand and rung colours are fixed cyan, pink and mint.
- The helix geometry is fixed pixels (a fixed amplitude, 150px margins top and bottom), so it does not scale with the frame's width.
- Defaults print 'Encoded' / 'the blueprint of it all'.

**Reference:** `remotion/src/shots/DNAHelix.tsx`
