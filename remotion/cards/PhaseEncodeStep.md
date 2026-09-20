# PhaseEncodeStep

**Identity:** an MR diagram — on the left a phase-encode gradient blip steps from −Gmax to +Gmax, and at every step one more horizontal line lights in the k-space grid on the right while a counter reads "n / steps lines written": the grid filling one line per repetition.

**Use when:** an MRI beat whose claim is the serial bottleneck — k-space is written one line per TR, which is what makes MRI slow. **Not when:** the beat is about skipping lines (use UndersampledKspace), turning k-space into an image (use KSpaceToImage), or anything outside MR physics — the diagram's labels are fixed physics text.

**Motion core:** stepped, not eased — the current step is floor(t × `steps`), so across the whole clip the blip bar jumps to its next height and the next k-space line lights at even intervals, the newest line drawn brightest; the headline brightens from 40% to full over the first quarter. It never settles: the last line lights only in the final 1/`steps` of the clip.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `steps` | how many phase-encode lines the grid has | few (e.g. 8) give thick bands and big, countable jumps; many give a fast, fine fill. Integer 2–128 — past 128 the lines sit so close they merge |
| `label` | the headline across the top | a fixed 40px centred line; long text wraps across the full width |
| `accent` | the k-space lines, the grid's frame and the "/steps" in the counter | the colour of the data being written |
| `accent2` | the gradient blip bar | the colour of the cause; far from `accent` it separates blip from line |

**Known traps:**
- `steps` is a representative count, not the real matrix — the refusal message says to draw a representative count and name the real matrix in `label`.
- The lines fill top to bottom "for clarity" (the code's own note), not the centre-out order a real acquisition often uses.
- The diagram labels (`k-space`, `lines written`, `±Gmax · steps each TR`, `gradient blip`) are fixed English INTRINSIC_TEXT; no prop reaches them. `gradient blip` was once undeclared and slipped past onscreen_text_qa, which drops any string containing "gradient" as CSS.
- The ink is the film's: the line being written now, the counter, the blip's name and the headline take the DNA's `fg`, the smaller labels take `dim`, the blip's zero line takes `line`, and `accent`/`accent2` fall back to the film's two accents before their own cyan and violet. A prop still wins, and with no DNA every original literal prints as before. Until this was done the grid and its count drew white on white on a light-ground film (measured median 1.54:1). Omitting `label` prints "Phase encoding · one line per TR".

**Refuses:** `steps` that is not an integer from 2 to 128 (one step used to divide by zero and draw a NaN bar).

**Reference:** `remotion/src/shots/PhaseEncodeStep.tsx`
