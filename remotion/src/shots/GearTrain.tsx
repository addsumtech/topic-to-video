// SHOT · Gear Train — interlocking gears mesh and turn in a CHAIN: the drive gear spins, each neighbour
// engages a beat later and turns the opposite way, hubs carry the step labels (kept upright), and the last
// gear LOCKS and lights the payoff. The "mechanism / one turn drives the next" register (family I). Deterministic.
//
// EVERY STEP GETS ITS GEAR. `items` used to be cut with `.slice(0, 4)`, so a five-step mechanism silently lost
// its last step — and the last gear is the one that locks and carries the payoff, so the frame credited the
// payoff to the wrong step. More than four now throws (the gears are fixed-size and a fifth leaves the frame),
// as does fewer than two: one gear drives nothing, and "one turn drives the next" is the whole claim. A film
// that sets `label: ''` gets no payoff badge rather than an empty green pill.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic, easeOutBack} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {useDNA, dnaPalette, mix, readableOn, separated, TONE_MIN_STEP} from '../runtime/dna';
import {useGlide} from '../runtime/glide';

export const DURATION = 155; // ~5.2s
export const FIDELITY = {
  subject: 'a train of equal spur gears with standard full-depth involute teeth, meshing',
  depicts: 'real',
  references: [
    {kind: 'drawing', source: 'references/object-refs/GearTrain/spur-gears.png',
      note: 'two external involute spur gears meshed on a carrier (Wikimedia Commons, CC BY-SA 4.0): each tip runs into the other gear\'s gap, the two root circles never touch'},
    {kind: 'spec', source: 'https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html',
      note: 'KHK Table 4.1, standard spur gear: centre distance a = (z1 + z2) m / 2; reference diameter d = z m; tip diameter d + 2m; root diameter d - 2.5m'},
    {kind: 'spec', source: 'https://khkgears.net/new/gear_knowledge/gear_technical_reference/involute_gear_profile.html',
      note: 'KHK 3.1: addendum 1.00 m, dedendum 1.25 m, whole depth 2.25 m; pressure angle usually 20°'},
  ],
  proportions: {
    centre_distance: {value: '(z1 + z2) m / 2 — for equal gears, z m', drawn: 'SPACING = TEETH × m',
      source: 'https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html'},
    tip_and_root_radius: {value: 'r ± (1.00 m, 1.25 m)', drawn: 'r + 1.00 m, r − 1.25 m',
      source: ['https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html',
        'https://khkgears.net/new/gear_knowledge/gear_technical_reference/involute_gear_profile.html']},
    pressure_angle: {value: '20°', drawn: '20° (straight flanks: the rack form of the involute)',
      source: 'https://khkgears.net/new/gear_knowledge/gear_technical_reference/involute_gear_profile.html'},
    mesh: {value: 'a tip enters the other gear\'s gap; the bodies never overlap', drawn: 'tip clearance 0.25 m',
      source: 'references/object-refs/GearTrain/spur-gears.png'},
  },
  parts: ['teeth', 'gear-body'],
  materials: ['machined gear blanks (the film\'s tones)', 'spokes and a rim on the web'],
};
const BG_D0 = '#0b0c11';
const TONES0 = ['#5b8cff', '#f6a531', '#ff5b7f', '#22c197'];
// THE TEETH MESH (FIDELITY above). The gears were 12 square tabs centred on r = 156 round a 150 px disc, with the
// centres 278 apart — so the two DISCS overlapped by 22 px and every tooth at the mesh vanished inside its
// neighbour's body: no tooth ever entered a gap. They are standard spur gears now: centre distance = z·m (equal
// gears), so the module is SPACING / TEETH; tips at r + m, roots at r − 1.25 m, flanks at the 20° pressure angle,
// and a tip meets the other gear's root with the standard 0.25 m clearance. `R` stays the OUTER (tip) radius the
// layout below was fitted to: 16 teeth put the tip at 156.4, where it already was.
const TEETH = 16, SPACING = 278;
const MODULE = SPACING / TEETH;                      // equal gears: a = z m
const RP = SPACING / 2;                              // reference (pitch) radius
const R = RP + MODULE;                               // tip radius (156.4)
const R_ROOT = RP - 1.25 * MODULE;                   // root radius (117.3)
const PRESSURE = (20 * Math.PI) / 180;
export const MAX_GEARS = 4;

