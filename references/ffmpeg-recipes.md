# ffmpeg Recipes

These are representative/simplified ffmpeg invocations based on what `render.py`
does. They help with debugging, manual re-runs, and codec troubleshooting.
Note: the live `render.py` command also carries one overlay input per timed caption segment (each gated with
`enable='between(t,start,end)'`), callouts, the brand bug, the seam transition and the platform-safe frame — so the
real command is more complex than these minimal examples.

---

## 1. Per-slide clip — the Ken Burns move

An image slide's move is NOT an ffmpeg filter. `render.py` draws every frame itself and pipes it to ffmpeg as
rawvideo:

* `_fit_frame` fits the slide image to the W×H canvas once (`fit_NN.png`);
* `_kenburns_window(params, frames, on, W, H)` is the move on frame `on` — a FLOAT crop window, never rounded:
  `z = z0 + (z1 - z0)·k`, `x = fx + (tx - fx)·k`, `y = fy + (ty - fy)·k`, `k = min(on, frames)/frames`,
  `frames = round(duration·fps)`; the window is `W/z × H/z` at `((W - W/z)·x, (H - H/z)·y)`, held inside the
  picture (zoom clamped to [1, 10], corner to [0, W - W/z]) exactly as zoompan held it;
* `_kenburns_frames` resamples that window whole to W×H with Pillow's Lanczos (`Image.resize(..., box=float
  window)`) on a few threads with a bounded look-ahead; a move that does not move (reduced motion, from == to) is
  the fitted frame's own bytes repeated;
* `_run_fed` streams the frames to ffmpeg, which overlays callouts / bug / captions and encodes:

```bash
python … | ffmpeg -y \
  -f rawvideo -pix_fmt rgb24 -s 1920x1080 -framerate 30 -i pipe:0 \
  -i audio/01.mp3 [-i co_01.png -i cap_01_00.png …] \
  -filter_complex "[0:v]null[v0];[v0][2:v]overlay=0:0[v2];…;[vN]scale=out_range=tv,format=yuv420p[vrange]" \
  -map "[vrange]" -map 1:a -t 10.0 -r 30 -pix_fmt yuv420p \
  -c:v libx264 -crf 18 -tune grain -x264-params chroma-qp-offset=2 \
  -c:a aac -ar 48000 -ac 1 -shortest clip_01.mp4
