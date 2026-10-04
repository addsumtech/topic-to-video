# KSpaceToPicture

**Identity:** two panels joined by the transform: on the left an image's k-space, written one row at a time from its centre outward; on the right the picture computed from exactly the rows written so far, which sharpens as a WHOLE with every row. The data is not the picture — the picture is computed from it.

**Use when:** a picture is computed from measured data, and every row of data sharpens the WHOLE picture rather than adding one strip of it — how an MR image is made from k-space, what a scan that stops early still shows. **Not when:** the beat is about reading k-space's regions (`KSpaceAnatomy`), the starburst on its own (`KSpaceReal`), or one phase-encode step (`PhaseEncodeStep`).

**Motion core:** k-space rows are written from the centre outward (or top down) between 0.14 and 0.8 of the beat while, beside it, the inverse transform of exactly those rows steps from blur to sharp; the transform arrow draws on first and the finished picture's frame lights in the accent.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `srcKspace` | the k-space magnitude image, a public-dir path — written with `srcFrames` by `scripts/kspace_frames.py` from the film's own image | required in a film; with neither, the register computes its own Shepp–Logan phantom |
| `srcFrames` | that k-space's reconstructions in fill order, the last the whole image | more frames read as a smoother sharpening; at most 64 |
| `order` | how the rows were filled when the frames were computed: `centre` (default) or `top` | must match the frames; `top` fills the picture's detail unevenly and is the shape to show only when that is the point |
| `rows` | the k-space's row count (default 256) | the reveal advances in whole rows; set it to the matrix the frames were computed at |
| `kspaceLabel` | the left panel's name, above it | fitted to the panel's width |
| `kspaceNote` | one line under the left panel | fitted to the panel's width |
| `imageLabel` | the right panel's name, above it | fitted to the panel's width |
| `imageNote` | one line under the right panel | fitted to the panel's width |
| `transformLabel` | the arrow's name | drawn only where it fits between the panels |
| `credit` | the source image's attribution, at the foot | the licence of a real image usually requires it |
| `title` | a line in the title band | fitted to 80% of the width |
| `kicker` | a small spaced label above the title | follows the DNA's label spacing |

**Known traps:**
- A film hands `srcKspace` and `srcFrames` together or not at all: half a pair would light the rows of one image beside the reconstructions of another, so it is refused. Both are `src` props because the library's sweeps feed copy to every other string prop.
- The frames must be computed in the `order` the reveal lights them, at the matrix `rows` names — `scripts/kspace_frames.py` writes them that way (k-space as log magnitude above its median, every frame on one white point, the full inverse checked to return the image) and prints the props.
- Both panels keep a scan viewport's black on every ground, so on a light film the frame is a pale page with two black squares in it: ground reach measures about 40% of the frame following the film's ground.
- Its standalone preview is a computed modified Shepp–Logan phantom (its 2-D FFT and the inverse of the rows written so far, the full inverse checked against the phantom). validate.py requires a film's own `srcKspace` and `srcFrames`, so the phantom is never a film's picture by accident.
- Promoted from the film 磁共振成像是怎么把人体内部变成图像的, which handed it a real T1 axial slice (CC BY-SA 4.0) and that slice's k-space and 24 centre-out reconstructions; it was judged there against: 遮住字幕：看得出左边的方阵一行行被写满、右边同时出现并越来越清楚的人脑切片，二者由“傅里叶变换”箭头连着. The first film that meets a trap here writes it down.

**Refuses:** half a data pair or an empty path; more than 64 frames; an `order` other than `centre`/`top`; a `rows` outside 8–4096; a computed phantom whose full inverse does not return it.

**Measured:** 8.4% ink (clip median) · 42.6% footprint · 0.0067 motion. Measured on the register's own defaults — its computed phantom, so the numbers describe the preview, not a film's image.

**Reference:** `remotion/src/shots/KSpaceToPicture.tsx`

**Provenance:** scientific. **Family:** S. **Ground:** `bg` (`DNA_GROUND_TOKEN`), measured dark.
