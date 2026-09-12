// SHOT · Isometric Assembly — an ORIGINAL design (isometric explainer + a factory metaphor): a RAW grey block
// rides the conveyor INTO one WorkBuddy machine and comes out the far side as a FINISHED, colour deliverable,
// which stacks on the "Delivered" pad. The literal "it does the work" made physical + legible (no bobbing).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutBack, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, inkBlockH, wrapLines} from '../runtime/layout';

export const DURATION = 165; // 5.5s
const A = Math.PI / 6;
const iso = (x: number, y: number, z: number, ox: number, oy: number): [number, number] =>
  [ox + (x - y) * Math.cos(A), oy + (x + y) * Math.sin(A) - z];

function shade(hex: string, f: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgb(${Math.round(((n >> 16) & 255) * f)},${Math.round(((n >> 8) & 255) * f)},${Math.round((n & 255) * f)})`;
}
const Cuboid: React.FC<{x: number; y: number; z: number; w: number; d: number; h: number; top: string; ox: number; oy: number; opacity?: number}> = ({x, y, z, w, d, h, top, ox, oy, opacity = 1}) => {
  const P = (X: number, Y: number, Z: number) => iso(X, Y, Z, ox, oy).join(',');
  return <g opacity={opacity}>
    <polygon points={`${P(x, y, z + h)} ${P(x + w, y, z + h)} ${P(x + w, y + d, z + h)} ${P(x, y + d, z + h)}`} fill={top} />
    <polygon points={`${P(x, y + d, z)} ${P(x + w, y + d, z)} ${P(x + w, y + d, z + h)} ${P(x, y + d, z + h)}`} fill={shade(top, 0.82)} />
    <polygon points={`${P(x + w, y, z)} ${P(x + w, y + d, z)} ${P(x + w, y + d, z + h)} ${P(x + w, y, z + h)}`} fill={shade(top, 0.62)} />
  </g>;
};

const DONE = ['#2E7BFF', '#7C5CFF', '#12B76A'];

export const IsometricAssembly: React.FC<{items?: [string, string, string]}> = ({items = ['Raw work', 'WorkBuddy', 'Delivered ✓']} = {}) => {
  // LEVEL-C: the iso factory diorama flips its GROUND to the DNA (a dark iso world) + labels/intake-glow to DNA
  // tokens; the object colours (grey raw → coloured finished, dark machine, green delivered pad) are SEMANTIC and
  // read on any ground, so they're kept. Null DNA = the original light diorama.
  const dna = useDNA();
  const bgc = dna?.bgGrad ?? dna?.bg ?? 'linear-gradient(180deg,#eef1f7,#e2e6ef)';
  const GLOW = dna?.accent ?? '#5B8CFF', L1 = dna?.dim ?? '#8791a3', L2 = dna?.fg ?? '#2b3450', L3 = dna?.accent2 ?? '#12a561';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const ox = W / 2 - 140;
  const y = 70, beltLen = 1040, mx = 440, mw = 200;   // machine occupies [mx, mx+mw] on the belt
  const inX = 60, outStart = mx + mw + 40, outX = beltLen - 40;
  // THE WHOLE SCENE IS SCALED TO THE CONTENT ZONE. An isometric projection drops (x + y)·sin(30°) below its
  // origin, so the far end of a 1040-long belt lands 635px down; with `oy` fixed at 330 the 'Delivered ✓'
  // pad label sat 49px inside the strip the renderer burns the caption over. Nudging that one label would
  // have broken it away from the pad it names, and the scene does not fit at full size — so the scene
  // yields, uniformly, and every element keeps its relationship to every other.
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  // MOVE FIRST, SCALE ONLY IF IT STILL DOES NOT FIT — and both numbers MEASURED off a render, not reasoned
  // from the projection. The scene's ink runs from 16px below the belt origin to 683px below it: 667px, and
  // the content zone at 16:9 is 677px. So it fits exactly as drawn, and all it ever needed was to be moved
  // up; at `oy = 330` it hung 160px past the zone while the top of the zone sat empty. Two guesses at these
  // constants cost real density before the ruler came out — scaling the whole scene took it from 8.9% ink to
  // 6.2%, and a wrong guess at the rise took it to 4.5%.
  const SCENE_TOP_OFF = 16;                                  // ink begins this far BELOW the belt origin
  const SCENE_DROP = 683;                                    // ink ends this far below it
  const oy = zTop - SCENE_TOP_OFF;
  const SCENE_HALF_W = 900;                                  // measured: max |iso x - ox| incl. the pad labels
  const k = Math.min(1, (zBot - zTop) / (SCENE_DROP - SCENE_TOP_OFF), (W * 0.95) / (2 * SCENE_HALF_W));
  // three parts flow through, staggered; a part is HIDDEN while inside the machine, and emerges COLOURED.
  const parts = [0, 1, 2].map((i) => {
    const p = clamp01((t - 0.06 - i * 0.26) / 0.8);
    const x = lerp(inX, outX, p);
    const inside = x > mx - 10 && x < mx + mw + 10;
    const finished = x >= mx + mw / 2;
    return {p, x, inside, finished, color: DONE[i]};
  });
  const busy = parts.some((pt) => pt.inside && pt.p < 1);
  const labelTop = (y: number, text: unknown, px: number, measure: number) =>
    Math.min(y, contentBottom(W, H) - inkBlockH(px, wrapLines(String(text ?? ''), px, measure)));

  return (
    <AbsoluteFill style={{background: bgc}}>
     <div style={{position: 'absolute', inset: 0, transform: `scale(${k})`, transformOrigin: `50% ${zTop}px`}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* conveyor slab */}
        <Cuboid x={0} y={y} z={-22} w={beltLen} d={150} h={22} top="#cdd4e1" ox={ox} oy={oy} />
        {/* IN pad (grey) + queued raw blocks */}
        <Cuboid x={inX - 70} y={y} z={0} w={54} d={150} h={14} top="#aab2c2" ox={ox} oy={oy} />
        {/* the WorkBuddy MACHINE — static, with a glowing intake slot that brightens while processing */}
        <Cuboid x={mx} y={y - 34} z={0} w={mw} d={218} h={200} top="#232a3a" ox={ox} oy={oy} />
        <Cuboid x={mx + 26} y={y - 6} z={200} w={mw - 52} d={150} h={16} top={busy ? GLOW : '#39415a'} ox={ox} oy={oy} />
        {/* OUT pad (green) where finished parts land */}
        <Cuboid x={outStart} y={y} z={0} w={outX - outStart + 40} d={150} h={12} top="#5fd996" ox={ox} oy={oy} />
        {/* the travelling parts (hidden while inside the machine, emerge coloured) */}
        {parts.map((pt, i) => (pt.p > 0 && pt.p < 1 && !pt.inside) && (
          <Cuboid key={i} x={pt.x} y={y + 34} z={0} w={82} d={82} h={pt.finished ? 92 : 66}
            top={pt.finished ? pt.color : '#b6bece'} ox={ox} oy={oy} />
        ))}
      </svg>
      {/* A PROJECTED LABEL LANDS WHERE THE GEOMETRY PUTS IT, and the geometry knows nothing about the
          caption band: a Chinese label wraps in its fixed 200-260px column and the lowest of the three
          reaches into it (21px at 16:9). Each top is clamped to the ink its own copy takes — Latin is one
          line and every label stays exactly where it was. */}
      {/* labels */}
      <div style={{position: 'absolute', left: iso(inX - 40, y + 200, 0, ox, oy)[0] - 110, top: labelTop(iso(inX - 40, y + 200, 0, ox, oy)[1], items[0], 38, 200), width: 200, textAlign: 'center', textWrap: 'balance', font: '700 38px/1.2 var(--f-body, Inter,system-ui,sans-serif)', color: L1}}>{items[0]}</div>
      <div style={{position: 'absolute', left: iso(mx + mw / 2, y + 80, 0, ox, oy)[0] - 130, top: labelTop(iso(mx + mw / 2, y + 80, 0, ox, oy)[1] - 300, items[1], 44, 260), width: 260, textAlign: 'center', textWrap: 'balance', font: '800 44px/1.15 var(--f-body, Inter,system-ui,sans-serif)', color: L2}}>{items[1]}</div>
      <div style={{position: 'absolute', left: iso(outX, y + 200, 0, ox, oy)[0] - 60, top: labelTop(iso(outX, y + 200, 0, ox, oy)[1] + 10, items[2], 40, 260), width: 260, textWrap: 'balance', font: '800 40px/1.2 var(--f-body, Inter,system-ui,sans-serif)', color: L3}}>{items[2]}</div>
     </div>
    </AbsoluteFill>
  );
};
export default IsometricAssembly;
