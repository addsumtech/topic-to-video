// CONTENT ATOMS — the parts a frame is built from, rendered in the FORM the active Design DNA speaks.
// A shot declares WHAT a part is (`<Bar value={0.88}/>`); the DNA decides how it looks (`████░` under a
// terminal system, a ruled scale under an editorial one). This is what makes one design language have a
// real variant per style instead of a recolour.
//
// Two rules hold every atom together:
//   1. TOTAL — no DNA, no `atoms`, or an unknown form all reach the NEUTRAL form. Never throw.
//   2. PURE — no remotion hooks and no internal animation, so a shot keeps ownership of timing and the
//      atoms can be unit-tested outside a Composition. Anything time-varying takes a `phase` prop.
import React from 'react';
import {useDNA, NEUTRAL_DNA, mix, type DesignDNA, type AtomForms} from './dna';

const FORMS = {
  bar: ['block', 'solid', 'ruled', 'pixel', 'dimension'],
  figure: ['mono', 'serif', 'display', 'segment'],
  list: ['tree', 'ruled', 'bullet', 'numbered'],
  label: ['prompt', 'kicker', 'spec', 'chip'],
  divider: ['scanline', 'hairline', 'dimension', 'dotted'],
  marker: ['caret', 'triangle', 'crosshair', 'arrow'],
} as const;
const NEUTRAL = {bar: 'solid', figure: 'display', list: 'bullet',
                 label: 'kicker', divider: 'hairline', marker: 'triangle'} as const;

/** The form this DNA speaks for `k` — or `fallbackForm` when the DNA declares no form for `k` at all — or
 *  the neutral form when there is no DNA, no `atoms`, no `fallbackForm`, or a value the atom does not
 *  implement. A DNA that DOES declare a form for `k` always wins over `fallbackForm` — the DNA still
 *  decides. `fallbackForm` only fills the gap left by "no opinion", the same `dna?.token ?? ORIGINAL`
 *  pattern used everywhere else in this runtime — so a shot can keep its own pre-atoms look under a truly
 *  un-themed film without weakening a themed DNA's authority. */
const formOf = <K extends keyof AtomForms>(dna: DesignDNA | null, k: K, fallbackForm?: NonNullable<AtomForms[K]>): string => {
  const f = dna?.atoms?.[k] as string | undefined;
  if (f && (FORMS[k] as readonly string[]).includes(f)) return f;
  if (fallbackForm && (FORMS[k] as readonly string[]).includes(fallbackForm as string)) return fallbackForm as string;
  return NEUTRAL[k];
};
const T = (dna: DesignDNA | null) => dna ?? NEUTRAL_DNA;   // token source; never null downstream

