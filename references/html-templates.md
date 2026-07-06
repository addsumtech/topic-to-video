# HTML template library (premium, copy-paste page compositions)

Reference implementations of the richer **composite forms** — the pages that make a video look *directed*
rather than a card grid. Each is a full `.stage` composition (kicker + title + the focal archetype +
supporting element + staggered, cued reveals), **rendered and visually verified** at 1920×1080.

**Use these as starting points to ADAPT, not fixed slots** — design is still choosing (pick the form via
`agents/design-director.md`'s Concept→Visual dictionary, then copy the matching template and swap in your
REAL content). They are not a licence to template; they are a floor on quality so the agent never
reinvents good HTML from scratch.

**Standard head + seek.js** (same for every page — see `references/html-pages.md`): each page links
`base.css` → `theme.css` → `motifs.css` and ends with `<script src="…/seek.js"></script>`. The bodies
below assume that wrapper. Every reveal already carries a `data-cue-index` (spoken order) — add the
matching `data-cue="<spoken phrase>"` from the beat's narration so it fires on the voice (per
`references/html-pages.md` "Audio-synced reveals"). All reveals go static/opacity-fade under reduced
motion automatically.

**Colour is semantic** (per `references/design-intelligence-addendum.md` §7): `--accent` = through-line,
`--accent2` = risk/loss, `--green` = positive, `--muted` = support.

---

## hero_stat — the WOW metric (a single number that must land)
**Content shape:** one magnitude / result is the whole point. **Text budget:** kicker ≤ 24 chars, one
`.stat` number, sub ≤ 90 chars. Pair with `props.climax` on the payoff beat.
```html
<div class="bg-soft-tint"></div>
<div class="stage" style="justify-content:center">
  <div class="kicker reveal-up">Net revenue retention</div>
  <div class="reveal-up" data-cue-index="0" style="display:flex;align-items:baseline;gap:28px">
    <div class="stat">92<span class="unit">%</span></div>
    <div class="delta down" style="font-size:56px">▼ 14 pts</div>
  </div>
  <div class="sub reveal-up" data-cue-index="1" style="max-width:1100px">Down from 106% a year ago —
    the growth engine is now leaking faster than it fills.</div>
</div>
```
Drop the `.delta` for a pure number. **9:16:** unchanged (already center-stacked); scale `.stat` up
(`font-size:280px`) and let it own the upper-middle, sub below.

## before_after — two states in tension (defocus the old one)
**Content shape:** old→new / problem→solution / baseline→proposed. **Text budget:** title ≤ 34 chars, one
big figure per side, note ≤ 30 chars. The `.reveal-up` is on the WRAPPER, `.defocus` on the inner card —
never both on one element (the `.defocus` opacity would override the reveal and pre-show it).
```html
<div class="stage"><div style="display:flex;flex-direction:column;height:100%;justify-content:center;gap:40px">
  <div><div class="kicker reveal-up">Onboarding redesign</div>
    <h1 class="title reveal-up" style="font-size:76px">Seven screens → one.</h1></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:stretch">
    <div class="reveal-up" data-cue-index="0"><div class="card defocus" style="height:100%">
      <div class="kicker" style="color:var(--muted)">Before</div>
      <div class="label" style="font-size:120px;margin-top:12px">7</div>
      <div class="note">screens, 4 min median</div></div></div>
    <div class="reveal-up" data-cue-index="1"><div class="card" style="height:100%;border-color:var(--accent)">
      <div class="kicker">After</div>
      <div class="label" style="font-size:120px;margin-top:12px;color:var(--accent)">1</div>
      <div class="note">screen, 40 sec median</div></div></div>
  </div>
</div></div>
```
**9:16:** stack the two cards vertically (`grid-template-columns:1fr`), Before above After, an ↓ or the
delta between them.

