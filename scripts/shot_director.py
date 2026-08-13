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

# register -> family letter (A Product-UI, B Camera/space, C Kinetic type/title, D Data/technical, E 3D,
# F Fluid/generative, G Illustrated/craft, H Comparison, I Mechanical/physical). Mirrors LIBRARY.md.
FAMILY = {
    "CollaborativeCursors": "A", "CommandSummon": "A", "TemporalAccelerate": "A", "VelocitySnap": "A",
    "CursorStory": "A", "ScreenBubble": "A", "AnswerStream": "A", "ChatThread": "A", "BlockAssembly": "A",
    "CodeCompose": "A", "LiquidGlass": "A",
    "InfiniteCanvas": "B", "TimelineTravel": "B", "MapRoutes": "B", "ExplodedSchematic": "B",
    "KineticManifesto": "C", "FocalIsolation": "C", "SwissEditorial": "C", "BrutalistType": "C",
    "LiquidChrome": "C", "HoloFoil": "C", "CinematicTitle": "C", "BokehPull": "C", "NeonGrid": "C",
    "AnalogTape": "C", "AsciiField": "C",
    "ChartLive": "D", "BlueprintGrid": "D", "KnowledgeGraph": "D", "WireGlobe": "D", "DataOrrery": "D",
    "MaterialHero": "E",
    "AuroraFlow": "F", "LiquidMorph": "F", "LiquidFill": "F", "ParticleForm": "F", "VoiceSignal": "F",
    "RadialBurst": "F", "LightTrails": "F",
    "IsometricAssembly": "G", "HandDrawn": "G", "CartoonPop": "G", "HalftonePop": "G", "ClayStack": "G",
    "PaperCutout": "G", "SpotlightStage": "G", "PixelBuild": "G",
    "BeforeAfterSlider": "H",
    "SplitFlap": "I", "PhysicsStack": "I",
}
# candidates by visual_intent (ordered; the assigner picks the first whose family != the previous beat's)
CANDIDATES = {
    # mostly family C (kinetic type/title), plus cross-family options (E/F/I/G) so two ADJACENT statement beats
    # can still land in different families instead of both being C.
    "statement": ["CinematicTitle", "FocalIsolation", "KineticManifesto", "SwissEditorial", "BrutalistType",
                  "LiquidChrome", "NeonGrid", "HoloFoil", "MaterialHero", "AuroraFlow", "SplitFlap", "PixelBuild"],
    "sequence": ["ExplodedSchematic", "TimelineTravel", "CommandSummon", "CodeCompose"],
    "structure": ["CollaborativeCursors", "KnowledgeGraph", "MapRoutes", "DataOrrery", "WireGlobe",
                  "BlueprintGrid", "IsometricAssembly"],
    # mostly family A; cross-family options (I/G) so two ADJACENT list beats don't both land in A.
    "list": ["BlockAssembly", "TemporalAccelerate", "CursorStory", "AnswerStream", "SplitFlap", "PhysicsStack", "HandDrawn"],
    "metric": ["ChartLive", "PhysicsStack", "BlueprintGrid", "BeforeAfterSlider"],
}
CLIMAX = ["ParticleForm", "RadialBurst", "LightTrails", "SpotlightStage", "LiquidFill"]
CLOSE = ["LiquidChrome", "HoloFoil", "CinematicTitle", "SwissEditorial"]
FALLBACK = ["ChatThread", "AuroraFlow", "MaterialHero", "SplitFlap", "ClayStack", "AnalogTape"]


def _pick(cands, last_family, used):
    """First candidate whose family differs from the previous beat's; prefer unused registers."""
    fresh = [c for c in cands if FAMILY.get(c) != last_family and c not in used]
    if fresh:
        return fresh[0]
    diff = [c for c in cands if FAMILY.get(c) != last_family]
    return diff[0] if diff else cands[0]


def assign_shots(data, content_plan=None):
    """Fill each scene's `shot` + `shot_props` (={}). Returns the modified data. VARIES family across beats."""
    beats = {b.get("id"): b for b in (content_plan or {}).get("beats", [])}
    data.setdefault("meta", {})["renderer"] = "remotion"
    last_family, used = None, set()
    for s in data.get("slides", []):
        beat = beats.get(s.get("index"), {})
        intent = beat.get("visual_intent") or "statement"
        if beat.get("climax"):
            cands = CLIMAX
        elif beat.get("relation") == "close" or beat.get("hold"):
            cands = CLOSE
        else:
            cands = CANDIDATES.get(intent, FALLBACK)
        shot = _pick(cands, last_family, used)
        s["shot"], s["shot_props"] = shot, s.get("shot_props") or {}
        used.add(shot)
        last_family = FAMILY.get(shot)
    return data


def main():
    ap = argparse.ArgumentParser(description="Assign remotion shots to storyboard scenes (deterministic fallback).")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    sb_path = os.path.join(a.out_dir, "storyboard.json")
    cp_path = os.path.join(a.out_dir, "content_plan.json")
    data = json.load(open(sb_path, encoding="utf-8"))
    cp = json.load(open(cp_path, encoding="utf-8")) if os.path.isfile(cp_path) else None
    assign_shots(data, cp)
    json.dump(data, open(sb_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    seq = [(s.get("index"), s.get("shot"), FAMILY.get(s.get("shot"))) for s in data.get("slides", [])]
    print("[shot_director] assigned %d scenes (family-varied):" % len(seq))
    for i, shot, fam in seq:
        print("  #%s -> %s [%s]" % (i, shot, fam))


if __name__ == "__main__":
    main()
