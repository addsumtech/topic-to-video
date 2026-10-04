// SHOT · Molecule Ball-Stick — a ball-and-stick molecule (a hex ring + outer atoms) rotates in REAL 3D
// geometry projected BY HAND (`proj()` below, not WebGL): bonds are depth-sorted sticks, atoms are
// depth-shaded spheres coloured by element, assembling with a spin. The positions are genuinely three-
// dimensional and the sorting is genuine; only the renderer is 2D, and saying so is the difference between
// a technique and a claim. A chemistry
// register (family S · scientific/molecular). Deterministic (rotation = fn of t; positions fixed).
//
// ELEMENTS ARE A CLAIM, SO THEY COME FROM THE FILM. This drew one fixed, made-up molecule under any title: a
// carbon ring with oxygen, nitrogen and hydrogen hung off it, the element of each outer atom picked by its
// POSITION (`el: (k % 3) + 1`). A chemistry film titled with its own compound would have shown a structure
// that compound does not have, coloured as specific elements, and nothing said so. Now a film that has a
// molecule passes it — `molecule: {atoms: [{x, y, z?, el}], bonds: [[a, b]]}` with element symbols — and it is
// drawn in the conventional CPK colours. Without one, the register draws its ring form in ONE neutral tone:
// the shape of "a molecule", naming no element and no compound.
//
// THE CPK COLOURS ARE THE MEANING AND ARE KEPT, ON ANY GROUND — oxygen is red, nitrogen is blue, and a film
// that says so must not be re-coloured, re-exposed or re-balanced by a design system. What is NOT an element
// colour is everything else on the frame: the bonds, the specular on a ball, the title, the tagline and the
// ground, and those are the film's. A light ground is met the way print meets it — every ball gets an edge.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA, mix, shade} from '../runtime/dna';
import {onLight, groundFrom} from '../runtime/light';
import {bottomInset} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#070a14';
const POOL_D0 = '#101430';        // the lit core of the ground, a LIFT off this register's own night
const BOND_D0 = '#9fb0d0', BOND_OP_D0 = 0.5;
const SPEC_D0 = '#ffffff';        // the specular cap on a ball
const TITLE_D0 = '#eaf2ff', TAG_D0 = '#9fb2d0';
// CPK colours for the elements a film is likely to name; an element outside this table throws rather than
// being drawn in a guessed colour.
const CPK: Record<string, string> = {
  H: '#e6ecff', C: '#6b7488', N: '#5b8cff', O: '#ff5b5b', F: '#8fe06a', Cl: '#3fd07a', Br: '#b0503a',
  I: '#9a52d0', S: '#f2d24a', P: '#ff9a3c', B: '#f5b5a0', Si: '#d8b88a', Na: '#a86bff', K: '#8f4fe0',
  Mg: '#7fe07f', Ca: '#7fd0a0', Fe: '#e07a3a', Zn: '#8a90d8', Cu: '#d88a4a',
};
const NEUTRAL = '#8f9ab2';   // the generic form: an atom, not any element

export type MoleculeAtom = {x: number; y: number; z?: number; el: string};
export type Molecule = {atoms: MoleculeAtom[]; bonds: [number, number][]};
export const MAX_MOLECULE_ATOMS = 40;

