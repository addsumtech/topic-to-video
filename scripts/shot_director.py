#!/usr/bin/env python3
"""shot_director — propose a library register per beat as MATERIAL: a family-varied skeleton to adapt or borrow from.

It is NOT the beat's assignment. Design first (agents/shot-director.md Step 0.55): each beat's ideal picture
(`shot_fit.ideal`, no register named) is written BEFORE this runs, and the route — adapt, build, or as-is when the
register already IS the ideal — is the director's decision after it. This module is the DETERMINISTIC scaffold:
given the content_plan beats' `visual_intent`/`stage`/`climax`, it proposes a register per beat while VARYING THE
FAMILY (never two adjacent beats from the same family), records the proposal as `shot_fit.material` with
`verdict: "unjudged"`, keeps any `ideal`/`form` already written, and never touches a beat whose route was already
decided. It fills shot_props={} (the register's neutral defaults). validate.py's design-first floor refuses a
film left on its proposals. See remotion/LIBRARY.md for the catalogue.
"""
import argparse, json, os, re, sys

# register -> family letter. The family set is OPEN-ENDED (not fixed at 9): add a NEW letter when a bold new
# design language doesn't fit an existing bucket — the variety rule only cares that adjacent beats differ, so
# new families cost nothing. Current: A Product-UI · B Camera/space · C Kinetic type/title · D Data/technical ·
# E 3D/spatial · F Fluid/liquid/light (physical-feeling liquids & light) · G Illustrated/craft · H Comparison ·
# I Mechanical/physical · (J RETIRED — folded into P; letter free for a future language) ·
# K Generative/computed-fields (algorithmic pattern fields) · L Editorial/print · M Glitch/digital-decay ·
# N Isometric · O Urban/signage · P Dimensional/experimental type (type as living/physical material:
# variable-axis morph, inflated, elastic) · Q Anti-design/maximalist · R AI/neural · S Scientific/molecular ·
# T Circuit/hardware ·
# U Audio/music · V Cosmic/space · W Organic/botanical · X Weather/atmosphere · Y Fire/energy · Z Textile/fabric ·
# GE Geography (where / route / scale — offline Natural Earth projected in code: GlobeFocus, FlightArcs).
# Mirrors LIBRARY.md. (A–Z full; open AA+ if needed.) Boundary: F=physical liquids/light; K=computed algorithmic
# fields — so a "generative" beat is never ambiguous. Post-audit (2026-08-15): VoiceSignal F→U (audio waveform),
# IsometricAssembly G→N (all iso shots together), VariableTypeMorph J→P (J retired, one-shot subset of P).
FAMILY = {
    "EquationMorph": "MA",
    "FunctionPlot": "MA",
    "GlobeFocus": "GE",
    "FlightArcs": "GE",
    "GazetteerEntry": "JA",
    "StatedBy": "JA",
    "ProfileGrowth": "J",
    "PhotoToDiagram": "J",
    "PhotoPlate": "H",
    "Rearrange": "H",
    "ExtractionFlow": "H",
    "ObjectCompare": "H",
    "TechnicalPlate": "J",
    "Inscription": "JA",
    "MuseumLabel": "JA",
    "TallyLedger": "JA",
    "PlanPalimpsest": "J",
    "StrataColumn": "J",
    "MapPlate": "J",
    "CollaborativeCursors": "A", "CommandSummon": "A", "TemporalAccelerate": "A", "VelocitySnap": "A",
    "FilmScreen": "A",
    "LandscapeWell": "A",
    "ReplyWindow": "A",
    "PourSync": "A",
    "DeviceHero": "A",
    "DeviceDemo": "A",
    "TaskFold": "A",
    "CompanionCard": "A",
    "StateSheet": "L",
    "SeamBetween": "L",
    "CarryOver": "L",
    "FallbackPath": "A",
    "GlowPick": "A",
    "SurfaceCarousel": "A",
    "AcceptanceStamp": "A",
    "GrantedTree": "A",
    "CursorStory": "A", "ScreenBubble": "A", "AnswerStream": "A", "ChatThread": "A", "BlockAssembly": "A",
    "CodeCompose": "A", "LiquidGlass": "A", "BentoReveal": "A",
    "InfiniteCanvas": "B", "TimelineTravel": "B", "MapRoutes": "B", "ExplodedSchematic": "B", "CubeRotate": "B",
    "DollyZoom": "B",
    "RackFocus": "B",
    "PageWrite": "B",
    "PointerTour": "B",
    "CrashZoom": "B", "TerrainFly": "B",
    "OverlapSeparation": "D", "SharedBlindspot": "H",
    "LivingMap": "D",
    "RankRace": "D",
    "FlowCounter": "D",
    "FlowSankey": "D",
    "WeightedWheel": "D",
    "OrbitClockGain": "D",
    "Escalation": "D",
    "ShorteningHold": "C",
    "Callback": "C",
    "ColdOpen": "C",
    "MagicMoveType": "C",
    "WordRoll": "C",
    "HeadlineReveal": "C",
    "BreaksWhenAsked": "C",
    "HeldInstant": "D",
    "CraneUp": "B",
    "NearTheLine": "R",
    "ForkingAnswers": "D",
    "PulledThread": "Z",
    "AverageHides": "D",
    "ViewSwitch": "D",
    "TermSpace": "D",
    "SpatialSlides": "C",
    "WordTunnel": "C",
    "RestsOn": "D",
    "InOrder": "D",
    "MadeOf": "D",
    "KineticManifesto": "C", "FocalIsolation": "C", "SwissEditorial": "C", "BrutalistType": "C",
    "SourceDeal": "C",
    "LastLeg": "A",
    "LiquidChrome": "C", "HoloFoil": "C", "CinematicTitle": "C", "BokehPull": "C", "NeonGrid": "C",
    "AnalogTape": "C", "AsciiField": "C",
    "ChartLive": "D", "BlueprintGrid": "D", "KnowledgeGraph": "D", "WireGlobe": "D", "DataOrrery": "D",
    "OdometerRoll": "D", "GaugeCluster": "D", "HudReticle": "D", "ChartRace": "D",
    # terminal-native family (Term*) — one family so the adjacency-variety check discourages stacking terminal
    # boxes (the three-layer "don't box every frame" goal); the terminal COHERENCE comes from the DNA layer, not this tag.
    "TermBars": "D", "TermTree": "D", "TermLog": "D", "TermGitLog": "D", "TermCounter": "D",
    "TermTable": "D", "TermDiff": "D", "TermThink": "D",
    "MaterialHero": "E", "CardFlip3D": "E", "FractureIn": "E", "CardStack3D": "E", "DataMonolith": "E",
    "ObjectStage": "E",
    "MorphForms": "E", "KSpaceToImage": "E", "MagnetizationTip": "E",
    "InducedFID": "U", "GFactorNoise": "M", "UndersampledKspace": "D", "ScanReconstruct": "G", "RealVersus": "H", "SpinningProton": "S", "PhaseEncodeStep": "D", "MRIPipeline": "B", "FrequencyEncode": "U", "CompressedSensingEq": "L", "KSpaceReal": "G", "SpeedLimit": "D", "LarmorPrecession": "S", "Aliasing": "M", "DiffusionDenoise": "F", "SpinsAlign": "M", "GradientTilt": "U", "KSpaceAnatomy": "H", "TensionScale": "H", "PlatformSurfaces": "A", "OpenQuestions": "C",
    "GrowingFigure": "S",
    "LightShellOrbit": "F",
    "RangeSpheres": "S",
    "KSpaceToPicture": "S",
    "AuroraFlow": "F", "LiquidMorph": "F", "LiquidFill": "F", "ParticleForm": "F",
    "RadialBurst": "F", "LightTrails": "F", "MetaballMerge": "F", "InkBloom": "F", "LiquidMetal": "F",
    "HandDrawn": "G", "CartoonPop": "G", "HalftonePop": "G", "ClayStack": "G",
    "PaperCutout": "G", "SpotlightStage": "G", "PixelBuild": "G", "RisoPrint": "G", "ComicPanels": "G",
    "BeforeAfterSlider": "H", "QuadSplit": "H", "PositioningMatrix": "H", "VersusSplit": "H",
    "SplitFlap": "I", "PhysicsStack": "I", "GearTrain": "I", "ConveyorBelt": "I",
    "ObjectPath": "I",
    "SameStuffChanged": "I",
    "WorksThrough": "I",
    "HardBarrier": "I",
    "SectionRoute": "I",
    "FlowField": "K", "LowPolyForm": "K", "KaleidoMandala": "K", "RidgeField": "K", "GameOfLife": "K",
    "ObjectTurntable": "K",
    "MagazineSpread": "L", "PaperSlot": "L", "PortRail": "B", "RansomZine": "L",
    "EdStat": "L", "EdTimeline": "L", "EdCompare": "L",   # editorial-native family (Ed*) — grouped like Term* above
    "GlitchDatamosh": "M", "CodeRain": "M",
    "IsoWorld": "N", "VoxelBuild": "N", "IsometricAssembly": "N",
    "PlaneStack": "N",
    "NeonTickerWall": "O",
    "VariableTypeMorph": "P", "InflateType": "P", "ElasticType": "P",
    "WordDust": "P",
    "CroppedType": "P",
    "TypeOnPath": "P",
    "AntiDesignChaos": "Q",
    "NeuralField": "R",
    "DNAHelix": "S", "AtomOrbital": "S", "MoleculeBallStick": "S",
    "CircuitTrace": "T",
    "SpectrumPulse": "U", "VoiceSignal": "U",
    "StarfieldWarp": "V",
    "NebulaField": "V",
    "FractalTree": "W",
    "RainGlass": "X",
    "LightShafts": "X",
    "AuroraCurtain": "X",
    "LitMedium": "X",
    "EmberFlame": "Y",
    "ClothWave": "Z",
}

