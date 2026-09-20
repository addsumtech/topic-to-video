# PaperSlot

**Identity:** on matte paper stock, a scored card carries one slot per item, and cut paper tags — each with a printed colour band, a punch hole and its label — drop one by one into their slots, each landing a hair off straight; the hub's name (and a note) sits under the card.

**Use when:** the claim is "these all go into one simple thing", said by hand rather than by machine — a hub and 1–6 parts, warm and made. **Not when:** the fit should feel engineered (the machined 3D version is PortRail), there are more than six parts, or the film wants its own dark ground here — this register always prints on light stock.

**Motion core:** the card fades in over 0–0.14 and the hub title over 0.04–0.20; tag i drops from above into its slot with a slight overshoot over 0.10 + 0.42·i/n to that plus 0.26, so the tags land one after another; the note fades in over 0.66–0.84; then everything holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `hub` | the name of the one thing, under the card | fitted to about 60% of the width and balanced — a short name is a bold title, a long one shrinks |
| `items` | one tag and one slot each | 1–2 give wide, calm tags; 6 give a row of narrow ones. Every tag shares ONE label size — the largest that fits the longest label — so one long label shrinks all of them |
| `note` | a dim line under the title | a short supporting line, balanced across lines |

**Known traps:**
- Omitting the props prints demo copy: `One slot` over Docs, Chat, Mail, Calendar, Wiki, DB.
- A dark DNA ground is REJECTED — the register falls back to its own paper stock and its own dark ink. The ink used to follow the DNA even then, which printed white text on paper at 1.22:1 under every dark preset; don't try to force the film's ground or ink here.
- Entering tags used to start cut off by the top edge; their start is now held inside the frame.

**Refuses:** no `items`; more than six (at six on a 9:16 frame a tag is ~107px and its label already sets smaller than the note, and the printed bands come from a six-tone palette — a seventh would repeat the first); an empty entry.

**Reference:** `remotion/src/shots/PaperSlot.tsx`
