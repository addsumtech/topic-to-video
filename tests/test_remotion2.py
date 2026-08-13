"""Backstop for the remotion2 bespoke-shot tier (phase-3 integration): the shot registry stays in sync with the
library, the shot-director varies families, and validate.py enforces the shot contract."""
import os, sys, json, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import validate as v
import shot_director as sd
import render_remotion as rr

_SHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "remotion2", "src", "shots")
_SHOT_IDS = {f[:-4] for f in os.listdir(_SHOTS_DIR) if f.endswith(".tsx")}


def _deck(n=6):
    """A minimal valid remotion2 storyboard with n scenes, each with a real shot + audio/duration."""
    shots = ["CinematicTitle", "ExplodedSchematic", "CollaborativeCursors", "KnowledgeGraph", "MapRoutes", "LiquidChrome"]
    return {"meta": {"renderer": "remotion2"},
            "slides": [{"index": i + 1, "shot": shots[i % len(shots)], "shot_props": {},
                        "audio": f"audio/{i+1:02d}.mp3", "duration": 8.0, "narration": "A sentence."} for i in range(n)]}


def test_registry_in_sync_with_shot_files():
    # every shot file is a valid id, and there are 50 of them (the whole library)
    assert len(_SHOT_IDS) == 50, _SHOT_IDS
    assert rr._remotion2_shot_ids() == _SHOT_IDS
    # the FAMILY map covers every shot (shot_director can place any of them)
    missing = _SHOT_IDS - set(sd.FAMILY)
    assert not missing, "shots missing from shot_director.FAMILY: %s" % missing


def test_valid_deck_passes():
    r = v.evaluate(_deck(6), "/tmp")
    assert r["ok"], r["errors"]
    assert r["scenes"] == 6


def test_missing_shot_errors():
    d = _deck(3)
    d["slides"][0].pop("shot")            # a missing shot is a STRUCTURAL error (sb.validate, caught early)
    r = v.evaluate(d, "/tmp")
    assert not r["ok"]
    assert any("shot" in e for e in r["errors"])


def test_unknown_shot_errors():
    d = _deck(3)
    d["slides"][1]["shot"] = "NotAShot"   # a present-but-invalid id is caught by _check_remotion2
    r = v.evaluate(d, "/tmp")
    assert not r["ok"]
    assert any("unknown shot" in e for e in r["errors"])


def test_number_bearing_shot_warns_on_demo_default():
    d = _deck(2)
    d["slides"][0]["shot"] = "ChartLive"      # a number-bearing register...
    d["slides"][0]["shot_props"] = {}         # ...left on its demo number
    r = v.evaluate(d, "/tmp")
    assert any("SOURCED figure" in w for w in r["warnings"])
    # passing the sourced figure silences it
    d["slides"][0]["shot_props"] = {"endVal": 68, "unit": "×", "label": "surge"}
    r2 = v.evaluate(d, "/tmp")
    assert not any("SOURCED figure" in w for w in r2["warnings"])


def test_shot_director_varies_family():
    cp = {"beats": [{"id": i + 1, "visual_intent": vi} for i, vi in
                    enumerate(["statement", "statement", "structure", "list", "metric", "statement",
                               "sequence", "structure", "statement", "structure"])]}
    data = {"meta": {}, "slides": [{"index": i + 1} for i in range(10)]}
    sd.assign_shots(data, cp)
    fams = [sd.FAMILY[s["shot"]] for s in data["slides"]]
    adj = sum(1 for a, b in zip(fams, fams[1:]) if a == b)
    assert adj == 0, "adjacent same-family repeats: %s" % list(zip([s["shot"] for s in data["slides"]], fams))
    assert data["meta"]["renderer"] == "remotion2"
    assert all(s["shot"] in _SHOT_IDS for s in data["slides"])
