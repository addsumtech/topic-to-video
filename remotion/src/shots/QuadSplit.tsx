// SHOT · Quad Split — the content zone divides into a 2×2 grid of micro-panels that populate in sequence
// (each a tone from the film's palette + a DECODABLE glyph), then ONE hero panel expands to take the frame.
// The "four things we rely on, then the one that matters" register (comparison / overview). Deterministic.
//
// GLYPHS. Each panel carries a small form that MEANS its label — pass `glyph` per panel:
//   checks  a row of passing check marks            → tests / a suite that goes green
//   gutter  a code gutter, covered vs uncovered     → coverage / what the tests never touched
//   peers   two badges producing the same answer    → cross-check / peer agreement (AI 互检)
//   review  a reviewer's cursor on a line of code   → human review / someone reads it
//   bars · ring · dots · wave                       → the neutral quantity/progress/set/trend motifs
// Omitting `glyph` keeps the historical behaviour (motif = panel INDEX → bars/ring/dots/wave), so films
// authored before glyphs existed render exactly as they did. An UNKNOWN glyph name throws rather than
// silently drawing the wrong picture — a typo must not ship as a bar chart labelled "human review".
//
// FRAME-CRAFT: the grid lives strictly inside [CONTENT_TOP, contentBottom(W,H)] and the expanded hero stops
// at contentBottom too, so the burned caption band stays the shot's own clean ground for the WHOLE shot.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {fitTextOnNLines} from '@remotion/layout-utils';
import {useT, seg, lerp, clamp01, easeOutCubic, easeInOutCubic, easeOutBack, hash01} from '../runtime/motion';
import {useDNA, dnaPalette, mix} from '../runtime/dna';
import {CONTENT_TOP, TITLE_Y, contentBottom} from '../runtime/layout';

export const DURATION = 150; // 5s

// no-DNA fallbacks (the shot must render on its own, un-themed, exactly as it always did)
const BG_D0 = '#0b0d14';
const TONES_D0 = ['#5b8cff', '#ff5b7f', '#22c197', '#f6a531'];
const INK_D0 = '#f3f5ff', DIM_D0 = '#7f879c', HEAD_D0 = '#aeb6ca';
const SURF_D0 = '#141724', EDGE_D0 = '#20243a';
const TRACK_D0 = '#ffffff18';   // the ring's unfilled track (the register's original value)
const OFF_D0 = '#ffffff14';     // an unfilled dot (the register's original value)
const SOFT_D0 = '#ffffff2e';    // secondary marks — code lines a glyph has not highlighted

export type QuadGlyph = 'bars' | 'ring' | 'dots' | 'wave' | 'checks' | 'gutter' | 'peers' | 'review';
export const QUAD_GLYPHS: QuadGlyph[] = ['bars', 'ring', 'dots', 'wave', 'checks', 'gutter', 'peers', 'review'];
const INDEX_GLYPHS: QuadGlyph[] = ['bars', 'ring', 'dots', 'wave'];

/** Resolve a panel's glyph: an explicit name, else the historical index motif. Fails loudly on a typo. */
const glyphFor = (name: string | undefined, i: number): QuadGlyph => {
  if (!name) return INDEX_GLYPHS[i % INDEX_GLYPHS.length];
  if ((QUAD_GLYPHS as string[]).includes(name)) return name as QuadGlyph;
  throw new Error(
    `QuadSplit: unknown panel glyph "${name}". Use one of: ${QUAD_GLYPHS.join(', ')} (or omit it for the index motif).`,
  );
};

type Ink = {
  c: string;      // this panel's tone
  warn: string;   // the "not verified" tone (the film's second accent; dim when the tone IS that accent)
  soft: string;   // secondary marks — inactive code lines, rules
  track: string;  // an unfilled ring track / a pending badge
  off: string;    // an unfilled dot
  ink: string;    // primary ink
  ground: string; // the ground these marks sit on
};

