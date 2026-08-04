import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Theme} from './Video';

// DIEGETIC BRIDGE — an in-world "advance gesture" that carries the film from THIS scene into the next
// (type-a-command-and-Enter, click-a-control, …) instead of a plain editorial cut. It is a SCREEN-FIXED
// overlay played over the OUTGOING scene's own TAIL (the last ~1.4s, over the narration's end + breath),
// so it never eats live narration and needs no transition-overlap extension (which would double-audio) —
// the ordinary cut/dip then reveals the next scene as the "output" of the gesture.
//
// Frame-safe by construction: everything is a pure function of useCurrentFrame() (typed substring, caret
// blink, Enter flash) — no CSS transition/@keyframes/setInterval. One gesture per film, chosen from the
// deck's aesthetic (render_remotion derives it from theme.style/fontKind); reduced-motion → no gesture.
// The full gesture menu + per-aesthetic mapping lives in references/camera-and-bridges.md.

export type BridgeData = {gesture: string; label?: string; atFrame?: number} | null;

export const BridgeOverlay: React.FC<{bridge: BridgeData; theme: Theme; reducedMotion?: boolean}> = ({
  bridge,
  theme,
  reducedMotion,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  if (!bridge || !bridge.gesture || bridge.gesture === 'none' || reducedMotion) return null;

  const dur = Math.max(1, durationInFrames);
  const play = Math.round(1.4 * fps); // the gesture occupies the last ~1.4s of the scene
  const start = bridge.atFrame != null ? bridge.atFrame : Math.max(0, dur - play);
  if (frame < start) return null;
  const t = frame - start; // scene-local frames since the gesture began

  const mono = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace';
  const go = '#4fe08a'; // terminal-green prompt / GO
  const accent = theme?.accent || '#f5a623';

  if (bridge.gesture === 'type-enter') {
    const label = (bridge.label || 'continue').trim();
    const perChar = 2.2; // ~2 frames/char
    const nChars = Math.floor(t / perChar);
    const typed = label.slice(0, Math.max(0, nChars));
    const typedDone = nChars >= label.length;
    const enterFrame = Math.round(label.length * perChar) + 9; // hold ~9f on the full line, then ENTER
    const entered = t >= enterFrame;
    const caretOn = Math.floor(frame / 15) % 2 === 0;
    const flash = entered ? Math.max(0, 1 - (t - enterFrame) / 5) * 0.26 : 0;
    // ease the bar in, and out just before the cut so it never hard-pops at the seam
    const inO = Math.min(1, t / 5);
    const outO = frame > dur - 5 ? Math.max(0, (dur - frame) / 5) : 1;
    const barOpacity = inO * outO;
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <div
          style={{
            position: 'absolute',
            left: '50%',
            bottom: 232, // clear of the ~14% bottom caption zone
            transform: 'translateX(-50%)',
            opacity: barOpacity,
            background: '#0b0f14ee',
            border: `1px solid ${accent}33`,
            borderRadius: 12,
            padding: '16px 28px',
            fontFamily: mono,
            fontSize: 34,
            color: '#E7EDF3',
            boxShadow: '0 24px 70px rgba(0,0,0,.55)',
            whiteSpace: 'pre',
            // safety cap so a long command can never run off both frame edges (a length lint keeps it short).
            maxWidth: 1500,
            overflow: 'hidden',
          }}
        >
          <span style={{color: go, fontWeight: 700}}>$ </span>
          {typed}
          <span
            style={{
              background: caretOn && !entered ? go : 'transparent',
              color: '#0b0f14',
              marginLeft: 1,
            }}
          >
            &nbsp;
          </span>
          {typedDone ? (
            <span style={{color: entered ? accent : '#6b7680', marginLeft: 14, fontWeight: 700}}>⏎</span>
          ) : null}
        </div>
        {flash > 0 ? (
          <AbsoluteFill style={{background: accent, opacity: flash, mixBlendMode: 'screen'}} />
        ) : null}
      </AbsoluteFill>
    );
  }

  // Other gestures (cursor-click, page-turn, control-toggle, …) are specified in
  // references/camera-and-bridges.md; until natively rendered they fall through to a plain cut.
  return null;
};
