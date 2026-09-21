// SHOT · Isometric Assembly — an ORIGINAL design (isometric explainer + a factory metaphor): a RAW grey block
// rides the conveyor INTO one WorkBuddy machine and comes out the far side as a FINISHED, colour deliverable,
// which lines up with the others on the "Delivered" pad. The literal "it does the work" made physical + legible
// (no bobbing).
//
// THE FINISHED WORK STAYS WHERE IT WAS DELIVERED. This header used to say the finished block "stacks on the
// 'Delivered' pad", and nothing did: a part was drawn only while 0 < p < 1, so each one vanished the moment it
// reached the end of the belt, and with the third part setting off at 0.58 and taking 0.8 to cross, it was
// still hidden INSIDE the machine on the last frame (intake glowing). The settled frame — the one the viewer
// is left with, under a label saying 'Delivered ✓' — showed one part in transit, one in the machine and one
// gone: a delivery pad with nothing delivered on it, a process that never finishes.
// So the parts now run as a real conveyor against an end stop: at the SAME belt speed as before (the whole
// belt in 0.8 of the clip), set off 0.14 apart instead of 0.26, and each stops at its own slot on the pad,
// the first at the far end and the others behind it. The last one arrives at ~0.91, the intake goes dark, and
// the frame holds on three finished deliverables on the pad the label names. They are drawn back-to-front
// by belt position, because a part queued behind another is farther from the viewer in iso.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutBack, clamp01} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {onLight} from '../runtime/light';
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
// The RAW side of the diorama — belt, intake pad, unfinished block. These are greys because the work is not
// coloured yet; the value is the meaning, not the lightness, so on a light ground they are taken from the
// film's own paper→ink axis instead (see `raw` below). Lightest to darkest: belt, block, intake pad.
const BELT_D0 = '#cdd4e1', RAW_D0 = '#b6bece', INPAD_D0 = '#aab2c2';
const BELT_F = 0.52, RAW_F = 0.60, INPAD_F = 0.68;

// three parts at the old belt speed, closer together, each stopping at its slot on the pad
const N_PARTS = 3, START = 0.06, STAGGER = 0.14, SLOT_GAP = 90, PART = 82;

