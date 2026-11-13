// PROMO · PromoFilm — a product film written as a SHOT TABLE (references/promo-film.md).
//
// props: {look, shots: Shot[], cut?: 'carry' | 'flash' | 'hard'}. Shots play back to back. Every cut INTO a shot
// carries one move through it (Cards.carryStyle) unless the film or the shot names another cut. Chapter cards are
// numbered in order (01 / 04) unless a card says `index: false`. The outro recalls the film's own product shots,
// frozen at their settled frames, as the wall the lockup forms over. Timings inside a shot are frames from the
// shot's own start. Sound is not drawn here: scripts/promo_film.py pins the cues to the same table.
import React from 'react';
import {AbsoluteFill, Freeze, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {LookContext, DEFAULT_LOOK, type Look} from './kit';
import {PageCam, Ground, type CamKey} from './PageCam';
import {Layers, type LayerSpec} from './Layers';
import {ChapterCard, FlashCut, CaptionStrip, BrandOpen, RecallOutro, carryStyle} from './Cards';

type Cut = 'carry' | 'flash' | 'hard';
export type PageShot = {kind: 'page'; dur: number; src: string; w: number; h: number; keys: CamKey[]; layers?: LayerSpec[]; acts?: LayerSpec[];
  caption?: {text: string; at?: number; dur?: number}; cut?: Cut; radius?: number; maxZoom?: number; contain?: boolean};
export type Shot =
  | {kind: 'brand'; dur: number; mark: string; aspect: number; kicker?: string; markH?: number; cut?: Cut}
  | {kind: 'title'; dur: number; text: string; kicker?: string; sub?: string; size?: number; index?: number | false; cut?: Cut}
  | PageShot
  | {kind: 'outro'; dur: number; mark: string; aspect: number; tagline?: string; stampAt?: number; markH?: number; recall?: number[]; cut?: Cut};

export type PromoProps = {look?: Partial<Look>; shots: Shot[]; cut?: Cut};

export const promoDuration = (p: PromoProps) => {
  if (!p?.shots?.length) throw new Error('PromoFilm: no shots');
  return p.shots.reduce((n, s) => {
    if (!(s.dur > 0)) throw new Error(`PromoFilm: shot ${s.kind} has no positive dur`);
    return n + Math.round(s.dur);
  }, 0);
};

export const PageShotView: React.FC<{s: PageShot}> = ({s}) => (
  <AbsoluteFill>
    <Ground />
    <PageCam src={s.src} w={s.w} h={s.h} keys={s.keys} radius={s.radius} maxZoom={s.maxZoom} contain={s.contain}>
      <Layers layers={s.layers ?? s.acts ?? []} src={s.src} pageW={s.w} pageH={s.h} />
    </PageCam>
    {s.caption ? (
      <Sequence from={s.caption.at ?? 8} durationInFrames={s.caption.dur ?? Math.max(20, s.dur - (s.caption.at ?? 8) - 6)}>
        <CaptionStrip text={s.caption.text} dur={s.caption.dur ?? Math.max(20, s.dur - (s.caption.at ?? 8) - 6)} />
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

const Carried: React.FC<{dur: number; dirIn: number; dirOut: number; inn: boolean; out: boolean; children: React.ReactNode}> = (
  {dur, dirIn, dirOut, inn, out, children}) => {
  const frame = useCurrentFrame();
  const {width: W} = useVideoConfig();
  return <AbsoluteFill style={carryStyle(frame, dur, dirIn, dirOut, W, inn, out)}>{children}</AbsoluteFill>;
};

export const PromoFilm: React.FC<PromoProps> = ({look, shots, cut = 'carry'}) => {
  const L: Look = {...DEFAULT_LOOK, ...(look ?? {})};
  for (const k of ['accent', 'accentInk', 'paper', 'ground'] as const) {
    if (!/^#[0-9a-fA-F]{6}$/.test(L[k])) throw new Error(`PromoFilm: look.${k} must be #rrggbb (got ${L[k]})`);
  }
  let t = 0;
  const starts = shots.map((s) => { const a = t; t += Math.round(s.dur); return a; });
  const cards = shots.map((s, i) => (s.kind === 'title' && s.index !== false ? i : -1)).filter((i) => i >= 0);
  const cutInto = (i: number): Cut => (i === 0 ? 'hard' : shots[i].cut ?? cut);
  const pages = shots.map((s, i) => (s.kind === 'page' ? i : -1)).filter((i) => i >= 0);

  const view = (s: Shot, i: number): React.ReactNode => {
    switch (s.kind) {
      case 'brand': return <BrandOpen mark={s.mark} aspect={s.aspect} kicker={s.kicker} dur={s.dur} markH={s.markH} />;
      case 'title': {
        const k = cards.indexOf(i);
        return <ChapterCard text={s.text} dur={s.dur} size={s.size} kicker={s.kicker ?? s.sub}
          index={k >= 0 ? (typeof s.index === 'number' ? s.index : k + 1) : undefined} total={k >= 0 ? cards.length : undefined} />;
      }
      case 'page': return <PageShotView s={s} />;
      case 'outro': {
        // the wall: the film's product shots at their settled frames (default: up to 6, spread across the film)
        const pick = s.recall ?? (pages.length <= 6 ? pages : Array.from({length: 6}, (_, k) => pages[Math.round((k * (pages.length - 1)) / 5)]));
        const tiles = pick.filter((j) => shots[j]?.kind === 'page').map((j) => (
          <Freeze key={j} frame={Math.round(shots[j].dur * 0.9)}><PageShotView s={{...(shots[j] as PageShot), caption: undefined}} /></Freeze>
        ));
        return <RecallOutro tiles={tiles} mark={s.mark} aspect={s.aspect} tagline={s.tagline} dur={s.dur} stampAt={s.stampAt} markH={s.markH} />;
      }
      default: throw new Error(`PromoFilm: unknown shot kind ${(s as {kind: string}).kind}`);
    }
  };

  return (
    <LookContext.Provider value={L}>
      <AbsoluteFill style={{background: L.paper}}>
        {shots.map((s, i) => (
          <Sequence key={i} from={starts[i]} durationInFrames={Math.round(s.dur)}>
            <Carried dur={Math.round(s.dur)} dirIn={travel(s, i)} dirOut={travel(shots[Math.min(i + 1, shots.length - 1)], i + 1)}
              inn={cutInto(i) === 'carry'} out={i + 1 < shots.length && cutInto(i + 1) === 'carry'}>
              {view(s, i)}
            </Carried>
          </Sequence>
        ))}
        {shots.map((_, i) => (cutInto(i) === 'flash' ? (
          <Sequence key={`fl${i}`} from={starts[i] - 5} durationInFrames={10}><FlashCut /></Sequence>
        ) : null))}
      </AbsoluteFill>
    </LookContext.Provider>
  );
};
