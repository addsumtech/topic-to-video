# ProfileGrowth

**Identity:** a hatched ground line draws across, then one cross-section rises out of it at successive sizes — each state grows up from the same line, the earlier ones left behind as faint ghosts inside the later ones — until the last, accent-coloured profile lands with a caption saying what it became.

**Use when:** the claim is "it became something else by being ENLARGED, not replaced" — one object widened step by step (a footprint, an allocation, a scope, a pit, a caseload), where seeing every earlier size inside the current one is the point. **Not when:** separate objects pass through stages (a pipeline register), two states are compared (a before/after register), or two different things share the same ground (use `PlanPalimpsest`).

**Motion core:** kicker 0.02–0.16; the ground rule and its hatching draw left to right 0.08–0.28; states rise one after another from 0.20, each taking about 0.52/*n* of the clip and growing upward from the ground line with its label riding its top edge; the last state's caption and the note land 0.80–0.94, then the frame holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | the small spaced caps line above the field | a heading; omitted, the demo `THE SAME SECTION, WIDENED` prints |
| `states` | the profiles in order: `label`, `w` and `h` as fractions of the field in (0, 1], optional `note` | 1–5 states; each is drawn at exactly its own size, centred on the same ground line. Two or three read as a clear progression, five as a nest of ghosts. The last one is drawn in the accent with a heavier edge, and ONLY its `note` is shown — as the large caption under the plate. Omitted, three demo states (`at first` / `wider` / `and then this`) print |
| `ground` | a small mono label on the ground line ("street", "grade") | empty draws no label; a word names what the section is cut into |
| `note` | a small dim line under the last state's caption | a quiet qualifier; long copy wraps and the caption block is lifted to stay above the caption band |

**Known traps:**
- Profiles used to default to one invented size, so a film listing states by name got identical rectangles under a register about growth; `w` and `h` are now required and the size IS the claim.
- A sixth state used to be silently cut — the last state is what the thing became, so more than five now throws.
- Labels used to be hidden under the next, larger fill; fills are drawn first and every label on top. Keep that order.
- A `note` on any state but the last is never drawn.
- Nothing checks that each state is larger than the one before; a shrinking state is drawn as given, and states of near-equal height put their centred labels on the same line.

**Refuses:** fewer than 1 or more than 5 states; a state without a finite `w` and `h` in (0, 1].

**Reference:** `remotion/src/shots/ProfileGrowth.tsx`
