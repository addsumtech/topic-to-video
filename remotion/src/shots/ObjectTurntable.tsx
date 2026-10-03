// SHOT · ObjectTurntable — a thing the film drew, turned on a turntable so its shape in the round is seen: a
// platter under it whose rim marks the turn, its name under the platter. Family K (3D form).
//
// THE ARGUMENT SHAPE: "this is what it is like from every side." A front view hides depth; a turn shows it. An
// object that draws its own 3D (META.turns — its points projected with runtime/project3d, like objects/DemoForm)
// is handed the yaw and turns for real. Any other object is turned as a CARD with CSS perspective, at most ±60°,
// so its back never faces the camera; a `sweep` past 120° on such an object is refused, not quietly flattened.
// The rim's ticks move with the yaw either way, so the turn reads even when the object itself is nearly symmetric —
// and they travel the SAME WAY the object turns (rimTickDeg). A negative sweep turns it the other way, for an object
// whose motion has a sense of its own (a gear, a precessing spin).
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, separated} from '../runtime/dna';
import {ObjectSlot, useObjectEntry, fitAspect, type ObjectRef} from '../runtime/objectSlot';
import {DEMO_ID} from '../objects/DemoForm';

export const DURATION = 180;
export const REQUIRED_IN_FILM = ['object'] as const;
export const MAX_CARD_TURN = 60;         // degrees each way for an object that does not draw its own 3D
const BG_D0 = '#eef0f3', FG_D0 = '#1b1f27', DIM_D0 = '#5d6573', ACC_D0 = '#2f5bd8', LINE_D0 = '#c9ced6';
const DEMO_OBJECT: ObjectRef = {id: DEMO_ID};
const TICKS = 24;

/** Where rim mark `k` sits on the platter's ellipse, in degrees of its screen angle (0 = the right end, 90 = the
 *  near edge, since screen y runs DOWN), with the platter turned `yawDeg`. A rising yaw turns the object
 *  counter-clockwise seen from above — runtime/project3d's yawPoint takes +x toward the back, and so does the
 *  card's CSS rotateY — which on this ellipse is a FALLING angle. Adding the yaw would send the marks round
 *  the platter the opposite way to the object they mark. */
export const rimTickDeg = (k: number, yawDeg: number): number => (k * 360) / TICKS - yawDeg;

