import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

// Load the bundled font for this deck (theme.py writes assets/fonts/*.ttf; render_remotion.py copies to out/.fonts/).
// Called once per composition registration — promises can be shared across comps.
const fontCache = new Map<string, Promise<void>>();

export async function loadDeckFont(fontFamily: string, weight?: number | string): Promise<void> {
  const key = `${fontFamily}-${weight || 400}`;
  if (fontCache.has(key)) {
    return fontCache.get(key)!;
  }
  // Font file naming convention: "Playfair Display" -> "PlayfairDisplay-Regular.ttf"
  // Weight map: 400 -> Regular, 700 -> Bold, 300 -> Light, etc.
  const weightMap: Record<number, string> = {
    300: 'Light',
    400: 'Regular',
    500: 'Medium',
    600: 'SemiBold',
    700: 'Bold',
    900: 'Black',
  };
  const w = typeof weight === 'number' ? weight : parseInt(weight || '400', 10);
  const suffix = weightMap[w] || 'Regular';
  const familySlug = fontFamily.replace(/[^a-zA-Z0-9]/g, '');
  const url = staticFile(`.fonts/${familySlug}-${suffix}.ttf`);

  const promise = loadFont({family: fontFamily, url, weight: w, display: 'block'});
  fontCache.set(key, promise);
  return promise;
}
