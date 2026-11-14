// PROMO · Stage — the product as OBJECTS in a world of the film's own (references/promo-film.md §staging).
//
// WHY. Side by side with the showcase films (the round-3 study, 2026-11-14), ours lost on the MATERIAL, not the
// polish: they film ONE component at a time — a card, a field, a result — large (60-80 % of the frame), lit, in a
// space with depth, while everything in it keeps moving; we filmed the whole web page edge to edge, its type 1-2 % of
// the frame and no world of the film's own. This file is that other way of filming:
//   ObjectShot  one hero component (plus optional ones behind it, out of focus) arriving in 3D and holding, in a world
//               (glow · paper · pastel), with a feature label beside it (index / kicker / a two-line claim)
//   WallShot    many components laid on a plane in perspective — a floor or a wall — the camera gliding across it
// A component is a promo_capture `--parts` capture (4x, its own corners and fill) or a promo_record recording CROPPED
// to it (a live object). Acts (count, ring, type, pop, callout) sit on it in its own CSS px.
//
// STILLNESS (the jitter lessons, runtime/glide + PageCam): every object is laid out ONCE at its size at rest and moved
// by ONE transform per frame whose scale is <= 1 (an arrival comes from further away, never from closer); a landed
// object HOLDS — what moves is its content. Grounds are still (a slow crawl of fine detail shimmers).
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {span, useLook, LookContext, typeScale, isDarkHex, alpha, contrast, isCJK, MONO, SANS, type Look, type Box} from './kit';
import {RiseLine} from './Cards';
import {Layers, type LayerSpec} from './Layers';
import {BASELINE_UNLOCK} from '../runtime/glide';

const U = BASELINE_UNLOCK;
const urlOf = (src: string) => (/^(https?:|data:|\/)/.test(src) ? src : staticFile(src));

export type World = 'glow' | 'paper' | 'pastel';
export const defaultWorld = (look: Look): World => (isDarkHex(look.paper) ? 'glow' : 'paper');

/** The film's look as it reads IN a world: on the glow world the ink is light and the accent is the light itself. */
export const worldLook = (look: Look, world: World): Look => {
  if (world === 'glow') {
    const base = '#100f0d';
    return {...look, paper: base, ground: base, groundEdge: '#1c1a17', ink: '#f3f0ea', muted: '#a39d92',
      accentInk: contrast(look.accent, base) >= 3 ? look.accent : '#f3f0ea'};
  }
  if (world === 'pastel') return {...look, paper: '#f6f5f9', ground: '#f6f5f9', ink: '#141318', muted: '#6b6874'};
  return look;
};

const hexToHsl = (hex: string): [number, number, number] => {
  const n = parseInt(hex.replace('#', '').slice(0, 6), 16);
  const r = ((n >> 16) & 255) / 255, g = ((n >> 8) & 255) / 255, b = (n & 255) / 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  if (mx === mn) return [0, 0, l];
  const d = mx - mn, s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
  const h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
};
const hsl = (h: number, s: number, l: number, a = 1) => `hsla(${((h % 360) + 360) % 360}, ${Math.round(s * 100)}%, ${Math.round(l * 100)}%, ${a})`;

/** THE WORLD: the film's own space behind the objects. glow — near-black, the accent as a pool of light and faint
 *  outlines receding (the showcase gallery film); pastel — soft light ground with three blurred blooms of the
 *  accent's neighbours; paper — the film's paper with a spotlight. All still. */
