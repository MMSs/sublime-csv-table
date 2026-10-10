"""Format CSV text into an aligned table."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

REASON_EMPTY = "empty"
REASON_NOT_CSV = "not_csv"
REASON_UNCLOSED_QUOTE = "unclosed_quote"

_DELIMITER_CANDIDATES = [",", ";", "\t", "|"]
_CURRENCY = set("$€£¥")
_GAP_CHARACTERS = set(" \u00a0\u202f")
_WHITESPACE_SEPARATORS = set(" \u00a0\u202f")
_BOUNDARIES = set(",;\t|\r\n")
_EXPONENT_RE = re.compile(r"[eE][+-]?\d+$")
_LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")
# The editor shows a quoted cell's later lines one column in, under the
# first character after the opening quote.
_CONTINUATION_INDENT = 1
_SIGN_CHARACTERS = set("+-")


class FormatError(Exception):
    """CSV text could not be formatted."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class _Field:
    interior: str
    quoted: bool


def format_csv(text: str, delimiter: Optional[str] = None) -> str:
    """Return aligned CSV. delimiter None auto-detects. Raises FormatError."""
    formatted, _delimiter = format_csv_with_delimiter(text, delimiter)
    return formatted


def format_csv_with_delimiter(
    text: str, delimiter: Optional[str] = None
) -> Tuple[str, str]:
    """Return aligned CSV and the delimiter used. Raises FormatError."""
    if text.strip(" \t\r\n\u00a0\u202f") == "":
        raise FormatError(REASON_EMPTY)
    quote = _choose_quote(text)
    if delimiter is None:
        delimiter, rows = _detect(text, quote)
    else:
        rows = _parse(text, delimiter, quote)
        if _score(rows) is None:
            raise FormatError(REASON_NOT_CSV)
    lines = _align(rows, delimiter, quote)
    newline = _output_newline(text)
    formatted = newline.join(lines)
    if text.endswith("\n") or text.endswith("\r"):
        formatted += newline
    return formatted, delimiter


def _choose_quote(text: str) -> str:
    single_quotes = _count_quoted_fields(text, "'")
    double_quotes = _count_quoted_fields(text, '"')
    if single_quotes > double_quotes:
        return "'"
    return '"'


def _count_quoted_fields(text: str, quote: str) -> int:
    count = 0
    index = 0
    length = len(text)
    at_boundary = True
    while index < length:
        char = text[index]
        if at_boundary and char == " ":
            index += 1
            continue
        if at_boundary and char == quote:
            cursor = index + 1
            closed = False
            while cursor < length:
                if text[cursor] != quote:
                    cursor += 1
                    continue
                if cursor + 1 < length and text[cursor + 1] == quote:
                    cursor += 2
                    continue
                closed = True
                cursor += 1
                break
            if not closed:
                break
            count += 1
            index = cursor
            at_boundary = False
            continue
        at_boundary = char in _BOUNDARIES
        index += 1
    return count


def _detect(text: str, quote: str) -> Tuple[str, List[Optional[List[_Field]]]]:
    best_key: Optional[Tuple[int, int]] = None
    best_rows: Optional[List[Optional[List[_Field]]]] = None
    best_delimiter: Optional[str] = None
    for index, delimiter in enumerate(_DELIMITER_CANDIDATES):
        rows = _parse(text, delimiter, quote)
        score = _score(rows)
        if score is None:
            continue
        key = (score, -index)
        if best_key is None or key > best_key:
            best_key = key
            best_rows = rows
            best_delimiter = delimiter
    if best_delimiter is None or best_rows is None:
        raise FormatError(REASON_NOT_CSV)
    return best_delimiter, best_rows


def _score(rows: List[Optional[List[_Field]]]) -> Optional[int]:
    counts: Dict[int, int] = {}
    for row in rows:
        if row is None:
            continue
        field_count = len(row)
        counts[field_count] = counts.get(field_count, 0) + 1
    best_fields = 0
    best_records = 0
    for field_count, records in counts.items():
        if field_count < 2:
            continue
        if records > best_records or (
            records == best_records and field_count > best_fields
        ):
            best_records = records
            best_fields = field_count
    if best_fields < 2:
        return None
    return best_records