```

**The encode is part of the glide (`render._KB_X264`).** With the resample exact (0.004 px RMS on a slow pan over a
photo, encoded losslessly), x264's defaults at crf 18 put back 0.09–0.10 px — a WARN: on smooth content x264 codes a
slow move as quarter-pel motion vectors and drops the residual, so the picture steps a quarter pixel at a time.
Measured on that pan: crf 16 0.102, crf 14 0.090 (+100% bytes), `aq-mode=0` 0.084, `-tune grain` **0.040** (+8%
bytes). `-tune grain` also moves the PPS chroma QP offset (−2 → −4), and the `-c copy` concat decodes every clip with
the FIRST clip's SPS/PPS — so `chroma-qp-offset=2` pins it back; `test_a_ken_burns_clip_concats_with_the_films_other_
clips` holds the headers byte-identical to a programmatic clip's (and fails with the pin removed).

The clip's frame count is unchanged from the zoompan era (`-t duration -r fps`; two frames past it are offered and
ffmpeg stops reading when it has enough), so the per-clip cache, the `-c copy` concat and the A/V gate hold. The
cache key of an image slide carries `"kb": "lanczos-float1"`, so a clip cached by the old chain re-renders once.

**Why not zoompan (retired, with `meta.motion_ss`).** zoompan places its crop at WHOLE pixels of its input. The old
chain ran it in a `motion_ss`× supersampled space (scale up → zoompan → scale down), which only shrinks the step to
1/`motion_ss` px: a slow push or pan holds, then jumps, and the pixel jitter gate (`jitter_qa.py`) reads every tile.
Measured on the bench in `film_work/kenburns` (`bench/bench.py`: real `render._render_slide`, a UI screenshot with
13 px type, a chart, two public-domain photos; a push 1.0→1.12, a slow push 1.0→1.04 and a slow pan at 1.10;
5 s clips; jitter = jitter_qa's own estimator and judge against the exact move; sharpness = Laplacian variance of
the decoded luma over the fitted still's, at frame 0 and mid-move):

| aspect | method | cases | tiles ERROR / WARN / clean | worst RMS px | median RMS px | sharpness at rest | mid-move | render s per s of video |
|---|---|---|---|---|---|---|---|---|
| 16:9 | zoompan, `motion_ss` 2 (old default) | 12 | 128 / 0 / 0 | 0.420 | 0.371 | 0.83 | 0.72 | 5.0 |
| 16:9 | zoompan, `motion_ss` 4 | 3 | 34 / 0 / 0 | 0.245 | 0.201 | 0.80 | 0.66 | 17.2 |
| 16:9 | zoompan, `motion_ss` 8 | 1 | 0 / 8 / 3 | 0.111 | 0.103 | 0.57 | 0.50 | 63.4 |
| 16:9 | ffmpeg `perspective` (cubic, per frame) | 12 | 0 / 3 / 125 | 0.104 | 0.050 | 0.88 | 0.75 | 1.4 |
| 16:9 | float Lanczos, default encode | 12 | 0 / 3 / 125 | 0.103 | 0.048 | 0.98 | 0.78 | 1.1 |
| 16:9 | **float Lanczos + grain encode (shipped)** | 12 | **0 / 0 / 128** | 0.064 | 0.020 | 0.99 | 0.80 | 1.1 |
| 1:1 | zoompan, `motion_ss` 2 | 9 | 101 / 0 / 0 | 0.355 | 0.315 | 0.68 | 0.60 | 2.9 |
| 1:1 | **float Lanczos + grain encode (shipped)** | 12 | **0 / 0 / 136** | 0.060 | 0.021 | 0.94 | 0.78 | 0.5 |
| 9:16 | zoompan, `motion_ss` 2 | 9 | 81 / 0 / 0 | 0.381 | 0.280 | 0.72 | 0.64 | 6.8 |
| 9:16 | **float Lanczos + grain encode (shipped)** | 12 | 8 / 13 / 91 | see below | 0.035 | 0.92 | 0.82 | 2.0 |

Render time is wall-clock on a shared, loaded machine (load 10-14 on 10 cores), so read it as a ratio: the float
resample is ~4-5x faster than `motion_ss` 2 at every aspect. Peak memory (python + ffmpeg) 0.8-1.4 GB, about the
same as `motion_ss` 2; `motion_ss` 8 took 1.7 GB. Sharpness at rest is the Laplacian variance of frame 0 over the
fitted still's — higher is sharper; frame 0 of a push IS the fitted frame, where zoompan's up-and-down resample
softened UI type to 0.60 (screenshot 0.90 now, chart 0.86 vs 0.52).

**9:16 is not fully clean on the bench.** 7 of its 12 cases are; the rest: the chart under the default push reads
0.17 px on 3 tiles of its TITLE as it is carried towards the top edge (0.185 with the default encode, 0.38 under
zoompan); a 640 px photo (`rocket`) cover-fitted to 1080x1920 — upscaled 4.5x, almost no texture — reads pops of
1.6-15 px on 2-3 tiles, which are correlation failures on featureless windows (looked at: the worst, a 15 px "pop", is a window on the
rocket's smooth body — a vertical gradient with nothing to lock onto in y — identical frame to frame; zoompan read
the same two cases 10-11 ERROR tiles each, with pops up to 7 px);
and single "does not follow its geometry" WARNs on chart tiles holding only steep data lines (the aperture problem:
the same WARN appears on the lossless exact frames). The 9:16 fixture films (`tests/test_jitter_html.py`,
GATE_RENDER=1) and a 4-slide 9:16 proof film read clean.

`perspective` (ffmpeg 8.1: `eval=frame` with the `in` frame counter, 1/256 px corners, cubic) is also jitter-clean,
but softer than Lanczos (screenshot at rest 0.73 vs 0.89) and slower; it is not used. `zoompan` with any
`motion_ss` stays an ERROR or WARN, and costs more the higher it goes.

---

## 2. Concatenation

After all per-slide clips are rendered, they are concatenated with the
ffmpeg concat demuxer:

```bash
ffmpeg -y -f concat -safe 0 -i list.txt -c copy out.mp4
```

`list.txt` contains:
```
file '/tmp/.../clip_01.mp4'
file '/tmp/.../clip_02.mp4'
...
```

### Fallback if `-c copy` fails

If clips have timestamp gaps or codec mismatches (rare but possible after
manual edits), re-encode on concat:

```bash
ffmpeg -y -f concat -safe 0 -i list.txt \
  -c:v libx264 -c:a aac \
  out.mp4
```

---

## 3. Burning the SRT sidecar on demand (optional, requires libass)

`out.mp4` already has captions burned in via PIL. However, if you need
to burn the `out.srt` sidecar onto the video using ffmpeg's subtitle
filter as an alternative (e.g., for a different font/style):

```bash
ffmpeg -i out.mp4 -vf subtitles=out.srt burned.mp4
```

**This requires a libass-enabled ffmpeg build.** Our default render pipeline
does NOT use this — PIL burn works with any stock ffmpeg install. Use this
only as an optional post-processing step if needed.

Check whether your ffmpeg has libass:
```bash
ffmpeg -filters 2>&1 | grep subtitles
```

---

## Useful diagnostics

Check audio duration (source of truth for slide timing):
```bash
ffprobe -v error -show_entries format=duration -of json audio/01.aiff
```

Inspect a clip's streams:
```bash
ffprobe -v error -show_streams clip_01.mp4
```

Play a clip:
```bash
ffplay clip_01.mp4
```