export const WorldGround: React.FC<{world: World; focus?: {x: number; y: number}; children?: React.ReactNode}> = ({world, focus = {x: 0.5, y: 0.5}, children}) => {
  const look = useLook();
  const {width: W, height: H} = useVideoConfig();
  const s = typeScale(W, H);
  const wl = worldLook(look, world);
  let ground: React.ReactNode;
  if (world === 'glow') {
    const rects = [[0.08, 0.16, 0.22, 0.2, -260], [0.7, 0.08, 0.26, 0.22, -420], [0.04, 0.62, 0.2, 0.24, -360], [0.76, 0.66, 0.2, 0.2, -300],
      [0.36, 0.04, 0.3, 0.14, -620], [0.58, 0.8, 0.26, 0.14, -540]];
    ground = (
      <AbsoluteFill style={{background: wl.paper, perspective: 1400 * s}}>
        <AbsoluteFill style={{background: `radial-gradient(42% 46% at ${focus.x * 100}% ${focus.y * 100}%, ${alpha(look.accent, 0.20)}, rgba(0,0,0,0) 72%)`}} />
        <AbsoluteFill style={{background: `radial-gradient(70% 30% at 50% 100%, ${alpha(look.accent, 0.08)}, rgba(0,0,0,0) 70%)`}} />
        <AbsoluteFill style={{background: `radial-gradient(28% 6% at ${focus.x * 100}% ${Math.min(96, focus.y * 100 + 32)}%, ${alpha(look.accent, 0.22)}, rgba(0,0,0,0) 75%)`}} />
        {rects.map(([x, y, w, h, z], i) => (
          <div key={i} style={{position: 'absolute', left: x * W, top: y * H, width: w * W, height: h * H, border: `${2 * s}px solid ${alpha(look.accent, 0.38)}`,
            borderRadius: 10 * s, transform: `translateZ(${z * s}px) rotateY(${i % 2 ? -18 : 14}deg) rotateX(${8 - i * 3}deg)`}} />
        ))}
        <AbsoluteFill style={{background: 'radial-gradient(120% 100% at 50% 50%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)'}} />
      </AbsoluteFill>
    );
  } else if (world === 'pastel') {
    const [h0, s0] = hexToHsl(look.accent);
    const blooms = [[0.18, 0.22, h0, 0.42], [0.82, 0.3, h0 + 45, 0.36], [0.62, 0.86, h0 - 50, 0.34]];
    ground = (
      <AbsoluteFill style={{background: wl.paper, overflow: 'hidden'}}>
        {blooms.map(([x, y, hh, a], i) => (
          <div key={i} style={{position: 'absolute', left: x * W - 0.32 * W, top: y * H - 0.32 * W, width: 0.64 * W, height: 0.64 * W, borderRadius: '50%',
            background: `radial-gradient(closest-side, ${hsl(hh, Math.max(0.55, s0), 0.78, a)}, ${hsl(hh, Math.max(0.55, s0), 0.85, 0)})`}} />
        ))}
        <AbsoluteFill style={{background: 'radial-gradient(90% 80% at 50% 50%, rgba(255,255,255,0.35), rgba(255,255,255,0) 70%)'}} />
      </AbsoluteFill>
    );
  } else {
    // PAPER, LIT: a spotlight pooled where the object sits, the paper falling off warm toward the edges, and a soft
    // shadow pool under the object — the showcase's lit paper. Flat even grey read as a slide (round-4 review).
    const dark = isDarkHex(wl.paper);
    ground = (
      <AbsoluteFill style={{background: wl.paper}}>
        <AbsoluteFill style={{background: `radial-gradient(150% 120% at ${focus.x * 100}% ${focus.y * 100}%, rgba(0,0,0,0) 30%, ${dark ? 'rgba(0,0,0,0.5)' : 'rgba(58,44,24,0.20)'} 100%)`}} />
        <AbsoluteFill style={{background: `radial-gradient(34% 40% at ${focus.x * 100}% ${focus.y * 100 - 4}%, ${dark ? 'rgba(255,255,255,0.09)' : 'rgba(255,253,248,0.95)'}, rgba(255,255,255,0) 75%)`}} />
        <AbsoluteFill style={{background: `radial-gradient(26% 7% at ${focus.x * 100}% ${Math.min(96, focus.y * 100 + 31)}%, ${dark ? 'rgba(0,0,0,0.5)' : 'rgba(40,30,15,0.16)'}, rgba(0,0,0,0) 75%)`}} />
      </AbsoluteFill>
    );
  }
  return <LookContext.Provider value={wl}>{ground}{children}</LookContext.Provider>;
};

