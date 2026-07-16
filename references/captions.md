# Captions

**No libass required.** Captions are burned directly with PIL using the
bundled `assets/fonts/DejaVuSans.ttf`. The ffmpeg pipeline composites a
pre-drawn PNG overlay on top of each slide — no subtitle filter, no libass,
no special ffmpeg build needed.

---

## How the caption bar looks

- **Position:** Centered, near the bottom of the frame.
- **Background:** Semi-transparent black rectangle (alpha ≈ 140/255).
- **Text:** White, horizontally centered within the bar.
- **Font size:** ~4.5% of frame height (i.e., `int(H * 0.045)`).
  At 1080p that's ~48 px; at 1920p (vertical) it's ~86 px.
- **Bottom safe margin:** ~6% of frame height (`int(H * 0.06)`).
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

### Placement — overlay (default) vs a band BELOW the content

`meta.caption_mode` controls WHERE the burned caption sits:

- **`"overlay"` (default):** **NO background bar** — the caption text is burned flush at the **very
  bottom** of the W×H content in the deck's `--fg` ink with a subtle **opposite-luminance outline** (drawn
  per glyph), and the karaoke word is contrast-picked vs the frame's own `--bg`. A flat strip — even a
  theme-coloured one — reads as a heavy block, so there is none; the outline keeps the text legible over
  ANY ground (empty frame, a tint, a photo) on any theme + aspect. The tradeoff: content that reaches the
  bottom ~15% of the frame can sit *under* the caption. Authors must keep content clear of that
  zone (heroes/airy beats are fine; a dense bottom-anchored beat can collide). This applies to BOTH
  aspects; a top-anchored 9:16 deck (bottom zone empty) reads it as the frame's own footer.
- **`"band"`:** the caption is drawn in a **dedicated strip BELOW the content**, so it
  **never overlaps the slide**. The output canvas grows to `W×(H+band)` (a ~138 px strip at
  1080p → 1920×1218). By default (`meta.caption_band` = `"flush"`) the strip **samples each scene's own
  bottom-edge colour** and continues it, so it reads as that page's **bottom margin** — seamless whether
  the slide ground is off-white, a tint, a full **accent-fill** (a red divider → a red strip), or a photo;
  the text auto-flips to whichever of `--fg`/`--bg` contrasts that ground. Set `meta.caption_band` =
  `"contrast"` for a fixed dark **subtitle bar** instead (`--fg` strip, `--bg` text). Contrast stays
  legible either way. The band uses a slightly smaller face than the overlay bar (it has its own
  strip, so it needn't shout). Content keeps the full 1080 — no bottom-clearance needed. Pick band
  when the frame is dense or when a clean, un-obscured content area matters more than exact 16:9
  output dimensions.

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
| 16:9 (1920×1080) | 1080 | 65 px | ~48 px |
| 9:16 vertical (1080×1920) | 1920 | 115 px | ~86 px |

For vertical video (use `--vertical` flag), the caption bar sits higher
above the bottom edge proportionally — safe for mobile display.
The 6% bottom margin avoids the UI chrome on most platforms.
