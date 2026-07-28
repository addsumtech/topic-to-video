#!/usr/bin/env python3
"""Tests for shot-based scene rendering (P2)."""
import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import render_remotion as rr
import storyboard as sb
import theme as th


def test_shot_based_scene_detection():
    """Shot-based scenes (stage + shot) are not unsupported even without an image."""
    data = {
        "meta": {"fps": 30},
        "slides": [
            {
                "index": 0,
                "type": "title",
                "duration": 2.0,
                "audio": "test.mp3",
                "props": {
                    "stage": {
                        "elements": [
                            {"id": "card", "kind": "panel", "position": [0, 0, -500], "title": "Test"}
                        ]
                    },
                    "shot": {"type": "MEDIUM", "motion": "PUSH_IN", "target": "card", "duration": 60}
                }
            }
        ]
    }
    # Should NOT be flagged as unsupported (no image, but has stage+shot)
    bad = rr.unsupported_scenes(data)
    assert bad == [], f"shot-based scene should not be unsupported, got {bad}"


def test_build_props_with_shot():
    """build_props passes through stage + shot for shot-based scenes."""
    with tempfile.TemporaryDirectory() as tmp:
        # Minimal storyboard with shot-based scene
        data = {
            "meta": {"fps": 30},
            "slides": [
                {
                    "index": 0,
                    "type": "title",
                    "duration": 3.0,
                    "audio": "test.mp3",
                    "narration": "Test shot",
                    "stage": {
                        "elements": [
                            {"id": "panel-1", "kind": "panel", "position": [0, 0, -500],
                             "title": "Shot Test", "kicker": "P2", "align": "center"},
                            {"id": "grid-bg", "kind": "grid", "position": [0, 0, -800]}
                        ],
                        "perspective": 1400
                    },
                    "shot": {
                        "type": "MEDIUM",
                        "motion": "PUSH_IN",
                        "target": "panel-1",
                        "easing": "out"
                    }
                }
            ]
        }

        props = rr.build_props(data, tmp)

        assert len(props["scenes"]) == 1
        scene = props["scenes"][0]

        # Verify stage + shot are present
        assert scene["stage"] is not None, "stage should be present"
        assert scene["shot"] is not None, "shot should be present"

        # Verify stage structure
        stage = scene["stage"]
        assert isinstance(stage["elements"], list)
        assert len(stage["elements"]) == 2
        assert stage["elements"][0]["id"] == "panel-1"
        assert stage["elements"][0]["kind"] == "panel"
        assert stage["elements"][0]["position"] == [0, 0, -500]
        assert stage["perspective"] == 1400

        # Verify shot structure
        shot = scene["shot"]
        assert shot["type"] == "MEDIUM"
        assert shot["motion"] == "PUSH_IN"
        assert shot["target"] == "panel-1"
        assert shot["easing"] == "out"
        # shot.duration should be auto-filled from scene durationInFrames
        assert shot["duration"] == 90  # 3.0s * 30fps


def test_shot_motion_patterns():
    """Motion pattern names are case-insensitive and accept various formats."""
    patterns = [
        ("PUSH_IN", "PUSH_IN"),
        ("push-in", "PUSH_IN"),
        ("PushIn", "PUSH_IN"),
        ("pull out", "PULL_OUT"),
        ("PAN_RIGHT", "PAN_RIGHT"),
        ("pan-left", "PAN_LEFT"),
        ("tilt_up", "TILT_UP"),
        ("ORBIT-RIGHT", "ORBIT_RIGHT"),
        ("rack focus", "RACK_FOCUS"),
        ("static", "STATIC"),
        ("invalid", "STATIC"),  # unknown falls back to STATIC
        (None, "STATIC"),
    ]

    # Import from TypeScript would require Node; test Python side can pass through
    for input_name, expected in patterns:
        # Python side just passes the string; TypeScript normalizes it
        # For now, verify Python doesn't reject any format
        with tempfile.TemporaryDirectory() as tmp:
            data = {
                "meta": {"fps": 30},
                "slides": [{
                    "index": 0,
                    "type": "title",
                    "duration": 2.0,
                    "audio": "test.mp3",
                    "stage": {"elements": [{"id": "el", "kind": "panel", "position": [0, 0, -500]}]},
                    "shot": {"type": "MEDIUM", "motion": input_name, "target": "el"}
                }]
            }
            props = rr.build_props(data, tmp)
            assert props["scenes"][0]["shot"]["motion"] == input_name


def test_legacy_layers_still_work():
    """Legacy scenes with layers (no stage/shot) continue to work unchanged."""
    with tempfile.TemporaryDirectory() as tmp:
        data = {
            "meta": {"fps": 30},
            "slides": [{
                "index": 0,
                "type": "slide",
                "duration": 2.0,
                "audio": "test.mp3",
                "layers": [
                    {"kind": "fill"},
                    {"kind": "panel", "title": "Legacy", "z": -500}
                ],
                "lens": [
                    {"atFrame": 0, "dolly": 0, "pitch": 0, "yaw": 0, "zoom": 1.0},
                    {"atFrame": 60, "dolly": 150, "pitch": 0, "yaw": 0, "zoom": 1.1, "easing": "out"}
                ]
            }]
        }

        props = rr.build_props(data, tmp)
        scene = props["scenes"][0]

        # Legacy fields should be present, shot-based fields absent
        assert scene["layers"] is not None
        assert scene["lens"] is not None
        assert scene["stage"] is None
        assert scene["shot"] is None


def test_shot_validation_errors():
    """Shot-based scenes with invalid stage/shot raise clear errors."""
    with tempfile.TemporaryDirectory() as tmp:
        # stage must be a dict
        data = {
            "meta": {"fps": 30},
            "slides": [{
                "index": 0,
                "duration": 2.0,
                "audio": "test.mp3",
                "stage": "not-a-dict",
                "shot": {"type": "MEDIUM"}
            }]
        }
        try:
            rr.build_props(data, tmp)
            assert False, "should have raised RuntimeError for non-dict stage"
        except RuntimeError as e:
            assert "stage` must be an object" in str(e)

        # shot must be a dict
        data["slides"][0]["stage"] = {"elements": []}
        data["slides"][0]["shot"] = "not-a-dict"
        try:
            rr.build_props(data, tmp)
            assert False, "should have raised RuntimeError for non-dict shot"
        except RuntimeError as e:
            assert "shot` must be an object" in str(e)

        # stage.elements must be a list
        data["slides"][0]["stage"] = {"elements": "not-a-list"}
        data["slides"][0]["shot"] = {"type": "MEDIUM"}
        try:
            rr.build_props(data, tmp)
            assert False, "should have raised RuntimeError for non-list elements"
        except RuntimeError as e:
            assert "stage.elements` must be a list" in str(e)


if __name__ == "__main__":
    test_shot_based_scene_detection()
    print("✓ shot-based scenes not flagged as unsupported")

    test_build_props_with_shot()
    print("✓ build_props passes through stage + shot")

    test_shot_motion_patterns()
    print("✓ motion patterns pass through Python side")

    test_legacy_layers_still_work()
    print("✓ legacy layers/lens scenes unchanged")

    test_shot_validation_errors()
    print("✓ shot validation errors are clear")

    print("\nAll P2 tests passed!")
