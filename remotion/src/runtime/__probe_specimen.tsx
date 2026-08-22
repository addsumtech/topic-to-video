// PROBE — renders one library shot inside a chosen DNA, for the type specimen contact sheet.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {DesignDNAContext, DNA_PRESETS} from './dna';
import {REGISTRY} from '../registry';

export const DURATION = 150;

export const TypeSpecimen: React.FC<{shot?: string; dnaId?: string}> = ({
  shot = 'EdStat', dnaId = 'editorial'}) => {
  const C = REGISTRY[shot];
  const dna = DNA_PRESETS[dnaId] ?? null;
  return (
    <AbsoluteFill style={{background: dna?.bg ?? '#000'}}>
      <DesignDNAContext.Provider value={dna}>
        <AbsoluteFill>{C ? <C /> : null}</AbsoluteFill>
      </DesignDNAContext.Provider>
    </AbsoluteFill>
  );
};
export default TypeSpecimen;
