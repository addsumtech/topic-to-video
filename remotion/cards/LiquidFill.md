# LiquidFill

**Identity:** a round vessel fills with glowing, gooey liquid (two wobbling wave surfaces and merging bubbles) up to the film's percentage, while the numeral counts up with it. Only a vessel filled to exactly 100 swaps its numeral for a checkmark.

**Use when:** progress or completion stated as one sourced percentage. **Not when:** there is no figure (the vessel stays empty), the number is not a 0–100 share (EdStat, OdometerRoll, TermCounter), or the claim is a trend over time (ChartLive).

**Motion core:** the fill and the count-up run together over 0.1–0.62 (easing in and out). The level then holds while the waves and bubbles keep moving. At exactly 100, the check pops in with overshoot from 0.64 and replaces the numeral shortly after.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `pct` | the liquid's level and the numeral | a number from 0 to 100 prints with `%`. A string holding one number (`"40%"`, `"约 40%"`) prints exactly as written. `null` or `''` draws no liquid and no numeral. `0` draws no liquid but prints the numeral. The numeral is fitted inside the vessel at up to 150px |
| `label` | the mono line under the vessel | fitted to one line at up to 34px, so long copy shrinks |

**Known traps:**
- The liquid used to fill to the brim and tick whatever `pct` said, so `pct: 40` ended as a full vessel with a check. It now rises to `pct` and ticks only at 100.
- Leaving `label` unset prints `on your machine`, even when the film passes `pct`. Only a render with neither prop gets the illustrative full vessel.
- At 100 the numeral is replaced by the check, so a film that wants "100%" on screen loses the figure for the rest of the clip.
- The liquid and ring colours (teal to blue) are fixed. The DNA reaches only the background.

**Refuses:** a `pct` that is not one number from 0 to 100 (a range, a word, a negative, more than 100).

**Reference:** `remotion/src/shots/LiquidFill.tsx`