export const MoleculeBallStick: React.FC<{title?: string; tagline?: string; molecule?: Molecule | null}> = ({
  title: TITLE = 'Composed', tagline: TAG = 'the chemistry of it', molecule: MOL = null} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  // A BALL-AND-STICK MODEL IS A DRAWING, NOT A LIGHT — it is printed on white in every chemistry book — so it
  // takes the film's ground and ink. Measured on a light film (`ink_contrast_qa.py`): 28.7% of this register's
  // ink under 3:1, and the mark render names two things — a ring around ball after ball, which is each one's
  // BLOOM and not the ball, and the tagline.
  //
  // THE ELEMENT COLOURS ARE NOT EXPOSED, THEY ARE OUTLINED. Walking them to the ink floor is what this file
  // does for a hue it owns, and it cannot be done to CPK: on the probe's paper it lands hydrogen's #e6ecff on
  // #696c75 and carbon's #6b7488 on #676f82 — the two commonest atoms in organic chemistry, the same grey,
  // the claim gone. So every ball keeps its element colour exactly and a light ground gets what a printed
  // model gets: a hairline of the film's ink around each one, drawn by the same hand as the sticks. Hydrogen
  // is then a white ball with an edge, which is what it is on paper, rather than 1.07:1 of nothing.
  const lit = dna && onLight(dna) ? groundFrom(dna, {bg: dna.bg}) : null;
  // The ground's core is a LIFT off this register's own night; on a light film the literal is a dark blob in
  // the middle of the page (the light probe rendered the whole molecule in that murk rather than on the paper).
  const POOL = lit ? shade(BG, 0.06) : POOL_D0;
  // A bond is not an element: it is a rule drawn between two of them, so it is the film's secondary ink — and
  // on a light ground it is also the ball edge. Its alpha is a dark-ground device: half of a pale slate is a
  // lit stick on black and half-way to the page on paper, so lit, the stick is drawn nearer full strength.
  const BOND = dna ? mix(dna.fg, dna.dim, 0.4) : BOND_D0;
  const BOND_OP = lit ? 0.7 : BOND_OP_D0;
  const TITLE_INK = dna?.fg ?? TITLE_D0;
  const TAG_INK = dna ? mix(dna.fg, dna.dim, 0.4) : TAG_D0;
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  // THE MOLECULE LIVES ABOVE ITS TITLE. It was centred on the frame at a fixed 220px per unit, so the outer
  // atoms swung down through the title and tagline as it turned (measured: the ring's lowest atom at y≈950 on a
  // 1080 frame whose title starts near 780). The title block's top is computed from the same numbers it is laid
  // out with, and the scale below is fitted to the room above it over the WHOLE rotation, not the first frame.
  const titlePx = Math.round(Math.min(104, W * 0.09)), tagPx = Math.round(Math.min(30, W * 0.028));
  const titleTop = H - bottomInset(W, H, 110) - tagPx - Math.round(U * 0.015) - titlePx;
  const zoneTop = Math.round(H * 0.07), zoneBot = titleTop - Math.round(U * 0.035);
  const cx = W / 2, cy = (zoneTop + zoneBot) / 2;
  const atoms: {p: [number, number, number]; c: string; r: number}[] = [];
  const bonds: [number, number][] = [];
  if (MOL) {
    const list = Array.isArray(MOL.atoms) ? MOL.atoms : [];
    if (list.length < 2 || list.length > MAX_MOLECULE_ATOMS) {
      throw new Error(`MoleculeBallStick: \`molecule.atoms\` needs 2-${MAX_MOLECULE_ATOMS} atoms (got ${list.length}).`);
    }
    const pts = list.map((a, i) => {
      const x = Number(a?.x), y = Number(a?.y), z = Number(a?.z ?? 0);
      if (![x, y, z].every(Number.isFinite)) throw new Error(`MoleculeBallStick: atom ${i + 1} needs finite x, y (and z).`);
      const el = String(a?.el ?? '').trim();
      if (!CPK[el]) {
        throw new Error(`MoleculeBallStick: atom ${i + 1} has element "${el}", which has no colour here. ` +
          `Known: ${Object.keys(CPK).join(', ')}.`);
      }
      return {x, y, z, el};
    });
    // centre the film's coordinates and scale the farthest atom to the same radius the generic form uses
    const mx = pts.reduce((n, q) => n + q.x, 0) / pts.length, my = pts.reduce((n, q) => n + q.y, 0) / pts.length;
    const mz = pts.reduce((n, q) => n + q.z, 0) / pts.length;
    const far = Math.max(1e-6, ...pts.map((q) => Math.hypot(q.x - mx, q.y - my, q.z - mz)));
    for (const q of pts) {
      atoms.push({p: [(q.x - mx) / far * 1.9, (q.y - my) / far * 1.9, (q.z - mz) / far * 1.9],
        c: CPK[q.el], r: q.el === 'H' ? 18 : 26});
    }
    for (const [k, b] of (Array.isArray(MOL.bonds) ? MOL.bonds : []).entries()) {
      const [a1, a2] = Array.isArray(b) ? b : [NaN, NaN];
      if (!Number.isInteger(a1) || !Number.isInteger(a2) || a1 < 0 || a2 < 0 || a1 >= pts.length || a2 >= pts.length || a1 === a2) {
        throw new Error(`MoleculeBallStick: bond ${k + 1} must join two different atom indices 0-${pts.length - 1}.`);
      }
      bonds.push([a1, a2]);
    }
  } else {
    // the generic form: a 6-ring + an outer atom off each ring vertex, every atom the same neutral tone
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2;
      atoms.push({p: [Math.cos(a), Math.sin(a), Math.sin(a * 2) * 0.3], c: NEUTRAL, r: 30});
      bonds.push([k, (k + 1) % 6]);
    }
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2, R = 1.9;
      atoms.push({p: [Math.cos(a) * R, Math.sin(a) * R, Math.sin(a * 2) * 0.5], c: NEUTRAL, r: 22});
      bonds.push([k, 6 + k]);
    }
  }
  const build = easeOutBack(clamp01(seg(t, 0.06, 0.44)));
  const tilt = -0.4;
  // unit-scale projection at rotation `ang` — x/y in molecule units, before the frame scale S is applied
  const unitProj = (p: [number, number, number], ang: number) => {
    const ca = Math.cos(ang), sa = Math.sin(ang);
    const x = p[0] * ca + p[2] * sa, z0 = -p[0] * sa + p[2] * ca, y = p[1];
    const y2 = y * Math.cos(tilt) - z0 * Math.sin(tilt), z = y * Math.sin(tilt) + z0 * Math.cos(tilt);
    const persp = 2 / (2 - z * 0.5);
    return {x: x * persp, y: y2 * persp, z, persp};
  };
  // THE MOLECULE ROCKS ABOUT ITS FACE; IT DOES NOT TURN AWAY. It turned 1.6 rad one way over the clip — 92° —
  // so a flat molecule (every atom at z = 0, which is what most films will pass) ended the beat seen edge-on,
  // a line of overlapping balls under its own title. It now swings ±0.5 rad around facing the viewer: the depth
  // still reads, and the settled frame still shows the structure.
  const angAt = (tt: number) => (tt - 0.5) * 1.0;
  // the largest extent any atom reaches over the rotation this clip actually plays, plus that atom's own radius,
  // so S fits the ball and not just its centre
  let ext = {x: 1e-6, y: 1e-6};
  for (let k = 0; k <= 32; k++) {
    for (const at of atoms) {
      const q = unitProj(at.p, angAt(k / 32));
      ext = {x: Math.max(ext.x, Math.abs(q.x)), y: Math.max(ext.y, Math.abs(q.y))};
    }
  }
  const rMax = Math.max(...atoms.map((a) => a.r)) * 1.25 * 1.1;   // 1.1 = easeOutBack's overshoot
  const S = Math.min(220, (W * 0.42 - rMax) / ext.x, ((zoneBot - zoneTop) / 2 - rMax) / ext.y);
  const ang = angAt(t);
  const proj = (p: [number, number, number]) => {
    const q = unitProj(p, ang);
    return {x: cx + q.x * S * build, y: cy + q.y * S * build, z: q.z, persp: q.persp};
  };
  const pa = atoms.map((at) => ({...at, s: proj(at.p)}));
  const titleIn = easeOutCubic(seg(t, 0.52, 0.76));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 42%, ${POOL}, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* bonds (behind) */}
        {bonds.map(([a, b], i) => {
          const A = pa[a].s, B = pa[b].s;
          return <line key={'b' + i} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={BOND}
            strokeWidth={7 * ((A.persp + B.persp) / 2)} strokeLinecap="round" opacity={BOND_OP * build} />;
        })}
        {/* atoms (depth-sorted) */}
        {[...pa].map((at, i) => ({at, i})).sort((u, v) => u.at.s.z - v.at.s.z).map(({at, i}) => {
          const depth = clamp01((at.s.z + 1) / 2);
          return <g key={'a' + i} opacity={clamp01(build)}>
            {/* The bloom is a dark-ground device — it is the ring the gate flagged on ball after ball: on paper
                it is a wash of the element's colour lying between the ball and the page, dissolving the very
                edge it is meant to lift. Lit, the edge is DRAWN instead, which is also what carries a white
                hydrogen on a white page. */}
            <circle cx={at.s.x} cy={at.s.y} r={at.r * at.s.persp} fill={at.c}
              stroke={lit ? BOND : undefined} strokeWidth={lit ? 2 : undefined}
              style={{filter: lit ? 'none' : `drop-shadow(0 0 10px ${at.c}66)`}} />
            {/* A BALL'S LIT FACE CANNOT BE BRIGHTER THAN THE PAPER IT SITS ON. The gate did not flag this cap —
                it measures it against the ball it sits on — but pure white on a pale element ON PAPER is a hole
                punched through the atom rather than a highlight. Lit, it is a LIFT of the element's own colour,
                so a white hydrogen simply has no visible cap; on a dark ground it is still white. */}
            <ellipse cx={at.s.x - at.r * 0.3 * at.s.persp} cy={at.s.y - at.r * 0.32 * at.s.persp}
              rx={at.r * 0.3 * at.s.persp} ry={at.r * 0.22 * at.s.persp}
              fill={lit ? mix(at.c, '#ffffff', 0.3) : SPEC_D0} opacity={0.4 + 0.3 * depth} />
          </g>;
        })}
      </svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', paddingBottom: bottomInset(W, H, 110)}}>
        {/* the title and its tagline are ON the ground, so they are the film's ink and its metadata; the
            separation shadow is the ground's own colour on paper, never a fixed black under near-black type */}
        <div style={{opacity: titleIn, transform: glide(`translateY(${(1 - titleIn) * 14}px)`, titleIn !== 1), color: TITLE_INK,
          font: `800 ${titlePx}px/1 var(--f-display, Inter, system-ui, sans-serif)`, letterSpacing: '-0.03em', textShadow: `0 8px 40px ${lit ? BG : '#000'}`}}>{TITLE}</div>
        <div style={{opacity: easeOutCubic(seg(t, 0.62, 0.84)), marginTop: Math.round(U * 0.015), color: TAG_INK,
          font: `600 ${tagPx}px/1 var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.18em'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default MoleculeBallStick;
