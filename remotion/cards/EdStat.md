# EdStat

**Identity:** a magazine pull-stat: kicker and rule, one huge figure — counting up, or still — with its unit and a caption beneath.

**Use when:** one sourced headline number in a print register. **Not when:** there are several numbers to compare (DataMonolith, ChartRace), or you want a mechanical or terminal feel (OdometerRoll, TermCounter).

**Motion core:** kicker and rule draw first (to ~0.26); the figure counts up and settles by ~0.32, then holds for the remaining two thirds, so the true figure is on screen at the mid-scene frame. With `roll: false` nothing counts.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `value` | the figure, as the film's string | printed byte for byte once settled ("3–5", "−12", "1.2M" survive). A string that is exactly one number counts up; a range or a word shows verbatim from frame one. Fitted to the column's width and the content zone's height — a longer figure gets smaller type, never below 48px. Its form (serif, mono, segment…) follows the DNA |
| `unit` | the unit | sits on the figure's baseline if both fit the column; otherwise drops to its own accent line beneath |
| `caption` | a dim line of body text under the figure | wraps; the height budget reserves up to four lines |
| `kicker` | the small caps above the rule | '' leaves the rule alone |
| `roll` | whether the figure counts up | `false` shows the true figure from the first frame — use it when the beat is ABOUT the number |
| `framed` | puts the stat on a bordered surface panel | a card instead of type on the ground |

**Known traps:**
- The figure used to be stripped to digits and re-formatted: "3–5" printed 35, "1.2M" printed 1.2, the year 2024 printed "2,024". It is the film's string now — pass it exactly as it should read.
- The old roll settled at 0.7, so for most of a beat the frame showed figures no source gave (17%, 56%… on the way to a narrated 60%). It settles by ~0.32 now, and `roll: false` removes the intermediate digits entirely.
- A comma hanging below the figure's tight line box once landed inside the unit line; a descender reserve is kept under every figure and a unit that does not fit stacks beneath.
- Omitting `value` prints '100'; the kicker defaults to 'BY THE NUMBERS'.
- A caption past about four lines is not reserved for, and pushes the block toward the caption band.

**Refuses:** an empty `value`.

**Reference:** `remotion/src/shots/EdStat.tsx`
