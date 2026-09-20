# TermThink

**Identity:** a `$ command` types, a `❯ question` prompt appears, and a dashed `<think>` block streams reasoning lines one by one. The block then closes (`</think>` brightens) and a bold `= answer` line lands under a blinking caret.

**Use when:** the beat shows reasoning before an answer, such as a model thinking through a question or a chain of steps that ends in one result, in a terminal-grammar film. **Not when:** the steps are a process log with no single answer (use `TermLog`), or the reasoning is long prose (the whole stack shrinks to fit).

**Motion core:** the command types over 0.05–0.16 and the question appears with the result from 0.20. The think box fades in over 0.28–0.38. Reasoning lines arrive evenly across 0.36–0.82, each fading and sliding in over 0.06. They take no space until they arrive, so the box grows and the centred stack re-centres upward as they land. At 0.86 the closing tag switches to full strength, and the answer, which fades in over 0.84–0.92, turns from dim to full ink.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cmd` | the command typed above | leaving the demo `hermes --mode hybrid` prints a model name on any film |
| `question` | the `❯` prompt line | wraps. The demo is `solve it` |
| `think` | the reasoning lines inside the box, each with a `│` gutter | more lines print faster and make the stack taller. The whole stack (question, box, answer) starts at 40px and steps down until it fits the zone, but never below about a third of that. The demo is `reason…` |
| `answer` | the `=` line under the box, bold | wraps. The demo is `answer` |
| `framed` | draws it inside an explicit terminal window | for anchor beats |

**Known traps:**
- The stack used to be a fixed 40px. Chinese reasoning that wrapped past the zone put the answer 89px inside the caption band at 1:1, because the block is centred on the frame, not on the content zone. It is now sized against the nearer zone edge.
- The shrink stops at 0.36× (about 14px). A reasoning stream that still does not fit at that size overflows instead of shrinking further, so trim the lines.
- LIBRARY.md once advertised props this register never read, and films authored from it printed the demo defaults. These five props are the whole interface.
- The closing tag and the answer colour switch at 0.86 as a hard change, not a fade.

**Reference:** `remotion/src/shots/TermThink.tsx`
