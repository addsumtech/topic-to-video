# FilmScreen

**Identity:** a film or recording shown as ITSELF — playing on a program monitor at no more than its own pixels, from the second the beat names, its stretch marked on a scrub bar of the whole clip. It can come in close on part of the picture (`region`), mask the clip's own burned caption strip (`crop`), pin one note to a point by a leader, run the film's beats past beneath it (`run`), or light one frame per beat beside it so their count is seen (`reel`).

**Use when:** the evidence is footage — a film the skill made, a product recording, a screen capture — and the beat's claim is "here it is, really running". Built for the topic-to-video promo (2026-11-03): showing its real films as stills read as a slideshow (film_energy_qa p75 0.0027, under the 0.0037 floor); playing them was the single biggest lift. **Not when:** the picture should sit in its device (`DeviceHero`), something is being operated (`DeviceDemo`), or a vertical film needs to tour one landscape frame (`LandscapeWell`).

**Motion core:** the clip plays at its own speed from `from`; its content leans in 5% over the beat inside a fixed frame (so the clip is drawn at ≤ 1/1.05 of its pixels and stays sharp at the peak); the scrub bar's fill runs with it; a `run` passes at ~3.5% of the short side a frame; a `reel` lights its frames one after another and counts them.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `video` | the clip's path in the film's folder (or `{src}`); `w`, `h`, `seconds` are read off the file by the render | absent, the register's own text-free skeleton (no film ever sees it) |
| `from` | the clip second the beat starts on | pick a stretch that moves — a static page tier film reads still here too |
| `name` | the film's own name over the monitor (mono) | short; it is a label, not a title |
| `crop` | share of the clip's height masked off its bottom | 0.185 for a 16:9 film with burned captions, so its caption never doubles the film's own |
| `region` | `{x, y, w}` shares: a close-up of part of the picture | at its own pixels a close-up is SMALLER on screen than the whole clip — choose it for the detail, not the size |
| `note` | one line pinned by a leader to a point of the clip | one fact the viewer would miss |
| `noteAt` | where the leader points, `{x, y}` shares of the clip's frame | on the thing the note names, not beside it |
| `run` | the film's beat frames (paths), passing beneath | the film running; frames are measured off the files and must be frame-shaped |
| `reel` | the film's beat frames, a lit grid with its count | "this many beats" made visible; with a `run` too, the run passes beneath and the reel stands beside (below, in a tall frame) |

**Known traps:**
- A delivered film's `_keyframes/scene_NN.png` may be a STRIP of phases (the html tier writes 2800x315 sheets): `register_props` refuses a frame whose shape is not a frame's.
- Its library energy row is ~0: standalone it has no clip and draws its skeleton. Its motion IS the footage — choose a `from` where the clip moves, then check the beat with `workshop.py motion` or the film's `film_energy_qa`.
- A typed `w`/`h` is how a clip gets drawn past its pixels: the render reads them off the file and ignores none it can measure.

**Refuses:** a clip with no measured size or length; a stretch that runs past the clip's end; `crop` ≥ 0.5; a region outside the picture; fewer than 2 frames; a frame drawn past its own pixels.

**Reference:** `remotion/src/shots/FilmScreen.tsx`, `scripts/render_remotion.py` `film_screen_props`
