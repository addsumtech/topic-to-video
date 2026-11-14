// PROMO · Layers — what happens ON the page under the camera (references/promo-film.md §layers).
//
// Every layer is positioned in the capture's CSS px (the PageCam's children), timed in frames from the shot's start,
// and is a pure function of the frame. They are the verbs of a product film:
//   pop    an element of the page arrives in its own slot (row-embed: the slot is blank until it lands)
//   lift   an element rises off the page toward the camera, a sheen crosses it and its accent under-glow blooms, it settles back
//   focus  a RACK FOCUS: the page falls out of focus and dims, the one element stays sharp (a lens, not a stencil)
//   ring   an accent outline draws itself round an element
//   type   text is typed into a field (the field's placeholder is covered by the field's own fill)
//   cursor a pointer travels and clicks
//   callout a leader line draws from a point on an element to a label (kicker + line), the label rising into place
//   note   a callout without a leader
import React from 'react';
import {staticFile, useCurrentFrame} from 'remotion';
import {span, track, useLook, SANS, MONO, alpha, isDarkHex, isCJK, type Box, type Key} from './kit';
import {PageCamContext} from './PageCam';
import {RiseLine} from './Cards';

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

export type LiftSpec = {kind: 'lift'; box: Box; at: number; until: number; z?: number; scale?: number; radius?: number; sheen?: boolean; slot?: string};
export const Lift: React.FC<LiftSpec & Common> = ({box, at, until, z = 90, scale = 1.06, radius = 12, sheen = true, slot = '#f4f4f2', src, pageW, pageH}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const rise = span(frame, at, at + 12, 'overshoot');
  const back = span(frame, until, until + 16, 'swift');
  const lift = Math.max(0, rise * (1 - back));
  const bob = 0;   // no hover wobble: a sub-pixel sine on a sharp crop is a shimmer, not a float (see PageCam CREEP)
  const sw = span(frame, at + 8, at + 30, 'smooth');           // one sheen across the surface after it rises
  return (
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h}}>
      <div style={{position: 'absolute', inset: 0, borderRadius: radius, background: slot, opacity: Math.min(1, lift * 3)}} />
      {/* the accent light the element rises out of, blooming on the page under it */}
      <div style={{position: 'absolute', inset: -box.h * 0.4, borderRadius: radius * 4, opacity: lift * 0.9,
        background: `radial-gradient(closest-side, ${alpha(look.accent, 0.45)}, ${alpha(look.accent, 0)})`, filter: 'blur(6px)'}} />
      {/* 2D on purpose: the page is ONE flattened layer (PageCam raster), so height reads as rise + scale + shadow */}
      <div style={{position: 'absolute', inset: 0, transform: `translateY(${-(z * lift + bob) * 0.12}px) scale(${1 + (scale - 1) * lift})`}}>
        <Crop src={src} pageW={pageW} pageH={pageH} box={box} radius={radius} style={{left: 0, top: 0,
          boxShadow: `0 ${6 + 30 * lift}px ${10 + 70 * lift}px rgba(20,18,14,${0.08 + 0.22 * lift}), 0 0 0 ${1.5 * lift}px ${alpha(look.accent, 0.55 * lift)}`}} />
        {sheen && sw > 0 && sw < 1 ? (
          <div style={{position: 'absolute', inset: 0, borderRadius: radius, overflow: 'hidden', pointerEvents: 'none'}}>
            <div style={{position: 'absolute', top: '-50%', bottom: '-50%', width: '35%', left: `${-40 + sw * 140}%`, transform: 'rotate(18deg)',
              background: 'linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.65), rgba(255,255,255,0))'}} />
          </div>
        ) : null}
      </div>
    </div>
  );
};

export type FocusSpec = {kind: 'focus'; box: Box; at: number; until?: number; dim?: number; radius?: number; blur?: number};
/** A rack focus drawn in page space: a softened copy of the whole capture over it (the page goes out of focus), the
 *  element re-drawn sharp from the same texture on top, a soft light falling off round it. */