# register -> IDIOM WORLD: which world this shot's visual language comes FROM. Family says what a
# shot looks like; provenance says whose vocabulary it is speaking. A city documentary that came out of
# this library speaking developer-tooling (six terminal shots, a SaaS dashboard under a children's book
# character) passed every gate, because nothing in the pipeline knew that a `$ diff` belongs to a
# different world than a canal. A film declares meta.idiom_world; validate ERRORS on a beat whose
# register's provenance is not among them.
#
# KNOW WHAT THIS CANNOT DO: it catches a whole vocabulary arriving from the wrong world, which was the
# systematic failure. It does NOT catch a single beat misusing an in-world idiom — an industrial
# conveyor belt is legitimate in a harbour film and still wrong for people cycling to a station. That
# judgement is the shot-critic's (S10 meaning), and no table can make it.
# EVERY VALUE HERE MUST BE ONE OF `IDIOM_WORLDS` ABOVE, and for a session it was not. Seven registers
# carried `product-demo`, `product-hardware` or `paper-craft` — none of which is a world. `product-demo` is
# the name of a TEMPLATE (one of the six seed directions), and it had been written here as though it were a
# vocabulary. The effect was a catch-22 no film could escape: validate refuses `meta.idiom_world` entries it
# does not know, so a film using PortRail was told it draws from an undeclared world AND that the world it
# would have to declare is unknown. Seven registers were unusable in any film the gate would pass, and the
# only way out was to stop using them — which is how a gate gets switched off. `tests/test_provenance.py`
# pins the subset so it cannot drift again.
PROVENANCE = {
    "FilmScreen":              'product-ui',
    "PhotoToDiagram":          'photographic',
    "LivingMap":               'data-viz',
    "Callback":                'motion-graphics',
    "ColdOpen":                'motion-graphics',
    "WordDust":                'motion-graphics',
    "Rearrange":               'data-viz',
    "LandscapeWell":           'product-ui',
    "MagicMoveType":           'motion-graphics',
    "NebulaField":             'natural-world',
    "LightShafts":             'natural-world',
    "AuroraCurtain":           'natural-world',
    "FunctionPlot":            'scientific',
    "GrowingFigure":           'scientific',
    "EquationMorph":           'scientific',
    "RankRace":                'data-viz',
    "FlowCounter":             'data-viz',
    "FlowSankey":              'data-viz',
    "FlightArcs":              'motion-graphics',
    "GlobeFocus":              'motion-graphics',
    "LitMedium":               'craft-handmade',
    "CroppedType":             'motion-graphics',
    "TypeOnPath":              'motion-graphics',
    "WordRoll":                'motion-graphics',
    "HeadlineReveal":          'motion-graphics',
    "ForkingAnswers":          'data-viz',
    "WeightedWheel":           'data-viz',
    "ReplyWindow":             'product-ui',
    "OrbitClockGain":          'scientific',
    "LightShellOrbit":         'scientific',
    "RangeSpheres":            'scientific',
    "PourSync":                'product-ui',
    "ExtractionFlow":          'industrial',
    "KSpaceToPicture":         'scientific',
    "ObjectTurntable":         'motion-graphics',
    "ObjectPath":              'motion-graphics',
    "ObjectCompare":           'motion-graphics',
    "ObjectStage":             'motion-graphics',
    "DeviceHero":              'product-ui',
    "DeviceDemo":              'product-ui',
    "WorksThrough":            'scientific',
    "SameStuffChanged":        'scientific',
    "BreaksWhenAsked":         'print-editorial',
    "HardBarrier":             'survey-archive',
    "Escalation":              'data-viz',
    "ShorteningHold":          'motion-graphics',
    "HeldInstant":             'data-viz',
    "CraneUp":                 'motion-graphics',
    "NearTheLine":             'scientific',
    "PulledThread":            'craft-handmade',
    "AverageHides":            'data-viz',
    "SeamBetween":             'print-editorial',
    "ViewSwitch":              'product-ui',
    "StatedBy":                'survey-archive',
    "CarryOver":               'print-editorial',
    "PlaneStack":              'industrial',
    "TaskFold":                'product-ui',
    "CompanionCard":           'product-ui',
    "StateSheet":              'product-ui',
    "FallbackPath":            'product-ui',
    "TermSpace":               'developer-tooling',
    "DollyZoom":               'photographic',
    "RackFocus":               'photographic',
    "WordTunnel":              'motion-graphics',
    "SpatialSlides":           'motion-graphics',
    "SourceDeal":              'product-ui',
    "GlowPick":                'product-ui',
    "PageWrite":               'product-ui',
    "PointerTour":             'product-ui',
    "SurfaceCarousel":         'product-ui',
    "AcceptanceStamp":         'product-ui',
    "RestsOn":                 'data-viz',
    "InOrder":                 'data-viz',
    "MadeOf":                  'data-viz',
    "LastLeg":                 'product-ui',
    "GrantedTree":             'product-ui',
    "PhotoPlate":              'photographic',
    "Aliasing":                'scientific',
    "AnalogTape":              'motion-graphics',
    "AnswerStream":            'product-ui',
    "AntiDesignChaos":         'craft-handmade',
    "AsciiField":              'developer-tooling',
    "AtomOrbital":             'scientific',
    "AuroraFlow":              'motion-graphics',
    "BeforeAfterSlider":       'data-viz',
    "BentoReveal":             'product-ui',
    "BlockAssembly":           'product-ui',
    "BlueprintGrid":           'survey-archive',
    "BokehPull":               'motion-graphics',
    "BrutalistType":           'motion-graphics',
    "CardFlip3D":              'motion-graphics',
    "CardStack3D":             'motion-graphics',
    "CartoonPop":              'craft-handmade',
    "ChartLive":               'data-viz',
    "ChartRace":               'data-viz',
    "ChatThread":              'product-ui',
    "CinematicTitle":          'motion-graphics',
    "CircuitTrace":            'industrial',
    "ClayStack":               'craft-handmade',
    "ClothWave":               'craft-handmade',
    "CodeCompose":             'developer-tooling',
    "CodeRain":                'developer-tooling',
    "CollaborativeCursors":    'product-ui',
    "ComicPanels":             'craft-handmade',
    "CommandSummon":           'developer-tooling',
    "CompressedSensingEq":     'scientific',
    "ConveyorBelt":            'industrial',
    "CrashZoom":               'motion-graphics',
    "CubeRotate":              'motion-graphics',
    "CursorStory":             'product-ui',
    "DNAHelix":                'scientific',
    "DataMonolith":            'motion-graphics',
    "DataOrrery":              'data-viz',
    "DiffusionDenoise":        'scientific',
    "EdCompare":               'print-editorial',
    "EdStat":                  'print-editorial',
    "EdTimeline":              'print-editorial',
    "ElasticType":             'motion-graphics',
    "EmberFlame":              'natural-world',
    "ExplodedSchematic":       'motion-graphics',
    "FlowField":               'motion-graphics',
    "FocalIsolation":          'motion-graphics',
    "FractalTree":             'natural-world',
    "FractureIn":              'motion-graphics',
    "FrequencyEncode":         'scientific',
    "GFactorNoise":            'scientific',
    "GameOfLife":              'motion-graphics',
    "GaugeCluster":            'data-viz',
    "GazetteerEntry":          'survey-archive',
    "GearTrain":               'industrial',
    "GlitchDatamosh":          'motion-graphics',
    "GradientTilt":            'scientific',
    "HalftonePop":             'craft-handmade',
    "HandDrawn":               'craft-handmade',
    "HoloFoil":                'motion-graphics',
    "HudReticle":              'data-viz',
    "InducedFID":              'scientific',
    "InfiniteCanvas":          'motion-graphics',
    "InflateType":             'motion-graphics',
    "InkBloom":                'motion-graphics',
    "Inscription":             'survey-archive',
    "IsoWorld":                'motion-graphics',
    "IsometricAssembly":       'industrial',
    "KSpaceAnatomy":           'scientific',
    "KSpaceReal":              'scientific',
    "KSpaceToImage":           'scientific',
    "KaleidoMandala":          'motion-graphics',
    "KineticManifesto":        'motion-graphics',
    "KnowledgeGraph":          'data-viz',
    "LarmorPrecession":        'scientific',
    "LightTrails":             'motion-graphics',
    "LiquidChrome":            'motion-graphics',
    "LiquidFill":              'motion-graphics',
    "LiquidGlass":             'product-ui',
    "LiquidMetal":             'motion-graphics',
    "LiquidMorph":             'motion-graphics',
    "LowPolyForm":             'motion-graphics',
    "MRIPipeline":             'scientific',
    "MagazineSpread":          'print-editorial',
    "PaperSlot":               'craft-handmade',
    "PortRail":                'industrial',
    "MagnetizationTip":        'scientific',
    "MapPlate":                'survey-archive',
    "MapRoutes":               'motion-graphics',
    "MaterialHero":            'motion-graphics',
    "MetaballMerge":           'motion-graphics',
    "MoleculeBallStick":       'scientific',
    "MorphForms":              'motion-graphics',
    "MuseumLabel":             'survey-archive',
    "NeonGrid":                'motion-graphics',
    "NeonTickerWall":          'broadcast-signage',
    "NeuralField":             'developer-tooling',
    "OdometerRoll":            'industrial',
    "OpenQuestions":           'motion-graphics',
    "OverlapSeparation":       'scientific',
    "PaperCutout":             'craft-handmade',
    "ParticleForm":            'motion-graphics',
    "PhaseEncodeStep":         'scientific',
    "PhysicsStack":            'industrial',
    "PixelBuild":              'craft-handmade',
    "PlanPalimpsest":          'survey-archive',
    "PlatformSurfaces":        'product-ui',
    "PositioningMatrix":       'data-viz',
    "ProfileGrowth":           'survey-archive',
    "QuadSplit":               'data-viz',
    "RadialBurst":             'motion-graphics',
    "RainGlass":               'natural-world',
    "RansomZine":              'craft-handmade',
    "RealVersus":              'photographic',
    "RidgeField":              'motion-graphics',
    "RisoPrint":               'craft-handmade',
    "ScanReconstruct":         'photographic',
    "ScreenBubble":            'product-ui',
    "SectionRoute":            'survey-archive',
    "SharedBlindspot":         'scientific',
    "SpectrumPulse":           'audio-music',
    "SpeedLimit":              'scientific',
    "SpinningProton":          'scientific',
    "SpinsAlign":              'scientific',
    "SplitFlap":               'broadcast-signage',
    "SpotlightStage":          'craft-handmade',
    "StarfieldWarp":           'natural-world',
    "StrataColumn":            'survey-archive',
    "SwissEditorial":          'motion-graphics',
    "TallyLedger":             'survey-archive',
    "TechnicalPlate":          'survey-archive',
    "TemporalAccelerate":      'product-ui',
    "TensionScale":            'data-viz',
    "TermBars":                'developer-tooling',
    "TermCounter":             'developer-tooling',
    "TermDiff":                'developer-tooling',
    "TermGitLog":              'developer-tooling',
    "TermLog":                 'developer-tooling',
    "TermTable":               'developer-tooling',
    "TermThink":               'developer-tooling',
    "TermTree":                'developer-tooling',
    "TerrainFly":              'motion-graphics',
    "TimelineTravel":          'motion-graphics',
    "UndersampledKspace":      'scientific',
    "VariableTypeMorph":       'motion-graphics',
    "VelocitySnap":            'product-ui',
    "VersusSplit":             'data-viz',
    "VoiceSignal":             'audio-music',
    "VoxelBuild":              'motion-graphics',
    "WireGlobe":               'data-viz',
}

