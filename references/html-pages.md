# Authoring HTML pages (the "HTML pages" visual tier)

Each `html` scene is one designed full-screen page (1920×1080) you author at
`<out_dir>/pages/scene_NN.html`, rendered by headless Chrome. The page is screenshotted at
progress `p=0..1`; `seek.js` freezes its CSS reveals so the entrance animates then holds.

## Boilerplate (link the bundled design system)
```html
<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="file:///ABS/PATH/TO/skill/assets/html/base.css"></head>
<body>
  <div class="stage"><!-- your layout --></div>
  <script src="file:///ABS/PATH/TO/skill/assets/html/seek.js"></script>
</body></html>
```
Use absolute `file://` paths to the skill's `assets/html/base.css` and `seek.js`.

## Layout patterns (compose with base.css classes)
- **Title:** `.kicker` + `.rule` + `.title` (+ `.sub`).
- **Big stat:** a `.stat` number + `.unit`, with a `.sub` caption.
- **Split / breakdown:** a `.grid` of `.bar` rows (widths set inline as `style="width:74%;background:var(--blue)"`), each labeled — for decompositions like 165 = 123 + 42.
- **List / key points:** `.grid` of `.row`s, each `.dot` + `.label` (+ `.note`).
- **Quote / takeaway:** a large `.title` line + `.sub` attribution.
- **Timeline:** a `.grid`/flex row of dated `.row`s.

## Reveal animation (so the page captures cleanly)
- Add `class="reveal"` or `class="reveal-up"` to elements you want to animate in.
- Stagger by giving later elements an inline positive delay: `style="animation-delay:.18s"`.
- ONLY use CSS animations via these classes. **No** `setTimeout`/JS-driven motion, **no** external
  network assets (images/fonts/CDNs) — they break deterministic, offline, seekable capture.

## Faithfulness (required)
Every number, name, date, and claim on the page must come from the material (or a verified
source) — type the real data into the HTML. Never invent figures or labels. Data lives on the
page as real text/bars, not as a decorative picture. The critic checks the page against the
narration (R2 audio↔visual) and the facts (R1d/R1e).

## Example (a faithful split page)
```html
<div class="stage">
  <div class="kicker reveal">2025 · 165 次发射</div>
  <div class="rule reveal" style="animation-delay:.05s"></div>
  <div class="title reveal-up" style="animation-delay:.1s">真正能争夺的，只有一小块</div>
  <div class="grid" style="margin-top:40px">
    <div class="bar reveal-up" style="animation-delay:.25s;width:74%;background:var(--blue)">自用 Starlink · 123</div>
    <div class="bar reveal-up" style="animation-delay:.4s;width:26%;background:var(--orange)">对外发射 · 42</div>
  </div>
</div>
```

## Motifs & pictures (make pages fancier)

Also link `assets/html/motifs.css` (after `base.css`). Motifs are **atmosphere behind real
content** — they assert no fact, so they stay decorative; the real data is the text/bars.

**CSS motifs** — put backdrops as direct children of `<body>`, BEFORE `.stage` (content sits above):
- `<div class="bg-stars"></div>` — a deterministic starfield.
- `<div class="bg-glow blue" style="width:640px;height:640px;top:-120px;right:-120px"></div>` — a soft accent glow (position + size inline).
- `<div class="ghost">165</div>` — an oversized faint number behind the content.
- `<span class="grad-text">…</span>` — gradient accent text.
- Motion (seekable, paused): `class="float"` (gentle rise) on any element.

**Inline SVG motifs** (copy-paste; style with `fill`/`stroke`/`.float`/`.draw`):
```html
<!-- generic rocket silhouette -->
<svg width="180" height="320" viewBox="0 0 60 120" class="float" style="position:absolute;right:160px;top:300px;z-index:1">
  <path d="M30 4 C42 22 44 52 44 78 H16 C16 52 18 22 30 4 Z" fill="var(--blue)"/>
  <path d="M16 78 L4 104 L18 92 Z M44 78 L56 104 L42 92 Z" fill="var(--orange)"/>
  <circle cx="30" cy="46" r="7" fill="#0d1117"/>
</svg>
<!-- orbit ring (use .draw for a stroke-on; path/circle must set pathLength="1") -->
<svg width="520" height="520" viewBox="0 0 200 200" style="position:absolute;left:-80px;bottom:-120px;z-index:1;opacity:.5">
  <circle cx="100" cy="100" r="90" fill="none" stroke="#3a4150" stroke-width="2" pathLength="1" class="draw"/>
</svg>
```

**Pictures (`gpt-image` backdrops or your own photos)** — a LOCAL image is allowed (a `file://`
path is offline/deterministic; only NETWORK assets are forbidden). Use it as a darkened backdrop:
```html
<img class="bg-photo" src="file:///ABS/PATH/assets/bg_01.png" alt="">
<div class="scrim"></div>
<div class="stage"><!-- legible text over the photo --></div>
```
A gpt-image backdrop must stay **generic/atmospheric** (`broll`) — no fabricated specific
vehicle/event/figure, no embedded numbers — the facts live in the page text, never in the image.