def _parse(text: str, delimiter: str, quote: str) -> List[Optional[List[_Field]]]:
    rows: List[Optional[List[_Field]]] = []
    row: List[_Field] = []
    interior: List[str] = []
    quoted_mode = False
    field_quoted = False
    started = False
    index = 0
    length = len(text)

    def finish_field() -> None:
        nonlocal interior, field_quoted, started
        row.append(_Field("".join(interior), field_quoted))
        interior = []
        field_quoted = False
        started = False

    def finish_row(blank: bool) -> None:
        nonlocal row
        if blank:
            rows.append(None)
        else:
            rows.append(row)
        row = []

    while index < length:
        if quoted_mode:
            if text[index] == quote:
                if index + 1 < length and text[index + 1] == quote:
                    interior.append(quote)
                    index += 2
                    continue
                quoted_mode = False
                index += 1
                cursor = index
                while cursor < length and text[cursor] == " ":
                    cursor += 1
                if _is_field_end(text, cursor, delimiter):
                    index = cursor
                continue
            interior.append(text[index])
            index += 1
            continue

        char = text[index]
        if not started and not field_quoted and char == " ":
            cursor = index
            while cursor < length and text[cursor] == " ":
                cursor += 1
            if cursor < length and text[cursor] == quote:
                index = cursor
                continue
        if not started and char == quote:
            field_quoted = True
            quoted_mode = True
            started = True
            index += 1
            continue
        if char == delimiter:
            finish_field()
            index += 1
            continue
        if char in "\r\n":
            if not started and not row and not interior:
                index = _skip_newline(text, index)
                finish_row(True)
                continue
            finish_field()
            index = _skip_newline(text, index)
            finish_row(False)
            continue
        interior.append(char)
        started = True
        index += 1

    if quoted_mode:
        raise FormatError(REASON_UNCLOSED_QUOTE)
    if started or field_quoted or row or interior:
        finish_field()
        finish_row(False)
    return rows


def _is_field_end(text: str, index: int, delimiter: str) -> bool:
    if index >= len(text):
        return True
    return text[index] == delimiter or text[index] in "\r\n"


def _skip_newline(text: str, index: int) -> int:
    if text[index] == "\r" and index + 1 < len(text) and text[index + 1] == "\n":
        return index + 2
    return index + 1


def _align(
    rows: List[Optional[List[_Field]]],
    delimiter: str,
    quote: str,
) -> List[str]:
    data_rows = [row for row in rows if row is not None]
    width = max(len(row) for row in data_rows)
    normalized = [
        row + [_Field("", False)] * (width - len(row)) for row in data_rows
    ]
    rendered = [
        [_render(field, delimiter, quote) for field in row] for row in normalized
    ]
    columns: List[List[str]] = []
    for column_index in range(width):
        cells = []
        for row_fields, row_rendered in zip(normalized, rendered):
            field = row_fields[column_index]
            shown = row_rendered[column_index]
            interior = field.interior if field.quoted else field.interior.strip(" ")
            cells.append((shown, _is_number(interior, delimiter)))
        columns.append(_pad_column(cells))
    separator = delimiter if delimiter == "\t" else f"{delimiter} "
    records = [
        separator.join(column[data_index] for column in columns).rstrip(" ")
        for data_index in range(len(data_rows))
    ]
    ends = [
        _record_end(record, [column[data_index] for column in columns], separator)
        for data_index, record in enumerate(records)
    ]
    # Pad every record to the widest one, so the table is a rectangle and
    # row stripes in the editor end at the same column.
    table_width = max(ends)
    lines: List[str] = []
    data_index = 0
    for row in rows:
        if row is None:
            lines.append("")
            continue
        padding = table_width - ends[data_index]
        lines.append(records[data_index] + " " * padding)
        data_index += 1
    return lines


def _record_end(record: str, parts: List[str], separator: str) -> int:
    """Return the column where a trimmed record's last line ends.

    A line that continues a quoted cell is measured from where the editor
    shows it, just after the cell's opening quote.
    """
    column = 0
    indent = 0
    for index, part in enumerate(parts):
        if index:
            column += len(separator)
        pieces = _LINE_BREAK_RE.split(part)
        if len(pieces) > 1:
            indent = column + _CONTINUATION_INDENT
            column = indent
        column += len(pieces[-1])
    return indent + len(_LINE_BREAK_RE.split(record)[-1])


def _width(cell: str) -> int:
    """Return the width of a cell's longest line, as the editor shows it."""
    first, *rest = _LINE_BREAK_RE.split(cell)
    return max([len(first)] + [_CONTINUATION_INDENT + len(piece) for piece in rest])


def _ljust(cell: str, width: int) -> str:
    """Pad a cell so its last line reaches width."""
    pieces = _LINE_BREAK_RE.split(cell)
    shown = len(pieces[-1]) + (_CONTINUATION_INDENT if len(pieces) > 1 else 0)
    return cell + " " * (width - shown)


def _render(field: _Field, delimiter: str, quote: str) -> str:
    interior = field.interior if field.quoted else field.interior.strip(" ")
    if not _must_quote(field, interior, delimiter, quote):
        return interior
    escaped = interior.replace(quote, quote + quote)
    return f"{quote}{escaped}{quote}"


def _must_quote(field: _Field, interior: str, delimiter: str, quote: str) -> bool:
    return (
        field.quoted
        or delimiter in interior
        or quote in interior
        or "\n" in interior
        or "\r" in interior
    )


