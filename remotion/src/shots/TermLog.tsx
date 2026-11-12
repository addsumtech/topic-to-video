// SHOT · TermLog — a TERMINAL-NATIVE streaming build/pipeline log. Default OPEN (grammar, no window box): a
// command executes and lines print one-by-one on the open canvas, → (step) / ✓ (done) / # (note). `framed` =
// explicit terminal window. Deterministic (line reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {rows} from '../runtime/rows';
import {useDNA, TermFrame, termInnerW} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import type {SoundDecl} from '../runtime/sound';

export const DURATION = 165;
// a key on each character of the command as TermFrame types it (round(n * u) over [0.05, 0.16], runtime/dna.tsx)
export const SOUNDS: readonly SoundDecl[] = [
  {kind: 'key', type: 'cmd', at: 0.05, to: 0.16, draw: 'round'},
] as const;
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
  // A THEMED FILM'S LOG IS SET TO ITS ROOM (craft standard, 2026-11-12): two short lines at a fixed 40 px were specks in
  // the frame. Up to 72 px, bounded by the zone's height and the longest line against TermFrame's width.
  const longest = Math.max(4, ...lines.map((l) => [...String(l.text ?? '')].length + 3));
  const FS = dna ? Math.max(40, Math.min(72, Math.floor(((contentBottom(W, H) - CONTENT_TOP) * 0.62) / (n * 1.85)),
    Math.floor((termInnerW(W, framed) * 0.92) / (longest * 0.6)))) : 40;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        <div style={{font: `500 ${FS}px/1.85 ${mono}`}}>
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
                {i === cur ? <span style={{display: 'inline-block', width: Math.round(FS * 0.35), height: Math.round(FS * 0.75), marginLeft: 4,
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
