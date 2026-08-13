import React from 'react';
import {Composition} from 'remotion';
import {CollaborativeCursors, DURATION as CC} from './shots/CollaborativeCursors';
import {CommandSummon, DURATION as CS} from './shots/CommandSummon';
import {TemporalAccelerate, DURATION as TA} from './shots/TemporalAccelerate';
import {FocalIsolation, DURATION as FI} from './shots/FocalIsolation';
import {KineticManifesto, DURATION as KM} from './shots/KineticManifesto';
import {InfiniteCanvas, DURATION as IC} from './shots/InfiniteCanvas';
import {BlockAssembly, DURATION as BA} from './shots/BlockAssembly';
import {AnswerStream, DURATION as AS} from './shots/AnswerStream';
import {ScreenBubble, DURATION as SB} from './shots/ScreenBubble';
import {VelocitySnap, DURATION as VS} from './shots/VelocitySnap';
import {CursorStory, DURATION as CST} from './shots/CursorStory';
import {ExplodedSchematic, DURATION as ES} from './shots/ExplodedSchematic';
import {MaterialHero, DURATION as MH} from './shots/MaterialHero';
import {TimelineTravel, DURATION as TT} from './shots/TimelineTravel';
import {MapRoutes, DURATION as MR} from './shots/MapRoutes';
import {ChatThread, DURATION as CT} from './shots/ChatThread';
import {BeforeAfterSlider, DURATION as BAS} from './shots/BeforeAfterSlider';
import {AuroraFlow, DURATION as AF} from './shots/AuroraFlow';
import {IsometricAssembly, DURATION as IA} from './shots/IsometricAssembly';
import {LiquidMorph, DURATION as LM} from './shots/LiquidMorph';
import {VoiceSignal, DURATION as VSG} from './shots/VoiceSignal';
import {AsciiField, DURATION as ASC} from './shots/AsciiField';
import {ParticleForm, DURATION as PF} from './shots/ParticleForm';
import {HandDrawn, DURATION as HD} from './shots/HandDrawn';
import {ChartLive, DURATION as CL} from './shots/ChartLive';
import {CartoonPop, DURATION as CP} from './shots/CartoonPop';
import {LiquidChrome, DURATION as LC} from './shots/LiquidChrome';
import {CodeCompose, DURATION as CC2} from './shots/CodeCompose';
import {KnowledgeGraph, DURATION as KG} from './shots/KnowledgeGraph';
import {CinematicTitle, DURATION as CIN} from './shots/CinematicTitle';
import {BlueprintGrid, DURATION as BG} from './shots/BlueprintGrid';
import {SpotlightStage, DURATION as SS} from './shots/SpotlightStage';
import {AnalogTape, DURATION as AT} from './shots/AnalogTape';
import {NeonGrid, DURATION as NG} from './shots/NeonGrid';
import {SwissEditorial, DURATION as SE} from './shots/SwissEditorial';
import {ClayStack, DURATION as CLY} from './shots/ClayStack';
import {LiquidFill, DURATION as LF} from './shots/LiquidFill';
import {HalftonePop, DURATION as HP} from './shots/HalftonePop';
import {PaperCutout, DURATION as PC} from './shots/PaperCutout';
import {RadialBurst, DURATION as RB} from './shots/RadialBurst';
import {SplitFlap, DURATION as SF} from './shots/SplitFlap';
import {WireGlobe, DURATION as WG} from './shots/WireGlobe';
import {LiquidGlass, DURATION as LG} from './shots/LiquidGlass';
import {HoloFoil, DURATION as HF} from './shots/HoloFoil';
import {BokehPull, DURATION as BP} from './shots/BokehPull';
import {PixelBuild, DURATION as PX} from './shots/PixelBuild';
import {BrutalistType, DURATION as BT} from './shots/BrutalistType';
import {LightTrails, DURATION as LT} from './shots/LightTrails';
import {DataOrrery, DURATION as DO} from './shots/DataOrrery';
import {PhysicsStack, DURATION as PS} from './shots/PhysicsStack';
import {Film, WORKBUDDY_SCENES, filmDuration} from './Film';

