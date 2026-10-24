# LandscapeWell

**Identity:** the product's own 16:9 picture — a frame it made, a screenshot, its recording — shown in a frame of another shape without shrinking it to a strip. `scan`: a tall well whose CROP travels from one named point of interest to the next, a map of the whole frame in its corner with the crop's rectangle on it, a ring drawing round each point as the crop lands. `loupe`: the whole frame as a band and a lens that magnifies each point in turn on a leader from where it sits.

**Use when:** "look at THIS, in the thing itself" in a vertical (or square) film about something that makes landscape pictures — the detail is the argument and the picture is the evidence. A 9:16 film could otherwise only show its product's frames as thumbnails on black (bench-launch: five of eight beats a 16:9 band across a 9:16 frame; three crops hand-rolled). **Not when:** the picture should be seen whole on its device (`DeviceHero`), or something is being operated (`DeviceDemo`).

**Motion core:** the well rises in on the first point's framing; each leg eases the crop's centre and interpolates its zoom geometrically (a push in reads at a constant rate), then holds the point for its label's reading time. In the loupe the lens stays put, its content pans, and the leader follows the point along the band. The label is one slot (`runtime/kinetic` swap) that rolls to each point's name as the crop lands, with an `01/03` index beside it.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `media` | `{image | video, w, h, from?, keepOut?}` — the film's own picture in its public dir, with its pixel size; `keepOut` shares the crop must not show | absent, the register's own text-free skeleton frame (no film ever sees it) |
| `points` | 1–6 `{x, y, label, zoom?}`: shares of the media, the point's name, and how much of the media's width the crop shows there | the crop goes only where the film says, in its order; `zoom` absent = as close as the well allows while still covering it |
| `mode` | `scan` or `loupe` | scan fills a tall frame with the detail; loupe keeps the whole frame in view and argues "this part of it" |
| `kicker` | a small spaced mono label over the well | not held to a reading time |

**Schedule — in seconds:** the rise 0.35–0.7 s, each leg 0.45–0.9 s, and each point's hold its label's read-once time first, the rest shared by must-read time; `points.N.label` may bring a name earlier. `PACE = 'seconds'`.

**Carry:** the well is the `screen` anchor — a `container` can carry a device's screen (`DeviceHero`, `DeviceDemo`) straight into it, and a `through-window` can push into it.

**Known traps:**
- A film's own frame carries its burned caption: a crop that shows it puts a second subtitle on screen (bench-launch b2). `media.keepOut: {bottom: 0.2}` (shares, any side) keeps the crop out of it; the map still shows the whole frame.
- Faded up from nothing, the well was an empty ground for a whole seam — a through-window into this beat looked through its letters at black. The picture is there on the first frame and only settles (3.5% scale); the ring, map, lens, leader and label arrive after.
- The crop is clamped inside the media (less its keep-out), so a point near an edge is framed off-centre rather than showing the ground past the picture; a recording plays from `from` at 1x for the beat.
- The index (`01 / 03`) changes on the label's own swap, not when the crop starts to travel.

**Refuses:** no points or more than 6; a point outside 0..1; a point with no label; a zoom outside (0, 1]; media with neither image nor video, or without its pixel size; a keep-out share outside [0, 0.8) or leaving under a fifth of the media.

**Reference:** `remotion/src/shots/LandscapeWell.tsx`

**Measured:** (skeleton frame, no media) 2.8% ink · 21.3% footprint · 0.0005 motion · reach 0.05 — the fixture can vary only the labels and the kicker; the picture is the film's own media, which no fixture has. Holds: clean at its own 8 s (2.37 / 2.20 / 1.87 s); two points at 4 s — clean (1.67 / 1.23 s).

**Review:** NOT critic-reviewed — built and looked at by its author (scan and loupe; 9:16, 16:9, 1:1; a real 16:9 frame from the GPS film and the skeleton).

**Provenance:** product-ui. **Family:** A.
