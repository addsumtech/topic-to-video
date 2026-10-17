// TITLE PROBE — where does each beat put its title? Asked of the DOM, one settled frame per beat, so a film's
// titles can be compared beat to beat (scripts/text_safe_qa.py `title_repetition`).
//
// WHY THIS IS NOT IN textSafe.tsx. The first version read "the frame's largest visible type" inside the text-safety
// walk. On the GPS film the largest type was the title; on the compound-interest test (2026-10-17) it was the
// printed figures — 1,000, 2,593.74, 18% — while the real titles sat top-left on 9 of 11 beats, and the check said
// nothing. Fixing it there was not an option: textSafe.tsx is imported (through runtime/glide) by most registers,
// and the library's measurements hash every runtime module a register imports, so one edit there would mark the
// whole catalogue stale behind a multi-hour re-sweep. This file is imported only by Root.tsx's audit wiring.
// The three helpers below are small copies of textSafe's private ones for the same reason.
//
// WHAT IS A TITLE HERE. The largest visible text that is not a READOUT: a figure with at most two letters around it
// ("1,050", "18%", "2,000 美元") is data, however large. Its x is the edge the line is SET FROM — the left edge of a
// left-aligned line, the right edge of a right-aligned one, the centre of a centred one — so a long left-aligned
// title is not read as centred because it happens to reach the middle of the frame.

import React from 'react';
import {cancelRender, continueRender, delayRender} from 'remotion';
import {renderedPx} from './textSafe';

export const TITLE_PROBE_TAG = 'TITLE-PROBE ';
// ANY script's letters. A Latin+CJK class read every Cyrillic, Greek, Arabic, Devanagari and Thai title as a
// "readout" (fewer than two letters), so on those films the title check found no titles and never fired.
const LETTER = /\p{L}/gu;

export const isReadout = (text: string): boolean => {
  const letters = (text.match(LETTER) || []).length;
  return letters < 2 || (/\d/.test(text) && letters <= 2);
};

const ownText = (el: Element): string => {
  let s = '';
  el.childNodes.forEach((n) => { if (n.nodeType === 3) s += n.textContent ?? ''; });
  return s.trim();
};

const opacityOf = (el: Element, win: Window): number => {
  let o = 1;
  for (let n: Element | null = el; n; n = n.parentElement) o *= parseFloat(win.getComputedStyle(n).opacity || '1');
  return o;
};

const inkBox = (el: Element): DOMRect | null => {
  const doc = el.ownerDocument;
  const rects: DOMRect[] = [];
  el.childNodes.forEach((n) => {
    if (n.nodeType !== 3 || !(n.textContent ?? '').trim() || !doc?.createRange) return;
    const range = doc.createRange();
    range.selectNodeContents(n);
    Array.from(range.getClientRects()).forEach((r) => { if (r.width > 0 && r.height > 0) rects.push(r as DOMRect); });
  });
  if (!rects.length) {
    const b = el.getBoundingClientRect();
    return b.width > 0 && b.height > 0 ? b : null;
  }
  const l = Math.min(...rects.map((r) => r.left)), t = Math.min(...rects.map((r) => r.top));
  return new DOMRect(l, t, Math.max(...rects.map((r) => r.right)) - l, Math.max(...rects.map((r) => r.bottom)) - t);
};

const visible = (el: Element, win: Window): boolean => {
  for (let n: Element | null = el; n; n = n.parentElement) {
    const cs = win.getComputedStyle(n);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
  }
  return true;
};

export type TitleRecord = {text: string; ax: number; cy: number; px: number; align: string};

export const pickTitle = (root: Element, frame: DOMRect): TitleRecord | null => {
  const win = root.ownerDocument?.defaultView;
  if (!win) return null;
  let best: {text: string; px: number; r: DOMRect; align: string} | null = null;
  root.querySelectorAll('*').forEach((el) => {
    const text = ownText(el);
    if (!text || isReadout(text) || el.closest?.('[data-echo]')) return;
    if (!visible(el, win) || opacityOf(el, win) < 0.5) return;
    const r = inkBox(el);
    if (!r || r.right <= frame.left || r.left >= frame.right || r.bottom <= frame.top || r.top >= frame.bottom) return;
    const cs = win.getComputedStyle(el);
    const px = renderedPx(el, cs);
    if (!best || px > best.px + 0.5 || (Math.abs(px - best.px) <= 0.5 && r.top < best.r.top)) {
      const a = (cs.textAlign || 'left').toLowerCase();
      const rtl = cs.direction === 'rtl';
      const align = a === 'center' || a === '-webkit-center' ? 'center'
        : a === 'right' || (a === 'end' && !rtl) || (a === 'start' && rtl) ? 'right' : 'left';
      best = {text, px, r, align};
    }
  });
  if (!best) return null;
  const b = best as {text: string; px: number; r: DOMRect; align: string};
  const x = b.align === 'left' ? b.r.left : b.align === 'right' ? b.r.right : (b.r.left + b.r.right) / 2;
  const round = (v: number) => Math.round(v * 1000) / 1000;
  return {text: b.text.length > 48 ? b.text.slice(0, 48) + '…' : b.text,
          ax: round((x - frame.left) / frame.width), cy: round(((b.r.top + b.r.bottom) / 2 - frame.top) / frame.height),
          px: Math.round(b.px), align: b.align};
};

/** Armed by `titleProbe: true` on a beat's props (Root.tsx): measures the settled frame and cancels with the record. */
export const TitleProbe: React.FC = () => {
  const ref = React.useRef<HTMLDivElement>(null);
  const [handle] = React.useState(() => delayRender('title probe', {timeoutInMilliseconds: 60000}));
  React.useEffect(() => {
    let dead = false;
    (async () => {
      try { await (document as unknown as {fonts?: {ready: Promise<unknown>}}).fonts?.ready; } catch { /* lays out */ }
      await new Promise((res) => requestAnimationFrame(() => res(null)));
      if (dead) return;
      const host = ref.current;
      if (!host) { continueRender(handle); return; }
      cancelRender(new Error(TITLE_PROBE_TAG + JSON.stringify(pickTitle(host.ownerDocument.body,
        host.getBoundingClientRect()))));
    })();
    return () => { dead = true; };
  }, [handle]);
  return <div ref={ref} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}} />;
};

// A frame built to fool the old reading: a huge figure, a long LEFT-aligned title that reaches past the middle, and a
// small label. The title is the sentence, set from the left.
export const TitleProbeFixture: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, background: '#f3f0e6', color: '#1c1f24',
    font: '700 64px/1.2 var(--f-body, Inter, system-ui, sans-serif)'}}>
    <div style={{position: 'absolute', left: 110, top: 70, width: 1500, textAlign: 'left'}}>
      THE SECOND YEAR EARNS INTEREST ON 1,050 NOT 1,000</div>
    <div style={{position: 'absolute', left: 600, top: 380, fontSize: 220}}>2,593.74</div>
    <div style={{position: 'absolute', left: 120, top: 700, fontSize: 30, fontWeight: 400}}>a small label</div>
  </div>
);
