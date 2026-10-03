#!/usr/bin/env python3
"""Render the six object examples of references/object-authoring.md into references/object-examples/<Name>.png —
each on ObjectStage (ComposeScreen on DeviceHero's screen), at half size, at ITS OWN host's settled frame. The doc
embeds what this writes; re-run it after changing an example.

    python3 scripts/object_examples.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import render_remotion as rr  # noqa: E402
import workshop as ws  # noqa: E402

SKILL = os.path.dirname(_HERE)
EX = os.path.join(SKILL, "references", "object-examples")
SHOTS = {  # name: (host, props) — every word on the frame comes from these props
    "PuckInSection": ("ObjectStage", {"object": {"id": "PuckInSection", "props": {"packed": 0.85}},
                                      "title": "压实的粉饼", "note": "越密，水越难穿过",
                                      "labels": [{"text": "粉饼", "x": 0.5, "y": 0.68}, {"text": "热水", "x": 0.3, "y": 0.1}]}),
    "StrataOverTime": ("ObjectStage", {"object": {"id": "StrataOverTime", "props": {"layers": [3, 2, 4, 1.5]}},
                                       "title": "一条街的四个年代",
                                       "labels": [{"text": "1900", "x": 0.5, "y": 0.9}, {"text": "今天", "x": 0.5, "y": 0.06}]}),
    "ComposeScreen": ("DeviceHero", {"device": "phone", "screen": {"object": {"id": "ComposeScreen", "props": {
        "to": "给：团队", "draft": "今天的实验结果已经整理好，请查看附件。", "send": "发送"}}}}),
    "ChromeMachine": ("ObjectStage", {"object": {"id": "ChromeMachine"}, "title": "一台咖啡机"}),
    "LabeledPuck": ("ObjectStage", {"object": {"id": "LabeledPuck"}, "title": "粉饼"}),
    "SwirlOfCoffee": ("ObjectStage", {"object": {"id": "SwirlOfCoffee"}, "title": "萃取"}),
}


def _settled_frame(out_dir, host):
    """The frame at which `host`'s OWN `useT()` has settled — read from its real `DURATION`, the same inversion
    `workshop.still()` uses by default, so a host shorter or longer than any host this script already renders
    still lands past its entrance and before its exit instead of mid-animation or past its last frame."""
    return int(round(rr.frame_at_t(ws._required_duration(ws.shot_source(out_dir, host), host), rr.SETTLED_T)))


def main():
    film = tempfile.mkdtemp(prefix="object_examples_")
    try:
        d = os.path.join(film, "workshop", "objects")
        os.makedirs(d)
        for n in SHOTS:
            shutil.copy(os.path.join(EX, n + ".tsx"), os.path.join(d, n + ".tsx"))
        ws.write_index(film)
        for n, (host, props) in SHOTS.items():
            pf = os.path.join(film, n + ".json")
            with open(pf, "w", encoding="utf-8") as fh:
                json.dump(dict(props, dna="product"), fh, ensure_ascii=False)
            png = os.path.join(EX, n + ".png")
            frame = _settled_frame(film, host)
            subprocess.run(["npx", "remotion", "still", "src/index.ts", host, png, "--frame=%d" % frame,
                            "--scale=0.5", "--gl=angle", "--log=error", "--props=" + pf], cwd=ws.REMOTION,
                           check=True, **ws.run_kwargs(film))
            print("[object_examples] %s (frame %d)" % (png, frame))
    finally:
        shutil.rmtree(film, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
