import os, subprocess, sys, pytest
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)

@pytest.fixture(scope="session", autouse=True)
def _build_fixtures():
    if not os.path.exists(os.path.join(HERE, "fixtures", "deck.pptx")):
        subprocess.run([sys.executable, os.path.join(HERE, "fixtures", "make_fixtures.py")], check=True)

@pytest.fixture
def fixtures_dir():
    return os.path.join(HERE, "fixtures")
