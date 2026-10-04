// SHOT · Screen + Bubble — Loom language: a light app screen being walked through, with a circular cam
// BUBBLE in the corner (a person narrating) and a cursor demonstrating. Casual, human, light. The picture-
// in-picture + screen choreography is a Remotion-native composite the flat tier doesn't do. Deterministic.
//
// THE SELECTED PAGE AND THE BUTTON ARE THE FILM'S. The sidebar always highlighted `nav[2]` and printed it as
// the page heading, and the button always read "+ New" in English. So a film that listed its own four
// sections got its THIRD one lit and titled as the page being demonstrated — a selection nobody made — and a
// Chinese walkthrough clicked an English button. The button label is `action` now (default '+ New', which
// the demo-copy gate lists when a film omits it; '' draws no button). The highlighted item is `active`, an
// index into `nav`, and like every prop that SELECTS it defaults to none: a film that passes its own `nav`
// without `active` gets an even sidebar and no page heading. The demo keeps its "Deliverables" page only as
// part of the whole demo — `active` falls back to 2 when `nav` itself is the demo list, never when the list
// is the film's. `nav` is 1-6 labels (eight one-line labels fill a 1080px-tall sidebar, and wrapped CJK
// labels fill it at six), and an `active` that names no item throws.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeCursor, easeOutBack, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {leading} from '../runtime/cjkType';
import {textWidthPx} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 165; // 5.5s
const BRAND = '#6C5CE7';

// THE REC DOT IS THE INSTRUMENT DEPICTING ITSELF — a screen recording says it is recording, in the three
// letters every recorder uses, and no film would translate it any more than it would translate the mac
// traffic lights beside it. Everything else a viewer reads here is the FILM's, and now says so.
export const INTRINSIC_TEXT = ['REC'];

export const MAX_NAV = 6;
const DEFAULT_NAV = ['Home', 'Projects', 'Deliverables', 'Team'];
const DEMO_ACTIVE = 2;   // the demo's own page — used only while `nav` is DEFAULT_NAV