export const Focus: React.FC<FocusSpec & Common> = ({box, at, until = 1e9, dim = 0.28, radius = 14, blur = 5, src, pageW, pageH}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const on = span(frame, at, at + 16, 'smooth') * (1 - span(frame, until, until + 12, 'smooth'));
  if (on <= 0.001) return null;
  const dark = isDarkHex(look.ground);
  const cx = box.x + box.w / 2, cy = box.y + box.h / 2, r = Math.max(box.w, box.h) * 0.9;
  return (
    <>
      <Crop src={src} pageW={pageW} pageH={pageH} box={{x: 0, y: 0, w: pageW, h: pageH}} radius={0}
        style={{left: 0, top: 0, opacity: on, filter: `blur(${blur * on}px) saturate(${1 - 0.25 * on})`}} />
      <div style={{position: 'absolute', left: 0, top: 0, width: pageW, height: pageH, opacity: on, pointerEvents: 'none',
        background: `radial-gradient(${r}px ${r * 0.8}px at ${cx}px ${cy}px, rgba(0,0,0,0) 35%, ${dark ? `rgba(0,0,0,${dim + 0.2})` : `rgba(28,24,18,${dim})`} 100%)`}} />
      <Crop src={src} pageW={pageW} pageH={pageH} box={box} radius={radius} style={{left: box.x, top: box.y, opacity: on,
        boxShadow: `0 ${12 * on}px ${36 * on}px rgba(10,10,10,${0.18 * on})`}} />
    </>
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
  if (frame < path[0].f - 6) return null;
  const x = track(path, frame, 'x'), y = track(path, frame, 'y');
  const appear = span(frame, path[0].f - 6, path[0].f + 4, 'out');
  const press = clicks.reduce((m, c) => Math.max(m, 1 - Math.abs(frame - c - 2) / 4), 0);
  return (
    <>
      {/* no click ring: a ripple is a demo's tell — the click shows by what it CHANGES on the same frame */}
      <svg width={size} height={size * 1.4} viewBox="0 0 20 28" style={{position: 'absolute', left: x - 2, top: y - 2, opacity: appear,
        transform: `scale(${1 - 0.12 * Math.max(0, press)})`, transformOrigin: '2px 2px', filter: 'drop-shadow(0 2px 3px rgba(0,0,0,0.35))'}}>
        <path d="M2 2 L2 22 L7.5 17 L11 25.5 L14.5 24 L11 15.8 L18 15.8 Z" fill="#111" stroke="#fff" strokeWidth={1.6} strokeLinejoin="round" />
      </svg>
    </>
  );
};

export type CalloutSpec = {kind: 'callout'; x: number; y: number; lx: number; ly: number; at: number; until?: number; text: string; kicker?: string; size?: number; z?: number};
/** A leader line drawn from the point (x, y) on an element to a label at (lx, ly): a pulsing accent dot, the line,
 *  then the label — an optional mono kicker and one line rising through its mask (accent span filled). */
export const Callout: React.FC<CalloutSpec & {leader?: boolean}> = ({x, y, lx, ly, at, until = 1e9, text, kicker, size = 30, z = 40, leader = true}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const line = span(frame, at, at + 12, 'snappy');
  const out = span(frame, until, until + 10, 'exit');
  if (frame < at - 1 || out >= 1) return null;
  const dark = isDarkHex(look.ground);
  // KEEP THE LABEL ON THE FRAME. Its side and its clamp are decided ONCE, from where the camera puts it at the frame
  // the label lands (and where it will be a second later), so a label never jumps sides mid-shot. Width estimated
  // from its copy (Latin ~0.56 em, CJK 1 em, plus padding); rotation ignored, a margin covers it.
  const cam = React.useContext(PageCamContext);
  const em = (t: string) => Array.from(t).reduce((n, ch) => n + (isCJK(ch) ? 1 : 0.56), 0);
  const labelW = Math.max(em(text.replace(/\*/g, '')) * size, kicker ? em(kicker) * size * 0.42 * 1.25 : 0) + 34;
  const labelH = size * 1.25 + (kicker ? size * 0.42 + 4 : 0) + 20;
  let LX = lx, LY = ly, right = lx >= x;
  if (cam) {
    const land = at + 16, later = Math.min(until, at + 46);
    const fits = (lxx: number, side: boolean) => [land, later].every((f) => {
      const p = cam.toScreen(f, lxx, ly), z0 = cam.poseAt(f).zoom, m = 24;
      const x0 = side ? p.x : p.x - labelW * z0, x1 = side ? p.x + labelW * z0 : p.x;
      return x0 >= m && x1 <= cam.W - m;
    });
    if (!fits(LX, right)) {
      const mirror = x - (lx - x);
      if (fits(mirror, !right)) { LX = mirror; right = !right; }
      else {
        // neither side fits whole: slide the label in along its side until it does (or as far as it can)
        const z0 = cam.poseAt(land).zoom, p = cam.toScreen(land, LX, ly), m = 24;
        const over = right ? p.x + labelW * z0 - (cam.W - m) : m - (p.x - labelW * z0);
        if (over > 0) LX += (right ? -1 : 1) * over / z0;
      }
    }
    const z0 = cam.poseAt(land).zoom, p = cam.toScreen(land, LX, LY), m = 24;
    const top = p.y - (labelH * z0) / 2, bot = p.y + (labelH * z0) / 2;
    if (top < m) LY += (m - top) / z0;
    if (bot > cam.H - m) LY -= (bot - (cam.H - m)) / z0;
  }
  const pulse = 1 + 0.35 * Math.max(0, Math.sin((frame - at) / 6));
  const ex = x + (LX - x) * line, ey = y + (LY - y) * line;
  void z;
  return (
    <div style={{position: 'absolute', left: 0, top: 0, opacity: 1 - out}}>
      {leader ? <>
        <svg style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}} width={1} height={1}>
          <line x1={x} y1={y} x2={ex} y2={ey} stroke={look.accent} strokeWidth={2} strokeLinecap="round" />
        </svg>
        <div style={{position: 'absolute', left: x - 6, top: y - 6, width: 12, height: 12, borderRadius: '50%', background: look.accent,
          transform: `scale(${Math.min(1, line * 3) * pulse})`, boxShadow: `0 0 0 4px ${alpha(look.accent, 0.25)}`}} />
      </> : null}
      <div style={{position: 'absolute', left: LX, top: LY, transform: `translate(${right ? '0' : '-100%'}, -50%)`, padding: '10px 16px',
        borderRadius: 12, background: dark ? 'rgba(22,22,24,0.92)' : 'rgba(255,255,255,0.95)', boxShadow: '0 14px 40px rgba(10,10,10,0.20)',
        opacity: span(frame, at + (leader ? 8 : 0), at + (leader ? 16 : 8), 'out'), whiteSpace: 'nowrap'}}>
        {kicker ? <div style={{fontFamily: MONO, fontSize: size * 0.42, fontWeight: 700, letterSpacing: '0.16em', textTransform: 'uppercase',
          color: look.accentInk, marginBottom: 4}}>{kicker}</div> : null}
        <RiseLine text={text} px={size} start={at + (leader ? 9 : 2)} gap={2} weight={640} align="left" nowrap color={dark ? '#f4f3ef' : look.ink} />
      </div>
    </div>
  );
};
export type NoteSpec = {kind: 'note'; x: number; y: number; at: number; until?: number; text: string; size?: number; z?: number; kicker?: string};

