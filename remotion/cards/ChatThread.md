# ChatThread

**Identity:** a messaging thread. The user's bubbles sit right in the accent colour; the other side's bubbles sit left on the surface colour beside a gradient avatar. Each message springs up at its own moment, and a three-dot typing indicator shows just before each reply.

**Use when:** the beat is a short exchange (a request and its replies, or a support conversation) and the timing of each turn matters. **Not when:** one answer with sources is the point (use `AnswerStream`), or speakers need names (there are no name labels, only two sides).

**Motion core:** timing is the film's: message i appears at its `at` fraction of the clip, rising 30px with an overshoot over 0.22; a typing indicator shows during the 0.12 before each `wb` message, with its dots pulsing. Already-shown bubbles stay.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `messages` | the thread: `{side: 'you' \| 'wb', text, at}` | `'you'` goes right in the accent, `'wb'` left with the avatar; any other `side` throws. `at` is 0–0.9 (later is still fading in on the last frame, so it throws). The type (46px base) scales down until the whole thread fits the content zone, with a floor at 0.34 of full size; a thread that does not fit even there throws. A short thread is big and airy, and a long one is small and dense |

**Known traps:**
- Omitting `messages` prints the demo WorkBuddy exchange (`Build the Q3 board deck…`, `Done ✓ — 24 slides…`).
- Bubbles stack in ARRAY order, but appear at their `at`. Keep `at` increasing down the list, or a later-timed bubble will pop in above ones already shown and push them down.
- A thread too long for the 0.34 floor THROWS (it names the px it needed and the px the zone holds). Split the exchange over two ChatThread beats, or shorten it. A nine-turn Chinese exchange of 30–45 characters a turn needed 773px of the 710px a 16:9 frame holds.
- The fit is an ESTIMATE, and emoji-heavy text beats it (an emoji counts 0.72em and renders wider). If a thread overflows anyway, the column is bottom-anchored, so the OLDEST message is the one clipped off the top and the newest stays in view. It used to be the reverse (laid out from the top, so the last reply was the one cut off).
- A message with no `text`, no `at`, an `at` outside 0–0.9, or a `side` that is not `'you'`/`'wb'` throws. Each of these used to draw nothing or draw on the wrong side, silently.
- The column used to scale by width only; at 1:1 the last message (the one the exchange is for) ran 28px into the caption band. It now fits by estimated height, too.
- The typing indicator shows only for the `wb` side.

**Reference:** `remotion/src/shots/ChatThread.tsx`
