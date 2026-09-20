# SplitFlap

**Identity:** a Solari departure board — rows of dark flap tiles riffle through random characters and settle one by one, left to right and row by row, to spell the message, each landed character glowing in its row's tone under a small spaced header.

**Use when:** a status or announcement moment — "the board updates": what is live, done or waiting, a destination or a result, with a mechanical, premium feel. Rows can carry different tones so two states read as two states. **Not when:** the copy is a sentence (it is one tile per character), or there are many rows.

**Motion core:** from the first frame every unlanded tile flickers through random glyphs; tiles settle from 0.14, staggered by column and by row (with slight jitter), the schedule compressed so the LAST tile lands by 0.80. The settled board holds to the end.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | the small, very widely spaced header above the board | a status heading; omitted, the demo `STATUS · TODAY` prints |
| `rows` | the board's lines — each a string, or `{text, tone}` with tone `accent`, `accent2`, `dim` or `fg` | one tile per character, each row centred on the widest. Tile size shrinks so the widest row fits the frame width, so long rows make small tiles; more rows make a taller board. A tone lights that row in the film's DNA colour — two tones make two states. Omitted, the demo rows (a product name and `DELIVERED`) print |

**Known traps:**
- The cascade used to be an unbounded sum, so any tile past column 17 of row one (11 of row three) never landed and the board flickered to the last frame — real Chinese rows ended more than half unresolved. It is now normalised to the board; don't reintroduce a fixed per-tile offset.
- Every row used to be one hardcoded amber, erasing a beat whose whole point was two states (green = working, grey = waiting). Use `tone` per row when rows mean different things. Without a DNA, tones are ignored and every row is amber.
- Only width is fitted: the board is centred on the frame, not the content zone, so at 1080p a board of four or more full-size rows reaches into the caption band.
- The riffle draws Latin letters, digits and symbols whatever the row's language; only the settled characters are the film's.

**Reference:** `remotion/src/shots/SplitFlap.tsx`