/** One gear's toothed outline about (0, 0): straight flanks at the pressure angle (the rack form of the involute),
 *  the tooth πm/2 thick on the reference circle. */
const TOOTH_PATH = (() => {
  // the flank widens toward the root down to the BASE circle (r·cos α), where the involute begins; below it the
  // flank runs radially into the root, so the space between two teeth stays open at the root as a real gear's does
  const RB = RP * Math.cos(PRESSURE);
  const halfAbove = (r: number) => ((Math.PI * MODULE) / 4 + (RP - r) * Math.tan(PRESSURE)) / r;
  const half = (r: number) => (r >= RB ? halfAbove(r) : halfAbove(RB));
  const pts: string[] = [];
  for (let j = 0; j < TEETH; j++) {
    const c = (j / TEETH) * Math.PI * 2;
    const pitch = (Math.PI * 2) / TEETH;
    const P = (r: number, a: number) => `${(Math.cos(a) * r).toFixed(2)} ${(Math.sin(a) * r).toFixed(2)}`;
    pts.push(`${j ? 'L' : 'M'}${P(R_ROOT, c - pitch / 2)}`);
    pts.push(`L${P(R_ROOT, c - half(R_ROOT))}`);
    pts.push(`L${P(RB, c - half(RB))}`);
    pts.push(`L${P(RP, c - half(RP))}`);
    pts.push(`L${P(R, c - half(R))}`);
    pts.push(`A${R.toFixed(2)} ${R.toFixed(2)} 0 0 1 ${P(R, c + half(R))}`);
    pts.push(`L${P(RP, c + half(RP))}`);
    pts.push(`L${P(RB, c + half(RB))}`);
    pts.push(`L${P(R_ROOT, c + half(R_ROOT))}`);
    pts.push(`A${R_ROOT.toFixed(2)} ${R_ROOT.toFixed(2)} 0 0 1 ${P(R_ROOT, c + pitch / 2)}`);
  }
  return pts.join(' ') + ' Z';
})();

// A GEAR IS AN OBJECT ON THE FILM'S GROUND, not a black disc with its own night. Its body, its dead-tooth
// grey and its two inner highlights were literals, so on a film grounded paper three black discs sat on white
// and the step names — white type that only reads BECAUSE the disc is black — were legible by accident rather
// than by design. `body`/`dead`/`ink` are passed in so the Gear stays a pure function of its props.
const Gear: React.FC<{cx: number; cy: number; angle: number; tone: string; live: boolean;
  body: string; dead: string; spoke: string; rim: string}> = ({cx, cy, angle, tone, live, body, dead, spoke, rim}) => (
  <g transform={`translate(${cx} ${cy}) rotate(${angle})`}>
    <path data-part="teeth" d={TOOTH_PATH} fill={live ? tone : dead} strokeLinejoin="round" />
    <circle data-part="gear-body" cx={0} cy={0} r={R_ROOT - 3} fill={body} stroke={live ? tone : dead} strokeWidth={4} />
    <circle cx={0} cy={0} r={R_ROOT - 38} fill="none" stroke={rim} strokeWidth={10} />
    {[...Array(6)].map((_, s) => {
      const a = (s / 6) * Math.PI * 2;
      return <line key={s} x1={Math.cos(a) * 40} y1={Math.sin(a) * 40}
        x2={Math.cos(a) * (R_ROOT - 40)} y2={Math.sin(a) * (R_ROOT - 40)}
        stroke={spoke} strokeWidth={12} strokeLinecap="round" />;
    })}
  </g>
);

