"""Density and real use (spec 2026-11-06 E). The HTTPS film shipped at a median 7.0 % ink — clean line drawings in a
mostly empty frame — with a warning nobody had to answer; the GPS film the user approved after asking for fuller
frames measured 28.8 %. A launch film earns trust by showing the product in use (WorkBuddy's intro, the user's own
example), and leads with its most valuable moment."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import shot_proof as sp  # noqa: E402
import validate as v  # noqa: E402

HTTPS = [4.0, 22.8, 9.8, 44.9, 7.0, 4.9, 3.7, 6.2, 5.4, 7.8, 7.6, 3.9, 7.8, 4.6]
GPS = [92.2, 85.0, 28.8, 5.6, 64.7, 18.4, 35.4, 13.0, 33.1, 82.8, 28.4, 21.2, 61.3, 24.7, 7.4]


def _slides(n):
    return [{"index": i + 1, "shot": "S"} for i in range(n)]


THIN = [2.0, 5.0, 4.0, 6.5, 3.0]                              # a line of type per beat: median under 6 %
ANC = [77.2, 3.9, 7.1, 10.6, 17.9, 6.8, 4.6, 16.4, 17.8, 28.7, 12.7, 4.2, 12.7, 12.9, 8.3, 12.3, 13.6, 3.4, 14.4,
       40.2, 14.0, 23.7, 77.2, 6.6]                           # the film the user found okay: median 12.9 %


def test_a_film_of_near_empty_frames_is_an_error():
    errs, _w = sp.tonal_findings(list(enumerate(THIN, 1)), {}, _slides(5))
    assert len(errs) == 1 and "TONAL REGISTER is thin" in errs[0]


def test_a_sparse_film_stays_a_warning_because_the_okay_film_is_sparse_too():
    """Calibration (spec anti-goal): an error must stay quiet on ANC, which measures 12.9 % — under the 14 % SPARSE
    line. So SPARSE warns (HTTPS 7.0 %, ANC 12.9 %) and only the near-empty film errors."""
    for inks, n in ((HTTPS, 14), (ANC, 24)):
        errs, warns = sp.tonal_findings(list(enumerate(inks, 1)), {}, _slides(n))
        assert not errs and any("SPARSE" in w for w in warns)


def test_a_named_reason_turns_it_back_into_a_warning():
    errs, warns = sp.tonal_findings(list(enumerate(THIN, 1)), {"sparse_reason": "a minimal ink register, on purpose"},
                                    _slides(5))
    assert not errs and any("sparse_reason" in w for w in warns)


def test_the_approved_film_passes():
    errs, _w = sp.tonal_findings(list(enumerate(GPS, 1)), {}, _slides(15))
    assert not errs


def test_hero_and_title_beats_leave_the_median():
    inks = [(1, 2.0), (2, 2.0), (3, 30.0), (4, 30.0), (5, 30.0)]            # heroes/titles out: median 30
    slides = _slides(5)
    slides[0]["shot_fit"] = {"form": "title card"}
    assert sp.tonal_findings(inks, {"hero_moments": [2]}, slides)[0] == []         # median over 3, 4, 5
    assert sp.tonal_findings(inks + [(6, 2.0), (7, 2.0)], {}, _slides(7))[0]   # nothing left out: median 2.0


def _promo(n, real=(), hero=None, cold=None):
    slides = [{"index": i + 1, "shot": "S%d" % (i + 1), "duration": 4.0} for i in range(n)]
    for b in real:
        slides[b - 1]["real_use"] = True
    if cold:
        slides[0] = {"index": 1, "shot": "ColdOpen", "duration": 4.0, "shot_props": {"beats": cold}}
    meta = {"renderer": "remotion", "purpose": "launch"}
    if hero:
        meta["hero_moments"] = hero
    return meta, slides


def test_a_launch_film_with_little_real_use_is_warned():
    assert any("real use" in w for w in v._real_use(*_promo(9, real=(2, 5))))
    assert not any("real use" in w for w in v._real_use(*_promo(9, real=(2, 5, 7))))


def test_a_filmscreen_beat_counts_as_real_use_and_an_explainer_is_not_asked():
    meta, slides = _promo(6, real=(2,))
    slides[3]["shot"] = "FilmScreen"
    assert not any("real use" in w for w in v._real_use(meta, slides))
    meta["purpose"] = "teach"
    assert v._real_use(meta, _promo(6)[1]) == []


def test_a_launch_film_previews_a_hero_moment_in_its_first_five_seconds():
    assert any("first 5 s" in w for w in v._real_use(*_promo(9, real=(2, 5, 7), hero=[6])))
    assert not any("first 5 s" in w for w in v._real_use(*_promo(9, real=(2, 5, 7), hero=[6], cold=[6, 8])))
    assert not any("first 5 s" in w for w in v._real_use(*_promo(9, real=(2, 5, 7), hero=[1])))
