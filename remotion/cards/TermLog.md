# TermLog

**Identity:** a `$ command` types and executes, and a build or pipeline log streams out one line at a time: `→` for a step, `✓` for done and `#` for a note. A caret blinks on the line currently printing.

**Use when:** the beat is a process running through its steps (a build, a pipeline, an agent working through a task) in a terminal-grammar film, and the sense of it happening line by line is the point. **Not when:** the steps need to be compared or scored (use `TermBars` or `TermTable`), or there are so many lines that the stream has to be read at a glance.

**Motion core:** the command types over 0.05–0.16 and the result appears from 0.20. Lines arrive in order, spread evenly from 0.24 across the next 0.66, each fading and sliding in from the left over 0.06. The caret follows the line being printed. Lines take no space until they arrive, so the centred block re-centres, stepping up, each time one lands.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cmd` | the command typed above | leaving the demo `build --pipeline` prints it on any film |
| `lines` | the log, `{text, kind}`, where `kind` is `run` / `ok` / `info` | `run` (and any unknown or missing kind) gets a `→` in the second accent. `ok` gets a `✓` in the accent. `info` gets a `#`, with the whole line dimmed. More lines means each prints faster. Type is a fixed 40px at loose leading, so a long line wraps and a long log grows tall rather than shrinking. The demo is `step one` / `done` |
| `framed` | draws it inside an explicit terminal window | for anchor beats. The command sits in the title bar instead of being typed |

**Known traps:**
- Nothing is fitted to the frame: 40px type at 1.85 leading and no row cap. A long log grows past the content zone at both ends instead of shrinking, so keep it to a screenful.
- Leaving `lines` or `cmd` out prints the demo copy on any film.
- `kind` defaults to a step. A line meant as the result needs `kind: 'ok'` or it reads as still running.

**Reference:** `remotion/src/shots/TermLog.tsx`
