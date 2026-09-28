"""A REGISTER THAT GAINED AN OBJECT SLOT DRAWS EXACTLY WHAT IT DREW BEFORE WHEN THE SLOT IS EMPTY.

The reference is the register's own source at the commit before any slot existed (BEFORE), rendered as a
film-local shot beside the current register — one bundle, the same props, the same frames — so the comparison is
exact on any machine and needs no stored pictures. Every pixel must match at frames taken from the register's
OWN real motion (an entrance, a tap, a scroll, a screen transition — never a blind fraction of the duration,
which can land outside every one of them), at 16:9 and 9:16 for the settled frame, under the product DNA, a
light DNA and the null DNA (no theme at all), for the register's standalone preview and for a film-like prop
set."""
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
# A DNA distinct from the default (device.defaultLook reads a DNA's own bg luminance, and every NAMED preset
# is dark, so "product" alone never exercises the 'flat' look) and the null DNA — no theme at all, the
# register's own INK_D0/BG_D0 fallbacks. Both stand beside "product" below, never replacing it.
LIGHT_DNA = {"bg": "#eef1f4", "fg": "#14171c", "surface": "#ffffff", "accent": "#3563e9", "accent2": "#00b894"}


def _before_source(name):
    # A missing COMMIT (a shallow clone, a git-archive checkout with no history) is a skip: there is nothing
    # to compare against. A missing PATH at a commit that DOES exist is a bug in this fixture, not a machine
    # that cannot run it — it must fail loudly, not read as "no history here" and vanish from the count.
    if subprocess.run(["git", "-C", _ROOT, "cat-file", "-e", BEFORE + "^{commit}"],
                      capture_output=True).returncode != 0:
        pytest.skip("the reference commit %s is not in this checkout (a git-archive copy has no history)" % BEFORE)
    r = subprocess.run(["git", "-C", _ROOT, "show", "%s:remotion/src/shots/%s.tsx" % (BEFORE, name)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, "git show %s:remotion/src/shots/%s.tsx failed: %s" % (BEFORE, name, r.stderr)
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
        # A MEASURABLE tap (it lands on the first text row's real ink, so prepare() gives it a push-in — a
        # bare coordinate over blank ground gets no focus/textFrac and never moves the camera), a scroll, and
        # a SECOND screen (its own transition, "via": "push") — three different motions on one register,
        # none of them an object.
        row0_y = ds._viewport((420 + 30) / 6000.0, 1170, 6000, "phone", 0.0)
        props = {"device": "phone", "steps": [
            {"screen": {"image": "ui_long.png"}},
            {"tap": [0.2, row0_y]},
            {"scroll": 0.5},
            {"screen": {"image": "ui.png"}, "via": "push"},
        ]}
    else:
        props = {"device": "phone", "screen": {"image": "ui.png"}}
    out, _w = ds.prepare(props, shot=shot, out_dir=public, dur_frames=_duration(shot), fps=30, W=W, H=H, lang="zh")
    return out


# {register: [(label, make_props(aspect, public_dir), dna)]} — its standalone preview and a film-like set,
# slot unset either way; DNA varies across entries so "product", a light DNA and the null DNA are each
# exercised on both a demo and a film-prepared case, without crossing all three with every frame.
CASES = {
    "DeviceDemo": [
        ("demo", lambda a, pub: {}, "product"),
        ("demo", lambda a, pub: {}, LIGHT_DNA),
        ("film", lambda a, pub: _prepared("DeviceDemo", a, pub), "product"),
        ("film", lambda a, pub: _prepared("DeviceDemo", a, pub), None),
    ],
    "DeviceHero": [
        ("demo", lambda a, pub: {}, "product"),
        ("demo", lambda a, pub: {}, LIGHT_DNA),
        ("film", lambda a, pub: _prepared("DeviceHero", a, pub), "product"),
        ("film", lambda a, pub: _prepared("DeviceHero", a, pub), None),
    ],
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


def _entry_frames(name, label, props, dur):
    """[(when, frame, aspects)] taken from THIS case's own real motion — never a blind fraction of the
    duration (DeviceHero's rise finishes a third in; DeviceDemo's tap and scroll sit wherever the schedule
    put them, evenly on the standalone demo or on ds.prepare()'s real schedule for a film-like script)."""
    import render_remotion as rr
    at = lambda t: int(round(rr.frame_at_t(dur, t)))
    settled = ("settled", at(rr.SETTLED_T), ("16:9", "9:16"))
    if name == "DeviceHero":
        mid_entrance = (rr.ENTRY_T + 0.32) / 2                # inside seg(t, ENTRY_T, 0.32)'s rise+turn
        return [("entrance", at(mid_entrance), ("16:9",)), settled]
    if label == "demo":
        # DEMO_STEPS = [screen, tap], spread evenly by scheduled()'s own formula: slot = (1-ENTRY_T)/2, and
        # step i=1 (the tap) acts across ta=ENTRY_T+1.35*slot .. t1=ENTRY_T+1.9*slot.
        slot = (1 - rr.ENTRY_T) / 2
        ta, t1 = rr.ENTRY_T + 1.35 * slot, rr.ENTRY_T + 1.9 * slot
        return [("tap", at((ta + t1) / 2), ("16:9",)), settled]
    steps = props["steps"]
    tap = next(s for s in steps if "tap" in s)
    scroll = next(s for s in steps if "scroll" in s)
    transition = steps[-1]                                    # the second `screen` step
    mid = lambda s: (s["ta"] + s["t1"]) / 2
    return [
        ("tap", at(mid(tap)), ("16:9",)),
        ("scroll", at(mid(scroll)), ("16:9",)),
        ("transition", at((transition["t0"] + transition["ta"]) / 2), ("16:9",)),
        settled,
    ]


def _dna_tag(dna):
    if dna is None:
        return "null"
    return dna if isinstance(dna, str) else "light"


@pytest.mark.parametrize("name", SLOTTED)
def test_an_empty_slot_draws_exactly_what_the_register_drew_before(bundle, name):
    diffs = []
    dur = _duration(name)
    for label, make, dna in CASES[name]:
        props0 = make("16:9", bundle["public"]) if label == "film" else None
        for when, frame, aspects in _entry_frames(name, label, props0, dur):
            for aspect in aspects:
                base = make(aspect, bundle["public"]) if label == "film" else {}
                props = dict(base, dna=dna, aspect=aspect)
                tag = "%s-%s-%s-%s-%s" % (name, label, _dna_tag(dna), when, aspect.replace(":", "x"))
                now = Image.open(_render(bundle, name, props, frame, tag + "-now")).convert("RGB")
                was = Image.open(_render(bundle, name + "Before", props, frame, tag + "-before")).convert("RGB")
                box = ImageChops.difference(now, was).getbbox()
                if box:
                    diffs.append((tag, box))
    assert not diffs, "with its slot empty the register no longer draws what it drew before: %r" % diffs
