// SHOT · Callback — the film's finale gathers what it showed: its own earlier beats come back as cards and settle
// around the closing line, the way a launch event ends with everyone on stage. The claim is "all of that, together":
// a recap you SEE, not one you are told. (Peer: video-shotcraft's outro-group-photo-launch — the film's elements
// assemble around the wordmark — reviewed 2026-11-02.)
//
// The cards are the film's own beats (`beats`, 1-based), each drawn by its own register on its own ground and frozen
// at its settled frame (runtime/teaser, provided by Film.tsx). They fly in from beyond the frame on staggered paths
// (runtime/layoutMorph's morph), land with a small tilt each, and the closing line arrives in the space they leave.
// Standalone — a still, a sweep — each card is a neutral stand-in panel.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutBack, lerp} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useGlide} from '../runtime/glide';
import {useTeaser} from '../runtime/teaser';
import {morph, type Rect} from '../runtime/layoutMorph';

export const DURATION = 180; // 6 s

const h01 = (i: number, s: number) => {
  const x = Math.sin((i + 1) * 12.9898 + s * 78.233) * 43758.5453;
  return x - Math.floor(x);
};

/** Where each of n cards rests: around an ellipse framing the centre, the top and bottom rows first. */
const restAround = (n: number, zone: Rect, cardW: number, cardH: number): Rect[] => {
  const cx = zone.x + zone.w / 2, cy = zone.y + zone.h / 2;
  const rx = (zone.w - cardW) / 2, ry = (zone.h - cardH) / 2;
  return Array.from({length: n}, (_, i) => {
    const a = -Math.PI / 2 + (i + 0.5) * ((2 * Math.PI) / n) + Math.PI / n;   // never dead centre, never one row
    return {x: cx + rx * Math.cos(a) - cardW / 2, y: cy + ry * Math.sin(a) - cardH / 2, w: cardW, h: cardH};
  });
};

export const Callback: React.FC<{beats?: number[]; title?: string; note?: string}> = ({
  beats = [2, 3, 4, 5], title = 'Demo closing line', note = ''} = {}) => {
  if (!Array.isArray(beats) || beats.length < 3 || beats.length > 6) {
    throw new Error(`Callback needs 3-6 \`beats\` (the film's own beats to gather), got ${JSON.stringify(beats)}`);
  }
  if (!String(title ?? '').trim()) throw new Error('Callback needs a `title` — the closing line the cards gather round');
  const dna = useDNA();
  const teaser = useTeaser();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const BG = dna?.bg ?? '#08090c', FG = dna?.fg ?? '#f3f4f7', DIM = dna?.dim ?? '#8a909c', ACC = dna?.accent ?? '#7cc4ff';
  const EDGE = dna?.line ?? '#2a303a';
  const DISPLAY = 'var(--f-display, Inter, system-ui, sans-serif)';

  const top = Math.max(CONTENT_TOP, Math.round(U * 0.06)), bottom = contentBottom(W, H) - Math.round(U * 0.02);
  const zone = {x: Math.round(W * 0.04), y: top, w: Math.round(W * 0.92), h: bottom - top};
  const portrait = H > W;
  const k = portrait ? 0.3 : 0.22;                       // a card is the frame at this scale
  const cardW = W * k, cardH = H * k;
  const rest = restAround(beats.length, zone, cardW, cardH);
  // they come from beyond the frame, each from the side it will rest on
  const start = rest.map((r, i) => {
    const dx = r.x + r.w / 2 - W / 2, dy = r.y + r.h / 2 - H / 2, len = Math.hypot(dx, dy) || 1;
    const far = Math.max(W, H) * (0.75 + 0.2 * h01(i, 1));
    return {x: r.x + (dx / len) * far, y: r.y + (dy / len) * far, w: r.w, h: r.h};
  });
  const fly = seg(t, 0.08, 0.5);
  const rects = morph(start, rest, fly, {stagger: 0.45, arc: 0.12});
  const titleOn = easeOutCubic(clamp01(seg(t, 0.46, 0.62)));
  const noteOn = easeOutCubic(clamp01(seg(t, 0.58, 0.72)));
  // the closing line sits in the space the ring leaves: inside the ellipse, clear of every card
  const innerW = zone.w - 2 * cardW * 0.9, innerTop = zone.y + cardH * 0.9, innerH = zone.h - 2 * cardH * 0.9;
  const titlePx = Math.max(Math.round(U * 0.04), fitTextPx(title, Math.max(innerW, W * 0.3), Math.round(U * 0.085), {usable: 0.95}));
  const notePx = note ? Math.max(Math.round(U * 0.028), fitTextPx(note, Math.max(innerW, W * 0.3), Math.round(U * 0.034))) : 0;

  return (
    <AbsoluteFill style={{background: dna ? `radial-gradient(80% 70% at 50% 50%, ${mix(BG, ACC, 0.1 * titleOn)}, ${BG} 72%)` : BG}}>
      {rects.map((r, i) => {
        const land = clamp01(seg(fly, (0.45 * i) / Math.max(1, beats.length - 1), 1));
        const tilt = lerp((h01(i, 2) - 0.5) * 30, (h01(i, 3) - 0.5) * 7, easeOutBack(land));
        const pic = teaser ? teaser.render(beats[i]) : null;
        return (
          <div key={i} style={{position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, overflow: 'hidden',
            borderRadius: Math.round(U * 0.012), border: `${Math.max(1, Math.round(U * 0.0015))}px solid ${mix(EDGE, FG, 0.25)}`,
            boxShadow: `0 ${Math.round(U * 0.025)}px ${Math.round(U * 0.06)}px #0007`,
            transform: `rotate(${tilt}deg)`, transformOrigin: 'center'}}>
            {pic ? (
              <div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transformOrigin: '0 0',
                transform: `scale(${r.w / W})`}}>{pic}</div>
            ) : (
              <AbsoluteFill style={{background: `linear-gradient(${140 + i * 50}deg, ${mix(BG, ACC, 0.3)}, ${mix(BG, FG, 0.06)})`}} />
            )}
          </div>
        );
      })}
      <div style={{position: 'absolute', left: zone.x + (zone.w - Math.max(innerW, W * 0.3)) / 2, width: Math.max(innerW, W * 0.3),
        top: innerTop, height: innerH, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        opacity: titleOn, transform: glide(`translateY(${(1 - titleOn) * U * 0.015}px)`, true)}}>
        <div style={{color: FG, font: `800 ${titlePx}px/${leading(title, 1.08)} ${DISPLAY}`, textAlign: 'center',
          letterSpacing: '-0.02em', textWrap: 'balance'}}>{title}</div>
        {note ? <div style={{color: mix(DIM, FG, 0.35), opacity: noteOn, marginTop: Math.round(U * 0.018), textAlign: 'center',
          font: `500 ${notePx}px/${leading(note, 1.3)} var(--f-body, Inter, system-ui, sans-serif)`}}>{note}</div> : null}
      </div>
    </AbsoluteFill>
  );
};
export default Callback;
