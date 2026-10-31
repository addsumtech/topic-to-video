// THE SURFACE A DRAWING IS MADE ON, as a tile a box paints under its own content.
//
// A box's background is painted beneath its children, so a texture laid in as one more background layer textures
// the ground and the cards and never the type set on them. The tile is an SVG of seeded noise — static, the same on
// every frame and every render. (An SVG group takes the same medium through a filter: runtime/styleFilters.tsx.)
import {SURFACE_NOISE, toothMatrix} from './styleFilters';

const TILE = 256;

/** A `url("data:…")` background layer of the medium `kind` at `strength` (0..1), tiled; null for no medium. On a
 *  `dark` ground the tooth is LIGHT grain (blended with screen): multiplied into near-black it moved one level, which
 *  no viewer sees (WordTunnel measured no surface at all). The matrix is shared with the SVG filter (toothMatrix). */
export const surfaceTile = (kind: string, strength: number, scale: number, dark = false): string | null => {
  const n = SURFACE_NOISE[kind];
  if (!n || !(strength > 0)) return null;
  const [fx, fy, oct, k] = n;
  const amt = +(k * strength).toFixed(3);
  const t = Math.round(TILE * scale);
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${t}' height='${t}'>` +
    `<filter id='n' x='0' y='0' width='100%' height='100%'>` +
    `<feTurbulence type='fractalNoise' baseFrequency='${+(fx / scale).toFixed(4)} ${+(fy / scale).toFixed(4)}' numOctaves='${oct}' seed='7' stitchTiles='stitch'/>` +
    `<feColorMatrix type='matrix' values='${toothMatrix(amt, dark)}'/>` +
    `</filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>`;
  return `url("data:image/svg+xml;utf8,${svg.replace(/"/g, "'").replace(/</g, '%3C').replace(/>/g, '%3E')}")`;
};
