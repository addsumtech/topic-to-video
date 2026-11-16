"""`workshop.py <film_dir> clip <Name>` renders a built shot to <film_dir>/clips/<Name>.mp4 at full size with the same
composition and props `still` uses — the door through which the director path puts the kit's lit / material / 3D
work into a film it assembles itself (SKILL.md step 6)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import workshop  # noqa: E402


def test_clip_renders_the_still_composition_full_size(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(workshop, "still_plan", lambda out_dir, name, props=None, **kw: ("Comp_" + name, {"a": 1}, 90))

    def fake_render(run, cmd, **kw):
        seen["cmd"] = cmd
        open(cmd[5], "wb").write(b"x")
        class R:
            returncode, stdout, stderr = 0, "", ""
        return R()

    monkeypatch.setattr(workshop._c, "run_render", fake_render)
    mp4 = workshop.render_clip(str(tmp_path), "Lit", frames="0-29")
    assert mp4 == os.path.join(str(tmp_path), "clips", "Lit.mp4") and os.path.isfile(mp4)
    cmd = seen["cmd"]
    assert cmd[:5] == ["npx", "remotion", "render", "src/index.ts", "Comp_Lit"]
    assert "--frames=0-29" in cmd and "--muted" in cmd
    assert not any(c.startswith("--scale") for c in cmd)            # full size, unlike the motion probe
    pf = next(c for c in cmd if c.startswith("--props="))[len("--props="):]
    assert json.load(open(pf)) == {"a": 1}


def test_clip_is_a_subcommand():
    src = open(workshop.__file__, encoding="utf-8").read()
    assert 'sub.add_parser("clip"' in src and "<out_dir> clip <Name>" in src
