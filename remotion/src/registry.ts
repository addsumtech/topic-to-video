// Registry — maps a shot's string id (as used in a storyboard `scene.shot`) to its component, so a data-driven
// film can look shots up by name. Every bespoke shot in the library is registered here; keep in sync with Root.tsx.

import React from 'react';
import {CollaborativeCursors} from './shots/CollaborativeCursors';
import {CommandSummon} from './shots/CommandSummon';
import {TemporalAccelerate} from './shots/TemporalAccelerate';
import {FocalIsolation} from './shots/FocalIsolation';
import {KineticManifesto} from './shots/KineticManifesto';
import {InfiniteCanvas} from './shots/InfiniteCanvas';
import {BlockAssembly} from './shots/BlockAssembly';
import {AnswerStream} from './shots/AnswerStream';
import {ScreenBubble} from './shots/ScreenBubble';
import {VelocitySnap} from './shots/VelocitySnap';
import {CursorStory} from './shots/CursorStory';
import {ExplodedSchematic} from './shots/ExplodedSchematic';
import {MaterialHero} from './shots/MaterialHero';
import {TimelineTravel} from './shots/TimelineTravel';
import {MapRoutes} from './shots/MapRoutes';
import {ChatThread} from './shots/ChatThread';
import {BeforeAfterSlider} from './shots/BeforeAfterSlider';
import {AuroraFlow} from './shots/AuroraFlow';
import {IsometricAssembly} from './shots/IsometricAssembly';
import {LiquidMorph} from './shots/LiquidMorph';
import {VoiceSignal} from './shots/VoiceSignal';
import {AsciiField} from './shots/AsciiField';
import {ParticleForm} from './shots/ParticleForm';
import {HandDrawn} from './shots/HandDrawn';
import {ChartLive} from './shots/ChartLive';
import {CartoonPop} from './shots/CartoonPop';
import {LiquidChrome} from './shots/LiquidChrome';
import {CodeCompose} from './shots/CodeCompose';
import {KnowledgeGraph} from './shots/KnowledgeGraph';
import {CinematicTitle} from './shots/CinematicTitle';
import {BlueprintGrid} from './shots/BlueprintGrid';
import {SpotlightStage} from './shots/SpotlightStage';
import {AnalogTape} from './shots/AnalogTape';
import {NeonGrid} from './shots/NeonGrid';
import {SwissEditorial} from './shots/SwissEditorial';
import {ClayStack} from './shots/ClayStack';
import {LiquidFill} from './shots/LiquidFill';
import {HalftonePop} from './shots/HalftonePop';
import {PaperCutout} from './shots/PaperCutout';
import {RadialBurst} from './shots/RadialBurst';
import {SplitFlap} from './shots/SplitFlap';
import {WireGlobe} from './shots/WireGlobe';
import {LiquidGlass} from './shots/LiquidGlass';
import {HoloFoil} from './shots/HoloFoil';
import {BokehPull} from './shots/BokehPull';
import {PixelBuild} from './shots/PixelBuild';
import {BrutalistType} from './shots/BrutalistType';
import {LightTrails} from './shots/LightTrails';
import {DataOrrery} from './shots/DataOrrery';
import {PhysicsStack} from './shots/PhysicsStack';

export const REGISTRY: Record<string, React.FC<any>> = {
  CollaborativeCursors, CommandSummon, TemporalAccelerate, FocalIsolation, KineticManifesto, InfiniteCanvas,
  BlockAssembly, AnswerStream, ScreenBubble, VelocitySnap, CursorStory, ExplodedSchematic, MaterialHero,
  TimelineTravel, MapRoutes, ChatThread, BeforeAfterSlider, AuroraFlow, IsometricAssembly, LiquidMorph,
  VoiceSignal, AsciiField, ParticleForm, HandDrawn, ChartLive, CartoonPop, LiquidChrome, CodeCompose,
  KnowledgeGraph, CinematicTitle, BlueprintGrid, SpotlightStage, AnalogTape, NeonGrid, SwissEditorial,
  ClayStack, LiquidFill, HalftonePop, PaperCutout, RadialBurst, SplitFlap, WireGlobe, LiquidGlass, HoloFoil,
  BokehPull, PixelBuild, BrutalistType, LightTrails, DataOrrery, PhysicsStack,
};

export const SHOT_IDS = Object.keys(REGISTRY);
