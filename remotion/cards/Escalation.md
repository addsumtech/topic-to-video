# Escalation

**Identity:** one time rule across the frame, with marks landing on it as the gaps between them close. The last mark takes the accent and stands taller, and the rule keeps going past it into empty ruling.

**Use when:** the beat's claim is that something kept happening and happened MORE OFTEN — incidents before an outage, releases shipping faster, revisions before a deadline, a cost compounding, a symptom recurring. **Not when:** the claim is that a quantity got BIGGER (that is `EdStat` / `TermCounter` / `ValueStagger` — a number doubling is a size problem, an interval halving is a rate problem, and a rising line is routinely mistaken for the second when it means the first), or when there are only two events to compare (`VersusSplit` / `RackFocus`).

**Motion core:** the kicker fades 0.02–0.12, the rule draws across 0.04–0.26 (easeOutCubic). The marks then land on `cadence(t, n, accel)` from `runtime/motion` — the same function that decides WHEN each one arrives also decides WHERE it sits, so the rhythm a viewer hears and the spacing a viewer reads are the same evidence and cannot say two different things. Each mark pops with an easeOutBack. The note fades in 0.82–0.92.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `marks` | the events, `{label, when?}` — 3 to `MAX_ESCALATION_MARKS` (7) | `label` is REQUIRED; a tick with nothing beside it is furniture. `when` is optional and is the film's own words for the date ("3月", "v2.1", "第 4 周") — never a computed one. Three is the minimum because two events make ONE gap, which cannot close against anything |
| `accel` | how hard the gaps closed: `1` is a metronome, `>1` accelerates (clamped to 5) | this is the FILM's claim about its subject, not the register's decoration. At 1 the marks are evenly spaced and the picture says "regularly"; at 2 the last two almost touch. Default 1.8 |
| `from` | the left end of the rule, in the film's words | sits on its own row BELOW the marks' `when` line, so the two never overprint |
| `to` | the right end | as `from`, right-aligned |
| `kicker` | the spaced label over the rule | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the rule, in the film's voice | the place to say what the closing gaps MEAN, which the picture shows but does not name |

**Known traps:**
- The last mark stops at `LAST_AT` (0.82) of the rule, not at its end. The tail is the argument: an escalation whose final event sits at the end of the line reads as a thing that finished. An earlier build normalised the last landing to 1.0 and this file's own header described a tail the frame did not have.
- The mark positions are derived from the same interval series as `cadence`, not re-measured from it. A test pins the two against each other, because a second copy of a rule is how this repo's caption band became four disagreeing definitions.
- Labels WRAP rather than shrink — the rule's height is reserved from the tallest stack, in the column each label actually wraps in, so a Chinese label and its English translation reserve different heights and both clear the caption band.
- Seven marks is a rhythm; an eighth is a chart. Past that the gaps a viewer is asked to compare are narrower than the marks are wide: the argument is still true and no longer visible.

**Refuses:** fewer than 3 `marks`; more than `MAX_ESCALATION_MARKS`; a mark with no `label`.

**Reference:** `remotion/src/shots/Escalation.tsx`
