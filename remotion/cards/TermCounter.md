# TermCounter

**Identity:** a `$ command` types and executes, and one huge mono number counts up on the open canvas with its unit beside it and a `# note` beneath. It lands early and holds.

**Use when:** the beat is one key figure (a percentage, a count, a year span) and the film is in terminal grammar. **Not when:** there are several figures to compare (use `TermBars` or `TermTable`), or the figure needs context drawn around it rather than a caption.

**Motion core:** the command types over 0.05–0.16 and the result rises in from 0.20. The count-up runs over 0.12–0.35 (easeOutCubic), so on the open canvas it is already most of the way there by the time the number fades in. Only in `framed` mode is the whole climb visible. From 0.35 the settled string holds, which covers the mid-scene delivery frame.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cmd` | the command typed above the figure | leaving the demo `stat --value` prints it on any film |
| `value` | the figure, as a string exactly as it should read (`"19%"`, `"−12"`, `"2019–2024"`) | a string that is exactly one number counts up, keeping its sign, decimals, grouping, prefix and suffix. A range, a span or a word shows verbatim from the first frame, since there is nothing to count. The size (at most 220px) is fitted to the settled string plus its unit, so a long string comes out smaller, down to a 56px floor. The demo is `100` |
| `unit` | the unit set beside the figure, at about a quarter of its size | short units (`%`, `ms`, `天`) read cleanly. A long unit takes width from the figure and shrinks it |
| `note` | a `# comment` line under the figure | a fixed 34px line, centred. A long note wraps |
| `framed` | draws it inside an explicit terminal window | for anchor beats. It also shows the count-up from its start, because the window does not fade the result in |

**Known traps:**
- The number used to be parsed and re-printed: "−12" landed as 12, "3–5" as 35, "2019-2024" as 20,192,024, "N/A" as 0, and anything ≥ 1000 was rounded. The settled frame is now the film's string exactly. Pass the figure as written, sourced.
- It used to land at t = 0.70, so a mid-scene delivery frame showed "18%" for a sourced 19%. It lands by 0.35 now; do not slow it back down.
- The size fit floors at 56px, so a very long string can still overrun the column. Keep it to one figure.

**Refuses:** an empty `value`.

**Reference:** `remotion/src/shots/TermCounter.tsx`
