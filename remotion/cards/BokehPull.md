# BokehPull

**Identity:** thirty soft coloured bokeh orbs drift over a dark ground; then the lens pulls focus — the orbs shrink, sharpen and dim while a blurred wordmark resolves crisp at the centre, followed by a widely spaced tagline.

**Use when:** the beat is a reveal of one name or word, i.e. "coming into focus" or clarity emerging. **Not when:** the beat carries more than a short title, or it's an interface/UI focus beat (the header points to `FocalIsolation` for UI blur).

**Motion core:** the orbs drift continuously, falling slowly and swaying. The focus pull runs 0.32–0.72 with an ease in-out: orb radius shrinks about 5×, their blur drops from 10 to 1.5 and the title's blur from 34 to 0. The title fades 0.36–0.66 and the tagline 0.62–0.84, still half-blurred as it arrives.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the wordmark that comes into focus | fixed 190px display, not fitted. One short word is the intended look; several words wrap into huge lines centred on the whole frame, and one long word runs past the edges |
| `tagline` | the spaced mono line under it | fixed 32px with 0.4em tracking, not fitted |

**Known traps:**
- Omitting the props prints the demo `WorkBuddy` / `IN FOCUS`.
- The title isn't fitted and has no caption-band reserve (it centres on the frame), so long or Chinese titles can overflow.
- The orb palette follows the DNA, but the wordmark is fixed near-white and the vignette always darkens the edges, so a light DNA ground loses the title's contrast.

**Reference:** `remotion/src/shots/BokehPull.tsx`
