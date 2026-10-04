// SHOT · Atom Orbital — an atom: a glowing nucleus at the core and electron orbits around it, the whole atom
// slowly turning. A scientific / physics register (family S · scientific/molecular). Deterministic (electron
// angle = t·speed + phase).
//
// AN ELECTRON COUNT IS A FACT ABOUT AN ELEMENT. Every atom this register drew had seven nucleus spheres (in two
// colours alternating by index, so "four of one, three of the other") and seven electrons on shells of 2 / 3 / 2
// — whatever the title said. A film titled "Carbon" showed an atom with the wrong number of electrons in a
// shell arrangement no element has. The count is now the film's:
//   * `shells` — electrons per shell, inner to outer (carbon [2, 4], sodium [2, 8, 1]). Given, the shells are
//     drawn as concentric orbits in one tilted plane, inner to outer, each with exactly that many electrons.
//   * no `shells` — the three-ring atom emblem, and NO electrons: a soft light runs along each ring instead, so
//     the atom still lives and moves, but there is nothing on it to count. (The standalone demo is this mode.)
//   * the nucleus is one glowing core in both modes. Its particle count would be a second fact (protons AND
//     neutrons) that no prop carries, so it is not drawn as particles at all.
// 1-7 shells, each a whole number of electrons from 1 to 32; anything else throws.
//
// THE NUCLEUS'S AMBER IS THE ONE COLOUR THAT MEANS SOMETHING HERE — a hot core, the light the rest of the atom
// is drawn around — so it is KEPT on any ground and only its exposure moves. A shell's colour is not an element
// colour: it is only "this ring is not that ring", so the ring palette is the FILM's (dnaPalette), the way every
// other categorical palette in this library is. The title, the tagline and the ground are ink and paper.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA, mix, shade, dnaPalette} from '../runtime/dna';
import {onLight, groundFrom} from '../runtime/light';
import {bottomInset} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#060812', CORE_D0 = '#ffd36e', CORE2_D0 = '#ff8f5e';
const POOL_D0 = '#101430';        // the lit core of the ground, a LIFT off this register's own night
const CORE_HOT_D0 = '#fff6d8';    // the nucleus's specular centre
const RING_COLS_D0 = ['#37e0ff', '#ff5b9e', '#8f7bff'];
const TITLE_D0 = '#eaf2ff', TAG_D0 = '#9fb2d0';
const RING_OP_D0 = 0.35;          // an orbit's stroke alpha (see the light-ground note in the body)
// the emblem's three rings (no-`shells` mode) — the atom symbol, not a shell structure. `ci` indexes the ring
// palette rather than naming a colour, because that palette is the film's and is resolved per render.
const EMBLEM = [{rx: 340, ry: 120, tilt: 0, ci: 0, sp: 1.0},
  {rx: 300, ry: 300, tilt: 60, ci: 1, sp: -0.8},
  {rx: 340, ry: 120, tilt: 120, ci: 2, sp: 1.3}];
export const MAX_ATOM_SHELLS = 7;
const SHELL_RMAX = 400, SHELL_FLAT = 0.46;   // outermost shell's radius and the orbit plane's foreshortening
export const MAX_SHELL_ELECTRONS = 32;

const checkShells = (shells: unknown): number[] | null => {
  if (shells == null) return null;
  if (!Array.isArray(shells) || shells.length < 1 || shells.length > MAX_ATOM_SHELLS) {
    throw new Error(`AtomOrbital: \`shells\` is electrons per shell, inner to outer — 1-${MAX_ATOM_SHELLS} entries ` +
      `(got ${Array.isArray(shells) ? shells.length : typeof shells}). Omit it to draw the atom emblem with no electrons.`);
  }
  shells.forEach((n, i) => {
    if (!(Number.isInteger(n) && n >= 1 && n <= MAX_SHELL_ELECTRONS)) {
      throw new Error(`AtomOrbital: shells[${i}] must be a whole number of electrons from 1 to ${MAX_SHELL_ELECTRONS}, ` +
        `got ${JSON.stringify(n)}.`);
    }
  });
  return shells as number[];
};

// a colour per shell, blended inner -> outer across the ring palette (never cycled by index)
const shellColour = (i: number, n: number, cols: string[]) => {
  if (n === 1) return cols[0];
  const u = (i / (n - 1)) * (cols.length - 1), k = Math.min(cols.length - 2, Math.floor(u));
  return mix(cols[k], cols[k + 1], u - k);
};

