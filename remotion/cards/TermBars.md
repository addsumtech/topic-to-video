# TermBars

**Identity:** a `$ command` types and executes, and a column of labelled metric bars prints beneath it. All the bars grow together on one clock against a faint 25/50/75 guide and a % axis, while each figure counts up beside its bar. By about a fifth of the way in they hold the true figures.

**Use when:** the beat compares a few measured quantities (benchmark scores, pass rates, shares) in a terminal-grammar film, and the comparison is the point: a 2× difference must read as a 2× length. **Not when:** there are more than ten rows or the values need a full grid (use `TermTable`), or it is one figure (use `TermCounter`).

**Motion core:** the command types very quickly and executes at 0.11. Rows print with a small opacity stagger that affects opacity only. Every bar is its target × one shared growth value, which runs over 0.12–0.205 (easeOutExpo) and snaps to 1, so the ratio between any two bars is exact on every frame and a ranking can never invert. Guides and axis fade in around 0.12–0.21. Tags light up in their row's tone once the bars settle. It holds the true figures for the rest of the beat.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cmd` | the command typed above (in the title bar when `framed`) | leaving the demo `eval --suite bench` prints it on any film |
| `title` | an optional headline above the readout | fitted to one line (26–46px). Empty draws no title |
| `rows` | 1–10 rows of `{label, fill?, pct?, value?, tag?, tone?}` | bar thickness shrinks as rows are added (16–52px), so two rows are fat bars and ten are thin ones. `fill` is a 0–1 fraction and `pct` a 0–100 percentage. `value` ("1.2M") is printed instead of a percentage, and a row with only a `value` gets no bar and no track. Labels share one size fitted to the widest and are cut with an ellipsis. `tag` is a bordered chip, dim until the bars settle. `tone`: `warn`/`accent2`/`alert` uses the second accent, `dim`/`muted` de-emphasises, and anything else uses the accent |
| `note` | a `# comment` line under the bars | wraps. It takes height from the bars |
| `cells` | how many block glyphs make up a full bar, when the DNA draws bars as a block run | more cells give finer steps. By default it is measured so the run fills the track exactly |
| `framed` | draws it inside an explicit terminal window with traffic-light dots | for 2–3 anchor beats only. The default open canvas keeps the terminal grammar without the box |

**Known traps:**
- The bars used to grow staggered over half the beat. Mid-flight, the 0.40 bar was drawn shorter than the 0.20 bar at the exact frame the narration said "20% vs 40%". Do not give rows their own timing back.
- The track used to be a fixed 420px, so 20% vs 40% differed by about 85px. It is now sized from the frame, minus the label, figure and tag columns.
- `pct` once guessed its unit (≤ 1 meant a fraction), so `pct: 0.8` drew an 80% bar. Now `pct` is always 0–100 and `fill` always 0–1, and a value out of range throws. Figures print exactly as written, so a sourced 99.6% no longer settles as "100%".
- A row with nothing to draw once printed an empty bar labelled "0%", a measurement nobody made. It now throws. If any row carries a `value`, the axis keeps its guides but drops the 0–100 labels.
- Leaving `rows` out prints the demo `metric_a` / `metric_b` with `PASS` tags. The bar's look (block run, ruled scale, pixel cells, solid track) comes from the DNA; this register owns only the clock, the columns and the scale.

**Refuses:** `rows` not an array, empty, or more than 10; a row that is not an object; a row with no `label`; `fill` outside 0–1 or `pct` outside 0–100 (or non-numeric); a row with neither `fill`/`pct` nor `value`.

**Reference:** `remotion/src/shots/TermBars.tsx`
