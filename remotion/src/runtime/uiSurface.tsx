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
import {fitBlockPx} from './layout';
import {leading} from './cjkType';
import {type DesignDNA} from './dna';

export type UiPage = 'cards' | 'chart' | 'table' | 'form';

export type UiContent = {
  title?: string;        // the window's own title
  nav?: string[];        // sidebar entries
  items?: string[];      // card titles · table rows · form labels, depending on `page`
  series?: number[];     // chart values, PLOTTED AS GIVEN — never generated
};

const PAGES: UiPage[] = ['cards', 'chart', 'table', 'form'];

// THE GEOMETRY IS EXPORTED, because something else has to be able to AIM at it.
//
// A camera that flies to "the third card" needs the third card's rectangle, and there are exactly two ways to
// get one: read it from the component that draws it, or write the number down twice. video-shotcraft solved
// the same problem with a `live-layout.json` sidecar beside a baked screenshot; the honest version here is
// that the drawing and the aiming call ONE function. A second copy of a rectangle is a second answer, and it
// goes stale the first time the padding changes.
export const uiChromeH = (W: number, H: number) =>
  Math.round(Math.max(Math.min(W, H) * 0.075, Math.max(2, Math.round(Math.min(W, H) * 0.022)) * 2.4));
export const uiPad = (W: number) => Math.round(W * 0.030);
export const uiNavW = (W: number, H: number, nav = true) =>
  nav && W > Math.min(W, H) * 0.9 ? Math.round(W * 0.20) : 0;

/** Where the `cards` page puts its six cards, in the surface's own coordinates. */
export const uiCardRects = (W: number, H: number, nav = true, cols = 3, rows = 2) => {
  const pad = uiPad(W), x0 = uiNavW(W, H, nav), y0 = uiChromeH(W, H);
  const bw = W - x0 - pad * 2, bh = H - y0 - pad * 2;
  const cw = (bw - pad * (cols - 1)) / cols, ch = (bh - pad * (rows - 1)) / rows;
  const out: {x: number; y: number; w: number; h: number}[] = [];
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    out.push({x: x0 + pad + c * (cw + pad), y: y0 + pad + r * (ch + pad), w: cw, h: ch});
  }
  return out;
};

// Below this a glyph is a smudge, and a smudge that looks like a word is worse than an honest bar.
const READABLE_PX = 11;

