// Remotion CLI config (used by `remotion render`/`studio`). Kept minimal — the storyboard
// drives everything else through --props.
import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
