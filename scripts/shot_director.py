#!/usr/bin/env python3
"""shot_director — assign a remotion bespoke SHOT (register) + shot_props to every storyboard scene.

The PRIMARY path is the `agents/shot-director.md` LLM agent (it writes good topic copy into shot_props and
reasons about the "use when" per beat). This module is the DETERMINISTIC fallback / test scaffold: given the
content_plan beats' `visual_intent`/`stage`/`climax`, it picks a register per beat while VARYING THE FAMILY
(never two adjacent beats from the same family) so a film never reads as one look. It fills shot_props={} (the
register's neutral defaults) — a real topic film should run the agent to get faithful topic copy + sourced
numbers. See remotion/LIBRARY.md for the catalogue.
"""
import argparse, json, os, sys

# register -> family letter. The family set is OPEN-ENDED (not fixed at 9): add a NEW letter when a bold new
# design language doesn't fit an existing bucket — the variety rule only cares that adjacent beats differ, so
# new families cost nothing. Current: A Product-UI · B Camera/space · C Kinetic type/title · D Data/technical ·
# E 3D/spatial · F Fluid/liquid/light (physical-feeling liquids & light) · G Illustrated/craft · H Comparison ·
# I Mechanical/physical · (J RETIRED — folded into P; letter free for a future language) ·
# K Generative/computed-fields (algorithmic pattern fields) · L Editorial/print · M Glitch/digital-decay ·
# N Isometric · O Urban/signage · P Dimensional/experimental type (type as living/physical material:
# variable-axis morph, inflated, elastic) · Q Anti-design/maximalist · R AI/neural · S Scientific/molecular ·
# T Circuit/hardware ·
# U Audio/music · V Cosmic/space · W Organic/botanical · X Weather/atmosphere · Y Fire/energy · Z Textile/fabric.
# Mirrors LIBRARY.md. (A–Z full; open AA+ if needed.) Boundary: F=physical liquids/light; K=computed algorithmic
# fields — so a "generative" beat is never ambiguous. Post-audit (2026-08-15): VoiceSignal F→U (audio waveform),
# IsometricAssembly G→N (all iso shots together), VariableTypeMorph J→P (J retired, one-shot subset of P).
FAMILY = {
    "GazetteerEntry": "JA",
    "StatedBy": "JA",
    "ProfileGrowth": "J",
    "PhotoPlate": "H",
    "TechnicalPlate": "J",
    "Inscription": "JA",
    "MuseumLabel": "JA",
    "TallyLedger": "JA",
    "PlanPalimpsest": "J",
    "StrataColumn": "J",
    "MapPlate": "J",
    "CollaborativeCursors": "A", "CommandSummon": "A", "TemporalAccelerate": "A", "VelocitySnap": "A",
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
    "Escalation": "D",
    "ShorteningHold": "C",
    "BreaksWhenAsked": "C",
    "HeldInstant": "D",
    "CraneUp": "B",
    "NearTheLine": "R",
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
    "MorphForms": "E", "KSpaceToImage": "E", "MagnetizationTip": "E",
    "InducedFID": "U", "GFactorNoise": "M", "UndersampledKspace": "D", "ScanReconstruct": "G", "RealVersus": "H", "SpinningProton": "S", "PhaseEncodeStep": "D", "MRIPipeline": "B", "FrequencyEncode": "U", "CompressedSensingEq": "L", "KSpaceReal": "G", "SpeedLimit": "D", "LarmorPrecession": "S", "Aliasing": "M", "DiffusionDenoise": "F", "SpinsAlign": "M", "GradientTilt": "U", "KSpaceAnatomy": "H", "TensionScale": "H", "PlatformSurfaces": "A", "OpenQuestions": "C",
    "AuroraFlow": "F", "LiquidMorph": "F", "LiquidFill": "F", "ParticleForm": "F",
    "RadialBurst": "F", "LightTrails": "F", "MetaballMerge": "F", "InkBloom": "F", "LiquidMetal": "F",
    "HandDrawn": "G", "CartoonPop": "G", "HalftonePop": "G", "ClayStack": "G",
    "PaperCutout": "G", "SpotlightStage": "G", "PixelBuild": "G", "RisoPrint": "G", "ComicPanels": "G",
    "BeforeAfterSlider": "H", "QuadSplit": "H", "PositioningMatrix": "H", "VersusSplit": "H",
    "SplitFlap": "I", "PhysicsStack": "I", "GearTrain": "I", "ConveyorBelt": "I",
    "SameStuffChanged": "I",
    "WorksThrough": "I",
    "HardBarrier": "I",
    "SectionRoute": "I",
    "FlowField": "K", "LowPolyForm": "K", "KaleidoMandala": "K", "RidgeField": "K", "GameOfLife": "K",
    "MagazineSpread": "L", "PaperSlot": "L", "PortRail": "B", "RansomZine": "L",
    "EdStat": "L", "EdTimeline": "L", "EdCompare": "L",   # editorial-native family (Ed*) — grouped like Term* above
    "GlitchDatamosh": "M", "CodeRain": "M",
    "IsoWorld": "N", "VoxelBuild": "N", "IsometricAssembly": "N",
    "PlaneStack": "N",
    "NeonTickerWall": "O",
    "VariableTypeMorph": "P", "InflateType": "P", "ElasticType": "P",
    "AntiDesignChaos": "Q",
    "NeuralField": "R",
    "DNAHelix": "S", "AtomOrbital": "S", "MoleculeBallStick": "S",
    "CircuitTrace": "T",
    "SpectrumPulse": "U", "VoiceSignal": "U",
    "StarfieldWarp": "V",
    "FractalTree": "W",
    "RainGlass": "X",
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
    "statement": ["CinematicTitle", "VariableTypeMorph", "FocalIsolation", "KineticManifesto", "SwissEditorial",
                  "BrutalistType", "LiquidChrome", "NeonGrid", "HoloFoil", "RisoPrint", "MagazineSpread",
                  "RansomZine", "MaterialHero", "FractureIn", "HudReticle", "FlowField", "LowPolyForm",
                  "GlitchDatamosh", "MorphForms", "NeonTickerWall", "MetaballMerge", "InflateType", "ElasticType",
                  "AntiDesignChaos", "DNAHelix", "KaleidoMandala", "InkBloom", "SpectrumPulse", "StarfieldWarp",
                  "RidgeField", "CodeRain", "FractalTree", "RainGlass", "AtomOrbital", "LiquidMetal",
                  "EmberFlame", "ClothWave", "GameOfLife", "MoleculeBallStick", "TerrainFly",
                  "AuroraFlow", "SplitFlap", "PixelBuild"],
    "sequence": ["ExplodedSchematic", "TimelineTravel", "CubeRotate", "CommandSummon", "GearTrain", "ConveyorBelt",
                 "IsoWorld", "ComicPanels", "CircuitTrace", "CodeCompose"],
    "structure": ["CollaborativeCursors", "KnowledgeGraph", "CrashZoom", "MapRoutes", "DataOrrery", "WireGlobe",
                  "BlueprintGrid", "CubeRotate", "BentoReveal", "IsoWorld", "NeuralField", "CircuitTrace", "DNAHelix",
                  "PositioningMatrix", "DataMonolith", "VoxelBuild", "CardStack3D", "IsometricAssembly"],
    # mostly family A; cross-family options (I/G/E) so two ADJACENT list beats don't both land in A.
    "list": ["BlockAssembly", "TemporalAccelerate", "CursorStory", "AnswerStream", "SplitFlap", "CardStack3D", "PhysicsStack", "HandDrawn"],
    "metric": ["OdometerRoll", "ChartLive", "ChartRace", "GaugeCluster", "DataMonolith", "PhysicsStack", "BlueprintGrid", "BeforeAfterSlider"],
    # contrast/before-after — cross-family so two adjacent contrast beats differ (H comparison + I + E + C).
    "contrast": ["BeforeAfterSlider", "VersusSplit", "QuadSplit", "SharedBlindspot", "PositioningMatrix", "CardFlip3D", "SplitFlap"],
}
CLIMAX = ["ParticleForm", "RadialBurst", "FractureIn", "MorphForms", "SpectrumPulse", "EmberFlame", "LightTrails", "SpotlightStage", "LiquidFill"]
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


