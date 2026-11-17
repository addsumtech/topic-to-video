"""assets/html/stage3d.js renders a lit 3D stage with a real screen as a panel, from file://, in headless Chrome:
the canvas is not blank, the screen's own colours survive (it emits its picture), and the build is the committed one."""
import os
import shutil
import subprocess

import pytest
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


@pytest.mark.skipif(not os.path.exists(CHROME), reason="Chrome not installed")
def test_a_screen_renders_as_a_lit_panel(tmp_path):
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), tmp_path)
    Image.new("RGB", (800, 500), (255, 40, 40)).save(tmp_path / "screen.png")       # a pure red "screen"
    (tmp_path / "p.html").write_text("""<!doctype html><html><body style="margin:0;background:#000">
<canvas id="c" width="640" height="360"></canvas><script src="stage3d.js"></script><script>
const st = Stage3D.create({canvas: document.getElementById('c'), background: '#05060a'});
st.studio(); st.floor({}); st.panel('screen.png', {width: 4, x: 0, y: 1.6, rotY: -0.2});
st.ready().then(() => st.render({pos: [0, 1.8, 6], look: [0, 1.6, 0], fov: 40}));
</script></body></html>""")
    shot = tmp_path / "shot.png"
    subprocess.run([CHROME, "--headless=new", "--allow-file-access-from-files", "--hide-scrollbars",
                    "--window-size=640,360", "--virtual-time-budget=6000", "--screenshot=%s" % shot,
                    "file://%s" % (tmp_path / "p.html")], capture_output=True, timeout=120)
    im = Image.open(shot).convert("RGB")
    r, g, b = im.getpixel((320, 150))                          # the panel's centre
    assert r > 200 and g < 90 and b < 90, (r, g, b)            # the screen keeps its own red: it emits, unlit
    assert im.getpixel((5, 5))[0] < 40                         # the ground is the dark stage, not blank white


def test_the_committed_bundle_matches_its_source(tmp_path):
    out = tmp_path / "stage3d.js"
    subprocess.run([os.path.join(ROOT, "remotion", "node_modules", ".bin", "esbuild"),
                    os.path.join(ROOT, "assets", "html", "stage3d", "src.js"), "--bundle", "--minify", "--format=iife",
                    "--global-name=Stage3D", "--log-level=warning", "--outfile=%s" % out,
                    "--alias:three=%s" % os.path.join(ROOT, "remotion", "node_modules", "three", "build", "three.module.js"),
                    "--alias:three/examples=%s" % os.path.join(ROOT, "remotion", "node_modules", "three", "examples")],
                   check=True)
    assert out.read_bytes() == open(os.path.join(ROOT, "assets", "html", "stage3d.js"), "rb").read(), \
        "assets/html/stage3d.js is stale: run scripts/build_stage3d.sh"
