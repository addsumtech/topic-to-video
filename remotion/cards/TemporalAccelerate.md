# TemporalAccelerate

**Identity:** a long task compressed. A checklist of steps scrolls up at speed with motion blur and speed streaks, each step ticking off as it passes, while a counter (and, if the film measured one, a timer) races alongside; then everything snaps to done.

**Use when:** the claim is "all of this took almost no time". The film has a real list of steps and, ideally, the real elapsed seconds. **Not when:** the steps need to be read (at speed they are a blur by design; use a list register), or there is no speed argument at all.

**Motion core:** the list scrolls over 0.08–0.80 on a slow, fast, settle curve. Blur (up to 26px) and nine faint speed streaks follow the scroll's velocity, peaking mid-run. The counter climbs with the scroll, and the timer, when present, races up to the film's figure. At 0.84 it snaps: every row ticks, the counter turns to the success colour and reads `N / N · doneLabel` with a small overshoot scale (0.84–0.98), and the timer settles on the exact figure.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | the steps, one checklist row each | the counter is `k / N` of this list. Lists of four or fewer do not scroll at all: they sit still, with only the first row ticked, until the snap. Longer lists scroll until their last four rows sit at the top, and the more steps there are, the faster they fly past. Each row is a fixed 96px at 44px type, so a long step wraps inside it. Leaving the demo in place prints twelve English office steps ("Read the brief" … "Deliver to folder") |
| `seconds` | the elapsed time the film measured | no default. Absent, there is no timer numeral and the list and counter still race. Present, a huge numeral with an accent `s` races up using the film's own decimals and lands on the figure exactly as written, never rounded or padded |
| `doneLabel` | the word after `N / N` when it snaps | the film's language for "done". `''` leaves the bare `N / N`. Leaving the demo in place prints English `done` |

**Known traps:**
- The timer used to race to a hard-coded `2.8s`, so every film reported the same invented duration. The numeral now appears only when `seconds` is given, and it must be a number (a string like `'2.8s'` throws).
- The counter once claimed "12 / 12 · done" above three unticked rows, and counted a hard-coded 12 whatever the list. At the snap every row is now ticked and the count is the list's own length.
- The layout is fixed pixels drawn for a 1920×1080 frame: a 980px list box at x=150 and a right-aligned timer at 260px type. Nothing scales to the frame, so at 1080 wide the list box runs past the right edge and under the timer.
- It is short (4.5s) and built for speed. It is the wrong shot for a list the viewer must actually read.

**Refuses:** `items` empty or not an array; `seconds` that is not a finite number ≥ 0 (omit it for no timer).

**Reference:** `remotion/src/shots/TemporalAccelerate.tsx`
