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
import interUrl from '../../../assets/fonts/Inter-VF.ttf';
import sourceSerif4Url from '../../../assets/fonts/SourceSerif4-VF.ttf';
import ibmPlexSansUrl from '../../../assets/fonts/IBMPlexSans-VF.ttf';
import ibmPlexMonoUrl from '../../../assets/fonts/IBMPlexMono-Regular.ttf';
import bodoniModaUrl from '../../../assets/fonts/BodoniModa-VF.ttf';
import baloo2Url from '../../../assets/fonts/Baloo2-VF.ttf';

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
  {family: 'Inter', file: 'Inter-VF.ttf', url: interUrl, weight: '100 900', variable: true},
  {family: 'Source Serif 4', file: 'SourceSerif4-VF.ttf', url: sourceSerif4Url, weight: '200 900', variable: true},
  {family: 'IBM Plex Sans', file: 'IBMPlexSans-VF.ttf', url: ibmPlexSansUrl, weight: '100 700', variable: true},
  {family: 'IBM Plex Mono', file: 'IBMPlexMono-Regular.ttf', url: ibmPlexMonoUrl, weight: '400', variable: false},
  {family: 'Bodoni Moda', file: 'BodoniModa-VF.ttf', url: bodoniModaUrl, weight: '400 900', variable: true},
  {family: 'Baloo 2', file: 'Baloo2-VF.ttf', url: baloo2Url, weight: '400 800', variable: true},
];

// One delayRender for the whole set: the first frame must not render in a fallback face.
const handle = delayRender('loading DNA typefaces');
Promise.all(
  FACES.map((f) => loadFont({family: f.family, url: f.url, weight: f.weight, format: 'truetype'})),
)
  .then(() => continueRender(handle))
  .catch((err) => cancelRender(err));
