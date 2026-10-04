// SHOT · Data Orrery — an orbiting "solar-system of your work" register: a glowing core with perspective-tilted
// orbital rings, each carrying a labeled data node that ORBITS continuously (nodes pass behind the core for real
// depth). Distinct from RadialBurst (static bloom) + KnowledgeGraph (static graph) — this MOVES in orbit.
// Deterministic (each node's angle = base + t·speed).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {focusAt, focusFilter} from '../runtime/focus';
import {useGlide} from '../runtime/glide';

export const DURATION = 170; // ~5.7s
// THE LIGHT LAYER, WHICH WAS ONE LITERAL FOUR TIMES OVER. The hub's name, each node's core, the core's own
// centre and its rim were all near-white constants: they read because everything under them was ALSO a
// literal near-black, and on a light film the ground arrived and the ink did not. `ink_contrast_qa` reported
// 33.7% of the marks under 3:1, a median of 3.76:1 and a 0.30%-of-frame hole — and the hole was the word
// `hub`, the beat's own subject, painted white on warm paper. The core assembly is left alone deliberately:
// it carries its own dark disc under its own pale centre, so it reads on either ground (see the card).
const HUB_D0 = '#eaf0ff', NODE_D0 = '#f2f7ff';
// the hub's separation bloom. Under near-white type on night it is what lifts the word off the orbits;
// under dark type on paper a black bloom is a smudge, so it follows the film's own ground.
const HUB_BLOOM_D0 = '#000';
// THE ORBITS carry geometry only. Their labels used to live here too — four English words in a module
// const, which is not a prop default and so was invisible to the demo-default check: every film that omitted
// `items` printed Docs / Code / Tasks / Comms whatever it was about, and nothing anywhere said so. Moved
// into the signature the render is identical and the words are finally visible to the gate that hunts them.
const RING_GEOM = [
  {rx: 300, ry: 96, speed: 1.0, base: 0.2, c: '#4c8dff'},
  {rx: 470, ry: 150, speed: -0.7, base: 2.4, c: '#22d3c5'},
  {rx: 640, ry: 205, speed: 0.5, base: 4.1, c: '#b06cff'},
  {rx: 800, ry: 262, speed: -0.38, base: 1.0, c: '#ff8fc7'},
];

