// SHOT · SharedBlindspot — CORRELATED vs INDEPENDENT failure, drawn on one field of cases.
//
// The argument this register encodes: when two producers come from the SAME source their mistakes are
// correlated — their blind areas COINCIDE, so the field keeps ONE shared hole that neither of them can see.
// Two INDEPENDENT sources go blind in different places, so each one's blind area is covered by the other and
// the field ends up with no hole at all.
//
// The encoding (hide the caption and the frame still says exactly this, and only this): one field of small
// case-marks per group, with each producer's BLIND AREA laid over it as a ring — solid = producer `a`,
// dashed = producer `b`, both in the DNA's warning accent because a ring is where that producer sees nothing.
//   · a case inside exactly ONE ring is still caught by the other producer  -> it LIGHTS UP in dna.accent
//   · a case inside BOTH rings is caught by nobody                          -> it becomes an EMPTY outline,
//     and the lens where the two rings overlap fills with the warning accent — the shared hole.
// Left panel: the two rings sit almost on top of each other -> one amber hole full of empty marks.
// Right panel: the rings sit apart -> their overlap is empty, so every mark stays lit.
//
// Topic-agnostic by construction: every word on screen arrives through props, every colour comes from the
// Design DNA (with *_D0 fallbacks for an un-themed film), every position is a pure function of hash01(index)
// and useT — no Math.random, no Date. Lays out side-by-side in landscape and STACKS in portrait.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutExpo, hash01} from '../runtime/motion';
import {useDNA, dnaHas, mix} from '../runtime/dna';
import {TITLE_Y, CONTENT_TOP, contentBottom} from '../runtime/layout';
import {fitTextOnNLines, measureText} from '@remotion/layout-utils';

export const DURATION = 150; // 5s

// ── no-DNA fallbacks (this shot's own identity when no film provides a Design DNA) ─────────────────────────
const BG_D0 = 'radial-gradient(120% 110% at 50% 0%, #13202c, #080d13 74%)';
const GROUND_D0 = '#0a0f16';
const FG_D0 = '#e8eef6';
const DIM_D0 = '#7d8a9b';
const OK_D0 = '#3ddc97';
const WARN_D0 = '#f2b544';
const SURF_D0 = '#111823';
const EDGE_D0 = '#22303f';
const LINE_D0 = '#1a2431';

export type BlindGroup = {label?: string; a?: string; b?: string; note?: string};

// Blind-area centres, in FIELD fractions. `shared` = the two blind areas coincide (a big overlap);
// `indep` = they land in different places (no overlap at all). Radius is a fraction of the field's short side.
const REG_SHARED = [{cx: 0.42, cy: 0.46}, {cx: 0.51, cy: 0.55}];
const REG_INDEP = [{cx: 0.25, cy: 0.36}, {cx: 0.75, cy: 0.62}];
const R_FRAC = 0.30;

