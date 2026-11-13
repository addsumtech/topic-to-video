// PROMO · Layers — what happens ON the page under the camera (references/promo-film.md §layers).
//
// Every layer is positioned in the capture's CSS px (the PageCam's children), timed in frames from the shot's start,
// and is a pure function of the frame. They are the verbs of a product film:
//   pop    an element of the page arrives in its own slot (row-embed: the slot is blank until it lands)
//   lift   an element rises off the page toward the camera, a beam laps its edge, and it settles back
//   focus  everything but one element dims (the light locks on it)
//   ring   an accent outline draws itself round an element
//   type   text is typed into a field (the field's placeholder is covered by the field's own fill)
//   cursor a pointer travels and clicks
//   note   a short serif annotation floats beside an element, a marker sweeping under its accent word
import React from 'react';
import {staticFile, useCurrentFrame} from 'remotion';
import {span, track, useLook, SERIF, SANS, parseWords, type Box, type Key} from './kit';

const urlOf = (src: string) => (/^(https?:|data:|\/)/.test(src) ? src : staticFile(src));

/** A crop of the capture, drawn from the same 2x texture (so it is as sharp as the page under the camera). */
export const Crop: React.FC<{src: string; pageW: number; pageH: number; box: Box; radius?: number; style?: React.CSSProperties}> = (
  {src, pageW, pageH, box, radius = 10, style}) => (
  <div style={{position: 'absolute', width: box.w, height: box.h, borderRadius: radius, overflow: 'hidden',
    backgroundImage: `url(${urlOf(src)})`, backgroundSize: `${pageW}px ${pageH}px`, backgroundPosition: `${-box.x}px ${-box.y}px`,
    backgroundRepeat: 'no-repeat', ...style}} />
);

type Common = {src: string; pageW: number; pageH: number};

// `src`/`srcBox` take the arriving element from ANOTHER capture (a state change: the send button lit once text is in)
export type PopSpec = {kind: 'pop'; box: Box; at: number; fill?: string; radius?: number; dur?: number; from?: 'up' | 'left' | 'scale';
  src?: string; srcBox?: Box; srcW?: number; srcH?: number; cover?: boolean};
export const Pop: React.FC<PopSpec & {pageSrc: string; pageW: number; pageH: number}> = (
  {box, at, fill = '#ffffff', radius = 10, dur = 14, from = 'up', src, srcBox, srcW, srcH, cover = true, pageSrc, pageW, pageH}) => {
  const other = Boolean(src && src !== pageSrc);
  const cs = other ? src as string : pageSrc, cw = other ? (srcW ?? pageW) : pageW, ch = other ? (srcH ?? pageH) : pageH;
  const sb = srcBox ?? box;
  const frame = useCurrentFrame();
  const p = span(frame, at, at + dur, 'overshoot');
  const o = span(frame, at, at + dur * 0.6, 'out');
  const tx = from === 'left' ? (1 - p) * -40 : 0, ty = from === 'up' ? (1 - p) * 26 : 0, sc = from === 'scale' ? 0.86 + 0.14 * p : 0.97 + 0.03 * p;
  return (
    <>
      {/* the slot is blank until its element lands */}
      {cover && !other ? <div style={{position: 'absolute', left: box.x - 2, top: box.y - 2, width: box.w + 4, height: box.h + 4, background: fill, opacity: 1 - o}} /> : null}
      <Crop src={cs} pageW={cw} pageH={ch} box={{...sb, w: box.w, h: box.h}} radius={radius} style={{left: box.x, top: box.y, opacity: o,
        transform: `translate(${tx}px, ${ty}px) scale(${sc})`, boxShadow: `0 ${10 * (1 - o)}px ${30 * (1 - o)}px rgba(20,18,14,${0.18 * (1 - o)})`}} />
    </>
  );
};

