// CRAFT KIT · TYPE — the type ladder and the reveal every built shot uses (references/craft-standard.md §Type).
//
// WHY (2026-11-12, the video-shotcraft study + 12 SaaS launch films): in the films that read as designed, type is BIG
// and has a hierarchy — a display line, a kicker, a folio — and a headline arrives word by word with the key word in the
// accent and the tail still ghosted (Perplexity's "Ask anything. anywhere.", Slack's multi-colour key word). Our
// registers measured a median subject extent of 0.30 of the frame against 0.70, and most of our words were 20–40 px.
// THE LADDER is in px at 1080 lines and scales with the frame. Read-it type is >= `small` (32); a beat's headline is
// >= `h1` (120); a type beat's display line is `display`/`mega`. Below `small` is texture only (dimmed, never content).
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {EASE, type EaseName} from './craftMotion';

export const TYPE_LADDER = {mega: 260, display: 180, h1: 120, h2: 84, h3: 60, body: 40, small: 32, label: 22} as const;
export type TypeStep = keyof typeof TYPE_LADDER;

/** The ladder step in px for a frame of height H (portrait frames read the ladder off the WIDTH, so a 1080x1920 frame
 *  sets type as a 1080-wide one does). */
export const typePx = (step: TypeStep | number, W: number, H: number): number => {
  const base = typeof step === 'number' ? step : TYPE_LADDER[step];
  return Math.round(base * Math.min(W, H) / 1080);
};

export const FONT_STACKS = {
  sans: 'Inter, "Noto Sans SC", "PingFang SC", system-ui, sans-serif',
  grotesk: '"Space Grotesk", Inter, "Noto Sans SC", system-ui, sans-serif',
  serif: '"Source Serif 4", "Noto Serif SC", Georgia, serif',
  display: '"Playfair Display", "Noto Serif SC", Georgia, serif',
  mono: '"JetBrains Mono", "Noto Sans SC", ui-monospace, monospace',
} as const;

/** Tracking by size: large type is set tight, small caps are set open. */
export const tracking = (px: number, caps = false): string =>
  caps ? (px >= 40 ? '0.06em' : '0.12em') : px >= 160 ? '-0.045em' : px >= 90 ? '-0.035em' : px >= 50 ? '-0.02em' : '-0.005em';

/** One line of style for a step of the ladder. */
export const typeStyle = (px: number, opts: {weight?: number; family?: keyof typeof FONT_STACKS | string; caps?: boolean;
  italic?: boolean; color?: string} = {}): React.CSSProperties => ({
  fontFamily: opts.family ? (FONT_STACKS as Record<string, string>)[opts.family] ?? opts.family : FONT_STACKS.sans,
  fontSize: px, fontWeight: opts.weight ?? (px >= 90 ? 760 : px >= 50 ? 680 : 520),
  letterSpacing: tracking(px, opts.caps), lineHeight: px >= 90 ? 0.98 : px >= 50 ? 1.08 : 1.32,
  textTransform: opts.caps ? 'uppercase' : undefined, fontStyle: opts.italic ? 'italic' : undefined,
  fontVariantNumeric: 'tabular-nums lining-nums', color: opts.color,
});

const CJK = /[　-〿㐀-鿿豈-﫿＀-￯]/;

/** Split a line into reveal units: words (Latin), or single characters for CJK runs (a CJK punctuation mark stays
 *  with the character before it, so a line never starts with '，'). Spaces are kept as their own units. */
export const revealUnits = (text: string, by: 'word' | 'char' = 'word'): string[] => {
  const out: string[] = [];
  const tokens = text.match(/\s+|[^\s]+/g) ?? [];
  for (const tok of tokens) {
    if (/^\s+$/.test(tok)) { out.push(tok); continue; }
    if (by === 'char' || CJK.test(tok)) {
      for (const ch of Array.from(tok)) {
        if (out.length && /^[　-〿＀-￯，。！？、；：,.!?;:)）」』]$/.test(ch) && !/^\s+$/.test(out[out.length - 1]))
          out[out.length - 1] += ch;
        else out.push(ch);
      }
    } else out.push(tok);
  }
  return out;
};

