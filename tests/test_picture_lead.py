"""Voice-timed layers run on the VOICE's clock under a carried cut (runtime/motion PictureLeadContext).

A beat that arrives by a carried cut (Film.tsx CutCarry) runs its picture's clock `cutFrame(TR) + CARRY_F` frames ahead.
Coverage and the focus lead sat inside that clock with plans written in voice time, so they cut that much early:
WorkBuddy beat 17's first close-up, planned for 0.8 s (after the entrance), cut 0.3 s in, mid-entrance (2026-11-11)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "remotion", "src")
read = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8").read()


def test_the_carried_cut_publishes_its_lead():
    film = read("Film.tsx")
    body = film.split("const CutCarry")[1].split("};")[0]
    assert "<PictureLeadContext.Provider value={lead}>" in body


def test_coverage_steps_on_the_voice_and_probes_the_picture_on_screen():
    cov = read("runtime", "coverage.tsx")
    assert "const frame = useCurrentFrame() - lead;" in cov
    assert "<Freeze frame={pf + lead}>" in cov
    assert "${lead}:${W}x${H}" in cov, "a framing measured under one lead must not be served under another"


def test_the_focus_lead_steps_on_the_voice():
    assert "useCurrentFrame() - useContext(PictureLeadContext)" in read("runtime", "focusLead.tsx")


def test_a_span_meant_to_last_the_beat_lasts_until_the_beat_leaves():
    """Under the lead the picture's clock reaches `dur` `lead` frames before the beat unmounts: the promo's screens went
    black 8-10 frames before their cut (2026-11-12). usePictureEnd is the end; the library's recordings use it."""
    mo = read("runtime", "motion.ts")
    assert "export const usePictureEnd = (dur: number): number => dur + React.useContext(PictureLeadContext);" in mo
    scr = read("runtime", "screen.tsx")
    assert "durationInFrames={frames + (i === spans.length - 1 ? lead : 0)}" in scr
    fs = read("shots", "FilmScreen.tsx")
    assert "usePictureEnd(dur)" in fs and "durationInFrames={Math.max(1, end)}" in fs


def test_no_library_shot_ends_a_sequence_at_the_beats_duration():
    import glob
    import sys
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import validate as v
    bad = {}
    for p in glob.glob(os.path.join(SRC, "**", "*.tsx"), recursive=True):
        hits = v.sequence_ends_at_duration(open(p, encoding="utf-8").read())
        if hits:
            bad[os.path.relpath(p, SRC)] = hits
    assert not bad, bad


def test_validate_names_a_workshop_sequence_sized_from_dur(tmp_path):
    import sys
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import validate as v
    d = tmp_path / "workshop" / "shots"
    d.mkdir(parents=True)
    (d / "Clip.tsx").write_text(
        "const end = usePictureEnd(dur);\n"
        "export const Clip = () => <>\n"
        "  <Sequence from={0} durationInFrames={Math.max(1, dur)} layout=\"none\"><V /></Sequence>\n"
        "  <Sequence from={a} durationInFrames={(last ? dur : f1) - a}><V /></Sequence>\n"
        "  <Sequence from={0} durationInFrames={Math.max(1, end)}><V /></Sequence>\n"
        "  <Sequence from={0} durationInFrames={30}><V /></Sequence>\n"
        "</>;\n", encoding="utf-8")
    errs = v._spans_end_at_duration(str(tmp_path), [{"shot": "Clip"}])
    assert [e.split(":")[1] for e in errs] == ["3", "4"], errs
    assert "usePictureEnd" in errs[0]


def test_the_camera_edge_budget_waits_for_the_fonts_like_coverage():
    """A render tab's first frames measured type in fallback metrics: the topic-to-video promo's closing title popped
    7% smaller on six isolated frames under its pull (2026-11-12). The budget waits for layout AND the fonts."""
    depth = read("runtime", "depth.tsx")
    body = depth.split("const apply = (): boolean => {")[1].split("if (apply()) return;")[0]
    assert "fonts.status !== 'loaded'" in body and body.index("fonts.status") < body.index("getBoundingClientRect")


def test_the_camera_edge_budget_is_measured_on_the_settled_layout():
    """Measured per frame, the budget followed type in flight: the promo's closing cards flew in from beyond the frame and
    the picture scaled 7% in single-frame pops, the same frames on every render (2026-11-12). It is measured once, on a
    transparent copy frozen at SETTLED_T, after the live picture, and dropped once measured."""
    depth = read("runtime", "depth.tsx")
    assert "<Freeze frame={settledF}>{children}</Freeze>" in depth
    assert "settled.current = cameraTypeBoxes(probe.current, W);" in depth
    assert "const boxes = settled.current ?? cameraTypeBoxes(el, W);" in depth
    probe = depth.split("data-camera-probe")[1].split("</div>")[0]
    assert "opacity: 0" in probe and "visibility" not in probe, "a hidden subtree's type has no boxes"
    live = depth.index("{children}\n      </div>")
    assert live < depth.index("data-camera-probe"), "the probe comes after the live picture (first SVG id wins)"
