# Captions

**No libass required.** Captions are burned directly with PIL using the
bundled `assets/fonts/DejaVuSans.ttf`. The ffmpeg pipeline composites a
pre-drawn PNG overlay on top of each slide — no subtitle filter, no libass,
no special ffmpeg build needed.

---

## How the caption bar looks

- **Position:** Centered, near the bottom of the frame.
- **Background:** DEFAULT = `overlay`: NO strip/bar — the subtitle is burned DIRECTLY on the frame's own background (the frame fills the whole frame), text contrast-picked against the frame's real bottom ground, and the per-glyph outline is the frame's OWN ground colour (never a white/black halo). Content is kept clear of the caption zone so they never conflict. (`band` is the opt-in alt: a separate strip below the content, canvas grows.)
- **Text:** White, horizontally centered within the bar.
- **Font size:** ~4.0% of the NARROW dimension (`int(min(W,H) * 0.040)`; `meta.caption_scale` tunes) —
  captions are a reading aid, not a headline; they must not compete with the page's own type.
- **Font face:** follows the DECK's type — `--font-kind` (theme.css) maps to the same bundled style
  face the pages use (sans→Space Grotesk, mono→JetBrains, serif→Playfair, comic→Bangers), so the burned
  caption reads as the deck's own voice. CJK captions use the system CJK face (the deck's CJK fallback).
  ~43 px in BOTH aspects (min-dim scaled).
- **Bottom safe margin:** ~2% of frame height above the very bottom edge (`H*0.02`).
  At 1080p ≈ 65 px from bottom — comfortably inside the safe zone.
- **Text wrap:** Greedy word-wrap to 90% of frame width.
- **Padding inside bar:** ~1.2% of frame height above and below text.

### Enabled / disabled

Captions are ON by default (`meta.captions: true`). To disable:

```json
"meta": { "captions": false }
```

When disabled, no caption bar is burned into the frame. The `out.srt` sidecar
is **always** written either way, so viewers can still turn on soft subtitles.

### Placement — overlay (DEFAULT) vs a band BELOW the content

`meta.caption_mode` controls WHERE the burned caption sits. The requirement is: the FRAME'S OWN background
fills the whole frame and the subtitle sits DIRECTLY on it — **no separate solid strip/bar for the caption,
no white/black halo** — in a colour that CONTRASTS the frame's real ground, with the LAYOUT keeping content
clear of the caption zone so they never conflict. **`overlay` is the default** because it delivers exactly
that:

- **`"overlay"` (DEFAULT):** **NO strip** — the caption is burned flush at the **very bottom** of the W×H
  content (canvas stays exact 16:9). The ink is **the deck's OWN content colour for each scene's sampled
  bottom ground** — `--fg` on a light/neutral page, `--on-accent` on a saturated/colored/dark fill — so the
  subtitle text MATCHES the frame's content (a red **accent-fill** flood, whose content is white, gets a
  WHITE caption; a cream page gets dark), NOT an independent max-contrast pick (which clashed — a dark
  caption under white-on-red content). The per-glyph OUTLINE is **the frame's OWN sampled ground colour** —
  invisible on the clean caption zone, a subtle hair only where the ground varies, NEVER a white bar. The
  karaoke word is a distinct contrasting accent. The subtitle sits on the frame's own content background. **The only rule authors owe it:** keep content out of the bottom ~15% (heroes/airy
  beats are fine; a dense bottom-anchored beat must leave the zone clear — `keyframe_qa` gates it). Applies
  to BOTH aspects; a top-anchored 9:16 deck (bottom empty) reads it as the frame's own footer.
- **`"band"` (opt-in alt):** the caption is drawn in a **dedicated strip BELOW the content**, so it never
  overlaps and the canvas grows to `W×(H+band)` (a ~126–138 px strip at 1080p → e.g. 1920×1206). Reach for
  it only when you deliberately want a separate footer region instead of the caption on the frame.
  `meta.caption_band` = `"flush"` (default) **samples each scene's own bottom-edge colour** so the strip
  reads as that page's bottom margin; `"contrast"` = a fixed dark `--fg` subtitle bar. The band uses a
  slightly smaller face; content keeps the full 1080.

`meta.caption_scale` (default 1.0) tunes the caption font in EITHER mode — e.g. `0.9` shrinks it a
touch (and, in band mode, the strip shrinks with it).

```json
"meta": { "captions": true, "caption_mode": "band" }
```

Both modes time captions identically and write the same `out.srt`. `check_av.py` and the
A/V gate are unaffected (the strip changes only the video canvas height, not durations). Works on
BOTH tiers (html/chart + image slides), in 16:9 AND 9:16, and on light OR dark themes (the strip is
`--fg`, the text `--bg`, so contrast is guaranteed). `caption_mode` applies to the **local renderer**;
the optional Remotion tier renders captions its own way and ignores it.

---

## Readability guidelines (caption craft)

Keep each on-screen caption to:
- **≤ ~42 characters per line** (CJK is full-width — far fewer per line).
- **≤ 2 lines** (the renderer draws as many lines as the text needs; `validate.py` warns when a caption wraps past 3).
- **No widows** — don't let the last wrapped line be a single short word
  ("…to the / **future**"). It reads as a typo. `validate.py` warns on this.
- **On screen ≥ ~0.7 s** — a chunk that flashes faster is unreadable.
  `validate.py` warns when a derived segment is too brief.

These are the same rules `scripts/validate.py` enforces as warnings before render,
and `agents/critic-narrative.md` (R7) checks at the script stage. If a caption
trips them, the underlying narration sentence is usually too long — shorten it.

---

## How captions are timed (auto-derived from narration)

Each slide's burned caption **tracks the narration as it's spoken** — it is not one
static block. `render.py` (`_captions_for`) splits the `narration` into sentence-sized
chunks (`_split_caption_chunks`), times them across the slide's audio duration weighted
by length, and burns each chunk only during its own window (an ffmpeg `overlay … enable`
per segment). So the subtitle changes with the voice, sentence by sentence.

If a slide provides an explicit **multi-segment** `captions` array (≥ 2 entries), that
authored track is honoured verbatim instead. A single `captions` entry is treated as
fallback text, not a fixed full-duration line.

The **`.srt` sidecar** (`out.srt`) is always written from the same segments with their
`start`/`end` timings — useful for YouTube auto-captions or subtitle editors.

---

## Authoring captions

### Option A: Let it default (most common)

Leave `captions: []` in each slide. The full `narration` becomes the single
burned caption and the `.srt` entry.

### Option B: Explicit per-phrase segments

Add timed entries manually if you want the `.srt` to have fine-grained
timestamps (e.g., for YouTube chapter-level accuracy):

```json
"captions": [
  { "start": 0.0, "end": 4.2, "text": "Here we see the raw undersampled k-space." },
  { "start": 4.2, "end": 9.0, "text": "After reconstruction, artifacts disappear." }
]
```

The burned bar will show both texts joined as one block for the whole slide.
The `.srt` will have two separate entries with exact timing.

---

## Safe-margin notes

| Format | H | Bottom margin | Font size |
|---|---|---|---|

For vertical video (use `--vertical` flag), the caption bar sits higher
above the bottom edge proportionally — safe for mobile display.
The 6% bottom margin avoids the UI chrome on most platforms.
