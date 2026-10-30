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

## Ken Burns jitter (an image slide shivers during the zoom or pan)

**How it is drawn.** Every frame of an image slide's move is the curve's FLOAT crop window
(`render._kenburns_window`) resampled whole to the frame by Pillow's Lanczos and streamed to ffmpeg as rawvideo
(`render._kenburns_frames`) — the picture lands where the curve says to a fraction of a pixel. There is no zoompan
and no supersampling in this path any more.

**Why it changed.** The old chain (scale to `meta.motion_ss`× → `zoompan` → scale back) placed zoompan's crop at
whole SUPERSAMPLED pixels, so a slow push or pan held and then jumped: `jitter_qa.py` read every tile of a Ken Burns
slide at 0.22–0.59 px RMS at the default `motion_ss` 2 (ERROR) and 0.10–0.14 px even at 8 (WARN). The float resample
is exact before the encode (0.004 px on a slow pan, measured losslessly); x264's defaults then put back ~0.1 px on
smooth content (quarter-pel motion vectors with the residual dropped), so image-slide clips are encoded with
`-tune grain` (its PPS chroma offset pinned back, so the `-c copy` concat still holds) — clean on the bench at 16:9
and 1:1 and on the fixture films at all three aspects; the 9:16 bench's remaining findings sit on featureless or
aperture-limited windows (`ffmpeg-recipes.md` §1).
`meta.motion_ss` is retired: it is ignored, and `validate.py` warns on a board that still sets it.

**If a slide still shivers:** run `python3 scripts/jitter_qa.py <out_dir>` — it judges every image slide's tiles
against the exact move. A finding there is a renderer defect to report, not a knob to turn. A zoom delta above 0.20
still reads as a lurch and an end zoom above 1.25× still softens fine text (validate warns on both): those are
about the move, not jitter.
Type that steps a pixel at a time on the remotion or HTML tier is a different defect — see `text_safe_qa.py --glide`.

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
# Pre-render gates (cheap — run BEFORE any render)
python scripts/validate.py out/          # structure/captions/motion/cues (~1s)
python scripts/keyframe_qa.py out/       # HTML decks: blank/overflow + contact sheets (~1 min)

# Verify a single slide before full render
python scripts/render.py out/ --sample 1
open out/sample.mp4

# Check A/V sync and per-clip sample-rate uniformity after full render
python scripts/check_av.py out/
```
