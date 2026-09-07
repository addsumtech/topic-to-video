// THE PRODUCT ITSELF, AS FURNITURE — an application window a shot can put on screen.
//
// WHY THIS EXISTS. A library of 155 registers could draw a beautiful abstraction OF a piece of software and
// could not show one: grep every shot for a sidebar and you get nothing, and the only window chrome in the
// whole runtime is a terminal. That is a SUBJECT gap, not a technique one — no amount of camera work, easing
// or WebGL makes a product film out of a library with no product in it, which is why "we have optimised the
// renderer for months and still cannot shoot this" was the right complaint and had the wrong diagnosis.
//
// WHAT IT IS NOT. It is not a wireframe generator. A grey-bar mock carries no meaning, and this library's own
// rule is that every element on the frame must be decodable in about a second — a shot made of anonymous bars
// fails that by construction. So the surface takes CONTENT: the real nav, the real card titles, the real rows
// of the topic being filmed. Bars are what it falls back to, per element, only where the box is too small for
// type to be read at all.
//
// THAT FALLBACK IS THE POINT, and it is a size rule rather than a taste one. The same surface has to hold up
// filling the frame in a hero shot and 250px wide as one card in a carousel; at 250px a real label is four
// unreadable pixels tall, and drawing it anyway is worse than a bar because it LOOKS like information. So
// each element asks whether its own type would clear a legibility floor and draws a bar when it would not.
//
// NO INVENTED DATA, EVER. The chart plots `series` exactly as given and draws no axis when given none; the
// table and the cards print `items` and nothing else. A surface that made its own numbers up would be a
// fabricated statistic with a chrome bar on top, and it would pass every gate in this repo.

import React from 'react';
import {hash01} from './motion';
import {type DesignDNA} from './dna';

export type UiPage = 'cards' | 'chart' | 'table' | 'form';

export type UiContent = {
  title?: string;        // the window's own title
  nav?: string[];        // sidebar entries
  items?: string[];      // card titles · table rows · form labels, depending on `page`
  series?: number[];     // chart values, PLOTTED AS GIVEN — never generated
};

const PAGES: UiPage[] = ['cards', 'chart', 'table', 'form'];

// Below this a glyph is a smudge, and a smudge that looks like a word is worse than an honest bar.
const READABLE_PX = 11;

// The fallback world, for a standalone preview with no DNA. The surface is separated from the ground on
// PURPOSE and by a measurable amount: the first pass put a #f7f8fa window on a #f2f3f5 page, which is a
// window you can only find because you know it is there — measured ink came out at a third of the library's
// floor, and the picture agreed with the number.
const D = {
  surface: '#ffffff', border: '#c9d0dc', line: '#e2e6ee',
  fg: '#1c2029', dim: '#7b8494', accent: '#5b6b86', chrome: '#f3f5f9',
};

/** A stand-in for one line of type: same footprint, no false claim to be readable. */
const Bar: React.FC<{w: number; h: number; c: string; o?: number; r?: number}> = ({w, h, c, o = 1, r}) => (
  <div style={{width: w, height: h, background: c, opacity: o, borderRadius: r ?? Math.min(h / 2, 3)}} />
);

