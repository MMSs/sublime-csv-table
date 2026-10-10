"""Tests for the generated CSV syntaxes."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))

import build_syntaxes  # noqa: E402


def test_generated_syntaxes_are_up_to_date() -> None:
    for path, text in build_syntaxes.outputs():
        with open(path, encoding="utf-8") as handle:
            assert handle.read() == text, f"run scripts/build_syntaxes.py: {path}"


def test_columns_cycle_back_to_the_first() -> None:
    _path, text = build_syntaxes.outputs()[0]
    last = len(build_syntaxes.COLUMN_SCOPES)
    assert f"  column_{last}:" in text
    assert "set: column_1\n" in text