## timeline_rail — a journey / roadmap / evolution (one focal node)
**Content shape:** 3–5 ordered/dated stages, one is the focus (`.tl-node.on`). **Text budget:** `.tl-what`
≤ 16 chars, `.tl-when` a short date. Don't exceed 5 nodes on 16:9 (they crowd).
```html
<div class="stage"><div class="kicker reveal-up">From prototype to product</div>
  <h1 class="title reveal-up" style="font-size:72px;margin-bottom:20px">Four quarters, one bet.</h1>
  <div class="timeline">
    <div class="tl-node reveal-up" data-cue-index="0"><div class="tl-dot"></div><div class="tl-when">Q1</div><div class="tl-what">Prototype</div></div>
    <div class="tl-node reveal-up" data-cue-index="1"><div class="tl-dot"></div><div class="tl-when">Q2</div><div class="tl-what">Private beta</div></div>
    <div class="tl-node on reveal-up" data-cue-index="2"><div class="tl-dot"></div><div class="tl-when">Q3</div><div class="tl-what">GA launch</div></div>
    <div class="tl-node reveal-up" data-cue-index="3"><div class="tl-dot"></div><div class="tl-when">Q4</div><div class="tl-what">Scale</div></div>
  </div>
</div>
```
**9:16:** switch to a VERTICAL rail — a single column of nodes down the left with the rail as a left
border; see `references/html-pages.md` "9:16 → vertical timeline rail".

## problem_leak — a funnel / bottleneck (loss across stages, the leak highlighted)
**Content shape:** a value drops across ordered stages; the constraint step is the focus. Recolour the
leak step's ring risk-red with `--focal:var(--accent2)` (per §7). **Text budget:** `.t` ≤ 14 chars, `.s`
a short figure.
```html
<div class="stage"><div class="kicker reveal-up" style="color:var(--accent2)">Where growth leaks</div>
  <h1 class="title reveal-up" style="font-size:72px;margin-bottom:28px">The drop is between activate and retain.</h1>
  <div class="flow">
    <div class="step reveal-up" data-cue-index="0"><div class="n">STAGE 1</div><div class="t">Acquire</div><div class="s">100%</div></div>
    <div class="arrow">→</div>
    <div class="step reveal-up" data-cue-index="1"><div class="n">STAGE 2</div><div class="t">Activate</div><div class="s">71%</div></div>
    <div class="arrow" style="color:var(--accent2)">→</div>
    <div class="step on reveal-up" data-cue-index="2" style="--focal:var(--accent2)">
      <div class="n" style="color:var(--accent2)">STAGE 3</div><div class="t">Retain</div>
      <div class="s" style="color:var(--accent2);font-weight:700">38%</div></div>
  </div>
</div>
```
Same skeleton serves **causal chain / root-cause** (drop the percentages, mark the causal node `.on`).
**9:16:** stack the steps vertically with a ↓ between them.

## system_map — inputs converge on one decision (hub + spokes)
**Content shape:** several signals/actors feed one hub (a router, a decision, a system). Only a hub/star
topology renders — decompose an arbitrary graph to a hub. **Text budget:** spoke ≤ 12 chars + a short `.s`.
```html
<div class="stage"><div class="kicker reveal-up">How the router decides</div>
  <h1 class="title reveal-up" style="font-size:66px;margin-bottom:8px">Three signals, one routing call.</h1>
  <div class="hubspoke" style="margin-top:20px">
    <div class="hs-spokes">
      <div class="hs-spoke reveal-up" data-cue-index="0">Latency<span class="s">p99, per region</span></div>
      <div class="hs-spoke reveal-up" data-cue-index="1">Cost<span class="s">$/1k tokens</span></div>
      <div class="hs-spoke reveal-up" data-cue-index="2">Load<span class="s">queue depth</span></div>
    </div>
    <div class="hs-connect"></div>
    <div class="hs-hub reveal-pop" data-cue-index="3">Route</div>
  </div>
</div>
```
**9:16:** stack spokes vertically above the hub; the `.hs-connect` runs down the centre.

