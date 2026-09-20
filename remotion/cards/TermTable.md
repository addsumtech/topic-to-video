# TermTable

**Identity:** a `$ command` types, and a mono table prints beneath it: first the header row, then each body row wiping in left to right the way a terminal line lands. One hero row can be lit with an accent tint, a left rule and a `◂ note`. The table sizes itself to its content and fills the content zone.

**Use when:** the beat is structured data (a config readout, a comparison grid, a short spec sheet) in a terminal-grammar film, and one row may be the point. **Not when:** the values should be compared as lengths (use `TermBars`), or the cells are sentences. Each cell is one line and never wraps, so long cells shrink the whole table.

**Motion core:** the prompt types over 0.04–0.17 and its caret blinks after. The header row prints at 0.20–0.29. The body rows then wipe in one after another from 0.28, all landed by 0.80. The hero row is lit from the moment it prints. It holds from 0.80.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cmd` | the prompt line (in the title bar when `framed`) | fitted to the table's width, so a long command gets smaller. The demo is `cat table.tsv` |
| `headers` | the column heads, in small spaced caps at about 0.6 of the body size | upper-cased unless the DNA says otherwise. The demo is `col` / `value` |
| `rows` | the body, `string[][]`, first column bold | column widths follow each column's widest measured cell (CJK counted at about twice a Latin advance). A ragged row is padded with empty cells. The type grows until the table fills the zone's width or height (with a cap), so a short table is large and a long one is small, down to 8px. A narrow table widens its columns up to 1.75×, and rows breathe taller in a tall zone. If every non-first column holds only short values, those columns are set flush right |
| `hero` | the 0-based index of the lit row | that row gets an accent tint, an accent left rule and an accent first cell. `-1`, absent or out of range lights nothing |
| `heroNote` | the `◂ note` printed after the hero row's last cell, in the accent at header size | shown only with a valid `hero`. Its default is the word `note`, so set it (or `''`) whenever you set `hero` |
| `framed` | draws it inside a window with three lights and the prompt in the title bar | for anchor beats. The open default puts the prompt on the canvas above the table |

**Known traps:**
- Setting `hero` without `heroNote` prints the demo `◂ note` beside the lit row.
- The table used to sit in a fixed left-aligned column, so a short Chinese table parked in x≈300..980 of a 1920 frame and three beats using it read as one recycled slot. It is now measured and fills the zone. Don't wrap it in another fixed-width box.
- Cells never wrap, and the type is one size for the whole table, so a single long cell shrinks every row. Put prose in a shorter paraphrase, or split the table.
- Value-column alignment is decided for the whole table. One prose column keeps every non-first column flush left.
- There is no row cap. A long table does not throw; it keeps shrinking toward 8px type.

**Reference:** `remotion/src/shots/TermTable.tsx`
