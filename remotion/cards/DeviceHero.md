# DeviceHero

**Identity:** the product on its device — phone, tablet, laptop or monitor — rising into place with its screen shown whole: the user's own screenshot or recording. In the realistic look it turns a few degrees toward the viewer and settles.

**Use when:** the beat says THIS is the product — an introduction, a reveal, a return to the product after an argument. **Not when:** something is done on the screen (`DeviceDemo`); not several surfaces of one product (`SurfaceCarousel`); not when there is no real screen to show.

**Motion core:** one rise and, in the realistic look, one small turn — both finished by a third of the beat; then the device holds and the screen carries the frame (a recording keeps playing).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `device` | phone, tablet, laptop or monitor (a tablet turns to landscape with a landscape capture) | the laptop is the default: a hero is usually the whole product |
| `look` | flat, real or screen | only `real` turns; absent: real on a dark beat, flat on a light one |
| `screen` | `{"image": file}`, `{"video": file, "from": s, "to": s}` (both optional: the whole recording), or `{"object": {"id": …}}` — a screen the film drew (scripts/workshop.py); prepared by `scripts/device_script.py` | a recording is spread over the beat, at most 2× speed; under 0.5× is said as slow motion |
| `placement` | center, left or right | where the device stands |
| `kicker` | a spaced label above the device | moves the device below the title band |

**Known traps:**
- A screenshot wider than the device's screen is refused, and the refusal names the device whose screen it fits (a 16:9 capture on a laptop: use `monitor`).
- A recording longer than the beat can hold at 2× is refused rather than sped past legibility.
- The entrance never leaves the rect the geometry fitted above the caption band: the device grows upward from its bottom edge, its perspective is centred on that edge, and in the realistic look it is drawn a few percent smaller so its turn still fits.
- A film's hero must name its `screen` — a screenshot, a recording, or a screen the film drew; its skeleton demo is the standalone preview only, and a missing or `page` screen is refused. A recording without `spans` is refused, not drawn black.

**Measured:** 9.7% ink (clip median) · 48.4% footprint · 0.0 motion · 8.7% ink on the settled frame. Measured on the register's own demo — a laptop showing skeleton rows — so the numbers describe the device, not a film's screen, which is what fills it in a film.

**Reference:** `remotion/src/shots/DeviceHero.tsx`

**Provenance:** product-ui. **Family:** A. **Ground:** `bg` (`DNA_GROUND_TOKEN`), measured light.
