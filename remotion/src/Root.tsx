import React from 'react';
import {AbsoluteFill, Composition} from 'remotion';
import {TextSafeAudit} from './runtime/textSafe';
import {CJK_MIN_LEADING} from './runtime/cjkType';
import {DesignDNAContext, coerceDna} from './runtime/dna';
import './runtime/fonts';  // side effect: loads the DNA typefaces for Film AND every standalone shot still
import {FontProbe, DURATION as FPR} from './runtime/__probe_fonts';
import {StageProbe, DURATION as SPD} from './runtime/__probe_stage3d';
import {TypeSpecimen, DURATION as TSP} from './runtime/__probe_specimen';
import {CollaborativeCursors, DURATION as CC} from './shots/CollaborativeCursors';
import {DollyZoom, DURATION as D_DOLLYZOOM} from './shots/DollyZoom';
import {RackFocus, DURATION as D_RACKFOCUS} from './shots/RackFocus';
import {WordTunnel, DURATION as D_WORDTUNNEL} from './shots/WordTunnel';
import {SpatialSlides, DURATION as D_SPATIALSLIDES} from './shots/SpatialSlides';
import {SourceDeal, DURATION as D_SOURCEDEAL} from './shots/SourceDeal';
import {GlowPick, DURATION as D_GLOWPICK} from './shots/GlowPick';
import {PageWrite, DURATION as D_PAGEWRITE} from './shots/PageWrite';
import {PointerTour, DURATION as D_POINTERTOUR} from './shots/PointerTour';
import {SurfaceCarousel, DURATION as D_SURFACECAROUSEL} from './shots/SurfaceCarousel';
import {AcceptanceStamp, DURATION as D_ACCEPTANCESTAMP} from './shots/AcceptanceStamp';
import {RestsOn, DURATION as D_RESTSON} from './shots/RestsOn';
import {InOrder, DURATION as D_INORDER} from './shots/InOrder';
import {MadeOf, DURATION as D_MADEOF} from './shots/MadeOf';
import {LastLeg, DURATION as D_LASTLEG} from './shots/LastLeg';
import {GrantedTree, DURATION as D_GRANTEDTREE} from './shots/GrantedTree';
import {PhotoPlate, DURATION as D_PHOTOPLATE} from './shots/PhotoPlate';
import {ProfileGrowth, DURATION as D_PROFILEGROWTH} from './shots/ProfileGrowth';
import {TechnicalPlate, DURATION as D_TECHNICALPLATE} from './shots/TechnicalPlate';
import {Inscription, DURATION as D_INSCRIPTION} from './shots/Inscription';
import {MuseumLabel, DURATION as D_MUSEUMLABEL} from './shots/MuseumLabel';
import {TallyLedger, DURATION as D_TALLYLEDGER} from './shots/TallyLedger';
import {PlanPalimpsest, DURATION as D_PLANPALIMPSEST} from './shots/PlanPalimpsest';
import {StrataColumn, DURATION as D_STRATACOLUMN} from './shots/StrataColumn';
import {MapPlate, DURATION as D_MAPPLATE} from './shots/MapPlate';
import {GazetteerEntry, DURATION as D_GAZETTEERENTRY} from './shots/GazetteerEntry';
import {SectionRoute, DURATION as D_SECTIONROUTE} from './shots/SectionRoute';
import {CommandSummon, DURATION as CS} from './shots/CommandSummon';
import {TemporalAccelerate, DURATION as TA} from './shots/TemporalAccelerate';
import {FocalIsolation, DURATION as FI} from './shots/FocalIsolation';
import {KSpaceToImage, DURATION as KSI} from './shots/KSpaceToImage';
import {MagnetizationTip, DURATION as MTP} from './shots/MagnetizationTip';
import {InducedFID, DURATION as IFD} from './shots/InducedFID';
import {GFactorNoise, DURATION as GFN} from './shots/GFactorNoise';
import {UndersampledKspace, DURATION as UKS} from './shots/UndersampledKspace';
import {ScanReconstruct, DURATION as SRC} from './shots/ScanReconstruct';
import {RealVersus, DURATION as RVS} from './shots/RealVersus';
import {SpinningProton, DURATION as SPN} from './shots/SpinningProton';
import {PhaseEncodeStep, DURATION as PES} from './shots/PhaseEncodeStep';
import {MRIPipeline, DURATION as MPL} from './shots/MRIPipeline';
import {FrequencyEncode, DURATION as FEN} from './shots/FrequencyEncode';
import {CompressedSensingEq, DURATION as CSE} from './shots/CompressedSensingEq';
import {KSpaceReal, DURATION as KSR} from './shots/KSpaceReal';
import {SpeedLimit, DURATION as SPL} from './shots/SpeedLimit';
import {LarmorPrecession, DURATION as LPR} from './shots/LarmorPrecession';
import {Aliasing, DURATION as ALI} from './shots/Aliasing';
import {DiffusionDenoise, DURATION as DDN} from './shots/DiffusionDenoise';
import {SpinsAlign, DURATION as SPA} from './shots/SpinsAlign';
import {GradientTilt, DURATION as GRT} from './shots/GradientTilt';
import {KSpaceAnatomy, DURATION as KAN} from './shots/KSpaceAnatomy';
import {TensionScale, DURATION as TNS} from './shots/TensionScale';
import {PlatformSurfaces, DURATION as PSF} from './shots/PlatformSurfaces';
import {OpenQuestions, DURATION as OQS} from './shots/OpenQuestions';
import {KineticManifesto, DURATION as KM} from './shots/KineticManifesto';
import {InfiniteCanvas, DURATION as IC} from './shots/InfiniteCanvas';
import {BlockAssembly, DURATION as BA} from './shots/BlockAssembly';
import {AnswerStream, DURATION as AS} from './shots/AnswerStream';
import {ScreenBubble, DURATION as SB} from './shots/ScreenBubble';
import {VelocitySnap, DURATION as VS} from './shots/VelocitySnap';
import {CursorStory, DURATION as CST} from './shots/CursorStory';
import {ExplodedSchematic, DURATION as ES} from './shots/ExplodedSchematic';
import {MaterialHero, DURATION as MH} from './shots/MaterialHero';
import {PaperSlot, DURATION as PSL} from './shots/PaperSlot';
import {PortRail, DURATION as PRL} from './shots/PortRail';
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
import {OdometerRoll, DURATION as ODR} from './shots/OdometerRoll';
import {QuadSplit, DURATION as QS} from './shots/QuadSplit';
import {CardFlip3D, DURATION as CF3} from './shots/CardFlip3D';
import {CubeRotate, DURATION as CBR} from './shots/CubeRotate';
import {GearTrain, DURATION as GT} from './shots/GearTrain';
import {FractureIn, DURATION as FR} from './shots/FractureIn';
import {PositioningMatrix, DURATION as PM} from './shots/PositioningMatrix';
import {GaugeCluster, DURATION as GC} from './shots/GaugeCluster';
import {BentoReveal, DURATION as BR} from './shots/BentoReveal';
import {ConveyorBelt, DURATION as CVB} from './shots/ConveyorBelt';
import {TermBars, DURATION as TBAR} from './shots/TermBars';
import {TermTree, DURATION as TTRE} from './shots/TermTree';
import {TermLog, DURATION as TLOG} from './shots/TermLog';
import {TermGitLog, DURATION as TGIT} from './shots/TermGitLog';
import {TermCounter, DURATION as TCNT} from './shots/TermCounter';
import {TermTable, DURATION as TTBL} from './shots/TermTable';
import {TermDiff, DURATION as TDIF} from './shots/TermDiff';
import {TermThink, DURATION as TTHK} from './shots/TermThink';
import {EdStat, DURATION as EDST} from './shots/EdStat';
import {EdTimeline, DURATION as EDTL} from './shots/EdTimeline';
import {EdCompare, DURATION as EDCM} from './shots/EdCompare';
import {CardStack3D, DURATION as CSK} from './shots/CardStack3D';
import {CrashZoom, DURATION as CZ} from './shots/CrashZoom';
import {OverlapSeparation, DURATION as OVS} from './shots/OverlapSeparation';
import {SharedBlindspot, DURATION as SBS} from './shots/SharedBlindspot';
import {VersusSplit, DURATION as VSU} from './shots/VersusSplit';
import {RisoPrint, DURATION as RIP} from './shots/RisoPrint';
import {HudReticle, DURATION as HUD} from './shots/HudReticle';
import {VariableTypeMorph, DURATION as VTM} from './shots/VariableTypeMorph';
import {FlowField, DURATION as FLF} from './shots/FlowField';
import {MagazineSpread, DURATION as MAG} from './shots/MagazineSpread';
import {RansomZine, DURATION as RZ} from './shots/RansomZine';
import {DataMonolith, DURATION as DML} from './shots/DataMonolith';
import {LowPolyForm, DURATION as LPF} from './shots/LowPolyForm';
import {GlitchDatamosh, DURATION as GDM} from './shots/GlitchDatamosh';
import {IsoWorld, DURATION as ISW} from './shots/IsoWorld';
import {MorphForms, DURATION as MPF} from './shots/MorphForms';
import {NeonTickerWall, DURATION as NTW} from './shots/NeonTickerWall';
import {MetaballMerge, DURATION as MBM} from './shots/MetaballMerge';
import {InflateType, DURATION as INF} from './shots/InflateType';
import {ElasticType, DURATION as ELT} from './shots/ElasticType';
import {AntiDesignChaos, DURATION as ADC} from './shots/AntiDesignChaos';
import {NeuralField, DURATION as NRF} from './shots/NeuralField';
import {DNAHelix, DURATION as DNA} from './shots/DNAHelix';
import {CircuitTrace, DURATION as CIR} from './shots/CircuitTrace';
import {KaleidoMandala, DURATION as KAL} from './shots/KaleidoMandala';
import {InkBloom, DURATION as INK} from './shots/InkBloom';
import {ComicPanels, DURATION as CMC} from './shots/ComicPanels';
import {SpectrumPulse, DURATION as SPC} from './shots/SpectrumPulse';
import {StarfieldWarp, DURATION as SFW} from './shots/StarfieldWarp';
import {RidgeField, DURATION as RDG} from './shots/RidgeField';
import {VoxelBuild, DURATION as VOX} from './shots/VoxelBuild';
import {ChartRace, DURATION as CRC} from './shots/ChartRace';
import {CodeRain, DURATION as CDR} from './shots/CodeRain';
import {FractalTree, DURATION as FRT} from './shots/FractalTree';
import {RainGlass, DURATION as RNG} from './shots/RainGlass';
import {AtomOrbital, DURATION as ATM} from './shots/AtomOrbital';
import {LiquidMetal, DURATION as LQM} from './shots/LiquidMetal';
import {EmberFlame, DURATION as EMB} from './shots/EmberFlame';
import {ClothWave, DURATION as CLW} from './shots/ClothWave';
import {GameOfLife, DURATION as GOL} from './shots/GameOfLife';
import {MoleculeBallStick, DURATION as MOL} from './shots/MoleculeBallStick';
import {TerrainFly, DURATION as TRN} from './shots/TerrainFly';
import {Film, WORKBUDDY_SCENES, filmDuration} from './Film';