/** The glyph set. Every form is drawn in its own viewBox and scaled by the tile, so the same drawing reads at
 *  quadrant size AND at hero size. Structure — not colour — is what distinguishes them. */
const Glyph: React.FC<Ink & {kind: QuadGlyph; g: number}> = ({kind, g, c, warn, soft, track, off, ink, ground}) => {
  // xMIN: the glyph shares the panel's left axis with the index and the label, instead of floating in the
  // middle of the box while the type hugs the edge.
  const box = (vb: string, children: React.ReactNode) => (
    <svg viewBox={vb} width="100%" height="100%" preserveAspectRatio="xMinYMid meet">{children}</svg>
  );

  // ── quantity: five bars rising ────────────────────────────────────────────────────────────────────────
  if (kind === 'bars') return box('0 0 220 120', [0, 1, 2, 3, 4].map((b) => {
    const h = (28 + ((b * 37) % 70)) * clamp01(g * 1.4 - b * 0.08);
    return <rect key={b} x={b * 44} y={120 - h} width={30} height={h} rx={5} fill={c} />;
  }));

  // ── proportion: a ring filling ────────────────────────────────────────────────────────────────────────
  if (kind === 'ring') return box('0 0 140 140', (
    <>
      <circle cx={70} cy={70} r={54} fill="none" stroke={track} strokeWidth={12} />
      <circle cx={70} cy={70} r={54} fill="none" stroke={c} strokeWidth={12} strokeLinecap="round"
        strokeDasharray={2 * Math.PI * 54} strokeDashoffset={2 * Math.PI * 54 * (1 - 0.72 * g)}
        transform="rotate(-90 70 70)" />
    </>
  ));

  // ── a set filling up ──────────────────────────────────────────────────────────────────────────────────
  if (kind === 'dots') return box('0 0 200 120', [...Array(12)].map((_, k) => (
    <circle key={k} cx={16 + (k % 6) * 34} cy={30 + Math.floor(k / 6) * 60} r={12}
      fill={k / 12 < g ? c : off} />
  )));

  // ── a trend drawing itself ────────────────────────────────────────────────────────────────────────────
  if (kind === 'wave') {
    const pts = [...Array(24)].map((_, k) => {
      const x = (k / 23) * 220;
      const y = 60 - Math.sin(k * 0.6) * 34 * clamp01(g * 1.3 - k / 40);
      return `${x},${y}`;
    }).join(' ');
    return box('0 0 220 120', (
      <polyline points={pts} fill="none" stroke={c} strokeWidth={5} strokeLinecap="round" />
    ));
  }

  // ── TESTS: a row of check marks going green, one after another ────────────────────────────────────────
  if (kind === 'checks') return box('0 0 240 84', [0, 1, 2, 3].map((k) => {
    const p = clamp01((g - k * 0.15) * 3.4);
    const cx = 34 + k * 57.4, cy = 42;
    return (
      <g key={k}>
        <circle cx={cx} cy={cy} r={25} fill={mix(ground, c, 0.16 * p)}
          stroke={p > 0.05 ? c : track} strokeWidth={4} opacity={0.4 + 0.6 * p} />
        <polyline points={`${cx - 11},${cy + 1} ${cx - 3.5},${cy + 9} ${cx + 12},${cy - 9}`} fill="none"
          stroke={c} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round"
          strokeDasharray={42} strokeDashoffset={42 * (1 - p)} />
      </g>
    );
  }));

  // ── COVERAGE: a code gutter — solid ticks where the tests ran, hollow amber ticks where they never did ─
  if (kind === 'gutter') {
    const COV = [1, 1, 0, 1, 1, 1, 0];          // fixed, deterministic: five lines exercised, two never run
    const IND = [0, 16, 16, 32, 16, 0, 16];     // indentation so the rows read as code, not as a bar chart
    return box('0 0 240 140', (
      <>
        <line x1={32} y1={4} x2={32} y2={136} stroke={soft} strokeWidth={2} />
        {COV.map((cv, k) => {
          const p = clamp01((g - k * 0.1) * 4);
          const y = 14 + k * 18.6;
          const bw = 76 + Math.round(hash01(k * 3 + 1) * 82);
          return (
            <g key={k} opacity={0.22 + 0.78 * p}>
              <rect x={13} y={y - 7} width={10} height={14} rx={2}
                fill={cv ? c : 'none'} stroke={cv ? c : warn} strokeWidth={2.5} />
              <rect x={46 + IND[k]} y={y - 4.5} width={bw * (0.4 + 0.6 * p)} height={9} rx={4.5}
                fill={cv ? mix(ground, c, 0.5) : mix(ground, warn, 0.3)} />
            </g>
          );
        })}
      </>
    ));
  }

  // ── PEER CROSS-CHECK: two badges hand back the SAME three lines and sign each other off ────────────────
  if (kind === 'peers') {
    const link = clamp01((g - 0.16) * 2.4);
    const seal = clamp01((g - 0.55) * 3);
    const badge = (bx: number, k: number) => (
      <g key={k} opacity={clamp01((g - k * 0.12) * 4)}>
        <rect x={bx} y={26} width={70} height={70} rx={15} fill={mix(ground, c, 0.15)} stroke={c} strokeWidth={3} />
        {[38, 28, 32].map((bw, r) => (
          <rect key={r} x={bx + 16} y={44 + r * 15} width={bw} height={7} rx={3.5} fill={c} opacity={0.82} />
        ))}
      </g>
    );
    return box('0 0 240 120', (
      <>
        {badge(8, 0)}{badge(162, 1)}
        <line x1={88} y1={61} x2={88 + 64 * link} y2={61} stroke={c} strokeWidth={4}
          strokeLinecap="round" opacity={0.5} />
        <polygon points="85,61 96,55 96,67" fill={c} opacity={link} />
        <polygon points="155,61 144,55 144,67" fill={c} opacity={link} />
        <circle cx={120} cy={61} r={19} fill={ground} stroke={c} strokeWidth={3} opacity={seal} />
        <polyline points="112,61 118,67.5 129,54" fill="none" stroke={c} strokeWidth={5}
          strokeLinecap="round" strokeLinejoin="round"
          strokeDasharray={30} strokeDashoffset={30 * (1 - seal)} />
      </>
    ));
  }

  // ── HUMAN REVIEW: a pointer travels down the listing and stops on one line, which lights up ────────────
  const ROWS = [{x: 18, w: 150}, {x: 34, w: 186}, {x: 34, w: 132}, {x: 18, w: 164}];
  const TARGET = 2;
  const ty = 22 + TARGET * 30;
  const trav = easeOutCubic(clamp01(g * 1.5));
  const mark = clamp01((g - 0.62) * 3.2);
  return box('0 0 240 132', (
    <>
      {mark > 0.01 ? (
        <rect x={8} y={ty - 16} width={224} height={32} rx={6}
          fill={mix(ground, c, 0.2)} stroke={c} strokeWidth={2} opacity={mark} />
      ) : null}
      {ROWS.map((r, k) => (
        <rect key={k} x={r.x} y={22 + k * 30 - 5} width={r.w * clamp01(g * 3 - k * 0.2)} height={10} rx={5}
          fill={k === TARGET ? c : soft} opacity={k === TARGET ? 0.5 + 0.5 * mark : 0.85} />
      ))}
      <g transform={`translate(${lerp(196, 74, trav)} ${lerp(6, ty - 10, trav)})`} opacity={clamp01(g * 5)}>
        <path d="M0,0 L0,30 L8,22 L14,34 L21,31 L15,19 L25,19 Z" fill={ink} stroke={ground}
          strokeWidth={2} strokeLinejoin="round" />
      </g>
    </>
  ));
};

