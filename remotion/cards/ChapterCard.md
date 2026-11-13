# ChapterCard

**Identity:** a chapter of the argument opens. `01 / 04` and the chapter's name sit at the top over a progress hairline (this chapter's share drawn in the accent); one short statement rises unit by unit through its mask — a Latin word or one CJK character — and its accent span is inked in the accent once it lands. The card holds still (no push: a slow scale makes type strokes shimmer) and its words rise out at the end.

**Use when:** the film turns to a new part of its argument (a `new-topic` seam) and one line names it. 3-5 per film is the rhythm. **Not when:** two adjacent beats; the beat has content to show (that is a product or diagram beat).

**Motion core:** units land 3 frames apart (CJK faster, the whole line within ~0.9 s), each rising over 12 frames on `snappy`; the accent fill sweeps after the last unit lands; the numbering fades in over 10 frames; the hairline draws over 4-22; the words leave in the last 9 frames.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `text` | the statement; `*…*` marks the accent span | ≤ ~8 words / ~16 CJK characters; longer wraps to two lines and reads as a paragraph |
| `kicker` | the chapter's name beside the number | one or two words, set in mono capitals |
| `index` | this chapter's number | with `total`, draws the progress hairline |
| `total` | how many chapters the film has | the hairline's scale |
| `size` | the statement's size at 1080 on the short side | 104 by default; smaller reads as a caption, larger crowds the frame |

**Known traps:**
- The statement sits in the zone above the caption band; the burned caption still runs under it unless the line IS the narration.
- Omitting props prints the demo `One *statement* opens each chapter.` (Chapter, 01 / 03).

**Refuses:** nothing; an empty `text` draws only the ground and the numbering.

**Reference:** `remotion/src/shots/ChapterCard.tsx`, `remotion/src/promo/Cards.tsx`
