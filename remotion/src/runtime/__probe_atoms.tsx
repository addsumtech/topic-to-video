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
console.log(fails ? `PROBE FAILED (${fails})` : `PROBE OK (${cases.length * samples.length} combinations)`);
process.exit(fails ? 1 : 0);
