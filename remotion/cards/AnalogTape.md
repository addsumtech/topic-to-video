# AnalogTape

**Identity:** a VHS/CRT frame. The wordmark wobbles in three RGB-split copies above a spaced tagline, under scanlines, a rolling tracking band, frame-by-frame grain and a barrel vignette. A retro OSD sits in the corners: a blinking `REC`, `SP · date`, `▶ PLAY` and a running counter.

**Use when:** the beat wants nostalgia, home video, an archive, or an "authentic / analog" feel for a name or short phrase. **Not when:** the beat carries data or a list, or when a recording date would be a false claim (see `date`).

**Motion core:** the wordmark fades in 0.06–0.40 and the tagline 0.40–0.70. The texture never stops: a per-frame wobble, an RGB split that breathes between about 3 and 7px, a tracking band rolling down the frame, grain reseeded every frame, `REC` blinking (on for 26 of every 40 frames), and the counter running with the clip.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big wordmark, uppercased | fitted to the frame width (minus the split), up to 168px. A short name fills the tape and a long one shrinks; Latin case is always forced to capitals |
| `tagline` | the spaced mono line under the wordmark | fixed 34px with 0.34em tracking and no fit, so long copy wraps into a wide, airy block |
| `date` | the recording date after `SP · ` in the top-right OSD | fitted to the room right of `REC`, up to 40px; `''` leaves only `SP` |

**Known traps:**
- `date` defaults to `AUG 12 2026`. That's a claim about when the footage was recorded, and it used to be a literal stamped on every film, including a 1994 home video. Pass the film's own date or `''`.
- Omitting `title`/`tagline` prints the demo `WorkBuddy` / `ON YOUR MACHINE`.
- The title used to be a flat 168px. Under the `cinematic` DNA (Bodoni Moda) it was cut off by about 85px on both sides in all three RGB copies, so it's now fitted with the split's excursion included.
- `REC`, `SP`, `▶ PLAY` and the counter are the deck describing itself (`INTRINSIC_TEXT`, `INTRINSIC_READOUT`). The counter measures nothing.
- The three RGB copies use fixed red, cyan and cream; only the ground follows the DNA.

**Reference:** `remotion/src/shots/AnalogTape.tsx`
