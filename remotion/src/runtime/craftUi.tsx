// CRAFT KIT · UI — publication-grade interface parts for product shots (references/craft-standard.md §UI).
//
// WHY (2026-11-12): side by side with a peer library's redesigned shots, our product UIs were grey skeleton bars and
// placeholder words ("series one", "first record") at 20-30 px; theirs were the same layouts with believable content —
// a metric with its delta and sparkline, avatars, status chips, a real button — set larger, with fewer elements.
// "A UI designed for the shot": fewer elements, bigger type, stronger contrast, but it must still look like a real
// product. These parts are that, as components: every word and value is a PROP (the film supplies its own; the parts
// never invent a number), every size is in px the caller chooses, and the look comes from one `UiTheme`.
import React from 'react';
import {mix} from './dna';
import {FONT_STACKS, tracking} from './craftType';
import {rgba, softShadow, isDark} from './craftStage';

export type UiTheme = {surface: string; surface2: string; line: string; ink: string; ink2: string; ink3: string;
  accent: string; onAccent: string; good: string; warn: string; shadowTint: string; radius: number; font: string; mono: string};

/** A theme from a ground and an accent: light grounds get a white work surface; dark grounds a tinted near-black one. */
export const uiTheme = (ground: string, accent: string, opts: Partial<UiTheme> = {}): UiTheme => {
  const dark = isDark(ground);
  return {
    surface: dark ? mix(ground, '#ffffff', 0.06) : '#ffffff',
    surface2: dark ? mix(ground, '#ffffff', 0.1) : mix(ground, '#ffffff', 0.6),
    line: dark ? 'rgba(255,255,255,0.09)' : 'rgba(15,30,25,0.09)',
    ink: dark ? '#f2f5f3' : '#121614', ink2: dark ? '#aab4af' : '#4d5752', ink3: dark ? '#6b7570' : '#8d9691',
    accent, onAccent: isDark(accent) ? '#ffffff' : '#08130f', good: '#12b886', warn: '#f59f00',
    shadowTint: dark ? '#000000' : mix(ground, '#0b1a14', 0.8), radius: 18, font: FONT_STACKS.sans, mono: FONT_STACKS.mono,
    ...opts,
  };
};

const txt = (px: number, w: number, c: string, font: string, extra: React.CSSProperties = {}): React.CSSProperties =>
  ({fontFamily: font, fontSize: px, fontWeight: w, color: c, letterSpacing: tracking(px), lineHeight: 1.25, whiteSpace: 'nowrap', ...extra});

/** A desktop app window: title bar with traffic lights, an optional sidebar, a work area. Sizes in px. */
export const AppWindow: React.FC<{w: number; h: number; theme: UiTheme; title?: string; scale?: number;
  sidebar?: {width: number; brand?: React.ReactNode; items: {label: string; active?: boolean; badge?: string}[]};
  children?: React.ReactNode; style?: React.CSSProperties}> = ({w, h, theme: t, title, scale = 1, sidebar, children, style}) => {
  const bar = 44 * scale;
  return (
    <div style={{position: 'absolute', width: w, height: h, borderRadius: t.radius * scale, overflow: 'hidden', background: t.surface,
      border: `1px solid ${t.line}`, boxShadow: `inset 0 1px 0 rgba(255,255,255,0.6), ${softShadow(3, t.shadowTint)}`, ...style}}>
      <div style={{height: bar, display: 'flex', alignItems: 'center', gap: 8 * scale, padding: `0 ${16 * scale}px`,
        borderBottom: `1px solid ${t.line}`, background: t.surface2}}>
        {['#ff5f57', '#febc2e', '#28c840'].map((c) => <span key={c} style={{width: 12 * scale, height: 12 * scale, borderRadius: '50%', background: c}} />)}
        {title ? <span style={{...txt(15 * scale, 600, t.ink2, t.font), marginLeft: 'auto', marginRight: 'auto'}}>{title}</span> : null}
      </div>
      <div style={{position: 'absolute', top: bar, left: 0, right: 0, bottom: 0, display: 'flex'}}>
        {sidebar ? (
          <div style={{width: sidebar.width, flex: 'none', borderRight: `1px solid ${t.line}`, background: t.surface2,
            padding: `${18 * scale}px ${12 * scale}px`, display: 'flex', flexDirection: 'column', gap: 4 * scale}}>
            {sidebar.brand ? <div style={{marginBottom: 14 * scale, paddingLeft: 8 * scale}}>{sidebar.brand}</div> : null}
            {sidebar.items.map((it, i) => (
              <div key={i} style={{display: 'flex', alignItems: 'center', gap: 10 * scale, padding: `${9 * scale}px ${10 * scale}px`,
                borderRadius: 10 * scale, background: it.active ? rgba(t.accent, 0.12) : 'transparent'}}>
                <span style={{width: 8 * scale, height: 8 * scale, borderRadius: 3 * scale, background: it.active ? t.accent : t.ink3, opacity: it.active ? 1 : 0.5}} />
                <span style={txt(17 * scale, it.active ? 650 : 500, it.active ? t.ink : t.ink2, t.font)}>{it.label}</span>
                {it.badge ? <span style={{...txt(13 * scale, 650, t.onAccent, t.font), marginLeft: 'auto', background: t.accent,
                  borderRadius: 99, padding: `${2 * scale}px ${8 * scale}px`}}>{it.badge}</span> : null}
              </div>
            ))}
          </div>
        ) : null}
        <div style={{position: 'relative', flex: 1, overflow: 'hidden'}}>{children}</div>
      </div>
    </div>
  );
};

