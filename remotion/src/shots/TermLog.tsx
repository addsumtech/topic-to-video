// SHOT · TermLog — a TERMINAL-NATIVE streaming build/pipeline log. Default OPEN (grammar, no window box): a
// command executes and lines print one-by-one on the open canvas, → (step) / ✓ (done) / # (note). `framed` =
// explicit terminal window. Deterministic (line reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {rows} from '../runtime/rows';
import {useDNA, TermFrame} from '../runtime/dna';

export const DURATION = 165;
type Line = {text?: string; kind?: 'run' | 'ok' | 'info'};

export const TermLog: React.FC<{cmd?: string; lines?: Line[]; framed?: boolean}> = ({
  cmd = 'build --pipeline', framed = false,
  lines: lines_IN = [{text: 'step one', kind: 'run'}, {text: 'done', kind: 'ok'}]} = {}) => {
  const lines = rows<Line>(lines_IN, 'lines', 'TermLog');
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const fg = dna?.fg ?? '#cdd7e4', dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4', acc2 = dna?.accent2 ?? '#4d8cff';
  const caretOn = Math.floor(frame / 16) % 2 === 0;
  const n = lines.length;
  const cur = Math.min(n - 1, Math.floor(clamp01(seg(t, 0.22, 0.92)) * n));
  const glyph = (k?: string) => k === 'ok' ? {c: acc, s: '✓'} : k === 'info' ? {c: dim, s: '#'} : {c: acc2, s: '→'};

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        <div style={{font: `500 40px/1.85 ${mono}`}}>
          {lines.map((ln, i) => {
            const start = 0.24 + i * (0.66 / Math.max(1, n));
            const show = clamp01(seg(t, start, start + 0.06));
            if (show <= 0) return null;
            const g = glyph(ln.kind);
            return (
              <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: 20, opacity: show,
                transform: `translateX(${(1 - show) * -12}px)`, color: ln.kind === 'info' ? dim : fg}}>
                <span style={{color: g.c, width: '1.4ch'}}>{g.s}</span>
                <span>{ln.text}</span>
                {i === cur ? <span style={{display: 'inline-block', width: 14, height: 30, marginLeft: 4,
                  verticalAlign: 'text-bottom', background: acc, opacity: caretOn ? 0.9 : 0.12}} /> : null}
              </div>
            );
          })}
        </div>
      </TermFrame>
    </AbsoluteFill>
  );
};
export default TermLog;