IDIOM_WORLDS = ['audio-music', 'broadcast-signage', 'craft-handmade', 'data-viz', 'developer-tooling', 'industrial', 'motion-graphics', 'natural-world', 'photographic', 'print-editorial', 'product-ui', 'scientific', 'survey-archive']

# candidates by visual_intent (ordered; the assigner picks the first whose family != the previous beat's)
CANDIDATES = {
    # mostly family C (kinetic type/title), plus cross-family options (E/F/I/G) so two ADJACENT statement beats
    # can still land in different families instead of both being C.
    "statement": ["CinematicTitle", "HeadlineReveal", "VariableTypeMorph", "FocalIsolation", "KineticManifesto", "SwissEditorial",
                  "BrutalistType", "LiquidChrome", "NeonGrid", "HoloFoil", "RisoPrint", "MagazineSpread",
                  "RansomZine", "MaterialHero", "FractureIn", "HudReticle", "FlowField", "LowPolyForm",
                  "GlitchDatamosh", "MorphForms", "NeonTickerWall", "MetaballMerge", "InflateType", "ElasticType",
                  "AntiDesignChaos", "DNAHelix", "KaleidoMandala", "InkBloom", "SpectrumPulse", "StarfieldWarp",
                  "RidgeField", "CodeRain", "FractalTree", "RainGlass", "AtomOrbital", "LiquidMetal",
                  "EmberFlame", "ClothWave", "GameOfLife", "MoleculeBallStick", "TerrainFly",
                  "AuroraFlow", "SplitFlap", "PixelBuild", "DeviceHero", "CroppedType", "LitMedium"],
    "sequence": ["ExplodedSchematic", "TimelineTravel", "CubeRotate", "CommandSummon", "GearTrain", "ConveyorBelt",
                 "IsoWorld", "ComicPanels", "CircuitTrace", "CodeCompose", "DeviceDemo"],
    "structure": ["CollaborativeCursors", "KnowledgeGraph", "CrashZoom", "MapRoutes", "DataOrrery", "WireGlobe",
                  "BlueprintGrid", "CubeRotate", "BentoReveal", "IsoWorld", "NeuralField", "CircuitTrace", "DNAHelix",
                  "PositioningMatrix", "DataMonolith", "VoxelBuild", "CardStack3D", "IsometricAssembly", "FlightArcs", "GlobeFocus"],
    # mostly family A; cross-family options (I/G/E) so two ADJACENT list beats don't both land in A.
    "list": ["BlockAssembly", "TemporalAccelerate", "CursorStory", "AnswerStream", "SplitFlap", "CardStack3D", "PhysicsStack", "HandDrawn"],
    "metric": ["OdometerRoll", "ChartLive", "ChartRace", "GaugeCluster", "DataMonolith", "PhysicsStack", "BlueprintGrid", "BeforeAfterSlider", "FlowCounter", "RankRace", "FlowSankey", "FunctionPlot"],
    # contrast/before-after — cross-family so two adjacent contrast beats differ (H comparison + I + E + C).
    "contrast": ["BeforeAfterSlider", "VersusSplit", "QuadSplit", "SharedBlindspot", "PositioningMatrix", "CardFlip3D", "SplitFlap",
                 "WordRoll"],
}
CLIMAX = ["ParticleForm", "RadialBurst", "FractureIn", "MorphForms", "SpectrumPulse", "EmberFlame", "LightTrails", "SpotlightStage", "LiquidFill"]

