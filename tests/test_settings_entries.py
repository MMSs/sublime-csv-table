"""The settings menu and palette entries open the package settings."""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_FILE = "${packages}/CSV Table/CSV Table.sublime-settings"


def _load(name: str) -> list:
    with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return json.load(handle)


def _edit_settings_args(node: object) -> list:
    if isinstance(node, list):
        return [args for item in node for args in _edit_settings_args(item)]
    if isinstance(node, dict):
        found = [node["args"]] if node.get("command") == "edit_settings" else []
        return found + _edit_settings_args(node.get("children", []))
    return []


def test_menu_and_palette_open_the_package_settings() -> None:
    for name in ("Main.sublime-menu", "Default.sublime-commands"):
        entries = _edit_settings_args(_load(name))
        assert len(entries) == 1, name
        assert entries[0]["base_file"] == BASE_FILE
    assert os.path.isfile(os.path.join(ROOT, "CSV Table.sublime-settings"))
