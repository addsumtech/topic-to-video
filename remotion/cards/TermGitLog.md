# TermGitLog

**Identity:** a `git log --graph` command types and executes, and a commit history prints top-down, newest first. Each commit is a `*` node with hash, `(ref)` and message, joined by `│` connectors, and the top commit's node glows and is marked `← HEAD`.

**Use when:** the beat is a version history (releases, iterations, what changed when) in a terminal-grammar film, and the newest state is the one that matters. **Not when:** the history has more than eight steps (it refuses), or its points need dates on an axis (a timeline register).

**Motion core:** the command types over 0.05–0.16 and the result appears from 0.20. Commits then arrive from 0.24, each fading and sliding in from the left over 0.13, with its connector below it — 0.16 apart for up to three commits and closer for more, so the last has always landed by 0.84 (just before the settled frame at 0.86). Rows hold their space before they arrive, so the block does not jump; it is centred on the content zone.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cmd` | the command typed above | leaving the demo `git log --oneline --graph` prints it on any film |
| `commits` | the commits, newest first: `{hash, ref, msg}` | the first entry is HEAD. The ref column is as wide as the widest ref, counted in mono cells, so a Chinese ref gets its full width. Rows are 38px and shrink to fit the widest row and the content zone's height, down to a 22px floor (eight commits stay at 38px on 16:9; on a 1080-wide frame the width decides first — about 31px for the Chinese test log). Past that floor, long messages are clipped with an ellipsis rather than shrunk further (a log truncates). Leaving the demo in place prints `a1b2c3d (v2) second` / `e4f5a6b (v1) first` |
| `framed` | draws it inside an explicit terminal window | for anchor beats |

**Known traps:**
- Commit timing was once a fixed 0.16 per commit, so a fifth commit was not quite settled on the last frame and a sixth or later was never drawn, with no error. It is laid out for the count now.
- A commit without a `ref` still prints empty parentheses `()`.
- The fixed 38px row once ran a Chinese message 345px past the frame edge and `← HEAD` 510px past it, because `white-space: pre` cannot wrap. The size is now fitted to the width it is actually given, and messages are clipped with `…` at the 22px floor.
- `← HEAD` is the form's own label and always prints, in English, on the first commit.

**Refuses:** no `commits`, more than eight, or more commits than the content zone holds at the 22px floor.

**Reference:** `remotion/src/shots/TermGitLog.tsx`