export type StageItem = {
  src?: string; w: number; h: number; radius?: number; bg?: string;
  video?: string; videoStart?: number; vw?: number; vh?: number; crop?: Box;   // a recording, cropped to the component
  x?: number; y?: number; width?: number;          // centre (frame shares) and width on the frame (share of its width)
  rx?: number; ry?: number; rz?: number; z?: number; blur?: number;
  at?: number; from?: 'tilt' | 'rise' | 'fade' | 'none'; acts?: LayerSpec[];
};

/** One object: laid out once at its size at rest, arriving (from further away: scale <= 1) and then HOLDING. */
export const StageObject: React.FC<{it: StageItem; world: World; perspective: number}> = ({it, world}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = typeScale(W, H);
  const width = (it.width ?? 0.6) * W;
  const S = width / it.w;                                   // screen px per CSS px of the component, at rest
  const h = it.h * S;
  const at = it.at ?? 0;
  const from = it.from ?? 'tilt';
  const rx0 = it.rx ?? 0, ry0 = it.ry ?? 0, rz0 = it.rz ?? 0;
  let rx = rx0, ry = ry0, dy = 0, dz = (it.z ?? 0) * s, op = 1;
  if (from === 'tilt') {
    const p = span(frame, at, at + 26, 'out');
    rx += (1 - p) * 14; ry -= (1 - p) * 20; dy = (1 - p) * 0.08 * H; dz += (1 - p) * -220 * s;
    op = span(frame, at, at + 8, 'out');
  } else if (from === 'rise') {
    const p = span(frame, at, at + 20, 'snappy');
    dy = (1 - p) * 0.05 * H; dz += (1 - p) * -80 * s; op = span(frame, at, at + 8, 'out');
  } else if (from === 'fade') {
    op = span(frame, at, at + 12, 'out');
  }
  if (op <= 0) return null;
  const R = (it.radius ?? 12) * S;
  const glow = world === 'glow';
  const sheen = span(frame, at + 18, at + 46, 'smooth');
  const shadow = glow
    ? `0 0 0 ${1.2 * s}px ${alpha(look.accent, 0.55)}, 0 0 ${46 * s}px ${alpha(look.accent, 0.30)}, 0 ${34 * s}px ${90 * s}px rgba(0,0,0,0.6)`
    : `0 0 0 ${1 * s}px rgba(20,18,14,0.07), 0 ${40 * s}px ${90 * s}px rgba(20,18,14,0.26), 0 ${8 * s}px ${20 * s}px rgba(20,18,14,0.10)`;
  return (
    <div style={{position: 'absolute', left: (it.x ?? 0.5) * W - width / 2, top: (it.y ?? 0.52) * H - h / 2, width, height: h, opacity: op,
      transform: `translate3d(0, ${dy}px, ${dz}px) rotateX(${rx}deg) rotateY(${ry}deg) rotateZ(${rz0}deg) ${U}`, willChange: 'transform',
      filter: it.blur ? `blur(${it.blur * s}px)` : undefined}}>
      <div style={{position: 'absolute', inset: 0, borderRadius: R, overflow: 'hidden', background: it.bg ?? (glow ? '#1b1a17' : '#ffffff'), boxShadow: shadow}}>
        {it.video && it.crop ? (
          <div style={{position: 'absolute', left: -it.crop.x * S, top: -it.crop.y * S, width: (it.vw ?? it.w) * S, height: (it.vh ?? it.h) * S}}>
            <Sequence from={at - (it.videoStart ?? 0)} layout="none">
              <OffthreadVideo src={urlOf(it.video)} muted style={{width: '100%', height: '100%'}} />
            </Sequence>
          </div>
        ) : it.src ? <Img src={urlOf(it.src)} style={{position: 'absolute', left: 0, top: 0, width, height: h}} /> : null}
        {it.acts?.length ? (
          <div style={{position: 'absolute', left: 0, top: 0, width: it.w, height: it.h, transform: `scale(${S})`, transformOrigin: '0 0'}}>
            <Layers layers={it.acts} src={it.src ?? ''} pageW={it.w} pageH={it.h} />
          </div>
        ) : null}
        {sheen > 0 && sheen < 1 ? (
          <div style={{position: 'absolute', inset: 0, background: `linear-gradient(105deg, rgba(255,255,255,0) ${-30 + sheen * 130}%, rgba(255,255,255,${glow ? 0.10 : 0.22}) ${-15 + sheen * 130}%, rgba(255,255,255,0) ${0 + sheen * 130}%)`}} />
        ) : null}
      </div>
    </div>
  );
};

