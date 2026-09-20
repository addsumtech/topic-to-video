# LiquidGlass

**Identity:** a soft, light UI list (a title over rounded rows) with a frosted-glass lens and two smaller droplets gliding across it. The lens settles on the film's target row, which ticks, strikes through and turns its chip green; with no target, the lens comes to rest off the list.

**Use when:** premium polish and focus: one item in a short list resolved, in a glassy, Apple-like idiom. **Not when:** several items resolve (only one row can be the target), there are more than six rows, or the point is a real product screen (GlowPick draws the product's own surface).

**Motion core:** the lens and droplets glide from the upper left to their rest point over 0.1–0.78 (easing in and out), then settle with overshoot over 0.78–0.94. The ✓ in the lens and the target row's strike-through and green chip appear early in the settle.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | 1–6 row labels, 44px, in fixed 900px-wide rows | rows keep a 150px pitch while they fit (four do at 16:9). More rows, or a shorter frame, close the pitch to stay out of the caption band, and the lens and its ✓ shrink with it. Labels are not fitted |
| `title` | the 60px heading above the list | a short heading. Not fitted |
| `target` | the index of the row the lens settles on | set: that row alone ticks, greens and strikes through. Omitted: nothing is resolved, and the lens rests in the empty gutter beside the list, below it on a tall frame, or peeking in from the right edge |

**Known traps:**
- The strike-through used to go to the fourth row and the ✓ to the last, making two different "done" claims. Only `target` resolves a row now.
- The lens rests mid-row, and frosted glass blurs whatever is under it, so the part of a long target label that runs under the lens is unreadable. Keep that label short.
- Leaving out `items` gives the demo rows and the demo target (`Ship it`). Leaving out `title` prints `Today’s plan` even with a film's rows.
- Past six rows the pitch would close below what a chip and a 44px label need on a square frame, which is why the maximum is six.

**Refuses:** 0 or more than 6 items; an empty item; a `target` that is not an integer index into `items`.

**Reference:** `remotion/src/shots/LiquidGlass.tsx`