// ── Bar — a quantity ─────────────────────────────────────────────────────────────────────────────────
export const Bar: React.FC<{value: number; label?: string; tag?: string; tone?: string; ink?: string;
  width?: number; height?: number; size?: number; labelWidth?: number | string; cells?: number;
  track?: boolean; fallbackForm?: NonNullable<AtomForms['bar']>}> =
  ({value, label, tag, tone, ink, width = 420, height, size, labelWidth = 92, cells = 18, track = true,
    fallbackForm}) => {
    const dna = useDNA(); const d = T(dna); const form = formOf(dna, 'bar', fallbackForm);
    const v = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
    const acc = tone ?? d.accent;
    // ink lets a migrating shot keep its OWN label/value colour instead of the atom's defaults (dim label,
    // accent-tinted value) — symmetric with Figure.ink/tone. Omit it and nothing changes from before.
    const labelInk = ink ?? d.dim;
    const tagInk = ink ?? acc;
    // height overrides the bar element's own thickness in the graphical forms (solid/pixel) — default 18
    // unchanged for anyone that doesn't pass it. ruled/dimension stay their own fixed thin-scale geometry
    // regardless (a scale doesn't get "taller", its ticks would just look wrong at other proportions).
    const row: React.CSSProperties = {display: 'flex', alignItems: 'center', gap: 14, marginBottom: 10};
    const lab = label ? <span style={{color: labelInk, font: `500 20px/1 ${d.fontMono}`, minWidth: labelWidth}}>{label}</span> : null;
    const tg = tag ? <span style={{color: tagInk, font: `600 18px/1 ${d.fontMono}`, marginLeft: 12}}>{tag}</span> : null;

    if (form === 'block') {                       // terminal: a run of block characters
      // block is TermBars' reference shot — its font runs at the SHOT's own size (default 22 for any other
      // future caller), not a fixed one, so the migrated row keeps its original scale exactly.
      const fs = size ?? 22;
      const on = Math.round(cells * v);
      const labB = label ? <span style={{color: labelInk, font: `500 ${fs}px/1.2 ${d.fontMono}`, minWidth: labelWidth}}>{label}</span> : null;
      const tgB = tag ? <span style={{color: tagInk, font: `500 ${fs}px/1.2 ${d.fontMono}`, minWidth: '5ch', textAlign: 'right'}}>{tag}</span> : null;
      return <div style={{...row, font: `500 ${fs}px/1.2 ${d.fontMono}`}}>{labB}
        <span style={{letterSpacing: '-2px'}}>
          <span style={{color: acc}}>{'█'.repeat(on)}</span>
          <span style={{color: d.dim}}>{'░'.repeat(cells - on)}</span>
        </span>{tgB}</div>;
    }
    if (form === 'ruled') {                       // editorial/data: a hairline scale with a filled run
      return <div style={{...row}}>{lab}
        <span style={{position: 'relative', width, height: 18, borderBottom: `1px solid ${d.line}`}}>
          <span style={{position: 'absolute', left: 0, bottom: -1, width: `${v * 100}%`, height: 3, background: acc}} />
          {[0, .25, .5, .75, 1].map((t) => (
            <span key={t} style={{position: 'absolute', left: `${t * 100}%`, bottom: -1, width: 1, height: 6, background: d.line}} />
          ))}
        </span>{tg}</div>;
    }
    if (form === 'pixel') {                       // retro: discrete cells
      const pc = Math.max(4, Math.min(cells, 24)), on = Math.round(pc * v);
      return <div style={{...row}}>{lab}
        <span style={{display: 'flex', gap: 3}}>
          {Array.from({length: pc}, (_, i) => (
            <span key={i} style={{width: 14, height: height ?? 18, background: i < on ? acc : mix(d.surface, d.bg, .4)}} />
          ))}
        </span>{tg}</div>;
    }
    if (form === 'dimension') {                   // blueprint: a measured span with end ticks
      return <div style={{...row}}>{lab}
        <span style={{position: 'relative', width, height: 20}}>
          <span style={{position: 'absolute', left: 0, top: 9, width: `${v * 100}%`, height: 1.5, background: acc}} />
          <span style={{position: 'absolute', left: 0, top: 3, width: 1.5, height: 14, background: acc}} />
          <span style={{position: 'absolute', left: `${v * 100}%`, top: 3, width: 1.5, height: 14, background: acc}} />
          <span style={{position: 'absolute', left: `${v * 100}%`, top: -6, color: acc,
            font: `600 16px/1 ${d.fontMono}`, transform: 'translateX(-50%)'}}>{Math.round(v * 100)}</span>
        </span>{tg}</div>;
    }
    return <div style={{...row}}>{lab}                       {/* solid — the neutral form */}
      <span style={{width, height: height ?? 18, borderRadius: d.radius, overflow: 'hidden',
        background: track ? mix(d.surface, d.bg, .3) : 'transparent'}}>
        <span style={{display: 'block', width: `${v * 100}%`, height: '100%', borderRadius: d.radius, background: acc}} />
      </span>{tg}</div>;
  };

