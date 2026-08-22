# DNA Type Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every typeface the Design DNA declares actually render, give the seven directions distinct typography, and deliver that typography to all 134 shots without regressing any existing film.

**Architecture:** Three ordered layers. (A) `remotion/src/runtime/fonts.ts` loads bundled variable fonts through `@remotion/fonts`, so declared families stop resolving to whatever the host machine has installed. (B) The eight presets in `dna.tsx` get distinct, CJK-safe font stacks drawn from those loaded faces. (C) `Film.tsx` injects `--f-display` / `--f-body` / `--f-mono` on `.dna-film`, and a codemod rewrites hardcoded family lists in the shots to `var(--f-ROLE, <original list>)` — the original list stays as the variable's fallback, so an un-themed film renders byte-identical pixels.

**Tech Stack:** Remotion 4.0.486, `@remotion/fonts` 4.0.486 (`loadFont`), React, TypeScript (types stripped by the bundler, not type-checked), Python 3 + pytest for gates and codemods, ffmpeg for pixel comparison.

**Spec:** `docs/superpowers/specs/2026-08-22-dna-type-layer-design.md`

## Global Constraints

- Repo root is the skill directory; all paths below are relative to it. The remotion project lives in `remotion/` and reuses a sibling `node_modules` — always run `npx` commands from inside `remotion/`.
- Font family names must match `assets/html/base.css` **verbatim**, so the HTML and remotion tiers name the same faces: `Space Grotesk`, `Playfair Display`, `JetBrains Mono`, `Bangers`.
- Variable-font weight ranges are load-bearing: a VF loaded without its range gets synthesised (faux) weights. Ranges from `base.css:8-11` are `300 700`, `400 900`, `100 800`, `400` respectively.
- Every font stack in `dna.tsx` must end with a CJK chain plus a generic family. The canonical chain already in the codebase (`Film.tsx:127`) is: `"PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif`.
- New font files are SIL OFL only, fetched from `https://raw.githubusercontent.com/google/fonts/main/`, committed under `assets/fonts/` with an `OFL-<Name>.txt` licence file beside them, matching the existing convention.
- A font that fails to load must `cancelRender` — never silently fall back. Silent fallback is the exact defect this plan exists to fix.
- Never `git add -A` / `git add .` — stage named paths only.
- Never push. Commit locally; the controller reports what is unpushed.
- `git commit` must not use `-c` to override identity.
- Layer C must not change the rendered pixels of a film with no DNA. This is verified by hashing real renders (Task 9), never by assertion alone.

---

## File Structure

| file | responsibility |
|---|---|
| `remotion/src/runtime/fonts.ts` | **create** — the single list of loaded faces + the delayRender-guarded load. Exports `FACES` so gates and tests can read it. |
| `remotion/src/types/assets.d.ts` | **create** — `declare module '*.ttf'` so `.ttf` imports type-resolve. |
| `remotion/src/Root.tsx` | **modify** — top-level `import './runtime/fonts'` so Film *and* standalone shot stills get the faces. |
| `remotion/remotion.config.ts` | **modify, contingency only** — `webpackOverride` adding an `asset/resource` rule for fonts, if the bundler rejects the `.ttf` import. |
| `remotion/src/runtime/__probe_fonts.tsx` | **create** — renders each face beside its bare generic fallback, and a weight ladder for the variable ones. |
| `scripts/font_gate.py` | **create** — renders the probe and asserts each pair differs. The only mechanical detector of a silent fallback. |
| `assets/fonts/*.ttf` + `OFL-*.txt` | **create** — six new OFL faces. |
| `remotion/src/runtime/dna.tsx` | **modify** — the eight presets' font stacks. |
| `remotion/src/Film.tsx` | **modify** — inject the three CSS variables; give the caption DNA typography. |
| `scripts/dna_migrate_type.py` | **create** — the codemod: hardcoded family list → `var(--f-ROLE, <original>)`, plus a dry-run assignment report. |
| `scripts/null_dna_pixel_gate.py` | **create** — renders N shots with no DNA and compares SHA-256 before vs after the migration. |
| `scripts/dna_audit.py` | **modify** — add `--type` reporting per-shot type reach. |
| `tests/test_remotion.py` | **modify** — drift and contract tests (base.css↔fonts.ts, declared⇒loaded, CJK present, codemod unit tests). |
| `references/remotion-shot-authoring.md`, `remotion/LIBRARY.md`, `SKILL.md`, `agents/shot-director.md` | **modify** — document the type layer. |

---

### Task 1: Load the bundled fonts

**Files:**
- Create: `remotion/src/runtime/fonts.ts`
- Create: `remotion/src/types/assets.d.ts`
- Modify: `remotion/src/Root.tsx`
- Test: `tests/test_remotion.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `remotion/src/runtime/fonts.ts` exports `export type Face = {family: string; file: string; url: string; weight: string; variable: boolean}` and `export const FACES: Face[]`. Tasks 2, 3 and 4 read `FACES`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_remotion.py`:

```python
_FONTS_TS = os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "runtime", "fonts.ts")
_BASE_CSS = os.path.join(os.path.dirname(__file__), "..", "assets", "html", "base.css")


def test_fonts_ts_loads_every_bundled_face_with_base_css_weights():
    """The HTML tier already declares these faces. The remotion tier must name the SAME families
    with the SAME weight ranges, or a variable font silently renders synthesised weights."""
    css = open(_BASE_CSS, encoding="utf-8").read()
    faces = re.findall(
        r'@font-face\{font-family:"([^"]+)";src:url\("\.\./fonts/([^"]+)"\);font-weight:([^;]+);',
        css,
    )
    assert len(faces) >= 4, "could not parse @font-face out of base.css (got %r)" % (faces,)
    ts = open(_FONTS_TS, encoding="utf-8").read()
    for family, filename, weight in faces:
        assert "family: '%s'" % family in ts, "fonts.ts does not load %r" % family
        assert filename in ts, "fonts.ts does not reference %r" % filename
        assert "weight: '%s'" % weight.strip() in ts, (
            "fonts.ts weight for %r drifted from base.css (%r)" % (family, weight.strip()))


def test_fonts_ts_fails_loudly_on_a_load_error():
    """A font that fails to load must abort the render. A silent fallback is the defect this fixes."""
    ts = open(_FONTS_TS, encoding="utf-8").read()
    assert "cancelRender" in ts, "fonts.ts must cancelRender on a failed load"
    assert "delayRender" in ts, "fonts.ts must delayRender until the faces are ready"
```

`re` and `os` are already imported at the top of `tests/test_remotion.py`; add them only if missing.

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_remotion.py -k fonts_ts -v`
Expected: FAIL — `FileNotFoundError` for `fonts.ts`.

- [ ] **Step 3: Create the `.ttf` module declaration**

Create `remotion/src/types/assets.d.ts`:

```ts
// The bundler emits font files as asset URLs; this declares the import so the type layer agrees.
declare module '*.ttf' {
  const src: string;
  export default src;
}
```

- [ ] **Step 4: Create `fonts.ts`**

Create `remotion/src/runtime/fonts.ts`:

```ts
// FONTS — the remotion tier used to load NOTHING: every family named in a DNA was a bare CSS family
// name resolved against whatever the render host had installed. On a machine without them, the
// "editorial high-contrast serif" was Georgia and the terminal monospace was SF Mono, and output
// therefore varied by machine — a determinism defect on a tier that otherwise pins seeds and hashes
// clips. These are the same files, under the same family names, that assets/html/base.css already
// declares for the HTML tier, so the two tiers name one set of faces.
//
// The imports below are resolved by the bundler into asset URLs. staticFile() is deliberately NOT
// used: render_remotion.py points --public-dir at the film's out_dir, and a standalone
// `npx remotion still` has a different public dir again, so a bundled asset is the only path that
// works for both.
import {loadFont} from '@remotion/fonts';
import {cancelRender, continueRender, delayRender} from 'remotion';

