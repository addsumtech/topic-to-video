# StarfieldWarp

**Identity:** stars stream outward from a vanishing point, accelerating into hyperspace streaks; at peak speed the core flashes white, the field slows, and a glowing title blooms out of the light with a tagline under it.

**Use when:** a cosmic "into the future" moment — a launch, a next-chapter title, a leap forward (family V). **Not when:** the beat carries content to read, or the film wants this beat on its own light ground (it keeps its night — see the dark-world trap).

**Motion core:** the stars accelerate 0.05–0.62, streaks lengthening with speed and looping so the field keeps streaming; the core flash rises and falls 0.60–0.78; the field decelerates 0.66–0.90 to under a third of its top speed; the title scales down into place as it fades in 0.72–0.92, the tagline 0.82–0.96.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the glowing line that blooms from the core | very large fixed-size white type, not fitted: a word or two lands as a title card; a long title wraps into several huge lines; omitted, the demo `Lightspeed` prints |
| `tagline` | the spaced mono line under it | a short phrase; omitted, the demo `the next era, now` prints |
| `accent` | the star colour and the title's glow | plumbing — the DNA accent does NOT replace it; pass the film's accent to match |

**Known traps:**
- **Dark world** (`@dark-world` in the shot). A star is a point of light and the warp is the trail it leaves, so this register takes the film's ground only while that ground is DARK and keeps its own night when the film's is light. A light film gets one deliberately dark beat here, which the seam guard and the caption ink already handle; it no longer paints a dark ellipse in the middle of the film's page.
- The centre of the ground gradient is a fixed navy, and the title, tagline and outer streaks are fixed white and pale blue. They all read because the ground under them is always dark.
- The title and the core bloom are fixed pixel sizes, authored for 1920×1080; the title is not fitted to narrower frames.
- The field is decoration: star count, speed and flash carry no data and take no props.

**Reference:** `remotion/src/shots/StarfieldWarp.tsx`
