# ProductPage

**Identity:** a real 2x capture of a product, a page or a document, shown as itself under a 2.5D page camera. The page floats on the film's ground and its elements act: they land in their own slots, lift toward the lens out of an accent under-glow, get typed into, clicked, rack-focused and called out with a leader line.

**Use when:** the beat SHOWS a thing that exists and can be captured — the product's own screen, the web page or paper that says so. It beats a rebuilt mock whenever the real thing is available. **Not when:** there is no capture (it refuses), or the beat is an idea with no page behind it.

**Motion core:** the camera keys (`{f, cx, cy, zoom, rx, ry, rz, ease}`) are authored over `nominal` frames; the beat's real length stretches the tail through a smooth map, keeping the entrances at their speed. The page is laid out once at the shot's largest zoom and moved by one 3D transform; moves land with linear deceleration and holds are pixel-still, so it neither steps nor shimmers (picture_glide_qa). An act whose `text` the voice speaks lands on the word (cue key `acts.<i>`); the beat's clock is never warped (`CLOCK = 'own'`).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the capture, a file in the film's folder (`scripts/promo_capture.py` writes it) | required; the page and every crop an act lifts come from it |
| `w` | the capture's CSS width (its pixels / 2) | wrong, and every box lands beside its element |
| `h` | the capture's CSS height | as `w` |
| `keys` | the camera's poses | a tilted first key (rx 14-24) reads as an arrival; one decisive move then a still hold — a segment slower than 8 px a frame is collapsed into a hold (a creeping page shimmers); effective zoom ≤ 2 (the capture's density) |
| `acts` | what happens on the page: `pop`, `lift`, `focus`, `ring`, `type`, `cursor`, `callout` (references/promo-film.md) | one or two per beat; more and the page becomes busy |
| `nominal` | the frame count `keys` and `acts` are authored over | default: the last key's frame |
| `maxZoom` | the capture's density | 2 for a 2x capture; past it the camera clamps |

**Known traps:**
- The boxes come from the capture's layout file (`caps/<n>.layout.json`); a guessed box lands an element beside its slot.
- The camera frames the zone above the caption band and the page fades into the ground under it; do not aim a key at the page's bottom strip expecting it above the caption.
- A callout keeps its label on the frame by itself (side and clamp decided at the frame it lands); authoring it far off still reads as far off.

**Refuses:** no `src`; `keys` or `acts` that is not a list.

**Reference:** `remotion/src/shots/ProductPage.tsx`, `remotion/src/promo/`