import spaceGroteskUrl from '../../../assets/fonts/SpaceGrotesk-VF.ttf';
import playfairDisplayUrl from '../../../assets/fonts/PlayfairDisplay-VF.ttf';
import jetBrainsMonoUrl from '../../../assets/fonts/JetBrainsMono-VF.ttf';
import bangersUrl from '../../../assets/fonts/Bangers-Regular.ttf';

export type Face = {
  family: string;      // must match assets/html/base.css verbatim
  file: string;        // filename under assets/fonts/, for the drift test
  url: string;         // bundler-emitted asset URL
  weight: string;      // a VF's full range, or a single weight for a static face
  variable: boolean;   // true = weight is a range; the weight-ladder gate only applies to these
};

export const FACES: Face[] = [
  {family: 'Space Grotesk', file: 'SpaceGrotesk-VF.ttf', url: spaceGroteskUrl, weight: '300 700', variable: true},
  {family: 'Playfair Display', file: 'PlayfairDisplay-VF.ttf', url: playfairDisplayUrl, weight: '400 900', variable: true},
  {family: 'JetBrains Mono', file: 'JetBrainsMono-VF.ttf', url: jetBrainsMonoUrl, weight: '100 800', variable: true},
  {family: 'Bangers', file: 'Bangers-Regular.ttf', url: bangersUrl, weight: '400', variable: false},
];

// One delayRender for the whole set: the first frame must not render in a fallback face.
const handle = delayRender('loading DNA typefaces');
Promise.all(
  FACES.map((f) => loadFont({family: f.family, url: f.url, weight: f.weight, format: 'truetype'})),
)
  .then(() => continueRender(handle))
  .catch((err) => cancelRender(err));
```

- [ ] **Step 5: Import it from `Root.tsx`**

In `remotion/src/Root.tsx`, immediately after the existing `import {Composition} from 'remotion';` line, add:

```ts
import './runtime/fonts';  // side effect: loads the DNA typefaces for Film AND every standalone shot still
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_remotion.py -k fonts_ts -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Verify a real render still works**

Run from `remotion/`:
```bash
npx remotion still src/index.ts EdStat /tmp/font-check.png --frame=140 --gl=angle
```
Expected: exit 0 and a PNG written.

If the bundler errors on the `.ttf` import, apply the contingency: add to `remotion/remotion.config.ts`

```ts
Config.overrideWebpackConfig((config) => ({
  ...config,
  module: {
    ...config.module,
    rules: [
      ...(config.module?.rules ?? []),
      {test: /\.(ttf|otf|woff2?)$/, type: 'asset/resource'},
    ],
  },
}));
```

and re-run. Record in the report whether the contingency was needed.

- [ ] **Step 8: Look at the render**

Open `/tmp/font-check.png`. The figure must now be set in Playfair Display (a high-contrast didone with hairline serifs), **not** Georgia. If it still looks like Georgia, the font did not load — do not proceed; Task 2 builds the gate that makes this mechanical, but this task must not be reported as done on a render that still shows the fallback.

- [ ] **Step 9: Commit**

```bash
git add remotion/src/runtime/fonts.ts remotion/src/types/assets.d.ts remotion/src/Root.tsx tests/test_remotion.py
git commit -m "feat(remotion): actually load the typefaces the DNA declares"
```

---

### Task 2: Gate A1 — the silent-fallback detector

A render that exits 0 proves nothing about which face was used; that is precisely how this defect survived. The only mechanical detector is a pixel comparison against the bare generic fallback.

**Files:**
- Create: `remotion/src/runtime/__probe_fonts.tsx`
- Create: `scripts/font_gate.py`
- Modify: `remotion/src/Root.tsx`
- Test: `tests/test_remotion.py`

**Interfaces:**
- Consumes: `FACES` from `remotion/src/runtime/fonts.ts`.
- Produces: `scripts/font_gate.py` exposes `def tiles_differ(png_path: str, rows: int, cols: int) -> list[bool]` returning, per row, whether that row's two column tiles differ. Nothing later depends on it.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_remotion.py`:

```python
def test_tiles_differ_detects_identical_and_distinct_halves(tmp_path):
    """The gate's comparison must call identical halves 'same' and distinct halves 'different'.
    Tested on synthetic images so the unit test needs no render."""
    from PIL import Image
    import importlib.util
    spec_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "font_gate.py")
    spec = importlib.util.spec_from_file_location("font_gate", spec_path)
    font_gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(font_gate)

    # row 0: both halves identical black; row 1: left black, right white
    img = Image.new("RGB", (200, 200), "black")
    for x in range(100, 200):
        for y in range(100, 200):
            img.putpixel((x, y), (255, 255, 255))
    p = tmp_path / "probe.png"
    img.save(p)

    assert font_gate.tiles_differ(str(p), rows=2, cols=2) == [False, True]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_remotion.py -k tiles_differ -v`
Expected: FAIL — `scripts/font_gate.py` does not exist.

- [ ] **Step 3: Write the probe composition**

Create `remotion/src/runtime/__probe_fonts.tsx`:

```tsx
// PROBE — one row per loaded face. Left tile: the family. Right tile: ONLY that family's bare
// generic fallback. If the family did not load, both tiles render the same face and the row's two
// tiles are pixel-identical — which is the single mechanical signal that a silent fallback happened.
// Variable faces get a second probe: a weight ladder. A VF loaded without its weight range clamps,
// so adjacent ladder steps collapse to identical pixels.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {FACES} from './fonts';

const SAMPLE = 'Handgloves 0123';

// The generic each family must be distinguishable FROM. A mono face compared against `monospace`
// on a machine whose default mono IS the face would false-pass; these generics are deliberately the
// bare CSS keywords, never a named face.
const GENERIC: Record<string, string> = {
  'JetBrains Mono': 'monospace',
  'Playfair Display': 'serif',
  'Space Grotesk': 'sans-serif',
  Bangers: 'sans-serif',
};

export const DURATION = 1;

export const FontProbe: React.FC<{ladder?: boolean}> = ({ladder = false}) => {
  const rows = FACES.filter((f) => !ladder || f.variable);
  return (
    <AbsoluteFill style={{background: '#fff', color: '#000', display: 'flex', flexDirection: 'column'}}>
      {rows.map((f) => (
        <div key={f.family} style={{flex: 1, display: 'flex'}}>
          <div style={{flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: f.family, fontWeight: ladder ? 300 : 700, fontSize: 64}}>
            {SAMPLE}
          </div>
          <div style={{flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: ladder ? f.family : (GENERIC[f.family] ?? 'sans-serif'),
            fontWeight: ladder ? 700 : 700, fontSize: 64}}>
            {SAMPLE}
          </div>
        </div>
      ))}
    </AbsoluteFill>
  );
};
export default FontProbe;
```

- [ ] **Step 4: Register the probe**

In `remotion/src/Root.tsx`, add the import beside the others:

