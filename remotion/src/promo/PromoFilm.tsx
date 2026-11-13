// PROMO · PromoFilm — a product film written as a SHOT TABLE (references/promo-film.md).
//
// props: {look, shots: Shot[]}. Shots play back to back (hard cuts); a flash cut straddles every cut INTO a page
// shot unless the shot says `flash: false`. Timings inside a shot are frames from the shot's own start. Sound is
// not drawn here: scripts/promo_film.py pins the cues to the same table and mixes them under the picture.
import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {LookContext, DEFAULT_LOOK, type Look} from './kit';
import {PageCam, Ground, type CamKey} from './PageCam';
import {Layers, type LayerSpec} from './Layers';
import {TitleCard, FlashCut, CaptionStrip, BrandOpen, OutroAssembly, type Piece} from './Cards';

export type PageShot = {kind: 'page'; dur: number; src: string; w: number; h: number; keys: CamKey[]; layers?: LayerSpec[];
  caption?: {text: string; at?: number; dur?: number}; flash?: boolean; radius?: number; maxZoom?: number};
export type Shot =
  | {kind: 'brand'; dur: number; mark: string; aspect: number; kicker?: string; markH?: number}
  | {kind: 'title'; dur: number; text: string; sub?: string; size?: number; flash?: boolean}
  | PageShot
  | {kind: 'outro'; dur: number; pieces: Piece[]; mark: string; aspect: number; tagline?: string; stampAt?: number; flash?: boolean; markH?: number};

export type PromoProps = {look?: Partial<Look>; shots: Shot[]};

export const promoDuration = (p: PromoProps) => {
  if (!p?.shots?.length) throw new Error('PromoFilm: no shots');
  return p.shots.reduce((n, s) => {
    if (!(s.dur > 0)) throw new Error(`PromoFilm: shot ${s.kind} has no positive dur`);
    return n + Math.round(s.dur);
  }, 0);
};

const PageShotView: React.FC<{s: PageShot}> = ({s}) => (
  <AbsoluteFill>
    <Ground />
    <PageCam src={s.src} w={s.w} h={s.h} keys={s.keys} radius={s.radius} maxZoom={s.maxZoom}>
      <Layers layers={s.layers ?? []} src={s.src} pageW={s.w} pageH={s.h} />
    </PageCam>
    {s.caption ? (
      <Sequence from={s.caption.at ?? 8} durationInFrames={s.caption.dur ?? Math.max(20, s.dur - (s.caption.at ?? 8) - 6)}>
        <CaptionStrip text={s.caption.text} dur={s.caption.dur ?? Math.max(20, s.dur - (s.caption.at ?? 8) - 6)} />
      </Sequence>
    ) : null}
  </AbsoluteFill>
);

const ShotView: React.FC<{s: Shot}> = ({s}) => {
  switch (s.kind) {
    case 'brand': return <BrandOpen mark={s.mark} aspect={s.aspect} kicker={s.kicker} dur={s.dur} markH={s.markH} />;
    case 'title': return <TitleCard text={s.text} sub={s.sub} dur={s.dur} size={s.size} />;
    case 'page': return <PageShotView s={s} />;
    case 'outro': return <OutroAssembly pieces={s.pieces} mark={s.mark} aspect={s.aspect} tagline={s.tagline} dur={s.dur} stampAt={s.stampAt} markH={s.markH} />;
    default: throw new Error(`PromoFilm: unknown shot kind ${(s as {kind: string}).kind}`);
  }
};

export const PromoFilm: React.FC<PromoProps> = ({look, shots}) => {
  const L: Look = {...DEFAULT_LOOK, ...(look ?? {})};
  for (const k of ['accent', 'accentInk'] as const) {
    if (!/^#[0-9a-fA-F]{6}$/.test(L[k])) throw new Error(`PromoFilm: look.${k} must be #rrggbb (got ${L[k]})`);
  }
  let t = 0;
  const starts = shots.map((s) => { const a = t; t += Math.round(s.dur); return a; });
  return (
    <LookContext.Provider value={L}>
      <AbsoluteFill style={{background: L.paper}}>
        {shots.map((s, i) => (
          <Sequence key={i} from={starts[i]} durationInFrames={Math.round(s.dur)}>
            <ShotView s={s} />
          </Sequence>
        ))}
        {shots.map((s, i) => {
          const into = i > 0 && (s.kind === 'page' || s.kind === 'outro') && (s as {flash?: boolean}).flash !== false;
          return into ? (
            <Sequence key={`fl${i}`} from={starts[i] - 5} durationInFrames={10}><FlashCut /></Sequence>
          ) : null;
        })}
      </AbsoluteFill>
    </LookContext.Provider>
  );
};