// ── Figure — one number ──────────────────────────────────────────────────────────────────────────────
export const Figure: React.FC<{value: string | number; unit?: string; size?: number; unitScale?: number;
  ink?: string; tone?: string; gap?: number; fallbackForm?: NonNullable<AtomForms['figure']>; fallbackFamily?: string}> =
  ({value, unit, size = 150, unitScale, ink, tone, gap, fallbackForm, fallbackFamily}) => {
    const dna = useDNA(); const d = T(dna); const form = formOf(dna, 'figure', fallbackForm);
    const txt = String(value ?? '');
    // ink/tone let a migrating shot keep ITS OWN colours (each of the four reference shots painted its
    // number differently, and none matched these defaults) — omit both and a DNA's own fg/accent speak.
    const fg = ink ?? d.fg;
    const acc = tone ?? d.accent;
    // fallbackFamily is fallbackForm's typeface counterpart. `d = T(dna)` substitutes NEUTRAL_DNA wholesale
    // when there is truly no DNA — and NEUTRAL_DNA.fontDisplay is Inter (tuned to match the `display` form's
    // OWN reference shots), so a shot whose fallbackForm points at 'mono'/'serif' can still lose its face
    // under a null DNA even once the FORM resolves correctly (weight/leading right, family wrong). This is
    // ONLY a stand-in for that one case — a themed DNA (declaring `atoms.figure` or not) always speaks its
    // own `fontMono`/`fontDisplay`, same as before.
    const fam = dna ? undefined : fallbackFamily;
    // Each form's DEFAULT unit ratio is its reference shot's ratio, so migrating that shot does not change
    // its appearance; any other shot passes `unitScale` explicitly for the same reason.
    const us = (dflt: number) => size * (unitScale ?? dflt);
    // Each form carries its OWN typography, matching the shot it is the reference for — a shared
    // letter-spacing here would silently re-set three migrating shots.
    // The unit is a PLAIN INLINE SIBLING by default — NO flex wrapper, no imposed gap — so a shot with no
    // opinion keeps its original inline text flow (and its original glyph shaping: flexbox measurably
    // shifts inter-digit spacing versus plain inline text). A shot that wants space between figure and
    // unit passes `gap` explicitly; only then does this become an inline-flex row with that gap.
    const base: React.CSSProperties = gap === undefined
      ? {color: fg, fontVariantNumeric: 'tabular-nums'}
      : {display: 'inline-flex', alignItems: 'baseline', gap, color: fg, fontVariantNumeric: 'tabular-nums'};

    if (form === 'mono') {
      // matches TermCounter, its reference shot: 800 weight, 0.9 leading, tight tracking, no prefix
      return <span style={{...base, font: `800 ${size}px/0.9 ${fam ?? d.fontMono}`, letterSpacing: '-0.018em'}}>{txt}
        {unit ? <span style={{color: acc, fontSize: us(.32)}}>{unit}</span> : null}</span>;
    }
    if (form === 'serif') {
      // matches EdStat: NOT scaled — EdStat passes a width-aware size that exists to prevent overflow
      return <span style={{...base, font: `900 ${size}px/0.86 ${fam ?? d.fontDisplay}`, letterSpacing: '-0.02em'}}>{txt}
        {unit ? <span style={{color: acc, font: `700 ${us(.28)}px/1 ${fam ?? d.fontDisplay}`}}>{unit}</span> : null}</span>;
    }
    if (form === 'segment') {                     // retro scoreboard: a dim ghost behind the live digits
      // ink/tone mean the SAME thing here as in every other form — ink is the figure's own colour, tone is
      // the unit's — so the live digits (and their glow) take `fg` (ink), and only the unit takes `acc`
      // (tone). The ghost stays a muted mix, unaffected by tone.
      return <span style={{...base, position: 'relative', font: `700 ${size}px/1 ${fam ?? d.fontMono}`, letterSpacing: '.06em'}}>
        <span aria-hidden style={{position: 'absolute', left: 0, top: 0, color: mix(fg, d.bg, .86)}}>
          {'8'.repeat(txt.length)}</span>
        <span style={{position: 'relative', color: fg, textShadow: `0 0 18px ${fg}66`}}>{txt}</span>
        {unit ? <span style={{color: acc, fontSize: us(.30)}}>{unit}</span> : null}</span>;
    }
    // display — the neutral form; 0.9 leading and -0.03em are what BOTH consumers (ChartLive, VelocitySnap) use
    return <span style={{...base, font: `800 ${size}px/0.9 ${fam ?? d.fontDisplay}`, letterSpacing: '-0.03em'}}>{txt}
      {unit ? <span style={{color: acc, fontSize: us(.48)}}>{unit}</span> : null}</span>;
  };

