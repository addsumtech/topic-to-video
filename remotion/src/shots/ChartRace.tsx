// SHOT · Chart Race — a bar-chart RACE: horizontal bars grow at different rates and RE-RANK as they overtake
// each other (bars slide to their live rank), value counters ticking, the leader glowing. The "who pulls
// ahead over time" data register (family D). Number-bearing → a real film passes SOURCED `data` (see NUM
// guard); the demo values are illustrative. Deterministic (value(t) = eased growth per item).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {Bar} from '../runtime/atoms';

export const DURATION = 155; // ~5.2s
const BG = '#0a0c14';
const TONES0 = ['#5b8cff', '#ff6f91', '#37d4a6', '#f6a531', '#c07bff', '#4dd0e1'];

type Row = {label?: string; value?: number; delay?: number};

export const ChartRace: React.FC<{data?: Row[]; title?: string; unit?: string}> = ({
  data: DATA = [{label: 'Alpha', value: 92, delay: 0.0}, {label: 'Bravo', value: 78, delay: 0.28},
    {label: 'Charlie', value: 100, delay: 0.42}, {label: 'Delta', value: 64, delay: 0.1}, {label: 'Echo', value: 84, delay: 0.5}],
  title: TITLE = 'Who pulls ahead', unit: UNIT = ''} = {}) => {
  const t = useT();
  const dna = useDNA(); const TONES = dnaPalette(dna, 6) ?? TONES0;
  const {width: W, height: H} = useVideoConfig();
  const rows = DATA.slice(0, 6);
  const maxVal = Math.max(...rows.map((r) => r.value ?? 0), 1);
  const barMax = W - 720, x0 = 420, rowH = 118, top = 240;
  // live value grows from each item's delay to the end
  const live = rows.map((r, i) => {
    const g = easeOutCubic(clamp01(seg(t, r.delay ?? 0, 0.92)));
    return {...r, i, cur: (r.value ?? 0) * g};
  });
  // SOFT rank: a continuous position (Σ sigmoid of pairwise value gaps) so bars SLIDE smoothly as they
  // overtake — CSS transitions don't animate across Remotion's per-frame capture, so the motion must be in t.
  const sig = (z: number) => 1 / (1 + Math.exp(-z));
  const softRank = (r: {i: number; cur: number}) =>
    live.reduce((s, o) => (o.i === r.i ? s : s + sig((o.cur - r.cur) * 0.22)), 0);
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? `radial-gradient(120% 100% at 30% 20%, #12162a, ${BG} 72%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 90, left: x0 - 40, opacity: titleIn,
        color: '#aeb6ca', font: '700 34px/1 "JetBrains Mono", monospace', letterSpacing: '0.24em', textTransform: 'uppercase'}}>{TITLE}</div>
      {live.map((r) => {
        const sr = softRank(r);
        const y = top + sr * rowH;
        const bw = (r.cur / maxVal) * barMax;
        const lead = sr < 0.5;
        const tone = TONES[r.i % TONES.length];
        return (
          <div key={r.i} style={{position: 'absolute', left: x0, top: y, width: barMax + 300, height: rowH - 22}}>
            {/* label — kept as the shot's OWN positioned element (right:100%, sits left of x0): the Bar atom's
                internal label lays out inline BEFORE its bar, which would shift every bar's start by that
                row's own label width and break the shared x0 baseline every bar-length comparison depends on. */}
            <div style={{position: 'absolute', right: '100%', top: 0, height: rowH - 22, paddingRight: 26,
              display: 'flex', alignItems: 'center', color: lead ? '#fff' : '#c7cee0',
              font: `${lead ? 800 : 600} 40px/1 Inter, system-ui, sans-serif`, whiteSpace: 'nowrap'}}>{r.label}</div>
            {/* bar — routed through the Bar atom so its FORM (solid pill / ruled scale / dimensioned measure /
                pixel cells) follows the active DNA. No label/tag passed in, for the reason above and because
                the value counter's OWN motion (it trails the bar's live growing edge, not a fixed max-width
                offset) is this shot's, not the atom's. */}
            <div style={{position: 'absolute', left: 0, top: 0, height: rowH - 22, display: 'flex', alignItems: 'center'}}>
              <Bar value={r.cur / maxVal} tone={tone} width={barMax} height={rowH - 22} track={false} />
            </div>
            {/* value */}
            <div style={{position: 'absolute', left: bw + 20, top: 0, height: rowH - 22, display: 'flex', alignItems: 'center',
              color: lead ? tone : '#8b93a8', font: `800 40px/1 Inter, system-ui, sans-serif`}}>
              {Math.round(r.cur)}{UNIT}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default ChartRace;