export type FeatureLabel = {index?: string; kicker?: string; text: string; sub?: string; side?: 'left' | 'right'; at?: number};

/** THE FEATURE LABEL (the showcase films' chapter device): `02 / CRT SHADER` in small mono, then a claim of one or
 *  two lines in display type at showcase size (~6 % of the frame height), its accent span inked; a muted sub line. */
export const Label: React.FC<{l: FeatureLabel}> = ({l}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = typeScale(W, H);
  const portrait = H > W;
  const at = l.at ?? 4;
  const lines = l.text.split('\n');
  const cjk = isCJK(l.text);
  const px = (portrait ? 64 : cjk ? 62 : 66) * s;
  const side = l.side ?? 'left';
  const kick = [l.index, l.kicker].filter(Boolean).join('  /  ');
  const box: React.CSSProperties = portrait
    ? {left: 0.08 * W, right: 0.08 * W, top: 0.1 * H}
    : {[side]: 0.07 * W, top: 0, bottom: 0, width: 0.38 * W, display: 'flex', flexDirection: 'column', justifyContent: 'center'};
  return (
    <div style={{position: 'absolute', ...box}}>
      {kick ? <div style={{fontFamily: MONO, fontSize: 21 * s, fontWeight: 700, letterSpacing: '0.18em', textTransform: 'uppercase', color: look.accentInk,
        marginBottom: 18 * s, opacity: span(frame, at, at + 8, 'out'), transform: U}}>{kick}</div> : null}
      {lines.map((ln, i) => (
        <div key={i} style={{marginBottom: 4 * s}}>
          <RiseLine text={ln} px={px} start={at + 3 + i * 6} gap={2} weight={720} align="left" nowrap lineHeight={1.08} />
        </div>
      ))}
      {l.sub ? <div style={{marginTop: 20 * s, fontFamily: SANS, fontSize: 26 * s, lineHeight: 1.4, color: look.muted, opacity: span(frame, at + 14, at + 24, 'out'), transform: U,
        maxWidth: 0.36 * W}}>{l.sub}</div> : null}
    </div>
  );
};

/** OBJECT: the product's component(s) as objects in the film's world, with a feature label beside them. With a label
 *  and one item, the item sits on the other side, turned a few degrees toward the label. */
export const ObjectShot: React.FC<{dur: number; world?: World; items: StageItem[]; label?: FeatureLabel}> = ({world: w0, items, label}) => {
  const look = useLook();
  const {width: W, height: H} = useVideoConfig();
  const s = typeScale(W, H);
  const world = w0 ?? defaultWorld(look);
  const portrait = H > W;
  const placed = items.map((it, i) => {
    if (i > 0 || !label) return it;
    const right = (label.side ?? 'left') === 'left';
    return portrait ? {x: 0.5, y: 0.62, width: 0.84, rx: 6, ...it}
      : {x: right ? 0.68 : 0.32, y: 0.52, width: 0.5, ry: right ? -9 : 9, rx: 5, ...it};
  });
  const hero: Partial<StageItem> = placed[0] ?? {};
  return (
    <WorldGround world={world} focus={{x: hero.x ?? 0.5, y: hero.y ?? 0.52}}>
      <AbsoluteFill style={{perspective: 2200 * s, perspectiveOrigin: '50% 45%'}}>
        {placed.map((it, i) => ({it, i})).sort((a, b) => (a.it.z ?? 0) - (b.it.z ?? 0)).map(({it, i}) => (
          <StageObject key={i} it={it} world={world} perspective={2200 * s} />
        ))}
      </AbsoluteFill>
      {label ? <Label l={label} /> : null}
    </WorldGround>
  );
};