const norm = (s: string) => s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');

export type RevealVariant = 'rise' | 'blur' | 'drop' | 'scale' | 'track';

/**
 * A line revealed unit by unit. `accent` names the words (case/punctuation-insensitive) drawn in `accentColor`;
 * `ghostFrom` keeps every unit from that index on at `ghostOpacity` until frame `ghostAt` (the trailing-clause device:
 * the line's end is visible but quiet until the voice reaches it). Settled units carry NO transform and NO filter, so
 * the resting frame is plain text the text gates can read and that never trembles.
 */
export const TextReveal: React.FC<{
  text: string; by?: 'word' | 'char'; variant?: RevealVariant; start?: number; each?: number; dur?: number;
  ease?: EaseName; accent?: string[]; accentColor?: string; ghostFrom?: number; ghostAt?: number; ghostOpacity?: number;
  style?: React.CSSProperties; unitStyle?: (unit: string, i: number) => React.CSSProperties | undefined;
}> = ({text, by = 'word', variant = 'rise', start = 0, each = 4, dur = 16, ease = 'snappy', accent = [], accentColor,
  ghostFrom, ghostAt = Infinity, ghostOpacity = 0.28, style, unitStyle}) => {
  const frame = useCurrentFrame();
  const units = revealUnits(text, by);
  const acc = new Set(accent.map(norm));
  let k = -1;
  return (
    <span style={{display: 'inline', ...style}}>
      {units.map((u, i) => {
        if (/^\s+$/.test(u)) return <span key={i}>{u}</span>;
        k += 1;
        const p = EASE[ease](Math.max(0, Math.min(1, (frame - start - k * each) / dur)));
        const ghost = ghostFrom !== undefined && k >= ghostFrom && frame < ghostAt;
        const settled = p >= 1;
        let transform: string | undefined, filter: string | undefined;
        if (!settled) {
          if (variant === 'rise') transform = `translateY(${(1 - p) * 0.42}em)`;
          if (variant === 'drop') transform = `translateY(${-(1 - p) * 0.5}em)`;
          if (variant === 'scale') transform = `scale(${0.7 + 0.3 * p})`;
          if (variant === 'blur' || variant === 'rise') filter = `blur(${(1 - p) * 0.14}em)`;
        }
        const ls = variant === 'track' && !settled ? `${(1 - p) * 0.3}em` : undefined;
        return (
          <span key={i} style={{display: 'inline-block', whiteSpace: 'pre', opacity: p * (ghost ? ghostOpacity : 1),
            transform, filter, letterSpacing: ls, color: acc.has(norm(u)) ? accentColor : undefined, ...unitStyle?.(u, k)}}>{u}</span>
        );
      })}
    </span>
  );
};

/** The frame (relative to `start`) at which a TextReveal of this text has fully landed. */
export const revealEnd = (text: string, by: 'word' | 'char' = 'word', each = 4, dur = 16): number =>
  (revealUnits(text, by).filter((u) => !/^\s+$/.test(u)).length - 1) * each + dur;

/** A small-caps kicker over a headline (the editorial hierarchy: kicker · headline · folio). */
export const Kicker: React.FC<{text: string; color?: string; px: number; mark?: string; style?: React.CSSProperties}> =
  ({text, color, px, mark, style}) => (
    <div style={{...typeStyle(px, {weight: 650, caps: true, family: 'sans', color}), display: 'flex', alignItems: 'center',
      gap: px * 0.6, ...style}}>
      {mark ? <span style={{width: px * 0.5, height: px * 0.5, borderRadius: '50%', background: mark, flex: 'none'}} /> : null}
      {text}
    </div>
  );

/** Hook form: the frame's ladder in px. */
export const useLadder = (): Record<TypeStep, number> => {
  const {width: W, height: H} = useVideoConfig();
  const out = {} as Record<TypeStep, number>;
  for (const k of Object.keys(TYPE_LADDER) as TypeStep[]) out[k] = typePx(k, W, H);
  return out;
};
