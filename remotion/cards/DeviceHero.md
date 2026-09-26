# DeviceHero

**Identity:** the product on its device — phone, tablet, laptop or monitor — rising into place with its screen shown whole: the user's own screenshot or recording. In the realistic look it turns a few degrees toward the viewer and settles.

**Use when:** the beat says THIS is the product — an introduction, a reveal, a return to the product after an argument. **Not when:** something is done on the screen (`DeviceDemo`); not several surfaces of one product (`SurfaceCarousel`); not when there is no real screen to show.

**Motion core:** one rise and, in the realistic look, one small turn — both finished by a third of the beat; then the device holds and the screen carries the frame (a recording keeps playing).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `device` | phone, tablet, laptop or monitor | the laptop is the default: a hero is usually the whole product |
| `look` | flat, real or screen | only `real` turns; absent: real on a dark beat, flat on a light one |
| `screen` | the screenshot or recording, prepared by `scripts/device_script.py` | a recording is spread over the beat, at most 2× speed |
| `placement` | center, left or right | where the device stands |
| `kicker` | a spaced label above the device | moves the device below the title band |

**Known traps:**
- A screenshot wider than the device's screen is refused: it is a capture of another device.
- A recording longer than the beat can hold at 2× is refused rather than sped past legibility.

**Reference:** `remotion/src/shots/DeviceHero.tsx`

**Provenance:** product-ui. **Family:** A.
