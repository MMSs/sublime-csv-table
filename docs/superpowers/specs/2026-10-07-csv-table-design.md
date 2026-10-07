# Format CSV Table

Sublime Text 4 plugin with one command-palette entry, **Format CSV Table**. It formats the current buffer as an aligned CSV table and sets the syntax to CSV.

## Decisions

- Quote-aware parse and write with no third-party packages. The reader is custom, because it must remember whether each field was quoted. `csv.reader` does not expose that, and `csv.writer` cannot keep an already-quoted number quoted while leaving other numbers bare. Escaping matches Python's `csv` module: the quote character is doubled.
- The formatter does not import Sublime, so tests run under normal Python 3.8.
- The plugin ships its own CSV syntax. Sublime Text does not include one.
- One palette command. It opens a quick panel so the delimiter can be overridden. Enter on the first item keeps auto-detect.
- Cells are padded with spaces. Text is left-aligned. Numbers are right-aligned on the last digit.
- Formatting again trims padding that this command added. Quoted interiors are never rewritten.
- Thousands separators may be commas, dots, or spaces (French), including no-break spaces. Detection follows the rules below. The characters in a cell stay as they are.

## Package

The repository root is the package. Installed folder name is exactly `CSV Table`, because the syntax path includes it.

```
csv_format.py
csv_table.py
CSV.sublime-syntax
Default.sublime-commands
README.md
tests/test_csv_format.py
```

`csv_format.py` has no import-time side effects. Sublime loads every top-level `.py` file; this module only defines functions. Tests live in a subdirectory, which Sublime does not load as plugins.

`Default.sublime-commands` contains one entry:

```json
[
    {
        "caption": "Format CSV Table",
        "command": "format_csv_table"
    }
]
```

## Command

`FormatCsvTableCommand` is a `TextCommand`.

It reads the whole buffer, not the selection and not the file on disk. The buffer does not need a `.csv` name.

The quick panel items, in order, are:

1. Auto-detect
2. Comma (,)
3. Semicolon (;)
4. Tab
5. Pipe (|)

Dismissing the panel changes nothing and shows no status message. If the view has no window, the command returns without changing anything.

On success the command replaces the entire buffer in a single edit, so one undo restores the previous text. It does not try to keep the cursor. It then sets the syntax with:

```text
view.assign_syntax("Packages/CSV Table/CSV.sublime-syntax")
```

Status messages:

| Outcome | Status bar |
| --- | --- |
| Success | `CSV Table: formatted` |
| Empty or whitespace-only buffer | `CSV Table: nothing to format` |
| No delimiter yields a table, or the forced delimiter does not | `CSV Table: not a CSV table` |
| Unclosed quote | `CSV Table: unclosed quote` |

Failures leave the buffer text and the current syntax unchanged.

## Formatter API

```python
class FormatError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason  # "empty", "not_csv", or "unclosed_quote"

def format_csv(text: str, delimiter: Optional[str] = None) -> str:
    """Return aligned CSV. delimiter None auto-detects. Raises FormatError."""
```

Target Python 3.8 (`Optional`, no `str | None`, no `match`).

`format_csv(format_csv(text, delimiter), delimiter) == format_csv(text, delimiter)` for the same delimiter choice, including auto-detect.

## Pipeline

1. If the buffer is empty or whitespace only, raise `FormatError("empty")`.
2. Choose the quote character.
3. Choose the delimiter (argument, or auto-detect).
4. Parse records. Remember whether each field was quoted. Keep each interior exactly.
5. Classify each field as text or number.
6. Render each field, then align columns.
7. Join rows with the chosen line ending.
8. Keep a final newline only if the input had one.

## Quote character

Default is `"`. Use `'` only when more fields are wrapped in single quotes than in double quotes. A wrapped field starts and ends with that quote and may contain doubled quotes inside. Escaping is always doubling. The quote character is never changed on output.

## Delimiter

Candidates, in tie-break order: comma `,`, semicolon `;`, tab `\t`, pipe `|`.

Auto-detect scans outside quotes. For each candidate, skip blank lines and count field counts. A candidate qualifies only when its most common field count is at least 2. The winner is the qualifier with the most records at that count. If one candidate has two field counts tied for most common, the larger count wins. Ties between candidates use the order above.

A forced delimiter skips detection. It still has to produce at least one non-empty record with 2 or more fields. Otherwise raise `FormatError("not_csv")`. The same error is raised when no candidate qualifies.

