// Registry — maps a shot's string id (as used in a storyboard `scene.shot`) to its component, so a data-driven
// film can look shots up by name. Every bespoke shot in the library is registered here; keep in sync with Root.tsx.

import React from 'react';
import {CollaborativeCursors} from './shots/CollaborativeCursors';
import {CommandSummon} from './shots/CommandSummon';
import {TemporalAccelerate} from './shots/TemporalAccelerate';
import {KSpaceToImage} from './shots/KSpaceToImage';
import {MagnetizationTip} from './shots/MagnetizationTip';
import {InducedFID} from './shots/InducedFID';
import {GFactorNoise} from './shots/GFactorNoise';
import {UndersampledKspace} from './shots/UndersampledKspace';
import {ScanReconstruct} from './shots/ScanReconstruct';
import {RealVersus} from './shots/RealVersus';
import {SpinningProton} from './shots/SpinningProton';
import {PhaseEncodeStep} from './shots/PhaseEncodeStep';
import {MRIPipeline} from './shots/MRIPipeline';
import {FrequencyEncode} from './shots/FrequencyEncode';
import {CompressedSensingEq} from './shots/CompressedSensingEq';
import {KSpaceReal} from './shots/KSpaceReal';
import {SpeedLimit} from './shots/SpeedLimit';
import {LarmorPrecession} from './shots/LarmorPrecession';
import {Aliasing} from './shots/Aliasing';
import {DiffusionDenoise} from './shots/DiffusionDenoise';
import {SpinsAlign} from './shots/SpinsAlign';
import {GradientTilt} from './shots/GradientTilt';
import {KSpaceAnatomy} from './shots/KSpaceAnatomy';
import {TensionScale} from './shots/TensionScale';
import {PlatformSurfaces} from './shots/PlatformSurfaces';
import {OpenQuestions} from './shots/OpenQuestions';
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
import {OdometerRoll} from './shots/OdometerRoll';
import {QuadSplit} from './shots/QuadSplit';
import {CardFlip3D} from './shots/CardFlip3D';
import {CubeRotate} from './shots/CubeRotate';
import {GearTrain} from './shots/GearTrain';
import {FractureIn} from './shots/FractureIn';
import {PositioningMatrix} from './shots/PositioningMatrix';
import {GaugeCluster} from './shots/GaugeCluster';
import {BentoReveal} from './shots/BentoReveal';
import {ConveyorBelt} from './shots/ConveyorBelt';
import {TermBars} from './shots/TermBars';
import {TermTree} from './shots/TermTree';
import {TermLog} from './shots/TermLog';
import {TermGitLog} from './shots/TermGitLog';
import {TermCounter} from './shots/TermCounter';
import {TermTable} from './shots/TermTable';
import {TermDiff} from './shots/TermDiff';
import {TermThink} from './shots/TermThink';
import {EdStat} from './shots/EdStat';
import {EdTimeline} from './shots/EdTimeline';
import {EdCompare} from './shots/EdCompare';
import {CardStack3D} from './shots/CardStack3D';
import {CrashZoom} from './shots/CrashZoom';
import {OverlapSeparation} from './shots/OverlapSeparation';
import {SharedBlindspot} from './shots/SharedBlindspot';
import {VersusSplit} from './shots/VersusSplit';
import {RisoPrint} from './shots/RisoPrint';
import {HudReticle} from './shots/HudReticle';
import {VariableTypeMorph} from './shots/VariableTypeMorph';
import {FlowField} from './shots/FlowField';
import {MagazineSpread} from './shots/MagazineSpread';
import {PaperSlot} from './shots/PaperSlot';
import {PortRail} from './shots/PortRail';
import {RansomZine} from './shots/RansomZine';
import {DataMonolith} from './shots/DataMonolith';
import {LowPolyForm} from './shots/LowPolyForm';
import {GlitchDatamosh} from './shots/GlitchDatamosh';
import {IsoWorld} from './shots/IsoWorld';
import {MorphForms} from './shots/MorphForms';
import {NeonTickerWall} from './shots/NeonTickerWall';
import {MetaballMerge} from './shots/MetaballMerge';
import {InflateType} from './shots/InflateType';
import {ElasticType} from './shots/ElasticType';
import {AntiDesignChaos} from './shots/AntiDesignChaos';
import {NeuralField} from './shots/NeuralField';
import {DNAHelix} from './shots/DNAHelix';
import {CircuitTrace} from './shots/CircuitTrace';
import {KaleidoMandala} from './shots/KaleidoMandala';
import {InkBloom} from './shots/InkBloom';
import {ComicPanels} from './shots/ComicPanels';
import {SpectrumPulse} from './shots/SpectrumPulse';
import {StarfieldWarp} from './shots/StarfieldWarp';
import {RidgeField} from './shots/RidgeField';
import {VoxelBuild} from './shots/VoxelBuild';
import {ChartRace} from './shots/ChartRace';
import {CodeRain} from './shots/CodeRain';
import {FractalTree} from './shots/FractalTree';
import {RainGlass} from './shots/RainGlass';
import {AtomOrbital} from './shots/AtomOrbital';
import {LiquidMetal} from './shots/LiquidMetal';
import {EmberFlame} from './shots/EmberFlame';
import {ClothWave} from './shots/ClothWave';
import {GameOfLife} from './shots/GameOfLife';
import {MoleculeBallStick} from './shots/MoleculeBallStick';
import {TerrainFly} from './shots/TerrainFly';
import {SectionRoute} from './shots/SectionRoute';
import {GazetteerEntry} from './shots/GazetteerEntry';
import {MapPlate} from './shots/MapPlate';
import {StrataColumn} from './shots/StrataColumn';
import {PlanPalimpsest} from './shots/PlanPalimpsest';
import {TallyLedger} from './shots/TallyLedger';
import {MuseumLabel} from './shots/MuseumLabel';
import {Inscription} from './shots/Inscription';
import {TechnicalPlate} from './shots/TechnicalPlate';
import {ProfileGrowth} from './shots/ProfileGrowth';
import {PhotoPlate} from './shots/PhotoPlate';
import {GrantedTree} from './shots/GrantedTree';
import {LastLeg} from './shots/LastLeg';
import {MadeOf} from './shots/MadeOf';
import {InOrder} from './shots/InOrder';
import {RestsOn} from './shots/RestsOn';
import {AcceptanceStamp} from './shots/AcceptanceStamp';
import {SurfaceCarousel} from './shots/SurfaceCarousel';
import {PointerTour} from './shots/PointerTour';
import {PageWrite} from './shots/PageWrite';
import {GlowPick} from './shots/GlowPick';
import {SourceDeal} from './shots/SourceDeal';
import {SpatialSlides} from './shots/SpatialSlides';
import {WordTunnel} from './shots/WordTunnel';
import {RackFocus} from './shots/RackFocus';

