# CursorStory

**Identity:** a list of rows on the film's own ground; one hero cursor glides to a row, a ⌘K chip fires, a command palette jump-cuts in, ↵ fires, and a result toast pops once the work has been cut past.

**Use when:** a single guided keyboard action on a list the film names — "one command and it is done". **Not when:** there is no row the action is about and no result to report (the palette and chips then carry nothing), or the action is a typed checklist (CommandSummon) or a tour of a screen (PointerTour).

**Motion core:** the cursor moves in three eased legs — into the list (0.08–0.30), down to the target (0.34–0.50), along that row (0.56–0.74). The ⌘K chip shows 0.30–0.44; the palette cuts in 0.32–0.56 with the list dimmed under it; the ↵ chip shows 0.50–0.64; rows marked done turn green after 0.60; the toast pops 0.74–0.86. Chips and palette hard-cut; only the cursor and the toast ease.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | the rows — a label, or `{label, done}` | 1–8. When they do not fit the content zone the rows close up (a smaller pitch) rather than leaving through the top. `done: true` turns that row's dot green after Return; nothing else is finished |
| `target` | the index of the row the cursor acts on | the row that highlights, carries ⌘K and where the cursor comes to rest; omitted or `null` = the cursor works from the gutter and never parks on a row |
| `command` | the text typed into the palette | with none the palette still cuts in, as an empty field with a caret |
| `doneLabel` | the big green line in the result toast | no default: with neither this nor `doneNote`, no toast is drawn |
| `doneNote` | the smaller line under it | same |

**Known traps:**
- The hovered row used to come from the clock, so the highlight and ⌘K fell on the FOURTH item of any list and every row up to it turned green — a six-vendor film "finished" four vendors nobody named. `target` and per-row `done` are the film's now.
- The toast once printed the literal `Cleared · 6 tasks` / `in one keystroke` — English, and a count nobody supplied. It is props with no default.
- On default props the toast container once drew an empty box over the list; no type or luminance gate could see it — it took looking at a still.
- Row type is a fixed 40px and the pitch assumes one line per row; a label long enough to wrap makes its row taller than the pitch allows.
- The ⌘K and ↵ glyphs are fixed, so the beat always reads as a Mac-style command palette.
- Every surface was a dark literal, and the selected row was not a surface at all — an 11%-alpha accent with nothing under it, so the row it painted was whatever the ground happened to be. On a light film that is the paper, and the row's label, its dot and its ⌘K were all drawn near-white on near-white: 31.0% of the register's ink under 3:1 on a warm-white ground, in one connected region 0.47% of the frame, and that region is the row the shot is about (the rest of the list read at a median 13.00:1). The rows, the palette and the toast take the DNA's container tokens now, the selection is mixed into the card's fill at the same 0.11, and the ground's radial no longer keeps a near-black inner stop over a paper film. The green "done" dot keeps its hue and moves only its exposure; the pointer keeps its white-with-a-dark-outline, which is what a pointer is on any ground.

**Refuses:** fewer than 1 or more than 8 items; an item with no label; a `done` that is not a boolean; a `target` that is not an index into the rows.

**Reference:** `remotion/src/shots/CursorStory.tsx`