// ASPECT support: the Composition dims are chosen from an `aspect` prop via calculateMetadata (default 16:9), so
// the SAME shots render at 9:16 / 1:1 / 4:5 without a separate composition. Shots read W/H from useVideoConfig and
// must lay out in FRACTIONS (see references/remotion-shot-authoring.md §A) so they reflow to the frame.
const ASPECTS: Record<string, [number, number]> = {
  '16:9': [1920, 1080], '9:16': [1080, 1920], '1:1': [1080, 1080], '4:5': [1080, 1350], '4:3': [1440, 1080],
};
const dims = (aspect?: string) => {
  const [width, height] = ASPECTS[String(aspect || '16:9')] || ASPECTS['16:9'];
  return {width, height};
};

// Redo tier: each bespoke shot registers as its OWN Composition (video-shotcraft pattern), renderable
// standalone for verification (pass --props '{"aspect":"9:16"}' to preview portrait). A film later sequences
// chosen shots through the pipeline wrapper.
// A standalone shot preview used to render with NO DesignDNA in scope, so every shot fell back to its own
// D0 constants — which meant a palette bug could only ever be seen after a full film render. Passing
// `--props='{"dna":"data"}'` (or a whole DNA object) now previews the shot inside the film's real design
// system, and `aspect` previews the reflow. Absent both, behaviour is exactly as before.

