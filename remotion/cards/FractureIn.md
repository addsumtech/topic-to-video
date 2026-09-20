# FractureIn

**Identity:** twenty-five gradient tiles fly in from scattered 3D space and lock into a 5×5 poster from the centre outward; a large title and tagline resolve over the settled surface.

**Use when:** many parts → one picture — a bold reveal title. **Not when:** the picture must be real content (the tiles form a colour gradient, not an image), or the parts must be named.

**Motion core:** tiles lock in a ripple by distance from the centre (start times from 0.06 at the centre to 0.40 at the corners, each landing over 0.26); the title rises 0.60–0.82, the tagline 0.72–0.90; then it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big line over the poster | fixed 128px, not fitted |
| `tagline` | the tracked mono line under it | fixed 34px, not fitted |
| `accent` | the start colour of every tile's gradient | a hex literal, not the DNA; the end colour is a fixed violet |

**Known traps:**
- The poster is a fixed 5×5 grid of fixed-size tiles (1040×750px), not scaled to the frame; on a 1080-wide frame it nearly fills the width.
- Only the ground's base reads the DNA; the tiles come from `accent` and a fixed violet.
- Title and tagline are not fitted; defaults print 'One picture' / 'from many moving parts'.

**Reference:** `remotion/src/shots/FractureIn.tsx`