export const AtomOrbital: React.FC<{title?: string; tagline?: string; shells?: number[] | null}> = ({
  title: TITLE = 'Elemental', tagline: TAG = 'the core of everything', shells: SHELLS = null} = {}) => {
  const shells = checkShells(SHELLS);
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  // AN ATOM IS A DIAGRAM, NOT A LIGHT SOURCE — it is drawn on paper in every textbook there has ever been — so
  // it takes the film's ground and ink. Measured on a light film (`ink_contrast_qa.py`): 26.3% of this
  // register's ink under 3:1, and the mark render says all of it is the tagline. The title read only because
  // the literal `#101430` core painted a dark pool under it, i.e. because of the second defect and not despite
  // it. On a light ground every hue here is walked along its own black-to-white axis until it clears the floor
  // (`groundFrom`: exposure only, hue kept). Null DNA and the eight (dark) presets never reach this.
  const lit = dna && onLight(dna) ? groundFrom(dna, {bg: dna.bg}) : null;
  const litHue = (c: string) => (dna && lit ? groundFrom(dna, {bg: dna.bg, fg: c}).fg : c);
  // The ring palette is CATEGORICAL — it says "this shell is not that shell" and names no element — so it is
  // the film's own, derived from its two accents the way every other tone list in this library is. The
  // nucleus's amber is not categorical and stays amber.
  const RING = (dnaPalette(dna, RING_COLS_D0.length) ?? RING_COLS_D0).map(litHue);
  const CORE = litHue(CORE_D0), CORE2 = litHue(CORE2_D0);
  // A CORE'S LIT FACE CANNOT BE BRIGHTER THAN THE PAPER IT SITS ON: the nucleus ramps from a near-white
  // specular, which on a light film is a hole punched through the middle of the atom. On paper the hot centre
  // is a LIFT of the core's own colour.
  const CORE_HOT = lit ? mix(CORE, '#ffffff', 0.3) : CORE_HOT_D0;
  // The ground's core is a LIFT off this register's own night; on a light film the literal is a dark blob in
  // the middle of the page (the light probe rendered the whole atom in that murk rather than on the paper).
  const POOL = lit ? shade(BG, 0.06) : POOL_D0;
  const TITLE_INK = dna?.fg ?? TITLE_D0;
  const TAG_INK = dna ? mix(dna.fg, dna.dim, 0.4) : TAG_D0;
  // ALPHA IS A DARK-GROUND DEVICE. A third of a bright hue still glows on black; on paper it is a third of the
  // way from the page to the ink, which is no orbit at all. On a light ground the orbit is a drawn line, and
  // the lights that run along it (nested strokes at 0.22-0.8, painted OVER it) still read as a swelling,
  // because on paper alpha adds ink rather than taking it away.
  const RING_OP = lit ? 0.9 : RING_OP_D0;
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2 + 10;
  const build = easeOutBack(clamp01(seg(t, 0.06, 0.44)));
  const titleIn = easeOutCubic(seg(t, 0.52, 0.76));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));

  // one orbit = an ellipse (rx, ry) rotated by `tilt` degrees; `at(a)` is the point at parametric angle a
  type Orbit = {rx: number; ry: number; tilt: number; col: string; sp: number; n: number};
  const orbits: Orbit[] = shells
    ? shells.map((n, i) => {
      const R = SHELL_RMAX * (shells.length === 1 ? 0.62 : 0.34 + 0.66 * (i + 1) / shells.length);
      // one plane for every shell, turning slowly: concentric orbits read inner -> outer
      return {rx: R, ry: R * SHELL_FLAT, tilt: -22 + 26 * t, col: shellColour(i, shells.length, RING), sp: 1.35 - 0.6 * i / Math.max(1, shells.length - 1), n};
    })
    : EMBLEM.map((o) => ({rx: o.rx, ry: o.ry, tilt: o.tilt, sp: o.sp, col: RING[o.ci], n: 0}));
  const at = (o: Orbit, a: number): [number, number] => {
    const tl = (o.tilt * Math.PI) / 180;
    const x0 = Math.cos(a) * o.rx * build, y0 = Math.sin(a) * o.ry * build;
    return [x0 * Math.cos(tl) - y0 * Math.sin(tl), x0 * Math.sin(tl) + y0 * Math.cos(tl)];
  };
  const coreR = 46 * clamp01(build);
  // THE COUNT HAS TO STAY COUNTABLE. An electron may be no wider than the gap to the next shell (measured at
  // the ellipse's flat side, where shells crowd) nor than its share of its own orbit: at 7 shells / 32 electrons
  // fixed 13px electrons fused into one pink band, which is a count nobody can read.
  const shellGapY = shells && shells.length > 1 ? (SHELL_RMAX * 0.66 / shells.length) * SHELL_FLAT : Infinity;

  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 44%, ${POOL}, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <radialGradient id="atomCore" cx="0.38" cy="0.34" r="0.7">
            <stop offset="0" stopColor={CORE_HOT} /><stop offset="0.35" stopColor={CORE} /><stop offset="1" stopColor={CORE2} />
          </radialGradient>
        </defs>
        <g transform={`translate(${cx} ${cy})`}>
          {orbits.map((o, i) => (
            <ellipse key={'e' + i} rx={o.rx * build} ry={o.ry * build} fill="none" stroke={o.col} strokeWidth={2}
              opacity={RING_OP} transform={`rotate(${o.tilt})`} />
          ))}
          {/* nucleus — one core; its particle count is not something any prop states. The bloom is a dark-ground
              device: on paper it is a halo of the core's own colour that only fogs the edge it is meant to lift. */}
          <circle r={coreR} fill="url(#atomCore)" opacity={clamp01(build * 1.4)}
            style={{filter: lit ? 'none' : `drop-shadow(0 0 18px ${CORE})`}} />
          {shells
            // electrons — exactly shells[i] on orbit i, each RACING with a motion trail
            ? orbits.map((o, i) => [...Array(o.n)].map((_, k) => {
              const base = t * o.sp * 2.2 + (k / o.n) * Math.PI * 2 + i * 0.7;
              const [ex, ey] = at(o, base);
              const trail = [ex, ey].join(',') + ' ' + [0.14, 0.3, 0.5].map((d) => at(o, base - d / Math.max(1, o.n / 3)).map((v) => v.toFixed(1)).join(',')).join(' ');
              const er = Math.max(4, Math.min(13, (Math.PI * (o.rx + o.ry)) / (o.n * 3.2), shellGapY * 0.42));
              return <g key={`${i}-${k}`} opacity={clamp01(build)}>
                <polyline points={trail} fill="none" stroke={o.col} strokeWidth={Math.max(2, er * 0.38)} strokeLinecap="round" opacity={0.32} />
                <circle cx={ex} cy={ey} r={er} fill={o.col} style={{filter: lit ? 'none' : `drop-shadow(0 0 12px ${o.col})`}} />
              </g>;
            }))
            // no shells: a soft light slides along each ring — motion with nothing on it to count
            : orbits.map((o, i) => {
              const head = t * o.sp * 2.2 + i;
              const dir = Math.sign(o.sp) || 1;
              // nested continuous strokes, each shorter, brighter and wider than the last, centred on the same
              // point — a glow that fades at both ends. Drawn as short separate segments it came out beaded, a
              // row of dots along the ring, which is the one thing this mode must not look like.
              const LAYERS = [{len: 1.8, w: 3, o: 0.22}, {len: 1.2, w: 5, o: 0.34}, {len: 0.7, w: 7, o: 0.5}, {len: 0.3, w: 9, o: 0.8}];
              return <g key={'glow' + i} opacity={clamp01(build)}>
                {LAYERS.map((L, s) => {
                  const pts = [...Array(25)].map((_, q) => at(o, head - dir * (0.5 * (1.8 - L.len) + (q / 24) * L.len)))
                    .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
                  return <polyline key={s} points={pts} fill="none" stroke={o.col} strokeWidth={L.w}
                    strokeLinecap="round" strokeLinejoin="round" opacity={L.o}
                    style={s === LAYERS.length - 1 && !lit ? {filter: `drop-shadow(0 0 10px ${o.col})`} : undefined} />;
                })}
              </g>;
            })}
        </g>
      </svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', paddingBottom: bottomInset(W, H, 110)}}>
        {/* the title and its tagline are ON the ground, so they are the film's ink and its metadata; the
            separation shadow is the ground's own colour on paper, never a fixed black under near-black type */}
        <div style={{opacity: titleIn, transform: glide(`translateY(${(1 - titleIn) * 14}px)`, titleIn !== 1), color: TITLE_INK,
          font: '800 104px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em', textShadow: `0 8px 40px ${lit ? BG : '#000'}`}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 16, color: TAG_INK,
          font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.18em'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default AtomOrbital;