// A PERMANENT POSITIVE CONTROL for scripts/cjk_type_qa.py.
//
// The gate's first controls were two real registers that had broken a real film. They worked exactly once:
// the moment both were repaired the controls reported "not caught" and the instrument could no longer prove
// it detects anything. A control that depends on production code STAYING broken is not a control. This
// composition is deliberately mis-set — Chinese copy at 0.55 leading, which stacks its own lines — so the
// detector always has something it must find, and nothing anyone might fix removes it.
export const TypeCollisionProbe: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, background: '#fff', padding: 80}}>
    <div style={{width: 700, color: '#000',
      font: '800 96px/0.55 var(--f-display, Inter, system-ui, sans-serif)'}}>
      它自主拆解任务并在你授权的目录里真正动文件
    </div>
  </div>
);

// THE SAME TWO CLASSES, ON A TILT — because a client rect is axis-aligned and a rotated line's bounding box
// is taller than the line, so on tilted type the rect instrument reports a collision whether or not one
// exists. It did: `CardStack3D` fans its cards ±13° and a visibly-separated 46px/1 label was reported as a
// 64px collision on a real film. These two hold the instrument to both answers under rotation — the mis-set
// block must still be CAUGHT, and the well-set one must come back CLEAN. Both are synthetic and permanent,
// so neither depends on a production register staying broken (or staying fixed).
const TILT: React.CSSProperties = {transform: 'rotate(-13deg)', transformOrigin: 'center'};

