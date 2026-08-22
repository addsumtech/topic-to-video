// Probe (not part of any render): every atom × every preset × the three fallback cases, through
// react-dom/server. Proves totality and that no `undefined` token leaks into the markup.
// Run by tests/test_remotion.py::test_atoms_are_total_across_every_dna_and_edge_case.
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {DesignDNAContext, DNA_PRESETS, NEUTRAL_DNA, type DesignDNA} from './dna';
import {Bar, Figure, List, Label, Divider, Marker} from './atoms';

const cases: Array<[string, DesignDNA | null]> = [
  ['no-dna', null],
  ...Object.entries(DNA_PRESETS).map(([k, val]) => [k, val] as [string, DesignDNA]),
  ['no-atoms', {...NEUTRAL_DNA, atoms: undefined}],
  ['unknown-forms', {...NEUTRAL_DNA, atoms: {bar: 'nope', figure: 'nope', list: 'nope',
    label: 'nope', divider: 'nope', marker: 'nope'} as never}],
];
const samples: Array<[string, React.ReactElement]> = [
  ['Bar', <Bar value={0.62} label="Alpha" tag="PASS" />],
  ['Bar-edge', <Bar value={NaN as unknown as number} />],
  ['Figure', <Figure value="88" unit="%" />],
  ['Figure-num', <Figure value={0} />],
  ['List', <List items={['a', 'b', 'c']} root="~/p" reveal={[1, .5, 0]} />],
  ['List-empty', <List items={[]} />],
  ['Label', <Label text="BY THE NUMBERS" />],
  ['Divider', <Divider width={120} />],
  ['Marker', <Marker phase={0.9} />],
];

let fails = 0;
for (const [cname, dna] of cases) {
  for (const [aname, el] of samples) {
    let html = '';
    try {
      html = renderToStaticMarkup(<DesignDNAContext.Provider value={dna}>{el}</DesignDNAContext.Provider>);
    } catch (e) {
      console.log(`FAIL ${aname} @ ${cname}: threw ${(e as Error).message}`); fails++; continue;
    }
    if (!html) { console.log(`FAIL ${aname} @ ${cname}: empty output`); fails++; }
    if (html.includes('undefined')) { console.log(`FAIL ${aname} @ ${cname}: "undefined" leaked into markup`); fails++; }
    if (html.includes('NaN')) { console.log(`FAIL ${aname} @ ${cname}: "NaN" leaked into markup`); fails++; }
  }
}

// ── GOLDEN — literal replicas of each migrated shot's own atom call, asserting the rendered `font:`/
// `font-size:` PX NUMBERS (via regex, not a raw string match — a couple of these ratios carry harmless
// float noise, e.g. TermCounter's pre-existing 56/220 renders 55.99999999999999px). Would have caught
// finding-1 (EdStat's unit losing its [32,64] clamp — 72.8px instead of 64px) as a plain numeric diff, no
// PNG baseline required. Also exercises `fallbackForm`/`fallbackFamily` (finding 6): zero coverage before
// this fix wave — the probe was written before those props existed.
const EDSTAT_UNIT = (numSize: number) => Math.max(32, Math.min(64, Math.round(numSize * 0.28))) / numSize;
const pxNear = (html: string, re: RegExp, expect: number, tol = 0.01): string | null => {
  const m = html.match(re);
  if (!m) return `pattern ${re} not found`;
  const got = parseFloat(m[1]);
  return Math.abs(got - expect) <= tol ? null : `expected ~${expect}px, got ${got}px`;
};
type Golden = {name: string; dna: DesignDNA | null; el: React.ReactElement;
  checks?: Array<{re: RegExp; expect: number}>; mustInclude?: string[]; mustExclude?: string[]};
