# PixelBuild

**Identity:** an 8-bit arcade screen — a chunky green pixel checkmark builds cell by cell on a diagonal sweep under a yellow score HUD and a `1UP` counter, over a brick ground, then a yellow pixel banner pops in beneath it, all behind CRT scanlines and a vignette.

**Use when:** a playful, nostalgic "level complete" payoff carried by one banner line. **Not when:** the film is serious, the result is anything other than a success (the sprite is always a checkmark), or the beat has content to show.

**Motion core:** each pixel pops in with an overshoot as a diagonal sweep passes it, starting from the top-left of the sprite, so the checkmark is complete within the first half of the clip; the banner scales up with an overshoot over 0.7–0.9; the HUD, bricks and scanlines are static throughout.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `hud` | the yellow score text at top left | a fixed 42px mono line; a short "SCORE 1200"-style string reads as arcade furniture, a long one runs across toward the `1UP` counter at top right |
| `label` | the banner under the checkmark | fitted to ONE line across the frame (minus 120px), capped at 68px — short copy keeps the full pixel size, long copy shrinks |

**Known traps:**
- Omitting the props prints a product demo: `SCORE 9999` and `WORKBUDDY · COMPLETE`.
- `1UP ▪▪▪` is fixed INTRINSIC_TEXT (the HUD depicting itself); no prop reaches it.
- A longer banner used to wrap to two lines at a fixed 68px and land in the caption band at 1:1; it is now fitted to one line and the sprite and banner slide up together by whatever does not fit.
- Only the ground follows the DNA; the sprite, HUD, banner and bricks keep their fixed arcade colours.

**Reference:** `remotion/src/shots/PixelBuild.tsx`
