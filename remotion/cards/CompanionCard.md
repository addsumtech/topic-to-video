# CompanionCard

**Identity:** a companion — an abstract sitting shape, or the subject's own picture via `src` — sits beside a status card about something happening elsewhere; the card's state turns once on its own, then a cursor presses the card and a line says where that press takes you back to.

**Use when:** the beat is "a small thing here reports on a larger thing elsewhere, and is the way back to it" — a build agent, a long export, a CI run. **Not when:** there are three or more states (that is a dashboard, not a glance), or the claim is status only with no way back — the form's point is `returnsTo`.

**Motion core:** three moments that never overlap — the card and companion settle (0.06–0.26), the state turns over 0.12 of the clip starting at `turnAt` (default 0.40; the word crossfades through the swap), the cursor comes in from below-right and presses around `pressAt` (default 0.72), and the return line rises just after the press. In portrait the companion sits above the card. Until the turn, the companion's lit part and the status dot breathe; they go still as the state turns, so the stillness reads as the work finishing.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `task` | the card's headline — what is being reported on | shrinks to fit the card's width; the card's height follows the wrapped lines |
| `states` | the two states, `[before, after]` | the first is set in the accent and breathes; the second is dim and still. Only the first two are ever drawn |
| `returnsTo` | the line under the card after the press, behind a ↩ | the form's payoff; empty draws no line, so the press lands on nothing |
| `note` | a dim line under the card for the rule behind the return | drawn whenever given, with or without `returnsTo` |
| `turnAt` | when the state STARTS to turn (t, 0.2–0.8) | put it on the word that names the new state — a board writes `{"cue": "灰色"}` and the renderer places it; early, the card contradicts the sentence still being spoken |
| `pressAt` | when the cursor presses (t, at least `turnAt` + 0.14) | `{"cue": "点一下"}` puts the press on the words that say it; too close to the turn and the press reads as causing it |
| `src` | the companion's own picture, served from the film's folder | a real character is drawn at twice the abstract shape's size so it can be recognised; omitted, the shape stays small and faceless |

**Known traps:**
- `returnsTo` defaults to empty: omit it and the cursor presses a card that leads nowhere — a status light, not this form.
- The turn used to sit at a fixed 0.40–0.56 of the clip, and on a delivered film the card went grey while the voice was still saying 「绿色的工作中」. Cue `turnAt` / `pressAt` to the narration.
- The press ring is the neutral ink, not a state colour: an accent ring once made the card glow "working" over a grey "waiting" dot and contradicted its own colour key.
- The breath was once described in a comment and never computed, and `register_energy` measured the shot as a still; it is real now, and stops by design at the turn.
- Omitting `task` / `states` prints the demo copy ('the long run', 'working' / 'waiting for you').

**Refuses:** an empty `task`; anything but exactly two `states`; `turnAt` outside 0.2–0.8 or `pressAt` less than 0.14 after it (or past 0.95).

**Reference:** `remotion/src/shots/CompanionCard.tsx`
