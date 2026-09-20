# BrutalistType

**Identity:** a stark brutalist page: hard ink rules, a hot accent block top-right (optionally carrying a folio), mono metadata, a huge two-line grotesque headline that rises in, and a statement whose second half is reversed out of an ink box. The headline jolts twice with an RGB-split glitch and slice bars.

**Use when:** the beat is a blunt, aggressive statement: a manifesto line, a refusal, a hard claim in two short headline words and a two-part statement. **Not when:** the tone is refined or editorial (the header points to `SwissEditorial` as the opposite pole), or the copy is long; long copy makes the headline shrink until it loses its force.

**Motion core:** the headline rises 60px and fades in 0.06–0.40 on an expo ease. Glitch jolts peak at t ≈ 0.42 (±0.05) and t ≈ 0.72 (±0.04): offset red and cyan copies plus three ground-coloured slice bars. The rules, accent block, metadata and statement are on screen from the first frame and don't animate.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `titleTop` | the headline's first line | both lines share one size: the smallest of 300px, the height left above the statement, and each line's width fit. One long line shrinks the whole headline |
| `titleBottom` | the headline's second line | as above; two short capitals-only words (`WORK` / `BUDDY.`) are the intended scale |
| `meta` | the mono metadata, top-left | fixed 30px, not fitted |
| `statement1` | the statement's plain first half | the two halves flow as one line, fitted to width up to 54px. When they wrap, their lines are counted and the headline gives up the room |
| `statement2` | the statement's second half, reversed out in an ink box | as above; this is the punch half |
| `counter` | the folio inside the accent block (`'02/05'`) | no default. Omitted, it leaves the bare hot block; given, it's fitted to the block (up to 46px) |

**Known traps:**
- The accent block used to carry a literal `01/03`, making every beat "part one of three" of a series that didn't exist. `counter` has no default on purpose.
- Omitting copy prints the demo `WORK` / `BUDDY.` / `WORKBUDDY / LOCAL-FIRST` / `NO CLOUD.` / `NO NONSENSE.`
- A fixed 300px headline once descended through the statement (`1674` over `A TORNADO CAME…`, a delivered beat). The headline is now sized from its room, the statement's counted lines and its width. Without the width fit, a six-glyph Chinese title ran 476px into the caption band.
- The glitch copies are fixed red and cyan; ink, ground and accent follow the DNA.

**Reference:** `remotion/src/shots/BrutalistType.tsx`
