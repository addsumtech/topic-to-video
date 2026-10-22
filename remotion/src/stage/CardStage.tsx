// STAGE · CardStage — ONE card that stays on stage across a run of beats and changes its state with each of them: where
// it sits, how it is turned, how big it is, what shape it is, what is on its face. The run's beats are its keyframes
// (runtime/stageRun): each beat says where the card should BE, the card moves there in the beat's first moments and
// lives there for the rest of it. Over the card, the beat's title — the same line, the same place, the same size on
// every beat, the key word marked — changes as the beat changes: the old line leaves, then the new one arrives.
//
// What it is for: a product promo's hero object (a deck page, a screenshot, a document) that the film keeps turning
// over instead of cutting away from — the shape of "the same thing, shown one more way" that a run of separate shots
// cannot draw. Every word and picture comes from props: the card's face is a beat's `image` (a file the film serves)
// or a `page` it draws; the titles are each beat's own.
import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {useDNA, mix, relLum} from '../runtime/dna';
import {hex6} from '../runtime/hexColor';
import {measureText} from '@remotion/layout-utils';
import {TITLE_Y, contentBottom, CONTENT_TOP} from '../runtime/layout';
import {useStageRun, heldAt, lerpState, StageBeat} from '../runtime/stageRun';

/** The card's pose in one beat. x/y: offset of its centre from the content zone's centre, as fractions of the frame's
 *  width/height; s: scale (1 = as large as the zone allows); rx/ry/rz: degrees; aspect: width over height — when a beat
 *  leaves it out, the card takes the shape of its face (the image's own `imageAspect`), so nothing is cropped. */
export type CardPose = {x?: number; y?: number; s?: number; rx?: number; ry?: number; rz?: number; aspect?: number};
type Pose = Required<CardPose>;
const POSE: Pose = {x: 0, y: 0, s: 1, rx: 0, ry: 0, rz: 0, aspect: 16 / 9};
type Page = {kicker?: string; title?: string; lines?: string[]};
type Face = {image?: string; page?: Page; aspect?: number};

// a character a line may break before or after (layout.ts keeps its own copy private: exporting it would re-key every
// register that imports layout.ts)
const CJK_CH = /[\u2e80-\u9fff\uf900-\ufaff\uff01-\uff60\u3000-\u303f]/;

const faceOf = (p: Record<string, unknown>): Face | undefined =>
  p.image !== undefined || p.page !== undefined
    ? {image: p.image as string | undefined, page: p.page as Page | undefined,
      aspect: typeof p.imageAspect === 'number' && p.imageAspect > 0 ? p.imageAspect : undefined}
    : undefined;
const sameFace = (a: Face, b: Face) => a.image === b.image && JSON.stringify(a.page) === JSON.stringify(b.page);

/** The card's pose in beat i: the last pose set (a beat that sets none keeps the card where it was), its shape the
 *  pose's own `aspect`, else the face's, else 16:9. */
const poseAt = (beats: StageBeat[], i: number): Pose => {
  const card = heldAt<CardPose>(beats, i, (p) => p.card as CardPose | undefined, {});
  const face = heldAt<Face>(beats, i, faceOf, {});
  return {...POSE, ...card, aspect: card.aspect ?? face.aspect ?? POSE.aspect};
};

/** Half the width and height a card of w×h covers on screen in pose p: its four corners scaled, turned (Z, then Y,
 *  then X — the order CSS applies `rotateX rotateY rotateZ scale` to a point) and put through the perspective. The
 *  corners are symmetric, so the extent does not depend on which way each turn goes. */
