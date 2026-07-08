# Design Intelligence Addendum

Deep reference for `agents/design-director.md` (and the `agents/design-critic.md` gates). Load it
whenever a design choice risks becoming a **card grid, a repeated template, or a visually even
medium-density page**. It turns "reason concept → visualization" from advice into an operational,
testable procedure — the difference between "clean and consistent" and "art-directed and
content-specific."

**Deliverability rule (non-negotiable):** every visual language below is named as a form the renderer
can ACTUALLY land (the archetypes in `references/html-pages.md` + the programmatic renderers). Where a
famous metaphor (Sankey, flywheel, fishbone, funnel, hourglass, heatmap) is NOT a first-class render, the
honest substitute is named. A metaphor may live in a **generic broll backdrop** (`.bg-soft`/`.bg-photo`),
never as the carrier of a fact. Never write a design plan that promises a diagram the renderer can't draw.

---

## 1. The design reasoning trace (make the decision visible)
For every beat that is not a plain `title`, the design plan must expose HOW the form was chosen — not
just the result. This is what prevents slide-type→template mapping. Emit, per beat:

```
narrative_job: diagnosis | proof | contrast | mechanism | transition | decision | action
content_shape: what data relationship the content actually has (order / magnitude / part-whole / two-axes / time / causality / structure / one-claim)
rejected_default: "card grid / bullet list / generic columns — because <the content has X, which a grid hides>"
chosen_form: the archetype + one line on why it explains the idea better than the default  (this is the schema's `visual.form` field)
```
The first three land in the per-beat schema as `narrative_job` / `content_shape` / `rejected_default`;
`chosen_form` is the beat's `visual.form`.
Worked example (business — a leaking growth engine):
> content_shape: three interacting failure points compounding into one loss ·
> rejected_default: "three problem cards — they read as independent, hiding the interaction" ·
> chosen_form: "a descending `.flow` (acquire → activate → retain) with the leak step highlighted —
> it shows the loss propagating across stages, which three cards cannot."

Worked example (research — the same move, non-business):
> content_shape: three error sources compounding into one reconstruction failure ·
> rejected_default: "three cards — they read as independent, hiding how the errors propagate" ·
> chosen_form: "a causal `.flow` (undersampling → motion → noise) into the failure, so the propagation
> reads — which three parallel cards cannot show."

---

## 2. The five bottlenecks (strengthened)

**2.1 Layout Intelligence.** Every beat identifies its NARRATIVE JOB before a layout. A layout is
**invalid if it is only a container for content** rather than a visual explanation of the idea. (Emit
`narrative_job` + `rejected_default` above.)

**2.2 Rhythm Design.** A deck can pass every per-beat check and still feel repetitive. The design plan
must carry a **rhythm map** — slide-to-slide variation across density, background, protagonist, and
emotional register:

This is ONE example arc (a business pitch); the Protagonist column is topic-derived, not prescribed —
a research arc runs question → method → result → conclusion, not problem → funnel → solution:

| # | Density | Background | Composition (anchor × balance) | Protagonist (the visual lead) | Register | Role |
|---|---|---|---|---|---|---|
| 1 | light | plain surface / hero `.bg-photo` | full-bleed × centered (hero) | hero title / the question | aspirational | opener (business: aspirational; research: the question) |
| 2 | medium | warm/`--accent2` tint | top × left-weighted | conflict — a risk KPI *or* the problem/gap | pressure | conflict |
| 3 | light | plain / soft texture | center × split | mechanism — a funnel *or* the `research_method` pipeline | diagnostic | explanation |
| 4 | medium | cool/`--accent` tint | bottom × grid-asym | payoff — a system `.hubspoke` *or* a `results_table` / `chart` | constructive | solution / result |