export const DataOrrery: React.FC<{items?: string[]; hub?: string}> = ({
  items = ['Docs', 'Code', 'Tasks', 'Comms'], hub: HUB = 'WorkBuddy'} = {}) => {
  const labels = (items ?? []).map((x) => String(x ?? '').trim()).filter(Boolean);
  if (!labels.length) {
    throw new Error(
      'DataOrrery needs at least one non-empty `items` entry — the things that orbit. With nothing to ' +
      'orbit it draws a glowing core and four empty chips, which composes and argues nothing.');
  }
  // ONE ORBIT PER ITEM. This used to draw all four orbits whatever it was given and fill them by
  // `labels[i % labels.length]`, so a film that named two things showed each of them twice and one that named
  // five lost the fifth without a word. The orbits are geometry; the count is the film's.
  if (labels.length > RING_GEOM.length) {
    throw new Error(
      `DataOrrery holds at most ${RING_GEOM.length} orbits and was given ${labels.length} items. Cut the list to ` +
      'the ones the beat is about, or cast a register that holds more — an extra item is never dropped silently.');
  }
  const t = useT();
  const glide = useGlide();
  const dna = useDNA();
  // FOUR ORBITS IN FOUR HUES, and the hues were the register's, not the film's. `dnaPalette` grows them from
  // the film's own two accents (null DNA -> null -> the originals), so a themed film's orbits belong to it,
  // and on a light film they are hues the film already exposed for its own paper. Their 0.28 stroke alpha is
  // NOT touched: it is as faint on the night as on the page, so it is this register's own restraint rather
  // than something the ground broke.
  const HUE = dnaPalette(dna, RING_GEOM.length);
  const RINGS = labels.map((label, i) => ({...RING_GEOM[i], c: HUE?.[i] ?? RING_GEOM[i].c, label}));
  const INK = dna?.fg ?? HUB_D0, NODE = dna?.fg ?? NODE_D0;
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  const U = Math.min(W, H);
  // the widest orbit is 800px of rx plus a ~90px label chip — scaled to the frame's half-width so the
  // outer ring's node label cannot ride off a narrow edge
  const rk = Math.min(1, (W / 2 - 110) / 800);
  const core = easeOutBack(seg(t, 0.02, 0.2));

  const nodeAt = (r: typeof RINGS[number]) => {
    const a = r.base + t * r.speed * Math.PI * 2;
    const sa = Math.sin(a);
    // 0 at the front of the orbit, 1 at the back — the distance the focus lens reads
    return {x: cx + Math.cos(a) * (r.rx * rk), y: cy + sa * (r.ry * rk), front: sa >= 0, depth: (1 - sa) / 2};
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 120% at 50% 46%, #0e1330 0%, #070a1c 60%, #04050f 100%)'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="og"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <radialGradient id="ocore"><stop offset="0" stopColor="#eaf0ff" /><stop offset="0.5" stopColor="#7aa2ff" /><stop offset="1" stopColor="#3a5cff" stopOpacity="0" /></radialGradient>
        </defs>

        {/* orbit rings (tilted ellipses) appear staggered */}
        {RINGS.map((r, i) => {
          const on = easeOutCubic(seg(t, 0.1 + i * 0.08, 0.34 + i * 0.08));
          return <ellipse key={`e${i}`} cx={cx} cy={cy} rx={r.rx * rk} ry={r.ry * rk} fill="none" stroke={r.c} strokeWidth={1.6} strokeOpacity={0.28 * on} />;
        })}

        {/* nodes BEHIND the core */}
        {RINGS.map((r, i) => {
          const n = nodeAt(r); if (n.front) return null;
          const on = easeOutBack(seg(t, 0.2 + i * 0.08, 0.4 + i * 0.08));
          return <circle key={`nb${i}`} cx={n.x} cy={n.y} r={12 * on} fill={r.c} opacity={0.45} filter="url(#og)" />;
        })}

        {/* core */}
        <g transform={`translate(${cx} ${cy}) scale(${core})`}>
          <circle r={140} fill="url(#ocore)" opacity={0.7} />
          <circle r={60} fill="#0c1330" stroke="#8fb0ff" strokeWidth={3} filter="url(#og)" />
          <circle r={34} fill="#cfe0ff" filter="url(#og)" />
        </g>

        {/* nodes IN FRONT of the core */}
        {RINGS.map((r, i) => {
          const n = nodeAt(r); if (!n.front) return null;
          const on = easeOutBack(seg(t, 0.2 + i * 0.08, 0.4 + i * 0.08));
          // the node's CORE is the marker; the 30px disc behind it at 0.18 is its glow and is left as it is,
          // since a halo that stops showing on paper costs a reader nothing. The core itself is the film's
          // ink: as a literal near-white it was a white disc on warm paper, and only the accent rim survived.
          return <g key={`nf${i}`}><circle cx={n.x} cy={n.y} r={30 * on} fill={r.c} opacity={0.18} />
            <circle cx={n.x} cy={n.y} r={13 * on} fill={NODE} filter="url(#og)" />
            <circle cx={n.x} cy={n.y} r={13 * on} fill="none" stroke={r.c} strokeWidth={3} /></g>;
        })}
      </svg>

      {/* NODE LABELS — they RECEDE behind the core, they do not vanish.
          `if (!n.front) return null` dropped a label the instant its node crossed behind, and the orbits are
          slow enough that most of them are behind most of the time: at the SETTLED frame — the one every
          visual gate and the shot-critic read — exactly one of the four was drawn. A register whose whole
          form is "a labelled node per orbit" was showing one label, and the CJK sweep reported it as having
          drawn almost nothing, which was true and not for the reason it assumed.
          Depth is what `runtime/focus` says: dimmer, softer, darker, smaller — the same recession the rest of
          the library uses, at its default curve, so a node on the far side reads as far rather than as gone. */}
      {RINGS.map((r, i) => {
        const n = nodeAt(r); const on = clamp01(seg(t, 0.3 + i * 0.08, 0.46 + i * 0.08));
        const f = focusAt(n.depth, U);
        // The node orbits for the whole beat, so its label is placed by a TRANSLATE (a label moved by left/top steps
        // a whole pixel at a time whatever unlocks it) and carries the baseline unlock on its WORDS, inside the
        // lens's blur — a blur keeps only the scale of the matrix above it (runtime/glide.ts).
        return <div key={i} style={{position: 'absolute', left: 0, top: 0,
          transform: `translate(${n.x}px, ${n.y + U * 0.024}px) translateX(-50%) scale(${f.scale})`,
          opacity: on * f.opacity, filter: focusFilter(f),
          zIndex: n.front ? 2 : 1,
          padding: `${Math.round(U * 0.004)}px ${Math.round(U * 0.013)}px`, borderRadius: 999,
          background: '#0b122acc', border: `1px solid ${r.c}66`, color: '#dbe5f5',
          font: `600 ${Math.round(U * 0.022)}px/1 var(--f-body, Inter, system-ui, sans-serif)`,
          whiteSpace: 'nowrap'}}><span style={{display: 'inline-block', transform: glide(undefined, true)}}>{r.label}</span></div>;
      })}
      <div style={{position: 'absolute', left: 0, right: 0, top: cy + 150, textAlign: 'center',
        opacity: clamp01(seg(t, 0.18, 0.34)), color: INK, font: `800 40px/1 var(--f-body, Inter, system-ui, sans-serif)`,
        letterSpacing: '-0.01em', textShadow: `0 2px 20px ${dna?.bg ?? HUB_BLOOM_D0}`}}>{HUB}</div>
    </AbsoluteFill>
  );
};
export default DataOrrery;
