// PROMO · PromoFilm — a product film written as a SHOT TABLE (references/promo-film.md).
//
// props: {look, shots: Shot[], cut?: 'carry' | 'flash' | 'hard'}. Shots play back to back. Every cut INTO a shot
// carries one move through it (Cards.carryStyle) unless the film or the shot names another cut. Chapter cards are
// numbered in order (01 / 04) unless a card says `index: false`. The outro recalls the film's own product shots,
// frozen at their settled frames, as the wall the lockup forms over. Timings inside a shot are frames from the
// shot's own start. Sound is not drawn here: scripts/promo_film.py pins the cues to the same table.
import React from 'react';
import {AbsoluteFill, Freeze, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {span} from './kit';
import {LookContext, DEFAULT_LOOK, type Look} from './kit';
import {PageCam, Ground, type CamKey, type Macro} from './PageCam';
import {Layers, OVERLAY_KINDS, type LayerSpec} from './Layers';
import {ChapterCard, FlashCut, CaptionStrip, BrandOpen, RecallOutro, OutroLockup, carryStyle} from './Cards';
import {Statement, Compare, Montage, Subtitles, throughStyle, type Region, type Sub} from './Shots';
import {ObjectShot, WallShot, StageOutro, type StageItem, type WallTile, type FeatureLabel, type World, type OutroObject} from './Stage';

type Cut = 'carry' | 'flash' | 'hard' | 'through' | 'morph';
export type PageShot = {kind: 'page'; dur: number; src: string; w: number; h: number; keys: CamKey[]; layers?: LayerSpec[]; acts?: LayerSpec[];
  caption?: {text: string; at?: number; dur?: number; pos?: 'bl' | 'br' | 'tl' | 'tr'}; cut?: Cut; radius?: number; maxZoom?: number; contain?: boolean;
  video?: string; videoStart?: number};
export type Shot =
  | {kind: 'brand'; dur: number; mark: string; aspect: number; kicker?: string; markH?: number; plate?: boolean; cut?: Cut}
  | {kind: 'title'; dur: number; text: string; kicker?: string; sub?: string; size?: number; index?: number | false; cut?: Cut}
  | PageShot
  | {kind: 'outro'; dur: number; mark: string; aspect: number; tagline?: string; stampAt?: number; markH?: number; recall?: number[]; cut?: Cut; cta?: string; plate?: boolean; world?: World}
  | {kind: 'statement'; dur: number; text: string; ground?: 'paper' | 'accent' | 'ink'; size?: number; sub?: string; cut?: Cut}
  | {kind: 'compare'; dur: number; a: Region; b: Region; labelA?: string; labelB?: string; at?: number; sweep?: number; cut?: Cut}
  | {kind: 'montage'; dur: number; items: Region[]; every?: number; full?: boolean; cut?: Cut}
  | {kind: 'object'; dur: number; world?: World; items: StageItem[]; label?: FeatureLabel; cut?: Cut}
  | {kind: 'wall'; dur: number; world?: World; tiles: WallTile[]; cols?: number; tile?: number; gap?: number; plane?: 'floor' | 'wall';
     from?: {x: number; y: number}; to?: {x: number; y: number}; label?: {text: string; sub?: string; at?: number}; cut?: Cut};

export type PromoProps = {look?: Partial<Look>; shots: Shot[]; cut?: Cut; subtitles?: Sub[]};

export const promoDuration = (p: PromoProps) => {
  if (!p?.shots?.length) throw new Error('PromoFilm: no shots');
  return p.shots.reduce((n, s) => {
    if (!(s.dur > 0)) throw new Error(`PromoFilm: shot ${s.kind} has no positive dur`);
    return n + Math.round(s.dur);
  }, 0);
};

// THE SHOT TABLE IS THE CLOCK. PromoFilm is its own composition: no Film CutCarry runs a picture lead over it
// (runtime/motion PictureLeadContext), so a span sized from a shot's length ends exactly when the shot does. The
// lengths are computed once, by name, below (validate.sequence_ends_at_duration guards the library's beats, not this).
const capSpan = (s: PageShot) => (s.caption?.dur ?? Math.max(20, Math.round(s.dur) - (s.caption?.at ?? 8) - 6));
export const PageShotView: React.FC<{s: PageShot}> = ({s}) => (
  <AbsoluteFill>
    <Ground />
    <PageCam src={s.src} w={s.w} h={s.h} keys={s.keys} radius={s.radius} maxZoom={s.maxZoom} contain={s.contain} video={s.video} videoStart={s.videoStart}
      macros={(s.layers ?? s.acts ?? []).filter((l) => l.kind === 'macro') as Macro[]}
      overlay={<Layers layers={(s.layers ?? s.acts ?? []).filter((l) => OVERLAY_KINDS.includes(l.kind))} src={s.src} pageW={s.w} pageH={s.h} />}>
      <Layers layers={(s.layers ?? s.acts ?? []).filter((l) => !OVERLAY_KINDS.includes(l.kind))} src={s.src} pageW={s.w} pageH={s.h} />
    </PageCam>
    {s.caption ? (
      <Sequence from={s.caption.at ?? 8} durationInFrames={capSpan(s)}>
        <CaptionStrip text={s.caption.text} dur={capSpan(s)} pos={s.caption.pos} />
      </Sequence>
    ) : null}
  </AbsoluteFill>
);

/** The direction the arriving shot's camera travels (content moves the other way): +1 / -1. */
const travel = (s: Shot, i: number): number => {
  if (s.kind === 'page' && s.keys.length > 1) {
    const d = s.keys[1].cx - s.keys[0].cx;
    if (Math.abs(d) > 20) return d > 0 ? 1 : -1;
  }
  return i % 2 ? 1 : -1;
};

const Carried: React.FC<{dur: number; dirIn: number; dirOut: number; inn: boolean; out: boolean; thrIn?: boolean; thrOut?: boolean;
  thrAt?: {x: number; y: number}; children: React.ReactNode}> = ({dur, dirIn, dirOut, inn, out, thrIn = false, thrOut = false, thrAt, children}) => {
  const frame = useCurrentFrame();
  const {width: W} = useVideoConfig();
  if (thrIn || thrOut) {
    const c = carryStyle(frame, dur, dirIn, dirOut, W, inn && !thrIn, out && !thrOut);
    return <AbsoluteFill style={c}><AbsoluteFill style={throughStyle(frame, dur, thrIn, thrOut, thrAt)}>{children}</AbsoluteFill></AbsoluteFill>;
  }
  return <AbsoluteFill style={carryStyle(frame, dur, dirIn, dirOut, W, inn, out)}>{children}</AbsoluteFill>;
};

const MORPH = 16;
/** A container transform: the next shot starts as the box (the thumbnail, the button), its picture SCALED into it (cover)
 *  and clipped to it, and the box and the picture grow together to the whole frame on an in-out curve — so the first
 *  frames read as "that thing lifting off the page", not as a hole opening. It fades up over 3 frames so the swap from
 *  the box's own pixels to the shot's is not a pop. */
const MorphIn: React.FC<{from?: {x: number; y: number; w: number; h: number}; children: React.ReactNode}> = ({from = {x: 0.42, y: 0.42, w: 0.16, h: 0.16}, children}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const p = span(frame, 0, MORPH, 'smooth');
  const bx = from.x * (1 - p), by = from.y * (1 - p);
  const bw = from.w + (1 - from.w) * p, bh = from.h + (1 - from.h) * p;
  const k0 = Math.max(from.w, from.h);                        // the picture covers the box at the start
  const k = k0 + (1 - k0) * p;
  const cx = (bx + bw / 2) * W, cy = (by + bh / 2) * H;       // the picture stays centred on the box
  const tx = cx - (k * W) / 2, ty = cy - (k * H) / 2;
  const fade = span(frame, 0, 3, 'out');
  return (
    <AbsoluteFill style={{clipPath: `inset(${by * H}px ${(1 - bx - bw) * W}px ${(1 - by - bh) * H}px ${bx * W}px round ${(1 - p) * 22}px)`, opacity: fade}}>
      <AbsoluteFill style={{transform: `translate(${tx}px, ${ty}px) scale(${k})`, transformOrigin: '0 0'}}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};

export const PromoFilm: React.FC<PromoProps> = ({look, shots, cut = 'carry', subtitles = []}) => {
  const L: Look = {...DEFAULT_LOOK, ...(look ?? {})};
  for (const k of ['accent', 'accentInk', 'paper', 'ground'] as const) {
    if (!/^#[0-9a-fA-F]{6}$/.test(L[k])) throw new Error(`PromoFilm: look.${k} must be #rrggbb (got ${L[k]})`);
  }
  let t = 0;
  const lens = shots.map((s) => Math.round(s.dur));
  const starts = lens.map((n) => { const a = t; t += n; return a; });
  const cards = shots.map((s, i) => (s.kind === 'title' && s.index !== false ? i : -1)).filter((i) => i >= 0);
  const cutInto = (i: number): Cut => (i === 0 ? 'hard' : shots[i].cut ?? cut);
  const pages = shots.map((s, i) => (s.kind === 'page' ? i : -1)).filter((i) => i >= 0);

  const view = (s: Shot, i: number): React.ReactNode => {
    switch (s.kind) {
      case 'brand': return <BrandOpen mark={s.mark} aspect={s.aspect} kicker={s.kicker} dur={s.dur} markH={s.markH} plate={s.plate} />;
      case 'title': {
        const k = cards.indexOf(i);
        return <ChapterCard text={s.text} dur={s.dur} size={s.size} kicker={s.kicker ?? s.sub}
          index={k >= 0 ? (typeof s.index === 'number' ? s.index : k + 1) : undefined} total={k >= 0 ? cards.length : undefined} />;
      }
      case 'page': return <PageShotView s={s} />;
      case 'outro': {
        if (s.world) {
          // STAGED: the film's own components (its object and wall shots' still parts) gather round the mark
          const objs: OutroObject[] = [];
          for (const x of shots) {
            if (x.kind === 'object') objs.push(...x.items.filter((it) => it.src && !it.video).map((it) => ({src: it.src as string, w: it.w, h: it.h, radius: it.radius})));
            if (x.kind === 'wall') objs.push(...x.tiles.filter((t) => t.src && !t.video).map((t) => ({src: t.src as string, w: t.w, h: t.h, radius: t.radius})));
          }
          const seen = new Set<string>();
          const uniq = objs.filter((o) => (seen.has(o.src) ? false : (seen.add(o.src), true)));
          const pick = uniq.length <= 6 ? uniq : Array.from({length: 6}, (_, k) => uniq[Math.round((k * (uniq.length - 1)) / 5)]);
          return <StageOutro dur={s.dur} world={s.world} objects={pick} stampAt={s.stampAt}
            lockup={<OutroLockup mark={s.mark} aspect={s.aspect} tagline={s.tagline} stampAt={s.stampAt} markH={s.markH} cta={s.cta} plate={s.plate} />} />;
        }
        // the wall: the film's product shots at their settled frames (default: up to 6, spread across the film)
        const pick = s.recall ?? (pages.length <= 6 ? pages : Array.from({length: 6}, (_, k) => pages[Math.round((k * (pages.length - 1)) / 5)]));
        const tiles = pick.filter((j) => shots[j]?.kind === 'page').map((j) => (
          <Freeze key={j} frame={Math.round(shots[j].dur * 0.9)}><PageShotView s={{...(shots[j] as PageShot), caption: undefined}} /></Freeze>
        ));
        return <RecallOutro tiles={tiles} mark={s.mark} aspect={s.aspect} tagline={s.tagline} dur={s.dur} stampAt={s.stampAt} markH={s.markH} cta={s.cta} plate={s.plate} />;
      }
      case 'statement': return <Statement text={s.text} dur={s.dur} ground={s.ground} size={s.size} sub={s.sub} />;
      case 'compare': return <Compare a={s.a} b={s.b} labelA={s.labelA} labelB={s.labelB} at={s.at} sweep={s.sweep} dur={s.dur} />;
      case 'montage': return <Montage items={s.items} every={s.every} full={s.full} dur={s.dur} />;
      case 'object': return <ObjectShot dur={s.dur} world={s.world} items={s.items} label={s.label} />;
      case 'wall': return <WallShot dur={s.dur} world={s.world} tiles={s.tiles} cols={s.cols} tile={s.tile} gap={s.gap} plane={s.plane}
        from={s.from} to={s.to} label={s.label} />;
      default: throw new Error(`PromoFilm: unknown shot kind ${(s as {kind: string}).kind}`);
    }
  };

  return (
    <LookContext.Provider value={L}>
      <AbsoluteFill style={{background: L.paper}}>
        {shots.map((s, i) => (
          <Sequence key={i} from={starts[i]} durationInFrames={lens[i]}>
            <Carried dur={lens[i]} dirIn={travel(s, i)} dirOut={travel(shots[Math.min(i + 1, shots.length - 1)], i + 1)}
              inn={cutInto(i) === 'carry'} out={i + 1 < shots.length && cutInto(i + 1) === 'carry'}
              thrIn={cutInto(i) === 'through'} thrOut={i + 1 < shots.length && cutInto(i + 1) === 'through'}
              thrAt={(shots[i + 1] as {throughAt?: {x: number; y: number}} | undefined)?.throughAt ?? (s as {throughAt?: {x: number; y: number}}).throughAt}>
              {view(s, i)}
            </Carried>
          </Sequence>
        ))}
        {/* MORPH: the next shot grows out of a box of this one (a button opening into its panel) over the cut's last
            frames — its first frame, held, clipped to the box and opening to the whole frame */}
        {shots.map((s, i) => (cutInto(i) === 'morph' ? (
          <Sequence key={`mo${i}`} from={starts[i] - MORPH} durationInFrames={MORPH}>
            <MorphIn from={(s as {morphFrom?: {x: number; y: number; w: number; h: number}}).morphFrom}>
              <Freeze frame={0}>{view(s, i)}</Freeze>
            </MorphIn>
          </Sequence>
        ) : null))}
        {subtitles.length ? <Subtitles subs={subtitles} /> : null}
        {shots.map((_, i) => (cutInto(i) === 'flash' ? (
          <Sequence key={`fl${i}`} from={starts[i] - 5} durationInFrames={10}><FlashCut /></Sequence>
        ) : null))}
      </AbsoluteFill>
    </LookContext.Provider>
  );
};
