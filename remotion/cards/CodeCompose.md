# CodeCompose

**Identity:** a dark IDE window with traffic-light dots and a filename tab. Syntax-coloured code types itself line by line beside a line-number gutter, with a caret at the typing head; then an output strip fades in at the bottom showing `$`, a drawn green tick, a done word and a status line.

**Use when:** the beat is "the work is written and run as code", with up to seven short lines that are real or plausible code for the film's subject. **Not when:** the code is long or wide, or the beat is a terminal session (use a `Term*` register).

**Motion core:** typing runs 0.06–0.66, linear in characters across all lines (newlines count); the caret is solid while typing and blinks afterwards; the output strip fades in 0.72–0.90.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `doneLabel` | the word after the green tick | short (`done`, `passed`) |
| `filename` | the tab's filename | fixed 24px mono |
| `lines` | the code: plain strings, or arrays of `{t, c}` tokens | a string is uncoloured plaintext; tokens carry explicit colours. Lines don't wrap or shrink (34px, 20.4px a cell, a Han glyph two cells): about 52 cells fit the full 1180px window. Few lines type slowly and read clearly, and more lines type faster |
| `status` | the grey text after the done word | a short outcome line |

**Known traps:**
- The window is a fixed 620px tall with a 58px line pitch, and nothing clips the code layer. From the eighth line, code draws under the output strip and then below the window.
- Omitting props prints the demo WorkBuddy Python, `workbuddy.py` and `— shipped, on your machine`.
- The caret used to count one cell per character and was drawn through the middle of Han glyphs (splitting 测). Wide characters count two cells, but the 20.4px cell is a constant for the default mono at 34px, so a DNA with a different mono face can drift the caret off the typing head.
- The output strip's `▶` read as player chrome, so it's now `$`. The `✓` fell back to a hairline glyph, so it's now drawn as SVG.
- The window chrome and token palette are fixed dark and syntax colours; only the ground follows the DNA.

**Reference:** `remotion/src/shots/CodeCompose.tsx`