export const TiltedTypeCollisionProbe: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, background: '#fff', padding: 80}}>
    <div style={{width: 700, color: '#000', ...TILT,
      font: '800 96px/0.55 var(--f-display, Inter, system-ui, sans-serif)'}}>
      它自主拆解任务并在你授权的目录里真正动文件
    </div>
  </div>
);

export const TiltedTypeCleanProbe: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, background: '#fff', padding: 80}}>
    <div style={{width: 700, color: '#000', ...TILT,
      font: '800 96px/1.3 var(--f-display, Inter, system-ui, sans-serif)'}}>
      它自主拆解任务并在你授权的目录里真正动文件
    </div>
  </div>
);


// TYPE INSIDE THE CAPTION BAND — the band audit's own positive control, and the reason it is synthetic.
//
// It used to be `AsciiField`, a register that drew a full-frame character field, and the test that used it
// wrote down the risk: "a positive control must not be a bug report". It became one anyway. AsciiField was
// putting 224 glyphs under the burned subtitle at 9:16 — a real defect — and fixing it took the control away
// with it, so the audit that proves the gate can SEE a band collision started reporting nothing, which is
// indistinguishable from a gate that cannot report at all.
//
// So the control is a probe: type deliberately placed inside the strip the renderer reserves, in a
// composition nobody will ever "fix". Paired with `CaptionBandCleanProbe`, which sets the same line in the
// content zone and must come back clean — a detector that fires on everything proves as little as one that
// fires on nothing.
const BAND_PROBE_TEXT = 'this line sits in the caption band';
export const CaptionBandProbe: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, background: '#fff'}}>
    <div style={{position: 'absolute', left: 80, right: 80, bottom: 24, color: '#000',
      font: '700 48px/1.2 var(--f-body, Inter, system-ui, sans-serif)'}}>{BAND_PROBE_TEXT}</div>
  </div>
);

export const CaptionBandCleanProbe: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, background: '#fff'}}>
    <div style={{position: 'absolute', left: 80, right: 80, top: 200, color: '#000',
      font: '700 48px/1.2 var(--f-body, Inter, system-ui, sans-serif)'}}>{BAND_PROBE_TEXT}</div>
  </div>
);


// A LAST LINE HOLDING ONE CHARACTER, and the one-property fix. Chinese breaks between any two glyphs, so a
// label a single unit too wide for its box drops one character onto a line of its own — a delivered film's
// card read 「Craft · 直接开」 over a line holding just 「干」. Fifteen characters in a box seven wide is that
// shape exactly: 7 / 7 / 1. The second probe is the same copy with `text-wrap: balance`, and it must come
// back clean, which is what makes the first one evidence rather than a coincidence.
const ORPHAN_COPY = '它自主拆解任务并在你授权的目录';

export const OrphanLineProbe: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, background: '#fff', padding: 80}}>
    <div style={{width: 700, color: '#000',
      font: '800 96px/1.3 var(--f-display, Inter, system-ui, sans-serif)'}}>{ORPHAN_COPY}</div>
  </div>
);

