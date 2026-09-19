// PlatformSurfaces — the "one platform, many surfaces" register, done MEANINGFULLY. A bento of product tiles pops
// in beside a hero statement, but each tile carries a glyph that ENCODES its own product (chat bubbles, API
// braces, a video frame, a code block, a cursor-on-window) rather than a random reused mini-chart. Keeps the
// bento-assembles VIBE; the CONTENT is designed per surface. Fully prop-driven (label/note/glyph) → generalises
// to any platform. Deterministic (pop = fn of t).
//
// THE TITLE IS SAID ONCE, AND A TILE'S PICTURE IS THE ONE THE FILM PICKED. Two things drew what nobody wrote:
//   * `title` was rendered twice — as the frame's header AND as the hero panel's headline, 180px apart — so
//     every film's one statement read as two, and a long title filled the frame twice over. It is now the
//     hero panel's headline only (the panel is the statement: kicker, headline, subtitle), and the header row
//     is left to the panel;
//   * a tile with no `glyph` (or a glyph name the file did not know) was given a generic 'node' pictogram, a
//     picture standing for a surface nobody said it was. A tile without a glyph now draws no picture, and an
//     unknown glyph name throws with the list of names that exist.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {leading} from '../runtime/cjkType';
import {contentBottom} from '../runtime/layout';

export const DURATION = 165; // 5.5s

type Tile = {label?: string; note?: string; glyph?: string};
const GLYPHS = ['chat', 'api', 'video', 'code', 'cursor', 'node'];
// Six tiles is three rows of two: past it a row is shorter than its own glyph and label.
export const MAX_PLATFORM_TILES = 6;

// each glyph is a small, legible pictogram that MEANS its surface (drawn in the tile's accent)
const Glyph: React.FC<{kind: string; c: string; g: number}> = ({kind, c, g}) => {
  const dash = (len: number) => ({strokeDasharray: len, strokeDashoffset: len * (1 - clamp01(g * 1.3))});
  if (kind === 'chat') return (<svg width={96} height={72}>
    <rect x={2} y={2} width={62} height={40} rx={12} fill="none" stroke={c} strokeWidth={4} /><path d="M18,42 L18,56 L34,42" fill="none" stroke={c} strokeWidth={4} strokeLinejoin="round" />
    <rect x={40} y={30} width={54} height={34} rx={11} fill={`${c}22`} stroke={c} strokeWidth={3} /></svg>);
  if (kind === 'api') return (<svg width={110} height={74}><text x={2} y={58} fill={c} style={{font: '800 68px/1 var(--f-mono, "JetBrains Mono", monospace)'}}>{'{'}</text>
    <circle cx={55} cy={37} r={7} fill={c} /><line x1={55} y1={12} x2={55} y2={62} stroke={c} strokeWidth={3} {...dash(50)} />
    <text x={78} y={58} fill={c} style={{font: '800 68px/1 var(--f-mono, "JetBrains Mono", monospace)'}}>{'}'}</text></svg>);
  if (kind === 'video') return (<svg width={104} height={72}>
    <rect x={2} y={2} width={100} height={68} rx={10} fill="none" stroke={c} strokeWidth={4} />
    {[16, 34, 52, 70, 88].map((x) => <line key={x} x1={x} y1={2} x2={x} y2={12} stroke={c} strokeWidth={3} />)}
    {[16, 34, 52, 70, 88].map((x) => <line key={'b' + x} x1={x} y1={60} x2={x} y2={70} stroke={c} strokeWidth={3} />)}
    <path d="M42,24 L68,37 L42,50 Z" fill={c} opacity={clamp01(g * 1.5)} /></svg>);
  if (kind === 'code') return (<svg width={112} height={72}>{[0, 1, 2].map((r) => {
    const w = [70, 96, 54][r]; return <rect key={r} x={2} y={6 + r * 22} width={w * clamp01(g * 1.4 - r * 0.15)} height={12} rx={6} fill={r === 1 ? c : `${c}88`} />;
  })}<text x={112} y={52} textAnchor="end" fill={c} style={{font: '800 30px/1 var(--f-mono, "JetBrains Mono", monospace)'}}>{'</>'}</text></svg>);
  if (kind === 'cursor') return (<svg width={100} height={78}>
    <rect x={2} y={2} width={96} height={62} rx={9} fill="none" stroke={c} strokeWidth={4} /><line x1={2} y1={20} x2={98} y2={20} stroke={c} strokeWidth={3} />
    <circle cx={12} cy={11} r={3} fill={c} /><circle cx={24} cy={11} r={3} fill={c} />
    <path d={`M54,34 L54,${34 + 34 * clamp01(g * 1.4)} L62,52 L68,60 L72,56 L66,48 L76,46 Z`} fill={c} stroke="#0a0c12" strokeWidth={2} /></svg>);
  // 'node': a generic node — drawn only when the film names it; it is never a stand-in for a missing glyph
  return (<svg width={80} height={72}><circle cx={40} cy={36} r={22} fill="none" stroke={c} strokeWidth={4} /><circle cx={40} cy={36} r={7} fill={c} /></svg>);
};