Forcing a delimiter rewrites separators only. Interiors stay character for character. A field gains quotes only when the new delimiter, the quote character, or a newline appears inside it. Quotes that were already there are never removed.

The space this formatter inserts after `,`, `;`, and `|` is padding, not part of the delimiter. Detection on an already formatted buffer returns the same delimiter.

## Parsing and whitespace

Unclosed quotes raise `FormatError("unclosed_quote")`.

A line with no characters is a blank line. Blank lines are preserved and are not rows of empty cells. A line that contains a delimiter and nothing else is a row of empty cells.

U+0020 characters between a delimiter and an opening quote are padding. They are not part of the interior. The same is true of U+0020 between a closing quote and the next delimiter. The next format strips that padding and writes it again.

Rows may have different lengths. Missing cells are empty. Extra cells extend the table.

A newline inside a quoted field stays inside the quotes. Rows after that embedded newline will not line up visually. That is still success.

Unquoted fields: strip leading and trailing spaces (U+0020 only) before classifying and rendering. That removes padding from an earlier format. Other characters, including no-break spaces that belong to a French number, stay.

Quoted fields: the interior is not stripped and not edited. Classification may ignore surrounding whitespace when deciding "is this a number?", but the characters written back are the original interior, quotes included.

## Quoting on output

A field is written in quotes when any of these is true:

- it was quoted in the input
- it contains the delimiter, the quote character, or a newline

Padding spaces are outside the quotes. The interior bytes are unchanged, so a German or French number is not rewritten into another format.

## Numbers

Classification looks at the interior. For the test only, surrounding whitespace (U+0020, U+00A0, U+202F) is ignored. The stored text is not changed.

A cell is a number when it matches the grammar below. Otherwise it is text. These are text: dates, percents (`12%`), parentheses for negatives, more than one currency symbol, currency on both sides, and a header word.

A header that is itself a number (`2024`) is right-aligned. Headers get no special case.

### Shape

At most one sign (`+` or `-`) and at most one currency symbol (`$` `€` `£` `¥`).

The sign sits at the start, or between a prefix currency and the digits (`-42`, `-$42`, `$-42`).

The currency symbol is a prefix or a suffix, not both. One space may separate the symbol from the number. That space may be U+0020, U+00A0, or U+202F, and it is preserved (`$42`, `$ 42`, `$ -42`, `42 €`, `1234,56€`). No wider gap is allowed.

### Body

The body is an integer, an optional decimal part, and an optional exponent `[eE][+-]?\d+`.

The integer is either plain digits, or groups with one consistent thousands separator:

- the first group is 1 to 3 digits
- every following group is exactly 3 digits
- the separator is the same throughout the cell

Thousands separators:

- `.`
- `,`
- U+0020 space
- U+00A0 no-break space
- U+202F narrow no-break space

`1  234` (two spaces) is text. `1 234` is a number. `1 23` is text.

The decimal mark is `.` or `,` and must differ from the thousands separator. The exponent never contains a thousands separator.

### Which mark means what

Apply the first match:

1. **Space thousands.** If the integer uses a whitespace thousands separator, a `.` or `,` after it is the decimal mark, even when three digits follow (`1 234,567`, `1 234.56`). This is independent of the file delimiter. Regular space, no-break space, and narrow no-break space all count, and they are preserved.
2. **Both `.` and `,`.** The rightmost one is the decimal mark. The other must be a thousands separator in groups of three (`1.234,56` and `1,234.56`). This applies in every file, including a comma-delimited file where the German form is quoted.
3. **Semicolon files, only one of `.` or `,`.** Comma is the decimal mark, with any number of fraction digits (`1,25`, `1,234` meaning one and 234 thousandths). Dot is a thousands separator and must fall in groups of three (`1.234` is a number, `1.23` is text).
4. **Every other delimiter, only one of `.` or `,`.** Dot is the decimal mark, with any number of fraction digits (`1.234` is one point two three four). Comma is a thousands separator in groups of three (`1,234` is a number). A comma that is not groups of three is a decimal mark instead (`1,50`, `1,2345`), which is how a quoted German decimal survives in a comma-delimited file. `1,234` matches groups of three, so it stays a thousands integer, not a three-place German decimal.

Scientific examples that are numbers: `1.2e-10`, `-3E+6`, `6.02e23`, `1,2e-10`. The integer part may use thousands separators. The exponent may not.

## Alignment

Column width is measured on the rendered form (quotes and padding included).

Text and empty cells are left-aligned and padded with U+0020 on the right.

