"""film_qc: a film of type only has no textured picture for the glide check to judge — that is OK, not red
(GSAP demo 2026-11-26: a type-only film went red on 'glide' with NOTHING TO JUDGE)."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_a_type_only_film_passes_glide_with_nothing_to_judge(tmp_path):
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=0x0b0c0d:s=1920x1080:d=2:r=30",
                    "-pix_fmt", "yuv420p", str(tmp_path / "final.mp4")], check=True)
    (tmp_path / "_plan.json").write_text(json.dumps({"video": "final.mp4", "fps": 30, "frames": 60, "cuts": [],
                                                    "segments": [{"start": 0, "end": 60, "kind": "shot"}]}))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "film_qc.py"), str(tmp_path), "--only", "glide"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and "OK   glide (nothing to judge)" in r.stdout, r.stdout + r.stderr
