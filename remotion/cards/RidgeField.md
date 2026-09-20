# RidgeField

**Identity:** the "Unknown Pleasures" plot — twenty-eight glowing ridgelines stacked in depth, each filled to hide the ones behind it, rise from the front row back while a wave ripples through them; a big title and a spaced tagline fade in over the field.

**Use when:** an atmospheric "signals / patterns in the noise" moment — a section or title card for data, sound, or measurement as a mood (family K, generative). **Not when:** the beat shows or claims real data: the ridge heights are summed sine waves, not measurements (use a chart register that takes the numbers).

**Motion core:** rows appear front to back — the front row from about 0.03, the back row by about 0.42–0.64 — each rising from flat; the whole field ripples continuously as waves travel through it. The title fades in 0.50–0.74, the tagline 0.62–0.84.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big line at the top | fixed large white type, not fitted: a word or two reads as a cover title; long copy wraps over the field; omitted, the demo `Signals` prints |
| `tagline` | the spaced mono line at the bottom | a short phrase; omitted, the demo `patterns in the noise` prints |
| `accent` | the ridgeline stroke and glow colour | plumbing — the DNA accent does NOT replace it; pass the film's accent explicitly to match |

**Known traps:**
- The field is placed by fixed pixel margins, not the content zone: at 1080p the front rows reach down into the band where the caption is burned.
- The field is decoration generated from sines. Captioned as a real spectrum or signal it is a fabricated figure.
- A ridgeline plot is a FORM, not a light: on a film that grounds on paper it draws dark-on-light. The stroke (the `accent` prop, default a pale cyan that measures 1.77:1 on warm white) is walked along its own black-to-white axis until it clears the graphics floor, hue kept; the title takes the film's ink, the kicker its `dim`, and the ground's lit core and the title's separation shadow follow the film's own paper.
- Each ridge is FILLED with the ground colour to occlude the rows behind it, so the occlusion works on either ground.
- The near rows' 4px glow is a dark-ground device and is dropped on a light one: on paper it is a halo of the stroke's own colour that dissolves the stroke's edge into it.
- The depth ramp lifts its floor on a light ground (0.62 → 1 instead of 0.35 → 1). A stroke painted at 35% composites toward whatever it sits on: against night that deepens the far rows and they stay lines, against paper it dilutes them into the page however well the stroke's colour was solved. The back of the field still recedes from the front, it just recedes in tone.
- Ridge margins are fixed pixels, so on a portrait frame the field is a narrow column.

**Reference:** `remotion/src/shots/RidgeField.tsx`
