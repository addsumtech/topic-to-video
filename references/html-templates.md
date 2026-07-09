# HTML template library (premium, copy-paste page compositions)

Reference implementations of the richer **composite forms** — the pages that make a video look *directed*
rather than a card grid. Each is a full `.stage` composition (kicker + title + the focal archetype +
supporting element + staggered, cued reveals), **rendered and visually verified** at 1920×1080.

**Use these as starting points to ADAPT, not fixed slots** — design is still choosing (pick the form via
`agents/design-director.md`'s Concept→Visual dictionary, then copy the matching template and **populate it
with your REAL content**). They are not a licence to template; they are a floor on quality so the agent
never reinvents good HTML from scratch. **A template copied and merely populated is a FLOOR, not the
design** — adapt it to the subject (shift the emphasis, re-cast the accent's role, vary the hero), and the
deck still needs at least one **bespoke** non-catalog beat (see `agents/design-director.md` "Freshness" +
design-critic D2). Populating alone produces the interchangeable "template every time" look.

**Every FORM here is topic-agnostic — the content swaps wholesale.** Several examples happen to use a
business scenario (for a familiar through-line), but the forms serve any subject. A research paper, a
code architecture, or a concept explainer keeps the same forms with scientific/technical content — and
the **research/technical templates** below (`research_method`, `code_architecture`, `equation_build`,
`results_table`, `figure_focus`) are built for exactly that. Match the form to the content *shape*, never
to the domain.

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
    <div class="arrow reveal" data-cue-index="1">→</div>
    <div class="step reveal-up" data-cue-index="1"><div class="n">STAGE 2</div><div class="t">Activate</div><div class="s">71%</div></div>
    <div class="arrow reveal" data-cue-index="2" style="color:var(--accent2)">→</div>
    <div class="step on reveal-up" data-cue-index="2" style="--focal:var(--accent2)">
      <div class="n" style="color:var(--accent2)">STAGE 3</div><div class="t">Retain</div>
      <div class="s" style="color:var(--accent2);font-weight:700">38%</div></div>
  </div>
</div>
```
Same skeleton serves **causal chain / root-cause** (drop the percentages, mark the causal node `.on`).
**9:16:** stack the steps vertically with a ↓ between them.
**Connectors reveal WITH their destination block** (applies to every `.flow`/`.hubspoke` here): an
`.arrow`/`.hs-connect` gets `reveal` (a plain fade — NOT `reveal-up`, so the glyph doesn't slide) +
`data-cue-index` = the **LATER** node's index (for a hub-and-spoke, the hub's). It carries **no `data-cue=`
of its own** — it borrows the destination's cue slot via seek.js, so nothing new is scraped and the render
is unchanged. Never leave a connector static among cued steps: it would paint from frame 0, before the
blocks (validate.py errors on that).

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
    <div class="hs-connect reveal" data-cue-index="3"></div>
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
    <div class="arrow reveal" data-cue-index="1">→</div>
    <div class="step reveal-up" data-cue-index="1"><div class="n">02</div><div class="t">More data</div></div>
    <div class="arrow reveal" data-cue-index="2">→</div>
    <div class="step reveal-up" data-cue-index="2"><div class="n">03</div><div class="t">Better model</div></div>
    <div class="arrow reveal" data-cue-index="3" style="color:var(--accent)">↻</div>
    <div class="step on reveal-up" data-cue-index="3"><div class="n" style="color:var(--accent)">back to 01</div><div class="t">Lower cost</div></div>
  </div>
</div>
```

---

# Research / technical templates
Built for papers, methods, architectures, and results — the shapes a business library misses.

## research_method — an input → METHOD → output pipeline (a neutral method diagram)
**Content shape:** a method that transforms an input into an output; the method stage is the focus
(accent `.step.on`, NOT the risk-red of `problem_leak`). Also serves a **procedural how-to** (numbered
steps). Where the true method is a data-flow *graph* (branches, an encoder/decoder, a data-consistency
loop), it's not renderable as a graph — decompose to a linear `.flow` with a named return step, or a
`system_map` hubspoke around the core. **Text budget:** `.t` ≤ 16 chars, `.s` a short sub-label.
```html
<div class="stage"><div class="kicker reveal-up">How the reconstruction works</div>
  <h1 class="title reveal-up" style="font-size:60px;margin-bottom:28px">Undersampled input, learned prior, clean cine.</h1>
  <div class="flow">
    <div class="step reveal-up" data-cue-index="0"><div class="n">INPUT</div><div class="t">Undersampled k-space</div><div class="s">8× accelerated</div></div>
    <div class="arrow reveal" data-cue-index="1">→</div>
    <div class="step on reveal-up" data-cue-index="1"><div class="n" style="color:var(--accent)">METHOD</div><div class="t">Deep image prior</div><div class="s">unrolled network</div></div>
    <div class="arrow reveal" data-cue-index="2">→</div>
    <div class="step reveal-up" data-cue-index="2"><div class="n">OUTPUT</div><div class="t">Full 4D cine</div><div class="s">no aliasing</div></div>
  </div>
</div>
```

## code_architecture — a layered system (stacked tiers, one data path)
**Content shape:** a system organised in layers/tiers with a data path through them; the key layer is
accent-filled. (A hub-of-modules → use `system_map` instead; an arbitrary dependency *graph* isn't
renderable — pick the dominant structure.) **Text budget:** `.bt` ≤ 18 chars, `.bd` ≤ 40 chars.
```html
<div class="stage"><div class="kicker reveal-up">System architecture</div>
  <h1 class="title reveal-up" style="font-size:58px;margin-bottom:24px">Four layers, one data path.</h1>
  <div class="blocks" style="grid-template-columns:1fr;gap:18px">
    <div class="block reveal-up" data-cue-index="0" style="background:var(--surface);color:var(--fg);border:var(--hairline);min-height:0;padding:26px 40px"><div class="bt" style="font-size:40px">Ingest</div><div class="bd">DICOM / raw k-space loaders</div></div>
    <div class="block reveal-up" data-cue-index="1" style="background:var(--surface);color:var(--fg);border:var(--hairline);min-height:0;padding:26px 40px"><div class="bt" style="font-size:40px">Preprocess</div><div class="bd">coil combine, normalise, mask</div></div>
    <div class="block reveal-up" data-cue-index="2" style="background:var(--accent);color:var(--on-accent);min-height:0;padding:26px 40px"><div class="bt" style="font-size:40px">Recon engine</div><div class="bd">unrolled network + data consistency</div></div>
    <div class="block reveal-up" data-cue-index="3" style="background:var(--surface);color:var(--fg);border:var(--hairline);min-height:0;padding:26px 40px"><div class="bt" style="font-size:40px">Export</div><div class="bd">4D cine, QA report</div></div>
  </div>
</div>
```

## equation_build — a typeset equation with annotated terms
**Content shape:** one equation is the point; each term gets explained. Author the math as styled HTML
(unicode ∑ ∫ ∇ √ ≈, `<sub>`/`<sup>`); wrap each annotated term in `.eqn-term` and either **anchor** the
key term with a static `.on` glow (below) OR make the terms **light up in spoken order** by giving each
`.eqn-term reveal-glow` + a `data-cue-index`. The explanations in `.eqn-terms` reveal in spoken order. For
heavy LaTeX: pre-render via matplotlib mathtext to a `.media` image, or author native `<math>` MathML
(Chrome renders it offline). **Text budget:** the equation on ONE line; ≤3 term notes.
```html
<div class="stage" style="justify-content:center"><div class="kicker reveal-up" style="text-align:center">The reconstruction objective</div>
  <div class="eqn reveal-up" data-cue-index="0" style="margin-top:24px">
    x̂ = argmin <span class="eqn-term on">‖Ax − y‖²</span> + <span class="eqn-term">λ·R(x)</span></div>
  <div class="eqn-terms">
    <div class="t reveal-up" data-cue-index="1"><b>Data consistency</b>the recon must explain the measured k-space y</div>
    <div class="t reveal-up" data-cue-index="2"><b>Learned prior R(x)</b>λ weights how much the network's prior corrects it</div>
  </div>
</div>
```

## results_table — a benchmark / ablation matrix (the winning row highlighted)
**Content shape:** N methods × M metrics; ONE row wins (`.win`, accent). Reveal row by row. Keep to ≤5
rows × ≤4 columns (a wall of numbers fails the squint test). **Text budget:** short method names, figures
only.
```html
<div class="stage"><div class="kicker reveal-up">Against the baselines</div>
  <h1 class="title reveal-up" style="font-size:56px;margin-bottom:24px">Better reconstruction, fewer parameters.</h1>
  <table class="rtable">
    <tr class="reveal-up" data-cue-index="0"><th>Method</th><th>Dice ↑</th><th>nRMSE ↓</th><th>Params</th></tr>
    <tr class="reveal-up" data-cue-index="1"><td>Zero-filled</td><td>0.71</td><td>0.184</td><td>—</td></tr>
    <tr class="reveal-up" data-cue-index="2"><td>U-Net</td><td>0.88</td><td>0.052</td><td>31M</td></tr>
    <tr class="win reveal-up" data-cue-index="3"><td>Ours</td><td>0.94</td><td>0.031</td><td>3.1M</td></tr>
  </table>
</div>
```

## figure_focus — a real plot/scan panel with labelled callout chips
**Content shape:** the finding IS a figure (a plot, a reconstructed image, a scan) — show it big and walk
it with cued callouts. The panel is a `.media` holding a `file://` image you generated (a matplotlib plot
/ a real scan crop — `object-fit:contain` for a plot, `cover` for an image); `.chip`s (`.good`/`.risk`
recolour the dot) reveal as the narration points. **Text budget:** takeaway ≤ 28 chars, each chip ≤ 34.
```html
<div class="stage"><div class="kicker reveal-up">Reconstruction error over iterations</div>
  <div class="split" style="padding:0;height:auto;grid-template-columns:1.3fr 1fr;gap:56px;margin-top:24px">
    <div class="media reveal-wipe" data-cue-index="0" style="height:620px"><img src="file:///ABS/recon_curve.png" style="object-fit:contain;background:var(--bg)"></div>
    <div style="display:flex;flex-direction:column;justify-content:center;gap:26px">
      <div class="label reveal-up" data-cue-index="0" style="font-size:52px">Converges 2.4× faster.</div>
      <div class="chip good reveal-up" data-cue-index="1"><span class="k"></span>ours: nRMSE 0.03 by iter 20</div>
      <div class="chip reveal-up" data-cue-index="2"><span class="k" style="background:var(--muted)"></span>baseline plateaus at 0.10</div>
    </div>
  </div>
</div>
```
The figure is a FAITHFUL asset (a real plot/scan), never an AI image standing in for data. Generate the
plot with matplotlib (the `chart` renderers, or a one-off) and reference it by `file://`.

## Cross-domain reminders (the forms above are not business-only)
- **hero_stat / metric_wall** → any RESULT with one dominant figure: `0.94 Dice` + support tiles
  (12 ms latency / 3.1M params), a `3.2× speedup`, a `10⁻⁹` error — not only ARR/NRR.
- **timeline_rail** → a method's phases (pretrain → finetune → eval), a study's stages, the evolution of
  a field — not only a product roadmap.
- **case_story** → any single entity tracked over time (a patient in a longitudinal study, one test
  sample, an observed object), ending on one proof figure.
- **problem_leak** → any loss across stages (a data pipeline dropping samples at a QC filter, error
  propagating across processing steps) — not only a growth funnel.
- **flywheel** → any self-reinforcing loop (a positive feedback loop, an active-learning loop, a chain
  reaction) — not only a growth-economics engine.

The research templates use MRI examples for concreteness, but they are **not imaging-only** — swap the domain:
- **results_table** → any N-methods × M-metrics benchmark (an NLP leaderboard, an economics model
  comparison, an assay panel, a hyper-parameter sweep).
- **equation_build** → any governing equation (a rate law, a regression/loss, a demand curve, a
  conservation law) — annotate its terms.
- **code_architecture** → any layered system (an ETL/data stack, an experimental apparatus, an org's
  process tiers) — not only software.
- **research_method** → any input→process→output pipeline (a lab protocol, a data-analysis workflow).
- **figure_focus** → any real plot/scan/spectrum/chart you generated (a spectrum, a heatmap, a micrograph).

---

# Quantitative & structural encodings (one number · two-point change · part-of-whole · position)
The forms above are mostly *narrative/structural*. These are the **quantitative** archetypes — reach for
them when the CONTENT is a number, a share, a change, or a set relationship, and a card would bury it. All
are pure CSS/SVG (deterministic, seekable), theme-var only, and **faithful**: every width/angle/count comes
from a real value the page states. Reveal parts with `data-cue-index`.

## one proportion — `.waffle` / `.gauge` / `.isotype` (pick by feel)
A single %/ratio, three ways: **waffle** = feel it as a count-of-100; **gauge** = one WOW arc; **isotype** =
discrete "k of N". ONE fact, not many — never cue the cells individually.
```html
<!-- waffle: first N of 100 cells .on = N% -->
<div class="waffle reveal-up" data-cue-index="0"><i class="on"></i>… (100 <i>, first 38 with class="on") …</div>
<!-- gauge: --p is the fraction; the number is the fact -->
<div class="gauge reveal-pop" data-cue-index="0" style="--p:.72"><div class="g-val">72%</div><div class="g-lab">capacity</div></div>
<!-- isotype: N .u glyphs, the real k get .on -->
<div class="isotype" style="--cols:5;max-width:420px"><div class="u on"><svg …person…></svg></div> … (10, first 7 .on) …</div>
```

## actual vs target — `.bullet` (did we hit the goal?)
A KPI against a target and qualitative bands. Band widths + value width + target position are real axis fractions.
```html
<div class="bullet reveal-up" data-cue-index="0">
  <div class="band hi" style="width:100%"></div><div class="band mid" style="width:75%"></div><div class="band" style="width:50%"></div>
  <div class="val" style="width:82%">$4.1M</div><div class="tgt" style="left:90%"></div></div>
```

## two-point change across many categories — slopegraph (SVG) / `.mk` matrix / waterfall
```html
<!-- SLOPEGRAPH: two axes, one line per category; rank crossover is the story. Strokes ≥2px. -->
<svg viewBox="0 0 900 560" style="width:900px">
  <text x="60" y="40" class="axl">2024</text><text x="840" y="40" text-anchor="end" class="axl">2025</text>
  <line class="sl reveal-wipe" data-cue-index="0" x1="90" y1="120" x2="810" y2="300" stroke="var(--accent)" stroke-width="3"/>
  <!-- label+value text at each end … one <line>+labels per category … -->
</svg>
<!-- CHECKMARK MATRIX: .rtable rows=features, cols=options; cells = .mk yes/no/mid -->
<table class="rtable"><tr><th>Capability</th><th>Ours</th><th>Theirs</th></tr>
  <tr class="win"><td>Audio-synced</td><td><span class="mk yes">✓</span></td><td><span class="mk no">✗</span></td></tr></table>
<!-- WATERFALL / bridge: start total → signed steps → end. .wbar height = magnitude, margin-top = baseline offset. -->
<div class="waterfall"><div class="wcol"><div class="wval">$100M</div><div class="wbar total" style="height:70%"></div><div class="wcap">FY24</div></div>
  <div class="wcol"><div class="wval">+$40M</div><div class="wbar up" style="height:28%;margin-top:2%"></div><div class="wcap">New</div></div>
  <div class="wcol"><div class="wval">−$18M</div><div class="wbar down" style="height:12%;margin-top:70%"></div><div class="wcap">Churn</div></div>
  <div class="wcol"><div class="wval">$122M</div><div class="wbar total" style="height:85%"></div><div class="wcap">FY25</div></div></div>
```

## set relationship & scope — `.venn` / `.rings`
`.venn` = shared vs unique (2–3 sets, screen-blended overlap — encodes MEMBERSHIP, never a precise area).
`.rings` = nested containment/scope (TAM/SAM/SOM, core→ecosystem). Author circles/rings inline; `.on` the focal one.
```html
<div class="venn"><div class="set" style="left:120px;top:40px;width:340px;height:340px;background:color-mix(in srgb,var(--accent) 45%,transparent)"></div>
  <div class="set" style="left:360px;top:40px;width:340px;height:340px;background:color-mix(in srgb,var(--green) 45%,transparent)"></div>
  <div class="vlab" style="left:150px;top:190px">A<span class="s">speed</span></div> … </div>
<div class="rings"><div class="ring" style="width:520px;height:520px"><div class="rlab">TAM · $50B</div></div>
  <div class="ring on" style="width:200px;height:200px"><div class="rlab">SOM · $1.4B</div></div></div>
```

## ordered procedure with position — `.stepper` (how-to / walkthrough)
Distinct from `.flow`: ordinality + a "you-are-here". `.step.done` past · `.step.on` current.
```html
<div class="stepper"><div class="step done"><div class="n">1</div><div class="st">Setup</div><div class="sd">install</div></div>
  <div class="step on reveal-up" data-cue-index="0"><div class="n">2</div><div class="st">Configure</div><div class="sd">set theme</div></div> … </div>
```

## enrich existing tiles/panels — `.spark` sparkline · `.wipe` before/after
`.spark` (an inline SVG trend inside a `.tile`/`.scorecard`, + a dashed `.base` target line) makes a metric
answer "trend?" and "vs target?". `.wipe` shows two **pixel-registered** images on one frame (denoised vs
noisy scan, redesign vs original) — a frozen `--w` split, or `.sweep` for a seek-frozen reveal.
```html
<div class="tile"><div class="stat">$482k</div><div class="note">MRR</div>
  <svg class="spark" viewBox="0 0 360 70" preserveAspectRatio="none"><line class="base" x1="0" y1="30" x2="360" y2="30"/>
    <polyline points="0,58 120,52 240,30 360,10"/><circle class="end" cx="360" cy="10" r="6"/></svg></div>
<div class="wipe" style="--w:.5"><div class="after"><img src="file://…/after.png"></div>
  <div class="before"><img src="file://…/before.png"></div><div class="seam"></div><div class="tag l">Before</div><div class="tag r">After</div></div>
```
(SVG helper: `.axl`/`.sl` are just author classes — set `fill:var(--muted)`/`stroke` inline or in a `<style>` using vars.)

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
