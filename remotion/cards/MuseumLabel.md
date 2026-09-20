# MuseumLabel

**Identity:** a real photograph in a hairline mount beside a museum catalogue label — an accent rule draws, the object's name, date and provenance set line by line, the accession number and a short paragraph follow, and the image's licence line sits under it.

**Use when:** the claim is "the thing itself is the evidence" — a real artefact the film cites by what it is, when it is from and where it came from; also the natural home for the credit a licence-clean image needs. **Not when:** there is no real image (it refuses), the film needs to point at parts of the picture (use PhotoPlate), or two things are compared (use RealVersus).

**Motion core:** the mount fades in over 0.03–0.26 while the image settles from a slight zoom; the rule draws across over 0.22–0.40; the name, date and provenance each rise in over 0.14 of the clip starting at 0.30, 0.38 and 0.44; the accession fades in over 0.32–0.62; the paragraph and credit fade in over 0.56–0.84; then it holds still. Landscape puts the image left and the label right; portrait stacks the image above the label.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the object's photograph (a path in the film's public dir) | cropped to fill its mount — 42% of the width in landscape, most of the width and about half the zone's height in portrait |
| `object` | the object's name, in the display serif | a name of a few words is the label's headline; a long one wraps down the label column |
| `date` | a mono line in the accent | a date or period; empty draws nothing |
| `provenance` | where it is from / where it is held, in the dim body face | a line or two; empty draws nothing |
| `accession` | the catalogue number, small mono | reads as a real label's reference line; empty draws nothing |
| `body` | one paragraph under a hairline — what the viewer should notice | two or three sentences sit well; the label column has no height limit, so a long paragraph runs on down the frame |
| `credit` | the licence line under the image | small mono in the dim colour; empty draws nothing, even when the image's licence requires attribution |

**Known traps:**
- All label type is sized from the frame's WIDTH, so on a portrait frame every line is markedly smaller than at 16:9.
- Omitting `object` prints `the object`.
- Nothing stops `body` or a wrapped `object` pushing the label down past the content zone; keep the paragraph short, especially in portrait where the label starts below the image.

**Refuses:** a missing or blank `src` (the register's premise is the real artefact; the error names `scripts/imagefetch.py` for fetching one).

**Reference:** `remotion/src/shots/MuseumLabel.tsx`