export type DealSpec = {kind: 'deal'; boxes: Box[]; at: number; every?: number; dur?: number; from?: {x: number; y: number}; fill?: string; radius?: number};
/** DEAL: the page's cards start as one tight stack at `from` (default: the middle of their union) and fly out to their
 *  own slots one by one along a lifted arc, a few degrees of turn settling flat as they land; each slot is blank until
 *  its card arrives. A grid that ASSEMBLES reads as a set being built, where a wave of pops reads as a page loading. */
export const Deal: React.FC<DealSpec & Common> = ({boxes, at, every = 3, dur = 18, from, fill = '#ffffff', radius = 12, src, pageW, pageH}) => {
  const frame = useCurrentFrame();
  if (!boxes.length) return null;
  const ux0 = Math.min(...boxes.map((b) => b.x)), uy0 = Math.min(...boxes.map((b) => b.y));
  const ux1 = Math.max(...boxes.map((b) => b.x + b.w)), uy1 = Math.max(...boxes.map((b) => b.y + b.h));
  const F = from ?? {x: (ux0 + ux1) / 2, y: (uy0 + uy1) / 2};
  const stackIn = span(frame, at - 10, at, 'out');
  return (
    <>
      {boxes.map((b, i) => {
        const t0 = at + i * every;
        const p = span(frame, t0, t0 + dur, 'snappy');
        const landed = p >= 1;
        const sx = F.x - b.w / 2 + (i % 3 - 1) * 2, sy = F.y - b.h / 2 - i * 1.5;
        const x = sx + (b.x - sx) * p, y = sy + (b.y - sy) * p - Math.sin(Math.PI * p) * 60;
        const rot = (1 - p) * (((i * 37) % 11) - 5);
        const sc = 0.92 + 0.08 * p;
        const air = Math.sin(Math.PI * Math.min(1, p));
        // once landed, the card IS the page again: its shadow and hairline fade out (they drew boxes round flat rows
        // that have no edge of their own — the regex101 run)
        const settle = 1 - span(frame, t0 + dur, t0 + dur + 8, 'out');
        return (
          <React.Fragment key={i}>
            <div style={{position: 'absolute', left: b.x - 2, top: b.y - 2, width: b.w + 4, height: b.h + 4, background: fill, opacity: landed ? 0 : 1}} />
            <Crop src={src} pageW={pageW} pageH={pageH} box={b} radius={radius} style={{left: x, top: y, opacity: Math.min(1, stackIn * 1.5),
              transform: `rotate(${rot}deg) scale(${sc})`, zIndex: landed ? 0 : 100 - i,
              boxShadow: settle > 0.001 ? `0 ${4 + 24 * air}px ${8 + 50 * air}px rgba(20,18,14,${(0.10 + 0.20 * air) * settle}), 0 0 0 1px rgba(20,18,14,${0.06 * settle})` : 'none'}} />
          </React.Fragment>
        );
      })}
    </>
  );
};

