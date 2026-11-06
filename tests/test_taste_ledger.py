"""The skill remembers what the user taught it (spec 2026-11-06 A). Every past design correction — header titles on a
video, one landscape behind a satellite, a red timetable palette for satellites — came from the user and became a
one-off rule; the next film could repeat the next mistake of the same kind. The ledger keeps the user's own words,
OUTSIDE this public repo, and retires an entry once a gate enforces it, so it only ever holds taught-but-ungated taste."""
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import taste_ledger as tl  # noqa: E402


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    p = tmp_path / "taste" / "ledger.json"
    monkeypatch.setenv("TTV_TASTE_LEDGER", str(p))
    return p


def test_add_then_brief_lists_only_active_rules_of_that_stage(ledger):
    tl.add("视频不是 PPT", "no header title per beat", "design")
    tl.add("背景要按实际来", "environment per beat from its subject", "design")
    tl.retire("no-header-title-per-beat", gate="validate SLIDE TITLES")
    assert tl.brief("design") == ["environment per beat from its subject"]
    assert tl.brief("render") == []


def test_the_users_words_are_kept_verbatim_and_the_file_is_written_where_asked(ledger):
    e = tl.add("卫星的背景怎么可能是山水", "environment per beat from its subject", "design", film="gps")
    data = json.loads(ledger.read_text(encoding="utf-8"))
    assert data["entries"][0]["said"] == "卫星的背景怎么可能是山水"
    assert e["status"] == "active" and e["film"] == "gps" and e["stage"] == "design"


def test_ids_are_unique_even_for_the_same_rule(ledger):
    a = tl.add("x", "every element decodable in ~1 s", "design")
    b = tl.add("y", "every element decodable in ~1 s", "build")
    assert a["id"] != b["id"]


def test_retire_names_its_gate_and_an_unknown_id_is_refused(ledger):
    tl.add("x", "lining figures", "render")
    tl.retire("lining-figures", gate="validate lining")
    e = tl.load()["entries"][0]
    assert e["status"] == "retired" and e["gate"] == "validate lining"
    with pytest.raises(KeyError):
        tl.retire("no-such-rule", gate="g")


def test_corrupt_ledger_is_an_error_not_an_empty_ledger(tmp_path, monkeypatch):
    p = tmp_path / "l.json"
    p.write_text("{not json")
    monkeypatch.setenv("TTV_TASTE_LEDGER", str(p))
    with pytest.raises(tl.LedgerError, match=str(p)):
        tl.load()
    with pytest.raises(tl.LedgerError):
        tl.add("x", "y", "design")                       # never overwrites a file it could not read


def test_missing_ledger_is_empty_and_bad_stage_is_refused(ledger):
    assert tl.load()["entries"] == []
    with pytest.raises(ValueError):
        tl.add("x", "y", "colour")
    with pytest.raises(ValueError):
        tl.add("", "y", "design")                        # a rule nobody said is not taught


def test_default_path_is_outside_the_repo(monkeypatch):
    monkeypatch.delenv("TTV_TASTE_LEDGER", raising=False)
    p = os.path.abspath(tl.ledger_path())
    assert not p.startswith(os.path.abspath(_ROOT)) and p.endswith(os.path.join(".topic-to-video", "taste-ledger.json"))


def test_cli_add_list_brief(ledger, capsys):
    assert tl.main(["add", "--said", "每个元素1秒看懂", "--rule", "every element decodable in ~1 s",
                    "--stage", "design"]) == 0
    assert tl.main(["brief", "--stage", "design"]) == 0
    assert "every element decodable" in capsys.readouterr().out


def test_a_long_rule_id_ends_on_a_whole_word(ledger):
    e = tl.add("x", "each beat's environment comes from its own subject, never one decorative world", "design")
    assert e["id"] == "each-beat-s-environment-comes-from-its-own" and len(e["id"]) <= 48


def test_a_ledger_that_parses_but_is_malformed_is_named_not_crashed_on(tmp_path, monkeypatch):
    """Review I1: {"entries": ["oops"]} crashed `check` with an AttributeError, and an entry with no rule raised a bare
    KeyError — neither named the file. Each entry is checked when the ledger is read."""
    p = tmp_path / "l.json"
    monkeypatch.setenv("TTV_TASTE_LEDGER", str(p))
    for bad in ({"entries": ["oops"]}, {"entries": [{"id": "x", "said": "s", "stage": "design", "status": "active"}]},
                {"entries": [{"id": "x", "said": "s", "rule": "r", "stage": "colour", "status": "active"}]}):
        p.write_text(json.dumps(bad))
        with pytest.raises(tl.LedgerError, match=str(p)):
            tl.load()


def test_an_unwritable_ledger_folder_is_a_named_error(tmp_path, monkeypatch):
    d = tmp_path / "ro"
    d.mkdir()
    d.chmod(0o500)
    monkeypatch.setenv("TTV_TASTE_LEDGER", str(d / "l.json"))
    try:
        with pytest.raises(tl.LedgerError, match="cannot be written"):
            tl.add("x", "a rule", "design")
        assert tl.main(["add", "--said", "x", "--rule", "a rule", "--stage", "design"]) == 1
    finally:
        d.chmod(0o700)
