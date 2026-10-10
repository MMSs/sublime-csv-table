"""Tests for the Package Control messages."""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_message_file_exists() -> None:
    with open(os.path.join(ROOT, "messages.json"), encoding="utf-8") as handle:
        messages = json.load(handle)
    assert "install" in messages
    for path in messages.values():
        assert os.path.isfile(os.path.join(ROOT, path)), path