// ── List — an enumeration ────────────────────────────────────────────────────────────────────────────
export const List: React.FC<{items: string[]; root?: string; reveal?: number[]; ink?: string; tone?: string;
  marker?: boolean; gap?: number; size?: number; weight?: number | string; lineHeight?: number | string;
  fallbackForm?: NonNullable<AtomForms['list']>}> =
  ({items, root, reveal, ink, tone, marker = true, gap, size, weight, lineHeight, fallbackForm}) => {
    const dna = useDNA(); const d = T(dna); const form = formOf(dna, 'list', fallbackForm);
    const shown = Array.isArray(items) ? items : [];
    // ink/tone let a migrating shot keep its OWN text/marker colour instead of the atom's defaults —
    // symmetric with Bar.ink/tone and Figure.ink/tone. Omit both and nothing changes from before.
    const fg = ink ?? d.fg;
    const acc = tone ?? d.accent;
    // marker=false suppresses the form's own leading glyph (bullet dot / tree branch / index number) for a
    // consumer that already supplies its OWN marker outside the atom (e.g. BlockAssembly's checkbox column)
    // — without it, the atom would ADD a second marker the shot never had. Default true: unchanged for any
    // caller that doesn't pass it.
    // gap/size/weight/lineHeight override the bullet form's own per-item spacing and type (defaults below
    // unchanged for any caller that omits them) — for a consumer rendering ONE item per call (its own outer
    // wrapper already spaces the rows), the atom's own trailing marginBottom would otherwise add a second,
    // uncalled-for gap on top of the shot's.
    const bGap = gap ?? 10, bSize = size ?? 28, bWeight = weight ?? 500, bLH = lineHeight ?? 1.45;
    // PER-ITEM reveal: shots stagger their items on their own easing, and one prefix fraction would
    // flatten that into a hard cut. Missing/NaN => fully shown.
    const op = (i: number) => {
      const r = reveal?.[i];
      return typeof r === 'number' && Number.isFinite(r) ? Math.max(0, Math.min(1, r)) : 1;
    };

    if (form === 'tree') {
      return <div style={{font: `500 26px/1.7 ${d.fontMono}`, color: fg}}>
        {root ? <div style={{color: acc}}>{root}</div> : null}
        {shown.map((it, i) => (
          <div key={i} style={{opacity: op(i)}}>
            {marker ? <span style={{color: d.dim}}>{i === shown.length - 1 ? '└─ ' : '├─ '}</span> : null}{it}</div>
        ))}</div>;
    }
    if (form === 'ruled') {
      return <div style={{color: fg}}>
        {shown.map((it, i) => (
          <div key={i} style={{padding: '14px 0', borderTop: marker && i ? `1px solid ${d.line}` : 'none',
            font: `500 30px/1.35 ${d.fontDisplay}`, opacity: op(i)}}>{it}</div>
        ))}</div>;
    }
    if (form === 'numbered') {
      return <div style={{color: fg}}>
        {shown.map((it, i) => (
          <div key={i} style={{display: 'flex', gap: 16, marginBottom: 10, opacity: op(i),
            font: `500 26px/1.5 ${d.fontMono}`}}>
            {marker ? <span style={{color: acc}}>{String(i + 1).padStart(2, '0')}</span> : null}{it}</div>
        ))}</div>;
    }
    return <div style={{color: fg}}>                                       {/* bullet — neutral */}
      {shown.map((it, i) => (
        <div key={i} style={{display: 'flex', gap: 14, marginBottom: bGap, opacity: op(i),
          font: `${bWeight} ${bSize}px/${bLH} ${d.fontBody}`}}>
          {marker ? <span style={{color: acc}}>•</span> : null}{it}</div>
      ))}</div>;
  };

