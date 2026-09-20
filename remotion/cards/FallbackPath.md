# FallbackPath

**Identity:** one action box forks into two routes: the preferred one lights and its road fills as it is taken; the fallback stays a dashed outline carrying the condition that would send you down it.

**Use when:** a mechanism with a preference in it — "tried first, and only if that misses, this" — a cache and its origin, a retry and its backoff, a font and its fallback. **Not when:** the second step follows the first by finishing it (that is a sequence — InOrder), or there is only one route.

**Motion core:** the action lands (0.04–0.20); the fork and both routes appear together (0.18–0.40), so both are seen before either is taken; the preferred road fills and its box glows (0.44–0.68) while the fallback dims; the `when` conditions fade in (0.62–0.82); the note comes last (0.74–0.92).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `action` | the one thing you do — both routes leave from it | shrinks to fit the box's width |
| `first` | `{label, when?}` — the route tried first | solid accent border, lit and travelled; `when` is optional |
| `then` | `{label, when}` — the fallback | dashed and dimmed; its `when` is what makes it read "only if not" rather than "then" |
| `note` | one line under the fork | its height is reserved first, so a long note shrinks the fork above it |

**Known traps:**
- All three of `action`, `first`, `then`, or none: a film that passed two once got the demo's fallback ("Open a new one / only when it is not") stated as its own product's behaviour. Now it throws, naming the missing one.
- Drawn as two ordered steps, "use the open tab, open a link only when there is none" reads as "use the tab, then open a link" — the opposite claim. Give `then.when` its condition.
- In portrait the routes stack under the action and no roads are drawn; the preference reads only from the solid vs dashed boxes.
- Route labels are a fixed size (wrapped, balanced), not fitted — a long label makes a tall box.

**Refuses:** some but not all of `action` / `first` / `then` passed; an empty `action`, `first.label` or `then.label`.

**Reference:** `remotion/src/shots/FallbackPath.tsx`
