# Motion Grammar

## Ken Burns (the only motion type in v1)

Every slide has a `motion` object:

```json
"motion": {
  "type": "kenburns",
  "from": [x, y, zoom],
  "to":   [x, y, zoom]
}
```

`[x, y, zoom]`:
- `x`, `y` are **normalized pan anchors in 0.0 – 1.0** — the point of the frame
  the camera keeps centered as it zooms. `0.5, 0.5` = dead center, `0, 0` =
  top-left, `1, 1` = bottom-right. (At `zoom == 1.0` the anchor has no effect;
  it only matters once you zoom in.)
- `zoom` is a scale multiplier (`1.0` = no zoom). Animating from the `from`
  zoom to the `to` zoom over the slide is the Ken Burns push.

**Default (from `storyboard.py`):**
```json
"motion": { "type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12] }
```

This is a gentle centered 1.0 → 1.12 zoom — barely noticeable, but it kills the
"static screenshot" look.

### Motion guidelines

| Situation | Recommendation |
|---|---|
| Default, nothing to highlight | Keep the centered default: `[0.5,0.5,1.0] → [0.5,0.5,1.12]` |
| Narration calls out a region | Move the `to` anchor toward that region (e.g. top-right ≈ `[0.8, 0.2, …]`) and zoom in so it lands centered |
| Diagram with fine text | Don't zoom past 1.25 — text softens at zoompan's scale limit |
| Zoom delta | Keep ≤ 0.20; larger values cause visible jitter in ffmpeg zoompan |

Zoom toward a region **only when the narration explicitly references it.**
Unmotivated motion is distracting.

---

## Callouts

Callouts are static overlays drawn on top of the zoomed slide (they do not
zoom with the Ken Burns effect — they stay fixed in frame).

```json
"callouts": [
  {
    "at": 0.0,
    "box": [x0, y0, x1, y1],
    "style": "highlight",
    "label": "Peak SNR"
  }
]
```

### Coordinate system

All four values in `box` are **normalized 0.0 – 1.0** of the output frame
(not the original slide image). `[0, 0, 1, 1]` = full frame.
`[0.1, 0.4, 0.6, 0.7]` = a horizontal band across the left half.

### Styles

| Style | Visual | Use when |
|---|---|---|
| `highlight` | Translucent yellow fill + yellow outline | "Look at this region broadly" |
| `box` | Solid red outline, no fill | Precise UI element or number |
| `arrow` | Red outline on the target box | Pointing to a single feature |

`arrow` and `box` use the same rendering (red outline); the distinction is
semantic — use `arrow` when your narration says "here" or "this arrow shows".

**Cap at ONE primary callout per slide.** Multiple callouts compete for
attention and dilute the message.

### `at` field

Currently unused in v1 rendering (callout is static for the whole slide).
Set `at: 0.0`. It is reserved for future timed callout support.

---

## Full Example

A slide where the narration says "notice the reconstruction error in the top-right corner":

```json
{
  "index": 3,
  "narration": "Notice the reconstruction error in the top-right corner — it disappears entirely after the compressed-sensing pass.",
  "motion": {
    "type": "kenburns",
    "from": [0.5, 0.5, 1.0],
    "to": [0.8, 0.2, 1.18]
  },
  "callouts": [
    {
      "at": 0.0,
      "box": [0.62, 0.05, 0.95, 0.38],
      "style": "box",
      "label": "Recon error"
    }
  ]
}
```

The camera starts centered and drifts the anchor to the top-right
(`x=0.8, y=0.2`) while zooming to 1.18, so the highlighted corner ends up
centered in frame as the narration points to it.
