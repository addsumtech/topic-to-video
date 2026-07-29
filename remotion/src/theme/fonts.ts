import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

// Load the deck's REAL bundled faces so the cinematic tier renders the same typography as the HTML
// tier — on ANY machine, not just one where the fonts happen to be installed. render_remotion._copy_fonts
// stages assets/fonts/*.ttf into <out_dir>/.fonts/; staticFile() resolves against --public-dir=<out_dir>.
//
// These are the four bundled SIL-OFL faces theme.py maps --font-kind to (see theme.py _FONT_FAMILIES):
// Space Grotesk (sans), Playfair Display (serif), JetBrains Mono (mono), Bangers (comic). The first
// three are VARIABLE fonts (one -VF.ttf spans all weights → register a '100 900' range so fontWeight
// 700/800 resolve to the real weight axis, not a synthesized bold); Bangers ships a single Regular.
//
// loadFont() calls delayRender()/continueRender() internally, so importing this module (Root.tsx does)
// BLOCKS the render until the faces are ready — deterministic, no FOUT. display:'block' hides text until
// the face loads rather than flashing a fallback. Family names EXACTLY match the CSS stacks theme.py
// emits, so the fontFamily strings in tokens resolve to these @font-face registrations.

type Face = {family: string; file: string; weight: string};

const BUNDLED_FACES: Face[] = [
  {family: 'Space Grotesk', file: 'SpaceGrotesk-VF.ttf', weight: '100 900'},
  {family: 'Playfair Display', file: 'PlayfairDisplay-VF.ttf', weight: '100 900'},
  {family: 'JetBrains Mono', file: 'JetBrainsMono-VF.ttf', weight: '100 900'},
  {family: 'Bangers', file: 'Bangers-Regular.ttf', weight: '400'},
];

let loaded: Promise<void[]> | null = null;

// Idempotent: registers every bundled face once. Safe to call at module scope and repeatedly.
// A missing file (e.g. a face not staged) rejects only that one load; the others still register, so a
// deck using an available face is never blocked by an absent one.
export function loadDeckFonts(): Promise<void[]> {
  if (loaded) return loaded;
  loaded = Promise.all(
    BUNDLED_FACES.map((f) =>
      loadFont({family: f.family, url: staticFile(`.fonts/${f.file}`), weight: f.weight, display: 'block'}).catch(
        (err) => {
          // Non-fatal: a deck that doesn't use this face must still render. Surfaced in the render log.
          // eslint-disable-next-line no-console
          console.warn(`[fonts] could not load ${f.family} (${f.file}): ${err}`);
        },
      ),
    ),
  );
  return loaded;
}
