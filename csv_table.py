"""Sublime command that formats the current buffer as a CSV table."""

import os
import sys

import sublime
import sublime_plugin

# Sublime loads this file as "<package>.csv_table", so a bare import of the
# sibling module does not resolve. Put the package directory on sys.path.
_PACKAGE_DIR = os.path.dirname(os.path.realpath(__file__))
if _PACKAGE_DIR not in sys.path:
    sys.path.insert(0, _PACKAGE_DIR)

from csv_format import FormatError, format_csv

_SYNTAX = "Packages/CSV Table/CSV.sublime-syntax"
_STATUS_FORMATTED = "CSV Table: formatted"
_STATUS_BY_REASON = {
    "empty": "CSV Table: nothing to format",
    "not_csv": "CSV Table: not a CSV table",
    "unclosed_quote": "CSV Table: unclosed quote",
}
_DELIMITER_CHOICES = (
    ("Auto-detect", None),
    ("Comma (,)", ","),
    ("Semicolon (;)", ";"),
    ("Tab", "\t"),
    ("Pipe (|)", "|"),
)


class FormatCsvTableCommand(sublime_plugin.TextCommand):
    """Ask for a delimiter, then format the whole buffer."""

    def run(self, _edit: sublime.Edit) -> None:
        window = self.view.window()
        if window is None:
            return
        window.show_quick_panel(
            [label for label, _delimiter in _DELIMITER_CHOICES],
            self._on_choice,
        )

    def _on_choice(self, index: int) -> None:
        if index < 0:
            return
        _label, delimiter = _DELIMITER_CHOICES[index]
        source = self.view.substr(sublime.Region(0, self.view.size()))
        try:
            formatted = format_csv(source, delimiter)
        except FormatError as exc:
            self._status(_STATUS_BY_REASON[exc.reason])
            return
        self.view.run_command("csv_table_replace", {"text": formatted})
        self.view.assign_syntax(_SYNTAX)
        self.view.settings().set("word_wrap", False)
        self._status(_STATUS_FORMATTED)

    def _status(self, message: str) -> None:
        window = self.view.window()
        if window is not None:
            window.status_message(message)


class CsvTableReplaceCommand(sublime_plugin.TextCommand):
    """Replace the buffer in one undo step."""

    def run(self, edit: sublime.Edit, text: str = "") -> None:
        self.view.replace(edit, sublime.Region(0, self.view.size()), text)