export type LiftSpec = {kind: 'lift'; box: Box; at: number; until: number; z?: number; scale?: number; radius?: number; beam?: boolean; slot?: string};
export const Lift: React.FC<LiftSpec & Common> = ({box, at, until, z = 90, scale = 1.06, radius = 12, beam = true, slot = '#f4f4f2', src, pageW, pageH}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const rise = span(frame, at, at + 12, 'overshoot');
  const back = span(frame, until, until + 16, 'swift');
  const lift = Math.max(0, rise * (1 - back));
  const bob = Math.sin(((frame - at) / 42) * Math.PI * 2) * 3 * lift;
  // two laps of a short bright arc round the edge while it hovers
  const lap = span(frame, at + 10, until - 6, 'smooth') * 2;
  const beamOn = beam ? Math.min(1, lift * 1.5) * (lap > 0 && lap < 2 ? 1 : 0) : 0;
  return (
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h, transformStyle: 'preserve-3d'}}>
      <div style={{position: 'absolute', inset: 0, borderRadius: radius, background: slot, opacity: Math.min(1, lift * 3),
        boxShadow: `inset 0 0 0 ${1.5}px ${look.accent}${Math.round(0x66 * lift).toString(16).padStart(2, '0')}`}} />
      <div style={{position: 'absolute', inset: 0, transform: `translateZ(${z * lift + bob}px) scale(${1 + (scale - 1) * lift})`,
        transformStyle: 'preserve-3d'}}>
        <Crop src={src} pageW={pageW} pageH={pageH} box={box} radius={radius} style={{left: 0, top: 0,
          boxShadow: `0 ${6 + 30 * lift}px ${10 + 70 * lift}px rgba(20,18,14,${0.08 + 0.22 * lift}), 0 0 0 1px rgba(255,255,255,${0.8 * lift})`}} />
        {beamOn > 0 ? (
          <svg width={box.w + 8} height={box.h + 8} style={{position: 'absolute', left: -4, top: -4, overflow: 'visible', opacity: beamOn}}>
            <rect x={2} y={2} width={box.w + 4} height={box.h + 4} rx={radius + 2} fill="none" pathLength={1} stroke={look.accent}
              strokeWidth={4} strokeLinecap="round" strokeDasharray="0.16 0.84" strokeDashoffset={-lap}
              style={{filter: `drop-shadow(0 0 6px ${look.accent})`}} />
            <rect x={2} y={2} width={box.w + 4} height={box.h + 4} rx={radius + 2} fill="none" pathLength={1} stroke="#ffffff"
              strokeWidth={1.6} strokeLinecap="round" strokeDasharray="0.10 0.90" strokeDashoffset={-lap - 0.03} />
          </svg>
        ) : null}
      </div>
    </div>
  );
};

export type FocusSpec = {kind: 'focus'; box: Box; at: number; until?: number; dim?: number; radius?: number};
export const Focus: React.FC<FocusSpec> = ({box, at, until = 1e9, dim = 0.42, radius = 14}) => {
  const frame = useCurrentFrame();
  const on = span(frame, at, at + 14, 'smooth') * (1 - span(frame, until, until + 12, 'smooth'));
  const pad = 10 + 30 * (1 - on);
  return (
    <div style={{position: 'absolute', left: box.x - pad, top: box.y - pad, width: box.w + 2 * pad, height: box.h + 2 * pad,
      borderRadius: radius + pad * 0.6, boxShadow: `0 0 0 4000px rgba(24,22,18,${dim * on})`, pointerEvents: 'none'}} />
  );
};

export type RingSpec = {kind: 'ring'; box: Box; at: number; until?: number; radius?: number; pad?: number};
export const Ring: React.FC<RingSpec> = ({box, at, until = 1e9, radius = 12, pad = 6}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const draw = span(frame, at, at + 16, 'snappy');
  const off = span(frame, until, until + 10, 'exit');
  if (draw <= 0 || off >= 1) return null;
  return (
    <svg width={box.w + 2 * pad + 8} height={box.h + 2 * pad + 8} style={{position: 'absolute', left: box.x - pad - 4, top: box.y - pad - 4, overflow: 'visible', opacity: 1 - off}}>
      <rect x={4} y={4} width={box.w + 2 * pad} height={box.h + 2 * pad} rx={radius + pad} fill="none" stroke={look.accent} strokeWidth={3}
        pathLength={1} strokeDasharray={`${draw} 1`} style={{filter: `drop-shadow(0 0 8px ${look.accent}88)`}} />
    </svg>
  );
};

export type TypeSpec = {kind: 'type'; box: Box; at: number; text: string; fill?: string; size?: number; color?: string; cpf?: number; weight?: number};
export const TypeIn: React.FC<TypeSpec> = ({box, at, text, fill = '#ffffff', size = 15, color = '#1b1b1b', cpf = 0.5, weight = 450}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const n = Math.max(0, Math.min(text.length, Math.floor((frame - at) * cpf)));
  const typing = frame >= at && n < text.length;
  const caret = typing || Math.floor(frame / 15) % 2 === 0;
  return (
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h, background: frame >= at - 4 ? fill : 'transparent',
      display: 'flex', alignItems: 'center', fontFamily: SANS, fontSize: size, fontWeight: weight, color, whiteSpace: 'nowrap', overflow: 'hidden'}}>
      {frame >= at - 4 ? <span>{text.slice(0, n)}</span> : null}
      {frame >= at - 4 && caret ? <span style={{display: 'inline-block', width: 2, height: size * 1.25, marginLeft: 1, background: look.accent}} /> : null}
    </div>
  );
};

