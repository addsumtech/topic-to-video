# RainGlass

**Identity:** a title seen through a rain-streaked window — droplets slide down the pane with wet trails over faint static streaks, while the soft-focus scene behind the glass (glowing bokeh and the message) slowly sharpens until the title resolves.

**Use when:** a moody, atmospheric title or section card — "calm behind the storm", clarity arriving, weather or waiting as the mood. **Not when:** the beat carries content to read (lists, figures, comparisons); or the film's ground is light (the type and rain are fixed pale).

**Motion core:** droplets slide down the whole time, each at its own speed, wrapping from bottom to top. The scene behind the glass goes from heavy blur to slight blur 0.30–0.80; the title fades in 0.28–0.60 and the tagline 0.50–0.74, both inside the blurred layer, so they come into focus with the scene.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the message behind the glass | very large fixed-size display type, centred and not fitted: a word or two fills the frame like a sign seen through a window; a longer title wraps into several huge lines; omitted, the demo `Weather it` prints |
| `tagline` | the spaced mono line under the title | a short phrase; omitted, the demo `calm behind the storm` prints |
| `accent` | the colour of one of the bokeh glows behind the glass | plumbing — it tints the light behind the pane, never the type; the DNA accent does not replace it |

**Known traps:**
- The title never goes fully crisp: the blur eases down to a slight softness, not to zero — the glass stays in front of it.
- Only the ground follows the DNA. Title, tagline, droplets and streaks are fixed near-white, so on a light-ground DNA they lose their contrast.
- The droplets are decoration with no meaning; there is no prop for them.

**Reference:** `remotion/src/shots/RainGlass.tsx`
