// SHOT · Code Compose — the dev-native register: a real IDE panel where syntax-highlighted code TYPES ITSELF
// line by line with a blinking caret + a line-number gutter, then an output strip resolves to "✓ done". Fits
// WorkBuddy-as-agent (it writes + runs the work). Deterministic (revealed chars = fn of t; caret blink = frame).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';

export const DURATION = 165; // 5.5s
type Tok = {t: string; c: string};
const C = {kw: '#ff7bd5', fn: '#7ee0ff', str: '#9df2a0', com: '#6b7688', num: '#ffd88a', pl: '#d9e0ea', op: '#c8b6ff'};
// hand-tokenized so highlighting is deterministic + correct (no fragile regex at render time)
const DEFAULT_LINES: Tok[][] = [
  [{t: '# WorkBuddy runs locally — on your machine', c: C.com}],
  [{t: 'def ', c: C.kw}, {t: 'handle', c: C.fn}, {t: '(task):', c: C.pl}],
  [{t: '    plan   = ', c: C.pl}, {t: 'buddy', c: C.fn}, {t: '.think(task)', c: C.pl}],
  [{t: '    draft  = ', c: C.pl}, {t: 'buddy', c: C.fn}, {t: '.draft(plan)', c: C.pl}],
  [{t: '    result = ', c: C.pl}, {t: 'buddy', c: C.fn}, {t: '.review(draft)', c: C.pl}],
  [{t: '    return', c: C.kw}, {t: ' result', c: C.pl}, {t: '      # ✓ shipped', c: C.com}],
];
const CHW = 20.4, LH = 58, FS = 34;
const lineLen = (l: Tok[]) => l.reduce((s, k) => s + k.t.length, 0);

export const CodeCompose: React.FC<{filename?: string; lines?: (Tok[] | string)[]; status?: string}> = ({
  filename = 'workbuddy.py', lines: LINESP, status: STATUS = '— shipped, on your machine'} = {}) => {
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  // topic code lines: default demo, or override — a plain string line is auto-coloured as plaintext.
  const LINES: Tok[][] = (LINESP ?? DEFAULT_LINES).map((l) => (typeof l === 'string' ? [{t: l, c: C.pl}] : l));
  const total = LINES.reduce((s, l) => s + lineLen(l) + 1, 0);
  const shown = Math.floor(total * clamp01(seg(t, 0.06, 0.66)));

  // window geometry
  const winW = 1180, winH = 620, wx = (W - winW) / 2, wy = (H - winH) / 2 - 30;
  const gx = wx + 40, gy = wy + 118, textX = gx + 64;

  // per-line reveal (clean, single pass) + caret at the true typing head
  let acc = 0;
  let caretX = textX, caretY = gy, caretLine = 0;
  const rendered: React.ReactNode[] = [];
  LINES.forEach((line, li) => {
    const yy = gy + li * LH;
    const before = acc;              // chars consumed before this line
    const chars = lineLen(line);
    const revealedHere = Math.max(0, Math.min(chars, shown - before));
    // spans up to revealedHere
    let col = 0; const spans: React.ReactNode[] = [];
    for (const tok of line) {
      const take = Math.max(0, Math.min(tok.t.length, revealedHere - col));
      if (take > 0) spans.push(<tspan key={col} fill={tok.c}>{tok.t.slice(0, take)}</tspan>);
      col += tok.t.length;
      if (col >= revealedHere) break;
    }
    rendered.push(
      <text key={li} x={textX} y={yy} style={{font: `600 ${FS}px/1 "JetBrains Mono", ui-monospace, monospace`, whiteSpace: 'pre'}} dominantBaseline="hanging">{spans}</text>
    );
    rendered.push(<text key={`g${li}`} x={gx + 40} y={yy} textAnchor="end" style={{font: `600 ${FS}px/1 "JetBrains Mono", monospace`}} fill="#39414d" dominantBaseline="hanging">{li + 1}</text>);
    // caret lives on the last line that has begun revealing
    if (shown > before && revealedHere < chars) {caretX = textX + revealedHere * CHW; caretY = yy; caretLine = li;}
    else if (shown >= before + chars) {caretX = textX + chars * CHW; caretY = yy; caretLine = li;}
    acc += chars + 1; // + newline
  });

  const typingDone = shown >= total;
  const caretOn = typingDone ? (frame % 30 < 16) : true;
  const outT = clamp01(seg(t, 0.72, 0.9));

  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 20%, #10151d, #080a0e 70%)'}}>
      {/* window */}
      <div style={{position: 'absolute', left: wx, top: wy, width: winW, height: winH, borderRadius: 18,
        background: '#0d1117', border: '1px solid #202836', boxShadow: '0 40px 120px #000a', overflow: 'hidden'}}>
        <div style={{height: 52, background: '#131a24', borderBottom: '1px solid #202836', display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 20}}>
          {['#ff5f57', '#febc2e', '#28c840'].map((c) => <div key={c} style={{width: 14, height: 14, borderRadius: 7, background: c}} />)}
          <div style={{marginLeft: 18, padding: '6px 16px', borderRadius: 8, background: '#0d1117', color: '#8b96a6', font: '600 24px/1 "JetBrains Mono", monospace'}}>{filename}</div>
        </div>
      </div>
      {/* code layer */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <line x1={gx + 54} y1={wy + 104} x2={gx + 54} y2={wy + winH - 130} stroke="#1b2430" strokeWidth={2} />
        {rendered}
        {caretOn && <rect x={caretX + 2} y={caretY - 2} width={3} height={FS + 6} fill="#7ee0ff" />}
      </svg>
      {/* output strip */}
      <div style={{position: 'absolute', left: wx, top: wy + winH - 96, width: winW, height: 96,
        borderTop: '1px solid #202836', background: '#0b1016', display: 'flex', alignItems: 'center', gap: 20,
        paddingLeft: 34, opacity: outT, borderRadius: '0 0 18px 18px'}}>
        <span style={{color: '#5a6577', font: '700 30px/1 "JetBrains Mono", monospace'}}>▶</span>
        <span style={{color: '#9df2a0', font: '700 32px/1 "JetBrains Mono", monospace'}}>✓ done</span>
        <span style={{color: '#5a6577', font: '600 30px/1 "JetBrains Mono", monospace'}}>{STATUS}</span>
      </div>
    </AbsoluteFill>
  );
};
export default CodeCompose;