export const SharedBlindspot: React.FC<{
  kicker?: string;
  title?: string;
  shared?: BlindGroup;
  independent?: BlindGroup;
  cases?: number;
}> = ({
  kicker: KICKER = 'Correlated vs independent',
  title: TITLE = 'Two checks from one source share one blind spot',
  shared: SHARED = {label: 'One source', a: 'The draft', b: 'Its own review',
    note: 'both go blind on the same cases'},
  independent: INDEP = {label: 'Two sources', a: 'The draft', b: 'An outside review',
    note: 'their blind areas do not line up'},
  cases: CASES = 140,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const t = useT();
  const dna = useDNA();

  // ── every colour from the DNA ──────────────────────────────────────────────────────────────────────────
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const GROUND = dna?.bg ?? GROUND_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const OK = dna?.accent ?? OK_D0;         // covered / caught
  const WARN = dna?.accent2 ?? WARN_D0;    // blind / missed
  const SURF = dna?.surface ?? SURF_D0;
  const EDGE = dna?.surfaceBorder ?? EDGE_D0;
  const LINE = dna?.line ?? LINE_D0;
  const RAD = dna?.radius ?? 8;
  const disp = dna?.fontDisplay ?? 'Inter, "PingFang SC", "Hiragino Sans", "Noto Sans CJK SC", system-ui, sans-serif';
  const mono = dna?.fontMono ?? '"JetBrains Mono", "PingFang SC", "Hiragino Sans", "Noto Sans CJK SC", ui-monospace, monospace';
  const track = dna?.labelSpacing ?? '0.1em';
  const upper = dna?.uppercaseLabels ?? false;
  const gridCue = dnaHas(dna, 'grid');
  const QUIET = mix(DIM, OK, 0.4);         // a case nobody is blind on — present, but not the story

  const portrait = W < H;
  const CB = contentBottom(W, H);

  // ── copy, flattened to primitives so the measuring memo has stable deps ─────────────────────────────────
  const sL = SHARED?.label ?? '', sA = SHARED?.a ?? '', sB = SHARED?.b ?? '', sN = SHARED?.note ?? '';
  const iL = INDEP?.label ?? '', iA = INDEP?.a ?? '', iB = INDEP?.b ?? '', iN = INDEP?.note ?? '';

  // THE LABEL FLOOR — 30 px at 1080 (the short side). Every piece of copy this register sets (kicker, title, group
  // label, producer names, note) is drawn at or above it: the kicker was 20 px (13 px at 1:1), the producer
  // names 23 px, the notes 22 px, and the fits below used to SHRINK them with the panel. A string that does not
  // fit its box at the floor now WRAPS (or, for the two producer names, stacks) instead of getting smaller.
  const FLOOR = Math.round(Math.min(W, H) * 0.0278);

  // ── title band: fit the REAL string, and reserve only the lines it actually needs ───────────────────────
  const titleBox = W * 0.84;
  const type = React.useMemo(() => {
    const fit1 = (txt: string, box: number, lines: number, cap: number, family: string, weight: number) =>
      fitTextOnNLines({
        text: txt && txt.length ? txt : ' ', maxLines: Math.max(1, lines),
        maxBoxWidth: Math.max(24, box), fontFamily: family, fontWeight: weight,
        maxFontSize: Math.max(8, cap),
      }).fontSize;
    const linesOf = (txt: string, size: number, family: string, weight: number, box: number, cap: number) => {
      if (!txt) return 1;
      const w = measureText({text: txt, fontFamily: family, fontSize: size, fontWeight: weight}).width;
      return Math.max(1, Math.min(cap, Math.ceil(w / Math.max(24, box))));
    };
    let tSize = fit1(TITLE, titleBox, 2, 40, disp, 700);
    let tLines = linesOf(TITLE, tSize, disp, 700, titleBox, 2);
    if (tSize < FLOOR) { tSize = FLOOR; tLines = linesOf(TITLE, tSize, disp, 700, titleBox, 3); }   // wrap, never shrink
    return {tSize, tLines, fit1, linesOf};
  }, [TITLE, titleBox, disp, FLOOR]);

  const titleH = type.tSize * 1.16 * type.tLines;
  const kickSize = FLOOR;
  const kickTop = Math.max(44, Math.round(TITLE_Y - kickSize * 1.2 - 8));

  // ── the two panels ─────────────────────────────────────────────────────────────────────────────────────
  const zoneTop = Math.max(CONTENT_TOP, Math.round(TITLE_Y + titleH + H * 0.024));
  const zoneBot = Math.round(CB - H * 0.018);                      // never touches the burned-caption band
  const mx = Math.max(Math.round(W * 0.05), Math.round(Math.min(W, H) * 0.05));   // clears the action-safe border
  const gap = Math.round(portrait ? H * 0.018 : W * 0.028);
  const pw = portrait ? W - 2 * mx : Math.round((W - 2 * mx - gap) / 2);
  const ph = Math.max(120, portrait ? Math.round((zoneBot - zoneTop - gap) / 2) : zoneBot - zoneTop);
  const panelXY = (i: number) => (portrait
    ? {x: mx, y: zoneTop + i * (ph + gap)}
    : {x: mx + i * (pw + gap), y: zoneTop});

  const P = Math.max(14, Math.round(Math.min(pw, ph) * 0.05));     // panel padding

  // ONE size per role across BOTH panels — they are peers being compared, so they must be typographically
  // identical; fitting each on its own would render the same kind of statement at two different sizes.
  const sizes = React.useMemo(() => {
    const {fit1, linesOf} = type;
    const labelBox = pw - 2 * P - 22;
    const labelCap = Math.max(FLOOR, Math.min(32, pw * 0.05));
    let labelSize = Math.min(fit1(sL, labelBox, 1, labelCap, disp, 700),
      fit1(iL, labelBox, 1, labelCap, disp, 700));
    let labelLines = 1;
    if (labelSize < FLOOR) {
      labelLines = 2;
      labelSize = Math.max(FLOOR, Math.min(fit1(sL, labelBox, 2, labelCap, disp, 700),
        fit1(iL, labelBox, 2, labelCap, disp, 700)));
    }
    const swW = Math.round(Math.min(36, Math.max(18, pw * 0.045)));
    // THE TWO PRODUCER NAMES sit side by side while the widest of the four fits its half of the panel at the
    // floor, and STACK (one per row, the whole panel width) when it does not — they used to be fitted down to
    // whatever the half allowed (23 px, 13 px on a narrow panel). A name that still does not fit one row wraps.
    const chipSize = FLOOR;
    const names = [sA, sB, iA, iB];
    const boxSide = (pw - 2 * P - 18) / 2 - swW - 12;
    const boxCol = pw - 2 * P - swW - 12;
    const widest = Math.max(0, ...names.map((n) => (n ? measureText({text: n, fontFamily: mono, fontSize: chipSize,
      fontWeight: 600}).width : 0)));
    const chipCols = widest * 1.04 <= boxSide ? 2 : 1;
    const chipBox = chipCols === 2 ? boxSide : boxCol;
    const chipLines = Math.max(1, ...names.map((n) => linesOf(n, chipSize, mono, 600, chipBox * 0.94, 2)));
    const chipRows = chipCols === 2 ? 1 : 2;
    const noteBox = pw - 2 * P - 16;
    const noteSize = FLOOR;
    const noteLines = Math.max(linesOf(sN, noteSize, mono, 500, noteBox * 0.94, 3),
      linesOf(iN, noteSize, mono, 500, noteBox * 0.94, 3));
    return {labelSize, labelLines, chipSize, chipLines, chipCols, chipRows, swW, noteSize, noteLines};
  }, [type, pw, P, sL, iL, sA, sB, iA, iB, sN, iN, disp, mono, FLOOR]);

  const labelH = Math.round(sizes.labelSize * 1.3 * sizes.labelLines);
  const CHIP_ROW_GAP = 8;
  const chipH = Math.round(sizes.chipSize * 1.32 * sizes.chipLines * sizes.chipRows + 6 + (sizes.chipRows - 1) * CHIP_ROW_GAP);
  const noteH = Math.round(sizes.noteSize * 1.42 * sizes.noteLines);
  const headGap = Math.round(P * 0.36);
  const headH = labelH + headGap + chipH;
  const fy0 = P + headH + Math.round(P * 0.55);                    // field top, relative to the panel
  const fwd = pw - 2 * P;
  const fhd = Math.max(60, ph - fy0 - noteH - Math.round(P * 0.6) - P);

  // ── the field of cases ─────────────────────────────────────────────────────────────────────────────────
  const nCases = Math.max(40, Math.min(260, Math.round(CASES)));
  const cols = Math.max(8, Math.min(18, Math.round(Math.sqrt(nCases * (fwd / fhd)))));
  const rows = Math.max(5, Math.min(14, Math.round(nCases / cols)));
  const pxx = fwd / cols, pxy = fhd / rows;
  const pitch = Math.min(pxx, pxy);
  const rr = R_FRAC * Math.min(fwd, fhd);
  const quietS = pitch * 0.30, bigS = pitch * 0.46;
  const sw = Math.max(2.2, Math.min(4, pw * 0.004));

  // ── timing (pure fn of useT, so meta.reduced_motion freezes on a fully-resolved frame) ──────────────────
  const tIn = easeOutCubic(clamp01(seg(t, 0.01, 0.11)));
  const lensIn = easeOutCubic(clamp01(seg(t, 0.56, 0.70)));
  const noteIn = easeOutCubic(clamp01(seg(t, 0.62, 0.76)));

  const defs: React.ReactNode[] = [];
  const svgParts: React.ReactNode[] = [];
  const htmlParts: React.ReactNode[] = [];

  for (let i = 0; i < 2; i++) {
    const g = i === 0 ? {label: sL, a: sA, b: sB, note: sN} : {label: iL, a: iA, b: iB, note: iN};
    const tone = i === 0 ? WARN : OK;
    const src = i === 0 ? REG_SHARED : REG_INDEP;
    const {x, y} = panelXY(i);
    const fX = x + P, fY = y + fy0;
    const cardIn = easeOutCubic(clamp01(seg(t, 0.01 + i * 0.03, 0.14 + i * 0.03)));
    const headIn = easeOutCubic(clamp01(seg(t, 0.05 + i * 0.03, 0.19 + i * 0.03)));

    // blind-area centres, clamped so a ring can never run outside its own field at any aspect
    const place = (v: number, span: number) => {
      const lo = rr / span + 0.02, hi = 1 - rr / span - 0.02;
      return hi <= lo ? 0.5 : Math.max(lo, Math.min(hi, v));
    };
    const regs = src.map((r) => ({x: fX + place(r.cx, fwd) * fwd, y: fY + place(r.cy, fhd) * fhd}));
    const ringIn = regs.map((_, j) => easeOutExpo(clamp01(seg(t, 0.28 + j * 0.13 + i * 0.02, 0.41 + j * 0.13 + i * 0.02))));

    // cells — deterministic jittered grid (hash01 seeded by panel+index, never Math.random)
    const marks: React.ReactNode[] = [];
    const holes: {x: number; y: number}[] = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const k = r * cols + c;
        const sd = i * 977 + k;
        const cx = fX + (c + 0.5) * pxx + (hash01(sd * 2 + 1) - 0.5) * pxx * 0.3;
        const cy = fY + (r + 0.5) * pxy + (hash01(sd * 2 + 2) - 0.5) * pxy * 0.3;
        const inA = Math.hypot(cx - regs[0].x, cy - regs[0].y) < rr;
        const inB = Math.hypot(cx - regs[1].x, cy - regs[1].y) < rr;
        const hole = inA && inB, saved = (inA || inB) && !hole;
        if (hole) holes.push({x: cx, y: cy});
        const ha = hash01(sd * 3 + 11), hb = hash01(sd * 5 + 29);
        const app = easeOutCubic(clamp01(seg(t, 0.04 + ha * 0.13, 0.18 + ha * 0.13)));
        if (app <= 0.004) continue;
        const res = (hole || saved)
          ? easeOutExpo(clamp01(seg(t, 0.54 + hb * 0.11, 0.68 + hb * 0.11)))
          : 0;
        const grow = lerp(0.72, 1, app);
        const s = lerp(quietS, bigS, res) * grow;
        marks.push(
          <rect key={`m${i}-${k}`} x={cx - s / 2} y={cy - s / 2} width={s} height={s} rx={s * 0.28}
            fill={saved ? mix(QUIET, OK, res) : QUIET}
            opacity={app * (hole ? 0.34 * (1 - res) : lerp(0.34, saved ? 1 : 0.4, res))} />,
        );
        if (hole && res > 0.01) {
          const hs = bigS * grow;
          marks.push(
            <rect key={`h${i}-${k}`} x={cx - hs / 2} y={cy - hs / 2} width={hs} height={hs} rx={hs * 0.28}
              fill="none" stroke={WARN} strokeWidth={Math.max(2, pitch * 0.06)} opacity={res * 0.95} />,
          );
        }
      }
    }

    // the shared hole, as an AREA: the lens where the two blind areas overlap (empty when they don't)
    defs.push(
      <clipPath key={`cp${i}`} id={`sb-clip-${i}`}>
        <circle cx={regs[0].x} cy={regs[0].y} r={rr} />
      </clipPath>,
    );
    let glow: React.ReactNode = null;
    if (holes.length) {
      const hx = holes.reduce((a, p) => a + p.x, 0) / holes.length;
      const hy = holes.reduce((a, p) => a + p.y, 0) / holes.length;
      const hr = Math.max(...holes.map((p) => Math.hypot(p.x - hx, p.y - hy))) + pitch * 1.3;
      defs.push(
        <radialGradient key={`gr${i}`} id={`sb-glow-${i}`}>
          <stop offset="0%" stopColor={WARN} stopOpacity={0.30} />
          <stop offset="60%" stopColor={WARN} stopOpacity={0.10} />
          <stop offset="100%" stopColor={WARN} stopOpacity={0} />
        </radialGradient>,
      );
      glow = <circle cx={hx} cy={hy} r={hr} fill={`url(#sb-glow-${i})`} opacity={lensIn} />;
    }

    svgParts.push(
      <g key={`p${i}`} opacity={cardIn}>
        <rect x={x} y={y} width={pw} height={ph} rx={RAD} fill={SURF} stroke={mix(EDGE, tone, 0.34)}
          strokeWidth={dna?.borderWidth ?? 1} />
        <line x1={x + P} y1={y + P + headH + Math.round(P * 0.26)} x2={x + pw - P}
          y2={y + P + headH + Math.round(P * 0.26)} stroke={LINE} strokeWidth={1} />
        {gridCue ? (
          <rect x={fX} y={fY} width={fwd} height={fhd} fill="none" stroke={LINE} strokeWidth={1}
            strokeDasharray="2 9" opacity={0.7} />
        ) : null}
        {glow}
        {/* each producer's blind AREA — a wash, so two coincident areas visibly stack */}
        {regs.map((rg, j) => (
          <circle key={`w${j}`} cx={rg.x} cy={rg.y} r={rr * lerp(0.8, 1, ringIn[j])} fill={WARN}
            opacity={ringIn[j] * 0.05} />
        ))}
        {/* the overlap of the two blind areas = the cases NOBODY catches */}
        <circle cx={regs[1].x} cy={regs[1].y} r={rr} fill={WARN} opacity={lensIn * 0.16}
          clipPath={`url(#sb-clip-${i})`} />
        {marks}
        {regs.map((rg, j) => (
          <circle key={`r${j}`} cx={rg.x} cy={rg.y} r={rr * lerp(0.8, 1, ringIn[j])} fill="none"
            stroke={WARN} strokeWidth={sw} opacity={ringIn[j] * 0.85}
            // @positional: the second reviewer's blind area is dashed so the two overlapping regions can be told apart
            strokeDasharray={j === 1 ? `${Math.max(7, rr * 0.1)} ${Math.max(6, rr * 0.07)}` : undefined}
            strokeLinecap="round" />
        ))}
      </g>,
    );

    htmlParts.push(
      <div key={`t${i}`} style={{position: 'absolute', left: x + P, top: y + P, width: fwd, height: headH}}>
        <div style={{height: labelH, display: 'flex', alignItems: 'center', gap: 12, opacity: headIn}}>
          {g.label ? <div style={{width: 4, height: Math.round(sizes.labelSize * 1.05 * sizes.labelLines),
            background: tone, borderRadius: 2, flex: '0 0 auto'}} /> : null}
          <div style={{color: tone, font: `700 ${sizes.labelSize}px/1.3 ${disp}`, letterSpacing: track,
            textTransform: upper ? 'uppercase' : 'none', minWidth: 0}}>{g.label}</div>
        </div>
        <div style={{height: headGap}} />
        <div style={{height: chipH, display: 'flex', flexDirection: sizes.chipCols === 2 ? 'row' : 'column',
          gap: sizes.chipCols === 2 ? 18 : CHIP_ROW_GAP, alignItems: sizes.chipCols === 2 ? 'center' : 'stretch',
          justifyContent: 'center', opacity: headIn}}>
          {[g.a, g.b].map((nm, j) => (
            <div key={j} style={{flex: '1 1 0', display: 'flex', alignItems: 'center', gap: 12, minWidth: 0}}>
              {nm ? <svg width={sizes.swW} height={Math.max(10, sw * 3)} style={{flex: '0 0 auto', overflow: 'visible'}}>
                <line x1={1} y1={Math.max(10, sw * 3) / 2} x2={sizes.swW - 1} y2={Math.max(10, sw * 3) / 2}
                  stroke={WARN} strokeWidth={sw} strokeLinecap="round"
                  // @positional: the second reviewer's blind area is dashed so the two overlapping regions can be told apart
                  strokeDasharray={j === 1 ? `${Math.max(5, sw * 1.8)} ${Math.max(4, sw * 1.4)}` : undefined} />
              </svg> : null}
              <div style={{color: FG, font: `600 ${sizes.chipSize}px/1.32 ${mono}`, minWidth: 0}}>{nm}</div>
            </div>
          ))}
        </div>
      </div>,
    );

    htmlParts.push(
      <div key={`n${i}`} style={{position: 'absolute', left: x + P, top: y + ph - P - noteH, width: fwd,
        height: noteH, display: 'flex', alignItems: 'center', opacity: noteIn,
        borderLeft: g.note ? `2px solid ${tone}` : undefined, paddingLeft: 12, boxSizing: 'border-box',
        color: mix(DIM, FG, 0.45), font: `500 ${sizes.noteSize}px/1.42 ${mono}`}}>{g.note}</div>,
    );
  }

  return (
    <AbsoluteFill style={{background: BG, backgroundColor: GROUND, color: FG}}>
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
        <defs>{defs}</defs>
        {svgParts}
      </svg>
      {KICKER ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: kickTop, textAlign: 'center',
          padding: `0 ${mx}px`, boxSizing: 'border-box',
          color: OK, opacity: tIn * 0.9, font: `600 ${kickSize}px/1.2 ${mono}`, letterSpacing: track,
          textTransform: upper ? 'uppercase' : 'none'}}>{KICKER}</div>
      ) : null}
      <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, height: titleH,
        padding: `0 ${Math.round((W - titleBox) / 2)}px`, boxSizing: 'border-box',
        display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
        color: FG, opacity: tIn, font: `700 ${type.tSize}px/1.16 ${disp}`, letterSpacing: '-0.01em'}}>{TITLE}</div>
      {htmlParts}
    </AbsoluteFill>
  );
};
export default SharedBlindspot;
