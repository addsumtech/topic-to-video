# WordRoll

**Identity:** one sentence with a slot in it, and the slot cycles: the alternatives roll through it like a split counter (or scramble into place, or flip), each held long enough to read, until it lands on the last and keeps it. An accent underline under the slot changes width with the word it holds.

**Use when:** "it is not X, not Y — it is Z", or "the same sentence is true of A, of B and of C": what is constant and what varies IS the argument, and the viewer should read the frame once and then watch one place. The order is the film's — the last option is the one the sentence lands on. **Not when:** the items are peers to be read together (a list register), or there is nothing that varies (`HeadlineReveal`).

**Motion core:** the sentence rises word by word through masks; the first option rises with it. Each change is a roll (stripe.com's digit roller: each glyph a strip that travels a full line through its clip, on (.33,1,.68,1), 0.38 s plus 0.028 s per glyph, with a breath of motion blur at the fastest point), a scramble (random glyphs of the copy's own script resolving left to right, changing on twos) or a flip (a split-flap's collapse and open, in 2D). The SCHEDULE gives each option time in proportion to what it takes to read it (`runtime/readingSpec.json`, the table the hold gate reads): the changes take their own turns and the rest is shared by must-read time, so a one-word option is not over-held while the three-word ending runs short. Each arrival may be cued (`options.N` moves earlier, never later, never before the one it replaces).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `options` | what the slot cycles through, in order; it lands on the LAST and keeps it | 2–6. Every option is set at one size (fitted on the widest), so the slot never jumps; more options means less time each, and the hold gate names any that cannot be read |
| `before` | the sentence before the slot | up to three balanced lines |
| `after` | the sentence after the slot, if it goes on | fades up word by word |
| `kicker` | a small spaced label over the sentence | not held to a reading time |
| `mode` | how the slot changes: `roll`, `scramble` or `flip` | roll is mechanical and calm; scramble is noisier and reads as "being decided"; flip is a departure board |

**Known traps:**
- Even spacing gave "here" and "on its word" the same time; at 6 s the demo's three came back from the hold gate a third of a second short. The schedule is now proportional to reading need and the register runs 7 s by default — in a film the beat's own length is what counts, and the gate measures that.
- The slot's clip is its own line box, so the space above it is where an outgoing word disappears; with a tight gap the exit read as the word sliding INTO the sentence above. The gap is kept.
- Set flush left at the column edge, a short sentence filled 43% of the frame from one side and the proof sheet called the other side dead. The block is centred on the widest thing it holds; the type inside stays flush left.
- QUIET by construction: measured 0.0005 motion, 3.5% ink, 0.018 light (product DNA) against 0.0037 / 12% / 0.135. Intercut with a dense register.

**Refuses:** fewer than `MIN_OPTIONS` (2) — one option is a sentence; more than `MAX_OPTIONS` (6) — past that each is gone before it is read; an empty option.

**Reference:** `remotion/src/shots/WordRoll.tsx`

**Measured:** 3.5% ink (clip median) · 17.4% footprint · 0.0005 motion · reach 0.844. Holds: clean at its own 7 s (1.37 / 1.40 / 2.53 s for here / there / on its word); at a 4 s beat the two one-word options cannot be read once (errors).

**Review:** NOT critic-reviewed — built and looked at by its author (roll / scramble / flip, 16:9 / 9:16 / 1:1, Latin and Chinese, three DNAs).

**Provenance:** motion-graphics. **Family:** C.
