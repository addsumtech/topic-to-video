# MagazineSpread

**Identity:** an editorial magazine cover sets itself on paper — the serif masthead drops in, a hairline rule draws across, a colour plate slides in from the right, a giant headline sets word by word in the left column, then an italic standfirst and an optional numbered contents list.

**Use when:** a feature or chapter-opener beat that names a story with a headline and one standfirst — the print-editorial, "cover story" register. **Not when:** the beat carries data, steps or comparisons (the cover has no place for them), or the headline is a long sentence.

**Motion core:** masthead drops 20px into place over 0.05–0.34 and the issue line fades in over 0.28–0.44; the rule draws left to right over 0.2–0.5; the plate slides 120px in from the right over 0.34–0.6 and its caption appears over 0.5–0.66; headline words rise in one at a time from 0.44, each 0.06 after the last — or closer together when that would not land the last word by 0.90; the standfirst fades in over 0.72–0.9 and the contents over 0.8–0.95.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the masthead, top left | fitted on one line to the room left of the issue line — a short name stays big, a long one shrinks |
| `headline` | the giant feature headline in the left column | fitted as a block to the column between its top and the standfirst, so a longer headline shrinks rather than overflows. Split on spaces: Latin sets word by word; Chinese (no spaces) sets as one piece |
| `deck` | the italic standfirst under the headline | wraps in the headline's column; a longer deck takes more lines and pushes the headline's room up, shrinking the headline |
| `issue` | the mono line at top right, repeated as the plate's second caption line | a short "ISSUE 07 — 2026"-style line; a long one narrows the room the masthead is fitted to |
| `sectionLabel` | the first line of the white caption on the colour plate | a section word ("FEATURE", "专题") |
| `contents` | a numbered index along the bottom of the text column, 0–6 entries | entries wrap into as many rows as they need with accent numerals, and the standfirst sits on the index's top (the headline's box yields to the rows); none given draws nothing there |
| `accent` | the plate's gradient start and the contents numerals | overrides the DNA accent; unset it takes the DNA accent, else editorial red |

**Known traps:**
- Omitting the text props prints demo copy: `OBLIQUE`, "The quiet revolution in how we work", "A field guide to the tools reshaping the day", `ISSUE 07 — 2026`, `FEATURE`.
- A long headline sets fast: the word stagger is squeezed so the last word lands by 0.90 — from six words on it tightens below 0.06 (0.04 at eight words, 0.02 at fifteen), so a long headline arrives as a quick run rather than word by word.
- The index's rows are estimated with a conservative advance, so a long index can reserve one row more than it draws, pushing the headline up a little with a gap above the standfirst.
- The standfirst and contents text are a fixed dark brown while the paper takes the DNA's `bg`; on a dark DNA ground they lose contrast.
- The folio used to invent a domain from the title (`{TITLE}.CO — 01`) and the plate caption used to be a literal `FEATURE` no prop reached; both are gone — don't reintroduce either.

**Refuses:** more than six `contents` entries (a cover carries an index, not a table of contents — give it its own beat); an empty entry.

**Reference:** `remotion/src/shots/MagazineSpread.tsx`
