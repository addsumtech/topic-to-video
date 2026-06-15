# ffmpeg Recipes

These are the exact ffmpeg invocations issued by `render.py`. Understanding
them helps with debugging, manual re-runs, and codec troubleshooting.

---

## 1. Per-slide clip

For each slide, `render.py` builds a `.mp4` clip from a looped still image +
audio + optional overlay PNG.

### Without overlay (no callouts, captions disabled)

```bash
ffmpeg -y \
  -loop 1 -i fit_01.png \
  -i audio/01.aiff \
  -filter_complex "[0:v]scale=1920:1080,zoompan=z='1.0+(1.15-1.0)*on/300':d=300:s=1920x1080:fps=30[base]" \
  -map "[base]" -map 1:a \
  -t 10.0 -r 30 -pix_fmt yuv420p \
  -c:v libx264 -c:a aac \
  -shortest \
  clip_01.mp4
```

### With overlay (callouts and/or captions)

The overlay PNG is input index `2`. It is composited with `overlay=0:0` after
the zoompan so it stays **fixed** while the slide zooms.

```bash
ffmpeg -y \
  -loop 1 -i fit_01.png \
  -i audio/01.aiff \
  -i ov_01.png \
  -filter_complex "[0:v]scale=1920:1080,zoompan=z='1.0+(1.15-1.0)*on/300':d=300:s=1920x1080:fps=30[base];[base][2:v]overlay=0:0[ov]" \
  -map "[ov]" -map 1:a \
  -t 10.0 -r 30 -pix_fmt yuv420p \
  -c:v libx264 -c:a aac \
  -shortest \
  clip_01.mp4
```

**Key variables:**
- `W`/`H`: output width/height (1920×1080 for 16:9; 1080×1920 for vertical)
- `z0`/`z1`: `motion.from[2]` and `motion.to[2]` (zoom values, default 1.0 → 1.15)
- `frames`: `round(duration * fps)` — number of zoompan frames
- `DUR`: `slide.duration` in seconds (measured by ffprobe from the audio file)
- `fps`: `meta.fps` (default 30)

The `zoompan` z-expression is exactly:
```
z='z0+(z1-z0)*on/frames'
```
where `on` is ffmpeg's built-in "frame number" variable. This gives a smooth
linear zoom from `z0` to `z1` over the slide duration.

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
