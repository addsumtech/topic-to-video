# CarryOver

**Identity:** a duplicate form and the carbon under it. The top sheet is complete; a second copy is drawn out from behind it carrying only the fields the film marked, the rest arriving as the printed rule with nothing on it. That second sheet — complete in its ruling, incomplete in its ink — is the claim.

**Use when:** the beat is a TRANSFER THAT LOSES FIELDS — an export that drops columns, a summary that keeps the conclusion and not the caveats, a schema migration, a referral letter, an API version bump, a decision moved between tools. **Not when:** most of the distance was covered and a little was not (that is `LastLeg`, the opposite proportion), or when something CHANGED rather than failed to come along (that is a diff — `TermDiff`).

**Motion core:** the kicker fades 0.02–0.12. The top sheet draws on 0.03–0.18 (easeOutCubic). The carbon copy slides out from behind it 0.16–0.56 (easeInOutCubic) — slow, because the whole argument is watching what does and does not arrive. The `carried`/`dropped` word is pressed onto each row in turn from 0.52, 0.085 apart. The note fades in 0.80–0.90.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `fields` | the form's rows, `{label, value?, carried?}` — 1 to `MAX_CARRYOVER_FIELDS` (5) | `label` is the left column and is REQUIRED. `carried: true` prints the value on the second sheet too; anything else leaves that row's rule empty there. The proportion of carried to dropped is the picture — one of four reads very differently from three of four |
| `from` | where the handoff LEAVES, printed over the top sheet | the complete copy's heading. Omitted, the demo's generic place prints |
| `to` | where it ARRIVES, printed over the carbon | the incomplete copy's heading. The two together are the sentence the form makes; passing one and not the other reads as a form with a missing heading |
| `carriedLabel` | the word pressed onto a row that CAME THROUGH | one of the register's only two words, so it speaks any language. Keep it short — it is pressed into the row, not set as a sentence |
| `droppedLabel` | the word pressed onto a row that did NOT | as `carriedLabel`. This is the one that carries the argument, and a film that leaves it at the demo is shipping the demo's language |
| `kicker` | the spaced label over the sheet | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the form, in the film's own voice | arrives last, after the presses have landed |

**Known traps:**
- Five rows is where a sheet stops being a form and becomes a table. A sixth takes the label and the value under the size at which a field name reads at a glance, so it throws rather than dropping the tail — a form that omits a row while still looking like a form is the failure this register exists to draw.
- `carried` is read off each field and from nowhere else: no index rule, no alternating pattern. A film that forgets it gets an empty second sheet, which is a legitimate claim, not a default.
- Ink is derived through `readableOn`/`dimOn` and `onAccentInk`, so the pressed word reads on the accent block on a light film as well as a dark one.

**Refuses:** no `fields`, or no field with a `label`; a field with no `label`; more than `MAX_CARRYOVER_FIELDS` fields.

**Reference:** `remotion/src/shots/CarryOver.tsx`
