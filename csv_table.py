"""Sublime command that formats the current buffer as a CSV table."""

import json
import os
import sys
from typing import Dict, List, Tuple

import sublime
import sublime_plugin

# Sublime loads this file as "<package>.csv_table", so a bare import of the
# sibling module does not resolve. Put the package directory on sys.path.
_PACKAGE_DIR = os.path.dirname(os.path.realpath(__file__))
if _PACKAGE_DIR not in sys.path:
    sys.path.insert(0, _PACKAGE_DIR)

from csv_format import FormatError, format_csv_with_delimiter
from csv_scheme import scheme_rules

_SYNTAX_BY_DELIMITER = {
    ",": "Packages/CSV Table/CSV.sublime-syntax",
    ";": "Packages/CSV Table/CSV (Semicolon).sublime-syntax",
    "\t": "Packages/CSV Table/CSV (Tab).sublime-syntax",
    "|": "Packages/CSV Table/CSV (Pipe).sublime-syntax",
}
_SETTINGS = "CSV Table.sublime-settings"
_HEADER_KEY = "csv_table_header"
_HEADER_RULE_HTML = (
    '<body id="csv-table-header" style="margin: 0; padding: 0;">'
    '<div style="background-color: {color}; width: {width}px; height: 1px;"></div>'
    "</body>"
)
_STRIPES_KEY = "csv_table_stripes"
_INDENT_KEY = "csv_table_indent"
_PADDING_KEY = "csv_table_padding"
_BLOCK_HTML = (
    '<body id="csv-table-block" style="margin: 0; padding: 0;">'
    '<div style="width: {width}px; height: {height}px;{background}"></div>'
    "</body>"
)
_CALIBRATION_KEY = "csv_table_calibration"
# The editor shows a quoted cell's later lines just after the opening quote.
# Matches _CONTINUATION_INDENT in csv_format.
_CONTINUATION_INDENT = 1
_phantom_sets: Dict[Tuple[int, str], sublime.PhantomSet] = {}
_phantom_gaps: Dict[int, Tuple[float, float]] = {}
_STRIPE_SCOPE = "region.csv-table.stripe"
_STRIPE_ALPHA = "14"
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
            formatted, used = format_csv_with_delimiter(source, delimiter)
        except FormatError as exc:
            self._status(_STATUS_BY_REASON[exc.reason])
            return
        self.view.run_command("csv_table_replace", {"text": formatted})
        self.view.assign_syntax(_SYNTAX_BY_DELIMITER[used])
        self.view.settings().set("word_wrap", False)
        highlight(self.view)
        self._status(_STATUS_FORMATTED)

    def _status(self, message: str) -> None:
        window = self.view.window()
        if window is not None:
            window.status_message(message)


class CsvTableReplaceCommand(sublime_plugin.TextCommand):
    """Replace the buffer in one undo step."""

    def run(self, edit: sublime.Edit, text: str = "") -> None:
        self.view.replace(edit, sublime.Region(0, self.view.size()), text)


class CsvTableHighlightListener(sublime_plugin.ViewEventListener):
    """Underline the header row and shade every other record."""

    @classmethod
    def is_applicable(cls, settings: sublime.Settings) -> bool:
        return "CSV Table/" in (settings.get("syntax") or "")

    def on_load_async(self) -> None:
        highlight(self.view)

    def on_activated_async(self) -> None:
        highlight(self.view)

    def on_modified_async(self) -> None:
        highlight(self.view)

    def on_close(self) -> None:
        for key in (_HEADER_KEY, _INDENT_KEY, _PADDING_KEY):
            _phantom_sets.pop((self.view.id(), key), None)
        _phantom_gaps.pop(self.view.id(), None)


