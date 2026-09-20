# ConveyorBelt

**Identity:** labelled cards ride a scrolling belt left to right, pass under a stamp press that drops and flashes, and leave the stamp flipped into filled "done" cards.

**Use when:** the claim is "it just processes everything" — an assembly line where every item comes out finished. **Not when:** some items fail or take different routes (every card that crosses the centre is stamped done), or the list is long (cast a list register).

**Motion core:** never still. The title rises (0.03–0.16); the belt treads scroll the whole clip; the cards, evenly spaced along the run, travel continuously (each covers 0.85 of the run over the clip) and flip to the done state the moment they cross the centre; the press drops as a card comes within reach of the stamp and flashes on contact.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one card per entry | few items leave long gaps on the belt; more pack it. Label type steps down by length (30 → 23 → 18 → 15px) and wraps; the card grows taller rather than spilling |
| `title` | the spaced heading above the belt | uppercase and widely tracked without a DNA; with one, mixed case and tighter |
| `doneLabel` | the sub-line on a stamped card | steps down by length; a sentence fits but shrinks |
| `queuedLabel` | the sub-line on a card still waiting for the stamp | `''` leaves waiting cards with just their label |

**Known traps:**
- The waiting word used to be a literal `queued`, so a Chinese film's belt read 「✓ 已处理」 on one side of the stamp and English on the other. It is `queuedLabel` now — pass it in the film's language.
- The belt has a capacity: a card needs 216px of run, so ten fit on a 1920-wide frame and seven on a 1080-wide one. Past that the cards used to overlap; now it throws.
- The belt is a loop: a card that leaves on the right re-enters on the left unstamped, so an item can be seen waiting again after it was shown done.
- Every default is demo copy ('ticket', 'email'…, 'Everything, handled', '✓ done', 'queued').

**Refuses:** an empty `items`; more items than the frame's width holds.

**Reference:** `remotion/src/shots/ConveyorBelt.tsx`
