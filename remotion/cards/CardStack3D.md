# CardStack3D

**Identity:** up to seven cards spring up one by one into a slightly messy pile at centre, then fan out into a tilted 3D arc so every card's icon chip (or its number) and label face the camera. A title rises in beneath the fan.

**Use when:** the beat is "a set of things, all in hand": 2–7 named peers (tools, sources, parts) gathered into one collection. **Not when:** the items are a sequence, carry numbers, or need detail beyond a short label.

**Motion core:** card i springs up with an overshoot over 0.06 + i·0.07 → +0.24 (a slight hashed tilt in the pile); the fan-out runs 0.58–0.92 with an ease in-out; the title rises 0.66–0.86. Then it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one card each: a string, or `{label, icon}` | card width follows the count (up to 360px), solved so neighbours clear each label and the fan fits both the width and the height of the zone. Three cards are big and airy; seven are narrow. Every label shares one size — 46px at most, brought down until every label fits the room under the chip (one line when that costs little), so on a narrow card or a 9:16 frame the labels get small rather than breaking a glyph per line. With `icon` the chip shows the icon, and without one it shows the card's number |
| `title` | the line under the fan | a fraction of the short side (about 62px at 1080), balanced wrapping |

**Known traps:**
- Omitting props prints the demo `Docs`, `Chat`, `Tasks`, `Code`, `Data`, `Calls` and `All of it, in hand`.
- The chip used to show only the index. A bare number still appears whenever `icon` is omitted, and it says nothing about the card, so give icons when the cards name things.
- Past failures: fixed 300px spacing hid a label's first character behind the next card (`「据汇总」`); the title sat wholly in the caption band; a six-card fan overran shorter zones; and a passed `bottom` on `AbsoluteFill` was silently ignored. The layout is now solved from both width and height.
- The title's box is budgeted for one line; a title that wraps grows upward toward the fan.
- The width solve does not count the swing of a rotated card, so at six and seven cards (seen on the 16:9 demo and at 9:16) the outermost cards' tops and chips reach past the frame edge; the labels stay inside.

**Refuses:** no `items`, or more than seven (past seven the solved card width drops under 240px and the labels break a word per line — split the set across two beats); a card with an empty label.

**Reference:** `remotion/src/shots/CardStack3D.tsx`
