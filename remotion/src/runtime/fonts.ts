// FONTS — the remotion tier used to load NOTHING: every family named in a DNA was a bare CSS family
// name resolved against whatever the render host had installed. On a machine without them, the
// "editorial high-contrast serif" was Georgia and the terminal monospace was SF Mono, and output
// therefore varied by machine — a determinism defect on a tier that otherwise pins seeds and hashes
// clips. Only FOUR of the ten faces below (Space Grotesk, Playfair Display, JetBrains Mono, Bangers)
// are shared with the HTML tier — those four must match assets/html/base.css verbatim (family, file,
// weight range; test_fonts_ts_loads_every_bundled_face_with_base_css_weights checks it). The other
// six (Inter, Source Serif 4, IBM Plex Sans, IBM Plex Mono, Bodoni Moda, Baloo 2) exist ONLY here —
// base.css declares no @font-face for them, so the HTML tier does not render these directions'
// fonts at all. The two tiers do NOT name one set of faces.
//
// The imports below are resolved by the bundler into asset URLs. staticFile() is deliberately NOT
// used: render_remotion.py points --public-dir at the film's out_dir, and a standalone
// `npx remotion still` has a different public dir again, so a bundled asset is the only path that
// works for both.
import {cancelRender, continueRender, delayRender} from 'remotion';

import spaceGroteskUrl from '../../../assets/fonts/SpaceGrotesk-VF.ttf';
import playfairDisplayUrl from '../../../assets/fonts/PlayfairDisplay-VF.ttf';
import jetBrainsMonoUrl from '../../../assets/fonts/JetBrainsMono-VF.ttf';
import bangersUrl from '../../../assets/fonts/Bangers-Regular.ttf';
import interUrl from '../../../assets/fonts/Inter-VF.ttf';
import sourceSerif4Url from '../../../assets/fonts/SourceSerif4-VF.ttf';
import ibmPlexSansUrl from '../../../assets/fonts/IBMPlexSans-VF.ttf';
import ibmPlexMonoUrl from '../../../assets/fonts/IBMPlexMono-Regular.ttf';
import bodoniModaUrl from '../../../assets/fonts/BodoniModa-VF.ttf';
import baloo2Url from '../../../assets/fonts/Baloo2-VF.ttf';
import notoSansSCUrl from '../../../assets/fonts/NotoSansSC-Subset.ttf';
import notoSerifSCUrl from '../../../assets/fonts/NotoSerifSC-Subset.ttf';

export type Face = {
  family: string;      // for the 4 faces shared with the HTML tier, must match assets/html/base.css
                        // verbatim; the other 6 are remotion-only and have no base.css counterpart
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
  {family: 'Inter', file: 'Inter-VF.ttf', url: interUrl, weight: '100 900', variable: true},
  {family: 'Source Serif 4', file: 'SourceSerif4-VF.ttf', url: sourceSerif4Url, weight: '200 900', variable: true},
  {family: 'IBM Plex Sans', file: 'IBMPlexSans-VF.ttf', url: ibmPlexSansUrl, weight: '100 700', variable: true},
  {family: 'IBM Plex Mono', file: 'IBMPlexMono-Regular.ttf', url: ibmPlexMonoUrl, weight: '400', variable: false},
  {family: 'Bodoni Moda', file: 'BodoniModa-VF.ttf', url: bodoniModaUrl, weight: '400 900', variable: true},
  {family: 'Baloo 2', file: 'Baloo2-VF.ttf', url: baloo2Url, weight: '400 800', variable: true},
  // THE CJK FACES. Ten Latin faces were bundled and none of them carries a single Han glyph, so every
  // Chinese character in every film was drawn by whatever the render machine happened to have — the exact
  // determinism defect the header above says this file exists to end, left in place for CJK. Measured on
  // one register across the two DNAs whose display faces differ most: the same title in English rendered
  // 1480px and 1573px wide (the face doing its job) and the same title in Chinese rendered 1383px in BOTH
  // — 0px apart, one system fallback drawing for both. On a CJK film the Design DNA's typography, the
  // first token it declares, did nothing at all.
  //
  // SIL OFL, subset to GB2312's 6763 Han plus kana, CJK punctuation, fullwidth forms, Latin and digits:
  // 10.05MB -> 2.20MB and 14.10MB -> 3.05MB. A character outside that set would render as tofu, so
  // cjk_type_qa.subset_coverage() reads the font file and validate.py refuses a board holding one, naming
  // the character — a glyph the face cannot draw is an empty box beside correct type, and reads as a bug.
  //
  // AND THEY ARE THE VARIABLE CUTS, which is not a detail. The first subsets were the STATIC Regular files
  // and this table declared them `'400 700', variable: true` — a lie the browser believes: told the face
  // covers the range, it draws 800-weight Chinese at 400 instead of synthesising a bold. A delivered film's
  // masthead came back visibly lighter than the same frame drawn in the system fallback, which is the
  // opposite of what bundling a face is for. `tests/test_remotion.py` now reads the files and refuses a
  // declaration the file cannot honour.
  {family: 'Noto Sans SC', file: 'NotoSansSC-Subset.ttf', url: notoSansSCUrl, weight: '100 900', variable: true},
  {family: 'Noto Serif SC', file: 'NotoSerifSC-Subset.ttf', url: notoSerifSCUrl, weight: '200 900', variable: true},
];

// One delayRender for the whole set: the first frame must not render in a fallback face.
// A GENEROUS timeout, not the default. These are local bundled assets and load in milliseconds on an idle
// machine (measured: no-fonts vs ten-fonts renders of the same frame, 5523ms vs 5477ms). But Remotion opens
// many tabs and each one loads the set; under a long high-concurrency render a starved tab blew past the
// default and killed a 37-scene film at frame 1810. Failing the whole render because one tab was slow is
// the wrong trade — cancelRender below still fires on a real load ERROR, which is the case that matters.
//
// The faces are loaded through the FontFace API DIRECTLY rather than through @remotion/fonts'
// loadFont. loadFont opens its OWN delayRender per face, and that one takes the CLI's global
// --timeout (120s) — the generous timeout above governed only our handle, not the ten hidden ones
// underneath it. A 37-scene film then died at exactly the failure this comment describes:
//   delayRender() "Loading font Space Grotesk (url: …)" was called but not cleared after 118000ms
// with the bundled asset sitting on local disk the whole time. One handle, one timeout, ours.
const handle = delayRender('loading DNA typefaces', {timeoutInMilliseconds: 300000});
Promise.all(
  FACES.map(async (f) => {
    const face = new FontFace(f.family, `url(${f.url}) format('truetype')`, {weight: f.weight});
    await face.load();
    document.fonts.add(face);
  }),
)
  .then(() => continueRender(handle))
  .catch((err) => cancelRender(err));
