// shotLuma — the ground-LUMINANCE class of each shot's SETTLED frame (dark | mid | light), measured
// deterministically from the rendered library (mean grayscale of a 6-frame strip). It is the luminance
// FOUNDATION the film tier reads: captions pick contrast against it (dark ground -> light ink, light ground ->
// dark ink) and P2 routes a dip-to-neutral transition whenever two adjacent shots differ. Re-derive for a NEW
// shot: render it, measure its mean grayscale, add an entry (a missing shot safely defaults to 'dark').
export type Lum = 'dark' | 'mid' | 'light';
// (KSpaceToImage added below with the map — a purpose-built dark shot)

export const SHOT_LUMA: Record<string, Lum> = {
  KSpaceToImage: 'dark', MagnetizationTip: 'dark', InducedFID: 'dark', GFactorNoise: 'dark', UndersampledKspace: 'dark', ScanReconstruct: 'dark', RealVersus: 'dark', SpinningProton: 'dark', PhaseEncodeStep: 'dark', MRIPipeline: 'dark', FrequencyEncode: 'dark', CompressedSensingEq: 'dark', KSpaceReal: 'dark', SpeedLimit: 'dark', LarmorPrecession: 'dark', Aliasing: 'dark', DiffusionDenoise: 'dark', SpinsAlign: 'dark', GradientTilt: 'dark', KSpaceAnatomy: 'dark', TensionScale: 'dark', PlatformSurfaces: 'dark', OpenQuestions: 'dark',
  AnalogTape: 'dark', AnswerStream: 'dark', AntiDesignChaos: 'light', AsciiField: 'dark',
  AtomOrbital: 'dark', AuroraFlow: 'mid', BeforeAfterSlider: 'light', BentoReveal: 'dark',
  BlockAssembly: 'light', BlueprintGrid: 'light', BokehPull: 'dark', BrutalistType: 'light',
  CardFlip3D: 'dark', CardStack3D: 'dark', CartoonPop: 'light', ChartLive: 'dark',
  ChartRace: 'dark', ChatThread: 'light', CinematicTitle: 'dark', CircuitTrace: 'dark',
  ClayStack: 'light', ClothWave: 'dark', CodeCompose: 'dark', CodeRain: 'dark',
  CollaborativeCursors: 'light', ComicPanels: 'light', CommandSummon: 'dark', ConveyorBelt: 'dark',
  CrashZoom: 'dark', CubeRotate: 'dark', CursorStory: 'dark', DNAHelix: 'dark',
  DataMonolith: 'dark', DataOrrery: 'dark', ElasticType: 'dark', EmberFlame: 'dark',
  ExplodedSchematic: 'dark', FlowField: 'dark', FocalIsolation: 'dark', FractalTree: 'dark',
  FractureIn: 'dark', GameOfLife: 'dark', GaugeCluster: 'dark', GearTrain: 'dark',
  GlitchDatamosh: 'dark', HalftonePop: 'light', HandDrawn: 'light', HoloFoil: 'dark',
  HudReticle: 'dark', InfiniteCanvas: 'light', InflateType: 'dark', InkBloom: 'light',
  IsoWorld: 'dark', IsometricAssembly: 'light', KaleidoMandala: 'dark', KineticManifesto: 'mid',
  KnowledgeGraph: 'dark', LightTrails: 'dark', LiquidChrome: 'dark', LiquidFill: 'dark',
  LiquidGlass: 'light', LiquidMetal: 'light', LiquidMorph: 'dark', LowPolyForm: 'dark',
  MagazineSpread: 'light', MapRoutes: 'dark', MaterialHero: 'dark', MetaballMerge: 'dark',
  MoleculeBallStick: 'dark', MorphForms: 'dark', NeonGrid: 'dark', NeonTickerWall: 'dark',
  NeuralField: 'dark', OdometerRoll: 'dark', PaperCutout: 'light', ParticleForm: 'dark',
  PhysicsStack: 'dark', PixelBuild: 'dark', PositioningMatrix: 'dark', QuadSplit: 'dark',
  RadialBurst: 'dark', RainGlass: 'dark', RansomZine: 'light', RidgeField: 'dark',
  RisoPrint: 'light', ScreenBubble: 'light', SpectrumPulse: 'dark', SplitFlap: 'dark',
  SpotlightStage: 'dark', StarfieldWarp: 'dark', SwissEditorial: 'light', TemporalAccelerate: 'light',
  TerrainFly: 'dark', TimelineTravel: 'light', VariableTypeMorph: 'dark', VelocitySnap: 'dark',
  VersusSplit: 'dark', VoiceSignal: 'dark', VoxelBuild: 'dark', WireGlobe: 'dark',
};

// the ground luminance for a scene: an explicit EDL `bgLum` wins, else the measured map, else 'dark'.
export const groundLum = (shot: string, bgLum?: Lum): Lum => bgLum ?? SHOT_LUMA[shot] ?? 'dark';
