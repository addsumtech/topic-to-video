# AnswerStream

**Identity:** a question slides up at the top; beneath it an answer types itself out character by character, and each `[n]` citation marker turns into a numbered accent chip as it streams. A row of numbered source cards (path above, title below) pops up under the answer.

**Use when:** the beat is "ask a question, get a grounded answer with its sources", in the language of an AI search engine. **Not when:** there are no real sources to cite, or the exchange has several turns (use `ChatThread`).

**Motion core:** the query rises and fades in 0–0.14; the answer types 0.20–0.78 on an ease-out clock, with a caret visible while it streams; source card i rises with an overshoot starting at 0.40 + i·0.08, each over 0.22. It holds from about 0.8.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `query` | the question, beside a sparkle icon | fixed 62px, not fitted. One line reads as a search box; a long question wraps inside the column (up to 1300px) |
| `answer` | the streamed paragraph; `[1]`…`[9]` become chips | fixed 50px/1.5, not fitted. A short answer finishes typing early and reads as instant, a long one types quickly and fills downward |
| `sources` | one card each: `t` (title) and `d` (path or domain) | cards share one row equally. Two or three sit wide and calm; more make each card narrow, so titles wrap and the row lifts to stay above the caption band |

**Known traps:**
- Omitting props prints the demo cost-cutting exchange (`How do we cut Q3 costs?`, with three finance sources).
- Only single-digit markers become chips: `[10]` prints as literal text. Nothing checks that a chip's number matches a source card, so the film has to keep them in step.
- The query and answer tops are fixed (y 150 and 300) and the source row sits at y ≤ 600. A query that wraps past two lines runs into the answer, and an answer past four lines runs into the source cards.
- The source row's top used to be fixed. Chinese titles wrap where English ones don't, and the row reached 101px into the caption band at 1:1. It now rises by the height its tallest card needs.
- Text colours are fixed pale navy and the ground is a navy radial into the DNA background; only accent, background and surface follow the DNA.

**Reference:** `remotion/src/shots/AnswerStream.tsx`