export type CursorSpec = {kind: 'cursor'; path: (Key & {f: number; x: number; y: number})[]; clicks?: number[]; size?: number};
export const Cursor: React.FC<CursorSpec> = ({path, clicks = [], size = 22}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  if (frame < path[0].f - 6) return null;
  const x = track(path, frame, 'x'), y = track(path, frame, 'y');
  const appear = span(frame, path[0].f - 6, path[0].f + 4, 'out');
  const press = clicks.reduce((m, c) => Math.max(m, 1 - Math.abs(frame - c - 2) / 4), 0);
  return (
    <>
      {clicks.map((c) => {
        const r = span(frame, c, c + 16, 'out');
        return frame >= c && r < 1 ? <div key={c} style={{position: 'absolute', left: x - 22 * r - 4, top: y - 22 * r - 4, width: 8 + 44 * r, height: 8 + 44 * r,
          borderRadius: '50%', border: `2px solid ${look.accent}`, opacity: 1 - r}} /> : null;
      })}
      <svg width={size} height={size * 1.4} viewBox="0 0 20 28" style={{position: 'absolute', left: x - 2, top: y - 2, opacity: appear,
        transform: `scale(${1 - 0.12 * Math.max(0, press)})`, transformOrigin: '2px 2px', filter: 'drop-shadow(0 2px 3px rgba(0,0,0,0.35))'}}>
        <path d="M2 2 L2 22 L7.5 17 L11 25.5 L14.5 24 L11 15.8 L18 15.8 Z" fill="#111" stroke="#fff" strokeWidth={1.6} strokeLinejoin="round" />
      </svg>
    </>
  );
};

export type NoteSpec = {kind: 'note'; x: number; y: number; at: number; until?: number; text: string; size?: number; z?: number; align?: 'left' | 'right'};
export const Note: React.FC<NoteSpec> = ({x, y, at, until = 1e9, text, size = 34, z = 70, align = 'left'}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const inn = span(frame, at, at + 14, 'snappy');
  const out = span(frame, until, until + 10, 'exit');
  if (inn <= 0 || out >= 1) return null;
  const words = parseWords(text);
  const hl = span(frame, at + 10, at + 26, 'snappy');
  return (
    <div style={{position: 'absolute', left: x, top: y, transform: `translateZ(${z + Math.sin((frame - at) / 7) * 2}px) translate(${align === 'right' ? '-100%' : '0'}, ${(1 - inn) * 18}px)`,
      opacity: inn * (1 - out), filter: `blur(${(1 - inn) * 4}px)`, fontFamily: SERIF, fontSize: size, fontWeight: 560, lineHeight: 1.15,
      color: look.ink, whiteSpace: 'nowrap', padding: '10px 18px', borderRadius: 12, background: 'rgba(255,255,255,0.94)',
      boxShadow: '0 14px 40px rgba(20,18,14,0.18)'}}>
      {words.map((w, i) => (
        <span key={i} style={{position: 'relative', marginRight: '0.26em', fontStyle: w.accent ? 'italic' : 'normal', color: w.accent ? look.accentInk : undefined}}>
          {w.accent ? <span style={{position: 'absolute', left: -3, bottom: 2, height: '0.42em', width: `calc(${hl} * (100% + 6px))`, background: `${look.accent}55`, borderRadius: 3, zIndex: -1}} /> : null}
          {w.text}
        </span>
      ))}
    </div>
  );
};

export type LayerSpec = PopSpec | LiftSpec | FocusSpec | RingSpec | TypeSpec | CursorSpec | NoteSpec;

/** Layers in the order given (later = on top). Pop/lift need the capture they crop from. */
export const Layers: React.FC<{layers: LayerSpec[]} & Common> = ({layers, ...c}) => (
  <>
    {layers.map((l, i) => {
      switch (l.kind) {
        case 'pop': return <Pop key={i} {...l} pageSrc={c.src} pageW={c.pageW} pageH={c.pageH} />;
        case 'lift': return <Lift key={i} {...l} {...c} />;
        case 'focus': return <Focus key={i} {...l} />;
        case 'ring': return <Ring key={i} {...l} />;
        case 'type': return <TypeIn key={i} {...l} />;
        case 'cursor': return <Cursor key={i} {...l} />;
        case 'note': return <Note key={i} {...l} />;
        default: throw new Error(`promo layer: unknown kind ${(l as {kind: string}).kind}`);
      }
    })}
  </>
);
