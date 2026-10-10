"""Tests for the colour scheme rules the plugin merges into the active scheme."""

import os
import re

from csv_scheme import COLUMN_SCOPES, QUOTE_SCOPES, column_scope, scheme_rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rules(stripes: bool, color_columns: bool) -> list:
    return scheme_rules("#d8dee9", "region.csv-table.stripe", "14", stripes, color_columns)


def test_defaults_add_only_the_stripe() -> None:
    assert _rules(stripes=True, color_columns=True) == [
        {
            "name": "CSV Table stripe",
            "scope": "region.csv-table.stripe",
            "background": "#d8dee914",
        }
    ]


def test_plain_columns_use_the_foreground_for_every_column() -> None:
    [rule] = _rules(stripes=False, color_columns=False)
    assert rule["foreground"] == "#d8dee9"
    scopes = rule["scope"].split(", ")
    columns = [column_scope(number) for number in range(1, len(COLUMN_SCOPES) + 1)]
    assert scopes == columns + QUOTE_SCOPES
    assert scopes[0] == "variable.other.column-1.csv"


def test_stripes_and_plain_columns_together() -> None:
    names = [rule["name"] for rule in _rules(stripes=True, color_columns=False)]
    assert names == ["CSV Table stripe", "CSV Table plain columns"]


def test_nothing_to_add() -> None:
    assert _rules(stripes=False, color_columns=True) == []


def test_every_setting_the_plugin_reads_has_a_default() -> None:
    with open(os.path.join(ROOT, "csv_table.py"), encoding="utf-8") as handle:
        read = set(re.findall(r'settings\.get\("(\w+)"', handle.read()))
    with open(os.path.join(ROOT, "CSV Table.sublime-settings"), encoding="utf-8") as handle:
        defaults = set(re.findall(r'^\s*"(\w+)":', handle.read(), re.M))
    read -= {"syntax", "color_scheme", "light_color_scheme", "dark_color_scheme"}
    assert read and read <= defaults