// ── tone legibility floor ────────────────────────────────────────────────────────────────────────────────
// dnaPalette keeps derived tones INSIDE the film's two hues (right — that is what stops a blue tile turning
// up in a green/amber film), but the ladder's "pressed toward the ground" step can land a tone so close to
// the ground that a 9px glyph stroke reads as a smudge. Lift such a tone toward the film's OWN ink until it
// separates. Works on a light-ground DNA too, because ink is by definition the contrasty end of the system.
const _HEX6 = /^#([0-9a-fA-F]{6})$/;
const lum = (c: string): number | null => {
  const m = _HEX6.exec(String(c).trim());
  if (!m) return null;
  const v = parseInt(m[1], 16);
  return (0.2126 * ((v >> 16) & 255) + 0.7152 * ((v >> 8) & 255) + 0.0722 * (v & 255)) / 255;
};
const MIN_TONE_SEP = 0.42;
const legibleTone = (c: string, ground: string, ink: string): string => {
  const lg = lum(ground);
  if (lg == null || lum(c) == null || lum(ink) == null) return c;   // non-hex token: leave it alone
  let out = c;
  for (let k = 1; k <= 5 && Math.abs((lum(out) as number) - lg) < MIN_TONE_SEP; k++) out = mix(c, ink, k * 0.14);
  return out;
};