```ts
import {FontProbe, DURATION as FPR} from './runtime/__probe_fonts';
```

and add this line immediately before the first `{F('CollaborativeCursors', ...)}` entry:

```tsx
    {F('FontProbe', FontProbe, FPR)}
```

- [ ] **Step 5: Write the gate**

Create `scripts/font_gate.py`:

```python
#!/usr/bin/env python3
"""font_gate — prove each declared typeface ACTUALLY renders.

A render exiting 0 says nothing about which face was used: for a long time every remotion film in
this repo rendered Georgia and SF Mono while the DNA declared Playfair Display and JetBrains Mono,
and nothing anywhere complained. This gate renders `FontProbe`, which draws each family beside its
bare generic fallback, and asserts the two tiles differ. It then renders the weight ladder and
asserts the light and heavy tiles differ, which catches a variable font loaded without its range.

Exit 0 = every face loaded and every variable face honours its weight range.
Exit 1 = at least one face is silently falling back (the message names it).
"""
import hashlib, os, re, subprocess, sys, tempfile

from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")


def tiles_differ(png_path, rows, cols=2):
    """Split the image into rows x cols tiles and report, per row, whether the tiles differ."""
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    out = []
    for r in range(rows):
        digests = []
        for c in range(cols):
            box = (c * w // cols, r * h // rows, (c + 1) * w // cols, (r + 1) * h // rows)
            digests.append(hashlib.sha256(img.crop(box).tobytes()).hexdigest())
        out.append(len(set(digests)) > 1)
    return out


def _families(ladder):
    """Read the face list out of fonts.ts so the gate cannot drift from what is loaded."""
    src = open(os.path.join(_REMOTION, "src", "runtime", "fonts.ts"), encoding="utf-8").read()
    faces = re.findall(r"\{family: '([^']+)'.*?variable: (true|false)\}", src)
    if not faces:
        sys.exit("font_gate: could not parse FACES out of fonts.ts")
    return [f for f, v in faces if (v == "true" or not ladder)]


def _render(out_png, ladder):
    r = subprocess.run(
        ["npx", "remotion", "still", "src/index.ts", "FontProbe", out_png,
         "--frame=0", "--gl=angle", "--props=" + ('{"ladder":true}' if ladder else '{"ladder":false}')],
        cwd=_REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("font_gate: probe render failed\n" + r.stderr[-2000:])


def main():
    failures = []
    with tempfile.TemporaryDirectory() as td:
        for ladder in (False, True):
            fams = _families(ladder)
            png = os.path.join(td, "ladder.png" if ladder else "faces.png")
            _render(png, ladder)
            for fam, ok in zip(fams, tiles_differ(png, rows=len(fams))):
                if not ok:
                    failures.append(
                        "%s: %s" % (fam, "weight range not honoured (light == heavy)" if ladder
                                    else "SILENT FALLBACK - renders identically to its generic"))
    if failures:
        print("font_gate FAILED:")
        for f in failures:
            print("  " + f)
        return 1
    print("font_gate: every declared face loaded and honours its weight range")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the unit test to verify it passes**

Run: `python3 -m pytest tests/test_remotion.py -k tiles_differ -v`
Expected: PASS.

- [ ] **Step 7: Run the real gate**

Run: `python3 scripts/font_gate.py`
Expected: exit 0, printing `font_gate: every declared face loaded and honours its weight range`.

If it fails, the fonts from Task 1 are not loading — fix Task 1 before continuing. Report the exact failing line.

- [ ] **Step 8: Commit**

```bash
git add scripts/font_gate.py remotion/src/runtime/__probe_fonts.tsx remotion/src/Root.tsx tests/test_remotion.py
git commit -m "test(remotion): gate against silent font fallback and clamped VF weights"
```

---

### Task 3: Add the six new OFL faces

**Files:**
- Create: `assets/fonts/Inter-VF.ttf`, `SourceSerif4-VF.ttf`, `IBMPlexSans-VF.ttf`, `IBMPlexMono-Regular.ttf`, `BodoniModa-VF.ttf`, `Baloo2-VF.ttf` and their `OFL-*.txt`
- Modify: `remotion/src/runtime/fonts.ts`

**Interfaces:**
- Consumes: `FACES` from Task 1.
- Produces: six more `Face` entries; Task 4's preset stacks may name only families present here.

- [ ] **Step 1: Fetch the fonts and their licences**

All six URLs were verified to resolve (HTTP 206 on a range request) on 2026-08-22. Run from the repo root:

```bash
B=https://raw.githubusercontent.com/google/fonts/main
set -e
curl -sSfL "$B/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf"                 -o assets/fonts/Inter-VF.ttf
curl -sSfL "$B/ofl/sourceserif4/SourceSerif4%5Bopsz%2Cwght%5D.ttf"   -o assets/fonts/SourceSerif4-VF.ttf
curl -sSfL "$B/ofl/ibmplexsans/IBMPlexSans%5Bwdth%2Cwght%5D.ttf"     -o assets/fonts/IBMPlexSans-VF.ttf
curl -sSfL "$B/ofl/ibmplexmono/IBMPlexMono-Regular.ttf"              -o assets/fonts/IBMPlexMono-Regular.ttf
curl -sSfL "$B/ofl/bodonimoda/BodoniModa%5Bopsz%2Cwght%5D.ttf"       -o assets/fonts/BodoniModa-VF.ttf
curl -sSfL "$B/ofl/baloo2/Baloo2%5Bwght%5D.ttf"                      -o assets/fonts/Baloo2-VF.ttf
curl -sSfL "$B/ofl/inter/OFL.txt"          -o assets/fonts/OFL-Inter.txt
curl -sSfL "$B/ofl/sourceserif4/OFL.txt"   -o assets/fonts/OFL-SourceSerif4.txt
curl -sSfL "$B/ofl/ibmplexsans/OFL.txt"    -o assets/fonts/OFL-IBMPlexSans.txt
curl -sSfL "$B/ofl/ibmplexmono/OFL.txt"    -o assets/fonts/OFL-IBMPlexMono.txt
curl -sSfL "$B/ofl/bodonimoda/OFL.txt"     -o assets/fonts/OFL-BodoniModa.txt
curl -sSfL "$B/ofl/baloo2/OFL.txt"         -o assets/fonts/OFL-Baloo2.txt
```

- [ ] **Step 2: Verify each file is a real TrueType font**

```bash
for f in assets/fonts/Inter-VF.ttf assets/fonts/SourceSerif4-VF.ttf assets/fonts/IBMPlexSans-VF.ttf \
         assets/fonts/IBMPlexMono-Regular.ttf assets/fonts/BodoniModa-VF.ttf assets/fonts/Baloo2-VF.ttf; do
  file "$f" | grep -q "TrueType" || { echo "NOT A FONT: $f"; exit 1; }