export type WallTile = {src?: string; w: number; h: number; radius?: number; bg?: string; video?: string; videoStart?: number; vw?: number;
  vh?: number; crop?: Box; acts?: LayerSpec[]};

/** WALL: many components laid on a plane in perspective — a FLOOR (seen from above at an angle) or a WALL (receding to
 *  the right) — appearing in a quick cascade, the camera crossing the plane in one decisive move (~1.2-2 s) and holding. Far tiles fall
 *  into the world's dark (depth). A label sits over it, large, in a corner. */
export const WallShot: React.FC<{dur: number; world?: World; tiles: WallTile[]; cols?: number; tile?: number; gap?: number; plane?: 'floor' | 'wall';
  from?: {x: number; y: number}; to?: {x: number; y: number}; label?: {text: string; sub?: string; at?: number}}> = (
  {dur, world: w0, tiles, cols = 4, tile = 560, gap = 36, plane = 'floor', from = {x: 0, y: 0}, to = {x: 0, y: -260}, label}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const {width: W, height: H} = useVideoConfig();
  const s = typeScale(W, H);
  const world = w0 ?? defaultWorld(look);
  const glow = world === 'glow';
  // each tile keeps its own aspect (a settings panel is tall, a card is wide); a row is as tall as its tallest tile
  const th = (t: WallTile) => tile * (t.h / t.w);
  const rows = Math.ceil(tiles.length / cols);
  const rowH = Array.from({length: rows}, (_, r) => Math.max(...tiles.slice(r * cols, r * cols + cols).map(th)));
  const rowY = rowH.map((_, r) => rowH.slice(0, r).reduce((a, b) => a + b + gap, 0));
  const pw = cols * tile + (cols - 1) * gap, ph = rowH.reduce((a, b) => a + b, 0) + (rows - 1) * gap;
  // ONE decisive move after the cascade, then a hold. Measured: the same travel spread over the whole shot (a slow
  // crawl) shimmered at 9.2 % on the glide gate (fail over 3 %) — fine detail creeping a fraction of a pixel a frame.
  // and it LANDS as PageCam's camera does: velocity a sine bump peaking at 38 % and falling linearly to rest (a craft
  // ease's long tail crawled into the hold and shimmered: 9.2 % on the Squoosh wall), the move sized so its peak is
  // >= ~12 px a frame (under ~8 the whole landing is a creep)
  const travelPx = Math.hypot(to.x - from.x, to.y - from.y) * s * 0.8;
  // after the cascade has LANDED (its last tile settles at 12 + n·1.4): a move under tiles still rising is two motions
  // at once, and the glide gate read the overlap as steps (0.130 px)
  const t0 = Math.min(dur * 0.35, 16 + tiles.length * 1.4);
  const t1 = Math.min(dur - 12, t0 + Math.max(20, Math.min(60, Math.round((travelPx * 2) / 12))));
  const q = Math.log(0.5) / Math.log(0.38);
  const lin = Math.min(1, Math.max(0, (frame - t0) / Math.max(1, t1 - t0)));
  const p = (1 - Math.cos(Math.PI * Math.pow(lin, q))) / 2;
  const cx = from.x + (to.x - from.x) * p, cy = from.y + (to.y - from.y) * p;
  const tilt = plane === 'floor' ? 'rotateX(48deg) rotateZ(-8deg)' : 'rotateY(-30deg) rotateX(4deg)';
  return (
    <WorldGround world={world} focus={{x: 0.5, y: 0.45}}>
      <AbsoluteFill style={{perspective: 1700 * s, perspectiveOrigin: '50% 30%'}}>
        <div style={{position: 'absolute', left: W / 2 - (pw * s) / 2, top: H / 2 - (ph * s) / 2, width: pw * s, height: ph * s, transformStyle: 'preserve-3d',
          transform: `${tilt} translate3d(${-cx * s}px, ${-cy * s}px, 0)`, willChange: 'transform'}}>
          {tiles.map((t, i) => {
            const c = i % cols, r = Math.floor(i / cols);
            const a = span(frame, i * 1.4, 12 + i * 1.4, 'snappy');       // the first tile is in by frame 6: no empty cut-in
            // NO depth blur on a moving plane: a CSS blur under a moving 3D transform is recomputed at a new sub-pixel
            // phase every frame and its sharpness flickers (measured: the glide gate's shimmer 0.0 -> 8.7 % on the
            // Squoosh wall when far rows were blurred). Depth here is the fog the far edge falls into.
            const dof = 0;
            const tw = tile * s, tH = th(t) * s;
            const S = tw / t.w;
            return (
              <div key={i} style={{position: 'absolute', left: c * (tile + gap) * s, top: rowY[r] * s, width: tw, height: tH, borderRadius: (t.radius ?? 14) * s,
                overflow: 'hidden', background: t.bg ?? (glow ? '#1b1a17' : '#fff'), opacity: a, filter: dof > 0.3 ? `blur(${dof}px)` : undefined,
                transform: `translate3d(0, ${(1 - a) * 40 * s}px, ${(1 - a) * -60 * s}px)`,
                boxShadow: glow ? `0 0 0 ${1 * s}px ${alpha(look.accent, 0.18)}, 0 ${20 * s}px ${50 * s}px rgba(0,0,0,0.55)`
                  : `0 0 0 ${1 * s}px rgba(20,18,14,0.10), 0 ${26 * s}px ${60 * s}px rgba(30,24,14,0.28), 0 ${6 * s}px ${14 * s}px rgba(30,24,14,0.10)`}}>
                {t.video && t.crop ? (
                  <div style={{position: 'absolute', left: -t.crop.x * S, top: -t.crop.y * S, width: (t.vw ?? t.w) * S, height: (t.vh ?? t.h) * S}}>
                    <Sequence from={-(t.videoStart ?? 0)} layout="none"><OffthreadVideo src={urlOf(t.video)} muted style={{width: '100%', height: '100%'}} /></Sequence>
                  </div>
                ) : t.src ? <Img src={urlOf(t.src)} style={{position: 'absolute', left: 0, top: 0, width: tw, height: t.h * S}} /> : null}
                {t.acts?.length ? (
                  <div style={{position: 'absolute', left: 0, top: 0, width: t.w, height: t.h, transform: `scale(${S})`, transformOrigin: '0 0'}}>
                    <Layers layers={t.acts} src={t.src ?? ''} pageW={t.w} pageH={t.h} />
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      {/* depth: the far edge falls into the world */}
      {/* the label sits in the fog the far edge falls into — over the near tiles it fought them (white on white) */}
      <AbsoluteFill style={{background: `linear-gradient(180deg, ${worldLook(look, world).paper} 0%, ${alpha(worldLook(look, world).paper, 0.85)} 22%, ${alpha(worldLook(look, world).paper, 0)} 42%)`}} />
      {label ? (
        <div style={{position: 'absolute', left: 0.06 * W, top: 0.08 * H}}>
          <RiseLine text={label.text} px={58 * s} start={label.at ?? 18} gap={2} weight={720} align="left" nowrap />
          {label.sub ? <div style={{marginTop: 10 * s, fontFamily: SANS, fontSize: 26 * s, color: worldLook(look, world).muted,
            opacity: span(frame, (label.at ?? 18) + 10, (label.at ?? 18) + 20, 'out'), transform: U}}>{label.sub}</div> : null}
        </div>
      ) : null}
    </WorldGround>
  );
};


export type OutroObject = {src: string; w: number; h: number; radius?: number};

/** THE STAGED OUTRO: the film's own components gather in depth round the lockup — each arriving from further away to
 *  its place in a loose ring, tilted toward the centre, softer the deeper it sits — then step back and dim as the
 *  mark lands in a band of light (glow) or a spotlight (paper), the tagline and the CTA under it. The film's objects
 *  ARE its recall: the round-4 outro was a small mark on an empty ground. */
export const StageOutro: React.FC<{dur: number; world?: World; objects: OutroObject[]; lockup: React.ReactNode; stampAt?: number}> = (
  {world: w0, objects, lockup, stampAt = 46}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const {width: W, height: H} = useVideoConfig();
  const s = typeScale(W, H);
  const world = w0 ?? defaultWorld(look);
  const glow = world === 'glow';
  const slots = [[0.15, 0.27, -220, 22, 6], [0.85, 0.29, -280, -22, 6], [0.12, 0.74, -140, 18, -5], [0.88, 0.72, -200, -18, -5],
    [0.33, 0.1, -460, 10, 12], [0.67, 0.91, -420, -10, -10]];
  const back = span(frame, stampAt - 6, stampAt + 12, 'smooth');
  const band = span(frame, stampAt - 2, stampAt + 20, 'out');
  // On a dark ground the gathered parts step back by dimming into it. On a light one dimming = fading to WHITE (the
  // regex101 run: pale ghosts round a thin mark), so there they keep their ink, recede by depth only, carry a contact
  // shadow plus a hairline edge to sit ON the paper, and take no blur (no CSS blur on a moving plane: it shimmers).
  return (
    <WorldGround world={world} focus={{x: 0.5, y: 0.5}}>
      <AbsoluteFill style={{perspective: 1900 * s, perspectiveOrigin: '50% 50%', opacity: 1 - (glow ? 0.45 : 0.12) * back}}>
        {objects.slice(0, slots.length).map((o, i) => {
          const [x, y, z, ry, rx] = slots[i];
          const a = span(frame, i * 3, i * 3 + 26, 'out');
          const width = (glow ? 0.21 : 0.23) * W, h = width * (o.h / o.w);
          return (
            <div key={i} style={{position: 'absolute', left: x * W - width / 2, top: y * H - h / 2, width, height: h, borderRadius: (o.radius ?? 10) * (width / o.w),
              overflow: 'hidden', opacity: a, willChange: 'transform',
              transform: `translate3d(0, 0, ${(z - (1 - a) * 500 - back * 160) * s}px) rotateY(${ry}deg) rotateX(${rx}deg) ${U}`,
              filter: glow ? `blur(${(Math.abs(z) / 220 + back * 2.5) * s}px)` : undefined,
              boxShadow: glow ? `0 0 0 ${1 * s}px ${alpha(look.accent, 0.35)}, 0 ${24 * s}px ${60 * s}px rgba(0,0,0,0.6)`
                : `0 0 0 ${1 * s}px rgba(30,24,14,0.10), 0 ${3 * s}px ${8 * s}px rgba(30,24,14,0.12), 0 ${30 * s}px ${70 * s}px rgba(30,24,14,0.24)`}}>
              <Img src={urlOf(o.src)} style={{width, height: h}} />
            </div>
          );
        })}
      </AbsoluteFill>
      {/* the light the mark lands in */}
      <AbsoluteFill style={{opacity: band, background: glow
        ? `radial-gradient(46% 13% at 50% 50%, ${alpha(look.accent, 0.42)}, ${alpha(look.accent, 0.10)} 55%, rgba(0,0,0,0) 80%)`
        : `radial-gradient(40% 30% at 50% 50%, rgba(255,253,248,0.96), rgba(255,253,248,0.55) 55%, rgba(255,253,248,0) 80%)`}} />
      {glow ? <div style={{position: 'absolute', left: W * (0.5 - 0.3 * band), width: W * 0.6 * band, top: H * 0.5 - 1 * s, height: 2 * s,
        background: `linear-gradient(90deg, rgba(0,0,0,0), ${alpha(look.accent, 0.9)}, rgba(0,0,0,0))`, filter: `blur(${1 * s}px)`, opacity: 0.5 * band}} /> : null}
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>{lockup}</AbsoluteFill>
    </WorldGround>
  );
};
