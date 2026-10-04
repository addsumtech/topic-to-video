// SHOT · PourSync — a physical thing and the phone that mirrors it, live, on ONE clock. Left (top, in portrait):
// the thing the film drew, doing what it measures. Right (bottom): a phone showing the screen the film drew for
// it. Between them, the link, with each reading running along it from the thing to the phone. Both objects are
// handed the same `t` AND the same `shared` props (merged over their own), so whatever they draw from those — an
// amount, a reading, a state — is one value shown twice: the frame cannot show them disagreeing.
//
// THE ARGUMENT SHAPE: "what happens HERE shows up THERE, as it happens" — a scale and its app, a sensor and its
// dashboard, a meter and its readout. It was built for a coffee scale and its brewing app, which drew one pour
// from `shared`. The topic arrives entirely through props: the two objects, what they share, when the readings
// run (`linkWhen`), the link's label, the kicker and title. Every word is a prop; with none, nothing is written.
// Content stays in the content zone; the phone is the device layer's own (runtime/device), so it looks like every
// other phone in the library. Standalone it shows its own preview — the stages' wordless form on both sides.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitTextPx} from '../runtime/layout';
import {useDNA, mix} from '../runtime/dna';
import {ObjectSlot, useObjectEntry, type ObjectRef} from '../runtime/objectSlot';
import {Device, deviceGeometry, type DeviceGeom, type DeviceLook} from '../runtime/device';
import {pointAt} from '../runtime/alongPath';
import {leading} from '../runtime/cjkType';

export const DURATION = 420;
export const REQUIRED_IN_FILM = ['thing', 'screen'] as const;

const BG_D0 = '#eef0f3', FG_D0 = '#1b1f27', DIM_D0 = '#5d6573', ACC_D0 = '#2f5bd8';
const PREVIEW: ObjectRef = {id: 'DemoForm', props: {layers: 3}};   // the stages' wordless form, standalone only
type Pt = {x: number; y: number};
type Win = {from: number; to: number};