/** A pointer with an optional name tag (the collaborative-cursor device) and a click ring at `click` 0..1. */
export const Cursor: React.FC<{x: number; y: number; size?: number; color?: string; label?: string; click?: number; ink?: string}> =
  ({x, y, size = 34, color = '#121614', label, click = 0, ink = '#ffffff'}) => (
    <div style={{position: 'absolute', left: x, top: y, pointerEvents: 'none'}}>
      {click > 0 && click < 1 ? <div style={{position: 'absolute', left: -size * click, top: -size * click, width: size * 2 * click,
        height: size * 2 * click, borderRadius: '50%', border: `${size * 0.08}px solid ${rgba(color, 0.5 * (1 - click))}`}} /> : null}
      <svg width={size} height={size} viewBox="0 0 24 24" style={{overflow: 'visible', filter: `drop-shadow(0 ${size * 0.08}px ${size * 0.14}px rgba(0,0,0,0.3))`,
        transform: `scale(${1 - 0.12 * Math.sin(Math.PI * Math.min(1, click * 2))})`, transformOrigin: '0 0'}}>
        <path d="M3 2 L3 19.5 L8 15 L11.5 22 L14.5 20.6 L11.2 13.8 L18 13.6 Z" fill={color} stroke={ink} strokeWidth={1.6} strokeLinejoin="round" />
      </svg>
      {label ? <div style={{position: 'absolute', left: size * 0.62, top: size * 0.78, background: color, color: ink, borderRadius: size * 0.3,
        padding: `${size * 0.1}px ${size * 0.28}px`, ...txt(size * 0.44, 650, ink, FONT_STACKS.sans)}}>{label}</div> : null}
    </div>
  );

export type ChipTone = 'neutral' | 'accent' | 'good' | 'warn' | 'solid';
export const Chip: React.FC<{text: string; theme: UiTheme; px: number; tone?: ChipTone; dot?: boolean; style?: React.CSSProperties}> =
  ({text, theme: t, px, tone = 'neutral', dot, style}) => {
    const c = tone === 'accent' ? t.accent : tone === 'good' ? t.good : tone === 'warn' ? t.warn : t.ink2;
    const solid = tone === 'solid';
    return (
      <span style={{display: 'inline-flex', alignItems: 'center', gap: px * 0.4, padding: `${px * 0.28}px ${px * 0.7}px`, borderRadius: 999,
        background: solid ? t.ink : tone === 'neutral' ? t.surface2 : rgba(c, 0.13), border: `1px solid ${solid ? t.ink : tone === 'neutral' ? t.line : rgba(c, 0.25)}`,
        ...txt(px, 620, solid ? t.surface : tone === 'neutral' ? t.ink2 : mix(c, t.ink, 0.25), t.font), ...style}}>
        {dot ? <span style={{width: px * 0.45, height: px * 0.45, borderRadius: '50%', background: c}} /> : null}{text}
      </span>
    );
  };

export const Button: React.FC<{text: string; theme: UiTheme; px: number; primary?: boolean; style?: React.CSSProperties}> =
  ({text, theme: t, px, primary = true, style}) => (
    <span style={{display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: `${px * 0.55}px ${px * 1.1}px`,
      borderRadius: px * 0.6, background: primary ? t.accent : t.surface, border: `1px solid ${primary ? 'transparent' : t.line}`,
      boxShadow: primary ? `0 ${px * 0.2}px ${px * 0.6}px ${rgba(t.accent, 0.35)}` : undefined, ...txt(px, 650, primary ? t.onAccent : t.ink, t.font), ...style}}>{text}</span>
  );

