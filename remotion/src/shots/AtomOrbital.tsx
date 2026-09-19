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

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {bottomInset} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#060812', CORE = '#ffd36e', CORE2 = '#ff8f5e';
const RING_COLS = ['#37e0ff', '#ff5b9e', '#8f7bff'];
// the emblem's three rings (no-`shells` mode) — the atom symbol, not a shell structure
const EMBLEM = [{rx: 340, ry: 120, tilt: 0, col: RING_COLS[0], sp: 1.0},
  {rx: 300, ry: 300, tilt: 60, col: RING_COLS[1], sp: -0.8},
  {rx: 340, ry: 120, tilt: 120, col: RING_COLS[2], sp: 1.3}];
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
const shellColour = (i: number, n: number) => {
  if (n === 1) return RING_COLS[0];
  const u = (i / (n - 1)) * (RING_COLS.length - 1), k = Math.min(RING_COLS.length - 2, Math.floor(u));
  return mix(RING_COLS[k], RING_COLS[k + 1], u - k);
};

export const AtomOrbital: React.FC<{title?: string; tagline?: string; shells?: number[] | null}> = ({
  title: TITLE = 'Elemental', tagline: TAG = 'the core of everything', shells: SHELLS = null} = {}) => {
  const shells = checkShells(SHELLS);
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
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
      return {rx: R, ry: R * SHELL_FLAT, tilt: -22 + 26 * t, col: shellColour(i, shells.length), sp: 1.35 - 0.6 * i / Math.max(1, shells.length - 1), n};
    })
    : EMBLEM.map((o) => ({...o, n: 0}));
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
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 44%, #101430, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <radialGradient id="atomCore" cx="0.38" cy="0.34" r="0.7">
            <stop offset="0" stopColor="#fff6d8" /><stop offset="0.35" stopColor={CORE} /><stop offset="1" stopColor={CORE2} />
          </radialGradient>
        </defs>
        <g transform={`translate(${cx} ${cy})`}>
          {orbits.map((o, i) => (
            <ellipse key={'e' + i} rx={o.rx * build} ry={o.ry * build} fill="none" stroke={o.col} strokeWidth={2}
              opacity={0.35} transform={`rotate(${o.tilt})`} />
          ))}
          {/* nucleus — one core; its particle count is not something any prop states */}
          <circle r={coreR} fill="url(#atomCore)" opacity={clamp01(build * 1.4)}
            style={{filter: `drop-shadow(0 0 18px ${CORE})`}} />
          {shells
            // electrons — exactly shells[i] on orbit i, each RACING with a motion trail
            ? orbits.map((o, i) => [...Array(o.n)].map((_, k) => {
              const base = t * o.sp * 2.2 + (k / o.n) * Math.PI * 2 + i * 0.7;
              const [ex, ey] = at(o, base);
              const trail = [ex, ey].join(',') + ' ' + [0.14, 0.3, 0.5].map((d) => at(o, base - d / Math.max(1, o.n / 3)).map((v) => v.toFixed(1)).join(',')).join(' ');
              const er = Math.max(4, Math.min(13, (Math.PI * (o.rx + o.ry)) / (o.n * 3.2), shellGapY * 0.42));
              return <g key={`${i}-${k}`} opacity={clamp01(build)}>
                <polyline points={trail} fill="none" stroke={o.col} strokeWidth={Math.max(2, er * 0.38)} strokeLinecap="round" opacity={0.32} />
                <circle cx={ex} cy={ey} r={er} fill={o.col} style={{filter: `drop-shadow(0 0 12px ${o.col})`}} />
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
                    style={s === LAYERS.length - 1 ? {filter: `drop-shadow(0 0 10px ${o.col})`} : undefined} />;
                })}
              </g>;
            })}
        </g>
      </svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', paddingBottom: bottomInset(W, H, 110)}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 14}px)`, color: '#eaf2ff',
          font: '800 104px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em', textShadow: '0 8px 40px #000'}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 16, color: '#9fb2d0',
          font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.18em'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default AtomOrbital;
