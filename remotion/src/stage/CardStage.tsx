// STAGE · CardStage — ONE card that stays on stage across a run of beats and changes its state with each of them: where
// it sits, how it is turned, how big it is, what shape it is. The run's beats are its keyframes (runtime/stageRun): each
// beat says where the card should BE, the card moves there in the beat's first moments and lives there for the rest of
// it. Over the card, the beat's title — the same line, the same place, the same style on every beat, the key word
// marked — changes as the beat changes.
//
// What it is for: a product promo's hero object (a deck page, a screenshot, a document) that the film keeps turning
// over instead of cutting away from — the shape of "the same thing, shown one more way" that a run of separate shots
// cannot draw. Every word and picture comes from props: the card's face is the run's `image` (a file the film serves)
// or a `page` it draws; the titles are each beat's own.
import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {TITLE_Y, contentBottom, CONTENT_TOP} from '../runtime/layout';
import {useStageRun, useActorState} from '../runtime/stageRun';

/** The card's pose in one beat. x/y: offset of its centre from the content zone's centre, as fractions of the frame's
 *  width/height; s: scale (1 = the base size); rx/ry/rz: degrees; aspect: width over height. */
export type CardPose = {x?: number; y?: number; s?: number; rx?: number; ry?: number; rz?: number; aspect?: number};
const POSE: Required<CardPose> = {x: 0, y: 0, s: 1, rx: 0, ry: 0, rz: 0, aspect: 16 / 9};

