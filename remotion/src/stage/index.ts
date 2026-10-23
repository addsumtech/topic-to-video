// THE STAGES — components that draw a whole stage run (runtime/stageRun.tsx). Kept apart from REGISTRY on purpose: a
// stage is not a register (it draws several beats at once and cannot render alone), so the library's per-register
// sweeps and manifests never see it, and Film.tsx looks a run's shot up here.
import React from 'react';
import {CardStage} from './CardStage';

export const STAGES: Record<string, React.FC<any>> = {CardStage};

/** The DNA colour each stage paints its ground with — what the caption ink and the seam guard judge a stage beat's
 *  ground by. A register's comes from its measured row (runtime/shotLuma DNA_GROUND_TOKEN); a stage has none, and the
 *  fallback called CardStage's light studio "dark" and burned WHITE captions onto it. */
export const STAGE_GROUND: Record<string, string> = {CardStage: 'bg'};
