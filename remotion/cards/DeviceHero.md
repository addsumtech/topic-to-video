# DeviceHero

**Identity:** the product on its device — phone, watch, tablet, laptop or monitor — rising into place with its screen shown whole: the user's own screenshot or recording, or a screen the film drew. In the realistic look it turns a few degrees toward the viewer and settles.

**Use when:** the beat says THIS is the product — an introduction, a reveal, a return to the product after an argument — shown on the product's real screen, or on a screen the film draws for an interface that does not exist yet. **Not when:** something is done on the screen (`DeviceDemo`); not several surfaces of one product (`SurfaceCarousel`).

**Motion core:** one rise and, in the realistic look, one small turn — both finished by a third of the beat; then the device holds and the screen carries the frame (a recording keeps playing). A screen the film drew gets that same beat `t`, so its own animation's first third plays under the rise, not from its own zero.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `device` | phone, watch, tablet, laptop or monitor (a tablet turns to landscape with a landscape capture) | absent: the kind of the model the capture came from, else the laptop — a hero is usually the whole product |
| `model` | a real device from `runtime/deviceSpec.json` `models` — absent: read off the capture's pixel size (`scripts/device_models.py`) | drawn in THAT model's published proportions: the capture fills its screen exactly, the bezel is the real bezel, the corners concentric |
| `look` | flat, real or screen | only `real` turns; absent: real on a dark beat, flat on a light one |
| `screen` | `{"image": file}`, `{"video": file, "from": s, "to": s}` (both optional: the whole recording), or `{"object": {"id": …}}` — a screen the film drew (scripts/workshop.py); prepared by `scripts/device_script.py` | a recording is spread over the beat, at most 2× speed; under 0.5× is said as slow motion |
| `placement` | center, left or right | where the device stands |
| `kicker` | a spaced label above the device | moves the device below the title band |

**Known traps:**
- THE DEVICE IS THE MODEL THE CAPTURE CAME FROM: 416x496 is a 46 mm Apple Watch Series 12, 374x446 the 42 mm, 1206x2622 a 6.3-inch iPhone 18 Pro (also the iPhone 17: name `model: "iphone-17"`), 1320x2868 the Pro Max, 1640x2360 the 11-inch iPad, 2560x1664 the 13-inch MacBook Air, 3024x1964 the 14-inch MacBook Pro — or those sizes at 1/2 or 1/3. Any other size is drawn on the generic kind and validate WARNS naming the size. A `model` the capture's size contradicts is refused.
- The watch has a crown with knurled ridges and a side button on its right, a sport band through lugs top and bottom (pin above, sizing holes below), a concentric display measured off watchOS's own corner mask. Its screen at 9:16 is drawn about 1.1x a 416 px capture — validate says so (media_res_qa's WARN scale), not an error.
- A picture that is ALREADY a device mockup (transparent around a drawn frame) is warned: a device around it frames a frame.
- A label set ON the device's body or band is `text_safe_qa`'s finding ("ON THE DEVICE").
- A screenshot wider than the device's screen is refused, and the refusal names the device whose screen it fits (a 16:9 capture on a laptop: use `monitor`).
- A recording longer than the beat can hold at 2× is refused rather than sped past legibility.
- The entrance never leaves the rect the geometry fitted above the caption band: the device grows upward from its bottom edge, its perspective is centred on that edge, and in the realistic look it is drawn a few percent smaller so its turn still fits.
- A film's hero must name its `screen` — a screenshot, a recording, or a screen the film drew; its skeleton demo is the standalone preview only, and a missing or `page` screen is refused. A recording without `spans` is refused, not drawn black.
- An object that declares a `META.aspect` narrower or wider than the screen is letterboxed inside it, on the screen's own black — a 16:9 object on a phone screen fills about a quarter of its height.
- A `tablet` with an object screen never turns to landscape: `_oriented` reads a screenshot's or recording's own file to decide, and an object has no file — it stays whatever `device` says (portrait, by default).

**Measured:** 9.7% ink (clip median) · 48.4% footprint · 0.0 motion · 8.7% ink on the settled frame. Measured on the register's own demo — a laptop showing skeleton rows — so the numbers describe the device, not a film's screen, which is what fills it in a film.

**Reference:** `remotion/src/shots/DeviceHero.tsx`

**Provenance:** product-ui. **Family:** A. **Ground:** `bg` (`DNA_GROUND_TOKEN`), measured light.
