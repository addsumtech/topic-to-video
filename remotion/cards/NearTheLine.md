# NearTheLine

**Identity:** the boundary a system learned crosses the field, bending; a band either side of it is where its answer is a coin-flip; the cases the film names sit where the film says they sit — some clear of the band, at least one inside it. Behind them, an anonymous field of cases, thinned inside the band.

**Use when:** the beat is about a system's own certainty — "it is sure in the middle and guessing at the edge", and from outside the guess looks exactly as confident as the certainty. **Not when:** the claim is about which MEASURE separates two populations — that is `OverlapSeparation`, a claim about instruments, where this is a claim about one system's answers. Not when the beat is a clean comparison: if nothing sits near the line, this register refuses, because the frame would argue the opposite.

**Why the boundary bends:** a ruled straight line is a RULE — someone wrote it and you can read it off. What a model has is a surface fitted to what it happened to see, so it wanders, and it wanders most where it saw least. Drawn straight it would illustrate the wrong object and make the register's own argument impossible: a rule's edge has no margin to be near.

**Motion core:** the boundary DRAWS on 0.06–0.34 (`drawOn`, easeOutCubic), and only then does the band fade up 0.36–0.56 — the line has to exist before the doubt around it can. The anonymous field arrives per dot on a hash-staggered window inside 0.02–0.50, so it settles as texture rather than appearing as an event. The named cases pop in order 0.50–0.78 (`easeOutBack`), the note 0.84–0.94. Nothing moves after that: the settled frame carries the whole argument, which is what the contact sheet and every reviewer read.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cases` | the cases the film points at — 2 to `MAX_CASES` (6), `{label, side, near}` | `side` is `'a'` or `'b'` and is the FILM's reading; `near` is the film's claim that this one is in the coin-flip band. The register decides neither |
| `sideA` | what the upper side is called | in the film's words |
| `sideB` | what the lower side is called | in the film's words |
| `kicker` | the spaced label over the field | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the field, in the film's voice | where to say what the margin MEANS — the frame shows it and does not name it |

**Known traps:**
- **At least one case must be `near`, and that is a refusal, not a warning.** With every case clear of the band the frame argues the OPPOSITE claim — that the system separates them cleanly — and a picture that argues the reverse of its narration passes every gate in this repo. If that is the beat, it is a comparison.
- The band's width is not a prop. How uncertain a model is near its own boundary is not something a beat measures, and a band a film could widen would be a number invented here and presented as a reading.
- The two populations are drawn FILLED on one side and as RINGS on the other. Two greys a shade apart is what the first render had, and at dot size that is one population, not two — which quietly removes half of what the register is arguing.
- A case clear of the band is clamped into the field. The push away from the boundary put a dot outside the plot where the boundary ran near the edge — measured on the first render, with a case sitting on the note.
- **No register-authored copy on the frame.** An earlier build printed "inside the band" under the marginal case: that ships English onto a Chinese film and is the register talking over the beat. The glow, the accent and the position inside the band already say it.
- The anonymous field is `@decor:` texture. It says one thing — "there were many cases" — which is the only thing a cloud of unlabelled dots can say honestly. It thins inside the band, because a model sees fewest examples where it is least sure, which is why the band is there at all.

**Refuses:** fewer than 2 `cases`; more than `MAX_CASES`; a `side` that is not `'a'` or `'b'`; a case with no `label`; and no case marked `near`.

**Reference:** `remotion/src/shots/NearTheLine.tsx`
