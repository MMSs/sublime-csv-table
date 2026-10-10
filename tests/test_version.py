"""The version in pyproject.toml is the one the release workflow bumps."""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return handle.read()


def test_uv_lock_has_the_project_version() -> None:
    project = re.search(r'^version = "([^"]+)"$', _read("pyproject.toml"), re.M)
    locked = re.search(
        r'^name = "sublime-csv-table"\nversion = "([^"]+)"$', _read("uv.lock"), re.M
    )
    assert project and locked
    assert locked.group(1) == project.group(1), "run uv lock"