Two adjacent rows must differ in at least TWO columns. A flat column (every row "medium / plain /
cards / neutral") is the auto-generated tell. **The Composition column may not be flat either:** no two
adjacent beats may share the same (anchor × balance), and ≥~1/3 of beats must be off-center. And **bind
the Background tag to an ACTUAL backdrop element** — a warm/cool/hero background MUST be a real
`.bg-soft`/`.bg-soft-tint`/`.bg-photo`/`.accent-fill`, not a bare `--bg` (`validate.py` gates
composition-center-share, off-center share, and bare-bg share).

**2.3 Space Intelligence.** Whitespace is an ACTIVE element, not unused capacity. If a beat feels thin,
**strengthen the hero or cut a secondary element — never add cards to fill space.** Emit the schema's
single `density` field = the number + the call:
```
density: "~55%|~60% utilization — keep airy because … | split into two beats because … | compress only because …"
```
Target roughly **~50–60% content utilization** — on 16:9 the html whitespace floor caps content near
**~60%**; on 9:16 keep the same airy DENSITY but DISTRIBUTE it to SPAN ≥70% of the column (gaps + a
lower-zone motif), never cram (span ≠ density; see `references/html-pages.md` "9:16").

**2.4 Visual Surprise.** A WOW beat is not merely a big element — it must create a **deliberate
contrast** against its neighbours and be memorable after the deck closes. For each hero beat emit:
```
why_memorable: bold number | iconic diagram | dramatic sentence | extreme contrast | unusual (on-topic) metaphor
surrounding_contrast: differs from beat X-1 and X+1 by layout + density + background mode
```
These land in the per-beat schema as `wow.why_memorable` / `wow.surrounding_contrast` (the beat id is the
object key — there is no separate `wow_beat` field). Emit `wow` on hero beats only.

**2.5 Visual Reasoning.** Do NOT map "problem slide → three cards." Map the CONTENT LOGIC: "this problem
is three interacting failure points → a causal `.flow` / a converging `.hubspoke` / a descending funnel."
Reason from the relationship, then pick the archetype that says it.

---

## 3. Block Dependency Audit (the strict anti-card-grid gate)
The form-family diversity gate (`≤45%` one family) can be gamed: "dashboard", "metric matrix", and "three
action cards" count as different forms but read as the SAME block-grid language. So, additionally:

**A block/card/panel layout is allowed ONLY if its units are ALL of:** parallel · unordered ·
equal-weight · independent · **and not better expressed** as time, flow, hierarchy, comparison, system,
or magnitude. For every beat that uses cards/`.blocks`/panels, state why blocks are necessary:

| # | Uses blocks? | Why allowed (all 5 conditions)? | Better non-block form considered | Keep or redesign |
|---|---|---|---|---|

**Hard rule:** if **>2 consecutive beats** use card/panel/block logic (regardless of form NAME), at least
one must be redesigned unless a content reason is stated. The design-critic (D1) enforces this.

---

## 4. Concept → Visual Language dictionary (deliverable, with use / avoid / failure)
Reason from the content logic to the form. **The "Deliverable form" column is what THIS renderer can
land** — a `*` marks a metaphor that is broll-only or approximated (the honest data-form is named first).

| Concept / content logic | Deliverable form (ours) | Use when | Avoid when | Common AI failure |
|---|---|---|---|---|
| Flow / Process | `.flow` (numbered steps + arrows) | steps happen in sequence | items are unordered | four cards with arrows |
| Journey / Evolution | `.timeline` · `render_timeline` | time or stages matter | no chronology | timeline as decoration, too much text |
| Growth / Trend | `chart` line (curve) / bars / counter | progress/acceleration is central | change is qualitative | a random upward arrow |
| Loop / Flywheel / Compounding | linear `.flow` with a "return" step *(no cycle renderer)* | each step feeds the next | steps don't feed back | a pretty circle with no compounding logic |
| Comparison / Before-after | `.split` + `.defocus` · `render_compare` | two states/options contrast | >3 alternatives | a table where visual contrast is needed |
| Hierarchy / Ranking | graded `.bar` rows / stacked `.blocks` tiers *(no pyramid)* | levels/magnitude matter | items are equal-weight | a flat card grid |
| Prioritization / Two axes | `.quadrant` | choice/order on two axes | there is no ranking | a quadrant with weak/undefined axes |
| Relationship / Ecosystem / System | `.hubspoke` (hub+spokes) *(no arbitrary graph)* | actors converge on a centre | a simple sequence | random nodes with no meaning |
| Parts of a whole / Share | `.segbar` / `.meter` · `render_compare` split | proportions of one whole | independent items | a pie-like grid of equal cards |
| Dependency | `.flow` (A feeds B) / `.segbar` *(no Sankey)* | inputs feed outputs | no volume/dependency | arrows with no weight or logic |
| KPIs / Performance | `.dash` + `.scorecard`/`.tile`/`.delta` | KPIs are central | the story is causal | a KPI wall with no hierarchy |
| Progress | `.meter` / milestone `.timeline` | completion status matters | open-ended exploration | decorative progress bars |
| Big number / Result | `.stat` / `chart` counter (`props.climax`) | one magnitude must land | many values are close | a giant number with no context |
| One idea / Insight / Conclusion | `.pullquote` / hero `title` / `.accent-fill` band | one message must land emotionally | detail-heavy content | the conclusion hidden small at the bottom |
| Section / divider | `title` / full-bleed `.accent-fill` | a chapter break | mid-topic | a full content page used as a divider |
| Bottleneck / Leakage / Drop-off (churn, attrition, signal/sample loss) | descending `render_chart` bars (funnel) / `.flow` with the constraint `.step.on` *(no hourglass/leaking-bucket)* | loss/constraint across stages | multiple unrelated problems | three warning cards |
| Method / pipeline (input→process→output) | `.flow` (neutral, method step `.on`) — `research_method` template | a method transforms input to output | a data-flow *graph* with branches | four cards with arrows |
| Layered architecture / system tiers | stacked `.blocks` tiers — `code_architecture` template | a system organised in layers | a convergent hub (use `.hubspoke`) | boxes joined by meaningless lines |
| Equation / math | `.eqn` + `.eqn-term` (term glow) — `equation_build` template *(heavy LaTeX → matplotlib mathtext image / MathML)* | one equation IS the point, term by term | a wall of equations | an equation shown but never explained |
| Benchmark / ablation | `.rtable` with the winning row `.win` — `results_table` template | N methods × M metrics, one wins | a 2-state before→after (use `.split`) | a KPI-tile wall for a comparison |
| Annotated figure / result | a big `.media` panel + `.chip` callouts — `figure_focus` template | the finding IS a plot / scan / image | a number (use `.stat`) | a decorative image with no annotation |
| Tradeoff | `.quadrant` (two axes) / `.split` (two objectives in tension) *(no balance-scale)* | two objectives conflict | only one objective | two columns with no tension shown |
| Causality / Root cause | causal `.flow` (chain) / `.hubspoke` (causes→effect) *(no fishbone/tree)* | cause→effect is the insight | items are merely descriptive | flat bullets/cards |
| Risk | `.quadrant` (likelihood×impact) / colour `.blocks` tiers / `.meter` *(no heatmap)* | severity/likelihood matter | risks are only examples | red colour everywhere |
| Roadmap | quarterly `.timeline` / milestone rail | future sequencing matters | no time order | three cards labelled Q1/Q2/H2 |
| Case study | `.timeline` (journey) as the PRIMARY, one small `.stat`/`.delta` proof accent (not a co-equal block) | an entity changes over time | a pure metric summary | a timeline with no protagonist |
| Operating model | `.hubspoke` / stacked `.blocks` layers / `.dash` *(no RACI/org-tree)* | roles/process/metrics interact | pure narrative | an org chart as decoration |
| Strategy | `.quadrant` / `.blocks` pillars *(no compass)* | direction & tradeoffs matter | pure execution detail | a decorative compass icon |
| Categories (last resort) | colour `.blocks` / `.card` grid / `.icon-tile` rows | units are parallel/unordered/equal-weight | any order/magnitude/relation exists | a card grid for everything |

---

## 5. Reference-vs-Generated gap heuristic (is the plan mature?)
Judge the WHOLE plan against these patterns:

**Weak generated-deck pattern** (not ready even if each beat is clean):
- many beats share the same shallow background · card grids are the main visual language · all cards have
  similar weight · colour follows the template not semantic emotion · dense beats solved by smaller text
  rather than hierarchy · few true visual events.

**Strong art-directed pattern:**
- each beat has a different visual protagonist · colour shifts semantically between problem / system /
  proof / action · one beat is a diagram, one a dashboard, one a timeline, one a hero claim · dense
  information is RANKED not evenly packed · every few beats has a memorable visual event.

If the plan resembles the weak pattern, redesign it.

---

## 6. Evenness penalty (something must win)
A beat is weak if all elements have similar visual weight ("clean but too even"). The design must decide
what wins. Check every beat:
- Is there a clear **first-read** element? a clear **second-read** layer? Are supporting details visibly
  **quieter**? Is at least ONE thing deliberately **oversized / isolated / darkened / framed / centred**?

If everything is equally polite, the beat fails the evenness penalty (design-critic D5).

---

## 7. Semantic colour ledger (colour carries meaning, mapped to our tokens)
The design plan must carry a semantic colour ledger — each role bound to a theme token (most emitted by
`theme.py` → `theme.css`; `--green` is a fixed base.css constant, `--rule` = `--accent2`), one meaning per hue:

| Semantic role | Token | Used for | Must NOT be used for |
|---|---|---|---|
| Structure | `--fg` / `--muted` | systems, labels, axes, rails | warnings / positives |
| Growth / positive | `--green` | improved result, a gain, `.delta.up`, expansion | neutral decoration |
| Risk / problem | `--accent2` / `--rule` | a worse result, a failure mode, a bottleneck, loss, `.delta.down` | ordinary emphasis |
| Neutral support | `--muted` / `--surface` | cards, grid, secondary text | the main hero |
| Through-line / decision | `--accent` | the topic's spine, roadmap, the payoff | historical/negative evidence |

Rules: **no accent colour without semantic meaning**; a **problem beat is allowed to feel different** from
a results beat; if the whole deck uses ONE accent hue for everything, the plan is not ready
(design-critic D8).

---

## 8. Minimum deck-level variation (hard floors)
For decks with **6+ content beats**:
- **≥4 distinct visual protagonists** across the deck.
- **≥3 non-card forms** (flow / timeline / quadrant / hubspoke / segbar / meter / pullquote / chart) —
  a `scorecard`/`.dash` is a TILE GRID, so it counts toward the diversity floor NOT as "non-card" and
  still trips the §3 consecutive card/panel audit.
- **≤2 consecutive** beats using card/panel logic (see §3).
- **≥1** hero/WOW beat.
- **≥1 diagrammatic** beat IF the content has any process, system, mechanism, or framework.
- **≥1 contrast** beat IF the content has before/after, old/new, problem/solution, or baseline/proposed.
- **≥1 time/roadmap** beat IF the content has sequence, phases, evolution, or a future plan.
The design-critic (D1) treats an unmet floor as a REVISE.

---

## 9. Slide archetype alternatives (break the default page type)
When a beat's job is one of these, pick from its list instead of defaulting to cards — each maps to a
deliverable form (§4):

- **Problem** → warning `.dash` (`.delta.down`) · descending funnel (bars) · causal `.flow` · a single
  dramatic hero number (`.stat`) · a `.quadrant` risk matrix.
- **Root cause** → causal `.flow` chain · converging `.hubspoke` · a bottleneck-highlighted `.flow` (mark
  the constraint step `.flow .step.on`; set `--focal:var(--accent2)` so the ring reads as risk, per §7).
- **Framework / model** → `.hubspoke` model · stacked `.blocks` layers · a lifecycle `.flow` (with a
  return step) · a `.quadrant` map.
- **Results** → `.dash` with ONE hero metric · a before/after `.split` scoreboard · a `chart` (slope/line)
  · a `.scorecard` with hierarchy (make one tile dominant *inline* — enlarge its `.num` or span a column;
  the grid is equal-width by default).
- **Case study** → journey `.timeline` · an expansion `chart` · a metric-progression `.scorecard`.
- **Action plan** → a roadmap `.timeline` · a milestone rail · a `.flow` cadence · a `.quadrant` decision
  matrix.

---

## 10. What "ready" means
The design plan is ready when: every non-title beat carries its reasoning trace (§1); the block audit
(§3) passes; the rhythm map (§2.2) varies; the colour ledger (§7) is semantic; the deck clears the
minimum-variation floors (§8); at least one beat is a named, contrast-creating WOW (§2.4); and no beat is
evenly-weighted (§6). Clean per-beat is necessary but NOT sufficient — the deck must be art-directed.
