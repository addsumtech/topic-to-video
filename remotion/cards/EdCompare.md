# EdCompare

**Identity:** an editorial two-column spread: a kicker and rule, then two columns split by a hairline — one dimmed as the foil, one in full ink under an accent head as the hero.

**Use when:** this vs that in a print register — a qualitative divide where one side is the point. **Not when:** a winner must be declared loudly with points (VersusSplit), the comparison is numeric, or real photographs make the case (RealVersus).

**Motion core:** the kicker and rule draw in first (to ~0.26), the left column rises 0.24–0.40, the right 0.36–0.52; then it holds — QUIET for its second half.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | the small accent caps above the rule | '' draws the rule alone |
| `left` | `{head, body, hero?}` for the left column | `head` is small tracked uppercase; `body` is a fixed 46px in the display face, not fitted — long copy only makes the column taller |
| `right` | the same for the right column | the default marks this side `hero: true` |
| `framed` | puts the spread on a bordered surface panel | a card instead of type on the ground |

**Known traps:**
- Emphasis lives inside each column object: pass your own `right` without `hero: true` and neither side is the hero — both dim. Mark exactly one.
- The hero's head gets a '↳ ' prefix and full ink; the foil is dimmed, so a foil carrying the important copy reads as unimportant.
- Omitted columns print the placeholder 'A' / 'B' with '…' bodies; the default kicker is 'THE DIVIDE'.
- Nothing is fitted, so several sentences per column can run past the content zone.

**Reference:** `remotion/src/shots/EdCompare.tsx`