// EVERY LINE THIS FILE SETS GOES THROUGH `leading()`. The leadings were written as literals — `/1` on the
// window title, `/1.2` on a nav entry — which are Latin values, and Han glyphs fill a full em-box: the CJK
// gate reported the chrome title at 18px set solid, tight by 1.1px, and every register drawing a surface
// inherited it at once. `leading()` is a no-op on Latin copy, so there is no cost to always asking.

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
  const pad = uiPad(W);
  const chromeH = uiChromeH(W, H);
  const navW = uiNavW(W, H, nav);
  const inner = {x: navW, y: chromeH, w: W - navW, h: H - chromeH};

  // ONE legibility decision, asked per element and never per shot: `type(px)` returns a real string only when
  // it would clear the floor, so a surface that shrinks degrades element by element instead of all at once.
  const type = (px: number) => px >= READABLE_PX;
  const navPx = Math.round(u * 0.042);
  const rowPx = Math.round(u * 0.040);

  // A WRONG SHAPE SAYS WHAT IT IS. Handed a bare string where a list belongs — which a fixture generator
  // reading a named element type does, because it can see the field and not its type — `.filter` throws from
  // inside this file and the register is reported as "failed to render". The register was fine; the caller
  // passed the wrong thing, and the error should say so.
  const listOf = (v: unknown, prop: string): string[] => {
    if (v == null) return [];
    if (!Array.isArray(v)) {
      throw new Error(`UiSurface: \`content.${prop}\` must be an array of strings, got ` +
        `${typeof v === 'string' ? `the string ${JSON.stringify(v.slice(0, 40))}` : typeof v}.`);
    }
    return v.filter((x) => String(x ?? '').trim());
  };
  const items = listOf(content.items, 'items');
  const navs = listOf(content.nav, 'nav');
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
        <div style={{color: dim, font: `600 ${Math.round(chromeH * 0.42)}px/${leading(content.title ?? '', 1.15)} ${body}`,
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
          <div key={i} style={{color: on ? accent : dim, font: `${on ? 700 : 500} ${navPx}px/${leading(label, 1.2)} ${body}`,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{label}</div>
        ) : <Bar key={i} w={wid(i, navW * 0.42, navW * 0.78)} h={barH} c={on ? accent : dim} o={on ? 0.9 : 0.4} />;
      })}
    </div>
  ) : null;

  // Drawn from `uiCardRects`, absolutely, rather than from a CSS grid — the grid produces the same picture
  // and produces it somewhere only the browser knows, which is no use to a camera that has to fly to card 3.
  const Cards = (() => {
    const rects = uiCardRects(W, H, !!navW);
    // ONE SIZE, FITTED TO THE CARD. A fixed size is a bet that every label is short, and Chinese calls it:
    // «规划执行步骤并调用工具» ran straight out of its card and printed across «自动拆解任务» in the next one —
    // two features rendered as one run of glyphs. Fitted per card instead, six cards print at five sizes.
    // The title gets a DECLARED share of the card and is fitted to it. Two things were wrong the first time,
    // and the Chinese render showed both at once — «规划执行步骤并调用工具» came out as «规划执行/步骤并调»,
    // a feature name cut off mid-phrase:
    //   * `usable: 1.0` threw away the margin that exists because the face which actually renders is the
    //     DNA's, not the fallback stack this file names. layout.ts says so in as many words.
    //   * the card had no budget for its title at all — the bars below it are laid out at their natural
    //     size, so a two-line heading simply pushed itself under the card's own `overflow: hidden`.
    // Now the title's box is stated, the filler yields to it, and the size comes down until the whole label
    // is inside. A label that is shown at all is shown whole.
    const innerH = rects[0].h - Math.round(pad * 0.7) * 2;
    const titleBox = {w: rects[0].w - Math.round(pad * 0.7) * 2, h: Math.round(innerH * 0.34)};
    const cardPx = items.slice(0, rects.length).reduce(
      (px, txt) => Math.min(px, fitBlockPx(txt, titleBox.w, titleBox.h, Math.round(u * 0.048),
        {usable: 0.92, leading: 1.15})),
      Math.round(u * 0.048));
    return (
    <>
      {rects.map((r, i) => {
        const label = items[i];
        return (
          <div key={i} style={{position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h,
            border: `${bw}px solid ${line}`, borderRadius: Math.round(radius * 0.6),
            padding: Math.round(pad * 0.7), boxSizing: 'border-box',
            display: 'flex', flexDirection: 'column', gap: Math.round(barH * 1.1),
            // THE TINT GOES ON THE FILL, NOT ON THE ELEMENT. `opacity: 0.14` fades the card's own TITLE with
            // it, so the one card a shot has selected is the one card you cannot read — the highlight erasing
            // exactly what it was highlighting.
            background: i === 0 ? `${accent}22` : 'transparent'}}>
            {label && type(cardPx) ? (
              <div style={{color: fg, font: `700 ${cardPx}px/${leading(label, 1.15)} ${body}`, flex: '0 0 auto',
                maxHeight: titleBox.h, overflow: 'hidden',
                // a CJK line breaks between any two glyphs, so a label a unit too wide drops one onto a
                // line of its own; balancing spreads the overflow instead of orphaning it
                textWrap: 'balance'}}>{label}</div>
            ) : <Bar w={wid(i, r.w * 0.30, r.w * 0.62)} h={barH} c={fg} o={0.7} />}
            <Bar w={wid(i + 9, r.w * 0.24, r.w * 0.52)} h={barH} c={dim} o={0.35} />
            {/* A card that a camera can fly INTO has to survive being looked at. Title-and-one-bar reads as a
                finished tile at overview scale and as an empty box in close-up, which is the moment the shot
                is asking the viewer to lean in. Three ranged rules are texture from far away and lines of
                content up close — and they claim nothing, which a made-up number would. */}
            {/* the filler YIELDS: it is what a longer heading takes its room from, not the other way round */}
            <div style={{marginTop: Math.round(barH * 1.4), display: 'flex', flexDirection: 'column',
              gap: Math.round(barH * 1.1), flex: '1 1 auto', minHeight: 0, overflow: 'hidden'}}>
              {[0, 1, 2].map((k) => (
                <Bar key={k} w={wid(i * 3 + k + 21, r.w * 0.34, r.w * 0.80)} h={barH} c={dim} o={0.22} />
              ))}
            </div>
          </div>
        );
      })}
    </>
    );
  })();

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
              <div style={{flex: 1, color: fg, font: `500 ${rowPx}px/${leading(label, 1.2)} ${body}`, whiteSpace: 'nowrap',
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
