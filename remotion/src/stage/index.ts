// THE STAGES — components that draw a whole stage run (runtime/stageRun.tsx). Kept apart from REGISTRY on purpose: a
// stage is not a register (it draws several beats at once and cannot render alone), so the library's per-register
// sweeps and manifests never see it, and Film.tsx looks a run's shot up here.
import React from 'react';
import {CardStage} from './CardStage';

export const STAGES: Record<string, React.FC<any>> = {CardStage};