export const Avatar: React.FC<{initials: string; color: string; size: number; ring?: string}> = ({initials, color, size, ring}) => (
  <span style={{width: size, height: size, borderRadius: '50%', flex: 'none', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    background: `linear-gradient(160deg, ${mix(color, '#ffffff', 0.25)}, ${color})`, boxShadow: ring ? `0 0 0 ${size * 0.06}px ${ring}` : undefined,
    ...txt(size * 0.38, 700, isDark(color) ? '#ffffff' : '#111111', FONT_STACKS.sans)}}>{initials}</span>
);

/** A sparkline of a SHAPE (values only set the curve; draw no axis numbers unless the film supplies real ones). */
export const Sparkline: React.FC<{values: number[]; w: number; h: number; color: string; progress?: number; fill?: boolean; stroke?: number}> =
  ({values, w, h, color, progress = 1, fill = true, stroke = 3}) => {
    if (values.length < 2) return null;
    const lo = Math.min(...values), hi = Math.max(...values), span = hi - lo || 1;
    const pts = values.map((v, i) => [(i / (values.length - 1)) * w, h - ((v - lo) / span) * h * 0.86 - h * 0.07]);
    const d = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
    const id = `sp${Math.round(w)}${Math.round(h)}${values.length}`;
    return (
      <svg width={w} height={h} style={{overflow: 'visible'}}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={color} stopOpacity={0.28} /><stop offset="1" stopColor={color} stopOpacity={0} /></linearGradient>
          <clipPath id={`${id}c`}><rect x={-stroke} y={-h} width={(w + stroke * 2) * Math.max(0, Math.min(1, progress))} height={h * 3} /></clipPath>
        </defs>
        <g clipPath={`url(#${id}c)`}>
          {fill ? <path d={`${d} L${w},${h} L0,${h} Z`} fill={`url(#${id})`} /> : null}
          <path d={d} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" />
        </g>
      </svg>
    );
  };

const EXT_COLOR: Record<string, string> = {xlsx: '#1d8a4e', csv: '#1d8a4e', docx: '#2b5fd9', doc: '#2b5fd9', pptx: '#d2502c',
  pdf: '#d93a3a', md: '#5b6470', html: '#e2731d', png: '#8a4fd8', jpg: '#8a4fd8', zip: '#6b6b6b', txt: '#5b6470'};
/** A file as a badge + name row. */
export const FileBadge: React.FC<{name: string; theme: UiTheme; px: number; ext?: string; note?: string; style?: React.CSSProperties}> =
  ({name, theme: t, px, ext, note, style}) => {
    const e = (ext ?? name.split('.').pop() ?? '').toLowerCase();
    const c = EXT_COLOR[e] ?? t.ink3;
    return (
      <div style={{display: 'flex', alignItems: 'center', gap: px * 0.6, ...style}}>
        <span style={{width: px * 1.7, height: px * 2.05, borderRadius: px * 0.25, background: c, flex: 'none', position: 'relative',
          display: 'inline-flex', alignItems: 'flex-end', justifyContent: 'center', paddingBottom: px * 0.22,
          clipPath: `polygon(0 0, 68% 0, 100% 26%, 100% 100%, 0 100%)`}}>
          <span style={txt(px * 0.46, 800, '#ffffff', t.font, {letterSpacing: '0.02em'})}>{e.toUpperCase()}</span>
        </span>
        <span style={{display: 'flex', flexDirection: 'column'}}>
          <span style={txt(px, 600, t.ink, t.font)}>{name}</span>
          {note ? <span style={txt(px * 0.72, 500, t.ink3, t.font)}>{note}</span> : null}
        </span>
      </div>
    );
  };

/** A labelled value with an optional delta and sparkline. The value is the film's (a prop), never made up here. */
export const MetricTile: React.FC<{label: string; value: string; theme: UiTheme; px: number; delta?: string; deltaGood?: boolean;
  spark?: number[]; w: number; progress?: number}> = ({label, value, theme: t, px, delta, deltaGood = true, spark, w, progress = 1}) => (
  <div style={{width: w, padding: px * 0.9, borderRadius: t.radius, background: t.surface, border: `1px solid ${t.line}`,
    boxShadow: softShadow(1, t.shadowTint), display: 'flex', flexDirection: 'column', gap: px * 0.35}}>
    <span style={txt(px * 0.62, 600, t.ink3, t.font, {textTransform: 'uppercase', letterSpacing: '0.08em'})}>{label}</span>
    <span style={{display: 'flex', alignItems: 'baseline', gap: px * 0.5}}>
      <span style={txt(px * 1.6, 760, t.ink, t.font)}>{value}</span>
      {delta ? <span style={txt(px * 0.7, 700, deltaGood ? t.good : t.warn, t.font)}>{delta}</span> : null}
    </span>
    {spark ? <Sparkline values={spark} w={w - px * 1.8} h={px * 1.6} color={t.accent} progress={progress} /> : null}
  </div>
);