const extent = (w: number, h: number, p: Pose, persp: number) => {
  const rad = Math.PI / 180;
  let hx = 0, hy = 0;
  for (const [sx, sy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
    let x = sx * w / 2 * p.s, y = sy * h / 2 * p.s, z = 0;
    [x, y] = [x * Math.cos(p.rz * rad) - y * Math.sin(p.rz * rad), x * Math.sin(p.rz * rad) + y * Math.cos(p.rz * rad)];
    [x, z] = [x * Math.cos(p.ry * rad) + z * Math.sin(p.ry * rad), -x * Math.sin(p.ry * rad) + z * Math.cos(p.ry * rad)];
    [y, z] = [y * Math.cos(p.rx * rad) - z * Math.sin(p.rx * rad), y * Math.sin(p.rx * rad) + z * Math.cos(p.rx * rad)];
    const f = persp / Math.max(1, persp - z);
    hx = Math.max(hx, Math.abs(x * f));
    hy = Math.max(hy, Math.abs(y * f));
  }
  return {hx, hy};
};

export const CardStage: React.FC<{
  // per beat (each beat's shot_props); a value a beat leaves out is the one the beat before it held
  image?: string;                                  // the card's face: a file the film serves (its public dir)
  imageAspect?: number;                            // the image's width / height — written by render_remotion, not authored
  page?: Page;                                     // or a page the card draws, when there is no image
  fit?: 'cover' | 'contain';                       // how an image meets a card of another shape (default cover)
  title?: string;                                  // the beat's title line
  highlight?: string;                              // the word of it to mark
  card?: CardPose;                                 // where the card is in this beat
}> = () => {
  const dna = useDNA();
  const now = useStageRun();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const ink = {bg: hex6(dna?.bg ?? '#F4F5F8'), fg: dna?.fg ?? '#15161A', dim: dna?.dim ?? '#6B6E78',
    acc: dna?.accent ?? '#2B5BFF', surface: dna?.surface ?? '#FFFFFF', on: dna?.onAccent ?? '#FFFFFF'};
  const portrait = W < H;
  const {beats, k} = now;

  // ── the title: one line at one size for the whole run, sized so the longest of its titles fits ──
  const sx = W * 0.065;
  const titleOf = (i: number) => String((beats[i].props.title as string) ?? '');
  // At most TWO lines: one size for the whole run, the largest at which every title fits in two and its longest word
  // in one. Widths are MEASURED in the face that draws them — forcing one line shrank every title of a portrait run to
  // a caption's size because one of them was long, and the runtime's generous estimate (0.72 em a character) read a
  // 0.39 em serif as twice its width.
  const titleBase = Math.round(U * (portrait ? 0.07 : 0.058));
  const lineW = W - 2 * sx;
  const family = dna?.uniformType ? dna.fontMono : (dna?.fontDisplay ?? 'system-ui');
  const per = (t: string) => measureText({text: t, fontFamily: family, fontSize: 100, fontWeight: '800',
    letterSpacing: '-0.01em'}).width / 100;
  const titles = beats.map((_b, i) => titleOf(i)).filter(Boolean);
  const titlePx = Math.max(12, Math.floor(titles.reduce((px, t) => {
    const longestWord = Math.max(...t.split(/\s+/).filter(Boolean).map((w) => (CJK_CH.test(w) ? 0 : per(w))), 0);
    return Math.min(px, (lineW * 2 * 0.92) / Math.max(0.01, per(t)), lineW / Math.max(0.01, longestWord));
  }, titleBase)));
  const titleLines = titles.reduce((n, t) => Math.max(n, per(t) * titlePx > lineW * 0.99 ? 2 : 1), 1);

  // ── the card's zone: below the title, above the caption band ──
  const zoneTop = Math.max(CONTENT_TOP, TITLE_Y + titleLines * titlePx * 1.15 + U * 0.04);
  const zoneBot = contentBottom(W, H) - U * 0.02;
  const side = W * (portrait ? 0.07 : 0.19);

  // ── the card: one object, posed in 3D, alive while it holds ──
  const pose = (k === 0 || now.morph >= 1 ? poseAt(beats, k)
    : lerpState(poseAt(beats, k - 1), poseAt(beats, k), now.morph)) as Pose;
  const sec = now.frame / now.fps;
  const idle = now.reduced ? 0 : 1;
  const floatY = idle * Math.sin((2 * Math.PI * sec) / 6.5) * U * 0.006;
  const sway = idle * Math.sin((2 * Math.PI * sec) / 9 + 1.1) * 1.2;
  const persp = U * 1.6;
  const centre = (p: Pose) => ({cx: W / 2 + p.x * W, cy: (zoneTop + zoneBot) / 2 + p.y * H});
  // the card's size in a pose: as large as the zone allows at its shape, then shrunk until the TURNED card (sway
  // included) stays inside it
  const sizeIn = (p: Pose) => {
    const {cx: x, cy: y} = centre(p);
    const a = Math.max(0.3, p.aspect);
    const room = {x: Math.max(1, Math.min(x - side, W - side - x)), y: Math.max(1, Math.min(y - zoneTop, zoneBot - y))};
    const w = Math.min(2 * room.x, 2 * room.y * a), h = w / a;
    const e = extent(w, h, {...p, ry: Math.abs(p.ry) + 1.2}, persp);
    const f = Math.min(1, room.x / e.hx, room.y / e.hy);
    return {w: w * f, h: h * f, hy: e.hy * f};
  };
  // during a move the SIZE travels between the two beats' sizes: sizing each in-between shape to the zone swelled the
  // card mid-move (a squarish in-between fills the zone both ways) and shrank it back as it arrived
  const size = k === 0 || now.morph >= 1 ? sizeIn(poseAt(beats, k))
    : lerpState(sizeIn(poseAt(beats, k - 1)), sizeIn(poseAt(beats, k)), now.morph) as {w: number; h: number; hy: number};
  const {cx, cy} = centre(pose);
  const cw = size.w, ch = size.h;
  const r = U * 0.014;
  const transform = `translate(${cx - cw / 2}px, ${cy + floatY - ch / 2}px) perspective(${persp}px) ` +
    `rotateX(${pose.rx}deg) rotateY(${pose.ry + sway}deg) rotateZ(${pose.rz}deg) scale(${pose.s})`;

  // ── the face: the one this beat holds. A face that changes is swapped at the middle of the move, where the card
  // travels fastest: the new face covers the old over a few frames. A cross-fade across the whole move read as a
  // double exposure, and fading out through the card's surface blinked the card to the ground's colour on a dark DNA ──
  const fit = heldAt<'cover' | 'contain'>(beats, k, (p) => p.fit as 'cover' | 'contain' | undefined, 'cover');
  const faceNow = heldAt<Face>(beats, k, faceOf, {});
  const faceBefore = k > 0 ? heldAt<Face>(beats, k - 1, faceOf, {}) : faceNow;
  const fading = k > 0 && now.morph < 1 && !sameFace(faceBefore, faceNow);
  const drawFace = (f: Face, opacity: number) => (
    <div style={{position: 'absolute', inset: 0, opacity, background: ink.surface}}>
      {f.image ? (
        <Img src={staticFile(f.image)} style={{width: '100%', height: '100%', objectFit: fit, display: 'block'}} />
      ) : f.page ? (
        <div style={{position: 'absolute', inset: 0, padding: cw * 0.06, boxSizing: 'border-box'}}>
          {f.page.kicker ? <div style={{color: ink.acc, font: `600 ${Math.round(cw * 0.022)}px/1.2 var(--f-body, system-ui)`,
            letterSpacing: '0.08em', textTransform: 'uppercase'}}>{f.page.kicker}</div> : null}
          {f.page.title ? <div style={{color: ink.fg, marginTop: cw * 0.012,
            font: `700 ${Math.round(cw * 0.05)}px/1.15 var(--f-display, system-ui)`}}>{f.page.title}</div> : null}
          {(f.page.lines ?? []).map((l, i) => <div key={i} style={{color: ink.dim, marginTop: cw * 0.02,
            font: `400 ${Math.round(cw * 0.028)}px/1.35 var(--f-body, system-ui)`}}>{l}</div>)}
        </div>
      ) : null}
    </div>
  );

  // ── the title line: the old one leaves in the first part of the move, then the new one arrives — never both ──
  const curTitle = titleOf(k);
  const prevTitle = k > 0 ? titleOf(k - 1) : '';
  const changed = prevTitle !== curTitle;
  const inP = changed && k > 0 ? clamp01((now.morph - 0.38) / 0.62) : 1;
  const outP = changed && k > 0 ? 1 - clamp01(now.morph / 0.36) : 0;
  const titleLine = (text: string, hi: string | undefined, p: number, leaving: boolean) => {
    if (!text) return null;
    const chars = [...text];
    const at = hi ? text.indexOf(hi) : -1;
    const hiFrom = at >= 0 ? [...text.slice(0, at)].length : -1, hiTo = at >= 0 ? hiFrom + [...hi!].length : -1;
    const nHi = Math.max(1, hiTo - hiFrom);
    // characters arrive left to right; then the marked word's block SWEEPS across it, one character after the next,
    // so it reads as one block growing (each character growing its own block at once read as a row of stripes) and
    // carries on over a line break; a character turns to the on-accent ink once the block is under it
    const sweep = leaving ? nHi : easeInOutCubic(clamp01(p * 1.4 - 0.3)) * nHi;
    const glyph = (c: string, i: number) => {
      const a = leaving ? 1 : easeOutCubic(clamp01(p * 1.6 - (i / Math.max(1, chars.length)) * 0.6));
      const fill = i >= hiFrom && i < hiTo ? clamp01(sweep - (i - hiFrom)) : -1;
      return <span key={i} style={{position: 'relative', zIndex: 0, display: 'inline-block', whiteSpace: 'pre', opacity: a,
        transform: `translateY(${(1 - a) * titlePx * 0.3}px)`, color: fill > 0.5 ? ink.on : ink.fg}}>
        {fill > 0 ? <span style={{position: 'absolute', left: -titlePx * 0.03, right: -titlePx * 0.03, top: '8%', bottom: '2%',
          background: ink.acc, zIndex: -1, transformOrigin: 'left center', transform: `scaleX(${fill})`}} /> : null}
        {c}
      </span>;
    };
    // where a line may break: between words, at any CJK character — never inside a word (each character is its own
    // box, and a browser breaks between any two boxes, so a word is held together in one)
    const tokens: React.ReactNode[] = [];
    let word: React.ReactNode[] = [];
    const flush = () => { if (word.length) tokens.push(<span key={`w${tokens.length}`} style={{display: 'inline-block',
      whiteSpace: 'nowrap'}}>{word}</span>); word = []; };
    chars.forEach((c, i) => {
      if (/\s/.test(c) || CJK_CH.test(c)) { flush(); tokens.push(glyph(c, i)); } else word.push(glyph(c, i));
    });
    flush();
    return (
      <div style={{position: 'absolute', left: sx, top: TITLE_Y + (leaving ? -(1 - p) * U * 0.03 : 0), width: lineW,
        opacity: leaving ? p : 1, color: ink.fg, font: `800 ${titlePx}px/1.15 var(--f-display, system-ui)`,
        letterSpacing: '-0.01em'}}>
        {tokens}
      </div>
    );
  };

  // ── the stage: the film's own ground, lit where the card stands (lighter on a light ground, a soft lift on a dark
  // one — a mix toward white on a dark ground turned the whole top of the frame grey) ──
  const dark = relLum(ink.bg) < 0.18;
  const glow = dark ? mix(ink.bg, ink.fg, 0.1) : mix(ink.bg, '#ffffff', 0.6);
  const rim = dark ? ink.bg : mix(ink.bg, ink.fg, 0.035);
  const shadowTop = Math.min(cy + size.hy * 0.96, zoneBot - U * 0.03);
  return (
    <AbsoluteFill style={{background: `radial-gradient(ellipse 70% 55% at 50% ${((zoneTop + zoneBot) / 2 / H) * 100}%, ` +
      `${glow} 0%, ${ink.bg} 72%, ${rim} 100%)`}}>
      {/* the card's shadow on the floor of the stage */}
      <div style={{position: 'absolute', left: cx - cw * 0.42 * pose.s, top: shadowTop, width: cw * 0.84 * pose.s,
        height: U * 0.04, borderRadius: '50%', background: dark ? '#000000' : mix(ink.fg, ink.bg, 0.6), opacity: dark ? 0.6 : 0.35,
        filter: `blur(${U * 0.028}px)`}} />
      <div style={{position: 'absolute', left: 0, top: 0, width: cw, height: ch, transform, transformOrigin: 'center center',
        borderRadius: r, overflow: 'hidden', background: ink.surface,
        // a shadow is darker than the ground on any ground: a mix toward the ink would be a pale halo on a dark one
        boxShadow: `0 ${U * 0.02}px ${U * 0.06}px ${dark ? 'rgba(0,0,0,0.55)' : mix(ink.fg, ink.bg, 0.75)}, ` +
          `0 0 0 1px ${mix(ink.fg, ink.bg, 0.88)}`}}>
        {fading ? drawFace(faceBefore, 1) : null}
        {drawFace(faceNow, fading ? clamp01((now.morph - 0.42) / 0.16) : 1)}
      </div>
      {outP > 0 ? titleLine(prevTitle, beats[k - 1].props.highlight as string | undefined, outP, true) : null}
      {titleLine(curTitle, now.beat.props.highlight as string | undefined, inP, false)}
    </AbsoluteFill>
  );
};
