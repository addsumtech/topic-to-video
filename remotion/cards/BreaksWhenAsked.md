# BreaksWhenAsked

**Identity:** a statement set as one printed line, several readers sweeping across it and each reporting it whole, then a single question arriving alone — and the clause nothing supports shears off along the seam, pale, leaving a ragged edge where it sat.

**Use when:** the beat's claim is about a MEDIUM rather than about an item — every check in the chain reads the same still surface, so a failure that only exists under interrogation is invisible to all of them at once, and adding readers makes it worse rather than better. A claim on a page that dies in the interview; a spec that passes review and fails in production; a policy that reads fine and collapses at the counter; a metric that survives every dashboard and dies in one user session. **Not when:** the beat points at something already visible and says "this one matters" — that is `FocalIsolation` or `RackFocus`. Not when the claim needs a process to point inside ("one moment in a run") — that is `HeldInstant`, whose measured motion also sits in the library's stillest third and should not carry a film's summit.

**Why the readers must leave it WHOLE.** If a reader found the flaw, the register would be arguing that review works and this one was unlucky. The claim is the opposite: the surface does not stammer, so no number of readers changes the outcome. They sweep, they pass, and only the question breaks it — the fracture is caused by the question and by nothing else, which is the whole argument and is legible with the caption hidden.

**Motion core:** the line sets, then the readers sweep on `cadenceAt` — quick, overlapping, each leaving a pass mark. The question arrives into silence after the last of them. The shear runs on `easeOutExpo` so the break is an event rather than a slide, and the fallen clause is capped by the room left on the stock (a page clips, as a page does — the first render dropped it off the bottom of its own sheet). `DURATION` is 210 frames / 7s because the break has to be allowed to land and then be read.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `parts` | the statement in the pieces it would come apart into — 2 to `MAX_BREAK_PARTS` (4) | the film says where it gives way; this register never picks the weak clause itself |
| `breaks` | the index of the clause that shears off | required once a film passes its own `parts` — WHICH clause fails IS the claim |
| `readers` | the checks that pass over it — up to `MAX_BREAK_READERS` (4) | naming them matters: three named readers passing is stronger than "review" passing |
| `question` | the one question that lands | open, in the film's words — a leading question would be a different argument |
| `passLabel` | what a clean sweep is called | e.g. 「读得通」 — the words the readers leave behind |
| `breakLabel` | what the fracture is called | e.g. 「守不住」 — it labels the edge, not the fallen piece |
| `kicker` | the spaced label over the sheet | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line beneath the sheet, in the film's voice | where to say what the break MEANS — the frame shows it and does not name it |

**Known traps:**
- **Fewer than two parts throws** — nothing can break away from nothing.
- **A film that passes its own `parts` must pass `breaks`.** Defaulting it would make the register choose which clause is unsupported, which is the film's judgement and never the register's.
- No readers, or no question, throws: without readers there is nothing the failure was invisible to, and without a question the break has no cause.
- Measured `motion_p75` **0.0096 — the highest in the library**, so it is a legitimate home for a film's summit. That is also a reason not to spend it on a quiet beat.

**Reference:** `remotion/src/shots/BreaksWhenAsked.tsx`

**Provenance:** print-editorial. **Family:** C. **Ground:** `bg` (`DNA_GROUND_TOKEN`).
