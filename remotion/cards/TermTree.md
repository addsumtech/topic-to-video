# TermTree

**Identity:** an `ls`-style command types and executes, and a file tree of the topic's parts prints under a root line. Each row is a `├──` / `└──` branch with a name, an optional dim note and an optional accent tag chip, and the whole tree is sized to fill the content zone.

**Use when:** the beat names the parts of one thing as a listing (a project's folders, a system's components, what is in a package) in a terminal-grammar film, and the names are the content. **Not when:** each part is really a different picture (a beat about seventeen character states once drew their filenames here; use `StateSheet`), or the parts carry numbers to compare.

**Motion core:** the command types over 0.05–0.16 and the root line appears with the result from 0.20. Rows then slide in from the left, their starts spread evenly over 0.26–0.68 and each taking 0.12, so the last lands at 0.80 whatever the count. Rows hold their space before they arrive, so the tree does not jump.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cmd` | the command typed above | leaving the demo `ls -la` prints it on any film |
| `root` | the root line at the top, in the accent | a path or the whole thing's name. The demo `~/project` prints if omitted |
| `items` | the rows, `{name, note?, tag?}` | the type size is solved so the widest line and the row count fill most of the content zone. Few short rows give big type; many rows or a long name give small type (floor 18px). Names are counted in mono cells, so a Han glyph counts as two. `note` is clipped with `…` at 24 cells. `tag` is a small bordered chip. The last row gets `└──`. The demo is `src/ source ok`, `docs/ docs ok` |
| `framed` | draws it inside an explicit terminal window | for anchor beats |

**Known traps:**
- A line cannot wrap (`white-space: pre` is what makes a tree a tree). Notes are clipped at 24 cells but names are not, so one long name drags the whole tree's size down, and at the 18px floor it can still overrun.
- Names used to be measured in characters, so a Chinese tree ran 2086px past the right edge at 16:9. The width is counted in cells now.
- Rows used to arrive 0.14 apart without limit: the fifth finished at t = 1.08 and the seventh at 1.36, so a list past five was never fully drawn. The stagger now scales with the list.
- At a fixed 40px the tree once filled 9% of a 1920 frame. It is sized to the zone now; do not pin the size back.

**Reference:** `remotion/src/shots/TermTree.tsx`
