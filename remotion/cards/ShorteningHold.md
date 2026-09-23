# ShorteningHold

**Identity:** the beat's statements arrive one at a time, each held for less time than the one before. The spent ones stack above the live line, packing tighter as they pile up; the last statement is never cut away. Under the live line is a rule as wide as that statement's own hold, measured against the first one's.

**Use when:** a run of things PILED UP and the claim is the pace — five tickets in a week, five things that broke, five asks that landed before you answered the first. **Not when:** the film has real dates and the claim is a measurable rate (`Escalation` draws that on a time rule and asks for the film's own words for each date); not when the items are peers whose ORDER is the argument (`WordTunnel`); not when two things are being compared (`VersusSplit`).

**How it differs from `Escalation`,** which argues the same shape: `Escalation` DRAWS a rate for a viewer to read, this one DOES the rate to them and keeps the stack only as the receipt. The deciding difference is not taste but what the film HAS — `Escalation` needs real time data and refuses a computed date, so a beat with no timeline had nowhere to go. This register never claims a date; its only claim about time is the film's own `accel`.

**Motion core:** the holds are the INTERVALS of `cadenceAt(n + 1, accel)` from `runtime/motion` — the same series `Escalation` places its marks with and `cadence` walks to time them, so the library has one definition of a rhythm and every reader of one reads it. A statement arrives on a CUT, not a dissolve: it is on screen at full position from its first frame and only settles after (`easeOutExpo` over the first sixth of its hold), because an eased fade-in spends the start of every hold half-legible and the shortest holds would never be fully on screen at all. The kicker fades 0.02–0.10, the note 0.84–0.94.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `statements` | the run, in the order it landed — 3 to `MAX_HOLDS` (6) | no dates: this register never claims one. Three is the minimum because two statements make ONE gap, which cannot shorten against anything |
| `accel` | how hard the room between them closed: `1` is a metronome, `>1` accelerates (clamped to 5) | the FILM's claim about its subject, not the register's decoration. Default 1.9 |
| `kicker` | the spaced label over the run | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the stack, in the film's voice | where to say what the pace MEANT, which the frame shows but does not name |

**Capacity is a trade, and the register states it.** An accelerating series is front-heavy by construction — the first hold is the baseline the rest are read against, so it is the longest — which means more statements need a gentler `accel`. At this register's own 7s, the last hold clears the `MIN_HOLD_S` (0.34s) reading floor for:

| statements | 3 | 4 | 5 | 6 |
|---|---|---|---|---|
| highest workable `accel` | 2.5+ | 1.9 | 1.6 | 1.3 |

In a FILM these numbers are not the ones that apply: the refusal measures against the scene's own duration, so a beat with more narration under it can carry a harder pace.

**Known traps:**
- `cadenceAt(k)` returns k LANDINGS, which is k−1 intervals. This register needs n HOLDS, so it asks for n+1 landings and reads the intervals between them. Asking for n gives the last statement a hold of exactly zero — the series ends at 1 and there is nothing after the final landing to hold for — and that is what the demo did on its first render.
- The rule under the live line is the hold RATIO itself, never a formula that trends the right way. An earlier build sized it `0.18 + 0.82 × (1 − live/(n−1))`, invented here, which is a second definition of the pace quietly disagreeing with the pace.
- The spent stack's line spacing closes on the same count the holds do, so the picture of the pace and the pace are one measurement.
- Cut cleanly away, the settled frame would be one statement on a ground — a title card, and the whole argument would live in frames nobody looks at, since the contact sheet, `shot_still_qa` and the energy sweep all read stills. The stack is what keeps the evidence on the frame a reviewer actually sees.

**Refuses:** fewer than 3 `statements`; more than `MAX_HOLDS`; an empty statement; and a pace whose shortest hold falls under `MIN_HOLD_S` — naming the measured hold in seconds and the three levers (`accel`, fewer statements, a longer beat), because a statement gone before it can be read passes every pixel gate.

**Reference:** `remotion/src/shots/ShorteningHold.tsx`
