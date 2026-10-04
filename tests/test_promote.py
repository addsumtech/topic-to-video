"""promote.py moves a DELIVERED film's built thing into the library, and refuses — by name — anything else.

These tests redirect every library path into a sandbox and stub the registration and the measurement runs, so they
judge promote.py's own decisions: the preconditions, the rewritten source, the card, the catalogue, the object
index, the order of measurements, and what happens to the film. A real promotion — the actual library, a real
render, real measurements — is exercised separately."""
import json
import os
import shutil
import sys
import time

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promote as pr  # noqa: E402
import workshop as ws  # noqa: E402

OBJ = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01} from '@runtime/motion';
export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};
export const %(name)s: React.FC<ObjectProps & {packed?: number}> = ({w, h, t, packed = 0}) => (
  <div style={{width: w, height: h * clamp01(t + packed)}} />
);
"""
SHOT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useT} from '@runtime/motion';
import {TermTable} from '@shots/TermTable';
export const DURATION = 150;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{
  title?: string;
  flow?: number;
}> = ({title = '', flow = 1}) => {
  const t = useT();
  return <AbsoluteFill>{title}{flow * t > 2 ? <TermTable /> : null}</AbsoluteFill>;
};
"""
DOCS = {"title?: string;": "title?: string;   // the curve's name — short, it heads the frame",
        "flow?: number;": "flow?: number;    // how fast the water moves, 0-3 — faster reads as pressure"}


def _film(tmp_path, delivered=True, name="EspressoPuck", kind="object", src=None):
    out = tmp_path / "film"
    d = out / "workshop" / (kind + "s")
    d.mkdir(parents=True)
    (d / (name + ".tsx")).write_text((src or (OBJ if kind == "object" else SHOT)) % {"name": name}, encoding="utf-8")
    board = {"meta": {"renderer": "remotion", "design_dna": "product", "title": "咖啡",
                      "build_list": [{"id": name, "kind": kind, "beats": [2], "slot": "ObjectStage" if kind == "object" else "own",
                                      "means": "water forced through a packed bed", "accept": "a viewer sees the bed resist"}]},
             "slides": [{"index": 2, "shot": "ObjectStage", "shot_props": {"object": {"id": name}}}]}
    (out / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    if delivered:
        time.sleep(0.01)
        (out / "out.mp4").write_bytes(b"\0")
    return str(out)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    lib = tmp_path / "lib"
    for sub in ("shots", "objects", "cards"):
        (lib / sub).mkdir(parents=True)
    shutil.copy(os.path.join(_ROOT, "remotion", "src", "objects", "index.ts"), str(lib / "objects" / "index.ts"))
    shutil.copy(os.path.join(_ROOT, "remotion", "LIBRARY.md"), str(lib / "LIBRARY.md"))
    monkeypatch.setattr(pr, "SHOTS", str(lib / "shots"))
    monkeypatch.setattr(pr, "OBJECTS", str(lib / "objects"))
    monkeypatch.setattr(pr, "CARDS", str(lib / "cards"))
    monkeypatch.setattr(pr, "LIBRARY", str(lib / "LIBRARY.md"))
    monkeypatch.setattr(ws, "check", lambda out_dir: [])
    calls = {"register": [], "run": []}

    def fake_register(name, family, use_when, provenance):
        calls["register"].append((name, family, use_when, provenance))
        with open(str(lib / "LIBRARY.md"), "a", encoding="utf-8") as fh:
            fh.write("\n999. **%s** — %s *Use: %s*\n" % (name, use_when, use_when))
    monkeypatch.setattr(pr, "_register", fake_register)
    monkeypatch.setattr(pr, "_run", lambda cmd, log=print: calls["run"].append(cmd[1:]))
    monkeypatch.setattr(pr, "_measured_line", lambda name: "**Measured:** 5.0% ink (clip median) · 40.0% footprint · 0.004 motion.")
    return lib, calls


def test_an_undelivered_film_is_refused(tmp_path, sandbox):
    out = _film(tmp_path, delivered=False)
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "EspressoPuck")
    assert any("no out.mp4" in p for p in e.value.problems)


def test_a_film_the_critic_has_not_passed_is_refused(tmp_path, sandbox):
    out = _film(tmp_path)
    open(os.path.join(out, "NOT_DELIVERED.md"), "w").close()
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "EspressoPuck")
    assert any("NOT_DELIVERED.md" in p for p in e.value.problems)


def test_an_item_changed_after_the_render_is_refused(tmp_path, sandbox):
    out = _film(tmp_path)
    time.sleep(0.02)
    p = os.path.join(ws.workshop_dir(out), "objects", "EspressoPuck.tsx")
    open(p, "a").write("\n// tweaked after delivery\n")
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "EspressoPuck")
    assert any("changed after the film was rendered" in x for x in e.value.problems)