def highlight(view: sublime.View) -> None:
    """Draw the header rule, row stripes, and continuation indents."""
    settings = sublime.load_settings(_SETTINGS)
    records = _records(view, settings.get("max_highlight_lines", 20000))
    header = records[:1] if settings.get("underline_header", True) else []
    stripes = records[2::2] if settings.get("stripe_rows", True) else []
    color_columns = settings.get("color_columns", True)
    # Without a stripe rule Sublime fills with the opaque foreground colour.
    if not _ensure_scheme_rules(view, bool(stripes), color_columns) and stripes:
        stripes = []
    view.add_regions(_STRIPES_KEY, stripes, _STRIPE_SCOPE, "", sublime.DRAW_NO_OUTLINE)
    _indent_continuations(view, records, stripes)
    right = max(
        (view.text_to_layout(line.end())[0] for line in _lines(view, records)),
        default=0,
    )
    _draw_header_rule(
        view, header, right, settings.get("header_scope", "markup.heading")
    )
    _pad_open_lines(view, stripes, right)


def _draw_header_rule(
    view: sublime.View,
    header: list,
    right: float,
    scope: str,
) -> None:
    """Draw a line under the header as wide as the widest record.

    A region underline skips whitespace and stops at the header's last
    character, so it looks broken and can be shorter than the table.
    """
    phantoms = _phantom_set(view, _HEADER_KEY)
    if not header:
        phantoms.update([])
        return
    # A phantom below a line starts at its anchor, so anchor at the start of
    # the header's last line.
    anchor = view.line(header[0].end()).begin()
    left = view.text_to_layout(anchor)[0]
    html = _HEADER_RULE_HTML.format(
        color=view.style_for_scope(scope).get("foreground", "#808080"),
        width=max(int(right - left), 1),
    )
    region = sublime.Region(anchor)
    phantoms.update([sublime.Phantom(region, html, sublime.LAYOUT_BELOW)])


def _indent_continuations(view: sublime.View, records: list, stripes: list) -> None:
    """Show each line that continues a quoted cell under its opening quote.

    The quoted text cannot gain spaces without changing the cell, so the
    indent is a phantom. The formatter pads the rest of the line to match.
    """
    end = records[-1].end() if records else 0
    color = view.style_for_scope(_STRIPE_SCOPE).get("background")
    tab_size = view.settings().get("tab_size", 4)
    indents: Dict[int, int] = {}
    phantoms: List[sublime.Phantom] = []
    for string in view.find_by_selector("string.quoted"):
        if string.begin() > end:
            break
        lines = view.lines(string)
        if len(lines) < 2:
            continue
        # The string scope starts at the padding before the opening quote.
        text = view.substr(string)
        quote = string.begin() + len(text) - len(text.lstrip(" "))
        row = view.rowcol(quote)[0]
        before = view.substr(sublime.Region(lines[0].begin(), quote))
        column = (
            indents.get(row, 0)
            + len(before.expandtabs(tab_size))
            + _CONTINUATION_INDENT
        )
        width = int(column * view.em_width() - _phantom_gaps_for(view, records)[0])
        for line in lines[1:]:
            indents[view.rowcol(line.begin())[0]] = column
            if width <= 0:
                continue
            striped = color and any(r.contains(line.begin()) for r in stripes)
            html = _BLOCK_HTML.format(
                width=width,
                height=int(view.line_height()),
                background=f" background-color: {color};" if striped else "",
            )
            region = sublime.Region(line.begin())
            phantoms.append(sublime.Phantom(region, html, sublime.LAYOUT_INLINE))
    _phantom_set(view, _INDENT_KEY).update(phantoms)


def _pad_open_lines(view: sublime.View, stripes: list, right: float) -> None:
    """Shade striped lines that end inside a quoted cell out to the table edge.

    The formatter pads every record's last line with spaces, but it cannot
    pad a line that ends inside quotes.
    """
    color = view.style_for_scope(_STRIPE_SCOPE).get("background")
    phantoms: List[sublime.Phantom] = []
    for line in _lines(view, stripes) if color else []:
        if not view.match_selector(line.end(), "string.quoted"):
            continue
        end = view.text_to_layout(line.end())[0]
        width = int(right - end - _phantom_gaps_for(view, stripes)[1])
        if width <= 0:
            continue
        html = _BLOCK_HTML.format(
            width=width,
            height=int(view.line_height()),
            background=f" background-color: {color};",
        )
        region = sublime.Region(line.end())
        phantoms.append(sublime.Phantom(region, html, sublime.LAYOUT_INLINE))
    _phantom_set(view, _PADDING_KEY).update(phantoms)


