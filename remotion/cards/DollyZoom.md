# DollyZoom

**Identity:** the subject stays pinned at one size in the middle while the room around it swells or recedes — a hairline grid growing past every edge, context labels travelling outward or inward and softening or sharpening as they go.

**Use when:** THIS did not change, what surrounds it did — the same task inside a bigger system, the same claim once its context arrives. **Not when:** the subject itself changes (a dolly-zoom on a moving subject is just a zoom), or the beat is two readings of one subject (RackFocus).

**Motion core:** the room moves from 0.16 to 0.86 (eased), the grid scaling 1 → 2.25 for `in`, 2.25 → 1 for `out`. On `in` the context labels arrive with the room (0.10–0.52) and travel outward, softening; on `out` they are there from frame one and travel inward, sharpening. The subject never moves, scales or blurs. The `reading` lands last (0.74–0.94).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `subject` | the pinned thing, drawn sharp at one size | fitted to a column (0.44 of the width, 0.80 in portrait) and a height budget; a long subject shrinks and wraps |
| `note` | a dim line under the subject | fitted to its own budget so it never grows into the caption band |
| `context` | short labels for the surroundings, split into two groups either side (above and below in portrait) | 0–8, every one drawn; they share one size, which steps down on a tight frame — or when a side's column of labels would be taller than the zone — so long labels come out small rather than on top of each other. A sentence here reads as the subject's caption, not as room |
| `reading` | the line that says what the new scale means | accent, uppercase mono, fitted; lands last |
| `direction` | `'in'` or `'out'` — named for the ROOM | `'in'`: labels travel OUTWARD and end large and soft — SUBTRACTION, these went away, this remains. `'out'`: labels travel INWARD and end small, crisp and near — ARRIVAL, all of this landed on it |

**Known traps:**
- `direction` reads backwards unless you think of the labels: a beat about six integrations LEAVING was authored `'out'` and ended with the departed names as the brightest, sharpest type converging on the subject — the opposite of its sentence.
- The default six `context` labels are placeholder copy ('around it', 'and this'…); omitting `context` prints them.
- The subject is pinned in the strict sense — no scale, translate or filter — because its size is the one constant the shot asserts; `test_dolly_zoom` measures it.
- The labels never leave the frame, on purpose: an earlier draft swept them out and the shot ended on an empty frame while `text_safe_qa` reported nothing.
- The room is drawn from `dim`, not `line`: at `line`'s contrast the first render was a subject floating in nothing.

**Refuses:** an empty `subject`; a `direction` other than `'in'` / `'out'`; more than eight `context` labels, or an empty one; a frame too tight to give the context labels room to travel (or to stack a side's column inside the zone) at any size down to 60%.

**Reference:** `remotion/src/shots/DollyZoom.tsx`