// ── Label — an eyebrow / tag ─────────────────────────────────────────────────────────────────────────
export const Label: React.FC<{text: string; fallbackForm?: NonNullable<AtomForms['label']>}> = ({text, fallbackForm}) => {
  const dna = useDNA(); const d = T(dna); const form = formOf(dna, 'label', fallbackForm);
  const t = String(text ?? '');
  if (form === 'prompt') {
    return <span style={{font: `600 22px/1 ${d.fontMono}`, color: d.dim}}>
      <span style={{color: d.accent}}>$ </span>{t}</span>;
  }
  if (form === 'spec') {
    return <span style={{font: `600 20px/1 ${d.fontMono}`, color: d.dim, letterSpacing: d.labelSpacing}}>
      <span style={{color: d.accent}}>◇ </span>{t.toUpperCase()}</span>;
  }
  if (form === 'chip') {
    return <span style={{font: `600 20px/1 ${d.fontBody}`, color: d.accent, background: `${d.surface}`,
      border: `1px solid ${d.line}`, borderRadius: 999, padding: '5px 14px'}}>{t}</span>;
  }
  return <span style={{font: `700 22px/1 ${d.fontBody}`, color: d.accent,   /* kicker — neutral */
    letterSpacing: d.labelSpacing, textTransform: d.uppercaseLabels ? 'uppercase' : 'none'}}>{t}</span>;
};

// ── Divider — a separation ───────────────────────────────────────────────────────────────────────────
export const Divider: React.FC<{width?: number | string; fallbackForm?: NonNullable<AtomForms['divider']>}> =
  ({width = 120, fallbackForm}) => {
  const dna = useDNA(); const d = T(dna); const form = formOf(dna, 'divider', fallbackForm);
  if (form === 'scanline') {
    return <span style={{display: 'block', width, height: 2, background: d.accent, opacity: .55,
      boxShadow: `0 0 12px ${d.accent}55`}} />;
  }
  if (form === 'dimension') {
    return <span style={{display: 'block', position: 'relative', width, height: 10}}>
      <span style={{position: 'absolute', left: 0, top: 4, width: '100%', height: 1.5, background: d.line}} />
      <span style={{position: 'absolute', left: 0, top: 0, width: 1.5, height: 10, background: d.line}} />
      <span style={{position: 'absolute', right: 0, top: 0, width: 1.5, height: 10, background: d.line}} />
    </span>;
  }
  if (form === 'dotted') {
    return <span style={{display: 'block', width, height: 0, borderTop: `3px dotted ${d.accent}`}} />;
  }
  return <span style={{display: 'block', width, height: 2, background: d.accent, opacity: .9}} />;  /* hairline */
};

// ── Marker — a point of focus ────────────────────────────────────────────────────────────────────────
export const Marker: React.FC<{phase?: number; fallbackForm?: NonNullable<AtomForms['marker']>}> =
  ({phase = 1, fallbackForm}) => {
  const dna = useDNA(); const d = T(dna); const form = formOf(dna, 'marker', fallbackForm);
  const on = phase >= 0.5;                     // the SHOT supplies phase; atoms never read the frame
  if (form === 'caret') {
    return <span style={{display: 'inline-block', width: 12, height: 24, background: d.accent,
      opacity: on ? .95 : .15, verticalAlign: 'text-bottom'}} />;
  }
  if (form === 'crosshair') {
    return <span style={{display: 'inline-block', position: 'relative', width: 22, height: 22}}>
      <span style={{position: 'absolute', left: 0, top: 10, width: 22, height: 1.5, background: d.accent}} />
      <span style={{position: 'absolute', left: 10, top: 0, width: 1.5, height: 22, background: d.accent}} />
    </span>;
  }
  if (form === 'arrow') {
    return <span style={{color: d.accent, font: `700 24px/1 ${d.fontBody}`}}>→</span>;
  }
  return <span style={{color: d.accent, font: `700 22px/1 ${d.fontBody}`}}>▸</span>;   /* triangle */
};
