"""scripts/workshop.py — the one door into a film's workshop: its layout, its generated index, the environment
every film-scoped render runs with, and the checks built code must pass before it is rendered."""
import json
import os
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
from test_workshop_bundle import _index, SHOT, OBJECT  # noqa: E402  (the one index format)

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _film(tmp_path, shots=(), objects=(), shot_src=SHOT, obj_src=OBJECT, name="film"):
    out = tmp_path / name
    for kind, names, src in (("shots", shots, shot_src), ("objects", objects, obj_src)):
        d = out / "workshop" / kind
        d.mkdir(parents=True, exist_ok=True)
        for n in names:
            (d / (n + ".tsx")).write_text(src % {"name": n}, encoding="utf-8")
    out.mkdir(exist_ok=True)
    return str(out)


def _stub_render(monkeypatch):
    """Stub subprocess.run for a test that needs still() to "succeed" without a real render: a `still`-shaped
    argv ([…, 'still', 'src/index.ts', comp, png, …]) creates the target png so the "did it render" check
    passes; any other call (e.g. typecheck's tsc) runs for real."""
    real_run = ws.subprocess.run

    def fake(cmd, **kwargs):
        if isinstance(cmd, list) and "still" in cmd:
            i = cmd.index("still")
            with open(cmd[i + 3], "wb") as fh:
                fh.write(b"stub")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(ws.subprocess, "run", fake)


def _stills_payload(out, name):
    p = os.path.join(out, "workshop", "_stills", name + ".props.json")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def test_a_film_without_a_workshop_changes_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("SLIDES_WORKSHOP", raising=False)
    out = _film(tmp_path)
    assert ws.prepare(out) is None and ws.run_kwargs(out) == {}


def test_an_inherited_workshop_never_leaks_into_another_film(tmp_path, monkeypatch):
    monkeypatch.setenv("SLIDES_WORKSHOP", "/some/other/film/workshop")
    env = ws.prepare(_film(tmp_path))
    assert env is not None and "SLIDES_WORKSHOP" not in env and env.get("PATH") == os.environ.get("PATH")


def test_prepare_makes_the_workshop_path_absolute(tmp_path, monkeypatch):
    """Review focus: the CLI runs with cwd=remotion/, where a relative path names a different folder."""
    _film(tmp_path, shots=["WsShotA"])
    monkeypatch.chdir(tmp_path)
    env = ws.prepare("film")
    assert env["SLIDES_WORKSHOP"] == os.path.join(str(tmp_path), "film", "workshop")
    assert os.path.isabs(env["SLIDES_WORKSHOP"])


def test_the_index_is_generated_from_the_folders_in_the_one_format(tmp_path):
    out = _film(tmp_path, shots=["WsShotB", "WsShotA"], objects=["WsDisc"])
    path = ws.write_index(out)
    assert open(path, encoding="utf-8").read() == _index(["WsShotA", "WsShotB"], ["WsDisc"])
    mtime = os.path.getmtime(path)
    ws.write_index(out)                                   # unchanged names: the file is not rewritten
    assert os.path.getmtime(path) == mtime


def test_a_bad_layout_is_refused_before_an_index_is_written(tmp_path):
    out = _film(tmp_path, shots=["TermTable"])
    with pytest.raises(ws.WorkshopError) as e:
        ws.write_index(out)
    assert any("already a library register" in p for p in e.value.problems)
    assert not os.path.exists(os.path.join(out, "workshop", "index.ts"))


@pytest.mark.parametrize("files,expect", [
    ({"shots/bad_name.tsx": SHOT % {"name": "bad_name"}}, "PascalCase"),
    ({"shots/WsX.tsx": SHOT % {"name": "WsX"}, "objects/WsX.tsx": OBJECT % {"name": "WsX"}}, "both a shot and an object"),
    ({"stuff/a.txt": "x"}, "objects/, shots/, assets/ and html/ only"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("export const DURATION = 30;\n", "")}, "DURATION"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("export const GROUND = 'bg';\n", "")}, "GROUND"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("'bg'", "'paper'")}, "not a DNA ground token"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("'bg'", "'bgGrad'")}, "no single luminance"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("'motion-graphics'", "''")}, "PROVENANCE"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("export const WsX", "export const Other")}, "export const WsX"),
    ({"objects/WsX.tsx": (OBJECT % {"name": "WsX"}).replace("export const META: ObjectMeta = {aspect: 1, provenance: 'motion-graphics'};\n", "")}, "META"),
    ({"objects/WsX.tsx": (OBJECT % {"name": "WsX"}).replace("'motion-graphics'", "'underwater'")}, "not one of"),
    ({"objects/WsX.tsx": (OBJECT % {"name": "WsX"}).replace("aspect: 1,", "aspect: 1, demo: true,")}, "`demo`"),
    ({"objects/WsX.tsx": "// @scaffold — replace\n" + OBJECT % {"name": "WsX"}}, "still the scaffold"),
    ({"objects/notes.md": "x"}, "only .tsx items and .ts helpers"),
])
def test_names_problems_say_what_is_wrong(tmp_path, files, expect):
    out = tmp_path / "film"
    for rel, text in files.items():
        p = out / "workshop" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    probs = ws.names_problems(str(out))
    assert any(expect in p for p in probs), probs


