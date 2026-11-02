"""A register keys a cued item by its index path (`files.0`); the words' full path (`files.0.label`) resolves to it.

WHY. The scaffold says `cue.win('<prop path>', ...)`, and a builder reading that literally wrote `files.0.label` — the
prop path of the words it cues. The cue map keys items by index (sync_qa.item_texts), so that key matched nothing and
every file of a delivered film fell back to its default timing, landing 1.6-2.6 s after the voice said it, with no
error anywhere. Two other builders' shots and the lead's own had the same spelling. runtime/cue's `cueKey` now resolves
a words-field path to its item; the field list is sync_qa.CUE_TEXT_FIELDS, held equal here.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)
import _tsprobe  # noqa: E402
import sync_qa  # noqa: E402


@pytest.fixture(scope="module")
def probe():
    if not _tsprobe.available():
        pytest.skip("node/esbuild not available")
    return _tsprobe.run_ts("import {cueKey, CUE_TEXT_FIELDS} from %s;" % _tsprobe.mod("cue.ts"),
                           "const at = {'files.0': 1.2, 'caption': 0.3, 'pts.1.text': 2};"
                           "out.fields = CUE_TEXT_FIELDS;"
                           "out.k = ['files.0', 'files.0.label', 'files.0.text', 'files.0.ext', 'files.9.label',"
                           "         'caption', 'pts.1.text', 'nope'].map((k) => cueKey(at, k));")


def test_a_words_field_path_resolves_to_its_item(probe):
    assert probe["k"] == ["files.0", "files.0", "files.0", "files.0.ext", "files.9.label", "caption", "pts.1.text",
                          "nope"]


def test_the_runtime_and_the_cue_map_agree_on_which_fields_carry_words(probe):
    assert tuple(probe["fields"]) == sync_qa.CUE_TEXT_FIELDS