// Redo tier: each bespoke shot registers as its OWN Composition (video-shotcraft pattern), renderable
// standalone for verification. A film later sequences chosen shots through the pipeline wrapper.
const F = (id: string, C: React.FC<any>, d: number) => (
  <Composition id={id} component={C} durationInFrames={d} fps={30} width={1920} height={1080} defaultProps={{}} />
);
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Film" component={Film} fps={30} width={1920} height={1080}
      defaultProps={{scenes: WORKBUDDY_SCENES}}
      calculateMetadata={({props}) => ({durationInFrames: filmDuration((props as any).scenes ?? WORKBUDDY_SCENES)})} />
    {F('CollaborativeCursors', CollaborativeCursors, CC)}
    {F('CommandSummon', CommandSummon, CS)}
    {F('TemporalAccelerate', TemporalAccelerate, TA)}
    {F('FocalIsolation', FocalIsolation, FI)}
    {F('KineticManifesto', KineticManifesto, KM)}
    {F('InfiniteCanvas', InfiniteCanvas, IC)}
    {F('BlockAssembly', BlockAssembly, BA)}
    {F('AnswerStream', AnswerStream, AS)}
    {F('ScreenBubble', ScreenBubble, SB)}
    {F('VelocitySnap', VelocitySnap, VS)}
    {F('CursorStory', CursorStory, CST)}
    {F('ExplodedSchematic', ExplodedSchematic, ES)}
    {F('MaterialHero', MaterialHero, MH)}
    {F('TimelineTravel', TimelineTravel, TT)}
    {F('MapRoutes', MapRoutes, MR)}
    {F('ChatThread', ChatThread, CT)}
    {F('BeforeAfterSlider', BeforeAfterSlider, BAS)}
    {F('AuroraFlow', AuroraFlow, AF)}
    {F('IsometricAssembly', IsometricAssembly, IA)}
    {F('LiquidMorph', LiquidMorph, LM)}
    {F('VoiceSignal', VoiceSignal, VSG)}
    {F('AsciiField', AsciiField, ASC)}
    {F('ParticleForm', ParticleForm, PF)}
    {F('HandDrawn', HandDrawn, HD)}
    {F('ChartLive', ChartLive, CL)}
    {F('CartoonPop', CartoonPop, CP)}
    {F('LiquidChrome', LiquidChrome, LC)}
    {F('CodeCompose', CodeCompose, CC2)}
    {F('KnowledgeGraph', KnowledgeGraph, KG)}
    {F('CinematicTitle', CinematicTitle, CIN)}
    {F('BlueprintGrid', BlueprintGrid, BG)}
    {F('SpotlightStage', SpotlightStage, SS)}
    {F('AnalogTape', AnalogTape, AT)}
    {F('NeonGrid', NeonGrid, NG)}
    {F('SwissEditorial', SwissEditorial, SE)}
    {F('ClayStack', ClayStack, CLY)}
    {F('LiquidFill', LiquidFill, LF)}
    {F('HalftonePop', HalftonePop, HP)}
    {F('PaperCutout', PaperCutout, PC)}
    {F('RadialBurst', RadialBurst, RB)}
    {F('SplitFlap', SplitFlap, SF)}
    {F('WireGlobe', WireGlobe, WG)}
    {F('LiquidGlass', LiquidGlass, LG)}
    {F('HoloFoil', HoloFoil, HF)}
    {F('BokehPull', BokehPull, BP)}
    {F('PixelBuild', PixelBuild, PX)}
    {F('BrutalistType', BrutalistType, BT)}
    {F('LightTrails', LightTrails, LT)}
    {F('DataOrrery', DataOrrery, DO)}
    {F('PhysicsStack', PhysicsStack, PS)}
  </>
);