export const ObjectTurntable: React.FC<{
  object?: ObjectRef;   // the thing the film drew (runtime/objectSlot); a `turns` object is handed the yaw
  sweep?: number;       // degrees turned across the beat, 20-360 either way; negative turns it clockwise seen from above (a flat object: at most 120)
  title?: string;       // what it is, under the platter
  note?: string;        // one line under the title
  kicker?: string;      // a spaced label in the title band
}> = ({object: OBJECT = DEMO_OBJECT, sweep = 80, title = '', note = '', kicker = ''} = {}) => {
  if (!(typeof sweep === 'number' && Number.isFinite(sweep) && Math.abs(sweep) >= 20 && Math.abs(sweep) <= 360)) {
    throw new Error(`ObjectTurntable: \`sweep\` is the turn in degrees, 20-360 either way (negative turns it ` +
      `clockwise seen from above) — got ${JSON.stringify(sweep)}`);
  }
  const entry = useObjectEntry(OBJECT);
  const turns = entry.meta?.turns === true;
  if (!turns && Math.abs(sweep) > 2 * MAX_CARD_TURN) {
    throw new Error(`ObjectTurntable: "${OBJECT.id}" is drawn flat, so it can turn at most ${2 * MAX_CARD_TURN}° ` +
      `(±${MAX_CARD_TURN}°) before its back faces the camera — give a sweep of ${2 * MAX_CARD_TURN} or less, or ` +
      'draw it in 3D from `yaw` and set META.turns (see objects/DemoForm).');
  }
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);

  const capW = Math.min(W * 0.84, 1240);
  const tLead = leading(title, 1.12), nLead = leading(note, 1.4);
  const titlePx = title ? fitBlockPx(title, capW, U * 0.12, Math.round(U * 0.048), {usable: 1, leading: tLead}) : 0;
  const titleH = title ? wrapLines(title, titlePx, capW) * titlePx * tLead : 0;
  const notePx = Math.round(U * 0.022);
  const noteH = note ? wrapLines(note, notePx, capW) * notePx * nLead : 0;
  const noteGap = title && note ? Math.round(U * 0.012) : 0;
  const wordsH = titleH + noteGap + noteH;
  const gap = wordsH ? Math.round(U * 0.035) : 0;

  // the object's room: as large as the words and the platter leave; the platter is a flattened ellipse under it
  const room = Math.max(U * 0.2, Math.min(W * 0.52, (zBot - zTop - U * 0.02 - gap - wordsH) / 1.13));
  const drawn = fitAspect({x: 0, y: 0, w: room, h: room}, entry.meta?.aspect);
  const pw = room * 1.15, ph = room * 0.22;
  const groupH = drawn.h + ph * 0.5 + gap + wordsH;
  const top0 = zTop + Math.max(U * 0.01, (zBot - zTop - groupH) / 2);
  const box = {x: (W - drawn.w) / 2, y: top0, w: drawn.w, h: drawn.h};
  const pcx = W / 2, pcy = box.y + box.h;                       // the object stands on the platter's centre line
  const wordsTop = pcy + ph * 0.5 + gap;

  const yawDeg = -sweep / 2 + sweep * easeInOutCubic(clamp01(seg(t, 0.08, 0.92)));
  const objT = clamp01(seg(t, 0.04, 0.4));
  const platIn = easeOutCubic(clamp01(seg(t, 0.02, 0.16)));
  const titleIn = easeOutCubic(clamp01(seg(t, 0.42, 0.6)));
  const noteIn = easeOutCubic(clamp01(seg(t, 0.48, 0.66)));
  const card = turns ? undefined : {
    transform: `perspective(${Math.round(room * 3)}px) rotateY(${Math.max(-MAX_CARD_TURN, Math.min(MAX_CARD_TURN, yawDeg))}deg)`,
    transformOrigin: '50% 100%'};
  const sw = Math.max(1, Math.round(U * 0.0025));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center', opacity: platIn,
          font: `600 ${Math.round(U * 0.018)}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      ) : null}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity: platIn}}>
        {/* A `turns` object rotates one fixed shape, so how close its drawn content comes to the box's own
            floor (pcy) shifts with which corner the turn currently presents — objects/DemoForm, for one,
            settles flush only at its own default yaw and sits visibly higher at others. A platter whose fill
            barely lifts off the ground colour reads as an outline around empty air once the object sits that
            way, so the fill has to separate from the GROUND THAT IS ACTUALLY PAINTED, not from a fixed
            fraction picked by eye: a flat mix toward FG clears every shipped (dark-ground) Design DNA by a
            comfortable margin but, mixed from the SAME fraction, lands short of the null-DNA light
            fallback's own ground by a visible amount — the identical "floating outline" this fill exists to
            prevent, just on the one ground a fixed fraction was not checked against. `separated()` walks the
            mix until it measurably clears the step a region needs to read as a lit surface rather than the
            void, against whatever ground is actually loaded — the eight shipped presets, the null-DNA
            fallback, or a film-authored ground coerceDna never pins to one polarity. */}
        <ellipse cx={pcx} cy={pcy} rx={pw / 2} ry={ph / 2} fill={separated(dna?.bg ?? BG_D0, FG)} stroke={LINE} strokeWidth={sw} />
        {Array.from({length: TICKS}).map((_, k) => {   // @decor: the rim's marks carry the turn, not a reading
          const a = rimTickDeg(k, yawDeg) * (Math.PI / 180);
          const front = Math.sin(a) > 0;
          const x = pcx + Math.cos(a) * (pw / 2), y = pcy + Math.sin(a) * (ph / 2);
          const x2 = pcx + Math.cos(a) * (pw / 2) * 0.92, y2 = pcy + Math.sin(a) * (ph / 2) * 0.92;
          return <line key={k} x1={x} y1={y} x2={x2} y2={y2} stroke={k === 0 ? ACC : LINE}
            strokeWidth={k === 0 ? sw * 2.5 : sw} opacity={front ? 0.95 : 0.35} />;
        })}
      </svg>
      <ObjectSlot object={OBJECT} box={box} t={objT} yaw={turns ? (yawDeg * Math.PI) / 180 : undefined} style={card} />
      {title ? (
        <div style={{position: 'absolute', left: (W - capW) / 2, top: wordsTop, width: capW, textAlign: 'center',
          opacity: titleIn, font: `700 ${titlePx}px/${tLead} ${disp}`, color: FG, textWrap: 'balance'}}>{title}</div>
      ) : null}
      {note ? (
        <div style={{position: 'absolute', left: (W - capW) / 2, top: wordsTop + titleH + noteGap, width: capW,
          textAlign: 'center', opacity: noteIn, font: `400 ${notePx}px/${nLead} ${bodyF}`, color: DIM}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default ObjectTurntable;
