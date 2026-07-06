# SVG icons in HTML pages (one coherent line family, used with restraint)

Icons can lift a designed page — label a category, mark a section, flag status — but used badly
they read as AI-slop clutter. The value is **consistency**: one coherent family is an identity
system; one icon gives a block a focal point. (Doctrine adapted from the slide-maker skill's
`references/icons.md`.)

In the HTML tier, icons are **inline SVG** (not rasterized PNGs like slide-maker needs for pptx):
inline SVG is themeable via `currentColor`, deterministic, offline, and crisp. The snippet library
below is **Lucide** (ISC license, one 24-grid line family, `stroke-width:2`, round caps) — paste a
`<svg class="icon">…</svg>` straight into a page. Use ONE family across the whole video.

## The rule-of-thumb — apply to EVERY icon before it ships
An icon must answer at least one of: **(1) What is this? · (2) What does it do? · (3) Why pay
attention?** — *before* the viewer reads the text. If it answers none, it's decoration → **cut it.**

## When icons HELP vs HURT
- **HELP:** a row of **category / feature cards** each marked by an icon; a section / wayfinding mark
  reused per section; one focal icon anchoring a sparse beat; a status flag (warning/key/check).
- **HURT (cut):** an icon on **every keypoint row** of every page (wallpaper); a decorative icon that
  labels nothing; **mixed families**; an icon **larger than the title**; an icon **on an evidence/stat
  beat** (a `chart`/number/figure is the focal point — an icon beside it competes); an icon carrying
  meaning with **no text label**. Icons are seasoning — a few, consistent, purposeful. **Never** use
  emoji or ✅/🚀/🔥 in place of a real icon.

## Role vocabulary (pick the glyph by the JOB, not the picture)
Reach for the glyph whose meaning matches the point's ROLE. Colour-code by role too (per the semantic
colour ledger, `references/design-intelligence-addendum.md` §7): risk in `--accent2`, growth in `--green`.

| Role | Meaning | Glyph (from the library below) | Colour |
|---|---|---|---|
| category | labels a feature/topic | `layout`, `file-text`, `image`, `bar-chart` | `--accent` |
| action | a thing done / a step | `refresh-cw`, `git-branch`, `search`, `sparkles` | `--accent` |
| risk | a problem / warning / loss | `alert-triangle`, `x-circle` | `--accent2` |
| growth | improvement / expansion | `sparkles`, an ▲ delta, `bar-chart` | `--green` |
| decision | a choice / gate | `list-checks`, `git-branch` | `--accent` |
| time | a stage / deadline / speed | `clock` | `--muted` |
| system | components / structure | `git-branch`, `layout` | `--accent` |
| user | audience / people | `users` | `--accent` |
| data | numbers / evidence | `bar-chart`, `sigma` | `--accent` |
| trust | verified / reviewed | `shield-check`, `check-circle` | `--green` |

If a point's role isn't here, it probably doesn't need an icon — a decorative glyph is worse than none.

## Five qualities of good icon use
1. **Semantic fit** — the metaphor *is* the thing (eye=perception, shield=trust, scale=fidelity,
   palette=design, bar-chart=data, languages=multilingual). A generic gear on every card mislabels.
2. **Color-code by category** — in a multi-category row give each its own hue (set `color:` on the
   `.icon-tile`, e.g. `var(--accent)` / `var(--accent2)`); the icon + its label share that hue.
   When the items are NOT distinct categories, use one accent for all.
3. **Contrast** — put the icon in an `.icon-tile` (tinted disc) or `.icon-badge` (ring) so it reads;
   never pale-grey or pure black.
4. **Consistent size & position across siblings** — same family, size, treatment, placement (top of
   each card, or left of each row). **≤ the title size** (`.icon-tile` is ~84px; never bigger).
5. **Style matches the deck** — this tier's pages are clean/modern, so **line** icons fit (don't mix
   in filled). One family only.

## Usage (classes live in `assets/html/motifs.css`)
```html
<!-- a category card with a tinted icon tile (color-code by setting color: per sibling) -->
<div class="card glass reveal-up" style="color:var(--accent)">
  <div class="icon-tile"><!-- paste an icon svg here --></div>
  <div class="label" style="margin-top:18px">Editable charts</div>
  <div class="note">native, any language</div>
</div>
```
- `.icon` — a bare inline glyph (40px, `currentColor`); sits inline before a label.
- `.icon-tile` — icon on a tinted disc (84px, color-coded by `color:`); the default category lockup.
- `.icon-badge` — icon in a thin ring (airy/editorial look on a light deck).
- `.icon-ghost` — an oversized faint icon as a card watermark (texture, not clutter).
Recolor by setting `color:` on the tile/icon (the SVG uses `currentColor`). Keep the text label —
the icon is support, never the sole carrier of meaning (set `aria-hidden="true"` on decorative-support
glyphs; the text says it).

## Snippet library (Lucide · ISC · paste inline)
Each is `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">…</svg>`. Pick by semantic fit.

- **check** — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>`
- **check-circle** (verified) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>`
- **x-circle** (dropped/rejected) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>`
- **alert-triangle** (problem/warning) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>`
- **clock** (time/slow) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`
- **search** (find/read) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`
- **eye** (perception/back-row review) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>`
- **file-text** (document/.pptx) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>`
- **image** (figure/extract) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/></svg>`
- **bar-chart** (data/chart) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>`
- **sigma** (equation/LaTeX) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M18 7V4H6l6 8-6 8h12v-3"/></svg>`
- **palette** (design/color) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.9 0 1.6-.7 1.6-1.7 0-.4-.2-.8-.4-1.1-.3-.3-.4-.7-.4-1.1a1.6 1.6 0 0 1 1.6-1.6h2c3 0 5.5-2.5 5.5-5.6C22 6 17.5 2 12 2Z"/></svg>`
- **languages** (multilingual) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/></svg>`
- **users** (audience) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/></svg>`
- **list-checks** (interview/questions) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/></svg>`
- **layout** (template) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>`
- **shield-check** (trust/review) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 13c0 5-3.5 7.5-7.7 9a1 1 0 0 1-.7 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.2-2.7a1.2 1.2 0 0 1 1.5 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1Z"/><path d="m9 12 2 2 4-4"/></svg>`
- **scale** (fidelity/faithful) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m16 16 3-8 3 8c-.9.7-1.9 1-3 1s-2.1-.3-3-1Z"/><path d="m2 16 3-8 3 8c-.9.7-1.9 1-3 1s-2.1-.3-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/></svg>`
- **git-branch** (workflow/reproducible) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><line x1="6" x2="6" y1="3" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>`
- **refresh-cw** (rebuild/iterate) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M8 16H3v5"/></svg>`
- **sparkles** (bespoke/generate) — `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l1.9 5.8a2 2 0 0 0 1.3 1.3L21 12l-5.8 1.9a2 2 0 0 0-1.3 1.3L12 21l-1.9-5.8a2 2 0 0 0-1.3-1.3L3 12l5.8-1.9a2 2 0 0 0 1.3-1.3Z"/></svg>`

Need an icon not here? Copy any **Lucide** glyph's inner SVG (lucide.dev) and wrap it in
`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">…</svg>` — staying in the one family.
