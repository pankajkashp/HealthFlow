"""Shared fixtures for the API test suite.

Seeds the 6 synthetic benchmark patients/plans once per test session, reusing the same script the
Docker Compose demo environment runs at startup (scripts/seed_demo_data.py) — DRY, and it exercises
that script as a side effect of running these tests.
"""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture(scope="session")
def _seed_demo_data() -> None:
    from scripts.seed_demo_data import seed

    seed()