def test_a_clean_layout_has_no_names_problems(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    (tmp_path / "film" / "workshop" / "objects" / "discGeometry.ts").write_text("export const R = 1;\n")
    (tmp_path / "film" / "workshop" / "assets").mkdir()
    assert ws.names_problems(out) == []


@pytest.mark.parametrize("name", ["Film", "FontProbe"])
def test_a_name_taken_by_a_root_composition_is_a_blocking_problem(tmp_path, name):
    """Root.tsx registers `Film` and `StageProbe` as `id="…"` Composition attributes, and `TypeSpecimen`,
    `FontProbe` and the other `*Probe` ids as `{F('<Id>', …)}` rows — none of them a file in src/shots/ or
    src/objects/, so library_shot_names()/library_object_names() cannot see a workshop name collide with one.
    Unrefused, that collision would hit Remotion's generic duplicate-composition error instead of a specific
    one. It must block the index the same way a shadowed library name does."""
    out = _film(tmp_path, shots=[name])
    probs = ws.names_problems(out)
    assert any("already a library composition" in p for p in probs), probs
    assert any("already a library composition" in p for p in ws.index_blockers(out)), ws.index_blockers(out)


def test_a_name_that_is_both_a_library_register_and_a_composition_id_gets_one_message(tmp_path):
    """TermTable is a real library shot file AND a {F('TermTable', …)} row in Root.tsx — the composition-id
    check must not fire independently of the library check and report the same clash twice."""
    out = _film(tmp_path, shots=["TermTable"])
    probs = [p for p in ws.names_problems(out) if "TermTable" in p and "already a library" in p]
    assert len(probs) == 1, probs
    assert "already a library register" in probs[0], probs


def test_composition_ids_are_read_across_line_breaks_and_from_still_elements(tmp_path, monkeypatch):
    """id="…" is not always on the same line as `<Composition`/`<Still` — and a `<Still>` element (a real
    Remotion component, not used in this file today) must be recognised too."""
    fake_root = tmp_path / "FakeRoot.tsx"
    fake_root.write_text(
        "export const RemotionRoot = () => (\n"
        "  <>\n"
        "    <Composition\n"
        "      id=\"Film\"\n"
        "      component={X} />\n"
        "    <Still\n"
        "      id=\"MultiLineStill\"\n"
        "      component={Y} />\n"
        "  </>\n"
        ");\n", encoding="utf-8")
    monkeypatch.setattr(ws, "ROOT_TSX", str(fake_root))
    ids = ws._root_composition_ids()
    assert ids == {"Film", "MultiLineStill"}, ids


def test_a_root_that_no_longer_lists_film_raises_loudly(tmp_path, monkeypatch):
    """If Root.tsx's own format changes in a way this parser doesn't understand, it must say so loudly rather
    than silently return an incomplete set that then under-refuses forever."""
    fake_root = tmp_path / "FakeRoot.tsx"
    fake_root.write_text("export const RemotionRoot = () => <Composition id=\"SomethingElse\" />;\n",
                          encoding="utf-8")
    monkeypatch.setattr(ws, "ROOT_TSX", str(fake_root))
    with pytest.raises(RuntimeError, match="Film"):
        ws._root_composition_ids()


def test_scaffold_refuses_a_name_taken_by_a_root_composition_before_writing(tmp_path):
    """scaffold() must share _problems()'s composition-id check, not only PascalCase/library-name — otherwise
    scaffold(out, "shot", "Film", …) writes a file every later check (and every later scaffold/new-shot call)
    would then refuse."""
    out = str(tmp_path / "film")
    with pytest.raises(ws.WorkshopError) as e:
        ws.scaffold(out, "shot", "Film", "a test")
    assert any("already a library composition" in p for p in e.value.problems), e.value.problems
    assert not os.path.exists(os.path.join(out, "workshop", "shots", "Film.tsx"))


def test_imports_are_held_to_react_remotion_the_runtime_the_library_and_the_workshop(tmp_path):
    out = _film(tmp_path, objects=["WsDisc"])
    bad = tmp_path / "film" / "workshop" / "objects" / "WsBad.tsx"
    bad.write_text("import x from 'lodash';\nimport {a} from '@runtime/nope';\nimport {B} from '@shots/Nope';\n"
                   "import {c} from '../../../outside';\nimport {d} from './missing';\n", encoding="utf-8")
    good = tmp_path / "film" / "workshop" / "objects" / "WsGood.tsx"
    good.write_text("import React from 'react';\nimport {useCurrentFrame} from 'remotion';\n"
                    "import {seg} from '@runtime/motion';\nimport {TermTable} from '@shots/TermTable';\n"
                    "import {R} from './discGeometry';\n", encoding="utf-8")
    (tmp_path / "film" / "workshop" / "objects" / "discGeometry.ts").write_text("export const R = 1;\n")
    probs = ws.import_problems(out, [str(bad), str(good)])
    for needle in ("'lodash'", "@runtime/nope", "@shots/Nope", "outside the film's workshop", "does not exist"):
        assert any(needle in p for p in probs), (needle, probs)
    assert not [p for p in probs if "WsGood" in p], probs


def test_a_film_folder_with_glob_metacharacters_still_sees_its_own_shot(tmp_path):
    """A film folder listing must treat the folder's own name as a literal path, not a glob pattern — in a
    folder named with `[...]`, a bracket expression that matches nothing on disk would otherwise make
    shot_names() (and _tsx_names underneath it) come back empty, so a real shot on disk goes invisible and
    `check` reports a false CLEAN."""
    out = _film(tmp_path, shots=["WsShotA"], name="film [v2]")
    assert ws.shot_names(out) == {"WsShotA"}
    assert ws.names_problems(out) == []
    bad = _film(tmp_path, shots=["TermTable"], name="bad [v2]")
    assert any("already a library register" in p for p in ws.names_problems(bad))


def test_a_film_folder_with_a_star_never_sees_a_sibling_films_shots(tmp_path):
    """A wildcard in the FOLDER name (e.g. a literal `*`) must never widen a listing to match a sibling film's
    directory too."""
    a = _film(tmp_path, shots=["WsShotA"], name="film*")
    _film(tmp_path, shots=["WsShotB"], name="filmXYZ")
    assert ws.shot_names(a) == {"WsShotA"}


def test_import_problems_resolves_relative_files_given_as_relative_paths(tmp_path, monkeypatch):
    """import_problems computes `target` from `os.path.dirname(f)`, which stays relative when `f` is relative,
    then compares it against workshop_dir()'s always-ABSOLUTE path — a relative-path caller must not lose that
    comparison and see a legitimate `./helper` import wrongly reported as outside the workshop."""
    out = _film(tmp_path, objects=["WsDisc"])
    (tmp_path / "film" / "workshop" / "objects" / "helper.ts").write_text("export const R = 1;\n", encoding="utf-8")
    f = tmp_path / "film" / "workshop" / "objects" / "WsUsesHelper.tsx"
    f.write_text("import {R} from './helper';\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rel_f = os.path.relpath(str(f), str(tmp_path))
    assert not os.path.isabs(rel_f)
    probs = ws.import_problems(out, [rel_f])
    assert not [p for p in probs if "outside the film's workshop" in p], probs


def test_source_files_finds_ts_helpers_at_any_depth(tmp_path):
    """source_files must use the SAME recursive traversal code_files does, or a helper module organised into a
    subfolder is hashed for the cache key but never import/contract/baked-words checked."""
    out = _film(tmp_path, objects=["WsDisc"])
    nested = tmp_path / "film" / "workshop" / "objects" / "lib"
    nested.mkdir()
    (nested / "geometry.ts").write_text("export const R = 1;\n", encoding="utf-8")
    files = ws.source_files(out)
    assert any(os.path.basename(f) == "geometry.ts" for f in files), files


def test_a_relative_import_must_resolve_inside_objects_shots_or_assets(tmp_path):
    """A relative import that resolves to the workshop ROOT (not objects/, shots/ or assets/) edits a file
    code_files() never hashes — the segment cache key would not change even though the imported code did."""
    out = _film(tmp_path, objects=["WsDisc"])
    (tmp_path / "film" / "workshop" / "helper.ts").write_text("export const R = 1;\n", encoding="utf-8")
    bad = tmp_path / "film" / "workshop" / "objects" / "WsRoot.tsx"
    bad.write_text("import {R} from '../helper';\n", encoding="utf-8")
    probs = ws.import_problems(out, [str(bad)])
    assert any("objects/, shots/ or assets/" in p for p in probs), probs


def test_contract_findings_are_reported_with_the_file_and_line(tmp_path):
    out = _film(tmp_path, objects=["WsDisc"])
    f = tmp_path / "film" / "workshop" / "objects" / "WsDisc.tsx"
    f.write_text(f.read_text() + "export const firstThree = (xs: string[]) => xs.slice(0, 3);\n", encoding="utf-8")
    probs = ws.contract_problems(out, [str(f)])
    assert any("WsDisc.tsx:" in p and "[truncate]" in p for p in probs), probs


def test_the_contract_message_declares_a_tag_the_checker_actually_accepts(tmp_path):
    """content_contract_qa._declared only accepts content_contract_qa._DECL[rule] (`truncate` -> the tag
    `truncates`, plural) — the message must print that tag, not `rule` itself, or an author who types exactly
    what it says (`// @truncate: <why>`) finds the violation still there."""
    import re as _re
    out = _film(tmp_path, objects=["WsDisc"])
    f = tmp_path / "film" / "workshop" / "objects" / "WsDisc.tsx"
    base = f.read_text()
    line = "export const firstThree = (xs: string[]) => xs.slice(0, 3);\n"
    f.write_text(base + line, encoding="utf-8")
    probs = ws.contract_problems(out, [str(f)])
    msg = next(p for p in probs if "[truncate]" in p)
    m = _re.search(r"declare `// @(\w+): <why>`", msg)
    assert m, msg
    f.write_text(base + ("// @%s: a fixed preview window, not a claim\n" % m.group(1)) + line, encoding="utf-8")
    probs2 = ws.contract_problems(out, [str(f)])
    assert not [p for p in probs2 if "[truncate]" in p], probs2


_WORDS_BAD = """import React from 'react';
export const WsWords: React.FC<{v?: number; mode?: 'fill' | 'stroke'; label?: string}> =
  ({v = 0, mode = 'fill', label = 'hand written label'}) => (
  <div className="box" style={{textAlign: 'center', fontFamily: 'Inter'}}>
    <span>Pressure</span>
    <span>{'Flow rate'}</span>
    <span>{v > 1 ? 'high' : 'low'}</span>
    <span>{`压力 ${v}`}</span>
    <Chip title="Grinder" />
    <span>&nbsp;&nbsp;</span>
  </div>
);
const Chip: React.FC<{title: string}> = ({title}) => <b>{title}</b>;
const UNIT = '毫升';
"""

_WORDS_GOOD = """import React from 'react';
export const WsQuiet: React.FC<{label?: string; unit?: string; mode?: 'fill' | 'stroke'}> =
  ({label = '', unit = '', mode = 'fill'}) => (
  <div className="box" style={{textAlign: 'center', fontFamily: 'Inter, sans-serif', position: 'absolute'}}>
    <span>{label}</span>
    {/* a comment is not drawn */}
    <span>{mode === 'fill' ? label : unit}</span>
    <span>&nbsp;&nbsp;·&nbsp;&nbsp;</span>
    {/* @fixed-text: the SI symbol for the quantity the film names */}
    <span>bar</span>
  </div>
);
"""


@needs_toolchain
def test_the_baked_words_scan_catches_each_way_words_get_written_in(tmp_path):
    bad = tmp_path / "WsWords.tsx"
    bad.write_text(_WORDS_BAD, encoding="utf-8")
    got = ws.baked_words(str(tmp_path), [str(bad)])
    text = "\n".join(got["problems"])
    for word in ("Pressure", "Flow rate", "high", "low", "压力", "Grinder", "hand written label", "毫升"):
        assert word in text, (word, text)
    assert "nbsp" not in text and "Inter" not in text and "'fill'" not in text, text


@needs_toolchain
def test_the_baked_words_scan_leaves_honest_code_alone_and_reports_what_was_declared(tmp_path):
    good = tmp_path / "WsQuiet.tsx"
    good.write_text(_WORDS_GOOD, encoding="utf-8")
    got = ws.baked_words(str(tmp_path), [str(good)])
    assert got["problems"] == [], got
    assert "bar" in got["declared"], got


@needs_toolchain
def test_the_scan_on_the_library_finds_real_words_only():
    """Calibration, re-run: every hit on the library is a word a viewer would read (a demo default, an intrinsic
    label) — never an entity-only run, a CSS keyword or an import path. The library is ALLOWED these; the point
    is that the scanner's rules only fire on words."""
    import glob
    import re
    files = sorted(glob.glob(os.path.join(_REM, "src", "shots", "*.tsx")))
    got = ws.baked_words(_ROOT, files)
    assert len(got["problems"]) > 100, len(got["problems"])
    words = [re.search(r"\): (.+) — every word", p).group(1) for p in got["problems"]]
    assert not [w for w in words if "nbsp" in w or "&lt;" in w or w.startswith(("'./", "'../", "'@"))], words
    assert all(re.search(r"[^\W\d_]", w) for w in words), [w for w in words if not re.search(r"[^\W\d_]", w)]


@needs_toolchain
def test_the_typecheck_catches_a_type_error_and_passes_clean_code(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    assert ws.typecheck(out) == []
    f = tmp_path / "film" / "workshop" / "objects" / "WsDisc.tsx"
    f.write_text(f.read_text() + "export const oops = (n: number) => n.toFixed('x');\n", encoding="utf-8")
    probs = ws.typecheck(out)
    assert probs and "type error" in probs[0] and "WsDisc.tsx" in probs[0], probs


@needs_toolchain
def test_the_typecheck_runs_in_a_folder_with_spaces(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], name="my film")
    assert ws.typecheck(out) == []


@needs_toolchain
def test_check_is_empty_for_a_clean_workshop(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    assert ws.check(out) == []


def test_code_files_hash_the_sources_and_leave_out_what_is_generated(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    ws.write_index(out)
    root = tmp_path / "film" / "workshop"
    (root / "assets").mkdir()
    (root / "assets" / "grain.png").write_bytes(b"x")
    (root / "_stills").mkdir()
    (root / "_stills" / "WsDisc.png").write_bytes(b"x")
    (root / ".tsconfig.json").write_text("{}")
    names = sorted(os.path.relpath(p, str(root)) for p in ws.code_files(out))
    assert names == ["assets/grain.png", "objects/WsDisc.tsx", "shots/WsShotA.tsx"], names


def test_durations_grounds_and_provenances_are_read_from_the_sources(tmp_path):
    shot = (SHOT % {"name": "WsShotA"}).replace("= 30;", "= 180;").replace("'bg'", "['accent', 'accent2']")
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"], shot_src=shot.replace("%", "%%"))
    assert ws.durations(out) == {"WsShotA": 180}
    assert ws.grounds(out) == {"WsShotA": ["accent", "accent2"]}
    assert ws.provenances(out) == {"WsShotA": "motion-graphics", "WsDisc": "motion-graphics"}


@pytest.mark.parametrize("decl,ok,frames", [
    ("export const DURATION = 6 * 30;", False, None),          # an expression is not a frame count
    ("export const DURATION = 150.5;", False, None),           # a decimal is not a whole number of frames
    ("export const DURATION = 0;", False, None),                # zero is not a positive frame count
    ("export const DURATION: number = 150;", True, 150),        # a type-annotated declaration is valid TS
])
def test_duration_is_read_by_one_anchored_parser(tmp_path, decl, ok, frames):
    shot = (SHOT % {"name": "WsDur"}).replace("export const DURATION = 30;", decl)
    out = _film(tmp_path, shots=["WsDur"], shot_src=shot.replace("%", "%%"))
    probs = [p for p in ws.names_problems(out) if "DURATION" in p]
    if ok:
        assert probs == [], probs
        assert ws.durations(out) == {"WsDur": frames}
        assert ws.index_blockers(out) == []
    else:
        assert probs and "export const DURATION = <frames>;" in probs[0], probs
        assert "WsDur" not in ws.durations(out)
        assert any("export const DURATION = <frames>;" in p for p in ws.index_blockers(out))


def test_a_commented_out_duration_never_wins(tmp_path):
    shot = (SHOT % {"name": "WsDur"}).replace(
        "export const DURATION = 30;", "// export const DURATION = 999;\nexport const DURATION = 45;")
    out = _film(tmp_path, shots=["WsDur"], shot_src=shot.replace("%", "%%"))
    assert ws.durations(out) == {"WsDur": 45}
    assert not [p for p in ws.names_problems(out) if "DURATION" in p]


def test_still_on_a_shot_with_a_bad_duration_is_a_sentence_not_a_keyerror(tmp_path, monkeypatch):
    """Proven by making a render attempt itself fail the test: still() must refuse BEFORE ever invoking
    subprocess.run, not rely on the render failing for an unrelated reason and getting wrapped anyway."""
    shot = (SHOT % {"name": "WsDur"}).replace("export const DURATION = 30;", "export const DURATION = 0;")
    out = _film(tmp_path, shots=["WsDur"], shot_src=shot.replace("%", "%%"))

    def _no_render(*a, **k):
        raise AssertionError("still() must refuse a bad DURATION before ever invoking a render")

    monkeypatch.setattr(ws.subprocess, "run", _no_render)
    with pytest.raises(ws.WorkshopError) as e:
        ws.still(out, "WsDur")
    assert any("DURATION" in p for p in e.value.problems), e.value.problems


def test_still_on_an_object_with_a_bad_host_duration_is_a_sentence_too(tmp_path, monkeypatch):
    """still()'s object branch resolves the slot and builds `payload` BEFORE calling
    `_required_duration(src, host)`, and that call happens before run_kwargs()/write_index() are ever reached
    (those are only invoked later, inside the subprocess.run() call at the bottom of still()) — so the error
    comes from still()'s OWN `_required_duration(src, host)` line, naming the BARE host ("WsBadHost: DURATION
    must be …"), not a workshop/shots/WsBadHost.tsx: file path (what _problems()/names_problems() would print
    instead). This is also the only path that reaches the host-is-a-LIBRARY-register case, which _problems()
    never sees at all (it only scans the WORKSHOP's own files) — one parser, reached from two call sites."""
    _stub_render(monkeypatch)
    shot = (SHOT % {"name": "WsBadHost"}).replace("export const DURATION = 30;", "export const DURATION = 0;")
    out = _film(tmp_path, shots=["WsBadHost"], objects=["WsDisc"], shot_src=shot.replace("%", "%%"))
    with pytest.raises(ws.WorkshopError) as e:
        ws.still(out, "WsDisc", host="WsBadHost")
    assert any("DURATION" in p for p in e.value.problems), e.value.problems


# Synthetic hosts, not any particular library register: these prove the general mechanism — still() reads the
# host's ACTUAL top-level ObjectRef slot name, never hard-codes "object".
_HOST_ART_SLOT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ObjectSlot, type ObjectRef} from '@runtime/objectSlot';
export const DURATION = 30;
export const GROUND = 'bg';
export const PROVENANCE = 'motion-graphics';
export const %(name)s: React.FC<{caption?: string; art?: ObjectRef}> = ({caption = '', art}) => (
  <AbsoluteFill style={{background: '#000000'}}>
    {art ? <ObjectSlot object={art} box={{x: 660, y: 240, w: 600, h: 600}} /> : null}
  </AbsoluteFill>
);
"""

_HOST_TWO_SLOTS = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ObjectSlot, type ObjectRef} from '@runtime/objectSlot';
export const DURATION = 30;
export const GROUND = 'bg';
export const PROVENANCE = 'motion-graphics';
export const %(name)s: React.FC<{first?: ObjectRef; second?: ObjectRef}> = ({first, second}) => (
  <AbsoluteFill style={{background: '#000000'}}>
    {first ? <ObjectSlot object={first} box={{x: 0, y: 0, w: 400, h: 400}} /> : null}
    {second ? <ObjectSlot object={second} box={{x: 800, y: 0, w: 400, h: 400}} /> : null}
  </AbsoluteFill>
);
"""

# A device-shaped host: its only ObjectRef is NESTED (steps[i].screen.object), never a top-level prop of the
# host's own React.FC<{...}> literal — `ScreenSrc` is a SEPARATE `type` alias, textually outside that literal.
_HOST_NESTED_SLOT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ObjectSlot, type ObjectRef} from '@runtime/objectSlot';
export const DURATION = 30;
export const GROUND = 'bg';
export const PROVENANCE = 'motion-graphics';
type ScreenSrc = {object?: ObjectRef};
export const %(name)s: React.FC<{steps?: {screen?: ScreenSrc}[]}> = ({steps = []}) => (
  <AbsoluteFill style={{background: '#000000'}}>
    {steps[0]?.screen?.object
      ? <ObjectSlot object={steps[0].screen.object} box={{x: 0, y: 0, w: 400, h: 400}} /> : null}
  </AbsoluteFill>
);
"""

# A HELPER component declared before the host's own export — some library registers do this (e.g.
# DeviceDemo.tsx's own `DemoPage` helper, declared before `export const DeviceDemo`).
_HOST_HELPER_BEFORE_EXPORT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ObjectSlot, type ObjectRef} from '@runtime/objectSlot';
export const DURATION = 30;
export const GROUND = 'bg';
export const PROVENANCE = 'motion-graphics';
const Helper: React.FC<{art?: ObjectRef}> = ({art}) => (
  <AbsoluteFill style={{background: '#111111'}}>
    {art ? <ObjectSlot object={art} box={{x: 0, y: 0, w: 200, h: 200}} /> : null}
  </AbsoluteFill>
);
export const %(name)s: React.FC<{title?: string; object?: ObjectRef}> = ({title = '', object}) => (
  <AbsoluteFill style={{background: '#000000'}}>
    <Helper />
    {object ? <ObjectSlot object={object} box={{x: 660, y: 240, w: 600, h: 600}} /> : null}
  </AbsoluteFill>
);
"""


def test_still_refuses_a_host_with_no_object_slot_of_its_own(tmp_path, monkeypatch):
    """The real, unmodified TermTable register — no film has ever been able to give it an object."""
    _stub_render(monkeypatch)
    out = _film(tmp_path, objects=["WsDisc"])
    with pytest.raises(ws.WorkshopError) as e:
        ws.still(out, "WsDisc", host="TermTable")
    assert any("no object slot of its own" in p for p in e.value.problems), e.value.problems


def test_still_puts_the_object_under_the_hosts_own_top_level_slot(tmp_path, monkeypatch):
    _stub_render(monkeypatch)
    out = _film(tmp_path, shots=["WsArtHost"], objects=["WsDisc"], shot_src=_HOST_ART_SLOT)
    ws.still(out, "WsDisc", host="WsArtHost")
    payload = _stills_payload(out, "WsDisc")
    assert payload == {"art": {"id": "WsDisc"}}, payload


def test_still_anchors_on_the_hosts_own_export_not_a_helper_declared_first(tmp_path, monkeypatch):
    """The top-level slot scan must anchor on the HOST's own export, not the first `React.FC<{` literal in the
    file — a helper component's own props literal, declared before the host's export, must not be read
    instead. The object must land under the EXPORT's own `object` slot, not the helper's `art`."""
    _stub_render(monkeypatch)
    out = _film(tmp_path, shots=["WsHost"], objects=["WsDisc"], shot_src=_HOST_HELPER_BEFORE_EXPORT)
    ws.still(out, "WsDisc", host="WsHost")
    payload = _stills_payload(out, "WsDisc")
    assert payload == {"object": {"id": "WsDisc"}}, payload


def test_top_level_scan_on_the_real_devicedemo_finds_its_own_injected_slot():
    """remotion/src/shots/DeviceDemo.tsx declares a helper (`DemoPage`) before its export. Injecting
    `object?: ObjectRef` into DeviceDemo's OWN top-level props literal (read from the real file, never written
    back to it) must be found there — not in DemoPage's, and not under DemoPage's own (non-existent) export
    name."""
    path = os.path.join(_REM, "src", "shots", "DeviceDemo.tsx")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    marker = "export const DeviceDemo: React.FC<{\n"
    assert marker in src, "DeviceDemo.tsx's own export literal no longer opens this way — update the fixture"
    injected = src.replace(marker, marker + "  object?: ObjectRef;\n", 1)
    assert "object" in ws._top_level_object_ref_keys(injected, "DeviceDemo")
    assert ws._top_level_object_ref_keys(injected, "DemoPage") == []   # not exported — no slot to find


def test_still_with_several_top_level_slots_needs_slot(tmp_path, monkeypatch):
    _stub_render(monkeypatch)
    out = _film(tmp_path, shots=["WsTwoSlots"], objects=["WsDisc"], shot_src=_HOST_TWO_SLOTS)
    with pytest.raises(ws.WorkshopError) as e:
        ws.still(out, "WsDisc", host="WsTwoSlots")
    assert any("first, second" in p and "--slot" in p for p in e.value.problems), e.value.problems
    ws.still(out, "WsDisc", host="WsTwoSlots", slot="second")
    payload = _stills_payload(out, "WsDisc")
    assert payload == {"second": {"id": "WsDisc"}}, payload


def test_still_refuses_a_slot_name_that_is_not_a_top_level_slot(tmp_path, monkeypatch):
    _stub_render(monkeypatch)
    out = _film(tmp_path, shots=["WsTwoSlots"], objects=["WsDisc"], shot_src=_HOST_TWO_SLOTS)
    with pytest.raises(ws.WorkshopError) as e:
        ws.still(out, "WsDisc", host="WsTwoSlots", slot="nope")
    assert any("nope" in p and "first" in p and "second" in p for p in e.value.problems), e.value.problems


def test_still_with_only_a_nested_slot_needs_props_to_place_it(tmp_path, monkeypatch):
    _stub_render(monkeypatch)
    out = _film(tmp_path, shots=["WsNested"], objects=["WsDisc"], shot_src=_HOST_NESTED_SLOT)
    with pytest.raises(ws.WorkshopError) as e:
        ws.still(out, "WsDisc", host="WsNested")
    assert any("no object slot of its own" in p for p in e.value.problems), e.value.problems
    given = {"steps": [{"screen": {"object": {"id": "WsDisc"}}}]}
    ws.still(out, "WsDisc", host="WsNested", props=given)
    payload = _stills_payload(out, "WsDisc")
    assert payload == given, payload


def test_ground_and_provenance_are_read_from_comment_stripped_source(tmp_path):
    shot = (SHOT % {"name": "WsCS"}).replace(
        "export const GROUND = 'bg';", "// export const GROUND = 'accent';\nexport const GROUND = 'surface';"
    ).replace(
        "export const PROVENANCE = 'motion-graphics';",
        "// export const PROVENANCE = 'natural-world';\nexport const PROVENANCE = 'motion-graphics';")
    out = _film(tmp_path, shots=["WsCS"], shot_src=shot.replace("%", "%%"))
    assert ws.grounds(out) == {"WsCS": "surface"}
    assert ws.provenances(out) == {"WsCS": "motion-graphics"}


def test_the_export_const_name_check_ignores_a_commented_out_stray(tmp_path):
    """Only a COMMENT still claims the real name; the live export was renamed away."""
    shot = "// export const WsCS2 = () => null; (an old export, left as a comment)\n" + \
        (SHOT % {"name": "WsCS2"}).replace("export const WsCS2", "export const NotTheRealOne")
    out = _film(tmp_path, shots=["WsCS2"], shot_src=shot.replace("%", "%%"))
    probs = ws.names_problems(out)
    assert any("export the component as `export const WsCS2`" in p for p in probs), probs


def test_the_scaffold_marker_is_still_found_after_stripping_elsewhere(tmp_path):
    """The marker itself IS a comment (`// @scaffold …`) — comment-stripping the OTHER declarations must not
    strip the one check that reads it."""
    out = str(tmp_path / "film")
    ws.scaffold(out, "shot", "WsFresh", "a fresh scaffold")
    assert any("still the scaffold" in p for p in ws.names_problems(out))


@pytest.mark.parametrize("suffix", ["", " satisfies ObjectMeta", " as const", " satisfies ObjectMeta as const"])
def test_object_meta_tolerates_missing_semicolon_and_trailing_assertions(suffix):
    src = ("export const META: ObjectMeta = {aspect: 1, provenance: 'motion-graphics'}%s\n"
           "export const X = 1;\n") % suffix
    meta = ws.object_meta(src)
    assert meta == {"aspect": 1.0, "provenance": "motion-graphics"}, (suffix, meta)


@pytest.mark.parametrize("bad_aspect", ["1.2.3", "16 / 0"])
def test_object_meta_never_raises_on_a_malformed_aspect(tmp_path, bad_aspect):
    """`float('1.2.3')` raises ValueError, `float('16') / float('0')` raises ZeroDivisionError — object_meta
    must catch both and report a None aspect for names_problems/check to flag, not crash its caller."""
    src = (OBJECT % {"name": "WsBadAspect"}).replace("aspect: 1,", "aspect: %s," % bad_aspect)
    meta = ws.object_meta(src)   # must not raise
    assert meta is not None and meta.get("aspect") is None, (bad_aspect, meta)
    out = _film(tmp_path, objects=["WsBadAspect"], obj_src=src.replace("%", "%%"))
    probs = ws.names_problems(out)
    assert any("aspect" in p.lower() for p in probs), probs


def test_object_refs_are_found_under_every_key_the_register_types_objectref():
    src = ("type ScreenSrc = {image?: string; object?: ObjectRef};\n"
           "export const X: React.FC<{steps?: {screen?: ScreenSrc}[]; art?: ObjectRef; object?: string}> = () => null;")
    props = {"object": "a caption, not a ref", "art": {"id": "Puck"},
             "steps": [{"screen": {"object": {"id": "Phone"}}}, {"tap": [0.5, 0.5]}]}
    assert sorted(ws.object_refs(src, props)) == [("art", {"id": "Puck"}), ("steps[0].screen.object", {"id": "Phone"})]
    assert ws.slot_keys("// object?: ObjectRef in a comment\n") == set()


def test_an_unambiguous_key_still_hand_validates_a_malformed_value(tmp_path):
    """A name the source ONLY EVER types ObjectRef must still hand back a malformed value (a plain string,
    not a ref object) under it, not silently drop it — validate.py's own build check needs to see it and
    report it; the render is still the last word regardless."""
    src = "export const X: React.FC<{art?: ObjectRef}> = () => null;"
    assert ws.object_refs(src, {"art": "Puck"}) == [("art", "Puck")]


def test_slot_keys_ignores_a_const_declaration(tmp_path):
    """A later stage register's own standalone-preview constant (`const DEMO_OBJECT: ObjectRef = …`) is a
    variable, not a prop a beat can set — slot_keys() must not treat its name as a slot."""
    src = "const DEMO_OBJECT: ObjectRef = {id: 'X'};\nexport const Y: React.FC<{}> = () => null;"
    assert "DEMO_OBJECT" not in ws.slot_keys(src)
    src2 = "let DEMO_OBJECT: ObjectRef = {id: 'X'};\nexport const Y: React.FC<{}> = () => null;"
    assert "DEMO_OBJECT" not in ws.slot_keys(src2)


def test_an_ambiguous_top_level_field_is_excluded_while_a_nested_one_is_found():
    """A second witness next to test_object_refs_are_found_under_every_key_the_register_types_objectref: a
    field typed differently at the top level (a caption) than in a nested type (an ObjectRef) must exclude
    the top-level value while still finding the nested one."""
    src = ("type ScreenSrc = {image?: string; object?: ObjectRef};\n"
           "export const X: React.FC<{steps?: {screen?: ScreenSrc}[]; art?: ObjectRef; object?: string}> = "
           "() => null;")
    props = {"object": "a caption, not a ref", "art": {"id": "Puck"},
             "steps": [{"screen": {"object": {"id": "Phone"}}}, {"tap": [0.5, 0.5]}]}
    assert sorted(ws.object_refs(src, props)) == [("art", {"id": "Puck"}), ("steps[0].screen.object", {"id": "Phone"})]


def test_a_destructuring_rename_does_not_hide_a_top_level_object_slot():
    """A register that destructures its own top-level ObjectRef prop under a local name (`object: OBJECT`,
    HudReticle's own style) reads, by NAME alone, as the same field typed twice — once `ObjectRef` in its
    declaration, once whatever follows the colon in the rename — which is the shape `_ambiguous_slot_keys`
    reads as "typed otherwise elsewhere" and excludes: validate.py's own build check never saw a malformed
    `"object": "a caption"` because of it. Named by its host, the TOP-LEVEL scan of the real declaration
    overrules that false ambiguity; without a host name the old exclusion still applies, and a NESTED
    occurrence of the same name keeps it regardless (test_an_ambiguous_top_level_field_is_excluded_while_a_
    nested_one_is_found, unchanged by this)."""
    src = "export const X: React.FC<{object?: ObjectRef}> = ({object: OBJECT}) => null;"
    assert ws.object_refs(src, {"object": "a caption"}) == []
    assert ws.object_refs(src, {"object": "a caption"}, "X") == [("object", "a caption")]


def test_required_in_film_is_read_from_the_register():
    assert ws.required_in_film("export const REQUIRED_IN_FILM = ['object', 'stations'] as const;") == {"object", "stations"}
    assert ws.required_in_film("export const X = 1;") == set()
    # comment-stripped like every other declaration reader: a commented-out line is not a live requirement.
    assert ws.required_in_film("// export const REQUIRED_IN_FILM = ['fill'];\nexport const X = 1;") == set()


def test_uses_maps_each_item_to_the_beats_that_show_it(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    slides = [{"index": 3, "shot": "WsShotA", "shot_props": {"object": {"id": "WsDisc"}}},
              {"index": 4, "shot": "WsShotA"}, {"index": 5, "shot": "TermTable"}]
    got = ws.uses(slides, out)
    assert got["WsShotA"] == [3, 4] and got["WsDisc"] == [3] and got["TermTable"] == [5]


def test_uses_takes_precomputed_refs_instead_of_recomputing_them(tmp_path):
    """A caller that already computed object_refs() per beat (validate.py's build check) passes them here
    rather than have `uses` walk every beat's props a second time — same answer either way."""
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    slides = [{"index": 3, "shot": "WsShotA", "shot_props": {"object": {"id": "WsDisc"}}},
              {"index": 4, "shot": "WsShotA"}, {"index": 5, "shot": "TermTable"}]
    refs = [ws.object_refs(ws.shot_source(out, s.get("shot")), s.get("shot_props") or {}) for s in slides]
    assert ws.uses(slides, out, refs=refs) == ws.uses(slides, out)


def test_scaffolds_are_written_once_and_are_flagged_until_replaced(tmp_path):
    out = str(tmp_path / "film")
    p = ws.scaffold(out, "object", "EspressoPuck", "water forced through a packed bed")
    assert p.endswith(os.path.join("workshop", "objects", "EspressoPuck.tsx"))
    src = open(p, encoding="utf-8").read()
    assert "@scaffold" in src and "water forced through a packed bed" in src and "export const META" in src
    with pytest.raises(ws.WorkshopError):
        ws.scaffold(out, "object", "EspressoPuck", "again")
    with pytest.raises(ws.WorkshopError):
        ws.scaffold(out, "shot", "TermTable", "a library name")
    assert any("still the scaffold" in x for x in ws.names_problems(out))
    s = ws.scaffold(out, "shot", "ExtractionCurve", "how the flow changes over the shot")
    assert "export const DURATION" in open(s, encoding="utf-8").read()


def test_a_work_in_progress_object_can_still_be_rendered(tmp_path):
    """A scaffold still in place, or a provenance not yet named, is reported — but the author can still render the
    object and look at it while drawing it. Only what the index cannot be written around blocks."""
    out = str(tmp_path / "film")
    ws.scaffold(out, "object", "HalfDrawn", "a thing being drawn")
    assert any("still the scaffold" in p for p in ws.names_problems(out))
    assert ws.index_blockers(out) == []
    assert os.path.exists(ws.write_index(out))


def test_write_index_on_a_film_with_no_workshop_at_all_is_a_sentence(tmp_path):
    """write_index() on an out_dir with no workshop/ folder at all must not try to open
    <out_dir>/workshop/index.ts for writing — its parent directory does not exist either, which is a raw
    FileNotFoundError, not a sentence."""
    out = str(tmp_path / "bare")
    os.makedirs(out)
    assert not os.path.isdir(os.path.join(out, "workshop"))
    with pytest.raises(ws.WorkshopError) as e:
        ws.write_index(out)
    assert e.value.problems and "workshop" in e.value.problems[0].lower()


@needs_toolchain
def test_typecheck_on_a_film_with_no_workshop_at_all_is_a_sentence(tmp_path):
    """typecheck() calls write_index() internally, so it must inherit the same graceful sentence."""
    out = str(tmp_path / "bare")
    os.makedirs(out)
    with pytest.raises(ws.WorkshopError) as e:
        ws.typecheck(out)
    assert e.value.problems and "workshop" in e.value.problems[0].lower()


def test_a_missing_props_file_is_a_sentence_not_a_traceback(tmp_path, capsys):
    out = _film(tmp_path, shots=["WsShotA"])
    rc = ws.main([out, "still", "WsShotA", "--props", str(tmp_path / "nope.json")])
    assert rc == 1
    out_text = capsys.readouterr().out
    assert "PROBLEM" in out_text and "nope.json" in out_text


def test_the_next_line_points_at_the_authoring_reference_for_the_kind_just_written(tmp_path, capsys):
    """new-shot and new-object point at different authoring references — a shot's structure and an object's
    drawing are different guides, so new-shot must not print the object guide."""
    out = str(tmp_path / "film")
    ws.main([out, "new-object", "EspressoPuck", "--means", "a compressed espresso puck"])
    assert "object-authoring.md" in capsys.readouterr().out
    ws.main([out, "new-shot", "ExtractionCurve", "--means", "how the flow changes"])
    assert "remotion-shot-authoring.md" in capsys.readouterr().out


def test_grounds_maps_a_shot_with_no_ground_to_none(tmp_path):
    shot = (SHOT % {"name": "WsNoGround"}).replace("export const GROUND = 'bg';\n", "")
    out = _film(tmp_path, shots=["WsNoGround"], shot_src=shot.replace("%", "%%"))
    assert ws.grounds(out) == {"WsNoGround": None}


@needs_toolchain
def test_the_workshop_never_writes_outside_its_folder(tmp_path, monkeypatch):
    """Covers typecheck() (writes .tsconfig.json) and still() (writes _stills/, with subprocess.run stubbed)
    alongside prepare()/scaffold()/names_problems() — every one of a film's own operations, all confined to
    workshop/."""
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    (tmp_path / "film" / "storyboard.json").write_text("{}")
    _stub_render(monkeypatch)
    before = {os.path.join(dp, f) for dp, _dn, fn in os.walk(str(tmp_path)) for f in fn}
    ws.prepare(out)
    ws.scaffold(out, "object", "WsNew", "a new thing")
    ws.names_problems(out)
    ws.typecheck(out)
    ws.still(out, "WsShotA")
    after = {os.path.join(dp, f) for dp, _dn, fn in os.walk(str(tmp_path)) for f in fn}
    new = sorted(os.path.relpath(p, out) for p in after - before)
    assert all(p.startswith("workshop" + os.sep) for p in new), new


def _device_board(out, steps, narration="打开它，点一下开始。", duration=None):
    beat = {"index": 1, "shot": "DeviceDemo", "narration": narration,
            "shot_props": {"device": "phone", "steps": steps}}
    if duration:
        beat["duration"] = duration
    with open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"meta": {"renderer": "remotion", "language": "zh", "aspect": "16:9"}, "slides": [beat]}, fh,
                  ensure_ascii=False)
    return beat


def test_still_on_a_device_host_renders_the_beat_that_shows_the_object(tmp_path, monkeypatch):
    """A screen the film drew is previewed on its device the way the film plays it: DeviceDemo refuses a step
    script nobody prepared, so still() takes the beat that shows the object and prepares it as the film does —
    with no props there is no top-level slot to place it under, and the still used to stop there."""
    _stub_render(monkeypatch)
    out = _film(tmp_path, objects=["WsDisc"])
    _device_board(out, [{"screen": {"object": {"id": "WsDisc"}}}, {"tap": [0.5, 0.9], "at": 0.6}])
    ws.still(out, "WsDisc", host="DeviceDemo")
    steps = _stills_payload(out, "WsDisc")["steps"]
    assert steps[0]["screen"]["object"]["id"] == "WsDisc"
    assert all(k in steps[1] for k in ("t0", "ta", "t1")), steps


def test_still_given_a_device_beats_own_props_prepares_its_cued_script(tmp_path, monkeypatch):
    _stub_render(monkeypatch)
    out = _film(tmp_path, objects=["WsDisc"])
    beat = _device_board(out, [{"screen": {"object": {"id": "WsDisc"}}}, {"tap": [0.5, 0.9], "at": {"cue": "点一下开始"}}],
                         duration=6.0)
    ws.still(out, "WsDisc", host="DeviceDemo", props=beat["shot_props"])
    tap = _stills_payload(out, "WsDisc")["steps"][1]
    assert isinstance(tap["at"], float) and tap["ta"] == tap["at"], tap


def test_still_on_a_device_host_no_beat_shows_names_what_to_pass(tmp_path, monkeypatch):
    _stub_render(monkeypatch)
    out = _film(tmp_path, objects=["WsDisc"])
    _device_board(out, [{"screen": {"image": "screen.png"}}])
    with pytest.raises(ws.WorkshopError) as e:
        ws.still(out, "WsDisc", host="DeviceDemo")
    assert any("no beat" in p and "--props" in p for p in e.value.problems), e.value.problems