const goldens: Golden[] = [
  // EdStat, default props (value:'100' — finalLen<=7 so numSize SATURATES at 260, finding-1's exact repro).
  // The unit must render the pre-atoms CLAMPED 64px, never the unclamped 260*0.28=72.8px.
  {name: 'EdStat-default(unit-clamp-high)', dna: null,
    el: <Figure value="100" unit="req/s" size={260} unitScale={EDSTAT_UNIT(260)}
      fallbackForm="serif" fallbackFamily='"Playfair Display", Georgia, serif' />,
    checks: [{re: /font:900 ([\d.]+)px\/0\.86/, expect: 260}, {re: /font:700 ([\d.]+)px\/1/, expect: 64}]},
  // EdStat, a long value (finalLen>=17 so numSize bottoms at 108): the unit must clamp to 32px, never the
  // unclamped 108*0.28=30.24px.
  {name: 'EdStat-long(unit-clamp-low)', dna: null,
    el: <Figure value="12,345,678,901,234" unit="requests/sec" size={108} unitScale={EDSTAT_UNIT(108)}
      fallbackForm="serif" fallbackFamily='"Playfair Display", Georgia, serif' />,
    checks: [{re: /font:700 ([\d.]+)px\/1/, expect: 32}]},
  // TermCounter reference call — its unit ratio (56/220) is unchanged by this fix wave; kept as a tripwire.
  {name: 'TermCounter', dna: null,
    el: <Figure value="100" unit="req/s" size={220} unitScale={56 / 220} gap={20}
      fallbackForm="mono" fallbackFamily='"JetBrains Mono", ui-monospace, monospace' />,
    checks: [{re: /font-size:([\d.]+)px/, expect: 56}], mustInclude: ['flex-wrap:wrap']},
  // ChartLive — the EXACT ratio (finding 15: 100/210, not the 0.476 float that painted 99.96px).
  {name: 'ChartLive', dna: null,
    el: <Figure value={128} unit="k" ink="#eafff4" tone="#37E0A0" size={210} unitScale={100 / 210}
      fallbackForm="display" fallbackFamily="Inter, system-ui, sans-serif" />,
    checks: [{re: /font-size:([\d.]+)px/, expect: 100}]},
  // VelocitySnap — unitScale=1 was never wrong; kept as a regression tripwire alongside its new
  // fallbackForm/fallbackFamily (finding 8).
  {name: 'VelocitySnap', dna: null,
    el: <Figure value="0" unit="ms" ink="#fff" tone="#7C89FF" size={120} unitScale={1}
      fallbackForm="display" fallbackFamily="Inter, system-ui, sans-serif" />,
    checks: [{re: /font-size:([\d.]+)px/, expect: 120}]},
  // A migrated shot's fallbackForm must reach THAT form under a null DNA, not the atom's neutral form.
  {name: 'Bar-fallbackForm-nullDna-reachesFallback', dna: null,
    el: <Bar value={0.5} fallbackForm="block" />, mustInclude: ['█']},
  // A DNA that DECLARES a form for this atom always wins over fallbackForm — editorial speaks `ruled`.
  {name: 'Bar-fallbackForm-dnaWins', dna: DNA_PRESETS.editorial,
    el: <Bar value={0.5} fallbackForm="block" />, mustInclude: ['border-bottom'], mustExclude: ['█']},
  // Figure.fallbackFamily supplies the face under a null DNA (fallbackForm alone gets weight/leading right
  // but not the family).
  {name: 'Figure-fallbackFamily-nullDna', dna: null,
    el: <Figure value="1" fallbackForm="serif" fallbackFamily="Georgia, serif" />,
    mustInclude: ['Georgia, serif']},
  // ...but a THEMED DNA always speaks its own family — fallbackFamily is a null-DNA stand-in only.
  {name: 'Figure-fallbackFamily-themedDnaWins', dna: DNA_PRESETS.terminal,
    el: <Figure value="1" fallbackForm="serif" fallbackFamily="Georgia, serif" />,
    mustInclude: ['JetBrains Mono'], mustExclude: ['Georgia, serif']},
];
for (const g of goldens) {
  let html = '';
  try {
    html = renderToStaticMarkup(<DesignDNAContext.Provider value={g.dna}>{g.el}</DesignDNAContext.Provider>);
  } catch (e) {
    console.log(`FAIL golden ${g.name}: threw ${(e as Error).message}`); fails++; continue;
  }
  for (const c of g.checks ?? []) {
    const err = pxNear(html, c.re, c.expect);
    if (err) { console.log(`FAIL golden ${g.name}: ${err} — html=${html}`); fails++; }
  }
  for (const s of g.mustInclude ?? []) {
    if (!html.includes(s)) { console.log(`FAIL golden ${g.name}: expected to find ${JSON.stringify(s)} — html=${html}`); fails++; }
  }
  for (const s of g.mustExclude ?? []) {
    if (html.includes(s)) { console.log(`FAIL golden ${g.name}: unexpectedly found ${JSON.stringify(s)} — html=${html}`); fails++; }
  }
}

console.log(fails ? `PROBE FAILED (${fails})` : `PROBE OK (${cases.length * samples.length} combinations + ${goldens.length} goldens)`);
process.exit(fails ? 1 : 0);