# ── REACH: the argument's SHAPE → the capability built for it ─────────────────────────────────────────────────────────
# The intent lists above match a KEYWORD (`metric`, `statement`), and three benchmark films (2026-10-24) found what that
# costs: the kinetic registers were barely proposed, the data/geography and maths registers never were (none of
# EquationMorph, GrowingFigure, FunctionPlot, TypeOnPath, CroppedType, WordRoll or LitMedium sat in any list), and no
# film reached camera space, because WorldStage is a stage run and nothing in the authoring path ever said when one is
# the right tool. A capability the director is never offered is built but unreachable.
#
# So each beat's ARGUMENT — the form the director derived from the subject (`shot_fit.form` and its entry in
# `meta.form_vocabulary`), the ideal picture (`shot_fit.ideal`) and the plan's `learning_point`/`narration_intent` — is
# read for the shapes these tools were built for. FORMS STILL COME FROM THE SUBJECT: nothing here names a form; it says
# which built tool draws the shape a form the director already chose is arguing. A matched route puts its registers
# first in the proposal (still MATERIAL, verdict unjudged) and every match is recorded in `shot_fit.reach` with when it
# is right and when it is not, so the director routes against it rather than discovering it. The full table, with the
# reading-time and tempo rules, is references/remotion-shot-authoring.md §F; the `when`/`not` lines are each card's.
#
# Cues are deliberately specific (a bare "becomes" or "国家" would fire on every film) and bilingual; a cue that fires on
# the wrong beat costs a line in shot_fit.reach, a missing one costs the capability. Ordered most specific first: the
# FIRST matched route with registers supplies the material.
REACH = [
    {"key": "derivation", "registers": ["EquationMorph"],
     "cues": [r"(?i)\bderiv(e|es|ed|ing|ation)\b", r"(?i)\bequations?\b", r"(?i)\bformula", r"(?i)\bsolv(e|es|ing) for\b",
              r"(?i)\bsimplif", r"(?i)\brearrang", r"(?i)\bsubstitut", "推导", "公式", "方程", "化简", "代入", "求解", "等式"],
     "when": "the next form IS the last one rearranged — solving, simplifying, substituting, deriving — or one formula "
             "with a term to point at",
     "not": "a quantity's history (a chart), several unrelated formulas, prose that merely mentions a formula",
     "needs": "the film's TeX in `steps[].tex` (scripts/mathtex.py typesets it before the render)"},
    {"key": "dependence-shape", "registers": ["FunctionPlot"],
     "cues": [r"(?i)\bcurves?\b", r"(?i)\bfunction of\b", r"(?i)\bdecay", r"(?i)\boscillat", r"(?i)\bexponential",
              r"(?i)\bgrows? faster", r"(?i)\bas (the )?\w+ (increases|grows|rises|falls)\b", "曲线", "函数", "衰减",
              "指数", "振荡", r"随着.{0,8}(增加|增大|变大|升高|下降)"],
     "when": "the SHAPE of a dependence is the point — where it rises, turns, dies away",
     "not": "comparing categories (a bar register), a history with events on it, one number",
     "needs": "the film's own samples `points` [[x, y], …], sourced — nothing is fitted or smoothed"},
    {"key": "shape-becomes-shape", "registers": ["GrowingFigure", "MorphForms"],
     "cues": [r"(?i)\bmorph(s|ing)?\b", r"(?i)\bdivides? into\b", r"(?i)\bcell division\b",
              r"(?i)\b(becomes|turns into|grows into) (a|an|one|two) (circle|square|triangle|segment|line|cell|cells|"
              r"sphere|cube|shape)\b", r"(?i)\bone (shape|figure) through\b", "分裂成",
              r"(变成|演变成|长成)(一个|一条|一颗|两个)?(圆|正方形|方形|三角|线段|细胞|球)"],
     "when": "continuity of ONE thing through its stages — a cell that stretches and divides, a point that becomes a "
             "segment, a triangle, a square",
     "not": "different things (a list register), two objects compared (an H register), a quantity growing (a chart)",
     "needs": "the states' shapes (`d` paths the film draws, or the built-in ones)"},
    {"key": "journey-across-scales", "registers": ["InfiniteCanvas", "CrashZoom"],
     "stage": "WorldStage", "moves": ["scale-zoom"],
     "cues": [r"(?i)\bacross scales\b", r"(?i)\bpowers of (ten|10)\b", r"(?i)\bnested (scales|inside)\b",
              r"(?i)\bmagnif(y|ied|ies|ication) (to|into|down)\b",
              r"(?i)\bzoom(s|ing)? (in|out|down)? ?(from|through|across)\b", r"(?i)\bscale(s)? of (the )?(universe|cell|body)",
              r"(?i)\bfrom the (planet|earth|city|galaxy|body|organ|country) (down )?to\b", "尺度", "放大到", "缩小到",
              "一层层", r"层层(深入|放大)", r"从.{1,8}到.{0,4}(细胞|分子|原子|星系|地球|城市)", "微观", "宏观"],
     "when": "the subject is a journey across scales — a planet into a region into a city: ONE continuous zoom "
             "through nested scales (exponential, the fixed point held still), not a cut per scale",
     "not": "two unrelated places (a cut is honest), or a push on one flat picture with nothing nested in it "
            "(slide.camera push)",
     "needs": "a stage run: `stage.run` on consecutive beats, `world.objects` with each scale `in` its parent "
              "(references/stage-runs.md WorldStage)"},
    {"key": "route-between-places", "registers": ["FlightArcs", "MapRoutes"],
     "cues": [r"(?i)\b(flight|shipping|trade|migration|air|sea) (routes?|lanes?|paths?)\b", r"(?i)\broutes? (from|between)\b",
              r"(?i)\bflights? (from|between)\b", r"(?i)\bgreat[- ]circle", r"\b(from|between) [A-Z][a-z]+ (to|and) [A-Z][a-z]+",
              "航线", "航班", "航路", r"(贸易|运输|迁徙|飞行|航行)路线", r"从.{1,6}飞往", r"之间的(距离|航线|路线)"],
     "when": "these places are connected and how far apart they really are — a great circle's length and poleward "
             "bulge are the geometry",
     "not": "connections with no geography (MapRoutes, KnowledgeGraph), one place (GlobeFocus)",
     "needs": "the places' real coordinates or names the geo runtime resolves (offline Natural Earth)"},
    {"key": "journey-through-space", "registers": ["TerrainFly", "CraneUp"],
     "stage": "WorldStage", "moves": ["dolly"],
     "move_cues": {"tilt": [r"(?i)\b(layers?|bands?) of the (sky|atmosphere|ocean)", r"(?i)\baltitude", "大气层",
                            "海拔", "高度层", r"(?i)\btilt"],
                   "crane": [r"(?i)\b(rise|rises|climb|climbs) (up )?(above|over)\b", "升到", "俯瞰"],
                   "orbit": [r"(?i)\borbit(s|ing)? (round|around)\b", r"(?i)\bfrom every side\b", "绕着", "环绕"]},
     "cues": [r"(?i)\b(fly|flies|flying|travel|travels|travelling|traveling) (from|through|across|down|up|to)\b",
              r"(?i)\bjourneys? (from|through|across|down|up) (the )?(sun|earth|sky|atmosphere|ocean|space|body|city|"
              r"planet|layers?)\b", r"(?i)\bfrom the sun to\b", r"(?i)\b(layers?|bands?) of the (sky|atmosphere|ocean)",
              r"(?i)\baltitude", r"(?i)\borbit(s|ing)? (round|around)\b", "飞向", "飞过", "穿过", "穿越", "从太阳到",
              "大气层", "海拔", "高度层", "绕着"],
     "when": "the subject HAS a geography the camera can travel — a dolly from the Sun to the Earth, a tilt up through "
             "the layers of the sky, an orbit round the thing — one place, so no cut",
     "not": "beats that are separate arguments (they are separate shots), a camera move with nothing at depth "
            "(parallax needs ≥2 planes)",
     "needs": "a stage run with `world.objects` placed in depth (`at` [x, y, z]); give a camera move 1.5–4 s"},
    {"key": "flow-of-a-quantity", "registers": ["FlowSankey", "MadeOf"],
     "cues": [r"(?i)\b(flow|flows|flowing) of (money|energy|water|goods|people|traffic|cash|funds|heat|power|capital|"
              r"carbon|oil|gas|food|freight|migrants|visitors)\b", r"(?i)(?<!user )(?<!work )(?<!app )\b(flows|flowing) "
              r"(into|from|through|to)\b", r"(?i)\bcash flow", r"(?i)\bwhere (the|a|its|every) \w+ goes\b",
              r"(?i)\bbudget",
              r"(?i)\bfunnel\b", r"(?i)\bsupply chain", r"(?i)\benergy balance", r"(?i)\bconserv(ed|ation)\b",
              "流向", "去向", "流入", "流出", "分配到", "预算", "守恒", "漏斗", "供应链"],
     "when": "where a whole goes and that it is conserved — a budget by programme, an energy balance, a funnel, a "
             "supply chain: the split and the rejoin are the argument",
     "not": "parts of one whole with no stages (MadeOf), a ranking (RankRace), connections with no quantity",
     "needs": "the film's sourced flow values on one scale"},
    {"key": "ranking-over-time", "registers": ["RankRace", "ChartRace"],
     "cues": [r"(?i)\brank(s|ed|ing|ings)?\b", r"(?i)\bovertak", r"(?i)\bleaderboard", r"(?i)\bpulls? ahead",
              "排名", "反超", "名次", "排行"],
     "when": "a ranking changed over time and WHEN the order changed is the story",
     "not": "one period (ChartRace, PhysicsStack), one quantity moving (FlowCounter), order that is not the point",
     "needs": "the film's sourced series, every period's figure exactly as written"},
    {"key": "one-quantity-moving", "registers": ["FlowCounter", "OdometerRoll"],
     "cues": [r"(?i)\b(grew|grows|rose|rises|fell|falls|climbed|jumped|dropped) (from|to)\b",
              r"(?i)\bfrom [\d.,]+\s*\S{0,12} to [\d.,]+", r"(增长|上涨|下降|增加|减少|涨|跌)(到|至)",
              r"从[\d.,]+.{0,6}(到|增长到|涨到)"],
     "when": "one quantity and how it moved — 1.2B, then 3.45B, then 12.8B — the distance travelled felt",
     "not": "several figures side by side (a stat or table register), a figure that does not move, a ranking",
     "needs": "the film's sourced values, in order"},
    {"key": "where", "registers": ["GlobeFocus", "MapPlate"],
     "cues": [r"(?i)\bwhere (is|are) (it|they|the|this|that)\b", r"(?i)\bwhere on (earth|the map|the globe)\b",
              r"(?i)\blocated (in|on|at|off)\b", r"(?i)\bon the map\b",
              r"(?i)\b(coast|coastline|region|province|island|peninsula|corridor)\b", "位于", "在哪", "哪里", "地图上",
              "海岸", "哪个国家", "半岛"],
     "when": "the claim is WHERE, at the scale that makes it legible — a country, a coast, two cities in one corridor",
     "not": "a route between places (FlightArcs), places with no geography between them (a list), an engraved or "
            "imagined plate (MapPlate)",
     "needs": "the place's name or coordinates"},
    {"key": "slot-that-varies", "registers": ["WordRoll"],
     "cues": [r"(?i)\bnot \w+(,| or) not \w+", r"(?i)\bnot (just|only) .{1,30}\bbut\b",
              r"(?i)\bit('s| is) not .{1,30}it('s| is)\b", r"不是.{1,12}而是", r"不是.{1,8}也不是"],
     "when": "\"it is not X, not Y — it is Z\", or one sentence true of A, of B, of C: what is constant and what "
             "varies IS the argument",
     "not": "peers to be read together (a list register), nothing that varies (HeadlineReveal)",
     "needs": "the options in the order the sentence lands them; each must be READ (see `timing`)"},
    {"key": "same-set-seen-again", "registers": ["Rearrange"],
     "cues": [r"(?i)\bthe same (items|things|ones|options|parts|sources|factors)\b", r"(?i)\bregroup",
              r"(?i)\bsorted? (them )?by\b", r"(?i)\bin order of\b", r"(?i)\bwhich (one|of them) matters\b",
              r"(?i)\bgroup(ed)? (them )?(by|into)\b", r"(?i)\bput (them )?in order\b",
              "按.{0,8}排", "排个序", "重新分组", "归成", "分成两类", "其中最重要", "同样这些"],
     "when": "one SET of things looked at again and again — all equal, then the one that matters, then in order of a "
             "sourced value, then by what they belong to: the beat changes its mind about the same items",
     "not": "a ranking that changes over TIME (RankRace), one quantity (FlowCounter), a whole and its parts (MadeOf)",
     "needs": "2-12 items; a `value` on every item for `rank`, a `group` on every item for `groups`"},
    {"key": "scale-word", "registers": ["CroppedType"],
     "cues": [r"(?i)\b(huge|enormous|massive|vast|gigantic|immense|the scale of)\b", "巨大", "庞大", "规模之大"],
     "when": "the claim is SCALE and one word carries it — the crop makes the word read as big, not merely large",
     "not": "a word that must be read whole and still (VariableTypeMorph), a headline (HeadlineReveal); a CJK word "
            "a crop can cut into other characters",
     "needs": "one word + the plain sentence it stands for (the sentence is the must-read line)"},
    {"key": "shape-is-claim", "registers": ["TypeOnPath"],
     "cues": [r"(?i)\b(cycle|cycles|cyclical|loop|loops|repeats|feeds (itself|back)|spiral|round and round)\b",
              "循环", "周而复始", "闭环", "螺旋"],
     "when": "the SHAPE is the claim — hide the caption and the path alone says \"this repeats\", \"this rises\", "
             "\"this is the route\"",
     "not": "steps in order (a process register), one static claim (HeadlineReveal); never a shape picked for looks",
     "needs": "a path that is the subject's own shape (ring, wave, climb, loop, or the film's `d`)"},
    {"key": "headline", "registers": ["HeadlineReveal"],
     "cues": [r"(?i)\b(headline|manifesto|slogan|tagline|motto|one line|in one breath|one sentence)\b", "宣言", "标语",
              "口号", "一句话", "金句"],
     "when": "the headline IS the beat — one claim said in one breath, the sentence's rhythm the design, one phrase "
             "of it marked `*…*`",
     "not": "a list of peers, one enormous word (CroppedType), a sentence with a slot that changes (WordRoll)",
     "needs": "the line(s) as the narration says them; each must-read line is held to its reading time"},
    {"key": "medium", "registers": ["LitMedium"],
     "cues": [r"(?i)\bmade (of|from) (paper|wood|clay|metal|glass|stone|water|steel)\b",
              r"(?i)\b(milled|hand-?made|shaped by hand|hand-?thrown|carved|forged|woven|on paper)\b",
              r"(?i)\b(harbou?r|clay|brushed metal)\b", "手工", "材质", "纸上", "黏土", "陶土", "打磨", "锻造"],
     "when": "what something is made of or where it lives — \"it started on paper\", \"the harbour decides\", "
             "\"milled from one block\": the medium as a lit surface, ONE light drifting across it",
     "not": "a breakdown of parts (MadeOf), a medium the subject is not made of",
     "needs": "`material` paper | water | metal | clay (or the DNA's `material: {kind}`)"},
    {"key": "light-as-content", "registers": ["SpotlightStage", "EmberFlame", "StarfieldWarp"],
     "optic": True,
     "cues": [r"(?i)\b(light|glow) (of|from|on|through|spills|falls|hits|pours)\b", r"(?i)\blights? up\b",
              r"(?i)\b(glows|glowing|shines|shining|flame|flames|spotlight|starlight|lamp|laser|beam of|flare|lit screen)\b",
              "发光", "火焰", "火光", "星光", "灯光", "激光", "光束", "照亮"],
     "when": "the picture HAS a light and the light is the content — a lit screen, a star, a spotlight, a flame: "
             "`slide.optic` (bloom / halation / sweep / aberration) on the register that draws it, or `leak` over the "
             "seam INTO the beat",
     "not": "decoration on a frame with no source of light; never on type (the glow is kept off the words)",
     "needs": "a register (or the film's own shot) that exports OPTICS — validate refuses an optic its register "
              "cannot anchor"},
]
_REACH_RE = {r["key"]: [re.compile(c) for c in r["cues"]] for r in REACH}
_MOVE_RE = {r["key"]: {m: [re.compile(c) for c in cs] for m, cs in (r.get("move_cues") or {}).items()} for r in REACH}


