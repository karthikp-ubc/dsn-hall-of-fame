import importlib.util
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent

for _p in (str(REPO_ROOT), str(TESTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dblp  # noqa: E402


def _load_dsn_ranking():
    """dsn-ranking.py can't be `import`ed normally (hyphen in filename)."""
    spec = importlib.util.spec_from_file_location(
        "dsn_ranking_under_test", REPO_ROOT / "dsn-ranking.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def dsn_ranking():
    """Fresh copy of the dsn-ranking module per test, since several
    functions under test mutate its module-level `authorList` dict."""
    return _load_dsn_ranking()


@pytest.fixture(autouse=True)
def block_real_network(monkeypatch):
    """Safety net: fail loudly if a test forgets to mock requests.get,
    rather than silently hitting the real (rate-limit-prone) dblp API."""

    def _guard(*_args, **_kwargs):
        raise AssertionError(
            "Test attempted a real network call — mock dblp.requests.get instead."
        )

    monkeypatch.setattr(dblp.requests, "get", _guard)