done
echo "all six are TrueType"
```

Expected: `all six are TrueType`. A 404 saved as an HTML error page fails here rather than silently later.

- [ ] **Step 3: Add them to `fonts.ts`**

In `remotion/src/runtime/fonts.ts`, add the imports beside the existing ones:

```ts
import interUrl from '../../../assets/fonts/Inter-VF.ttf';
import sourceSerif4Url from '../../../assets/fonts/SourceSerif4-VF.ttf';
import ibmPlexSansUrl from '../../../assets/fonts/IBMPlexSans-VF.ttf';
import ibmPlexMonoUrl from '../../../assets/fonts/IBMPlexMono-Regular.ttf';
import bodoniModaUrl from '../../../assets/fonts/BodoniModa-VF.ttf';
import baloo2Url from '../../../assets/fonts/Baloo2-VF.ttf';
```

and append these entries to `FACES`:

```ts
  {family: 'Inter', file: 'Inter-VF.ttf', url: interUrl, weight: '100 900', variable: true},
  {family: 'Source Serif 4', file: 'SourceSerif4-VF.ttf', url: sourceSerif4Url, weight: '200 900', variable: true},
  {family: 'IBM Plex Sans', file: 'IBMPlexSans-VF.ttf', url: ibmPlexSansUrl, weight: '100 700', variable: true},
  {family: 'IBM Plex Mono', file: 'IBMPlexMono-Regular.ttf', url: ibmPlexMonoUrl, weight: '400', variable: false},
  {family: 'Bodoni Moda', file: 'BodoniModa-VF.ttf', url: bodoniModaUrl, weight: '400 900', variable: true},
  {family: 'Baloo 2', file: 'Baloo2-VF.ttf', url: baloo2Url, weight: '400 800', variable: true},
```

- [ ] **Step 4: Extend the probe's generic map**

In `remotion/src/runtime/__probe_fonts.tsx`, add to `GENERIC`:

```ts
  Inter: 'sans-serif',
  'Source Serif 4': 'serif',
  'IBM Plex Sans': 'sans-serif',
  'IBM Plex Mono': 'monospace',
  'Bodoni Moda': 'serif',
  'Baloo 2': 'sans-serif',
```

- [ ] **Step 5: Run the gate**

Run: `python3 scripts/font_gate.py`
Expected: exit 0 with all ten faces passing.

The weight-ladder half of the gate is what checks the ranges declared in Step 3. If a ladder row fails, the declared range is wrong for that file — correct it from the failure, do not widen the range to make the gate pass.

- [ ] **Step 6: Run the existing suite**

Run: `python3 -m pytest tests/test_remotion.py -v`
Expected: PASS. (`test_fonts_ts_loads_every_bundled_face_with_base_css_weights` only asserts the base.css faces are *present*, so the six additions do not break it.)

- [ ] **Step 7: Commit**

```bash
git add assets/fonts/Inter-VF.ttf assets/fonts/SourceSerif4-VF.ttf assets/fonts/IBMPlexSans-VF.ttf \
        assets/fonts/IBMPlexMono-Regular.ttf assets/fonts/BodoniModa-VF.ttf assets/fonts/Baloo2-VF.ttf \
        assets/fonts/OFL-Inter.txt assets/fonts/OFL-SourceSerif4.txt assets/fonts/OFL-IBMPlexSans.txt \
        assets/fonts/OFL-IBMPlexMono.txt assets/fonts/OFL-BodoniModa.txt assets/fonts/OFL-Baloo2.txt \
        remotion/src/runtime/fonts.ts remotion/src/runtime/__probe_fonts.tsx
git commit -m "feat(fonts): add six SIL OFL faces for the per-direction type identities"
```

---

### Task 4: Give each direction its typography (Layer B)

**Files:**
- Modify: `remotion/src/runtime/dna.tsx` (the eight preset objects)
- Test: `tests/test_remotion.py`

**Interfaces:**
- Consumes: `FACES` from Tasks 1 and 3.
- Produces: preset font stacks read by `Film.tsx` in Task 7 and by every shot via Task 9's variables.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_remotion.py`:

```python
_CJK_FAMILIES = ('PingFang SC', 'Hiragino Sans', 'Microsoft YaHei', 'Noto Sans CJK SC')


def _font_stacks():
    """Every fontDisplay/fontMono/fontBody string literal in dna.tsx."""
    src = _dna_tsx()
    return re.findall(r"font(?:Display|Mono|Body): '([^']+)'", src)


def test_every_declared_family_is_actually_loaded():
    """A preset may only name a face fonts.ts loads — otherwise it silently falls back, which is
    the exact defect this layer exists to fix."""
    loaded = set(re.findall(r"family: '([^']+)'", open(_FONTS_TS, encoding="utf-8").read()))
    assert loaded, "could not parse FACES out of fonts.ts"
    generics = {'system-ui', 'sans-serif', 'serif', 'monospace', 'ui-monospace', 'cursive', 'fantasy'}
    for stack in _font_stacks():
        for fam in [p.strip().strip('"') for p in stack.split(',')]:
            if fam in generics or fam in _CJK_FAMILIES:
                continue
            assert fam in loaded, "dna.tsx names %r but fonts.ts does not load it" % fam


def test_every_font_stack_has_a_cjk_fallback():
    """None of these faces covers CJK; without a fallback, Chinese decks regress silently."""
    stacks = _font_stacks()
    assert len(stacks) >= 24, "expected 3 stacks x 8 presets, parsed %d" % len(stacks)
    for stack in stacks:
        assert any(c in stack for c in _CJK_FAMILIES), "no CJK fallback in %r" % stack
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_remotion.py -k "declared_family or cjk_fallback" -v`
Expected: FAIL — presets name `Georgia`/`Impact` (not loaded) and no stack has a CJK family.

- [ ] **Step 3: Rewrite the eight presets**

In `remotion/src/runtime/dna.tsx`, set each preset's three font tokens to exactly these values. `CJK` below stands for the literal text `"PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC"` — write it out in full in every stack; do not introduce a constant, because the test parses string literals.

| preset | fontDisplay | fontBody | fontMono |
|---|---|---|---|
| `TERMINAL_DNA` | `"JetBrains Mono", CJK, ui-monospace, monospace` | same as display | same as display |
| `NEUTRAL_DNA` | `Inter, CJK, system-ui, sans-serif` | `Inter, CJK, system-ui, sans-serif` | `"JetBrains Mono", CJK, ui-monospace, monospace` |
| `EDITORIAL_DNA` | `"Playfair Display", CJK, Georgia, serif` | `"Source Serif 4", CJK, Georgia, serif` | `"JetBrains Mono", CJK, ui-monospace, monospace` |
| `PRODUCT_DNA` | `"Space Grotesk", CJK, system-ui, sans-serif` | `Inter, CJK, system-ui, sans-serif` | `"JetBrains Mono", CJK, ui-monospace, monospace` |
| `BLUEPRINT_DNA` | `"JetBrains Mono", CJK, ui-monospace, monospace` | `"IBM Plex Sans", CJK, system-ui, sans-serif` | `"JetBrains Mono", CJK, ui-monospace, monospace` |
| `CINEMATIC_DNA` | `"Bodoni Moda", CJK, Georgia, serif` | `Inter, CJK, system-ui, sans-serif` | `"JetBrains Mono", CJK, ui-monospace, monospace` |
| `DATA_DNA` | `"IBM Plex Sans", CJK, system-ui, sans-serif` | `"IBM Plex Sans", CJK, system-ui, sans-serif` | `"IBM Plex Mono", CJK, ui-monospace, monospace` |
| `RETRO_DNA` | `"Baloo 2", CJK, system-ui, sans-serif` | `"Baloo 2", CJK, system-ui, sans-serif` | `"JetBrains Mono", CJK, ui-monospace, monospace` |

Two clean-ups while you are in there: delete `Impact` from `RETRO_DNA` (it is not loaded and is not the intended fallback), and keep `Georgia` **only** in the two serif stacks above, where it is a deliberate last-resort.