def _pad_column(cells: List[Tuple[str, bool]]) -> List[str]:
    digit_indexes: List[Optional[int]] = []
    for shown, numeric in cells:
        if not numeric:
            digit_indexes.append(None)
            continue
        digit_indexes.append(_last_digit_index(shown))
    numeric_indexes = [index for index in digit_indexes if index is not None]
    if not numeric_indexes:
        column_width = max(_width(shown) for shown, _numeric in cells)
        return [_ljust(shown, column_width) for shown, _numeric in cells]
    digit_column = max(numeric_indexes)
    tails = [
        len(shown) - index - 1
        for (shown, _numeric), index in zip(cells, digit_indexes)
        if index is not None
    ]
    max_tail = max(tails)
    padded: List[str] = []
    for (shown, _numeric), index in zip(cells, digit_indexes):
        if index is None:
            padded.append(shown)
            continue
        left = digit_column - index
        right = max_tail - (len(shown) - index - 1)
        padded.append(f"{' ' * left}{shown}{' ' * right}")
    column_width = max(_width(value) for value in padded)
    aligned: List[str] = []
    for value, index in zip(padded, digit_indexes):
        if index is None:
            aligned.append(_ljust(value, column_width))
            continue
        aligned.append(value.rjust(column_width))
    return aligned


def _last_digit_index(text: str) -> Optional[int]:
    for index in range(len(text) - 1, -1, -1):
        if text[index].isdigit():
            return index
    return None


def _is_number(value: str, delimiter: str) -> bool:
    text = value.strip(" \u00a0\u202f")
    if not text:
        return False
    if sum(1 for char in text if char in _CURRENCY) > 1:
        return False
    start = 0
    end = len(text)
    sign = ""
    prefix = ""
    if text[start] in _SIGN_CHARACTERS:
        sign = text[start]
        start += 1
    if start < end and text[start] in _CURRENCY:
        prefix = text[start]
        start += 1
        if start < end and text[start] in _GAP_CHARACTERS:
            start += 1
        if not sign and start < end and text[start] in _SIGN_CHARACTERS:
            sign = text[start]
            start += 1
    elif sign and start < end and text[start] in _GAP_CHARACTERS:
        return False
    if end > start and text[end - 1] in _CURRENCY:
        if prefix:
            return False
        end -= 1
        if end > start and text[end - 1] in _GAP_CHARACTERS:
            end -= 1
    body = text[start:end]
    if not body:
        return False
    return _body_is_number(body, delimiter)


def _body_is_number(body: str, delimiter: str) -> bool:
    if re.search(r"[eE]", body):
        exponent = _EXPONENT_RE.search(body)
        if exponent is None:
            return False
        head = body[: exponent.start()]
    else:
        head = body
    if not head or not head[0].isdigit() or not head[-1].isdigit():
        return False
    for char in head:
        if char.isdigit() or char in _WHITESPACE_SEPARATORS or char in ".,":
            continue
        return False
    return _head_is_number(head, delimiter)


def _head_is_number(head: str, delimiter: str) -> bool:
    whitespace = {char for char in head if char in _WHITESPACE_SEPARATORS}
    has_dot = "." in head
    has_comma = "," in head
    if whitespace:
        if len(whitespace) != 1:
            return False
        valid, decimal = _decimal_mark(has_dot, has_comma)
        if not valid:
            return False
        return _grouped(head, next(iter(whitespace)), decimal)
    if has_dot and has_comma:
        if head.rfind(".") > head.rfind(","):
            return _grouped(head, ",", ".")
        return _grouped(head, ".", ",")
    if delimiter == ";":
        if has_comma and not has_dot:
            return _plain_decimal(head, ",")
        if has_dot and not has_comma:
            return _grouped(head, ".", None)
        return head.isdigit()
    if has_dot and not has_comma:
        return _plain_decimal(head, ".")
    if has_comma and not has_dot:
        if _grouped(head, ",", None):
            return True
        return _plain_decimal(head, ",")
    return head.isdigit()


def _decimal_mark(has_dot: bool, has_comma: bool) -> Tuple[bool, Optional[str]]:
    if has_dot and has_comma:
        return False, None
    if has_dot:
        return True, "."
    if has_comma:
        return True, ","
    return True, None


def _grouped(head: str, thousands: str, decimal: Optional[str]) -> bool:
    if decimal is not None:
        if head.count(decimal) != 1:
            return False
        integer, fraction = head.split(decimal)
        if not fraction.isdigit() or fraction == "":
            return False
    else:
        integer = head
    return _grouped_integer(integer, thousands)


def _grouped_integer(integer: str, thousands: str) -> bool:
    if thousands not in integer:
        return integer.isdigit() and integer != ""
    parts = integer.split(thousands)
    if len(parts) < 2:
        return False
    first = parts[0]
    if not first.isdigit() or not 1 <= len(first) <= 3:
        return False
    return all(len(part) == 3 and part.isdigit() for part in parts[1:])


def _plain_decimal(head: str, mark: str) -> bool:
    if head.count(mark) != 1:
        return False
    integer, fraction = head.split(mark)
    if not integer.isdigit() or integer == "":
        return False
    if not fraction.isdigit() or fraction == "":
        return False
    return all(char.isdigit() or char == mark for char in head)


def _output_newline(text: str) -> str:
    crlf = text.count("\r\n")
    lone_lf = text.count("\n") - crlf
    if crlf >= 1 and crlf >= lone_lf:
        return "\r\n"
    return "\n"