export type QuadPanel = {label?: string; glyph?: string};

const DEFAULT_PANELS: QuadPanel[] = [{label: 'Faster'}, {label: 'Simpler'}, {label: 'Cheaper'}, {label: 'Safer'}];

export const QuadSplit: React.FC<{panels?: QuadPanel[]; heading?: string; hero?: number}> = ({
  panels: PANELS = DEFAULT_PANELS, heading: HEADING = 'Four ways it wins', hero: HERO = 0} = {}) => {
  const t = useT();
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const TONES = dnaPalette(dna, 4) ?? TONES_D0;
  const INK = dna?.fg ?? INK_D0, DIM = dna?.dim ?? DIM_D0, HEADC = dna?.dim ?? HEAD_D0;
  const SURF = dna?.surface ?? SURF_D0, EDGE = dna?.surfaceBorder ?? EDGE_D0;
  const ACC2 = dna?.accent2 ?? TONES_D0[3];
  // Derived from the film's own ground+ink when a DNA is present; the register's original literals when
  // there is none, so an un-themed film renders byte-for-byte as before.
  const SOFT = dna ? mix(BG, INK, 0.26) : SOFT_D0;
  const TRACK = dna ? mix(BG, INK, 0.14) : TRACK_D0;
  const OFF = dna ? mix(BG, INK, 0.11) : OFF_D0;
  const dispFace = dna?.fontDisplay ?? 'Inter, "PingFang SC", "Hiragino Sans", "Microsoft YaHei", system-ui, sans-serif';
  const monoFace = dna?.fontMono ?? '"JetBrains Mono", "PingFang SC", "Hiragino Sans", ui-monospace, monospace';
  const rad = dna?.radius != null ? Math.max(dna.radius, 10) : 22;
  const bwid = dna?.borderWidth ?? 1;
  const headSpacing = dna?.labelSpacing ?? '0.28em';
  const headCase: 'uppercase' | 'none' = dna ? (dna.uppercaseLabels ? 'uppercase' : 'none') : 'uppercase';

  const {width: W, height: H} = useVideoConfig();
  const cells = (PANELS && PANELS.length ? PANELS : DEFAULT_PANELS).slice(0, 4);
  const n = cells.length;
  const heroIdx = Math.max(0, Math.min(Math.round(HERO) || 0, n - 1));

  // GEOMETRY. Everything lives in the CONTENT ZONE — never the whole frame — so the bottom row and the
  // expanded hero both stop clear of the burned caption band. Fractions of W/H, so it reflows at any aspect.
  const zoneTop = CONTENT_TOP;
  const zoneBot = contentBottom(W, H);
  const zoneH = Math.max(200, zoneBot - zoneTop);
  const gap = Math.round(Math.min(W, H) * 0.018);
  const cols = n <= 1 ? 1 : 2;
  const rows = n <= 2 ? 1 : 2;
  const cellW = W / cols, cellH = zoneH / rows;
  // The hero's settled rect: full content zone minus a margin OUTSIDE the action-safe border.
  const safe = Math.round(Math.min(W, H) * 0.05);
  const eX = safe, eY = safe, eW = W - 2 * safe, eH = Math.max(200, zoneBot - safe);

  const expand = easeInOutCubic(seg(t, 0.72, 0.97));       // hero takes the frame
  // The other three CLEAR OUT BEFORE the hero crosses them. Fading them on the expand curve meant the hero's
  // label and glyph rode over three still-visible panels for ~10 frames — a glyph/type mash mid-shot.
  const clearOut = easeOutCubic(seg(t, 0.70, 0.80));
  const headIn = clamp01(seg(t, 0.04, 0.16)) * (1 - clamp01(seg(t, 0.66, 0.74)));

  // TYPE IS WIDTH-FITTED, twice: once for the quadrant box and once for the expanded hero box, then lerped.
  // A hardcoded 56/132px overflowed the panel the moment the label was real Chinese copy instead of "Safer".
  const labelFits = React.useMemo(() => cells.map((p, i) => {
    const txt = String(p?.label ?? '');
    const spanned = n === 3 && i === 2;
    const tileW = (spanned ? W : cellW) - gap;
    const tileH = cellH - gap;
    const tPad = Math.round(Math.max(16, Math.min(tileW * 0.06, tileH * 0.1, 64)));
    const hPad = Math.round(Math.max(16, Math.min(eW * 0.06, eH * 0.1, 64)));
    const fit = (boxW: number, cap: number) => (txt
      ? fitTextOnNLines({text: txt, maxLines: 2, maxBoxWidth: Math.max(60, boxW), fontFamily: dispFace,
        fontWeight: 800, maxFontSize: cap})
      : {fontSize: cap, lines: [] as string[]});
    const a = fit(tileW - 2 * tPad, Math.max(20, Math.min(56, tileH * 0.18, tileW * 0.34)));
    const b = fit(eW - 2 * hPad, Math.max(24, Math.min(132, eH * 0.18)));
    return {tile: a.fontSize, hero: b.fontSize, lines: Math.max(1, a.lines.length, b.lines.length)};
  }), [cells, n, W, cellW, cellH, gap, eW, eH, dispFace]);

  const headFit = React.useMemo(() => fitTextOnNLines({
    text: String(HEADING ?? ''), maxLines: 1, maxBoxWidth: W * 0.84, fontFamily: monoFace,
    fontWeight: 700, maxFontSize: 32, letterSpacing: headSpacing, textTransform: headCase,
  }).fontSize, [HEADING, W, monoFace, headSpacing, headCase]);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG}}>
      {cells.map((p, i) => {
        const spanned = n === 3 && i === 2;               // a 3-panel deck: the last one spans the bottom row
        const col = i % cols, row = Math.floor(i / cols);
        const enter = easeOutBack(clamp01(seg(t, 0.12 + i * 0.09, 0.34 + i * 0.09)));
        const grow = i === heroIdx ? expand : 0;
        const others = i === heroIdx ? 0 : clearOut;
        const x0 = spanned ? gap / 2 : col * cellW + gap / 2;
        const y0 = zoneTop + row * cellH + gap / 2;
        const w0 = (spanned ? W : cellW) - gap, h0 = cellH - gap;
        const x = lerp(x0, eX, grow), y = lerp(y0, eY, grow);
        const w = lerp(w0, eW, grow), h = lerp(h0, eH, grow);
        const raw = TONES[i % TONES.length];
        const tone = legibleTone(raw, BG, INK);
        // the "never verified" mark inside a glyph: the film's second accent — unless THIS tile already IS it,
        // in which case solid-vs-hollow has to carry the distinction and the mark drops to the dim ink.
        const warn = raw === ACC2 ? DIM : ACC2;
        const g = clamp01(seg(t, 0.16 + i * 0.09, 0.6)); // glyph fill progress

        // INTERNAL LAYOUT, computed (not space-between): header · glyph · label, all inside the padding box.
        // space-between is what pushed the bottom row's label onto the burned caption; explicit heights and
        // border-box sizing are what keep the panel the size it says it is.
        const pad = Math.round(Math.max(16, Math.min(w * 0.06, h * 0.1, 64)));
        const inner = Math.max(60, h - 2 * pad - 2 * bwid);
        const hs = Math.round(Math.max(15, Math.min(h * 0.05, 26)));
        const headH = Math.round(hs * 1.3);
        const gapY = Math.round(pad * 0.5);
        const fit = labelFits[i];
        const want = lerp(fit.tile, fit.hero, grow);
        const wantH = want * 1.24 * fit.lines;
        const labelH = Math.min(wantH, inner * 0.42);
        const labelSize = wantH > 0 ? want * (labelH / wantH) : want;
        const glyphH = Math.max(34, inner - headH - labelH - 2 * gapY);
        const glyphW = Math.max(40, w - 2 * pad - 2 * bwid);

        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, width: w, height: h, boxSizing: 'border-box',
            opacity: (0.15 + 0.85 * enter) * (1 - others), transform: `scale(${lerp(0.9, 1, enter)})`,
            transformOrigin: `${cols > 1 && !spanned ? (col ? 'left' : 'right') : 'center'} ${rows > 1 ? (row ? 'top' : 'bottom') : 'center'}`,
            background: `linear-gradient(150deg, ${mix(BG, SURF, 0.85)}, ${BG})`,
            border: `${bwid}px solid ${EDGE}`, borderRadius: rad, overflow: 'hidden',
            display: 'flex', flexDirection: 'column', padding: pad,
            boxShadow: i === heroIdx && grow > 0.1 ? `inset 0 0 200px ${tone}22` : '0 24px 60px #0006'}}>

            <div style={{height: headH, flex: 'none', display: 'flex', alignItems: 'center', gap: Math.round(hs * 0.7)}}>
              <div style={{width: Math.round(hs * 0.64), height: Math.round(hs * 0.64), borderRadius: 5,
                background: tone, boxShadow: `0 0 20px ${tone}`}} />
              <div style={{color: DIM, font: `600 ${hs}px/1 ${monoFace}`, letterSpacing: '0.14em'}}>
                {String(i + 1).padStart(2, '0')}
              </div>
            </div>

            <div style={{height: glyphH, marginTop: gapY, flex: 'none', display: 'flex',
              alignItems: 'center', justifyContent: 'flex-start'}}>
              <div style={{width: '100%', height: '100%', maxWidth: Math.min(glyphW, W * 0.82),
                maxHeight: Math.min(glyphH, H * 0.46)}}>
                <Glyph kind={glyphFor(p?.glyph, i)} g={g} c={tone} warn={warn} soft={SOFT} track={TRACK} off={OFF}
                  ink={INK} ground={BG} />
              </div>
            </div>

            <div style={{marginTop: gapY, flex: 'none', color: INK,
              font: `800 ${labelSize}px/1.24 ${dispFace}`, letterSpacing: '-0.02em'}}>{p?.label}</div>
          </div>
        );
      })}

      <div style={{position: 'absolute', top: TITLE_Y, left: '8%', right: '8%', textAlign: 'center',
        opacity: headIn, color: HEADC, font: `700 ${headFit}px/1.1 ${monoFace}`,
        letterSpacing: headSpacing, textTransform: headCase, whiteSpace: 'nowrap',
        overflow: 'hidden', textOverflow: 'ellipsis'}}>{HEADING}</div>
    </AbsoluteFill>
  );
};
export default QuadSplit;
