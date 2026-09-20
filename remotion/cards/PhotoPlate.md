# PhotoPlate

**Identity:** a real photograph mounted as a plate at its own proportions; the film's marks arrive one by one on a lifted plane — a ring at a point in the picture, an elbow leader, a callout chip — and a caption and licence line land beneath.

**Use when:** the claim is "look at the actual thing, and here is what to notice in it" — a real image and up to five features the narration names, in the order it names them. **Not when:** there is no real photograph (it refuses); the image is cited by its catalogue data (use MuseumLabel), compared with another (use RealVersus), or shown as a reconstruction (use ScanReconstruct).

**Motion core:** the plate fades in and settles from a slight shrink over 0.02–0.26, the title with it; the marks arrive from 0.30, spread evenly across the next 0.42 of the clip, each ring scaling in with its leader and chip over 0.20; the caption and credit land over 0.68–0.90; then it holds still.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the photograph (a path in the film's public dir) | the whole premise; framed in full at its own proportions when `imageAspect` is known |
| `title` | a small kicker above the plate, in the accent | uppercased and tracked unless the DNA says otherwise; empty draws nothing |
| `caption` | what the plate IS, in the display face under it | one line keeps the plate tall; a longer caption reserves a second line and shrinks the plate; past two lines it is cut off |
| `marks` | 0–5 points `{x, y, label?, n?}` in fractions of the photograph | none shows the photograph alone, centred; a few give rings with chips at their heights. A narrow plate moves left and the chips sit in the right margin; a wide one keeps them inside the plate. Crowded marks push their chips apart along a column (the leader bends to follow); `n` prefixes the chip with an accent number; a mark with neither label nor `n` is a bare ring |
| `imageAspect` | the photograph's width ÷ height (render_remotion.py fills it from the file) | the plate takes this aspect, capped between 0.62 and 2.3; unset, the plate is a 2.3:1 landscape strip and the image is cropped to fill |
| `credit` | the licence line under the caption | small mono in the dim colour; flows under however many lines the caption took |

**Known traps:**
- Marks used to be invented for the film: a mark without coordinates ringed the photograph's dead centre, out-of-range ones were clamped to the edge, and `marks` defaulted to two demo chips ("what to notice here", "and here"). Now coordinates are required, more than five throws, and the default is no marks. Omitting `caption` still prints `the thing itself`.
- Without `imageAspect` a portrait photograph is cropped hard (a delivered film lost 67.4% of a picture's height) and marks point at different features; render through render_remotion.py or pass it.
- The caption is cut at two lines without a signal — a longer one belongs in the narration.
- When the chips need more height than the plate has, they are spread evenly down it and may sit well away from their rings.

**Refuses:** a missing or blank `src`; `marks` not an array or more than 5; a mark whose `x` or `y` is missing or outside 0..1; a mark that falls in the part of the photograph the aspect cap crops away.

**Reference:** `remotion/src/shots/PhotoPlate.tsx`