def _template_families(template):
    if not template:
        return None
    try:
        import shot_templates
        return shot_templates.TEMPLATES.get(template, {}).get("families")
    except Exception:
        return None


def assign_shots(data, content_plan=None, template=None):
    """Fill each scene's `shot` + `shot_props` (={}). VARIES family across beats; when `template` (a
    shot_templates key) is given, biases the register selection toward that template's families and records
    it as meta.shot_template."""
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
    for pos, s in enumerate(data.get("slides", [])):
        beat, matched_by = _beat_for(s.get("index"), pos)
        intent = beat.get("visual_intent") or "statement"
        _energy = _es.declared(s, beat) if _motion else None
        band = _es.band_for(_energy, _qc, _kc, _floor) if _motion else None
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
                         "why": "assigned deterministically by %s%s — no one judged whether this "
                                "register's structure carries the beat's argument" %
                                (how, ", reusing a register already in this film" if shot in used else ""),
                         "assigned_by": how, "plan_matched_by": matched_by}
        used.add(shot)
        last_family = FAMILY.get(shot)
        lum = shot_luma(shot)
        prev_flip = _hard_flip(lum, last_luma)
        last_luma = lum
    return data


def main():
    ap = argparse.ArgumentParser(description="Assign remotion shots to storyboard scenes (deterministic fallback).")
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
    try:
        import seam_plan
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
    except Exception as e:                       # a board with no `relation` is a legitimate film, not a crash
        print("[shot_director] seam/camera plan skipped: %s" % e)

    json.dump(data, open(sb_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    seq = [(s.get("index"), s.get("shot"), FAMILY.get(s.get("shot"))) for s in data.get("slides", [])]
    print("[shot_director] assigned %d scenes (family-varied):" % len(seq))
    for i, shot, fam in seq:
        print("  #%s -> %s [%s]" % (i, shot, fam))


if __name__ == "__main__":
    main()