export const PlatformSurfaces: React.FC<{
  title?: string; subtitle?: string; tiles?: Tile[]; accent?: string; accent2?: string;
  markLabel?: string;
}> = ({
  markLabel = 'THE PLATFORM',
  title = 'One platform, not one app', subtitle = 'everything runs on the same models',
  tiles = [{label: 'API', note: 'developers build on it', glyph: 'api'},
           {label: 'Sora', note: 'image + video', glyph: 'video'},
           {label: 'Codex', note: 'coding agent', glyph: 'code'},
           {label: 'Operator', note: 'browser agent', glyph: 'cursor'}],
  accent: accent0 = '#10a37f', accent2: accent20 = '#7aa2ff',
} = {}) => {
  if (!Array.isArray(tiles) || tiles.length < 1 || tiles.length > MAX_PLATFORM_TILES) {
    throw new Error(`PlatformSurfaces needs 1-${MAX_PLATFORM_TILES} \`tiles\` (got ${Array.isArray(tiles) ? tiles.length : typeof tiles}). ` +
      'Each surface gets its own tile, two to a row; past six the rows are too short to hold a glyph and a label.');
  }
  tiles.forEach((tile, i) => {
    if (!String(tile?.label ?? '').trim()) throw new Error(`PlatformSurfaces: tile ${i + 1} has no label.`);
    if (tile.glyph != null && !GLYPHS.includes(tile.glyph)) {
      throw new Error(`PlatformSurfaces: tile ${i + 1} ("${tile.label}") has glyph ${JSON.stringify(tile.glyph)} — use one of ` +
        `${GLYPHS.join(', ')}, or leave it out and the tile draws no picture.`);
    }
  });
  const {width: W, height: H} = useVideoConfig();
  const t = useT();
  const dna = useDNA();
  const accent = dna?.accent ?? accent0, accent2 = dna?.accent2 ?? accent20;
  const TONES = [accent, accent2, '#e0b64b', '#c07bff', '#37d4a6'];
  const portrait = W < H;
  // LANDSCAPE: hero panel on the LEFT, a 2x2 tile grid on the RIGHT. PORTRAIT: hero STACKS on top, tiles fill below.
  const hx = portrait ? W * 0.06 : W * 0.06, hy = portrait ? H * 0.11 : H * 0.26;
  const hw = portrait ? W * 0.88 : W * 0.36, hh = portrait ? H * 0.2 : H * 0.5;
  const gx = portrait ? W * 0.06 : W * 0.47, gy = portrait ? hy + hh + H * 0.03 : H * 0.2;
  const gw = portrait ? W * 0.88 : W * 0.47;
  // as tall as the zone allows, never into the caption band ('browser agent' sat 39px inside it at 9:16)
  const gh = Math.min(portrait ? H * 0.58 : H * 0.62, contentBottom(W, H) - gy);
  // two to a row — one tile alone takes the whole row rather than half of it beside an empty slot
  const cols = Math.min(2, tiles.length), rows = Math.ceil(tiles.length / cols), tgap = 22;
  const tw = (gw - tgap) / cols, th = (gh - tgap * (rows - 1)) / rows;
  const heroE = easeOutBack(clamp01(seg(t, 0.04, 0.3)));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 100% at 28% 22%, #12162a, #0a0c12 72%)'}}>
      {/* hero panel */}
      <div style={{position: 'absolute', left: hx, top: hy, width: hw, height: hh, borderRadius: 22,
        background: `linear-gradient(150deg, ${accent}, #0e5c46)`, boxShadow: '0 24px 60px #0008',
        opacity: clamp01(heroE * 1.4), transform: `scale(${lerp(0.9, 1, heroE)})`, transformOrigin: 'center',
        padding: 48, display: 'flex', flexDirection: 'column', justifyContent: 'space-between'}}>
        <div style={{color: '#eafff7cc', font: `600 22px/${leading(markLabel, 1)} var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.14em'}}>{markLabel}</div>
        <div>
          <div style={{color: '#fff', font: `800 60px/1.05 var(--f-body, Inter, system-ui, sans-serif)`, letterSpacing: '-0.02em', textWrap: 'balance'}}>{title}</div>
          <div style={{color: '#eafff7dd', font: `500 27px/1.3 var(--f-body, Inter, system-ui, sans-serif)`, textWrap: 'balance', marginTop: 16}}>{subtitle}</div>
        </div>
      </div>
      {/* product tiles */}
      {tiles.map((tile, i) => {
        const c = i % cols, r = Math.floor(i / cols);
        const x = gx + c * (tw + tgap), y = gy + r * (th + tgap);
        const st = 0.16 + i * 0.12;
        const e = easeOutBack(clamp01(seg(t, st, st + 0.28)));
        const g = clamp01(seg(t, st + 0.05, st + 0.55));
        const tone = TONES[i % TONES.length];
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, width: tw, height: th, borderRadius: 20,
            background: 'linear-gradient(160deg, #15192880, #0d0f18)', border: `1px solid ${tone}55`,
            opacity: clamp01(e * 1.4), transform: `scale(${lerp(0.86, 1, e)})`, transformOrigin: 'center',
            padding: 34, display: 'flex', flexDirection: 'column', justifyContent: tile.glyph ? 'space-between' : 'flex-end',
            boxShadow: `0 18px 44px #0006, inset 0 0 60px ${tone}0e`}}>
            {tile.glyph ? <Glyph kind={tile.glyph} c={tone} g={g} /> : null}
            <div>
              <div style={{color: '#eef2ff', font: `800 34px/1 var(--f-body, Inter, system-ui, sans-serif)`, letterSpacing: '-0.01em', textWrap: 'balance'}}>{tile.label}</div>
              {tile.note ? <div style={{color: '#9aa4ba', font: `500 20px/1.2 var(--f-body, Inter, system-ui, sans-serif)`, textWrap: 'balance', marginTop: 8}}>{tile.note}</div> : null}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default PlatformSurfaces;
