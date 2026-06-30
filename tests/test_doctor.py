import json, subprocess, sys
import doctor


def test_evaluate_all_present_ok():
    results = [("ffmpeg", True, True, "x", "y"), ("PIL", True, True, "x", "y")]
    r = doctor.evaluate(results)
    assert r["ok"] is True and r["missing_required"] == [] and "ffmpeg" in r["present"]


def test_evaluate_missing_required_fails():
    results = [("ffmpeg", True, False, "rendering", "brew install ffmpeg")]
    r = doctor.evaluate(results)
    assert r["ok"] is False and r["missing_required"][0]["name"] == "ffmpeg"
    assert r["missing_required"][0]["install"] == "brew install ffmpeg"


def test_evaluate_missing_optional_is_not_failure():
    results = [("ffmpeg", True, True, "x", "y"), ("edge-tts", False, False, "neural voice", "pip install edge-tts")]
    r = doctor.evaluate(results)
    assert r["ok"] is True and r["missing_optional"][0]["name"] == "edge-tts"


def test_check_runs_real_probes():
    r = doctor.check()
    assert "ok" in r and isinstance(r["present"], list)


def test_main_json_exit_contract():
    out = subprocess.run([sys.executable, doctor.__file__, "--json"], capture_output=True, text=True)
    parsed = json.loads(out.stdout)
    # exit code must agree with the payload's ok flag (gate contract)
    assert (out.returncode == 0) == parsed["ok"]