export const CardStage: React.FC<{
  image?: string;                                  // the card's face: a file the film serves (its public dir)
  page?: {kicker?: string; title?: string; lines?: string[]};   // or a page the card draws, when there is no image
  // per beat (each beat's shot_props):
  title?: string;                                  // the beat's title line
  highlight?: string;                              // the word of it to mark
  card?: CardPose;                                 // where the card is in this beat
}> = ({image, page}) => {
  const dna = useDNA();
  const now = useStageRun();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const ink = {bg: dna?.bg ?? '#F4F5F8', fg: dna?.fg ?? '#15161A', dim: dna?.dim ?? '#6B6E78',
    acc: dna?.accent ?? '#2B5BFF', surface: dna?.surface ?? '#FFFFFF', on: dna?.onAccent ?? '#FFFFFF'};
  const pose = {...POSE, ...useActorState<CardPose>((p) => p.card as CardPose | undefined, POSE)} as Required<CardPose>;

  // ── the card: one object, posed in 3D, alive while it holds ──
  const sec = now.frame / now.fps;
  const idle = now.reduced ? 0 : 1;
  const floatY = idle * Math.sin((2 * Math.PI * sec) / 6.5) * U * 0.006;
  const sway = idle * Math.sin((2 * Math.PI * sec) / 9 + 1.1) * 1.2;
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const cx = W / 2 + pose.x * W, cy = (zoneTop + zoneBot) / 2 + pose.y * H + floatY;
  const portrait = W < H;
  const baseW = (portrait ? W * 0.8 : W * 0.56) * Math.min(1, Math.sqrt((16 / 9) / Math.max(0.3, pose.aspect)));
  const cw = baseW, ch = baseW / Math.max(0.3, pose.aspect);
  const r = U * 0.014;
  const transform = `translate(${cx - cw / 2}px, ${cy - ch / 2}px) perspective(${U * 1.6}px) ` +
    `rotateX(${pose.rx}deg) rotateY(${pose.ry + sway}deg) rotateZ(${pose.rz}deg) scale(${pose.s})`;
  const face = image ? (
    <Img src={staticFile(image)} style={{width: '100%', height: '100%', objectFit: 'cover', display: 'block'}} />
  ) : (
    <div style={{position: 'absolute', inset: 0, padding: cw * 0.06, boxSizing: 'border-box', background: ink.surface}}>
      {page?.kicker ? <div style={{color: ink.acc, font: `600 ${Math.round(cw * 0.022)}px/1.2 var(--f-body, system-ui)`,
        letterSpacing: '0.08em', textTransform: 'uppercase'}}>{page.kicker}</div> : null}
      {page?.title ? <div style={{color: ink.fg, marginTop: cw * 0.012,
        font: `700 ${Math.round(cw * 0.05)}px/1.15 var(--f-display, system-ui)`}}>{page.title}</div> : null}
      {(page?.lines ?? []).map((l, i) => <div key={i} style={{color: ink.dim, marginTop: cw * 0.02,
        font: `400 ${Math.round(cw * 0.028)}px/1.35 var(--f-body, system-ui)`}}>{l}</div>)}
    </div>
  );

  // ── the title: one line, one place, changing with the beat ──
  const titlePx = Math.round(U * (portrait ? 0.07 : 0.058));
  const sx = W * 0.065;
  const curTitle = String((now.beat.props.title as string) ?? '');
  const prevTitle = now.k > 0 ? String((now.beats[now.k - 1].props.title as string) ?? '') : '';
  const changed = prevTitle !== curTitle;
  const inP = changed ? now.morph : 1;
  const outP = changed && now.k > 0 ? 1 - now.morph : 0;
  const titleLine = (text: string, hi: string | undefined, p: number, leaving: boolean) => {
    if (!text) return null;
    const chars = [...text];
    const at = hi ? text.indexOf(hi) : -1;
    const hiFrom = at >= 0 ? [...text.slice(0, at)].length : -1, hiTo = at >= 0 ? hiFrom + [...hi!].length : -1;
    return (
      <div style={{position: 'absolute', left: sx, top: TITLE_Y + (leaving ? -(1 - p) * U * 0.03 : 0), right: sx,
        opacity: leaving ? p : 1, color: ink.fg, font: `800 ${titlePx}px/1.15 var(--f-display, system-ui)`,
        letterSpacing: '-0.01em'}}>
        {chars.map((c, i) => {
          // characters arrive left to right across the move; the marked word's block grows behind it after
          const a = leaving ? 1 : easeOutCubic(clamp01(p * 1.6 - (i / Math.max(1, chars.length)) * 0.6));
          const marked = i >= hiFrom && i < hiTo;
          return <span key={i} style={{position: 'relative', zIndex: 0, display: 'inline-block', opacity: a,
            transform: `translateY(${(1 - a) * titlePx * 0.3}px)`, color: marked ? ink.on : ink.fg, whiteSpace: 'pre'}}>
            {marked ? <span style={{position: 'absolute', left: -titlePx * 0.04, right: -titlePx * 0.04, top: '8%', bottom: '2%',
              background: ink.acc, zIndex: -1, transformOrigin: 'left center',
              transform: `scaleX(${leaving ? 1 : easeInOutCubic(clamp01(p * 1.4 - 0.3))})`}} /> : null}
            {c}
          </span>;
        })}
      </div>
    );
  };

  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${mix(ink.bg, '#ffffff', 0.5)} 0%, ${ink.bg} 70%)`}}>
      {/* the card's shadow on the floor of the stage, softer and wider as the card lifts */}
      <div style={{position: 'absolute', left: cx - cw * 0.42 * pose.s, top: cy + ch * 0.5 * pose.s, width: cw * 0.84 * pose.s,
        height: U * 0.05, borderRadius: '50%', background: mix(ink.fg, ink.bg, 0.6), opacity: 0.35,
        filter: `blur(${U * 0.03}px)`}} />
      <div style={{position: 'absolute', left: 0, top: 0, width: cw, height: ch, transform, transformOrigin: 'center center',
        borderRadius: r, overflow: 'hidden', background: ink.surface,
        boxShadow: `0 ${U * 0.02}px ${U * 0.06}px ${mix(ink.fg, ink.bg, 0.75)}, 0 0 0 1px ${mix(ink.fg, ink.bg, 0.88)}`}}>
        {face}
      </div>
      {outP > 0 ? titleLine(prevTitle, now.beats[now.k - 1].props.highlight as string | undefined, outP, true) : null}
      {titleLine(curTitle, now.beat.props.highlight as string | undefined, inP, false)}
    </AbsoluteFill>
  );
};
