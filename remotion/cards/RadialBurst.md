# RadialBurst

**Identity:** a glowing hub pops up in the centre of the frame, then four concentric rings of fourteen shapes each — rays, petals, dots, petals — bloom outward from it in turn in rainbow hues, the whole mandala turning slowly, with a name under the hub and a spaced tagline at the bottom.

**Use when:** a brand or idea moment that wants a mesmerising, symmetric, vivid picture — "everything revolves around this" said as atmosphere. **Not when:** the orbit is a claim about specific things or a count of them — the rings are fixed at 14-fold and name nothing (use a hub-and-spoke or list register that takes the items); or the film's palette must hold (the ring hues are fixed).

**Motion core:** the whole ring system rotates steadily through the clip. The hub scales up with an overshoot 0.02–0.20; the rings bloom outward with an overshoot, starting at 0.10, 0.24, 0.40 and 0.56 and each taking 0.24; the hub name fades in 0.16–0.32, the tagline 0.60–0.82.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `hub` | the name set under the hub | fixed-size bold type, not fitted: a one- or two-word name reads as a label on the hub, a longer one wraps under it; omitted, the demo product name `WorkBuddy` prints |
| `tagline` | the widely spaced mono line near the bottom | fixed size and wide tracking, not fitted: a few words read as a stamp, a sentence wraps; omitted, the demo `EVERYTHING, IN ORBIT` prints |

**Known traps:**
- The picture encodes nothing from the film: fourteen shapes per ring, four rings, always. Don't use it where the narration counts or names the things "in orbit" — the viewer will count shapes that mean nothing.
- A mandala is a FORM and prints on paper, so it takes the film's ground and ink. The ring HUES are still fixed (any palette gets a rainbow), but their exposure is not: on a film that grounds on paper each one is walked along its own black-to-white axis until it clears the graphics floor, because at the shipped 62% lightness every petal sits near 2:1 on warm white.
- The `#rg` bloom — a blur of each shape merged back under itself — is a dark-ground device and is dropped on a light one: against night it is a bloom, on paper it is a halo of the shape's own colour that dissolves the shape's edge into it. A printed mandala is crisp.
- The hub is left as it is on purpose — a deep violet disc with a lilac inner and a white core carries its own ground, so its tones read on any paper. Only its outer ring, which meets the film's ground, is exposed for it.
- The hub's name takes the film's ink, the kicker its `dim`, and the name's separation shadow follows the film's own ground.
- Ring radii are fixed pixel sizes: on a narrow (portrait) frame the outer rings run past the sides.
- Omitting `hub` prints a real product name on any film.

**Reference:** `remotion/src/shots/RadialBurst.tsx`