export const IsometricAssembly: React.FC<{items?: [string, string, string]}> = ({items: RAW = ['Raw work', 'WorkBuddy', 'Delivered ✓']} = {}) => {
  // THREE STATIONS, THREE LABELS. A fourth label used to be ignored and a missing third left the pad unnamed,
  // with no error; the diorama has exactly three stations, so anything else is refused.
  if (!Array.isArray(RAW) || RAW.length !== 3 || RAW.some((x) => !String(x ?? '').trim())) {
    throw new Error(`IsometricAssembly needs exactly three non-empty \`items\` — intake, machine, delivery pad — ` +
      `got ${JSON.stringify(RAW)}. For another number of stages use InOrder (1-6 steps) or ExplodedSchematic (1-6 parts).`);
  }
  const items = RAW.map((x) => String(x).trim());
  // LEVEL-C: the iso factory diorama flips its GROUND to the DNA (a dark iso world) + labels/intake-glow to DNA
  // tokens; the COLOURED objects (finished blocks, dark machine, green delivered pad) are SEMANTIC and read on
  // any ground, so they're kept. The uncoloured ones did not — see the raw-grey note below. Null DNA = the
  // original light diorama.
  const dna = useDNA();
  const bgc = dna?.bgGrad ?? dna?.bg ?? 'linear-gradient(180deg,#eef1f7,#e2e6ef)';
  const GLOW = dna?.accent ?? '#5B8CFF', L1 = dna?.dim ?? '#8791a3', L2 = dna?.fg ?? '#2b3450', L3 = dna?.accent2 ?? '#12a561';
  // A PALE SLAB ON PALE PAPER IS NOT A CONVEYOR. The raw side of this diorama is three light greys chosen to
  // sit on a dark iso world; on a light film they land within a hand's breadth of the page. Measured
  // (`ink_contrast_qa.py`, light probe): 35.0% of the register's ink under 3:1, and the largest hole — 0.38%
  // of the frame — is the belt's own silhouette, traced end to end, the thing everything else in the picture
  // rides on. Grey means UNFINISHED here, not "light", so on a light ground the three are taken from the
  // film's own paper→ink axis at the same order and spacing: the belt nearest the page, the intake pad
  // furthest from it. The finished blocks, the green pad and the dark machine are SEMANTIC colour and are
  // untouched — the only marks flagged on any of them are two facet edges inside one finished block, which is
  // that block's own shading and not its silhouette.
  const light = onLight(dna);
  const raw = (f: number, d0: string) => (dna && light ? mix(dna.bg, dna.fg, f) : d0);
  const BELT = raw(BELT_F, BELT_D0), RAWPART = raw(RAW_F, RAW_D0), INPAD = raw(INPAD_F, INPAD_D0);
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
  // three parts flow through, staggered; a part is HIDDEN while inside the machine, and emerges COLOURED. Each
  // travels at the belt's speed until it reaches its slot on the pad, and stays there.
  const SPEED = (outX - inX) / 0.8;                          // belt units per unit of t — the original speed
  const parts = Array.from({length: N_PARTS}, (_, i) => {
    const slot = outX - PART + 22 - i * SLOT_GAP;            // part 0 against the far end, the rest queued behind
    const start = START + i * STAGGER;
    const started = t > start;
    const x = Math.min(slot, inX + Math.max(0, t - start) * SPEED);
    const inside = x > mx - 10 && x < mx + mw + 10;
    const finished = x >= mx + mw / 2;
    return {started, x, inside, finished, color: DONE[i]};
  });
  const busy = parts.some((pt) => pt.started && pt.inside);
  // back to front by belt position (a part queued behind another is farther from the viewer); a part inside
  // the machine is hidden
  const drawOrder = parts.map((pt, i) => ({...pt, i})).filter((pt) => pt.started && !pt.inside).sort((a, b) => a.x - b.x);
  const partEl = (pt: (typeof drawOrder)[number]) => (
    <Cuboid key={pt.i} x={pt.x} y={y + 34} z={0} w={PART} d={PART} h={pt.finished ? 92 : 66}
      top={pt.finished ? pt.color : RAWPART} ox={ox} oy={oy} />
  );
  const machineRight = iso(mx + mw, y - 34, 200, ox, oy);   // the right vertex of the machine's top face
  const labelTop = (y: number, text: unknown, px: number, measure: number) =>
    Math.min(y, contentBottom(W, H) - inkBlockH(px, wrapLines(String(text ?? ''), px, measure)));

  return (
    <AbsoluteFill style={{background: bgc}}>
     <div style={{position: 'absolute', inset: 0, transform: `scale(${k})`, transformOrigin: `50% ${zTop}px`}}>
      {/* overflow visible: the scene is drawn in a W-wide SVG and then SCALED down about the centre, so at
          9:16 (k≈0.57, ox = W/2 − 140) the pad and every delivered part past x = W were cut off at the SVG's
          own edge — a vertical cut through the finished work, well inside the frame. */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        {/* conveyor slab */}
        <Cuboid x={0} y={y} z={-22} w={beltLen} d={150} h={22} top={BELT} ox={ox} oy={oy} />
        {/* IN pad (grey) + queued raw blocks */}
        <Cuboid x={inX - 70} y={y} z={0} w={54} d={150} h={14} top={INPAD} ox={ox} oy={oy} />
        {/* raw parts still UPSTREAM of the machine are drawn BEFORE it: in iso a smaller x is farther back, so
            the machine occludes a part nosing into it. They used to be painted after the machine, so for the
            last ~80 units before the intake a grey block sat pasted over the machine's front face. */}
        {drawOrder.filter((pt) => pt.x < mx).map(partEl)}
        {/* the WorkBuddy MACHINE — static, with a glowing intake slot that brightens while processing */}
        <Cuboid x={mx} y={y - 34} z={0} w={mw} d={218} h={200} top="#232a3a" ox={ox} oy={oy} />
        <Cuboid x={mx + 26} y={y - 6} z={200} w={mw - 52} d={150} h={16} top={busy ? GLOW : '#39415a'} ox={ox} oy={oy} />
        {/* OUT pad (green) where finished parts land */}
        <Cuboid x={outStart} y={y} z={0} w={outX - outStart + 40} d={150} h={12} top="#5fd996" ox={ox} oy={oy} />
        {/* the parts downstream (emerged coloured, stay on the pad), back to front */}
        {drawOrder.filter((pt) => pt.x >= mx).map(partEl)}
      </svg>
      {/* A PROJECTED LABEL LANDS WHERE THE GEOMETRY PUTS IT, and the geometry knows nothing about the
          caption band: a Chinese label wraps in its fixed 200-260px column and the lowest of the three
          reaches into it (21px at 16:9). Each top is clamped to the ink its own copy takes — Latin is one
          line and every label stays exactly where it was. */}
      {/* labels */}
      <div style={{position: 'absolute', left: iso(inX - 40, y + 200, 0, ox, oy)[0] - 110, top: labelTop(iso(inX - 40, y + 200, 0, ox, oy)[1], items[0], 38, 200), width: 200, textAlign: 'center', textWrap: 'balance', font: '700 38px/1.2 var(--f-body, Inter,system-ui,sans-serif)', color: L1}}>{items[0]}</div>
      {/* THE MACHINE'S NAME SITS BESIDE ITS TOP, on the ground, not across it. It used to hang at `-300` from
          the machine's base, centred — 7px below the machine's top vertex, dark ink across the dark machine —
          and it read only while the intake glowed blue behind it. Now that the shot settles with the machine
          idle (see the header), the settled frame ended on a half-illegible name. Above the machine there is
          no room (the scene already fills the zone from its top), so the name moves to the empty ground right
          of the machine's top face, left-aligned against its right vertex; the scene's measured extent is
          unchanged (it stays inside SCENE_HALF_W), and a wrapped name grows down into open ground, well
          above the pad. */}
      <div style={{position: 'absolute', left: machineRight[0] + 28, top: machineRight[1] - 30, width: 260, textAlign: 'left', textWrap: 'balance', font: '800 44px/1.15 var(--f-body, Inter,system-ui,sans-serif)', color: L2}}>{items[1]}</div>
      <div style={{position: 'absolute', left: iso(outX, y + 200, 0, ox, oy)[0] - 60, top: labelTop(iso(outX, y + 200, 0, ox, oy)[1] + 10, items[2], 40, 260), width: 260, textWrap: 'balance', font: '800 40px/1.2 var(--f-body, Inter,system-ui,sans-serif)', color: L3}}>{items[2]}</div>
     </div>
    </AbsoluteFill>
  );
};
export default IsometricAssembly;
