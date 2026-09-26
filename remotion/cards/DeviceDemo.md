# DeviceDemo

**Identity:** a phone, tablet, laptop or monitor showing the product's OWN screens — the user's screenshots or recording — and performing one operation on them: type into a field, tap, scroll, drag. Each step happens on the word the narration says; the camera pushes in wherever a screenshot's text would be too small to read.

**Use when:** the beat's claim is how an interface is USED — "search, open, scroll to it" — and real screens exist. **Not when:** there are no real screens (a concept, an unbuilt product — use an interface register such as `SurfaceCarousel`, or wait for the app templates); not a list of features in one place (`PointerTour`); not the product as an object with nothing done on it (`DeviceHero`).

**Motion core:** the device arrives with its first screen; then only the steps move — a ripple where a finger lands, typed words at the caret, a fling that settles. The push-in is computed, not styled: it zooms exactly as far as the target's text needs to match the caption, capped at 4×.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `device` | phone, tablet, laptop or monitor | touch devices tap with a ring; laptop and monitor move a cursor |
| `look` | flat, real or screen | absent: real on a dark beat, flat on a light one; `screen` drops the body entirely |
| `steps` | the script — `screen`, `type`, `tap`/`click`, `scroll`, `drag`, `mark` — prepared by `scripts/device_script.py` | each step on its cue; too many for the beat is a refusal in seconds, never a squeeze |
| `camera` | `"still"` turns the push-in off | the whole device stays in frame; small text stays small |
| `placement` | center, left or right | where the device stands in the content zone |
| `kicker` | a spaced label above the device | moves the device below the title band |

**Known traps:**
- A text target that is not in the screenshot, or is there twice without `nth`, is refused with the text that WAS recognised — the ring must land on what the film names.
- A `type` step paints the field's own colour over the field's INNER box before typing — without that the placeholder and the typed words both show — so an icon inside the field (a search magnifier, a mic) is hidden while typing. Neither geometry nor OCR tells an icon from placeholder text (OCR reads a magnifier as "Q"), and a placeholder word left beside typed text is the worse failure.
- A push-in near the device's edge stays on the device: the zoomed view keeps inside the device's face — its screen and bezel, not a laptop's base or a monitor's stand — along any axis the face is larger than the view, and centres on it along the other.
- A script step without its prepared time (`t0`/`ta`/`t1`), or a recording without its `spans`, is refused — never re-timed or drawn black.
- A long screenshot scrolls only within its real overflow; a fling may overshoot 4% and springs back.
- The standalone demo is skeleton bars with no text, so no demo copy exists to leak into a film.

**Reference:** `remotion/src/shots/DeviceDemo.tsx`

**Provenance:** product-ui. **Family:** A.