def _phantom_gaps_for(view: sublime.View, records: list) -> Tuple[float, float]:
    """Return the space Sublime adds to a block at a line's start and end.

    It depends on the font and display, so measure it once per view with a
    block on the first record.
    """
    gaps = _phantom_gaps.get(view.id())
    if gaps is not None or not records:
        return gaps or (0, 0)
    line = view.line(records[0].begin())
    before = view.text_to_layout(line.begin())[0]
    _add_calibration_block(view, line.begin(), 20)
    start = view.text_to_layout(line.begin())[0] - before - 20
    view.erase_phantoms(_CALIBRATION_KEY)
    # Nothing follows a block at the end of a line, so measure how far it
    # widens the layout. It must be wider than every line to do that.
    width = int(view.layout_extent()[0]) + 100
    _add_calibration_block(view, line.end(), width)
    end = view.layout_extent()[0] - view.text_to_layout(line.end())[0] - width
    view.erase_phantoms(_CALIBRATION_KEY)
    gaps = (start, end)
    _phantom_gaps[view.id()] = gaps
    return gaps


def _add_calibration_block(view: sublime.View, point: int, width: int) -> None:
    html = _BLOCK_HTML.format(
        width=width, height=int(view.line_height()), background=""
    )
    view.add_phantom(
        _CALIBRATION_KEY, sublime.Region(point), html, sublime.LAYOUT_INLINE
    )


def _phantom_set(view: sublime.View, key: str) -> sublime.PhantomSet:
    phantoms = _phantom_sets.get((view.id(), key))
    if phantoms is None:
        # A plugin reload forgets earlier phantom sets but not their phantoms.
        view.erase_phantoms(key)
        phantoms = sublime.PhantomSet(view, key)
        _phantom_sets[(view.id(), key)] = phantoms
    return phantoms


def _lines(view: sublime.View, records: list) -> List[sublime.Region]:
    return [line for record in records for line in view.lines(record)]


def _ensure_scheme_rules(view: sublime.View, stripes: bool, color_columns: bool) -> bool:
    """Add the stripe colour, or plain columns, to the active colour scheme.

    Sublime merges colour scheme files that share a name, so a rules-only
    file under Packages/User/CSV Table extends whatever scheme is in use.
    Returns False when the scheme is unknown.
    """
    settings = view.settings()
    scheme = settings.get("color_scheme") or ""
    if scheme == "auto":
        schemes = [
            settings.get("light_color_scheme") or "",
            settings.get("dark_color_scheme") or "",
        ]
    else:
        schemes = [scheme]
    schemes = [name for name in schemes if name]
    if not schemes:
        return False
    foreground = view.style().get("foreground", "#808080")[:7]
    rules = scheme_rules(foreground, _STRIPE_SCOPE, _STRIPE_ALPHA, stripes, color_columns)
    text = json.dumps({"rules": rules}, indent=4) + "\n"
    directory = os.path.join(sublime.packages_path(), "User", "CSV Table")
    for scheme_path in schemes:
        name = os.path.splitext(os.path.basename(scheme_path))[0]
        _write_if_changed(os.path.join(directory, name + ".sublime-color-scheme"), text)
    return True


def _write_if_changed(path: str, text: str) -> None:
    try:
        with open(path, encoding="utf-8") as handle:
            if handle.read() == text:
                return
    except OSError:
        pass
    # Sublime watches the folder; replace atomically so it never reads a
    # half-written scheme.
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(temporary, path)


def _records(view: sublime.View, max_lines: int) -> list:
    """Return one region per record. A quoted cell may span lines."""
    end = view.line(view.text_point(max_lines, 0)).end()
    records = []
    start = None
    for line in view.lines(sublime.Region(0, end)):
        if start is None:
            if line.empty():
                continue
            start = line.begin()
        if view.match_selector(line.end(), "string.quoted"):
            continue
        records.append(sublime.Region(start, line.end()))
        start = None
    return records