/** A step of a plan: todo · running (spinner) · done (check). */
export const StepRow: React.FC<{text: string; theme: UiTheme; px: number; state: 'todo' | 'running' | 'done'; spin?: number}> =
  ({text, theme: t, px, state, spin = 0}) => (
    <div style={{display: 'flex', alignItems: 'center', gap: px * 0.6}}>
      <span style={{width: px * 1.1, height: px * 1.1, borderRadius: '50%', flex: 'none', display: 'inline-flex', alignItems: 'center',
        justifyContent: 'center', background: state === 'done' ? t.accent : 'transparent',
        border: state === 'done' ? 'none' : `${px * 0.1}px solid ${state === 'running' ? rgba(t.accent, 0.3) : t.line}`,
        borderTopColor: state === 'running' ? t.accent : undefined, transform: state === 'running' ? `rotate(${spin}deg)` : undefined}}>
        {state === 'done' ? <svg width={px * 0.62} height={px * 0.62} viewBox="0 0 12 12"><path d="M2 6.4 L4.8 9 L10 3.2" fill="none" stroke={t.onAccent} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" /></svg> : null}
      </span>
      <span style={txt(px, state === 'todo' ? 500 : 600, state === 'todo' ? t.ink3 : t.ink, t.font)}>{text}</span>
    </div>
  );

/** A prompt box with typed text and a caret; `typed` 0..1 of `text`. */
export const PromptBox: React.FC<{text: string; typed: number; theme: UiTheme; px: number; w: number; placeholder?: string;
  send?: React.ReactNode; caretOn?: boolean; style?: React.CSSProperties}> = ({text, typed, theme: t, px, w, placeholder, send, caretOn = true, style}) => {
  const n = Math.round(Math.max(0, Math.min(1, typed)) * Array.from(text).length);
  const shown = Array.from(text).slice(0, n).join('');
  return (
    <div style={{width: w, padding: `${px * 0.9}px ${px}px`, borderRadius: t.radius * 1.1, background: t.surface,
      border: `${Math.max(1, px * 0.07)}px solid ${rgba(t.accent, 0.55)}`, boxShadow: `0 0 0 ${px * 0.28}px ${rgba(t.accent, 0.12)}, ${softShadow(2, t.shadowTint)}`,
      display: 'flex', alignItems: 'center', gap: px * 0.6, ...style}}>
      <span style={{...txt(px, 520, n ? t.ink : t.ink3, t.font), flex: 1, overflow: 'hidden'}}>
        {n ? shown : placeholder}{caretOn ? <span style={{display: 'inline-block', width: Math.max(2, px * 0.08), height: px * 1.1,
          verticalAlign: 'middle', marginLeft: px * 0.05, background: t.accent}} /> : null}
      </span>
      {send ?? null}
    </div>
  );
};

/** A small notification card (the celebration / done moment). */
export const Toast: React.FC<{title: string; body?: string; theme: UiTheme; px: number; w: number}> = ({title, body, theme: t, px, w}) => (
  <div style={{width: w, display: 'flex', gap: px * 0.7, alignItems: 'flex-start', padding: px * 0.9, borderRadius: t.radius,
    background: t.surface, border: `1px solid ${t.line}`, boxShadow: softShadow(2, t.shadowTint)}}>
    <span style={{width: px * 1.5, height: px * 1.5, borderRadius: '50%', background: t.good, flex: 'none', display: 'inline-flex',
      alignItems: 'center', justifyContent: 'center'}}>
      <svg width={px * 0.8} height={px * 0.8} viewBox="0 0 12 12"><path d="M2 6.4 L4.8 9 L10 3.2" fill="none" stroke="#ffffff" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" /></svg>
    </span>
    <span style={{display: 'flex', flexDirection: 'column', gap: px * 0.15}}>
      <span style={txt(px, 700, t.ink, t.font)}>{title}</span>
      {body ? <span style={txt(px * 0.8, 500, t.ink2, t.font, {whiteSpace: 'normal'})}>{body}</span> : null}
    </span>
  </div>
);
