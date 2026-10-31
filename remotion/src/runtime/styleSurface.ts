// THE SURFACE A DRAWING IS MADE ON, as a tile a box paints under its own content.
//
// A box's background is painted beneath its children, so a texture laid in as one more background layer textures
// the ground and the cards and never the type set on them. The tile is an SVG of seeded noise — static, the same on
// every frame and every render. (An SVG group takes the same medium through a filter: runtime/styleFilters.tsx.)
import {SURFACE_NOISE} from './styleFilters';

const TILE = 256;

/** A `url("data:…")` background layer of the medium `kind` at `strength` (0..1), tiled; null for no medium. */
export const surfaceTile = (kind: string, strength: number, scale: number): string | null => {
  const n = SURFACE_NOISE[kind];
  if (!n || !(strength > 0)) return null;
  const [fx, fy, oct, k] = n;
  const amt = +(k * strength).toFixed(3);
  const t = Math.round(TILE * scale);
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${t}' height='${t}'>` +
    `<filter id='n' x='0' y='0' width='100%' height='100%'>` +
    `<feTurbulence type='fractalNoise' baseFrequency='${+(fx / scale).toFixed(4)} ${+(fy / scale).toFixed(4)}' numOctaves='${oct}' seed='7' stitchTiles='stitch'/>` +
    `<feColorMatrix type='matrix' values='${2 * amt} 0 0 0 ${1 - 2 * amt}  ${2 * amt} 0 0 0 ${1 - 2 * amt}  ${2 * amt} 0 0 0 ${1 - 2 * amt}  0 0 0 0 1'/>` +
    `</filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>`;
  return `url("data:image/svg+xml;utf8,${svg.replace(/"/g, "'").replace(/</g, '%3C').replace(/>/g, '%3E')}")`;
};