`Georgia` is not a face `fonts.ts` loads, so `test_every_declared_family_is_actually_loaded` would flag it. Add `'Georgia'` to that test's `generics` set with this comment: Georgia ships with every macOS and Windows install, so it is a safe last-resort serif rather than a declared identity — which is exactly why it must never be a stack's FIRST entry.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_remotion.py -v`
Expected: PASS, full file.

- [ ] **Step 5: Verify the whole library still renders under the new stacks**

Run: `python3 scripts/dna_smoke.py editorial`
Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add remotion/src/runtime/dna.tsx tests/test_remotion.py
git commit -m "feat(dna): give each direction a distinct, CJK-safe type stack"
```

---

### Task 5: Specimen contact sheet (taste gate)

The pairings in Task 4 are a candidate slate. This task produces the evidence the user judges them on. It does not decide anything itself.

**Files:**
- Create: `scripts/type_specimens.py`

**Interfaces:**
- Consumes: the presets from Task 4.
- Produces: `<out>/specimens.png`, a contact sheet with one labelled row per direction. The controller shows it to the user; any pairing change is applied back into Task 4's table as a follow-up commit.

- [ ] **Step 1: Write the specimen script**

Create `scripts/type_specimens.py`:

```python
#!/usr/bin/env python3
"""type_specimens — render one representative shot per DNA direction into a contact sheet, so the
type pairings are judged on real frames rather than on family names in a table.

Usage: python3 scripts/type_specimens.py <out_dir>
"""
import os, subprocess, sys, json

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")

# One shot per direction, chosen because each shows a display size, a body size and a label together.
ROWS = [
    ("terminal", "TermCounter"), ("editorial", "EdStat"), ("product", "MaterialHero"),
    ("blueprint", "BlueprintGrid"), ("cinematic", "CinematicTitle"), ("data", "ChartLive"),
    ("retro", "NeonGrid"), ("neutral", "KnowledgeGraph"),
]


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    pngs = []
    for dna_id, shot in ROWS:
        png = os.path.join(out_dir, "spec_%s.png" % dna_id)
        props = json.dumps({"shot": shot, "dnaId": dna_id})
        r = subprocess.run(
            ["npx", "remotion", "still", "src/index.ts", "TypeSpecimen", png,
             "--frame=140", "--gl=angle", "--props=" + props],
            cwd=_REMOTION, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("specimen render failed for %s/%s\n%s" % (dna_id, shot, r.stderr[-1500:]))
        pngs.append(png)
    sheet = os.path.join(out_dir, "specimens.png")
    inputs = sum([["-i", p] for p in pngs], [])
    fc = "".join("[%d:v]scale=760:-1[v%d];" % (i, i) for i in range(len(pngs)))
    fc += "".join("[v%d]" % i for i in range(len(pngs))) + "vstack=inputs=%d" % len(pngs)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, sheet], check=True)
    print(sheet)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/type-specimens")
```

- [ ] **Step 2: Add the `TypeSpecimen` composition**

Create `remotion/src/runtime/__probe_specimen.tsx`:

```tsx
// PROBE — renders one library shot inside a chosen DNA, for the type specimen contact sheet.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {DesignDNAContext, DNA_PRESETS} from './dna';
import {REGISTRY} from '../registry';

export const DURATION = 150;

export const TypeSpecimen: React.FC<{shot?: string; dnaId?: string}> = ({
  shot = 'EdStat', dnaId = 'editorial'}) => {
  const C = REGISTRY[shot];
  const dna = DNA_PRESETS[dnaId] ?? null;
  return (
    <AbsoluteFill style={{background: dna?.bg ?? '#000'}}>
      <DesignDNAContext.Provider value={dna}>
        <AbsoluteFill>{C ? <C /> : null}</AbsoluteFill>
      </DesignDNAContext.Provider>
    </AbsoluteFill>
  );
};
export default TypeSpecimen;
```

Register it in `remotion/src/Root.tsx` the same way `FontProbe` was registered in Task 2:

```ts
import {TypeSpecimen, DURATION as TSP} from './runtime/__probe_specimen';
```
```tsx
    {F('TypeSpecimen', TypeSpecimen, TSP)}
```

- [ ] **Step 3: Render the contact sheet**

Run: `python3 scripts/type_specimens.py /tmp/type-specimens`
Expected: prints `/tmp/type-specimens/specimens.png`.

- [ ] **Step 4: Look at every row**

Open the sheet. For each row confirm the intended face is visibly present — Bodoni Moda's extreme thick/thin contrast on `cinematic`, Baloo 2's rounded terminals on `retro`, Source Serif 4's text-weight serifs on `editorial`. A row that looks like the previous row means two directions collapsed onto the same face; report which.

- [ ] **Step 5: Report, do not decide**

Write the sheet path and a one-line-per-row read into the task report. The pairing decision is the user's; the controller carries it back.

- [ ] **Step 6: Commit**

```bash
git add scripts/type_specimens.py remotion/src/runtime/__probe_specimen.tsx remotion/src/Root.tsx
git commit -m "test(remotion): render per-direction type specimens for review"
```

---

### Task 6: Library overflow sweep

Real typefaces have different advance widths from the fallbacks that have been rendering all along (Georgia → Playfair Display, SF Mono → JetBrains Mono). Several shots size text from assumed ratios — `EdStat.tsx:30` computes `numSize` from `finalLen * 0.6`. Text that fitted may now overflow. This task finds and fixes that.

