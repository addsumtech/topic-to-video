// OPTICS PROBE — the frames tests/test_optics.py renders to hold runtime/optics.tsx and runtime/material.tsx to
// their two promises: every optic and every material is DETERMINISTIC (scripts/determinism_qa.py: twice, at
// concurrency 1 vs 3, and frame N cold vs warm), and each one actually DRAWS (a probe with the layer switched off
// must differ from one with it on — a layer that renders nothing would pass the determinism check trivially).
//
// One frame carries all of them, each on the thing it is anchored to: a lamp (bloom), a lit filament (halation), a
// hero card the light sweeps across (sweep), a field of stars (aberration), a seam's leak, and the four material
// grounds as a strip. `layers.<name>: false` switches one off — the harness's layer attribution uses exactly that.
//
// `stateLeak: true` is the harness's POSITIVE CONTROL: a module-level counter that every render of a frame bumps,
// drawn as a bar, so a frame depends on how many frames its tab drew before it — the class of defect the
// determinism harness exists for (a Canvas2D state leak measured 29/30 order-dependent frames in the research).
// The determinism test asserts the harness FAILS it, and names the layer.
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {OpticSource, LightSweep, Aberration, SeamLeak, normalizeOptic, type OpticSpec} from './optics';
import {LitGround, MATERIALS} from './material';

export const DURATION = 90;
export const SWEEP_START = 22;   // the band is ON the card over frames 30-36, where the leak burns too
export const SEAM_START = 30;
const SEAM = 12;

let LEAKED = 0;          // the positive control's state — deliberately module-level, deliberately wrong

type Layers = Partial<Record<'bloom' | 'halation' | 'sweep' | 'aberration' | 'leak' | 'material', boolean>>;

const on = (layers: Layers | undefined, k: keyof Layers) => layers?.[k] !== false;

export const OpticsProbe: React.FC<{layers?: Layers; stateLeak?: boolean; only?: string;
  /** one material, full frame, on `base` — what tests/test_optics.py measures the lit span from */
  materialFull?: {material: (typeof MATERIALS)[number]; base: string; travel?: [number, number]}}> = ({layers, stateLeak,
  only, materialFull}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const opt = (k: 'bloom' | 'halation' | 'sweep' | 'aberration' | 'leak'): OpticSpec | null =>
    on(layers, k) && (!only || only === k) ? normalizeOptic(k) : null;
  const u = Math.min(W, H) / 1080;
  const landscape = W >= H;
  // four cells on a dark stage (2x2 at 16:9, a column at 9:16) and the material strip along the bottom
  const cell = (i: number) => landscape
    ? {x: (i % 2) * W / 2, y: Math.floor(i / 2) * H * 0.36, w: W / 2, h: H * 0.36}
    : {x: 0, y: i * H * 0.18, w: W, h: H * 0.18};
  const stripY = landscape ? H * 0.72 : H * 0.72;
  const c0 = cell(0), c1 = cell(1), c2 = cell(2), c3 = cell(3);
  if (stateLeak) LEAKED += 1;
  if (materialFull) {
    return <AbsoluteFill><LitGround material={materialFull.material} base={materialFull.base} durF={DURATION}
      travel={materialFull.travel} /></AbsoluteFill>;
  }
  const stars = (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      {Array.from({length: 90}).map((_, i) => {
        const x = c3.x + c3.w * ((i * 0.6180339) % 1), y = c3.y + c3.h * ((i * 0.7548777) % 1);
        return <circle key={i} cx={x} cy={y} r={(1.5 + (i % 3)) * u} fill="#ffffff" />;
      })}
    </svg>
  );
  return (
    <AbsoluteFill style={{background: '#06070b'}}>
      {/* bloom: a lamp — with a keep-out where a label would sit beside it, so the MASKED path is held too */}
      <OpticSource optic={opt('bloom')} keepOut={[{x: c0.x + c0.w * 0.62, y: c0.y + c0.h / 2 - 30 * u, w: c0.w * 0.3,
        h: 60 * u}]}>
        <div style={{position: 'absolute', inset: 0}}>
          <div style={{position: 'absolute', left: c0.x + c0.w / 2 - 70 * u, top: c0.y + c0.h / 2 - 70 * u,
            width: 140 * u, height: 140 * u, borderRadius: '50%', background: '#fff3d6'}} />
        </div>
      </OpticSource>
      {/* halation: a lit filament (a highlight bar) */}
      <OpticSource optic={opt('halation')}>
        <div style={{position: 'absolute', inset: 0}}>
          <div style={{position: 'absolute', left: c1.x + c1.w * 0.2, top: c1.y + c1.h / 2 - 6 * u, width: c1.w * 0.6,
            height: 12 * u, borderRadius: 6 * u, background: '#ffffff'}} />
        </div>
      </OpticSource>
      {/* sweep: a hero card */}
      <div style={{position: 'absolute', left: c2.x + c2.w * 0.15, top: c2.y + c2.h * 0.15, width: c2.w * 0.7,
        height: c2.h * 0.7, borderRadius: 24 * u, background: 'linear-gradient(160deg, #2b3550, #151a28)',
        overflow: 'hidden'}}>
        <LightSweep optic={opt('sweep')} start={SWEEP_START} frames={24} radius={24 * u} />
      </div>
      {/* aberration: stars */}
      <Aberration optic={opt('aberration')}>{stars}</Aberration>
      {/* the four materials */}
      {on(layers, 'material') && (!only || only === 'material') ? MATERIALS.map((m, i) => (
        <div key={m} style={{position: 'absolute', left: (i * W) / 4, top: stripY, width: W / 4, height: H - stripY,
          overflow: 'hidden'}}>
          <div style={{position: 'absolute', left: -(i * W) / 4, top: -stripY, width: W, height: H}}>
            <LitGround material={m} base={['#e9e2d2', '#1d4f6e', '#9aa1a8', '#b8714e'][i]} durF={DURATION} />
          </div>
        </div>
      )) : null}
      {/* the leak over a seam at SEAM_START */}
      {opt('leak') && frame >= SEAM_START && frame < SEAM_START + SEAM
        ? <SeamLeak optic={opt('leak')!} f={frame - SEAM_START} seam={SEAM} light="top" /> : null}
      {stateLeak ? <div data-layer="stateLeak" style={{position: 'absolute', left: 0, top: 0, height: 40 * u,
        width: ((LEAKED * 37) % 97) * 10 * u, background: '#ff00ff'}} /> : null}
    </AbsoluteFill>
  );
};
