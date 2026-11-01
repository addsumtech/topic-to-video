"""A film's own shot that draws a phone, tablet or laptop BY HAND (scripts/device_fidelity_qa.py hand_drawn_device).

Measured 2026-11-01 on a Grok Bot film: a workshop shot drew a phone as a black rounded outline with an "island"
(no buttons, wrong proportions) and the user said the phones were not refined. The existing check only fired when
a shot showed a CAPTURE of a known device's pixel size; this phone drew its own screen, so nothing was said. A device
named in the code is either the kit's (runtime/device, any import depth) or a build whose fidelity record cites a real
model's published numbers (deviceSpec.json) — or the source says why it is not a device.
"""
import json
import os

import device_fidelity_qa as fq


def _film(tmp_path, src, kit=None, fidelity=None):
    ws = tmp_path / "workshop" / "shots"
    ws.mkdir(parents=True)
    (ws / "Hands.tsx").write_text(src)
    if kit:
        (ws / "kit").mkdir()
        (ws / "kit" / "Surface.tsx").write_text(kit)
    entry = {"id": "Hands", "kind": "shot", "beats": [1]}
    if fidelity:
        entry["fidelity"] = fidelity
    board = {"meta": {"renderer": "remotion", "build_list": [entry]}, "slides": [{"index": 1, "shot": "Hands",
                                                                                 "shot_props": {}}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board))
    return board


DRAWN = "import React from 'react';\n// the phone, drawn: a black rounded body and the phone's island\n" \
        "export const Hands = () => <div style={{borderRadius: 60, border: '14px solid #111'}} />;\n"


def test_a_hand_drawn_phone_is_named(tmp_path):
    b = _film(tmp_path, DRAWN)
    msg = fq.hand_drawn_device(b["slides"][0], str(tmp_path), b["meta"]["build_list"])
    assert msg and "phone" in msg and "runtime/device" in msg, msg


def test_the_kit_at_any_depth_a_real_model_record_or_a_stated_reason_clears_it(tmp_path):
    via_kit = DRAWN.replace("import React from 'react';", "import React from 'react';\nimport {P} from './kit/Surface';")
    b = _film(tmp_path / "a", via_kit, kit="import {Device} from '@runtime/device';\nexport const P = Device;\n")
    assert fq.hand_drawn_device(b["slides"][0], str(tmp_path / "a"), b["meta"]["build_list"]) is None
    b = _film(tmp_path / "b", DRAWN.replace("phone", "laptop"),
              fidelity={"subject": "a MacBook Pro 14", "proportions": {"source": "deviceSpec models.macbook-pro-14"}})
    assert fq.hand_drawn_device(b["slides"][0], str(tmp_path / "b"), b["meta"]["build_list"]) is None
    b = _film(tmp_path / "c", DRAWN + "// @not-a-device: a phone-shaped speech bubble, no device is meant\n")
    assert fq.hand_drawn_device(b["slides"][0], str(tmp_path / "c"), b["meta"]["build_list"]) is None
    b = _film(tmp_path / "d", "export const Hands = () => <div>a cloud computer</div>;\n")
    assert fq.hand_drawn_device(b["slides"][0], str(tmp_path / "d"), b["meta"]["build_list"]) is None
