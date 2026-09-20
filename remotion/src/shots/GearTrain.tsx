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

export const DURATION = 155; // ~5.2s
const BG_D0 = '#0b0c11';
const TONES0 = ['#5b8cff', '#f6a531', '#ff5b7f', '#22c197'];
const R = 156, TEETH = 12, SPACING = 278;
export const MAX_GEARS = 4;

// A GEAR IS AN OBJECT ON THE FILM'S GROUND, not a black disc with its own night. Its body, its dead-tooth
// grey and its two inner highlights were literals, so on a film grounded paper three black discs sat on white
// and the step names — white type that only reads BECAUSE the disc is black — were legible by accident rather
// than by design. `body`/`dead`/`ink` are passed in so the Gear stays a pure function of its props.
const Gear: React.FC<{cx: number; cy: number; angle: number; tone: string; live: boolean;
  body: string; dead: string; spoke: string; rim: string}> = ({cx, cy, angle, tone, live, body, dead, spoke, rim}) => (
  <g transform={`rotate(${angle} ${cx} ${cy})`}>
    {[...Array(TEETH)].map((_, j) => {
      const a = (j / TEETH) * Math.PI * 2;
      const tx = cx + Math.cos(a) * R, ty = cy + Math.sin(a) * R;
      return <rect key={j} x={tx - 20} y={ty - 20} width={40} height={40} rx={7}
        fill={live ? tone : dead} transform={`rotate(${(a * 180) / Math.PI} ${tx} ${ty})`} />;
    })}
    <circle cx={cx} cy={cy} r={R - 6} fill={body} stroke={live ? tone : dead} strokeWidth={4} />
    <circle cx={cx} cy={cy} r={R - 58} fill="none" stroke={rim} strokeWidth={10} />
    {[...Array(6)].map((_, s) => {
      const a = (s / 6) * Math.PI * 2;
      return <line key={s} x1={cx + Math.cos(a) * 40} y1={cy + Math.sin(a) * 40}
        x2={cx + Math.cos(a) * (R - 60)} y2={cy + Math.sin(a) * (R - 60)}
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
  const TITLE_INK = dna?.dim ?? '#aeb6ca';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  if (!Array.isArray(ITEMS) || ITEMS.length < 2 || ITEMS.length > MAX_GEARS) {
    throw new Error(
      `GearTrain needs 2-${MAX_GEARS} \`items\` (got ${Array.isArray(ITEMS) ? ITEMS.length : typeof ITEMS}). Each step ` +
      'is one gear driving the next and the LAST gear carries the payoff, so no step can be dropped; a fifth ' +
      'gear runs off the frame. Merge steps down to four, or use a sequence register for a longer chain.');
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
        return (
          <div key={i} style={{position: 'absolute', left: cx, top: cy, transform: 'translate(-50%,-50%)',
            textAlign: 'center', opacity: on, width: R * 1.7}}>
            <div style={{color: IDX_INK, font: '600 20px/1 var(--f-mono, "JetBrains Mono", monospace)',
              letterSpacing: '0.14em', marginBottom: 8}}>{String(i + 1).padStart(2, '0')}</div>
            <div style={{color: isLast && locked ? LOCKED_INK : STEP_INK,
              font: `800 40px/${leading(g, 1)} var(--f-body, Inter, system-ui, sans-serif)`, letterSpacing: '-0.01em'}}>{g}</div>
          </div>
        );
      })}

      {/* payoff badge off the last gear — only when the film named a payoff */}
      {String(LABEL ?? '').trim() ? (
      <div style={{position: 'absolute', left: x0 + (n - 1) * SPACING, top: cy - R - 96,
        transform: `translate(-50%,0) scale(${payoff})`, opacity: clamp01(payoff * 1.4),
        padding: '16px 34px', borderRadius: 999, background: 'linear-gradient(150deg, #22c197, #12916e)',
        color: '#04120d', font: '800 40px/1 var(--f-body, Inter, system-ui, sans-serif)',
        boxShadow: '0 18px 50px #22c19755', whiteSpace: 'nowrap'}}>{LABEL}</div>
      ) : null}
      </div>
    </AbsoluteFill>
  );
};
export default GearTrain;