**Files:**
- Modify: whichever shot files the sweep implicates (unknown until run — that is the task's job)

**Interfaces:**
- Consumes: Tasks 1-4.
- Produces: nothing new; restores the library's existing overflow guarantees under the new metrics.

- [ ] **Step 1: Render the whole library under a serif-display DNA**

The largest metric change is Georgia → Playfair Display, so `editorial` is the worst case.

Run: `python3 scripts/dna_smoke.py editorial`
Expected: exit 0. A non-zero exit is a crash, not an overflow; fix it before proceeding.

- [ ] **Step 2: Run the frame gates over the smoke output**

Run: `python3 scripts/keyframe_qa.py <the out_dir dna_smoke.py printed>`
Expected: a report. Record every text-overflow and out-of-frame finding with its shot name.

- [ ] **Step 3: Repeat for the mono-display worst case**

Run: `python3 scripts/dna_smoke.py blueprint` then `python3 scripts/keyframe_qa.py <that out_dir>`
Expected: a second finding list. `blueprint` sets `fontDisplay` to JetBrains Mono, whose advance width is much wider than a proportional sans at the same size.

- [ ] **Step 4: Fix each implicated shot**

For each finding, make the shot width-aware rather than hardcoding a smaller size: the library's established pattern is `EdStat.tsx:26-30` — size the text from its final string length, clamped. Copy that shape; do not simply reduce a constant, which fixes this string and breaks the next one.

- [ ] **Step 5: Re-run both sweeps**

Run steps 1-3 again.
Expected: no text-overflow or out-of-frame findings.

- [ ] **Step 6: Commit**

```bash
git add <the shot files you changed>
git commit -m "fix(shots): keep text in frame under the real typefaces' metrics"
```

If no shot needed a change, record that in the report and skip the commit.

---

### Task 7: Inject the variables and give the caption its typography (Layer C1)

**Files:**
- Modify: `remotion/src/Film.tsx`
- Test: `tests/test_remotion.py`

**Interfaces:**
- Consumes: the presets from Task 4.
- Produces: the CSS custom properties `--f-display`, `--f-body`, `--f-mono`, scoped to `.dna-film`. Task 8's codemod writes `var(--f-display, …)` etc. against exactly these names.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_remotion.py`:

```python
def _film_tsx():
    return open(os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "Film.tsx"),
                encoding="utf-8").read()


def test_film_injects_the_three_type_variables():
    src = _film_tsx()
    for var in ("--f-display", "--f-body", "--f-mono"):
        assert var in src, "Film.tsx does not inject %s" % var
    assert ".dna-film {" in src or ".dna-film{" in src, "the type variables must be scoped to .dna-film"


def test_caption_typography_follows_the_dna():
    """The caption is on every frame; only its contrast was DNA-aware, never its typeface."""
    src = _film_tsx()
    assert "dnaFontBody" in src, "CaptionTrack must take the DNA body face"
    assert "font: '700 44px/1.26 Inter" not in src, "the caption font is still hardcoded"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_remotion.py -k "type_variables or caption_typography" -v`
Expected: FAIL on both.

- [ ] **Step 3: Inject the variables**

In `remotion/src/Film.tsx`, immediately **before** the existing `{activeDna?.uniformType ? <style>…` line, insert:

```tsx
      {/* TYPE VARIABLES — the DNA's three faces, published to the shots as CSS custom properties.
          Shots read them as `var(--f-body, <their original list>)`, so with NO DNA the variables are
          unset, the original list applies, and the frame is pixel-identical to before this layer
          existed (scripts/null_dna_pixel_gate.py proves it on real renders). A uniformType DNA's
          `!important` rule below still wins, so terminal is unchanged. */}
      {activeDna ? <style>{`.dna-film { --f-display: ${activeDna.fontDisplay}; --f-body: ${activeDna.fontBody}; --f-mono: ${activeDna.fontMono}; }`}</style> : null}
```

- [ ] **Step 4: Give the caption the DNA's body face**

Change `CaptionTrack`'s signature at `remotion/src/Film.tsx:90` from

```tsx
const CaptionTrack: React.FC<{scenes: SceneSpec[]; groundBg?: string; dnaBg?: string | null}> = ({scenes, groundBg, dnaBg}) => {
```

to

```tsx
const CaptionTrack: React.FC<{scenes: SceneSpec[]; groundBg?: string; dnaBg?: string | null;
  dnaFontBody?: string | null}> = ({scenes, groundBg, dnaBg, dnaFontBody}) => {
```

Change the caption's `font` at `remotion/src/Film.tsx:127` from the hardcoded shorthand to:

```tsx
        color: ink, font: `700 44px/1.26 ${dnaFontBody ?? 'Inter, "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif'}`,
```

and pass the prop at the call site (`remotion/src/Film.tsx:320`):

```tsx
      {captions ? <CaptionTrack scenes={scenes} groundBg={theme?.bg ?? activeDna?.bg} dnaBg={activeDna?.bg} dnaFontBody={activeDna?.fontBody} /> : null}
```

The fallback string is the *current* hardcoded value verbatim, so a film with no DNA keeps today's caption exactly.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_remotion.py -v`
Expected: PASS, full file.

- [ ] **Step 6: Render a captioned film and look at it**

Run: `python3 scripts/dna_smoke.py terminal`
Then open the first few keyframes. The caption must now be monospace on a terminal film, and must still be fully legible on its ground.

**Do not skip this by rendering with `captions:false`.** A previous round of this work verified every render with captions disabled and therefore missed a caption defect entirely.

- [ ] **Step 7: Commit**

```bash
git add remotion/src/Film.tsx tests/test_remotion.py
git commit -m "feat(film): publish DNA type variables and give captions the DNA face"
```

---

### Task 8: The codemod and its assignment report (Layer C2, dry run only)

This task writes **no** shot files. Its deliverable is the codemod plus a report a human reviews, because role assignment is a heuristic no gate can check.

**Files:**
- Create: `scripts/dna_migrate_type.py`
- Test: `tests/test_remotion.py`

**Interfaces:**
- Consumes: the variable names from Task 7.
- Produces: `rewrite_font_decl(text: str) -> tuple[str, list[dict]]` returning the rewritten source and a list of `{"line": int, "size": float, "role": str, "families": str}` assignments. Task 9 calls the script with `--apply`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_remotion.py`:

```python
def _migrate_mod():
    import importlib.util
    p = os.path.join(os.path.dirname(__file__), "..", "scripts", "dna_migrate_type.py")
    spec = importlib.util.spec_from_file_location("dna_migrate_type", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_codemod_assigns_display_body_and_mono_by_size_and_family():
    m = _migrate_mod()
    out, rep = m.rewrite_font_decl("font: '800 200px/0.9 Inter, system-ui, sans-serif'")
    assert out == "font: '800 200px/0.9 var(--f-display, Inter, system-ui, sans-serif)'"
    assert rep[0]["role"] == "display" and rep[0]["size"] == 200.0

    out, _ = m.rewrite_font_decl("font: '400 36px/1.4 Inter, system-ui, sans-serif'")
    assert out == "font: '400 36px/1.4 var(--f-body, Inter, system-ui, sans-serif)'"

    out, _ = m.rewrite_font_decl("font: '500 30px/1 \"JetBrains Mono\", ui-monospace, monospace'")
    assert out == "font: '500 30px/1 var(--f-mono, \"JetBrains Mono\", ui-monospace, monospace)'"


def test_codemod_rewrites_template_literals_whose_family_is_hardcoded():
    """A template literal can interpolate the WEIGHT and still hardcode the family:
    font: `${i === 2 ? 700 : 500} 30px/1 Inter`. Skipping every string containing ${ would miss
    this whole class - 4 shots use exactly this shape."""
    m = _migrate_mod()
    out, rep = m.rewrite_font_decl("font: `${i === 2 ? 700 : 500} 30px/1 Inter`")
    assert out == "font: `${i === 2 ? 700 : 500} 30px/1 var(--f-body, Inter)`"
    assert rep[0]["role"] == "body"


def test_codemod_skips_a_family_that_is_already_dynamic():
    """`${disp}` is already reading the DNA (or a prop). Rewriting it would double-wrap."""
    m = _migrate_mod()
    out, rep = m.rewrite_font_decl("font: `${c.hero ? 500 : 400} 46px/1.3 ${disp}`")
    assert out == "font: `${c.hero ? 500 : 400} 46px/1.3 ${disp}`"
    assert rep == []


def test_codemod_never_touches_an_svg_font_family_attribute():
    """var() does not work in an XML presentation attribute. No shot uses one today; the guard keeps
    it that way."""
    m = _migrate_mod()
    src = '<text font-family="Inter, sans-serif">x</text>'
    out, rep = m.rewrite_font_decl(src)
    assert out == src and rep == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_remotion.py -k codemod -v`
Expected: FAIL — `scripts/dna_migrate_type.py` does not exist.

- [ ] **Step 3: Write the codemod**

Create `scripts/dna_migrate_type.py`:

```python
#!/usr/bin/env python3
"""dna_migrate_type — rewrite hardcoded font families in the shot library to DNA-aware CSS variables.

    font: '800 200px/0.9 Inter, system-ui, sans-serif'
 -> font: '800 200px/0.9 var(--f-display, Inter, system-ui, sans-serif)'

The ORIGINAL family list becomes the variable's fallback, so a film with no DNA resolves exactly what
it resolved before (verified on real renders by scripts/null_dna_pixel_gate.py, not asserted).

Role is a HEURISTIC read off the shorthand: a mono family list -> mono; else >= 64px -> display;
else body. No gate can check whether a role is RIGHT - a heading on --f-body still renders fine - so
--report is reviewed by a human before --apply.

Usage:
  python3 scripts/dna_migrate_type.py --report          # dry run, prints the assignment table
  python3 scripts/dna_migrate_type.py --apply           # writes the files
"""
import json, os, re, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHOTS = os.path.join(_HERE, "..", "remotion", "src", "shots")

DISPLAY_MIN_PX = 64.0
_MONO_RE = re.compile(r"mono|JetBrains|Menlo|Consolas|Courier", re.I)

# `font:` followed by a single- or back-quoted shorthand. Captures the quote so the rewrite keeps it.
_DECL_RE = re.compile(r"font: *(['`])([^'`]*)\1")
# <weight/style words> <size>px[/<line-height>] <families...>
_SHORTHAND_RE = re.compile(r"^(?P<head>.*?)(?P<size>\d+(?:\.\d+)?)px(?P<lh>/[\d.]+)? +(?P<families>.+)$")


def _role(families, size):
    if _MONO_RE.search(families):
        return "mono"
    return "display" if size >= DISPLAY_MIN_PX else "body"


def rewrite_font_decl(text):
    """Rewrite every hardcoded `font:` shorthand in `text`. Returns (new_text, assignments)."""
    report = []

    def sub(m):
        quote, body = m.group(1), m.group(2)
        sh = _SHORTHAND_RE.match(body)
        if not sh:
            return m.group(0)
        families = sh.group("families").strip()
        # already dynamic (reads a prop or the DNA) or already migrated - leave it alone
        if "${" in families or "var(--f-" in families:
            return m.group(0)
        size = float(sh.group("size"))
        role = _role(families, size)
        line = text[: m.start()].count("\n") + 1
        report.append({"line": line, "size": size, "role": role, "families": families})
        head = sh.group("head") + sh.group("size") + "px" + (sh.group("lh") or "")
        return "font: %s%s var(--f-%s, %s)%s" % (quote, head, role, families, quote)

    # An SVG font-family="..." attribute cannot take a var(); _DECL_RE only matches `font:` in a CSS
    # context, so attributes are excluded by construction. Asserted by a test.
    return _DECL_RE.sub(sub, text), report


def main(argv):
    apply = "--apply" in argv
    rows, total = [], 0
    for name in sorted(os.listdir(_SHOTS)):
        if not name.endswith(".tsx"):
            continue
        path = os.path.join(_SHOTS, name)
        src = open(path, encoding="utf-8").read()
        out, rep = rewrite_font_decl(src)
        if not rep:
            continue
        total += len(rep)
        for r in rep:
            rows.append(dict(r, shot=name))
        if apply:
            open(path, "w", encoding="utf-8").write(out)
    if apply:
        print("rewrote %d declarations across %d shots" % (total, len({r['shot'] for r in rows})))
    else:
        print(json.dumps(rows, indent=1))
        print("\n%d declarations in %d shots" % (total, len({r['shot'] for r in rows})))
        for role in ("display", "body", "mono"):
            print("  %-8s %d" % (role, sum(1 for r in rows if r["role"] == role)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_remotion.py -k codemod -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Produce the assignment report**

Run: `python3 scripts/dna_migrate_type.py --report > /tmp/type-assignments.json`
Expected: a JSON array plus a summary. Roughly 93 shots carry `font:` shorthands.

- [ ] **Step 6: Review the assignments**

Read the report. Check specifically:
- every entry with `size >= 64` and `role: "display"` is genuinely a heading, not a large decorative number that should track the body face;
- no entry with `role: "mono"` names a proportional family (a false `_MONO_RE` hit);
- the `body` count dominates — a report where most entries are `display` means the threshold is wrong.

Record any entry you believe is misassigned, with the shot and line, in the task report. Do **not** hand-fix them in this task.

- [ ] **Step 7: Commit**

```bash
git add scripts/dna_migrate_type.py tests/test_remotion.py
git commit -m "feat(scripts): codemod hardcoded shot fonts onto DNA type variables"
```

---

### Task 9: Apply the migration behind a pixel gate (Layer C2)

**Files:**
- Create: `scripts/null_dna_pixel_gate.py`
- Modify: ~93 files under `remotion/src/shots/` (by codemod)
- Modify: `remotion/src/shots/InflateType.tsx`, `ElasticType.tsx`, `AntiDesignChaos.tsx`, `VariableTypeMorph.tsx`, `CodeRain.tsx`, `ComicPanels.tsx`, `RansomZine.tsx` (by hand)

**Interfaces:**
- Consumes: `rewrite_font_decl` from Task 8, the variables from Task 7.
- Produces: a library whose type follows the DNA.

- [ ] **Step 1: Write the pixel gate**

Create `scripts/null_dna_pixel_gate.py`:

```python
#!/usr/bin/env python3
"""null_dna_pixel_gate — prove a change did not alter what an UN-THEMED film renders.

Layer C's whole safety argument is that `var(--f-body, <original list>)` with the variable unset
resolves to the original list. That is a claim about real CSS in a real browser, so it is checked by
hashing real renders - not by asserting that a variable is present.

  python3 scripts/null_dna_pixel_gate.py --save   before/    # hash N shots as they render today
  python3 scripts/null_dna_pixel_gate.py --check  before/    # re-render and compare

Any differing shot is printed with its two hashes and the gate exits 1.
"""
import hashlib, json, os, subprocess, sys, tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")

# A stratified sample: the largest type, the smallest type, mono-heavy, mixed, and the shots that
# already read the DNA directly (which the codemod must have left alone).
SHOTS = ["EdStat", "TermCounter", "ChartLive", "VelocitySnap", "TermBars", "KnowledgeGraph",
         "CinematicTitle", "SwissEditorial", "MaterialHero", "BlueprintGrid", "ChatThread",
         "CodeCompose", "TermTable", "TermDiff", "AnswerStream", "TimelineTravel", "MapRoutes",
         "ExplodedSchematic", "NeonGrid", "ComicPanels"]


def _hash_shot(shot, td):
    png = os.path.join(td, shot + ".png")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, png,
                        "--frame=100", "--gl=angle"],
                       cwd=_REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("render failed for %s\n%s" % (shot, r.stderr[-1500:]))
    return hashlib.sha256(open(png, "rb").read()).hexdigest()


def main(argv):
    mode = argv[0] if argv else "--check"
    store = argv[1] if len(argv) > 1 else "/tmp/null-dna-hashes.json"
    with tempfile.TemporaryDirectory() as td:
        now = {s: _hash_shot(s, td) for s in SHOTS}
    if mode == "--save":
        json.dump(now, open(store, "w"), indent=1)
        print("saved %d hashes to %s" % (len(now), store))
        return 0
    before = json.load(open(store))
    bad = [s for s in SHOTS if before.get(s) != now[s]]
    for s in bad:
        print("CHANGED %s\n  before %s\n  after  %s" % (s, before.get(s), now[s]))
    if bad:
        print("\nnull-DNA pixel gate FAILED on %d/%d shots" % (len(bad), len(SHOTS)))
        return 1
    print("null-DNA pixel gate: all %d shots render identically" % len(SHOTS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 2: Capture the BEFORE hashes**

Run: `python3 scripts/null_dna_pixel_gate.py --save /tmp/null-dna-hashes.json`
Expected: `saved 20 hashes`.

This must run **before** any shot file is touched. If it runs after, the gate proves nothing.

- [ ] **Step 3: Apply the codemod**

Run: `python3 scripts/dna_migrate_type.py --apply`
Expected: `rewrote <N> declarations across <M> shots`, with M around 93.

- [ ] **Step 4: Migrate the seven `fontFamily:` shots by hand**

The codemod handles `font:` shorthands only. These seven shots set `fontFamily:` separately, and each needs its role chosen by reading what the text is:

`InflateType.tsx`, `ElasticType.tsx`, `AntiDesignChaos.tsx`, `VariableTypeMorph.tsx`, `ComicPanels.tsx`, `RansomZine.tsx` — these are display-type registers whose whole subject is large lettering; use `--f-display`. `CodeRain.tsx` renders falling code glyphs; use `--f-mono`.

Rewrite each occurrence in the same shape the codemod uses:

```tsx
fontFamily: 'Inter, system-ui, sans-serif'
// becomes
fontFamily: 'var(--f-display, Inter, system-ui, sans-serif)'
```

Leave any `fontFamily` that already interpolates a value alone.

- [ ] **Step 5: Run the pixel gate**

Run: `python3 scripts/null_dna_pixel_gate.py --check /tmp/null-dna-hashes.json`
Expected: `null-DNA pixel gate: all 20 shots render identically`.

A failure here means a rewrite changed an un-themed frame — the fallback list was altered, or a declaration was mangled. Fix the rewrite; do not re-baseline the hashes.

- [ ] **Step 6: Verify the variables actually take effect when a DNA IS present**

Run: `python3 scripts/type_specimens.py /tmp/type-after`
Open `/tmp/type-after/specimens.png` and compare against the Task 5 sheet. Body and display text across the library must now follow each direction's faces, not just the handful of shots that read the DNA directly. If a row is unchanged from Task 5, the variables are not reaching that shot — investigate before reporting done.

- [ ] **Step 7: Run the full suite and the smoke test**

Run: `python3 -m pytest tests/ -v && python3 scripts/dna_smoke.py editorial && python3 scripts/font_gate.py`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add scripts/null_dna_pixel_gate.py remotion/src/shots/
git commit -m "feat(shots): read the DNA's typefaces through CSS variables"
```

---

### Task 10: Audit reporting and documentation

**Files:**
- Modify: `scripts/dna_audit.py`
- Modify: `references/remotion-shot-authoring.md`, `remotion/LIBRARY.md`, `SKILL.md`, `agents/shot-director.md`
- Test: `tests/test_remotion.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `dna_audit.py --type` reporting per-shot type reach.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_remotion.py`:

```python
def test_every_shot_reads_the_type_variables_or_the_dna_directly():
    """After Layer C, a shot that renders text must get its face from the DNA - through a variable
    or through useDNA(). A shot that hardcodes a family again is a regression."""
    offenders = []
    for name in sorted(os.listdir(_SHOTS_DIR)):
        if not name.endswith(".tsx"):
            continue
        src = open(os.path.join(_SHOTS_DIR, name), encoding="utf-8").read()
        hardcoded = re.findall(r"font: *['`][^'`]*?\d+px[^'`]* (?!var\(--f-)[A-Z\"][^'`]*['`]", src)
        hardcoded = [h for h in hardcoded if "${" not in h.split("px", 1)[-1]]
        if hardcoded:
            offenders.append((name, hardcoded[:2]))
    assert not offenders, "shots still hardcode a font family: %r" % offenders[:5]
```

- [ ] **Step 2: Run it to verify it passes**

Run: `python3 -m pytest tests/test_remotion.py -k reads_the_type_variables -v`
Expected: PASS — Task 9 already migrated the library. If it fails, it names shots Task 9 missed; migrate those before continuing.

- [ ] **Step 3: Add `--type` to the audit**

In `scripts/dna_audit.py`, add this function and wire `--type` in `main` to call it and return its exit code:

```python
_TYPE_ROLES = ("display", "body", "mono")


def type_report(shots_dir):
    """Per-role type reach across the library. The spec's baseline, before this layer, was
    display 4 / body 3 / mono 10 of 134 shots - the tokens were declared and almost never read."""
    reach = {r: set() for r in _TYPE_ROLES}
    total = 0
    for name in sorted(os.listdir(shots_dir)):
        if not name.endswith(".tsx"):
            continue
        total += 1
        src = open(os.path.join(shots_dir, name), encoding="utf-8").read()
        for role in _TYPE_ROLES:
            token = role.capitalize() if role != "display" else "Display"
            if ("var(--f-%s" % role) in src or ("dna?.font%s" % token) in src:
                reach[role].add(name)
    print("type reach across %d shots:" % total)
    for role in _TYPE_ROLES:
        print("  %-8s %3d" % (role, len(reach[role])))
    silent = [n for n in sorted(os.listdir(shots_dir))
              if n.endswith(".tsx") and not any(n in reach[r] for r in _TYPE_ROLES)]
    if silent:
        print("  %d shots read no type token at all:" % len(silent))
        for n in silent[:10]:
            print("    " + n)
    return 0
```

Note `token` resolves to `Display` / `Body` / `Mono`, matching the `dna?.fontDisplay` / `dna?.fontBody` / `dna?.fontMono` property names in `dna.tsx`.

- [ ] **Step 4: Run it**

Run: `python3 scripts/dna_audit.py --type`
Expected: a summary showing display/body/mono reach across 134 shots. Record the three numbers in the task report — the spec's baseline was 4 / 3 / 10.

- [ ] **Step 5: Document the layer**

- `references/remotion-shot-authoring.md`: add a §C3 "Type" section stating that shots must write `var(--f-display|body|mono, <fallback list>)` and never a bare family; that the fallback list is what an un-themed film renders; and that a `uniformType` DNA's `!important` rule overrides the variables by design.
- `remotion/LIBRARY.md`: note that the library's type follows the film's DNA and list the eight directions' stacks.
- `SKILL.md`: one bullet in the DNA tooling list — `font_gate.py`, `dna_migrate_type.py`, `null_dna_pixel_gate.py`, `type_specimens.py`, `dna_audit.py --type`.
- `agents/shot-director.md`: in the worked `design_dna` JSON, show the three font fields with a CJK-terminated stack, and state that any family named must be one `fonts.ts` loads.

- [ ] **Step 6: Commit**

```bash
git add scripts/dna_audit.py tests/test_remotion.py references/remotion-shot-authoring.md \
        remotion/LIBRARY.md SKILL.md agents/shot-director.md
git commit -m "docs: document the DNA type layer and report its reach"
```

---

## Verification checklist (run before reporting the plan complete)

```bash
python3 -m pytest tests/ -v
python3 scripts/font_gate.py
python3 scripts/null_dna_pixel_gate.py --check /tmp/null-dna-hashes.json
python3 scripts/dna_smoke.py editorial
python3 scripts/dna_smoke.py terminal
python3 scripts/dna_audit.py --type
python3 scripts/type_specimens.py /tmp/type-final
```

Then **open** `/tmp/type-final/specimens.png` and look at all eight rows. Every gate above can pass on typographically wrong output; only the sheet shows whether the directions actually read as different design languages.