export const REGISTRY: Record<string, React.FC<any>> = {
  KSpaceToImage, MagnetizationTip, InducedFID, GFactorNoise, UndersampledKspace, ScanReconstruct, RealVersus, SpinningProton, PhaseEncodeStep, MRIPipeline, FrequencyEncode, CompressedSensingEq, KSpaceReal, SpeedLimit, LarmorPrecession, Aliasing, DiffusionDenoise, SpinsAlign, GradientTilt, KSpaceAnatomy, TensionScale, PlatformSurfaces, OpenQuestions,
  CollaborativeCursors, CommandSummon, TemporalAccelerate, FocalIsolation, KineticManifesto, InfiniteCanvas,
  BlockAssembly, AnswerStream, ScreenBubble, VelocitySnap, CursorStory, ExplodedSchematic, MaterialHero,
  TimelineTravel, MapRoutes, ChatThread, BeforeAfterSlider, AuroraFlow, IsometricAssembly, LiquidMorph,
  VoiceSignal, AsciiField, ParticleForm, HandDrawn, ChartLive, CartoonPop, LiquidChrome, CodeCompose,
  KnowledgeGraph, CinematicTitle, BlueprintGrid, SpotlightStage, AnalogTape, NeonGrid, SwissEditorial,
  ClayStack, LiquidFill, HalftonePop, PaperCutout, RadialBurst, SplitFlap, WireGlobe, LiquidGlass, HoloFoil,
  BokehPull, PixelBuild, BrutalistType, LightTrails, DataOrrery, PhysicsStack,
  OdometerRoll, QuadSplit, CardFlip3D, CubeRotate, GearTrain,
  FractureIn, PositioningMatrix, GaugeCluster, BentoReveal, ConveyorBelt,
  TermBars, TermTree, TermLog, TermGitLog, TermCounter, TermTable, TermDiff, TermThink,
  EdStat, EdTimeline, EdCompare,
  CardStack3D, CrashZoom, VersusSplit, RisoPrint, HudReticle,
  OverlapSeparation, SharedBlindspot,
  VariableTypeMorph, FlowField, MagazineSpread, PaperSlot, PortRail, RansomZine, DataMonolith,
  LowPolyForm, GlitchDatamosh, IsoWorld, MorphForms, NeonTickerWall,
  MetaballMerge, InflateType, ElasticType, AntiDesignChaos, NeuralField,
  DNAHelix, CircuitTrace, KaleidoMandala, InkBloom, ComicPanels,
  SpectrumPulse, StarfieldWarp, RidgeField, VoxelBuild, ChartRace,
  CodeRain, FractalTree, RainGlass, AtomOrbital, LiquidMetal,
  EmberFlame, ClothWave, GameOfLife, MoleculeBallStick, TerrainFly,
  SectionRoute,
  GazetteerEntry,
  MapPlate,
  StrataColumn,
  PlanPalimpsest,
  TallyLedger,
  MuseumLabel,
  Inscription,
  TechnicalPlate,
  ProfileGrowth,
  PhotoPlate,
  GrantedTree,
  LastLeg,
  MadeOf,
  InOrder,
  RestsOn,
  AcceptanceStamp,
  SurfaceCarousel,
  PointerTour,
  PageWrite,
  GlowPick,
  SourceDeal,
  SpatialSlides,
  WordTunnel,
  RackFocus,
};

export const SHOT_IDS = Object.keys(REGISTRY);
