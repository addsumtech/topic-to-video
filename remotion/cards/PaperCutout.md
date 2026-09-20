# PaperCutout

**Identity:** a layered cut-paper diorama — sun, far hills, clouds, mid hills, near hills and a foreground strip, each a paper plane with a soft shadow — pans left to right with real parallax and a gentle push-in, while a paper banner card rises tilted into the mid-ground and a tagline appears below.

**Use when:** a warm, handmade payoff or "it's done" beat carried by one short banner word and a tagline. **Not when:** the beat has parts, steps or data to show, or the film is technical or serious.

**Motion core:** the camera pans from left to right over the whole clip on an eased curve, near planes sliding further than far ones, while a slow push-in (most of it early, eased out) enlarges the nearest planes most; the banner rises from 120px below with an overshoot over 0.42–0.68; the tagline fades in over 0.7–0.9.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the word on the paper banner card | a fixed heavy 92px with no fit: one short word (or word plus mark) makes a bold sign; a longer label wraps into a taller card |
| `tagline` | the line under the diorama, above the caption band | a fixed 40px centred line; a short phrase sits as a caption, a long one runs toward the frame edges |

**Known traps:**
- Omitting the props prints a product demo: `DONE ✓` and "your ai team · on your machine".
- The tagline used to sit at `bottom: H*0.08`, under the burned caption; it is lifted clear of the band now — keep it one line.
- Under a DNA the planes are a ramp from the film's accent into its ground and the sun takes `accent2`, so the depth reads in the film's hues; without a DNA it is the warm construction-paper palette.

**Reference:** `remotion/src/shots/PaperCutout.tsx`
