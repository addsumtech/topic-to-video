# StateSheet

**Identity:** a contact sheet of real pictures prints cell by cell in reading order, each captioned with the state it is; then one cell, the state the thing is in now, lifts and takes the accent border, a strip of sibling members fades in underneath, and a note closes it.

**Use when:** the claim is "this one thing is actually N different pictures" (a character's states, a typeface's weights, a component's variants, a machine's error screens) and the film has those pictures as files. **Not when:** all the film has is names. A list of names can say how many; it cannot show that each one is a different drawing, and without the pictures this register has nothing to print (a list or `TermTree` carries names).

**Motion core:** title and directory line rise in 0.02–0.18. The cells land in reading order across 0.10–0.62, each rising and fading in over about 2.2 cell-slots, so neighbours overlap like a sheet coming off a printer. The marked cell lifts and glows in 0.66–0.82, the family strip fades in over 0.68–0.86, and the note arrives in 0.74–0.90. After that the frame holds. Nothing moves as a whole frame.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the one thing all the pictures are, set above the sheet | sized to fit one line across ~86% of the width, so a longer title comes out smaller rather than wrapping. Empty removes the headline row and the sheet grows into the space |
| `dir` | the directory or collection line under the title, in the mono face | one line only: a long path is cut with an ellipsis |
| `cells` | the pictures, `{src, label?}`, with `src` a file under `public/` | the column count is solved per count and aspect for the largest square cells, so 3 cells are big tiles and 20 are thumbnails, and a short last row is centred. There is no cap, because the count is the argument. A `label` wider than its cell is cut with an ellipsis, so more cells leave room for fewer letters |
| `mark` | the cell that is the current state (0-based) | that cell lifts, gets a 2px accent border, a glow and an accent label. `-1` or absent leaves the sheet even. An index past the end marks nothing and raises no error |
| `family` | the other members this one belongs to, `{src, label?, mark?}`, as a strip under the sheet | the sheet says "this is N pictures", the strip says "and it is one of M". The strip solves its tile size and wraps to more rows as members are added; past 12 members its labels drop a size. Every row it adds is height the sheet loses. `mark: true` gives a member the accent edge |
| `note` | one line under everything | fades in last. The layout reserves about one line of height for it, so a note that wraps hangs below the content zone |

**Known traps:**
- The pictures must be static. An animated SVG in `<img>` runs its own clock off wall time, not Remotion's frame, so the same frame renders differently twice. Strip the animation before handing the files over; the register cannot check this.
- It was built because a beat about "seventeen states each" drew the filenames as a terminal tree while the pictures sat in the repository. If all you have is names, you do not have this shot's material.
- Entries with no `src` are dropped without a message, so the sheet can show fewer cells than the array holds.
- The family strip used to be one fixed row, and at twenty members it would have run 1940px across a 1920 frame. It wraps now, but a long family pushes the sheet into thumbnails.

**Refuses:** `cells` empty, or every entry missing a `src`.

**Reference:** `remotion/src/shots/StateSheet.tsx`