export const ScreenBubble: React.FC<{appTitle?: string; nav?: string[]; active?: number | null; action?: string;
  deliverable?: string; note?: string}> = ({
  appTitle = 'workbuddy — untitled', nav: NAV = DEFAULT_NAV, active, action = '+ New',
  deliverable = 'Q3 board deck', note = 'created just now'} = {}) => {
  if (!Array.isArray(NAV) || NAV.length < 1 || NAV.length > MAX_NAV) {
    throw new Error(`ScreenBubble: \`nav\` takes 1-${MAX_NAV} sidebar labels (got ${Array.isArray(NAV) ? NAV.length : typeof NAV}). ` +
      'Eight one-line labels already fill the sidebar of a 1080px-tall window and a label that wraps takes half ' +
      'again as much, so six is the most that always fits — name the sections the walkthrough actually visits.');
  }
  const nav = NAV.map((n, i) => {
    const v = String(n ?? '').trim();
    if (!v) throw new Error(`ScreenBubble: nav item ${i + 1} is empty — every sidebar entry needs a label.`);
    return v;
  });
  // the selection is the film's; the demo's "Deliverables" belongs to the demo list alone
  const sel = active != null ? active : (NAV === DEFAULT_NAV ? DEMO_ACTIVE : null);
  if (sel != null && !(Number.isInteger(sel) && sel >= 0 && sel < nav.length)) {
    throw new Error(`ScreenBubble: \`active\` must be the index (0-${nav.length - 1}) of the nav item being shown, ` +
      `got ${JSON.stringify(active)}. Omit it to highlight nothing.`);
  }
  // LEVEL-C: the app-window chrome follows the DNA → a DARK-MODE app on a dark DNA (window=surface, ink=fg, brand=
  // accent), the original light app on null DNA. The mac traffic-lights + REC dot stay (universal, iconic on both).
  const dna = useDNA();
  const ACC = dna?.accent ?? BRAND, A2 = dna?.accent2 ?? '#EC4899', BG = dna?.bg ?? '#e9ebf2', SURF = dna?.surface ?? '#fff';
  const BAR = dna?.surface ?? '#f6f7fb', LINE = dna?.line ?? '#eef0f6', FG = dna?.fg ?? '#1b2333', DIM = dna?.dim ?? '#6b7180', ON = dna?.onAccent ?? '#fff';
  // per-element originals (a null DNA must be byte-identical to the pre-DNA shot)
  const TITLE_DIM = dna?.dim ?? '#8b90a3', ROW_BG = dna?.surface ?? '#fbfcfe', SUB_DIM = dna?.dim ?? '#98a0b0';
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const SX = 150, SY = 130, SW = W - 300, SH = H - 300;
  // cursor path: rest → the action button (click) → the created block.
  // THE CLICK LANDS ON THE BUTTON. It was aimed at a fixed `SX + 250`, which is inside the SIDEBAR — the cursor
  // clicked the gap between the first two nav items while the ripple played on the button 1200px away, so
  // the frame showed a click on navigation that no film had described. The button is right-aligned in the
  // main column (44px padding, 30px side padding, 32px bold label), so its centre is measured from its label.
  // With no button (`action: ''`) there is nothing to click, and the cursor goes straight to the new row.
  const btnW = 60 + textWidthPx(action, 32, {adv: 0.62});
  const rowPt: [number, number] = [SX + SW * 0.62, SY + 360];
  const clickPt: [number, number] = action ? [SX + SW - 44 - btnW / 2, SY + 66 + 44 + 34] : rowPt;
  const pts: [number, number][] = [[SX + SW * 0.5, SY + SH * 0.7], clickPt, rowPt];
  const seg1 = easeCursor(seg(t, 0.1, 0.34)), seg2 = easeCursor(seg(t, 0.44, 0.7));
  let cx = pts[0][0], cy = pts[0][1];
  if (t < 0.44) {cx = lerp(pts[0][0], pts[1][0], seg1); cy = lerp(pts[0][1], pts[1][1], seg1);}
  else {cx = lerp(pts[1][0], pts[2][0], seg2); cy = lerp(pts[1][1], pts[2][1], seg2);}
  const clicked = Boolean(action) && t > 0.34 && t < 0.44;
  const ripple = clicked ? (t - 0.34) / 0.1 : 0;
  const created = easeOutBack(seg(t, 0.46, 0.7));
  return (
    <AbsoluteFill style={{background: BG}}>
      {/* the app window */}
      <div style={{position: 'absolute', left: SX, top: SY, width: SW, height: SH, background: SURF, borderRadius: 18,
        boxShadow: '0 40px 100px rgba(40,45,80,.22)', overflow: 'hidden'}}>
        <div style={{height: 66, background: BAR, borderBottom: `1px solid ${LINE}`, display: 'flex', alignItems: 'center', gap: 12, padding: '0 26px'}}>
          {['#ff5f57', '#febc2e', '#28c840'].map(c => <div key={c} style={{width: 16, height: 16, borderRadius: 8, background: c}} />)}
          <div style={{marginLeft: 20, font: '600 26px/1 var(--f-body, Inter)', color: TITLE_DIM}}>{appTitle}</div>
        </div>
        <div style={{display: 'flex', height: SH - 66}}>
          <div style={{width: 300, borderRight: `1px solid ${LINE}`, padding: 26, display: 'flex', flexDirection: 'column', gap: 20}}>
            {nav.map((n, i) => <div key={i} style={{padding: '16px 20px', borderRadius: 10,
              background: i === sel ? `${ACC}22` : 'transparent',
              // a nav label wraps on a Chinese film, and `/1` stacks the two lines with no air between them
              font: `${i === sel ? 700 : 500} 30px/${leading(n, 1)} var(--f-body, Inter)`,
              color: i === sel ? ACC : DIM}}>{n}</div>)}
          </div>
          <div style={{flex: 1, padding: 44, position: 'relative'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              {/* no selection, no heading: the page title IS the selected item, so with none there is none */}
              <div style={{font: '800 52px/1 var(--f-body, Inter)', color: FG}}>{sel != null ? nav[sel] : null}</div>
              {action ? (
                <div style={{position: 'relative', padding: '18px 30px', borderRadius: 12, background: ACC, color: ON, font: '700 32px/1 var(--f-body, Inter)', whiteSpace: 'nowrap'}}>{action}
                  {ripple > 0 && <div style={{position: 'absolute', inset: 0, borderRadius: 12, border: `3px solid ${ACC}`, transform: `scale(${1 + ripple})`, opacity: 1 - ripple}} />}
                </div>
              ) : null}
            </div>
            {/* the "created" deliverable row */}
            <div style={{marginTop: 40, opacity: clamp01(created), transform: glide(`translateY(${lerp(24, 0, clamp01(created))}px)`, clamp01(created) !== 1),
              padding: '30px 34px', borderRadius: 14, border: `1px solid ${LINE}`, background: ROW_BG, display: 'flex', alignItems: 'center', gap: 24}}>
              <div style={{width: 54, height: 54, borderRadius: 12, background: `${ACC}22`}} />
              <div><div style={{font: `700 36px/${leading(deliverable, 1)} var(--f-body, Inter)`, color: FG}}>{deliverable}</div>
                <div style={{font: `500 26px/${leading(note, 1)} var(--f-body, Inter)`, color: SUB_DIM, marginTop: 10}}>{note}</div></div>
            </div>
          </div>
        </div>
      </div>
      {/* the cursor */}
      <div style={{position: 'absolute', left: cx, top: cy, filter: 'drop-shadow(0 5px 10px rgba(30,40,80,.3))'}}>
        <svg width="32" height="38" viewBox="0 0 22 26"><path d="M2,2 L2,22 L7,17 L10,24 L13,23 L10,16 L17,16 Z" fill={FG} stroke={BG} strokeWidth="1.6" strokeLinejoin="round" /></svg>
      </div>
      {/* the CAM BUBBLE (person narrating) */}
      <div style={{position: 'absolute', left: 90, top: H - 320, width: 230, height: 230, borderRadius: 115,
        background: `linear-gradient(150deg, ${ACC}, ${A2})`, border: `6px solid ${BG}`, boxShadow: '0 20px 50px rgba(40,45,80,.3)', overflow: 'hidden'}}>
        {/* abstract friendly avatar */}
        <div style={{position: 'absolute', left: 82, top: 46, width: 66, height: 66, borderRadius: 33, background: 'rgba(255,255,255,.9)'}} />
        <div style={{position: 'absolute', left: 48, top: 124, width: 134, height: 120, borderRadius: '60px 60px 0 0', background: 'rgba(255,255,255,.9)'}} />
        <div style={{position: 'absolute', left: 18, top: 18, display: 'flex', alignItems: 'center', gap: 8}}>
          <div style={{width: 14, height: 14, borderRadius: 7, background: '#ff4d4d'}} /><div style={{font: '700 20px/1 var(--f-body, Inter)', color: '#fff'}}>REC</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
export default ScreenBubble;
