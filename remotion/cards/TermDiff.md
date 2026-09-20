# TermDiff

**Identity:** a `$ diff` command types and executes, `--- before` / `+++ after` headers appear, and the removed lines (`-`, the DNA's second accent — red with no DNA) and then the added lines (`+`, the accent) slide in one at a time as tinted bars with a coloured left rule.

**Use when:** the beat is a before/after contrast told as a few lines of change (old wording vs new, old config vs new) in a terminal-grammar film. **Not when:** the contrast is two whole sides to weigh against each other (use `VersusSplit`), or there are more than eight lines in total (it refuses).

**Motion core:** the command types over 0.05–0.16 and the result appears from 0.20. The `---` header fades in at 0.22–0.30 and `+++` at 0.26–0.34. Then the lines arrive from 0.34, each sliding in from the left over 0.10: all `minus` lines first, then all `plus` lines. They are 0.13 apart for up to four lines and closer for more, so the last line has always landed by 0.84 (just before the settled frame at 0.86). Lines take no space until they arrive, so the block — centred on the content zone — re-centres, stepping up, as each one lands.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cmd` | the command typed above | leaving the demo `diff a b` prints it on any film |
| `leftLabel` | the `---` header, what the old side is | the demo `before` prints if omitted |
| `rightLabel` | the `+++` header, what the new side is | the demo `after` prints if omitted |
| `minus` | the removed lines, drawn first, in the second accent (red with no DNA) with dim text | 40px mono while the whole diff fits the content zone; more or longer lines step the type down (to a 22px floor) until it does — eight short lines set at about 28px on 16:9 and 25px at 1:1, 40px at 9:16. Long lines wrap inside the column. The demo is `old line` |
| `plus` | the added lines, drawn after all the removed ones, in the accent | as `minus`; together with `minus`, 1–8 lines. The demo is `new line` |
| `framed` | draws it inside an explicit terminal window | for anchor beats. The command sits in the title bar instead of being typed |

**Known traps:**
- Line timing was once a fixed 0.13 per line, so a sixth line was barely visible on the last frame and any after it was never drawn, silently. It is laid out for the count now.
- The lines are not paired into hunks: every `minus` line prints before every `plus` line.
- The removed-line red was a literal `#ff6b6b` whatever the DNA said. Under a DNA it is now the DNA's second accent (blue under `terminal`), so red/green is the diff's meaning only when the DNA's accents say so; the `-`/`+` sign and the dim/bright text carry it either way.
- The block is centred on the content zone, not the frame (12px higher than before at 16:9).

**Refuses:** no lines, more than eight across `minus` and `plus`, or lines too long to fit the content zone at the 22px floor.

**Reference:** `remotion/src/shots/TermDiff.tsx`