export const PourSync: React.FC<{
  thing?: ObjectRef;                      // the physical thing that measures — an object the film drew
  screen?: ObjectRef;                     // what the phone shows — an object the film drew for a screen
  shared?: Record<string, unknown>;       // merged into BOTH objects' props: the one value they both draw
  linkFrom?: Pt;                          // where the link leaves the thing, as fractions of its box
  linkWhen?: Win;                         // when readings run along the link, on the beat's clock — default most of the beat
  linkLabel?: string;                     // the link's name, set above it
  kicker?: string;                        // a small spaced label in the title band
  title?: string;                         // the claim, in the title band
  look?: DeviceLook;                      // the phone's look (absent: the device layer's own choice for the ground)
}> = ({thing, screen, shared = {}, linkFrom = {x: 1, y: 0.5}, linkWhen, linkLabel = '', kicker = '', title = '',
  look}) => {
  // the two ends are one claim: a film names both (validate.py requires them); standalone, both are the preview
  if ((thing === undefined) !== (screen === undefined)) {
    throw new Error('PourSync takes `thing` (the object that measures) and `screen` (what the phone shows) together — ' +
      'both {"id": …, "props": …} — or neither, for its own preview. Got ' +
      (thing === undefined ? '`screen` alone.' : '`thing` alone.'));
  }
  const THING = thing ?? PREVIEW, SCREEN = screen ?? PREVIEW;
  if (!(linkFrom && typeof linkFrom.x === 'number' && typeof linkFrom.y === 'number')) {
    throw new Error(`PourSync: \`linkFrom\` is {x, y}, fractions of the thing's box — got ${JSON.stringify(linkFrom)}`);
  }
  const win: Win = linkWhen ?? {from: 0.05, to: 0.95};
  if (!(win && typeof win.from === 'number' && typeof win.to === 'number' && win.from >= 0 && win.to <= 1 &&
        win.to > win.from)) {
    throw new Error(`PourSync: the link's window is {from, to} with 0 <= from < to <= 1 — got ${JSON.stringify(win)}`);
  }
  const thingRef: ObjectRef = {id: THING.id, props: {...(THING.props ?? {}), ...shared}};
  const screenRef: ObjectRef = {id: SCREEN.id, props: {...(SCREEN.props ?? {}), ...shared}};
  useObjectEntry(thingRef);
  useObjectEntry(screenRef);

  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const BG = dna?.bg ?? BG_D0, FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0;
  const U = Math.min(W, H);
  const portrait = W < H;
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H), zH = zBot - zTop;
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const enter = easeOutCubic(clamp01(seg(t, 0.0, 0.06)));

  // ── the phone: the device layer's own geometry, moved (and in portrait, scaled) to its part of the frame ──
  const lk: DeviceLook = look ?? 'flat';
  const g0: DeviceGeom = deviceGeometry('phone', lk, W, H, 'center', true);
  const k = portrait ? (zH * 0.5) / g0.body.h : 1;
  // in landscape the thing, the link and the phone are laid out as one group, centred on the frame
  const linkRoom = W * 0.17;
  const sideL = Math.min(zH, W * 0.9 - linkRoom - g0.body.w);
  const groupW = sideL + linkRoom + g0.body.w;
  const dx = (portrait ? W * 0.5 : (W - groupW) / 2 + sideL + linkRoom + g0.body.w / 2) - (g0.body.x + g0.body.w / 2) * k;
  const dy = portrait ? zBot - (g0.body.y + g0.body.h) * k : 0;
  const ph = {x: g0.body.x * k + dx, y: g0.body.y * k + dy, w: g0.body.w * k, h: g0.body.h * k};

  // ── the thing: as large as the room beside (above) the phone allows ──
  const gap = U * 0.06;
  const side = Math.min(W * 0.86, ph.y - gap - zTop);   // portrait: the room above the phone
  const box = portrait
    ? {x: (W - side) / 2, y: zTop, w: side, h: side}
    : {x: (W - groupW) / 2, y: zTop + (zH - sideL) / 2, w: sideL, h: sideL};

  // ── the link: from the thing's antenna to the phone's edge, a gentle arc, readings riding it ──
  const a: Pt = {x: box.x + box.w * linkFrom.x, y: box.y + box.h * linkFrom.y};
  const b: Pt = portrait ? {x: ph.x + ph.w / 2, y: ph.y - U * 0.01} : {x: ph.x - U * 0.012, y: ph.y + ph.h * 0.42};
  const mid: Pt = portrait ? {x: (a.x + b.x) / 2 + U * 0.08, y: (a.y + b.y) / 2}
    : {x: (a.x + b.x) / 2, y: Math.min(a.y, b.y) - U * 0.12};
  const linkD = `M${a.x.toFixed(1)} ${a.y.toFixed(1)} Q${mid.x.toFixed(1)} ${mid.y.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`;
  const flowing = t >= win.from && t <= win.to + 0.02;
  const linkIn = easeOutCubic(clamp01(seg(t, 0.02, 0.08)));
  const PULSES = 5;                                 // @decor: readings in flight; how many is texture, not a count
  const pulses = flowing ? Array.from({length: PULSES}, (_, k) => (t * 26 + k / PULSES) % 1) : [];
  const arrive = flowing ? 0.5 + 0.5 * Math.sin(t * 26 * Math.PI * 2) : 0;
  const labelAt = pointAt(linkD, 0.5);
  const labelPx = Math.round(U * 0.026);

  // ── the title band ──
  const kickerPx = Math.round(U * 0.022);
  const titlePx = title ? fitTextPx(title, W * (portrait ? 0.86 : 0.7), Math.round(U * 0.046), {usable: 1}) : 0;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: W * 0.06, top: TITLE_Y - kickerPx * 1.9, opacity: enter, color: ACC,
          font: `600 ${kickerPx}px/1.2 ${mono}`, letterSpacing: dna?.labelSpacing ?? '0.12em', whiteSpace: 'nowrap'}}>{kicker}</div>
      ) : null}
      {title ? (
        <div style={{position: 'absolute', left: W * 0.06, top: TITLE_Y - titlePx * 0.15, opacity: enter,
          font: `700 ${titlePx}px/${leading(title, 1.15)} ${disp}`, whiteSpace: 'nowrap'}}>{title}</div>
      ) : null}

      <div style={{position: 'absolute', inset: 0, opacity: enter}}>
        <ObjectSlot object={thingRef} box={box} t={t} />
      </div>

      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <path d={linkD} fill="none" stroke={mix(ACC, BG, 0.45)} strokeWidth={Math.max(2, U * 0.004)}
          strokeDasharray={`${U * 0.012} ${U * 0.01}`} strokeLinecap="round" opacity={linkIn} />
        {pulses.map((p, k) => {
          const q = pointAt(linkD, p);
          return <circle key={k} cx={q.x} cy={q.y} r={U * 0.008} fill={ACC} opacity={0.35 + 0.65 * p} />;
        })}
        {flowing ? (
          <circle cx={b.x} cy={b.y} r={U * (0.012 + 0.008 * arrive)} fill="none" stroke={ACC}
            strokeWidth={Math.max(1.5, U * 0.003)} opacity={0.3 + 0.5 * arrive} />
        ) : null}
      </svg>
      {linkLabel ? (
        <div style={{position: 'absolute', left: labelAt.x - W * 0.1, width: W * 0.2, top: labelAt.y - labelPx * 2.1,
          textAlign: 'center', color: DIM, opacity: linkIn, font: `600 ${labelPx}px/1.2 ${mono}`,
          letterSpacing: '0.08em', whiteSpace: 'nowrap'}}>{linkLabel}</div>
      ) : null}

      <div style={{position: 'absolute', inset: 0, opacity: enter}}>
        <div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transformOrigin: '0 0',
          transform: `translate(${dx}px, ${dy}px) scale(${k})`}}>
          <Device g={g0} dna={dna}>
            <ObjectSlot object={screenRef} box={{x: 0, y: 0, w: g0.screen.w, h: g0.screen.h}} t={t} />
          </Device>
        </div>
      </div>
    </AbsoluteFill>
  );
};
