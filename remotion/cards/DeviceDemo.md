# DeviceDemo

**Identity:** a phone, tablet, laptop or monitor showing the product's OWN screens — the user's screenshots or recording — or a screen the film drew, and performing one operation on them: type into a field, tap, scroll, drag. Each step happens on the word the narration says; the camera pushes in wherever a screenshot's text would be too small to read.

**Use when:** the beat's claim is how an interface is USED — "search, open, scroll to it" — shown on the product's real screens, or on a screen the film draws for an interface that does not exist yet. **Not when:** not a list of features in one place (`PointerTour`); not the product as an object with nothing done on it (`DeviceHero`).

**Motion core:** the device is there from the first frame, showing its first screen; then only the steps move — a ripple where a finger lands, typed words at the caret, a fling that settles. The push-in is computed, not styled: it zooms exactly as far as the target's text needs to match the caption, capped at 4×. A screen the film drew gets the beat's own `t` (0→1 across the whole beat — the same clock a numeric `at` uses), not the moment ITS screen appears: on a later screen part of its animation has already played.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `device` | phone, tablet, laptop or monitor (a tablet turns to landscape when its first screen is a landscape capture) | touch devices tap with a ring; laptop and monitor move a cursor |
| `look` | flat, real or screen | absent: real on a dark beat, flat on a light one; `screen` drops the body entirely |
| `steps` | the script — `screen` (a screenshot, a recording, or `{"object": …}`: a screen the film drew), `type`, `tap`/`click`, `scroll`, `drag`, `mark` — prepared by `scripts/device_script.py` | each step on its cue; too many for the beat is a refusal in seconds, never a squeeze |
| `camera` | `"still"` turns the push-in off | the whole device stays in frame; small text stays small |
| `placement` | center, left or right | where the device stands in the content zone |
| `kicker` | a spaced label above the device | moves the device below the title band |

**Known traps:**
- A text target that is not in the screenshot, or is there twice without `nth`, is refused with the text that WAS recognised — the ring must land on what the film names.
- A `type` step paints the field's own colour over the field's INNER box before typing — without that the placeholder and the typed words both show — so an icon inside the field (a search magnifier, a mic) is hidden while typing. Neither geometry nor OCR tells an icon from placeholder text (OCR reads a magnifier as "Q"), and a placeholder word left beside typed text is the worse failure.
- A push-in near the device's edge stays on the device: the zoomed view keeps inside the device's face — its screen and bezel, not a laptop's base or a monitor's stand — along any axis the face is larger than the view, and centres on it along the other.
- The push-in's view is the content zone, not the frame: a zoomed device is cropped at the caption band's top edge and the caption always sits on the film's own ground — filling the frame, it laid the screen's rows under the burned caption.
- A script step without its prepared time (`t0`/`ta`/`t1`), or a recording without its `spans`, is refused — never re-timed or drawn black.
- A long screenshot scrolls only within its real overflow; a fling may overshoot 4% and springs back.
- The standalone demo is skeleton bars with no text, so no demo copy exists to leak into a film — and a film may not show it: a `page` screen is refused.
- A recording plays as it was recorded: a `type`, `tap`, `click`, `drag` or `scroll` on it is refused (a finger over a video would perform an action the video does not show); point at something on it with `mark`. Its first frame is held until it plays and its last until it has gone, never black.
- A placeholder set in lowercase x-height letters only ("username") types at about half size: the typed size is taken from the placeholder's ink, and those letters have no ascenders to measure. A capitalised or CJK placeholder is exact.
- A label that nearly fills its button (a 44 px label in a 56 px button) is measured as the whole button — about 1.8× its ink — so the push-in stops short, silently: around such a label the button is the only ground the measure sees. A label with room above and below it inside its button is exact.
- A screen the film drew (an `object` from its workshop) is tapped and dragged by coordinates only: there is no screenshot to find text in, and typing or scrolling on it is the object's own animation — both are refused by name. The camera holds on it: there is no text height to push in to.
- An object that declares a `META.aspect` narrower or wider than the screen is letterboxed inside it, on the screen's own black — a 16:9 object on a phone screen fills about a quarter of its height. Taps still target `[x, y]` fractions of the whole SCREEN, not the letterboxed picture, so a tap meant for the object's own content must account for the bars.
- A `tablet` with an object screen never turns to landscape: `_oriented` reads a screenshot's or recording's own file to decide, and an object has no file — it stays whatever `device` says (portrait, by default).

**Step script:** `shot_props.steps` is a list, one object per step, each naming exactly one kind:
- `{"screen": {"image": "<file in the out dir>"}}`, `{"screen": {"video": "<file>", "from": 0, "to": 6.5}}` (seconds; `to` required), or `{"screen": {"object": {"id": "<Name>", "props": {...}}}}` — a screen the film drew — the first step is always a screen; a later one replaces the current screen, `"via": "push"` (default) or `"fade"`.
- `{"type": "上周的反馈", "into": T}` — Latin one key at a time, Chinese two glyphs a keystroke, or your own chunks as a list of strings.
- `{"tap": T}` / `{"click": T}` — one step, two spellings: a phone or tablet draws a ring, a laptop or monitor moves its cursor and clicks.
- `{"scroll": 0.6}` — a fraction of a LONG screenshot's overflow, added to what was scrolled before (downward only); a screenshot no longer than the screen has nothing to scroll and is refused.
- `{"drag": {"from": T, "to": T}}` — the push-in frames both ends.
- `{"mark": T, "video": 3.2}` — recordings only: points at something at that moment of the recording (`video` optional).
- A target `T` is `[x, y]`, fractions of the VISIBLE screen at the current scroll (not of the image), or `{"text": "反馈汇总", "nth": 1}` — words recognised in the screenshot on a Mac (`nth` 1 = top-most, then left-most).
- `"at": {"cue": "the words"}` acts when the voice says them (`"offset": seconds` shifts it); a number is a fraction of the beat from 0 to 1. Steps without `at` spread evenly between cued ones.
- Time each step needs (`runtime/deviceSpec.json`): a screen change 0.5 s, a tap or click 0.6 s, a Latin key 0.15 s, a Chinese word 0.35 s, a scroll or drag 0.9 s, a mark 0.6 s, plus a 0.35 s camera lead before every gesture. A beat's first 0.4 s is the cut into it, so the first action's words must come about 0.75 s into its line or later. Too much for the beat is refused, in seconds.
- A recording is spread from `from` to `to` over its screen's time: at most 2× speed and never backwards (refused), under 0.5× said as slow motion.
- After `tts.py`, `python3 scripts/validate.py <out_dir>` checks all of it — shape, files, text targets, time — and names every problem before a render.

**Measured:** 3.9% ink (clip median) · 16.0% footprint · 0.0 motion · 3.2% ink on the settled frame. Measured on the register's own demo — one phone of skeleton rows and a single tap, no screenshot — so the numbers describe the empty stage: in a film the density is the product's own screens.

**Reference:** `remotion/src/shots/DeviceDemo.tsx`

**Provenance:** product-ui. **Family:** A. **Ground:** `bg` (`DNA_GROUND_TOKEN`), measured light.