def _vocab_entry(form, vocab):
    """The `meta.form_vocabulary` entry naming this form, as one string (form + carries + looks_like), or ''."""
    for e in vocab or []:
        if isinstance(e, dict) and str(e.get("form") or "").strip() == form:
            return " ".join(str(e.get(k) or "") for k in ("form", "carries", "looks_like"))
    return ""


def beat_argument(slide, beat=None, vocab=None):
    """The text a beat's ARGUMENT is written in: its form (and the vocabulary's account of it), its ideal picture,
    and the plan's learning point and narration intent. The narration itself is left out — it names things in
    passing, and a cue that fires on a word said in passing is noise."""
    fit = slide.get("shot_fit") if isinstance(slide.get("shot_fit"), dict) else {}
    form = str(fit.get("form") or "").strip()
    parts = [form, _vocab_entry(form, vocab), str(fit.get("ideal") or "")]
    b = beat or {}
    parts += [str(b.get("learning_point") or ""), str(b.get("narration_intent") or "")]
    return " \n ".join(p for p in parts if p)


def match_reach(text):
    """[route, …] — every REACH route whose cue the argument text carries, in REACH order. A route is a dict with
    `key`, `registers`, and when it applies `stage` + `moves`, `optic`; plus `when` / `not` / `needs`."""
    out = []
    if not text:
        return out
    for r in REACH:
        if any(p.search(text) for p in _REACH_RE[r["key"]]):
            hit = dict(r)
            if r.get("move_cues"):
                moves = [m for m, ps in _MOVE_RE[r["key"]].items() if any(p.search(text) for p in ps)]
                hit["moves"] = moves or list(r.get("moves") or [])
            out.append(hit)
    return out


def _reach_note(route):
    """What shot_fit.reach records for one matched route — the tool, when it is right, when it is not."""
    note = {"route": route["key"]}
    if route.get("stage"):
        note["stage"], note["moves"] = route["stage"], list(route.get("moves") or ["dolly"])
        use = "%s run · camera.move %s" % (route["stage"], " / ".join(note["moves"]))
        if route.get("registers"):
            use += " (a one-beat stand-in: %s)" % ", ".join(route["registers"])
    elif route.get("optic"):
        offered = ["%s: %s" % (r, "/".join(register_optics(r)) or "none") for r in route["registers"]]
        use = "slide.optic on a register that draws the light (%s), or `leak` into the beat" % "; ".join(offered)
    else:
        use = " or ".join(route["registers"])
    note.update({"use": use, "when": route["when"], "not": route["not"], "needs": route["needs"]})
    return note


_SHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "shots")
_SRC_CACHE = {}


def _shot_source(shot):
    if shot not in _SRC_CACHE:
        try:
            _SRC_CACHE[shot] = open(os.path.join(_SHOTS_DIR, "%s.tsx" % shot), encoding="utf-8").read()
        except (OSError, TypeError):
            _SRC_CACHE[shot] = ""
    return _SRC_CACHE[shot]


def register_optics(shot):
    """The optics a library register anchors — its `export const OPTICS = [...]` (the list validate.py reads)."""
    m = re.search(r"^export const OPTICS\s*=\s*\[([^\]]*)\]", _shot_source(shot), re.M)
    return tuple(re.findall(r"'(\w+)'", m.group(1))) if m else ()


def authored_seconds(shot):
    """A register's own length in seconds (`export const DURATION` frames at the Film's 30 fps), or None."""
    m = re.search(r"^export const DURATION\s*=\s*(\d+)", _shot_source(shot), re.M)
    return int(m.group(1)) / 30.0 if m else None


def reading_held(shot):
    """Does this register set its copy with runtime/kinetic — the type `shot_proof.py` holds to reading time?"""
    return bool(re.search(r"""from\s+['"]\.\./runtime/kinetic['"]""", _shot_source(shot)))


def timing_note(shot, seconds):
    """A sentence when a reading-held register is proposed for a beat planned shorter than its own length, else None.
    The register still renders (every register is time-normalised to its beat); what shrinks is the time each
    must-read line has, which is what shot_proof measures and the launch benchmark ran into (WordRoll's second option
    readable 0.73 s against 0.83 s needed, on a 3-4 s beat)."""
    own = authored_seconds(shot)
    try:
        s = float(seconds)
    except (TypeError, ValueError):
        return None
    if own is None or s <= 0 or not reading_held(shot) or s >= own:
        return None
    return ("%s is authored for %.1f s and this beat is planned at %.1f s: shot_proof holds every must-read line to its "
            "reading time (runtime/readingSpec.json) — cut what must be read (lines, options, steps) to what %.1f s "
            "holds (`pace.py --budget %.1f`), or give the beat its length" % (shot, own, s, s, s))


