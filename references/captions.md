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

---

## Readability guidelines

Keep each caption block to:
- **≤ 42 characters per line**
- **≤ 2 lines**

Longer text wraps fine technically but exceeds safe reading speed for
most viewers. If a caption needs more than 2 lines, the narration sentence
is probably too long — shorten it.

---

## v1 caption behavior

In v1, each slide shows **one caption block** for its entire duration.

`render.py` joins all `captions[]` text segments with spaces to produce the
burned text:
```python
caption_text = " ".join(c["text"].strip() for c in _captions_for(slide)).strip()
```

If `captions[]` is empty, the full `narration` string is used as the single
caption block.

The **`.srt` sidecar** (`out.srt`) always uses the individual `captions[]`
entries with their precise `start`/`end` timings — useful for YouTube
auto-captions or subtitle editors.

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
