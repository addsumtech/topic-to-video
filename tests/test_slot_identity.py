"""A REGISTER THAT GAINED AN OBJECT SLOT DRAWS EXACTLY WHAT IT DREW BEFORE WHEN THE SLOT IS EMPTY.

The reference is the register's own source at the commit before any slot existed (BEFORE), rendered as a
film-local shot beside the current register — one bundle, the same props, the same frames — so the comparison is
exact on any machine and needs no stored pictures. Every pixel must match, at a moving frame and at the settled
one, at 16:9 and 9:16, for the register's standalone preview and for a film-like prop set."""
import json
import os
import re
import subprocess
import sys

import pytest
from PIL import Image, ImageChops, ImageDraw, ImageFont

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_workshop_bundle import _index, _env  # noqa: E402

BEFORE = "90df454"                       # the spec's commit: every register below, as it was before any slot
FONT = os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf")


def _before_source(name):
    r = subprocess.run(["git", "-C", _ROOT, "show", "%s:remotion/src/shots/%s.tsx" % (BEFORE, name)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip("the reference commit %s is not in this checkout (a git-archive copy has no history)" % BEFORE)
    src = r.stdout.replace("from '../runtime/", "from '@runtime/")
    src = re.sub(r"from '\./(\w+)'", r"from '@shots/\1'", src)
    src = re.sub(r"\bexport const %s\b" % name, "export const %sBefore" % name, src)
    src = re.sub(r"^export default %s;\s*$" % name, "", src, flags=re.M)
    return src + "\nexport const GROUND = 'bg';\n"


def _screenshot(path, h):
    im = Image.new("RGB", (1170, h), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 46)
    d.rounded_rectangle([60, 200, 1110, 320], radius=36, fill=(238, 241, 244))
    for i in range(max(1, (h - 500) // 180)):
        d.text((90, 420 + i * 180), "第%d条反馈" % (i + 1), fill=(20, 23, 28), font=f)
    im.save(path)


def _duration(name):
    src = open(os.path.join(_REM, "src", "shots", name + ".tsx"), encoding="utf-8").read()
    return int(re.search(r"export const DURATION\s*=\s*(\d+)", src).group(1))


def _prepared(shot, aspect, public):
    import device_script as ds
    W, H = {"16:9": (1920, 1080), "9:16": (1080, 1920)}[aspect]
    if shot == "DeviceDemo":
        props = {"device": "phone", "steps": [{"screen": {"image": "ui_long.png"}}, {"tap": [0.5, 0.2]}, {"scroll": 0.5}]}
    else:
        props = {"device": "phone", "screen": {"image": "ui.png"}}
    out, _w = ds.prepare(props, shot=shot, out_dir=public, dur_frames=_duration(shot), fps=30, W=W, H=H, lang="zh")
    return out


# {register: [(label, make_props(aspect, public_dir))]} — its standalone preview and a film-like set, slot unset
CASES = {
    "DeviceDemo": [("demo", lambda a, pub: {}), ("film", lambda a, pub: _prepared("DeviceDemo", a, pub))],
    "DeviceHero": [("demo", lambda a, pub: {}), ("film", lambda a, pub: _prepared("DeviceHero", a, pub))],
}
SLOTTED = sorted(CASES)


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    if not os.path.isdir(os.path.join(_REM, "node_modules")):
        pytest.skip("needs the remotion toolchain")
    root = tmp_path_factory.mktemp("identity")
    shots = root / "workshop" / "shots"
    shots.mkdir(parents=True)
    for n in SLOTTED:
        (shots / (n + "Before.tsx")).write_text(_before_source(n), encoding="utf-8")
    (root / "workshop" / "index.ts").write_text(_index(sorted(n + "Before" for n in SLOTTED), []), encoding="utf-8")
    pub = root / "public"
    pub.mkdir()
    _screenshot(str(pub / "ui.png"), 2532)
    _screenshot(str(pub / "ui_long.png"), 6000)
    out = root / "bundle"
    r = subprocess.run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + str(out), "--public-dir=" + str(pub),
                        "--log=error"], cwd=_REM, env=_env(root / "workshop"), capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    return {"bundle": str(out), "root": root, "public": str(pub)}


def _render(b, comp, props, frame, name):
    pf = b["root"] / (name + ".json")
    pf.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    png = str(b["root"] / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", b["bundle"], comp, png, "--frame=%d" % frame, "--gl=angle",
                        "--log=error", "--props=" + str(pf)], cwd=_REM, env=_env(), capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, (comp, (r.stdout + r.stderr)[-600:])
    return png


def _frames(name):
    import render_remotion as rr
    d = _duration(name)
    return [("mid", int(d * 0.4), ("16:9",)),
            ("settled", int(round(rr.frame_at_t(d, rr.SETTLED_T))), ("16:9", "9:16"))]


@pytest.mark.parametrize("name", SLOTTED)
def test_an_empty_slot_draws_exactly_what_the_register_drew_before(bundle, name):
    diffs = []
    for label, make in CASES[name]:
        for when, frame, aspects in _frames(name):
            for aspect in aspects:
                props = dict(make(aspect, bundle["public"]), dna="product", aspect=aspect)
                tag = "%s-%s-%s-%s" % (name, label, when, aspect.replace(":", "x"))
                now = Image.open(_render(bundle, name, props, frame, tag + "-now")).convert("RGB")
                was = Image.open(_render(bundle, name + "Before", props, frame, tag + "-before")).convert("RGB")
                box = ImageChops.difference(now, was).getbbox()
                if box:
                    diffs.append((tag, box))
    assert not diffs, "with its slot empty the register no longer draws what it drew before: %r" % diffs