def stage_run_hints(slides):
    """[(first, last, stage, moves)] — consecutive beats whose shot_fit.reach names one stage: a camera that should
    travel ONE world across them rather than cut between flat beats. 0-based, inclusive."""
    def stage_of(s):
        fit = s.get("shot_fit") if isinstance(s.get("shot_fit"), dict) else {}
        notes = [n for n in fit.get("reach") or [] if isinstance(n, dict) and n.get("stage")]
        if not notes:
            return None, []
        moves = []
        for n in notes:
            if n["stage"] == notes[0]["stage"]:
                moves += [m for m in n.get("moves") or [] if m not in moves]
        return notes[0]["stage"], moves
    out, i = [], 0
    while i < len(slides):
        st, moves = stage_of(slides[i])
        if not st:
            i += 1
            continue
        j = i
        while j + 1 < len(slides) and stage_of(slides[j + 1])[0] == st:
            j += 1
            moves += [m for m in stage_of(slides[j])[1] if m not in moves]
        out.append((i, j, st, moves))
        i = j + 1
    return out


def container_hints(slides, out_dir=None):
    """[(i, why)] — seams (into 0-based beat i) where the two beats realise the SAME form or the same built thing: the
    shared element can stay on screen and be re-framed (`container`, this IS that). seam_plan.py proposes the container
    itself once both beats are routed and their registers draw one anchor; this names where to make that possible."""
    out = []
    for i in range(1, len(slides)):
        a = slides[i - 1].get("shot_fit") if isinstance(slides[i - 1].get("shot_fit"), dict) else {}
        b = slides[i].get("shot_fit") if isinstance(slides[i].get("shot_fit"), dict) else {}
        fa, fb = str(a.get("form") or "").strip(), str(b.get("form") or "").strip()
        ra, rb = str(a.get("ref") or "").strip(), str(b.get("ref") or "").strip()
        same = ("the same built thing %r" % ra) if (ra and ra == rb) else ("the same form %r" % fa) if (fa and fa == fb) else None
        if not same:
            continue
        try:
            import carry_anchors as _ca
            common = _ca.shared(slides[i - 1].get("shot"), slides[i].get("shot"), out_dir)
        except Exception:                                   # noqa: BLE001 — no anchor reader is no anchor claim
            common = None
        tail = ("both registers draw '%s' — the cut can be a `container`" % common[0]) if common else (
            "neither register draws a shared anchor yet (`carry_anchors.py` lists what each draws); a film's own shot "
            "marks one with `data-carry` (runtime/carry.tsx), and the cut can then be a `container`")
        out.append((i, "beats %d and %d realise %s — %s" % (i, i + 1, same, tail)))
    return out
CLOSE = ["LiquidChrome", "HoloFoil", "CinematicTitle", "FlowField", "StarfieldWarp", "NeonTickerWall",
         "KaleidoMandala", "InkBloom", "LiquidMetal", "RainGlass", "SwissEditorial"]
FALLBACK = ["ChatThread", "AuroraFlow", "MaterialHero", "SplitFlap", "ClayStack", "AnalogTape"]

# COLOR-ARC: the ground-luminance of a shot, read from the SINGLE source (remotion/src/runtime/shotLuma.ts) so
# it can never drift from what the renderer measures. A film that flips dark<->light on nearly every beat STROBES
# (each seam is smooth after P2/P3, but the whole-film brightness pulse reads restless) — the assigner uses this
# to break up strobe streaks, and validate warns when a sequence flips too often.
_LUM_RANK = {"dark": 0, "mid": 1, "light": 2}
_LUMA = None


def shot_luma(shot):
    """'dark' | 'mid' | 'light' for a shot (default 'dark'). Parses shotLuma.ts once; empty/degrades safely."""
    global _LUMA
    if _LUMA is None:
        _LUMA = {}
        try:
            import re
            p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "remotion", "src", "runtime", "shotLuma.ts")
            body = open(p, encoding="utf-8").read().split("SHOT_LUMA")[1].split("{", 1)[1].split("};")[0]
            _LUMA = dict(re.findall(r"(\w+):\s*'(dark|mid|light)'", body))
        except Exception:
            _LUMA = {}
    return _LUMA.get(shot, "dark")


def _hard_flip(a, b):
    """True if two grounds are a dark<->light jump (the strobe unit); mid<->anything is a gradient, not a flip."""
    if not a or not b:
        return False
    return abs(_LUM_RANK.get(a, 0) - _LUM_RANK.get(b, 0)) >= 2


def _pick(cands, last_family, used, prefer=None, last_luma=None, soften=False, band=None, motion=None, summit=False):
    """First candidate whose family differs from the previous beat's; prefer unused registers. When `prefer`
    (the chosen template's family letters) is given, BIAS toward those families first — the template EMPHASIZES
    families without ever forcing two adjacent beats into the same one (variety still wins). When `band`
    (the beat's energy band from energy_skeleton.band_for) and the library's measured `motion` are given, a
    register INSIDE the band comes first — the plan's skeleton decides which of the fitting, fresh, varied
    candidates is taken, so a beat declared high is not handed one of the library's stillest registers. When
    `soften` (the previous seam already hard-flipped luminance), a stable TIE-BREAK prefers a candidate that
    does NOT flip again — smoothing the brightness arc WITHOUT overriding fit/family/freshness/energy (they
    pre-order the pool)."""
    if prefer:
        order = {c: i for i, c in enumerate(cands)}
        cands = sorted(cands, key=lambda c: (FAMILY.get(c) not in prefer, order[c]))
    pool = ([c for c in cands if FAMILY.get(c) != last_family and c not in used]
            or [c for c in cands if FAMILY.get(c) != last_family] or list(cands))
    in_band = (lambda c: c in motion and band[0] <= motion[c] < band[1]) if (band and motion) else (lambda c: True)
    flips = (lambda c: _hard_flip(shot_luma(c), last_luma)) if (soften and last_luma is not None) else (lambda c: False)
    # `summit`: this is the PEAK beat, and the film's most kinetic register belongs on it — the liveliest
    # in-band candidate, not the first. Otherwise the summit lands wherever a medium beat happened to draw
    # a lively register, which is what a delivered film measured (energy_skeleton.py, summit-off-peak).
    lively = (lambda c: -motion.get(c, 0.0)) if (summit and motion) else (lambda c: 0.0)
    pool = sorted(pool, key=lambda c: (not in_band(c), lively(c), flips(c)))       # stable: band, summit, non-flips
    return pool[0]


def _on_stage_run(slide):
    """Is this beat declared on a stage run drawn by a stage (references/stage-runs.md)?"""
    try:
        import stage_runs as _sr
        return bool(_sr.run_id(slide)) and slide.get("shot") in set(_sr.stage_names())
    except Exception:                                   # noqa: BLE001 — no stage reader, no run to protect
        return False


def _template_families(template):
    if not template:
        return None
    try:
        import shot_templates
        return shot_templates.TEMPLATES.get(template, {}).get("families")
    except Exception:
        return None


