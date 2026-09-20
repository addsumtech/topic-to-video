# PhysicsStack

**Identity:** weighty blocks fall from above one after another, land with a damped bounce and a dust puff, and settle into a bar chart whose heights are the film's own values drawn from zero — each value written on its bar, the labels under the ground line, a headline arriving last.

**Use when:** comparing 1–8 sourced, non-negative quantities where the comparison should feel physical and satisfying. **Not when:** any value is negative (use a signed chart register), the items are just names with no values (use a list register), or there are more than eight.

**Motion core:** the labels stand under the ground line from the start; bar i hits the ground at 0.16 + i × min(0.12, 0.5 / n) after an accelerating fall from above the frame, then bounces with decaying height over the next 0.34 of the clip while a dust puff spreads for 0.12; its value fades in 0.1–0.24 after it lands; the headline fades in over 0.7–0.9. With many bars the last one is still settling close to the end.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `bars` | one bar each: `label`, `value` (the sourced number), optional `display` (how the value is written) | heights are value ÷ largest value, from zero, so the tallest always fills the chart; 1–3 bars are wide slabs, 8 are narrow columns. Each bar takes the next DNA palette tone. Labels share one size, the largest at which every label fits two lines of its column. A value of 0 keeps its slot and label but draws no block |
| `items` | legacy label-only input | never draws: without `bars` it throws (heights would be invented); alongside `bars` it is ignored |
| `label` | the headline at the top | fitted to one line across 84% of the width; an accent full stop is always appended |
| `unit` | the suffix on each written value when a bar has no `display` | `%`, `ms`, `k` … appended to the raw number |

**Known traps:**
- It used to lay `items` over five hard-coded heights (a "rising week") and cycle the labels to fill five slots, so three tools came out with invented proportions and two names printed twice. Heights now come only from `bars`.
- Omitting both `bars` and `items` draws the demo — Mon–Fri with invented values under "a week of shipping" (validate.py warns when a film does this).
- The written value is the raw number plus `unit`, never rounded; pass `display` for a formatted figure ("1.2k", "3–4").
- The headline always gets a trailing accent `.`, so a question or a label already ending in punctuation ends up with two marks.

**Refuses:** `items` without `bars`; `bars` not an array or with fewer than 1 or more than 8 entries; a bar with no label; a value that is not a finite number ≥ 0; every value 0.

**Reference:** `remotion/src/shots/PhysicsStack.tsx`
