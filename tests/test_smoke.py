"""Smoke test: the package imports. Keeps CI meaningful before real tests exist."""

import aom


def test_package_imports() -> None:
    assert aom.__version__ == "0.0.1"