export const GearTrain: React.FC<{items?: string[]; label?: string; title?: string}> = ({
  items: ITEMS = ['Trigger', 'Process', 'Deliver'], label: LABEL = 'Automatic', title: TITLE = 'How it runs'} = {}) => {
  const dna = useDNA();
  const TONES = dnaPalette(dna, 4) ?? TONES0;   // derive the palette from the film's DNA (null DNA = the original)
  const GROUND = dna?.bg ?? BG_D0;
  // The gear body is a real step off the film's ground — toward whichever pole that ground has room for, so
  // it is a raised disc on a dark film and a machined plate on a light one, never a region that is not there.
  // Its label is then measured against the body it is actually drawn on, rather than assumed white.
  const BODY = dna ? separated(GROUND, readableOn(GROUND, '#ffffff', '#05070c'), TONE_MIN_STEP * 0.6) : '#12141f';
  const DEAD = dna ? separated(GROUND, readableOn(GROUND, '#ffffff', '#05070c'), TONE_MIN_STEP * 1.4) : '#2a2f45';
  const SPOKE = dna ? `${readableOn(BODY, '#ffffff', '#05070c')}12` : '#ffffff12';
  const RIM = dna ? `${readableOn(BODY, '#ffffff', '#05070c')}10` : '#ffffff10';
  // The last gear's label BRIGHTENS when the train locks, and that cue is a difference between two inks —
  // originally #e7ebf7 and a pure #fff. Reading both from the same picker would have collapsed them into one
  // colour on every themed film and quietly deleted the lock. The locked ink is the pure pole; the resting
  // one is that pole stepped back toward the body by the same small amount the original pair differed by.
  const POLE_INK = dna ? readableOn(BODY, '#ffffff', '#05070c') : '#fff';
  const STEP_INK = dna ? mix(POLE_INK, BODY, 0.10) : '#e7ebf7';
  const LOCKED_INK = POLE_INK;
  const IDX_INK = dna?.dim ?? '#7f879c';
  // THE PAYOFF PILL IS THE FILM'S ACCENT, not a fixed green: on a passbook film (red accent, paper ground) it was the one
  // green thing on the frame. No DNA keeps the original green.
  const PILL = dna?.accent ?? '#22c197';
  const PILL_DEEP = dna ? mix(PILL, '#000000', 0.22) : '#12916e';
  const PILL_INK = dna ? readableOn(PILL, '#ffffff', '#05070c') : '#04120d';
  const PILL_GLOW = dna ? mix(PILL, GROUND, 0.55) : '#22c19755';
  const TITLE_INK = dna?.dim ?? '#aeb6ca';
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  if (!Array.isArray(ITEMS) || ITEMS.length < 2 || ITEMS.length > MAX_GEARS) {
    throw new Error(
      `GearTrain needs 2-${MAX_GEARS} \`items\` (got ${Array.isArray(ITEMS) ? ITEMS.length : typeof ITEMS}). Each step ` +
      'is one gear driving the next and the LAST gear carries the payoff, so no step can be dropped; a fifth gear runs off the frame. Merge steps down to four, or use a sequence register for a longer chain.');
  }
  const gears = ITEMS;
  const n = gears.length;
  const totalW = (n - 1) * SPACING;
  const x0 = W / 2 - totalW / 2;
  const cy = H / 2 + 20;
  const revs = 2.2;
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const locked = t > 0.82;
  const payoff = easeOutBack(clamp01(seg(t, 0.82, 0.98)));
  // THE TRAIN FITS THE FRAME. The geometry is fixed pixels, so four gears (1186px across) ran off both sides of
  // a 1080-wide portrait frame and the payoff badge, pushed against the edge, wrapped one glyph per line.
  // Now that four is the stated maximum, four must be seen: the train scales down about its own centre when
  // it would not fit, and is untouched (k = 1) wherever it already did — every 16:9 frame.
  const fit = Math.min(1, (W * 0.92) / (totalW + 2 * (R + 24)));
  // THE STEP INDEX IS COPY — 30 px as RENDERED (it was a 20 px literal). The whole train is scaled by `fit` on a
  // narrow frame, so its CSS size is raised by the same factor to land on the floor after the scale.
  const idxPx = Math.ceil(Math.round(Math.min(W, H) * 0.0278) / fit);
  return (
    // ...and the ground's lift followed nothing: only its outer stop read the DNA, so a paper film got a navy
    // pool behind the train with its own paper around it.
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg
        ?? `radial-gradient(120% 100% at 50% 40%, #14172a, ${BG_D0} 70%)`}}>
      <div style={{position: 'absolute', top: 88, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: TITLE_INK, font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em',
        textTransform: 'uppercase'}}>{TITLE}</div>

      <div style={{position: 'absolute', inset: 0, transform: fit < 1 ? `scale(${fit})` : undefined,
        transformOrigin: `${W / 2}px ${cy}px`}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        {gears.map((_, i) => {
          const cx = x0 + i * SPACING;
          const dir = i % 2 === 0 ? 1 : -1;
          const engaged = easeInOutCubic(clamp01(seg(t, 0.12 + i * 0.12, 0.86)));
          const base = (i % 2) * (180 / TEETH); // half-tooth offset so neighbours interleave
          const angle = base + dir * revs * 360 * engaged;
          const live = t > 0.12 + i * 0.12 - 0.02;
          return <Gear key={i} cx={cx} cy={cy} angle={angle} tone={TONES[i % TONES.length]} live={live}
            body={BODY} dead={DEAD} spoke={SPOKE} rim={RIM} />;
        })}
      </svg>

      {/* upright hub labels (outside the rotating groups) + step index */}
      {gears.map((g, i) => {
        const cx = x0 + i * SPACING;
        const on = clamp01(seg(t, 0.16 + i * 0.12, 0.36 + i * 0.12));
        const isLast = i === n - 1;
        // A NAME STAYS ON ITS OWN GEAR. The box was R*1.7 (265 px) with centres 278 px apart, so two long names sat
        // 13 px apart and read as one line (the CJK fixture's 「规划执行步骤并调用工具」 ran into its neighbour).
        // The box is the hub's face now; the size is the largest of 40..30 px that fits in two lines, else 30 in three.
        const boxW = R * 1.3;
        const units = Array.from(String(g)).reduce((u, ch) => u + (/[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]/.test(ch) ? 1 : 0.56), 0);
        const stepPx = [40, 36, 33, 30].find((px) => Math.ceil((units * px) / boxW) <= 2) ?? 30;
        return (
          <div key={i} style={{position: 'absolute', left: cx, top: cy, transform: 'translate(-50%,-50%)',
            textAlign: 'center', opacity: on, width: boxW}}>
            <div style={{color: IDX_INK, font: `600 ${idxPx}px/1 var(--f-mono, "JetBrains Mono", monospace)`,
              letterSpacing: '0.14em', marginBottom: 8}}>{String(i + 1).padStart(2, '0')}</div>
            <div style={{color: isLast && locked ? LOCKED_INK : STEP_INK,
              font: `800 ${stepPx}px/${leading(g, 1)} var(--f-body, Inter, system-ui, sans-serif)`, letterSpacing: '-0.01em',
              textWrap: 'balance'}}>{g}</div>
          </div>
        );
      })}

      {/* payoff badge off the last gear — only when the film named a payoff */}
      {String(LABEL ?? '').trim() ? (
      <div style={{position: 'absolute', left: x0 + (n - 1) * SPACING, top: cy - R - 96,
        transform: glide(`translate(-50%,0) scale(${payoff})`, payoff !== 1), opacity: clamp01(payoff * 1.4),
        padding: '16px 34px', borderRadius: 999, background: `linear-gradient(150deg, ${PILL}, ${PILL_DEEP})`,
        color: PILL_INK, font: '800 40px/1 var(--f-body, Inter, system-ui, sans-serif)',
        boxShadow: `0 18px 50px ${PILL_GLOW}`, whiteSpace: 'nowrap'}}>{LABEL}</div>
      ) : null}
      </div>
    </AbsoluteFill>
  );
};
export default GearTrain;
