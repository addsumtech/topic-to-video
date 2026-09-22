# ViewSwitch

**Identity:** one body of records and several VIEWS of it. A tab strip names the views; under it the same rows travel from their place in one arrangement to their place in the next. What changes is the shape; the rows keep their identity, their order and their words.

**Use when:** the beat claims SEVERAL THINGS ARE REALLY ONE THING and the proof is that nothing changed — a database and its materialised views, a spreadsheet that is also an application, one dataset drawn three ways, a document and its outline, a design system themed twice. **Not when:** the faces carry DIFFERENT contents (that is `CubeRotate` — the opposite claim), or the point is what a thing is made of (that is a stack).

**Motion core:** the body label fades 0.01–0.12. The tab strip rises tab by tab from 0.06, 0.045 apart (easeOutCubic). The substrate enters 0.03–0.18. With no `at`, the shot WALKS the views across 0.16–0.94 — each row is ONE element for the whole shot and travels between arrangements; it is never re-created, its ordinal never changes and its words never change, because a viewer watching a row move is watching the argument. The note fades 0.72–0.86.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `views` | 2 to `MAX_VIEWS` (4) views, `{label, shape}` | `shape` is `'list' \| 'cards' \| 'board' \| 'panel'` and is DECLARED by the film, never picked by the tab's index. Two views is the minimum that can carry the claim; a fifth stops reading as a set of alternatives and becomes navigation |
| `rows` | 2 to `MAX_VIEW_ROWS` (6) records, `{label, note?}` | the things that do not change. Their words are set once and reused in every view — that is the proof. A board view gives each row a column, and a seventh sets its label under the legible floor |
| `body` | what the rows ARE, named once over the substrate | the one thing under every view. It is named once and never re-drawn, because it is the thing that did not move |
| `at` | rest on one view (0-based) instead of walking | use it when the beat names ONE view; omit it when the beat's claim is the switching itself |
| `kicker` | the spaced label over the strip | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the substrate, in the film's own voice | arrives after the walk has settled |

**Known traps:**
- A view with no `shape` throws. A shape chosen by position is the "widget by cell number" defect this library keeps finding, and here it would also make the register lie about which view looks like what.
- The rows' `label` must be the SAME string across views — the register does not re-word them per view, and a film that wants different words per view is asking for a different register.
- Sampling this register mid-clip catches a row in transit between two arrangements. That is the argument, not a layout fault; sample near the end of a view's dwell.

**Refuses:** fewer than 2 `views`; more than `MAX_VIEWS` views; a view with no `shape` or an unknown one; fewer than 2 `rows`; more than `MAX_VIEW_ROWS` rows; a row with no `label`.

**Reference:** `remotion/src/shots/ViewSwitch.tsx`
