# OpenQuestions

**Identity:** open questions surface one by one as a soft accent scan-light descends past each, then all stay lit together — no arrows, no order — under a kicker, with a footer and a blinking caret that says they are still unanswered.

**Use when:** an outlook or closing beat whose claim is "these are all still open" — 1–4 parallel questions. **Not when:** the questions are steps or have answers (use a list register), or there are more than four.

**Motion core:** the kicker fades in over the first fifth; the scan light descends from 0.1 until 0.14 + 0.2 per question, then disappears; question i lights over 0.12 + 0.2·i to 0.3 + 0.2·i, glowing hardest as the light passes it; the footer fades in over 0.78–0.92 and its caret blinks six times across the clip.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | the uppercase tracked mono line at the top | a short heading; always uppercased |
| `questions` | one centred 62px question each, 1–4, stacked | 1–2 sit high and airy; 4 fill the frame. Each wraps (balanced) inside 86% of the width; all rows are spaced for the deepest-wrapping question, and the block rises as a whole so the last one clears the footer and the caption band — when four long questions cannot keep their spacing under the kicker, the spacing tightens instead |
| `accent` | the scan light, the glow on each question, and the footer | the colour of the interrogation; unset it is green on every film. Must be a 6-digit hex (see traps) |
| `footer` | the accent line with the blinking caret, under the questions | a short "still unresolved"-style phrase; it is clamped above the caption band |

**Known traps:**
- Omitting the props prints demo copy: "The open questions", "How fast is too fast?", "Is it safe?", "Who gets a say?", "still unresolved".
- The questions light from a fixed dark grey to near-white and the kicker is a fixed grey — only the ground follows the DNA, so on a light DNA ground the lit questions lose contrast.
- `accent` gets alpha bytes appended (the scan glow and the text glow), so a named, rgb() or 3-digit colour breaks those effects.
- A question that wraps used to grow down into the caption band (Chinese at 1:1), and at four questions on 16:9 the footer printed across the last question; the block now rises to clear both, so several long questions push the stack up toward the kicker and, at the limit, closer together.

**Refuses:** no `questions`, or more than four (the fourth is lit just as the footer lands; a fifth would never finish lighting — split them across two beats); an empty question.

**Reference:** `remotion/src/shots/OpenQuestions.tsx`