export type WriteSpec = {kind: 'write'; box: Box; at: number; lineH?: number; every?: number; fill?: string};
/** WRITE: a block of the capture's own text appears line by line, each line uncovered left to right behind an accent
 *  caret — the document writing itself, in its own words and its own type (nothing is redrawn). */
export const Write: React.FC<WriteSpec> = ({box, at, lineH = 24, every = 5, fill = '#ffffff'}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const n = Math.max(1, Math.round(box.h / lineH));
  const lh = box.h / n;
  return (
    <>
      {Array.from({length: n}, (_, i) => {
        const a = at + i * every, w = span(frame, a, a + every * 1.6, 'smooth');
        if (w >= 1) return null;
        const y = box.y + i * lh;
        return (
          <React.Fragment key={i}>
            <div style={{position: 'absolute', left: box.x + box.w * w, top: y - 1, width: box.w * (1 - w) + 2, height: lh + 2, background: fill}} />
            {w > 0 ? <div style={{position: 'absolute', left: box.x + box.w * w - 1, top: y + lh * 0.15, width: 2.5, height: lh * 0.7,
              background: look.accent, borderRadius: 2, boxShadow: `0 0 6px ${look.accent}`}} /> : null}
          </React.Fragment>
        );
      })}
    </>
  );
};

export type CountSpec = {kind: 'count'; box: Box; to: number; from?: number; decimals?: number; prefix?: string; suffix?: string; at: number;
  dur?: number; fill?: string; size?: number; color?: string; weight?: number; align?: 'left' | 'center' | 'right'; font?: string};
/** COUNT: a number the product SHOWS, rolling from `from` to its real value (`to`, as the capture reads it) over ~1.4 s,
 *  decelerating onto it; the capture's own figure is covered by the field's fill while it rolls, and the rolled
 *  figure stays (set it in the product's face where you know it). Never a number the product does not show. */
export const Count: React.FC<CountSpec> = ({box, to, from = 0, decimals, prefix = '', suffix = '', at, dur = 42, fill = '#ffffff', size, color = '#1b1b1b',
  weight = 700, align = 'left', font}) => {
  const frame = useCurrentFrame();
  const p = span(frame, at, at + dur, 'expo');
  const dp = decimals ?? (String(to).split('.')[1]?.length ?? 0);
  const v = from + (to - from) * p;
  const txt = prefix + v.toLocaleString('en-US', {minimumFractionDigits: dp, maximumFractionDigits: dp}) + suffix;
  if (frame < at - 2) return null;
  return (
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h, background: fill, display: 'flex', alignItems: 'center',
      justifyContent: align === 'left' ? 'flex-start' : align === 'right' ? 'flex-end' : 'center', fontFamily: font ?? SANS, fontSize: size ?? box.h * 0.78,
      fontWeight: weight, color, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', overflow: 'hidden'}}>{txt}</div>
  );
};

export type MacroSpec = {kind: 'macro'; box: Box; src: string; scale?: number; at?: number; radius?: number};
/** Acts drawn OVER the page and its macros (annotation, not page content). */
export const OVERLAY_KINDS = ['callout', 'note', 'ring', 'cursor', 'count'];   // count rolls OVER a macro's figure
export type LayerSpec = PopSpec | LiftSpec | FocusSpec | RingSpec | TypeSpec | CursorSpec | CalloutSpec | NoteSpec | MacroSpec | DealSpec | WriteSpec | CountSpec;

/** Layers in the order given (later = on top). Pop/lift need the capture they crop from. */
export const Layers: React.FC<{layers: LayerSpec[]} & Common> = ({layers, ...c}) => (
  <>
    {layers.map((l, i) => {
      switch (l.kind) {
        case 'pop': return <Pop key={i} {...l} pageSrc={c.src} pageW={c.pageW} pageH={c.pageH} />;
        case 'lift': return <Lift key={i} {...l} {...c} />;
        case 'focus': return <Focus key={i} {...l} {...c} />;
        case 'ring': return <Ring key={i} {...l} />;
        case 'type': return <TypeIn key={i} {...l} />;
        case 'cursor': return <Cursor key={i} {...l} />;
        case 'callout': return <Callout key={i} {...l} />;
        case 'note': return <Callout key={i} kind="callout" x={l.x} y={l.y} lx={l.x} ly={l.y} at={l.at} until={l.until} text={l.text} size={l.size}
          z={l.z} kicker={l.kicker} leader={false} />;
        case 'deal': return <Deal key={i} {...l} {...c} />;
        case 'write': return <Write key={i} {...l} />;
        case 'count': return <Count key={i} {...l} />;
        case 'macro': return null;   // drawn by PageCam on its own layer (a 4x close-up)
        default: throw new Error(`promo layer: unknown kind ${(l as {kind: string}).kind}`);
      }
    })}
  </>
);