export const BalancedLineProbe: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, background: '#fff', padding: 80}}>
    <div style={{width: 700, color: '#000', textWrap: 'balance',
      font: '800 96px/1.3 var(--f-display, Inter, system-ui, sans-serif)'}}>{ORPHAN_COPY}</div>
  </div>
);

// THE LEADING FLOOR, AND ITS BOUNDARY. `tight` reports wrapped Chinese set below CJK_MIN_LEADING, and the
// first version compared the ratio alone: `line-height: 1.06` is a used value the browser rounds to whole
// pixels, so the ratio reads 1.0599… and two registers that already MEET the floor were reported, at a
// shortfall of 0px and 1px. The second probe here is set at EXACTLY the floor and must come back clean —
// that is the case that went wrong, and it is the one a threshold change would break again.
const FLOOR_COPY = '它自主拆解任务并在你授权的目录里真正动文件把重复动作沉淀成技能';

export const TightLeadingProbe: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, background: '#fff', padding: 80}}>
    <div style={{width: 900, color: '#000',
      font: '700 72px/0.95 var(--f-display, Inter, system-ui, sans-serif)'}}>{FLOOR_COPY}</div>
  </div>
);

export const FlooredLeadingProbe: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, background: '#fff', padding: 80}}>
    <div style={{width: 900, color: '#000',
      font: `700 72px/${CJK_MIN_LEADING} var(--f-display, Inter, system-ui, sans-serif)`}}>{FLOOR_COPY}</div>
  </div>
);

