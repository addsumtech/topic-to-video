# Troubleshooting

---

## LibreOffice / soffice

### `soffice` hangs during `.pptx` conversion

LibreOffice sometimes leaves a zombie process that blocks headless mode.

```bash
# Kill any stale soffice processes
pkill -f soffice
# Retry
python scripts/ingest.py deck.pptx out/
```

`ingest.py` runs `soffice --headless --convert-to pdf --outdir <dir> deck.pptx`.
This requires no display (Xvfb not needed on macOS). If it still hangs after
killing stale processes, check `~/.config/libreoffice` for a lock file.

### `soffice` not installed

`ingest.py` raises `RuntimeError: LibreOffice (soffice) not found`.

Options:
1. Install LibreOffice: https://www.libreoffice.org/download/
2. Export your deck to PDF manually from PowerPoint or Keynote,
   then feed the PDF directly:
   ```bash
   python scripts/ingest.py deck.pdf out/
   ```
3. Export slides as PNG images (one per file, named alphabetically),
   put them in a folder, and feed the folder:
   ```bash
   python scripts/ingest.py slides/ out/
   ```

---

## Fonts / Captions

### Bundled font not found

If `assets/fonts/DejaVuSans.ttf` is missing, `render.py` catches the
exception and falls back to PIL's built-in default font:

```python
except Exception:
    return ImageFont.load_default()
```

Captions still render — they just use a smaller, plainer bitmap font.
To restore the bundled font, check it exists at:
```
assets/fonts/DejaVuSans.ttf
```
The file should be committed in the repo (`assets/fonts/` is in git).

### Captions need libass / not showing

**Captions do NOT require libass.** They are drawn by PIL and composited as a
PNG overlay before ffmpeg encodes the clip. If captions are not appearing:
1. Confirm `meta.captions` is `true` in `storyboard.json`.
2. Confirm `narration` is non-empty for the slide (empty narration → empty caption).
3. Check that `tts.py` ran first — `render.py` needs `slide.audio` and `slide.duration` set.

---

## Audio / Video Drift

Slide durations come from `ffprobe` measuring the actual audio file — they
are never guessed or estimated. If your video feels out of sync:
- Make sure you ran `tts.py` after the last edit to `narration`.
- If you edited an audio file manually, re-run `tts.py --only N` for that slide.
- Durations are stored in `storyboard.json` as `slide.duration` (in seconds,
  3-decimal precision). Verify they look reasonable.
- Mixed TTS engines (edge `.mp3` @24000 Hz vs say `.aiff` @22050 Hz) silently desync
  with `-c copy`; run `python scripts/check_av.py <out_dir>` to detect; `render.py`
  pins `-ar 48000 -ac 1` to prevent it (clear `.clips/` and re-render if you see drift).

---

## Zoompan Jitter

Fast zoom jumps appear as jitter in the rendered clip.

**Cause:** Large zoom delta between `motion.from[2]` and `motion.to[2]`.

**Fix:** Keep zoom delta ≤ 0.20. The default (1.0 → 1.12, delta = 0.12) is
safe. Exceeding 0.25 often produces visible stepping at 30 fps with ffmpeg's
`zoompan`.

Note: `render.py` already applies `meta.motion_ss` (default 2) supersampling to reduce stepping
(scale up → zoompan → scale back down with lanczos). If jitter persists at the default delta,
raise `meta.motion_ss` to 3 before reducing the zoom delta.

---

## pptx Animations / Embedded Video

LibreOffice renders `.pptx` slides to static PDFs. Animations and slide
transitions are not captured — only the final static state of each slide is
used. Embedded video frames are not played.

Tell users: **export your deck with animations off** (or use a static export)
if the final slide state is not what they want rendered.

---

## ffmpeg concat fails

If `ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp4` exits with an error
about timestamps or codec compatibility, re-encode on concat:

```bash
ffmpeg -y -f concat -safe 0 -i list.txt -c:v libx264 -c:a aac out.mp4
```

This is slower but always correct. It is not the default because `-c copy` is
much faster for long decks.

---

## Quick self-check

```bash
# Verify a single slide before full render
python scripts/render.py out/ --sample 1
open out/sample.mp4

# Check A/V sync and per-clip sample-rate uniformity after full render
python scripts/check_av.py out/
```
