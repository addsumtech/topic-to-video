"""scripts/blender_clip.py: the director path's door to Blender — the plate runner and kit without a storyboard."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import blender_clip as bc  # noqa: E402


def test_command_renders_every_frame_whole_with_the_plate_runner():
    cmd = bc.command("/B", "s.py", "/out", 60, 30, 1920, 1080, "cycles", 48, False, "{}")
    assert cmd[:2] == ["/B", "-b"] and "--python-exit-code" in cmd
    assert cmd[cmd.index("--python") + 1] == bc.RUNNER and os.path.basename(bc.RUNNER) == "runner.py"
    assert "--no-reuse" in cmd                         # patch frames would need blender_plate's assembly
    assert cmd[cmd.index("--mode") + 1] == "rgba" and cmd[cmd.index("--engine") + 1] == "cycles"
    assert cmd[cmd.index("--frames") + 1] == "60" and "--still" not in cmd


def test_env_and_still_flags():
    cmd = bc.command("/B", "s.py", "/out", 60, 30, 640, 360, "eevee", 16, True, '{"a": 1}', still=12)
    assert cmd[cmd.index("--mode") + 1] == "env" and cmd[cmd.index("--still") + 1] == "12"
    assert cmd[cmd.index("--params") + 1] == '{"a": 1}'


def test_usage_errors_exit_2(tmp_path, capsys):
    assert bc.main([str(tmp_path), str(tmp_path / "missing.py"), "--seconds", "1"]) == 2
    scene = tmp_path / "s.py"
    scene.write_text("def build(k): pass\ndef pose(k, t): pass\n")
    assert bc.main([str(tmp_path), str(scene), "--seconds", "1", "--size", "big"]) == 2