def test_an_item_not_on_the_build_list_or_already_in_the_library_is_refused(tmp_path, sandbox, monkeypatch):
    out = _film(tmp_path, name="TermTable", kind="shot")
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "TermTable", family="I", use_when="x", motion="y")
    assert any("already has TermTable" in p for p in e.value.problems)


def test_an_object_moves_into_the_library_index_and_catalogue_and_the_film_follows_it(tmp_path, sandbox):
    lib, calls = sandbox
    out = _film(tmp_path)
    pr.promote(out, "EspressoPuck")
    src = open(str(lib / "objects" / "EspressoPuck.tsx"), encoding="utf-8").read()
    assert "from '../runtime/objectSlot'" in src and "from '../runtime/motion'" in src and "@runtime" not in src
    idx = open(str(lib / "objects" / "index.ts"), encoding="utf-8").read()
    assert "import * as O_EspressoPuck from './EspressoPuck';" in idx
    assert "EspressoPuck: {C: O_EspressoPuck.EspressoPuck, meta: O_EspressoPuck.META}," in idx
    cat = open(str(lib / "LIBRARY.md"), encoding="utf-8").read()
    assert "- **EspressoPuck** — water forced through a packed bed" in cat.split(pr.OBJECTS_ANCHOR)[1]
    assert not os.path.exists(os.path.join(ws.workshop_dir(out), "objects", "EspressoPuck.tsx"))
    entry = json.load(open(os.path.join(out, "storyboard.json")))["meta"]["build_list"][0]
    assert entry["promoted"] is True
    assert calls["register"] == [] and calls["run"] == []          # an object is catalogued, not measured


def test_a_shot_is_registered_carded_measured_in_order_and_the_film_follows_it(tmp_path, sandbox):
    lib, calls = sandbox
    src = SHOT
    for a, b in DOCS.items():
        src = src.replace(a, b)
    out = _film(tmp_path, name="ExtractionCurve", kind="shot", src=src)
    pr.promote(out, "ExtractionCurve", family="I", use_when="how flow changes through a shot", motion="the curve draws, then holds")
    code = open(str(lib / "shots" / "ExtractionCurve.tsx"), encoding="utf-8").read()
    assert "from '../runtime/motion'" in code and "from './TermTable'" in code
    assert "export const GROUND" not in code and "export const PROVENANCE" not in code
    assert calls["register"] == [("ExtractionCurve", "I", "how flow changes through a shot", "industrial")]
    assert calls["run"] == [c[1:] for c in pr.measurements("ExtractionCurve")], calls["run"]
    order = [c[0].split("/")[-1] for c in calls["run"]]
    assert order.index("measure_ground_reach.py") < order.index("measure_ground_luma.py") < order.index("register_energy.py")
    assert order.index("register_energy.py") < order.index("cjk_type_qa.py")
    # A `--only ... --emit` run classifies and prints but never writes the COMMITTED ground-luma table (a
    # bare spot check overwriting the whole library's table once lost it outright), so a register promoted
    # from a workshop needs its own merge into that file — `record_spot` — after both emits report their
    # classification and before anything downstream hashes the row.
    luma_positions = [i for i, c in enumerate(calls["run"]) if c[0].split("/")[-1] == "measure_ground_luma.py"]
    spot_positions = [i for i, c in enumerate(calls["run"]) if c[0] == "-c" and "record_spot" in c[-1]]
    assert len(luma_positions) == 2, calls["run"]
    assert len(spot_positions) == 1, calls["run"]
    assert max(luma_positions) < spot_positions[0] < order.index("register_energy.py")
    card = open(str(lib / "cards" / "ExtractionCurve.md"), encoding="utf-8").read()
    for part in ("# ExtractionCurve\n", "**Identity:** water forced through a packed bed", "**Use when:** how flow changes",
                 "**Motion core:** the curve draws, then holds", "| `title` | the curve's name", "| `flow` | how fast",
                 "faster reads as pressure", "**Known traps:**", "`remotion/src/shots/ExtractionCurve.tsx`",
                 "**Measured:** 5.0% ink", "**Provenance:** industrial. **Family:** I."):
        assert part in card, (part, card)
    assert "999. **ExtractionCurve** — water forced through a packed bed *Use: how flow changes through a shot.*" in \
        open(str(lib / "LIBRARY.md"), encoding="utf-8").read()
    assert not os.path.exists(os.path.join(ws.workshop_dir(out), "shots", "ExtractionCurve.tsx"))


def test_a_shot_with_an_undocumented_prop_is_refused(tmp_path, sandbox):
    out = _film(tmp_path, name="ExtractionCurve", kind="shot")
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "ExtractionCurve", family="I", use_when="x", motion="y")
    assert any("`title`" in p and "comment" in p for p in e.value.problems), e.value.problems