def assign_shots(data, content_plan=None, template=None):
    """Propose a register per scene as MATERIAL (`shot` + `shot_props` (={}) + `shot_fit.material`). VARIES family
    across beats; when `template` (a shot_templates key) is given, biases the selection toward that template's
    families and records it as meta.shot_template. A scene whose route is already decided (a `shot_fit.verdict`
    other than "unjudged") is left exactly as it is; an `ideal`/`form` written before this runs is kept."""
    prefer = _template_families(template)
    # content_plan beat ids are 1-BASED and storyboard scene indices are 0-BASED, so looking a scene up by
    # its own index missed beat 1 entirely and handed every other scene the PREVIOUS beat's plan — its
    # visual_intent, its climax flag, its relation. Silently, and with seven distinct intents in a real
    # plan. Match by id, then by the 1-based offset, then by position, and say which in shot_fit.
    _plan = (content_plan or {}).get("beats", []) or []
    _by_id = {b.get("id"): b for b in _plan if b.get("id") is not None}

    # The offset is decided ONCE for the whole plan, not per scene: scene indices 1..N are themselves
    # valid beat ids, so trying id-then-id+1 per scene picks the wrong beat for every scene but the first.
    _scene_ix = {s.get("index") for s in data.get("slides", [])}
    if _by_id and _scene_ix and set(_by_id) == _scene_ix:
        _offset, _how_matched = 0, "id"
    elif _by_id and _scene_ix and set(_by_id) == {i + 1 for i in _scene_ix if i is not None}:
        _offset, _how_matched = 1, "id = index + 1"
    else:
        _offset, _how_matched = None, "position"

    def _beat_for(scene_index, pos):
        if _offset is not None and (scene_index + _offset) in _by_id:
            return _by_id[scene_index + _offset], _how_matched
        if pos < len(_plan):
            return _plan[pos], "position"
        return {}, "no plan"

    data.setdefault("meta", {})["renderer"] = "remotion"
    if template:
        data["meta"]["shot_template"] = template
    # THE SKELETON FIRST. The plan declares an energy per beat; the library's sweep measures a motion per
    # register. Read both here so the pick below prefers a register in the beat's band — measured on a
    # delivered film, the picker that could not see energy put the plan's climax on a register under the
    # delivery motion floor and four HIGH beats on the library's stillest fifth (energy_skeleton.py).
    try:
        import energy_skeleton as _es
        _motion, _floor, _qc, _kc, _why = _es.load_sweep()
    except Exception:                                # no sweep = no band; the pick is unchanged, never wrong
        _es, _motion, _why = None, None, "energy_skeleton unavailable"
    if _why:
        print("[shot_director] energy skeleton not applied: %s" % _why)
    last_family, used, last_luma, prev_flip = None, set(), None, False
    last_shot, last_form = None, None
    vocab = data["meta"].get("form_vocabulary") if isinstance(data["meta"].get("form_vocabulary"), list) else []
    for pos, s in enumerate(data.get("slides", [])):
        prior = s.get("shot_fit") if isinstance(s.get("shot_fit"), dict) else {}
        # A DECLARED STAGE RUN IS A ROUTE TOO: a beat the director put on a WorldStage/CardStage run is one picture with
        # its neighbours, and proposing a register onto it would split the run (stage_runs.check refuses a mixed run).
        if prior.get("verdict") not in (None, "", "unjudged") and s.get("shot") or _on_stage_run(s):
            # A ROUTED BEAT IS THE DIRECTOR'S. Re-running the skeleton must not turn a built or adapted beat back
            # into a library proposal.
            used.add(s["shot"])
            last_family, last_luma = FAMILY.get(s["shot"]), shot_luma(s["shot"])
            last_shot, last_form = s["shot"], str(prior.get("form") or "").strip()
            continue
        beat, matched_by = _beat_for(s.get("index"), pos)
        intent = beat.get("visual_intent") or "statement"
        _energy = _es.declared(s, beat) if _motion else None
        band = _es.band_for(_energy, _qc, _kc, _floor) if _motion else None
        # THE ARGUMENT'S SHAPE FIRST (REACH above): a built tool for the shape this beat's form argues comes before the
        # keyword lists. Content wins over the direction's family lean and the energy band — energy_skeleton.py then
        # names a mismatch for the director to settle — but never over family variety: a route whose every register is
        # the previous beat's family falls through to the lists, and the match is still recorded in shot_fit.reach.
        reach = match_reach(beat_argument(s, beat, vocab))
        route_regs = []
        for r in reach:
            route_regs += [c for c in r.get("registers") or [] if c not in route_regs]
        fresh = [c for c in route_regs if FAMILY.get(c) != last_family]
        first_route = next((r["key"] for r in reach if set(r.get("registers") or []) & set(fresh)), None)
        _form = str((prior or {}).get("form") or "").strip()
        if fresh:
            shot, how = fresh[0], "reach '%s'" % first_route
        elif last_shot in route_regs and _form and _form == last_form:
            # ONE FORM ACROSS TWO BEATS IS ONE REGISTER: a derivation carried on into the next beat is the same
            # blackboard, and the shot-director's own rule allows a register reused on the same form
            shot = last_shot
            how = "reach '%s', the same form as the beat before" % next(
                r["key"] for r in reach if last_shot in (r.get("registers") or []))
        else:
            if beat.get("climax"):
                cands, how = CLIMAX, "climax list"
            elif beat.get("relation") == "close" or beat.get("hold"):
                cands, how = CLOSE, "close list"
            elif intent in CANDIDATES:
                cands, how = CANDIDATES[intent], "intent '%s'" % intent
            else:
                cands, how = FALLBACK, "FALLBACK (no candidate list for intent '%s')" % intent
            # color-arc: only SOFTEN after a flip (avoid a 2nd consecutive one) — isolated flips (contrast) survive
            shot = _pick(cands, last_family, used, prefer, last_luma, soften=prev_flip, band=band, motion=_motion,
                         summit=(_energy == "peak"))
        s["shot"], s["shot_props"] = shot, s.get("shot_props") or {}
        # RECORD THAT NOBODY JUDGED THIS. The deterministic path matches an intent keyword to a candidate
        # list; it cannot ask whether the register's STRUCTURE carries the beat's argument, which is the
        # only question that can surface "nothing in the library can draw this". Leaving the field absent
        # made "assigned mechanically" indistinguishable from "considered and found to fit", so the one
        # judgement that grows the library could be skipped without a trace.
        s["shot_fit"] = {"verdict": "unjudged",
                         "why": "proposed as MATERIAL by %s%s — not an assignment; no one judged whether this "
                                "register's structure carries the beat's argument. Route it against the ideal: "
                                "adapt, build, or as-is only if it already IS the ideal" %
                                (how, ", reusing a register already in this film" if shot in used else ""),
                         "material": shot, "assigned_by": how, "plan_matched_by": matched_by}
        for k in ("ideal", "form", "composition"):   # the ideal picture comes FIRST and is never overwritten
            if prior.get(k):
                s["shot_fit"][k] = prior[k]
        if reach:
            s["shot_fit"]["reach"] = [_reach_note(r) for r in reach]
        note = timing_note(shot, beat.get("est_seconds") or s.get("duration"))
        if note:
            s["shot_fit"]["timing"] = note
        used.add(shot)
        last_family, last_shot, last_form = FAMILY.get(shot), shot, _form
        lum = shot_luma(shot)
        prev_flip = _hard_flip(lum, last_luma)
        last_luma = lum
    bookends(data, content_plan)
    return data


BOOKEND_MIN_BEATS = 6
_ENERGY_RANK = {"peak": 4, "high": 3, "medium": 2, "low": 1}


def bookends(data, content_plan=None):
    """THE FILM'S FIRST AND LAST BEAT, by POSITION — what the per-beat picker cannot see. A launch or promo film (meta.
    purpose) of BOOKEND_MIN_BEATS or more may open COLD: its first beat proposed as `ColdOpen` flashing its three most
    energetic later beats (the peer library's trailer bumper). Any film that long whose last beat closes may END on a
    `Callback` gathering four of its beats around the closing line. Both are MATERIAL like every proposal here — only
    an unrouted beat is touched, `shot_fit.bookend` says why, and the director keeps or replaces it. Returns the notes."""
    slides = data.get("slides") or []
    meta = data.get("meta") or {}
    notes = []
    if len(slides) < BOOKEND_MIN_BEATS:
        return notes
    plan = (content_plan or {}).get("beats") or []
    energy = [_ENERGY_RANK.get(str((plan[i] if i < len(plan) else {}).get("energy") or s.get("energy") or ""), 2)
              for i, s in enumerate(slides)]
    open_ = lambda s: (s.get("shot_fit") or {}).get("verdict") in (None, "", "unjudged") and not _on_stage_run(s)
    first, last = slides[0], slides[-1]
    # FAMILY VARIETY STILL WINS: a bookend that would sit beside a beat of its own family is offered as a note only
    clash = lambda shot, nb: FAMILY.get(shot) == FAMILY.get(nb.get("shot"))
    if str(meta.get("purpose") or "").lower() in ("launch", "promo") and open_(first) and clash("ColdOpen", slides[1]):
        notes.append("beat 1: a ColdOpen would open this film, but beat 2 is family %s too — re-route beat 2 to "
                     "take it" % FAMILY.get("ColdOpen"))
    elif str(meta.get("purpose") or "").lower() in ("launch", "promo") and open_(first):
        later = sorted(range(1, len(slides) - 1), key=lambda i: (-energy[i], i))[:3]
        beats = sorted(i + 1 for i in later)
        first["shot"], first["shot_props"] = "ColdOpen", dict(first.get("shot_props") or {}, beats=beats)
        if meta.get("title") and "title" not in first["shot_props"]:
            first["shot_props"]["title"] = meta["title"]
        why = ("a %s film opens on itself: beats %s (its most energetic later ones) flash past, then the title — the "
               "trailer bumper. Replace it if the opening line must be read at once" % (meta.get("purpose"), beats))
        first.setdefault("shot_fit", {}).update({"material": "ColdOpen", "bookend": why})
        notes.append("beat 1: " + why)
    rel = str((plan[-1] if len(plan) >= len(slides) else {}).get("relation") or last.get("relation") or "")
    if open_(last) and rel in ("close", "payoff", "") and clash("Callback", slides[-2]):
        notes.append("beat %d: a Callback could close this film, but beat %d is family %s too — re-route it to "
                     "take it" % (len(slides), len(slides) - 1, FAMILY.get("Callback")))
    elif open_(last) and rel in ("close", "payoff", ""):
        pool = [i for i in sorted(range(len(slides) - 1), key=lambda i: (-energy[i], i))
                if slides[i].get("shot") not in ("ColdOpen", "Callback")]
        picked, fams = [], set()
        for i in pool:                                  # four beats that LOOK different: one per family first...
            f = FAMILY.get(slides[i].get("shot"))
            if f not in fams:
                picked.append(i)
                fams.add(f)
            if len(picked) == 4:
                break
        for i in pool:                                  # ...then the liveliest of the rest
            if len(picked) == 4:
                break
            if i not in picked:
                picked.append(i)
        if len(picked) >= 3:
            beats = sorted(i + 1 for i in picked)
            last["shot"], last["shot_props"] = "Callback", dict(last.get("shot_props") or {}, beats=beats)
            why = ("the film ends gathering what it showed: beats %s come back as cards round the closing line — a "
                   "recap you see. Replace it if the close is one image or one sentence alone" % beats)
            last.setdefault("shot_fit", {}).update({"material": "Callback", "bookend": why})
            notes.append("beat %d: %s" % (len(slides), why))
    for n in notes:
        print("[shot_director] bookend — " + n)
    return notes