## metric_wall — a dashboard with ONE hero metric (hierarchy, not equal tiles)
**Content shape:** a set of KPIs where ONE dominates and the rest support. Uses `.grid-asym` so the hero
is visually 2× the supporting column — never an equal `.scorecard` wall. **Text budget:** one big `.stat`,
supporting `.num` ≤ 6 chars, `.lab` ≤ 18 chars.
```html
<div class="stage"><div class="kicker reveal-up">Quarter in one screen</div>
  <div class="grid-asym" style="margin-top:16px;align-items:stretch">
    <div class="card reveal-up" data-cue-index="0" style="display:flex;flex-direction:column;justify-content:center;border-color:var(--accent)">
      <div class="note">Annual recurring revenue</div>
      <div class="stat" style="font-size:200px">$48<span class="unit">M</span></div>
      <div class="delta up" style="font-size:44px">▲ 31% YoY</div></div>
    <div class="dash-col">
      <div class="tile reveal-up" data-cue-index="1"><div class="num" style="font-size:96px">1,240</div><div class="lab">new logos</div></div>
      <div class="tile reveal-up" data-cue-index="2"><div class="num" style="font-size:96px">92<span style="font-size:48px">%</span></div><div class="lab">gross retention</div><div class="delta down">▼ 3 pts</div></div>
    </div>
  </div>
</div>
```
**9:16:** hero card on top (full width), the two support tiles in a row beneath.

## case_story — a customer/entity journey + a single proof metric
**Content shape:** one protagonist changes over time; end on ONE proof number (the timeline is the
primary, the stat is a small accent — not a co-equal block). **Text budget:** `.tl-what` ≤ 14 chars,
one proof figure + ≤ 30-char note.
```html
<div class="stage"><div class="kicker reveal-up">One customer, twelve months</div>
  <h1 class="title reveal-up" style="font-size:60px;margin-bottom:18px">From pilot to platform bet.</h1>
  <div class="timeline" style="margin-bottom:44px">
    <div class="tl-node reveal-up" data-cue-index="0"><div class="tl-dot"></div><div class="tl-when">Jan</div><div class="tl-what">10-seat pilot</div></div>
    <div class="tl-node reveal-up" data-cue-index="1"><div class="tl-dot"></div><div class="tl-when">May</div><div class="tl-what">Team rollout</div></div>
    <div class="tl-node on reveal-up" data-cue-index="2"><div class="tl-dot"></div><div class="tl-when">Dec</div><div class="tl-what">Company-wide</div></div>
  </div>
  <div class="row reveal-up" data-cue-index="3" style="justify-content:center;gap:24px">
    <span class="label" style="font-size:72px;color:var(--green)">40×</span>
    <span class="note" style="font-size:34px">seats in eleven months</span></div>
</div>
```

## flywheel — a compounding loop (linear flow with an explicit RETURN step)
**Content shape:** each step feeds the next and the last loops back (there is no cyclic renderer — make
the loop-back a labelled step, not a drawn circle). **Text budget:** `.t` ≤ 14 chars.
```html
<div class="stage"><div class="kicker reveal-up">The compounding loop</div>
  <h1 class="title reveal-up" style="font-size:64px;margin-bottom:28px">Each user makes the next one cheaper.</h1>
  <div class="flow">
    <div class="step reveal-up" data-cue-index="0"><div class="n">01</div><div class="t">More users</div></div>
    <div class="arrow">→</div>
    <div class="step reveal-up" data-cue-index="1"><div class="n">02</div><div class="t">More data</div></div>
    <div class="arrow">→</div>
    <div class="step reveal-up" data-cue-index="2"><div class="n">03</div><div class="t">Better model</div></div>
    <div class="arrow" style="color:var(--accent)">↻</div>
    <div class="step on reveal-up" data-cue-index="3"><div class="n" style="color:var(--accent)">back to 01</div><div class="t">Lower cost</div></div>
  </div>
</div>
```

---

## Text-budget discipline (why every template caps chars)
These pages are read at a glance on a moving frame — over-budget text shrinks or wraps and kills the
squint test. If your real content won't fit the budget, that's a signal to **split the beat**, not to
shrink the type. `keyframe_qa.py` catches overflow deterministically; the budgets keep you clear of it.

## Not in the library (and why)
Sankey, heatmap, org/decision tree, pyramid, morph, literal flywheel/funnel — **not deliverable**; use the
honest substitute from `agents/design-director.md`'s dictionary (funnel → descending `.flow`/bars, risk →
`.quadrant`, flywheel → this `flow`-with-return). A plain card grid needs no template — it's the fallback,
allowed only for parallel, unordered, equal-weight items (see the block dependency audit, addendum §3).