export const UiSurface: React.FC<{
  page: UiPage;
  W: number;
  H: number;
  dna?: DesignDNA | null;
  content?: UiContent;
  seed?: number;
  nav?: boolean;
}> = ({page, W, H, dna, content = {}, seed = 0, nav = true}) => {
  if (!PAGES.includes(page)) {
    throw new Error(`UiSurface: unknown page "${page}" — expected one of ${PAGES.join(', ')}.`);
  }
  if (!(W > 0 && H > 0 && isFinite(W) && isFinite(H))) {
    throw new Error(`UiSurface: needs a real box, got ${W}x${H}. A surface sized from an unresolved layout ` +
      'collapses to nothing and reads as a missing panel rather than as the bug it is.');
  }
  const surface = dna?.surface ?? D.surface;
  const border = dna?.surfaceBorder ?? D.border;
  const line = dna?.line ?? D.line;
  const fg = dna?.fg ?? D.fg;
  const dim = dna?.dim ?? D.dim;
  const accent = dna?.accent ?? D.accent;
  const radius = Math.min(dna?.radius ?? 10, Math.round(Math.min(W, H) * 0.06));
  const bw = dna?.borderWidth ?? 1;
  const body = dna?.fontBody ?? 'var(--f-body, system-ui, sans-serif)';

  const u = Math.min(W, H);
  const barH = Math.max(2, Math.round(u * 0.022));
  const pad = Math.round(W * 0.030);
  const chromeH = Math.round(Math.max(u * 0.075, barH * 2.4));
  const navW = nav && W > u * 0.9 ? Math.round(W * 0.20) : 0;
  const inner = {x: navW, y: chromeH, w: W - navW, h: H - chromeH};

  // ONE legibility decision, asked per element and never per shot: `type(px)` returns a real string only when
  // it would clear the floor, so a surface that shrinks degrades element by element instead of all at once.
  const type = (px: number) => px >= READABLE_PX;
  const navPx = Math.round(u * 0.042);
  const cardPx = Math.round(u * 0.048);
  const rowPx = Math.round(u * 0.040);

  const items = (content.items ?? []).filter((x) => String(x ?? '').trim());
  const navs = (content.nav ?? []).filter((x) => String(x ?? '').trim());
  const wid = (i: number, lo: number, hi: number) => Math.round(lo + hash01(seed * 31 + i) * (hi - lo));

  const Chrome = (
    <div style={{position: 'absolute', left: 0, top: 0, width: W, height: chromeH, background: dna?.bg ?? D.chrome,
      borderBottom: `${bw}px solid ${line}`, display: 'flex', alignItems: 'center',
      gap: Math.round(chromeH * 0.16), paddingLeft: pad, paddingRight: pad, boxSizing: 'border-box'}}>
      {[0, 1, 2].map((i) => (
        <div key={i} style={{width: Math.max(3, Math.round(chromeH * 0.17)), height: Math.max(3, Math.round(chromeH * 0.17)),
          borderRadius: '50%', background: dim, opacity: 0.35 + i * 0.06}} />
      ))}
      <div style={{flex: 1}} />
      {content.title && type(Math.round(chromeH * 0.42)) ? (
        <div style={{color: dim, font: `600 ${Math.round(chromeH * 0.42)}px/1 ${body}`,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: W * 0.5}}>
          {content.title}</div>
      ) : <Bar w={Math.round(W * 0.16)} h={barH} c={dim} o={0.35} />}
      <div style={{flex: 1}} />
    </div>
  );

  const Nav = navW ? (
    <div style={{position: 'absolute', left: 0, top: chromeH, width: navW, height: H - chromeH,
      borderRight: `${bw}px solid ${line}`, padding: pad, boxSizing: 'border-box',
      display: 'flex', flexDirection: 'column', gap: Math.round(u * 0.030)}}>
      {Array.from({length: 6}).map((_, i) => {
        const label = navs[i];
        const on = i === 1;
        return label && type(navPx) ? (
          <div key={i} style={{color: on ? accent : dim, font: `${on ? 700 : 500} ${navPx}px/1.2 ${body}`,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{label}</div>
        ) : <Bar key={i} w={wid(i, navW * 0.42, navW * 0.78)} h={barH} c={on ? accent : dim} o={on ? 0.9 : 0.4} />;
      })}
    </div>
  ) : null;

  const Cards = (
    <div style={{position: 'absolute', left: inner.x + pad, top: inner.y + pad,
      width: inner.w - pad * 2, height: inner.h - pad * 2,
      // the grid FILLS its page. Sized to its content it left the bottom half of every window empty, which
      // reads as a page that failed to load rather than as a product with six things on it.
      display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gridTemplateRows: 'repeat(2, 1fr)', gap: pad}}>
      {Array.from({length: 6}).map((_, i) => {
        const label = items[i];
        return (
          <div key={i} style={{border: `${bw}px solid ${line}`, borderRadius: Math.round(radius * 0.6),
            padding: Math.round(pad * 0.7), display: 'flex', flexDirection: 'column',
            gap: Math.round(barH * 0.9), justifyContent: 'flex-start',
            background: i === 0 ? accent : 'transparent', opacity: i === 0 ? 0.14 : 1}}>
            {label && type(cardPx) ? (
              <div style={{color: fg, font: `700 ${cardPx}px/1.2 ${body}`, overflow: 'hidden'}}>{label}</div>
            ) : <Bar w={wid(i, inner.w * 0.10, inner.w * 0.20)} h={barH} c={fg} o={0.7} />}
            <Bar w={wid(i + 9, inner.w * 0.08, inner.w * 0.17)} h={barH} c={dim} o={0.35} />
          </div>
        );
      })}
    </div>
  );

  // The chart plots what it is given and nothing else. With no `series` it draws the SHAPE of a chart — a
  // baseline and a grid — and no line, because a curve with no data behind it is a claim about a trend.
  const Chart = (() => {
    const box = {x: inner.x + pad, y: inner.y + pad, w: inner.w - pad * 2, h: inner.h - pad * 2};
    const s = (content.series ?? []).filter((v) => typeof v === 'number' && isFinite(v));
    const lo = Math.min(...s), hi = Math.max(...s), rng = hi - lo || 1;
    const pts = s.map((v, i) => [box.x + (i / Math.max(1, s.length - 1)) * box.w,
                                 box.y + box.h * 0.92 - ((v - lo) / rng) * box.h * 0.78]);
    return (
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1={box.x} x2={box.x + box.w} y1={box.y + box.h * f} y2={box.y + box.h * f}
            stroke={line} strokeWidth={bw} />
        ))}
        <line x1={box.x} x2={box.x + box.w} y1={box.y + box.h * 0.92} y2={box.y + box.h * 0.92}
          stroke={dim} strokeWidth={bw} opacity={0.5} />
        {pts.length > 1 ? (
          <polyline fill="none" stroke={accent} strokeWidth={Math.max(1.5, u * 0.010)}
            strokeLinejoin="round" strokeLinecap="round" points={pts.map((p) => p.join(',')).join(' ')} />
        ) : null}
      </svg>
    );
  })();

  const Rows = (
    <div style={{position: 'absolute', left: inner.x + pad, top: inner.y + pad,
      width: inner.w - pad * 2, height: inner.h - pad * 2,
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between'}}>
      {Array.from({length: 7}).map((_, i) => {
        const label = items[i];
        const isForm = page === 'form';
        return (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: pad,
            borderBottom: isForm ? 'none' : `${bw}px solid ${line}`, paddingBottom: Math.round(u * 0.018)}}>
            {label && type(rowPx) ? (
              <div style={{flex: 1, color: fg, font: `500 ${rowPx}px/1.2 ${body}`, whiteSpace: 'nowrap',
                overflow: 'hidden', textOverflow: 'ellipsis'}}>{label}</div>
            ) : <div style={{flex: 1}}><Bar w={wid(i, inner.w * 0.22, inner.w * 0.55)} h={barH} c={fg} o={0.6} /></div>}
            {isForm ? (
              <div style={{width: Math.round(u * 0.11), height: Math.round(u * 0.058), borderRadius: 999,
                background: i % 3 === 0 ? accent : dim, opacity: i % 3 === 0 ? 0.85 : 0.28,
                display: 'flex', alignItems: 'center', justifyContent: i % 3 === 0 ? 'flex-end' : 'flex-start',
                padding: Math.max(1, Math.round(u * 0.008)), boxSizing: 'border-box'}}>
                <div style={{width: Math.round(u * 0.042), height: Math.round(u * 0.042), borderRadius: '50%',
                  background: surface}} />
              </div>
            ) : (
              <Bar w={Math.round(inner.w * 0.10)} h={barH} c={i % 4 === 0 ? accent : dim}
                o={i % 4 === 0 ? 0.85 : 0.32} />
            )}
          </div>
        );
      })}
    </div>
  );

  return (
    // A WINDOW IS AN OBJECT ON A SURFACE, and a shadow is how a photograph says so. Without one the panel is a
    // rectangle painted on the page: on a light ground it disappears into it, and on a dark one it reads as a
    // hole. The shadow does the separating so the colours do not have to fight for it.
    <div style={{position: 'relative', width: W, height: H, background: surface,
      border: `${bw}px solid ${border}`, borderRadius: radius, overflow: 'hidden', boxSizing: 'border-box',
      boxShadow: `0 ${Math.round(u * 0.035)}px ${Math.round(u * 0.09)}px rgba(12,16,24,.16),`
        + ` 0 ${Math.round(u * 0.006)}px ${Math.round(u * 0.014)}px rgba(12,16,24,.10)`}}>
      {Chrome}
      {Nav}
      {page === 'cards' ? Cards : page === 'chart' ? Chart : Rows}
    </div>
  );
};

export default UiSurface;
