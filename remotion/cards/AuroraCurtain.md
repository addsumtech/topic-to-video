# AuroraCurtain

**Identity:** an aurora as a folded curtain of light in a night sky, drawn by runtime/volume as the line-of-sight integral a real one is — one sheet whose folds brighten where they turn edge-on, a sharp lower border, rays that stand along the field and travel along the arc, faint red tops, the far end receding toward the horizon — coloured by the altitude each part glows at, over a dark ridge that gives the sky its scale.

**Use when:** the subject is the aurora itself, or the claim is that its colour is its height ("颜色，就是高度"), light in the upper atmosphere, a curtain the solar wind lights. Give it the film's `bands` and the frame also draws the key: a ruler beside the curtain on the shader's own projection, each band's label at the height its colour glows. **Not when:** the beat is about the magnetosphere or the Sun (a diagram register), or a photograph of an aurora carries it better (PhotoPlate / a WorldStage image).

**Motion core:** the curtain lights up over the first 0.28 of the clip; the ruler and its labels arrive 0.12–0.34; the title 0.06–0.26; the rays drift along the arc and the folds travel slowly throughout; with `surgeAt`, a substorm brightening crests at that point of the beat (rising over 0.05, ebbing over 0.22) and runs along the sheet.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the statement, one or two lines, top left | empty draws no title |
| `kicker` | a mono line above it, in the DNA accent | — |
| `bands` | 1–6 `{label?, note?, from, to (km), color, gain?}` — the film's colour key | with labels or `ticks`, a ruler is drawn and the curtain fits under the title; without `bands` the curtain takes the sourced emission physics (volumeCore.AURORA_BANDS) and draws NO numbers |
| `ticks` | altitudes (km) to mark on the ruler | none given, none drawn |
| `unit` | the ruler's unit word | — |
| `surgeAt` | a point of the beat (0..1) where a substorm brightening crests | owns a `swell` sound (SOUNDS); absent: no surge and no sound |
| `sheets` | 1–3 parallel sheets | 1 is a single clean arc, 3 a busy display |
| `seed` | which folds and rays | — |

**Known traps:**
- Bands may not overlap (one altitude, one colour); a second emission at the same height is a separate beat or object.
- The ruler is exact at the curtain's near end (its left); the far end recedes and its altitudes read lower — keep tick labels on the left.
- Under a light DNA the register still paints a night sky (its measured ground is a literal dark): the aurora is not visible on a page.
- Its own sound rides with `meta.sound_design` (or `meta.shot_sounds: true`).

**Refuses:** overlapping or malformed bands; ticks that are not numbers; no WebGL context (a loud error, never an empty sky).

**Reference:** `remotion/src/shots/AuroraCurtain.tsx`, `remotion/src/runtime/volume.tsx`
