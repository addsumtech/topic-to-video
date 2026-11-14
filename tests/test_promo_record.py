"""promo_record: a page's own animation recorded frame-exact on Chrome's virtual clock, and the hand's events kept."""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import promo_capture as pc  # noqa: E402
import promo_record as pr  # noqa: E402

PAGE = """<!doctype html><html><head><title>Rec</title><style>body{margin:0;background:#fff}
#b{position:absolute;left:20px;top:20px;width:100px;height:40px}
#box{position:absolute;left:0;top:100px;width:40px;height:40px;background:#f00;transition:transform .5s linear}
#box.go{transform:translateX(300px)}</style></head>
<body><button id="b" onclick="document.getElementById('box').classList.add('go')">Go</button><div id="box"></div></body></html>"""


def _box_x(png):
    from PIL import Image
    with Image.open(png) as im:
        im = im.convert("RGB")
        y = 240                                                   # the box's row at 2x
        xs = [x for x in range(im.width) if (lambda p: p[0] > 200 and p[1] < 80 and p[2] < 80)(im.getpixel((x, y)))]
    return min(xs) / 2 if xs else None                            # back to CSS px


RAF = PAGE.replace("onclick=\"document.getElementById('box').classList.add('go')\"", 'onclick="go()"').replace(
    "</body>", "<script>function go(){const b=document.getElementById('box');const t0=performance.now();"
    "function f(){const u=Math.min(1,(performance.now()-t0)/500);b.style.left=(300*u)+'px';if(u<1)requestAnimationFrame(f)}"
    "requestAnimationFrame(f)}</script></body>")
LATER = PAGE.replace("onclick=\"document.getElementById('box').classList.add('go')\"",
                     "onclick=\"setTimeout(()=>document.getElementById('box').classList.add('go'),300)\"")


def _record_xs(tmp_path, page, fps, seconds=1.2):
    html = tmp_path / "p.html"
    html.write_text(page)
    out = pr.record(str(tmp_path), "file://" + str(html), "rec", seconds=seconds, script=[{"t": 0.2, "click": "#b"}],
                    W=480, H=240, fps=fps, wait=0.2)
    frames = tmp_path / "fr"
    frames.mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp_path / "caps" / "rec.mp4"), str(frames / "%03d.png")], check=True)
    return out, [_box_x(str(frames / ("%03d.png" % (k + 1)))) for k in range(out["frames"])]


def _expected(fps, start, n):
    """still until `start` (the frame the motion begins on), then 300 px over 0.5 s linearly, then at rest"""
    step = 300.0 / (0.5 * fps)
    return [min(300.0, max(0.0, (k - start) * step)) for k in range(n)]


@pytest.mark.skipif(not pc.find_chrome(), reason="no Chrome")
@pytest.mark.parametrize("fps", [30, 10])
def test_a_click_starts_the_pages_own_transition_on_the_recorded_frames(tmp_path, fps):
    out, xs = _record_xs(tmp_path, PAGE, fps)
    k = round(0.2 * fps)
    assert out["frames"] == round(1.2 * fps) and out["fps"] == fps and (out["w"], out["h"]) == (480, 240)
    assert [e for e in out["events"] if e["kind"] == "click"] == [{"frame": k, "kind": "click", "x": 70.0, "y": 40.0}]
    for f in ("rec.mp4", "rec.png", "rec.layout.json"):
        assert (tmp_path / "caps" / f).is_file()
    # still until the click's frame, then the page's own 0.5 s linear transition at its own pace, then at rest. A
    # transform transition runs on the compositor, on its own clock: unpinned it was sampled at 2/3 pace and snapped
    # to its end. Under Chrome's virtual time a still page produced no frame at 30 fps at all (it stalled).
    assert xs == _expected(fps, k, len(xs))


@pytest.mark.skipif(not pc.find_chrome(), reason="no Chrome")
@pytest.mark.parametrize("page, delay", [(RAF, 0.0), (LATER, 0.3)], ids=["requestAnimationFrame", "setTimeout"])
def test_the_pages_own_timers_and_frames_run_on_the_recording_clock(tmp_path, page, delay):
    _, xs = _record_xs(tmp_path, page, 30)
    assert xs == _expected(30, round((0.2 + delay) * 30), len(xs))


@pytest.mark.skipif(not pc.find_chrome(), reason="no Chrome")
def test_a_scroll_is_an_eased_move_on_the_frame_clock_not_the_compositors(tmp_path):
    from PIL import Image
    html = tmp_path / "p.html"
    html.write_text('<!doctype html><html><body style="margin:0;height:3000px;background:#fff">'
                    '<div style="position:absolute;left:0;top:400px;width:40px;height:40px;background:#f00"></div></body></html>')
    out = pr.record(str(tmp_path), "file://" + str(html), "rec", seconds=1.0, script=[{"t": 0.2, "scroll": [0, 300], "dur": 0.5}],
                    W=480, H=480, fps=10, wait=0.2)
    assert out["events"] == [{"frame": 2, "kind": "scroll", "by": [0, 300], "until": 6}]
    frames = tmp_path / "fr"
    frames.mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp_path / "caps" / "rec.mp4"), str(frames / "%02d.png")], check=True)

    def top(p):
        with Image.open(p) as im:
            im = im.convert("RGB")
            ys = [y for y in range(im.height) if (lambda q: q[0] > 200 and q[1] < 80)(im.getpixel((20, y)))]
        return min(ys) / 2

    ys = [top(str(frames / ("%02d.png" % (k + 1)))) for k in range(10)]
    eased = [400 - 300 * (u * u * (3 - 2 * u)) for u in (j / 5 for j in range(1, 6))]
    assert ys[:2] == [400, 400] and ys[7:] == [100, 100, 100]
    assert ys[2:7] == pytest.approx(eased, abs=1.0)            # the smoothstep, frame by frame (a smooth scrollBy hung)