const DnaPreview: React.FC<{C: React.FC<any>; p: Record<string, unknown>}> = ({C, p}) => {
  const {dna, aspect: _a, ...rest} = p as {dna?: unknown; aspect?: unknown};
  const active = coerceDna(dna as never);   // a string is a preset name; an object is a partial DNA
  const _p = p as {textSafe?: unknown; typeCollisions?: unknown; fedText?: unknown};
  // `fedText` asks a THIRD question of the same walk: of the strings the caller fed this register, which
  // never reached the screen? It is how a gate tells a legitimately sparse frame from one drawn out of
  // `undefined` — see `auditFedText`.
  const mode = _p.fedText ? 'fed' as const : _p.typeCollisions ? 'collisions' as const : 'safe' as const;
  const audit = <TextSafeAudit enabled={Boolean(_p.textSafe || _p.typeCollisions || _p.fedText)}
                               mode={mode} fed={Array.isArray(_p.fedText) ? _p.fedText : []} />;
  const shot = <><C {...rest} />{audit}</>;
  if (!active) return shot;
  return (
    <DesignDNAContext.Provider value={active}>
      <style>{`.dna-film { --f-display: ${active.fontDisplay}; --f-body: ${active.fontBody}; --f-mono: ${active.fontMono}; }`}</style>
      <AbsoluteFill className="dna-film" style={{background: active.bgGrad ?? active.bg}}>{shot}</AbsoluteFill>
    </DesignDNAContext.Provider>
  );
};
const F = (id: string, C: React.FC<any>, d: number) => (
  <Composition id={id} component={(p: Record<string, unknown>) => <DnaPreview C={C} p={p} />}
    durationInFrames={d} fps={30} width={1920} height={1080} defaultProps={{}}
    calculateMetadata={({props}) => ({...dims((props as any).aspect)})} />
);
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Film" component={Film} fps={30} width={1920} height={1080}
      defaultProps={{scenes: WORKBUDDY_SCENES}}
      calculateMetadata={({props}) => ({durationInFrames: filmDuration((props as any).scenes ?? WORKBUDDY_SCENES),
        ...dims((props as any).aspect)})} />
    <Composition id="StageProbe" component={StageProbe} durationInFrames={SPD} fps={30}
      width={1920} height={1080} calculateMetadata={({props}) => ({...dims((props as any).aspect)})} />
    {F('TypeCollisionProbe', TypeCollisionProbe, 165)}
    {F('TiltedTypeCollisionProbe', TiltedTypeCollisionProbe, 165)}
    {F('TiltedTypeCleanProbe', TiltedTypeCleanProbe, 165)}
    {F('CaptionBandProbe', CaptionBandProbe, 165)}
    {F('CaptionBandCleanProbe', CaptionBandCleanProbe, 165)}
    {F('OrphanLineProbe', OrphanLineProbe, 165)}
    {F('BalancedLineProbe', BalancedLineProbe, 165)}
    {F('TightLeadingProbe', TightLeadingProbe, 165)}
    {F('FlooredLeadingProbe', FlooredLeadingProbe, 165)}
    {F('FontProbe', FontProbe, FPR)}
    {F('TypeSpecimen', TypeSpecimen, TSP)}
    {F('CollaborativeCursors', CollaborativeCursors, CC)}
    {F('CommandSummon', CommandSummon, CS)}
    {F('TemporalAccelerate', TemporalAccelerate, TA)}
    {F('FocalIsolation', FocalIsolation, FI)}
    {F('KSpaceToImage', KSpaceToImage, KSI)}
    {F('MagnetizationTip', MagnetizationTip, MTP)}
    {F('InducedFID', InducedFID, IFD)}
    {F('GFactorNoise', GFactorNoise, GFN)}
    {F('UndersampledKspace', UndersampledKspace, UKS)}
    {F('ScanReconstruct', ScanReconstruct, SRC)}
    {F('RealVersus', RealVersus, RVS)}
    {F('SpinningProton', SpinningProton, SPN)}
    {F('PhaseEncodeStep', PhaseEncodeStep, PES)}
    {F('MRIPipeline', MRIPipeline, MPL)}
    {F('FrequencyEncode', FrequencyEncode, FEN)}
    {F('CompressedSensingEq', CompressedSensingEq, CSE)}
    {F('KSpaceReal', KSpaceReal, KSR)}
    {F('SpeedLimit', SpeedLimit, SPL)}
    {F('LarmorPrecession', LarmorPrecession, LPR)}
    {F('Aliasing', Aliasing, ALI)}
    {F('DiffusionDenoise', DiffusionDenoise, DDN)}
    {F('SpinsAlign', SpinsAlign, SPA)}
    {F('GradientTilt', GradientTilt, GRT)}
    {F('KSpaceAnatomy', KSpaceAnatomy, KAN)}
    {F('TensionScale', TensionScale, TNS)}
    {F('PlatformSurfaces', PlatformSurfaces, PSF)}
    {F('OpenQuestions', OpenQuestions, OQS)}
    {F('KineticManifesto', KineticManifesto, KM)}
    {F('InfiniteCanvas', InfiniteCanvas, IC)}
    {F('BlockAssembly', BlockAssembly, BA)}
    {F('AnswerStream', AnswerStream, AS)}
    {F('ScreenBubble', ScreenBubble, SB)}
    {F('VelocitySnap', VelocitySnap, VS)}
    {F('CursorStory', CursorStory, CST)}
    {F('ExplodedSchematic', ExplodedSchematic, ES)}
    {F('MaterialHero', MaterialHero, MH)}
    {F('PaperSlot', PaperSlot, PSL)}
    {F('PortRail', PortRail, PRL)}
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
    {F('OdometerRoll', OdometerRoll, ODR)}
    {F('QuadSplit', QuadSplit, QS)}
    {F('CardFlip3D', CardFlip3D, CF3)}
    {F('CubeRotate', CubeRotate, CBR)}
    {F('GearTrain', GearTrain, GT)}
    {F('FractureIn', FractureIn, FR)}
    {F('PositioningMatrix', PositioningMatrix, PM)}
    {F('GaugeCluster', GaugeCluster, GC)}
    {F('BentoReveal', BentoReveal, BR)}
    {F('ConveyorBelt', ConveyorBelt, CVB)}
    {F('TermBars', TermBars, TBAR)}
    {F('TermTree', TermTree, TTRE)}
    {F('TermLog', TermLog, TLOG)}
    {F('TermGitLog', TermGitLog, TGIT)}
    {F('TermCounter', TermCounter, TCNT)}
    {F('TermTable', TermTable, TTBL)}
    {F('TermDiff', TermDiff, TDIF)}
    {F('TermThink', TermThink, TTHK)}
    {F('EdStat', EdStat, EDST)}
    {F('EdTimeline', EdTimeline, EDTL)}
    {F('EdCompare', EdCompare, EDCM)}
    {F('CardStack3D', CardStack3D, CSK)}
    {F('CrashZoom', CrashZoom, CZ)}
    {F('OverlapSeparation', OverlapSeparation, OVS)}
    {F('SharedBlindspot', SharedBlindspot, SBS)}
    {F('VersusSplit', VersusSplit, VSU)}
    {F('RisoPrint', RisoPrint, RIP)}
    {F('HudReticle', HudReticle, HUD)}
    {F('VariableTypeMorph', VariableTypeMorph, VTM)}
    {F('FlowField', FlowField, FLF)}
    {F('MagazineSpread', MagazineSpread, MAG)}
    {F('RansomZine', RansomZine, RZ)}
    {F('DataMonolith', DataMonolith, DML)}
    {F('LowPolyForm', LowPolyForm, LPF)}
    {F('GlitchDatamosh', GlitchDatamosh, GDM)}
    {F('IsoWorld', IsoWorld, ISW)}
    {F('MorphForms', MorphForms, MPF)}
    {F('NeonTickerWall', NeonTickerWall, NTW)}
    {F('MetaballMerge', MetaballMerge, MBM)}
    {F('InflateType', InflateType, INF)}
    {F('ElasticType', ElasticType, ELT)}
    {F('AntiDesignChaos', AntiDesignChaos, ADC)}
    {F('NeuralField', NeuralField, NRF)}
    {F('DNAHelix', DNAHelix, DNA)}
    {F('CircuitTrace', CircuitTrace, CIR)}
    {F('KaleidoMandala', KaleidoMandala, KAL)}
    {F('InkBloom', InkBloom, INK)}
    {F('ComicPanels', ComicPanels, CMC)}
    {F('SpectrumPulse', SpectrumPulse, SPC)}
    {F('StarfieldWarp', StarfieldWarp, SFW)}
    {F('RidgeField', RidgeField, RDG)}
    {F('VoxelBuild', VoxelBuild, VOX)}
    {F('ChartRace', ChartRace, CRC)}
    {F('CodeRain', CodeRain, CDR)}
    {F('FractalTree', FractalTree, FRT)}
    {F('RainGlass', RainGlass, RNG)}
    {F('AtomOrbital', AtomOrbital, ATM)}
    {F('LiquidMetal', LiquidMetal, LQM)}
    {F('EmberFlame', EmberFlame, EMB)}
    {F('ClothWave', ClothWave, CLW)}
    {F('GameOfLife', GameOfLife, GOL)}
    {F('MoleculeBallStick', MoleculeBallStick, MOL)}
    {F('TerrainFly', TerrainFly, TRN)}
    {F('SectionRoute', SectionRoute, D_SECTIONROUTE)}
    {F('GazetteerEntry', GazetteerEntry, D_GAZETTEERENTRY)}
    {F('MapPlate', MapPlate, D_MAPPLATE)}
    {F('StrataColumn', StrataColumn, D_STRATACOLUMN)}
    {F('PlanPalimpsest', PlanPalimpsest, D_PLANPALIMPSEST)}
    {F('TallyLedger', TallyLedger, D_TALLYLEDGER)}
    {F('MuseumLabel', MuseumLabel, D_MUSEUMLABEL)}
    {F('Inscription', Inscription, D_INSCRIPTION)}
    {F('TechnicalPlate', TechnicalPlate, D_TECHNICALPLATE)}
    {F('ProfileGrowth', ProfileGrowth, D_PROFILEGROWTH)}
    {F('PhotoPlate', PhotoPlate, D_PHOTOPLATE)}
    {F('GrantedTree', GrantedTree, D_GRANTEDTREE)}
    {F('LastLeg', LastLeg, D_LASTLEG)}
    {F('MadeOf', MadeOf, D_MADEOF)}
    {F('InOrder', InOrder, D_INORDER)}
    {F('RestsOn', RestsOn, D_RESTSON)}
    {F('AcceptanceStamp', AcceptanceStamp, D_ACCEPTANCESTAMP)}
    {F('SurfaceCarousel', SurfaceCarousel, D_SURFACECAROUSEL)}
    {F('PointerTour', PointerTour, D_POINTERTOUR)}
    {F('PageWrite', PageWrite, D_PAGEWRITE)}
    {F('GlowPick', GlowPick, D_GLOWPICK)}
    {F('SourceDeal', SourceDeal, D_SOURCEDEAL)}
    {F('SpatialSlides', SpatialSlides, D_SPATIALSLIDES)}
    {F('WordTunnel', WordTunnel, D_WORDTUNNEL)}
    {F('RackFocus', RackFocus, D_RACKFOCUS)}
    {F('DollyZoom', DollyZoom, D_DOLLYZOOM)}
  </>
);