def reach_report(data, out_dir=None):
    """The lines that tell the director which BUILT capabilities this board's arguments call for: each beat's reach,
    the runs a world camera should travel, the seams a shared element can carry, and the film's cut tempo. Printed by
    main(); a list so a test can read it."""
    slides = data.get("slides", []) or []
    meta = data.get("meta") or {}
    out = []
    rows = []
    for s in slides:
        fit = s.get("shot_fit") if isinstance(s.get("shot_fit"), dict) else {}
        for n in fit.get("reach") or []:
            if isinstance(n, dict):
                rows.append("  #%s %-22s → %s" % (s.get("index"), n.get("route"), n.get("use")))
        if fit.get("timing"):
            rows.append("  #%s timing: %s" % (s.get("index"), fit["timing"]))
    if rows:
        out.append("[shot_director] REACH — the built tools these beats' arguments call for (when/not in shot_fit.reach; "
                   "references/remotion-shot-authoring.md §F):")
        out += rows
    for first, last, stage, moves in stage_run_hints(slides):
        span = ("beat %d" % (first + 1)) if first == last else ("beats %d-%d" % (first + 1, last + 1))
        out.append("[shot_director] %s travel%s ONE world: declare a %s run (`stage: {run: …}`, `world.objects` on beat "
                   "%d, camera.move %s) — references/stage-runs.md; a run moves its own camera, so its beats take no "
                   "`camera` and have no seam between them" % (span, "s" if first == last else "", stage, first + 1,
                                                                 " / ".join(moves)))
    for _i, why in container_hints(slides, out_dir):
        out.append("[shot_director] shared element: %s" % why)
    try:
        import seam_plan as _sp
        tempo, basis = _sp.film_tempo(meta)
        say = {"kinetic": "every unmarked seam becomes a hard `cut`",
               "scored": "half the seams cut hard on the music's beat (never into a low beat or the close)",
               "calm": "the unmarked seams keep their dissolve"}[tempo]
        out.append("[shot_director] cut tempo %s (%s): %s once seam_plan.py runs — `meta.cuts` names it outright"
                   % (tempo, basis, say))
    except Exception as e:                                   # noqa: BLE001 — the tempo line is advice, never a crash
        out.append("[shot_director] cut tempo not read: %s" % e)
    return out


def main():
    ap = argparse.ArgumentParser(description="Propose a library register per beat as MATERIAL to adapt or borrow "
                                             "from (a family-varied skeleton, not an assignment). Write each "
                                             "beat's shot_fit.ideal first; route every beat after.")
    ap.add_argument("out_dir")
    ap.add_argument("--template", default=None,
                    help="a shot_templates key (product-demo/kinetic-editorial/cinematic-craft/data-story/"
                         "retro-playful/terminal-technical) to bias family selection toward that direction")
    a = ap.parse_args()
    sb_path = os.path.join(a.out_dir, "storyboard.json")
    cp_path = os.path.join(a.out_dir, "content_plan.json")
    data = json.load(open(sb_path, encoding="utf-8"))
    cp = json.load(open(cp_path, encoding="utf-8")) if os.path.isfile(cp_path) else None
    assign_shots(data, cp, template=a.template)

    # THE FILM'S CUTS AND CAMERA, on this path too. This fallback used to emit only `shot` and
    # `shot_props`, so a film made without the LLM shot-director got a register per beat and nothing else:
    # 34 identical cuts and a camera that never moved. Those capabilities were fully built, tested and
    # documented and reached no film, which is indistinguishable from never having written them. The
    # planner derives both from the `relation` each beat already declares, skips anything already
    # authored, and is deterministic — so running it here changes nothing for a board that has its own.
    # ...BUT NOT ON MATERIAL. In the design-first flow this run only PROPOSES a register per beat (verdict
    # `unjudged`); a camera written now is planned for a register the beat will probably not keep, and because it
    # is then on the board, seam_plan treats it as AUTHORED and skips the beat (the GPS test film's beat 1). The cut
    # and camera plan waits for the routes: SKILL.md 3.6 ③ runs seam_plan.py after them.
    _proposed = [sl.get("index") for sl in data.get("slides", [])
                 if isinstance(sl.get("shot_fit"), dict) and sl["shot_fit"].get("verdict") == "unjudged"]
    try:
        if _proposed:
            raise RuntimeError("%d beat(s) still carry proposed material (verdict unjudged) — the cuts and camera are "
                               "planned by `python3 scripts/seam_plan.py <out_dir>` once every beat is routed"
                               % len(_proposed))
        import seam_plan
        # THE FILM'S OWN WORKSHOP REACHES THE PLAN HERE TOO. `seam_plan.plan`/`plan_camera` read a workshop
        # shot's declared ground and a workshop object's declared provenance (scripts/workshop.py) from
        # module state `install_workshop` sets — calling them without it judges a workshop beat's seam on no
        # ground at all, and never gives the push camera a workshop object's own PROVENANCE. `install_workshop`
        # is the one door this entry point and `seam_plan.main` both go through; restored in `finally` so it
        # never outlives this call.
        seam_plan.install_workshop(a.out_dir)
        try:
            marks = seam_plan.plan(data.get("slides", []), (data.get("meta") or {}).get("design_dna"))
            cams = seam_plan.plan_camera(data.get("slides", []))
            for i, m in marks.items():
                sl = data["slides"][i]
                if not (sl.get("transition_in") or sl.get("transition_style")):
                    sl["transition_in"] = {"type": m["type"]}
            for i, c in cams.items():
                sl = data["slides"][i]
                if not sl.get("camera"):
                    sl["camera"] = ({"move": c["move"]} if seam_plan.CAMERA_AMOUNT is None
                                    else {"move": c["move"], "amount": seam_plan.CAMERA_AMOUNT})
            print("[shot_director] %d marked seam(s), %d moving beat(s)" % (len(marks), len(cams)))
        finally:
            seam_plan.clear_workshop()
    except Exception as e:                       # a board with no `relation` is a legitimate film, not a crash
        print("[shot_director] seam/camera plan skipped: %s" % e)

    json.dump(data, open(sb_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    seq = [(s.get("index"), s.get("shot"), FAMILY.get(s.get("shot"))) for s in data.get("slides", [])]
    print("[shot_director] proposed MATERIAL for %d scenes (family-varied) — not an assignment:" % len(seq))
    for i, shot, fam in seq:
        print("  #%s -> %s [%s]" % (i, shot, fam))
    no_ideal = [str(s.get("index")) for s in data.get("slides", [])
                if not ((s.get("shot_fit") or {}).get("ideal") if isinstance(s.get("shot_fit"), dict) else None)]
    if no_ideal:
        print("[shot_director] WARN %d beat(s) have no shot_fit.ideal (%s) — the ideal picture comes BEFORE this "
              "skeleton (agents/shot-director.md Step 0.55); a register proposed without one is what the "
              "catalogue would draw, not what the beat needs" % (len(no_ideal), ", ".join(no_ideal[:12])))
    # THE FILM'S OWN MATERIAL COMES FIRST. The proposals above are matched on an intent KEYWORD and never read the
    # ideal — on the compound-interest test, "the passbook closes on its cloth cover" drew LiquidChrome and "the
    # 1,000 slides down into year two" drew CommandSummon. Listed alone they anchor the beat on a template; the
    # film usually already holds better material (the contest's winning hero, its kit), so it is named here first.
    try:
        import workshop as _ws
        own = sorted(_ws.shot_names(a.out_dir)) + sorted(_ws.object_names(a.out_dir))
    except Exception:                                # noqa: BLE001 — no workshop is simply no own material yet
        own = []
    if own:
        print("[shot_director] this film's OWN material, the first thing to compose beats from: %s" % ", ".join(own))
    for line in reach_report(data, a.out_dir):
        print(line)
    print("[shot_director] the proposals above are chosen by a keyword — the argument's shape (REACH) or the intent — "
          "not by your ideal: read them as donors of technique. The floor is HALF the non-exempt beats BUILT (a "
          "workshop shot, or the film's own object held in a frame's slot); adapting a register does not count toward it.")
    print("[shot_director] NEXT: route every beat against its ideal — build (scripts/workshop.py; compose from the "
          "film's own material), adapt (shot_adaptation.changes + a structure prop changed), or as-is with "
          "shot_fit.shares — then python3 scripts/validate.py %s" % a.out_dir)


if __name__ == "__main__":
    main()