Numeric cells align on the last digit character, not on the last character. A closing quote, a currency suffix, and any characters after the last digit hang to the right of that digit column. Shorter hangs are padded with spaces so every cell in the column has the same width. A prefix currency, an opening quote, and the sign sit to the left of the digits and are included in the left side when the digit column is chosen.

Take each numeric cell in its rendered form before padding. The digit column is the largest last-digit index among those cells. Left padding then moves every shorter number's last digit onto that column.

Join cells with the delimiter. For comma, semicolon, and pipe, add one U+0020 after the delimiter. For tab, the separator is the tab alone.

Then strip trailing U+0020 from each output line. That only shortens the last column's trailing pad. Digit columns and earlier delimiters stay put. The next format pads again.

Worked example. Input:

```text
name;amount;city
Alice;"1.234,56";Berlin
Bob;42;Munich
Cara;1 234,50 €;Paris
```

Output:

```text
name ; amount     ; city
Alice; "1.234,56" ; Berlin
Bob  ;        42  ; Munich
Cara ;  1 234,50 €; Paris
```

Semicolons are in the same columns. The last digits of `6`, `2`, and `0` are in the same column. The quotes around `1.234,56` remain. `42` stays unquoted. The euro and the French space stay in the cell.

## Line endings

If the input has at least one `\r\n` and the number of `\r\n` breaks is greater than or equal to the number of lone `\n` breaks, write `\r\n`. Otherwise write `\n`. A file that uses only bare `\r` is written with `\n`.

If the input ends with a newline, the output ends with the chosen newline. If it does not, the output does not gain one.

## Syntax definition

`CSV.sublime-syntax` sets the name `CSV` and the scope `text.csv`. It highlights double-quoted and single-quoted fields, including doubled quotes inside them. It does not need to know which delimiter the buffer uses.

## Tests

`python3 -m unittest discover -s tests` from the repository root. No test dependencies.

`tests/test_csv_format.py` covers:

- detection of comma, semicolon, tab, and pipe
- tie-break toward comma
- a quoted delimiter does not decide detection
- an explicit delimiter argument
- formatting twice is stable for auto-detect and for a forced delimiter
- text left, numbers right, last digits aligned
- currency prefix and suffix
- scientific notation
- US `1,234.56`
- quoted German `"1.234,56"` kept quoted, digits aligned with an unquoted `42`
- quoted `"1,50"` in a comma-delimited file recognized as a number and not unwrapped
- semicolon file: `1.234` is a number, `1.23` is text, `1,234` is a decimal number
- comma file: `1.234` is a decimal number, `"1,234"` is a thousands number
- French `1 234,56` with U+0020, U+00A0, and U+202F, characters unchanged, including a no-break space before a currency suffix
- a forced delimiter adds quotes only around cells that contain it
- uneven rows
- blank lines stay blank and are not turned into empty cells
- an embedded newline stays inside quotes
- empty input, non-CSV input, and an unclosed quote raise `FormatError` with the reasons `empty`, `not_csv`, and `unclosed_quote`
- unquoted padding is trimmed; spaces inside quotes are kept
- CRLF is preserved when it is the dominant break
- a trailing newline is preserved, and a missing one is not added

The Sublime command class is not unit-tested. The README states the manual check: open a buffer, run the command, confirm alignment, undo once, and confirm the syntax name is CSV.

## Install

Document this in `README.md` for Sublime Text 4. No Package Control package.

The installed directory must be named `CSV Table`. Symlink the repository (do not rename the files inside it).

macOS:

```bash
ln -s /path/to/sublime-csv-table "$HOME/Library/Application Support/Sublime Text/Packages/CSV Table"
```

Linux:

```bash
ln -s /path/to/sublime-csv-table "$HOME/.config/sublime-text/Packages/CSV Table"
```

Windows, from an elevated command prompt:

```bat
mklink /D "%APPDATA%\Sublime Text\Packages\CSV Table" "C:\path\to\sublime-csv-table"
```

Sublime loads an unpacked package as soon as the folder appears. If **Format CSV Table** is missing from the command palette, restart Sublime.

Run it from the command palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` on Linux and Windows), choose Auto-detect or a delimiter, and save the buffer when the result looks right.

## Out of scope

- Sublime Text 3
- A second command, a menu item, or a key binding
- Formatting only the selection
- Rewriting numbers into a canonical locale
- Percent values, parenthesized negatives, and date detection
- A header underline or a frozen header row
- Publishing to Package Control
