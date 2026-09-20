# EdTimeline

**Identity:** an editorial chronology: kicker and rule, then dated entries arriving one by one — an accent date beside a serif title and an optional note — separated by hairlines.

**Use when:** lineage — how something evolved across a few dated moments, in a print register. **Not when:** there are more than six entries (it refuses), the order matters more than the dates (InOrder), or you want to travel along a timeline (TimelineTravel).

**Motion core:** the kicker and rule draw first; entries rise in one at a time, the first at 0.24, each over 0.14. The gap between entries is 0.16 for up to four entries and closes for five or six, so the last entry has always landed by 0.84 (just before the settled frame at 0.86).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `entries` | one row each: `{date, title, note?}`, 1–6 | date 40, title 52, note 30px while the list fits the content zone; a longer list, or notes that wrap, scale the whole chronology down by one factor (never below half) until it fits, centred in the content zone. A long note wraps, balanced |
| `kicker` | the small accent caps above the rule | '' draws the rule alone |
| `framed` | puts the chronology on a bordered surface panel | a card instead of type on the ground |

**Known traps:**
- A long list sets noticeably smaller: six dated entries with one-line Chinese notes came out at about 0.6× on 16:9 and 0.55× at 1:1. Keep notes short when the list is long.
- The list is centred on the content zone, not the frame: centred on the frame, a Chinese note's extra wrap pushed half its growth into the caption band.
- Omitting `entries` prints the placeholder '01 / first / note' rows; the default kicker is 'A HISTORY'.

**Refuses:** no `entries`, or more than six (the rows would arrive faster than they can be read); a chronology whose copy would need type below half size to fit the content zone at the frame's aspect.

**Reference:** `remotion/src/shots/EdTimeline.tsx`