def test_a_shot_needs_its_family_use_and_motion(tmp_path, sandbox):
    out = _film(tmp_path, name="ExtractionCurve", kind="shot")
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "ExtractionCurve")
    assert any("--family" in p for p in e.value.problems)


def test_an_import_the_library_cannot_resolve_is_refused(tmp_path):
    text, probs = pr.library_source("import {R} from './puckGeometry';\nimport art from '../assets/a.png';\n"
                                    "import {seg} from '@runtime/motion';\nimport {X} from '@shots/NoSuchShot';\n",
                                    "object", "EspressoPuck")
    assert "from '../runtime/motion'" in text
    assert any("./puckGeometry" in p for p in probs) and any("../assets/a.png" in p for p in probs), probs
    assert any("NoSuchShot" in p for p in probs), probs


def test_dry_run_changes_nothing(tmp_path, sandbox):
    lib, calls = sandbox
    out = _film(tmp_path)
    before = sorted(os.listdir(str(lib / "objects")))
    plan = pr.promote(out, "EspressoPuck", dry_run=True)
    assert plan["kind"] == "object" and sorted(os.listdir(str(lib / "objects"))) == before
    assert os.path.exists(os.path.join(ws.workshop_dir(out), "objects", "EspressoPuck.tsx"))


ALIAS_OBJ = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 0.85, provenance: 'survey-archive'};
type Props = ObjectProps & {
  years?: number[];   // era boundaries, oldest first
  laid?: number;      // how many layers stand by the end
};
export const %(name)s: React.FC<Props> = ({w, h, years = [], laid}) => <svg width={w} height={h} />;
"""


@pytest.mark.parametrize("src,props", [(OBJ, "`packed`"), (ALIAS_OBJ, "`laid, years`")], ids=["inline", "alias"])
def test_an_objects_catalogue_line_names_the_props_it_declares_beside_the_slots_own(tmp_path, sandbox, src, props):
    """An object is declared over the slot's own props — `React.FC<ObjectProps & {...}>`, or a `Props` alias of
    that intersection — and its catalogue line is where a director learns what it takes. Read only up to the
    `ObjectProps &`, every promoted object was catalogued with no props at all."""
    lib, _calls = sandbox
    out = _film(tmp_path, src=src)
    pr.promote(out, "EspressoPuck")
    line = next(ln for ln in open(str(lib / "LIBRARY.md"), encoding="utf-8").read().splitlines()
                if ln.startswith("- **EspressoPuck**"))
    assert line.endswith(props), line


def test_a_promoted_shot_refreshes_the_catalogue_census_and_headline_count(monkeypatch):
    """register_shot's own command rewrites LIBRARY.md's family census and its "(N design languages)" headline
    after every registration. A promotion registers through the module, so it has to ask for the same refresh —
    without it the catalogue's one trusted number is one short after every promoted shot, and the census omits
    the shelf the shot was filed on."""
    import register_shot as rs
    calls = []
    monkeypatch.setattr(rs, "register", lambda *a, **k: calls.append("register") or {})
    monkeypatch.setattr(rs, "refresh_family_census", lambda: calls.append("census") or True)
    monkeypatch.setattr(rs, "check", lambda name: calls.append("check") or [])
    pr._register("SomeRegister", "H", "one setting decides the time", "industrial")
    assert calls == ["register", "census", "check"], calls


def test_a_census_that_cannot_be_refreshed_is_a_refusal_not_a_stale_catalogue(monkeypatch):
    import register_shot as rs
    monkeypatch.setattr(rs, "register", lambda *a, **k: {})
    monkeypatch.setattr(rs, "refresh_family_census", lambda: False)
    monkeypatch.setattr(rs, "check", lambda name: [])
    with pytest.raises(pr.PromoteError) as e:
        pr._register("SomeRegister", "H", "x", "industrial")
    assert any("census" in p for p in e.value.problems), e.value.problems


def test_measurements_runs_the_spot_merge_once_after_both_luma_emits(tmp_path):
    """measurements() is probed directly (no render, no sandbox) so the order claim cannot be satisfied by
    accident — a shot's promotion must leave the committed ground-luma table confirmable the moment both
    emits have printed their classification, never only after a later measurement that merely hashes it."""
    cmds = pr.measurements("SomeRegister")
    tags = [c[1].split("/")[-1] if c[1] != "-c" else "-c" for c in cmds]
    assert tags.count("measure_ground_luma.py") == 2
    assert tags.count("-c") == 1
    spot = cmds[tags.index("-c")]
    assert "record_spot(['SomeRegister'])" in spot[2]
    luma_idx = [i for i, t in enumerate(tags) if t == "measure_ground_luma.py"]
    assert max(luma_idx) < tags.index("-c") < tags.index("register_energy.py")
