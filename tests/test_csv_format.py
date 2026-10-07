"""Tests for CSV table formatting."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from csv_format import FormatError, format_csv  # noqa: E402


SPEC_INPUT = (
    "name;amount;city\n"
    'Alice;"1.234,56";Berlin\n'
    "Bob;42;Munich\n"
    "Cara;1 234,50 €;Paris\n"
)
SPEC_OUTPUT = (
    "name ; amount     ; city\n"
    'Alice; "1.234,56" ; Berlin\n'
    "Bob  ;        42  ; Munich\n"
    "Cara ;  1 234,50 €; Paris\n"
)


class FormatCsvTests(unittest.TestCase):
    def test_spec_example_aligns_digits_and_keeps_quotes(self) -> None:
        # Verify the worked example from the spec.
        self.assertEqual(format_csv(SPEC_INPUT), SPEC_OUTPUT)

    def test_format_twice_matches_once_for_auto_detect(self) -> None:
        # Verify padding from the first format is trimmed on the second.
        once = format_csv(SPEC_INPUT)
        self.assertEqual(format_csv(once), once)

    def test_format_twice_matches_once_for_forced_delimiter(self) -> None:
        # Verify a chosen delimiter stays stable across a second format.
        source = "a;b,c\nd;e,f\n"
        once = format_csv(source, ";")
        self.assertEqual(format_csv(once, ";"), once)

    def test_detects_comma(self) -> None:
        # Verify a comma-separated buffer keeps the comma.
        result = format_csv("a,b\nc,d\n")
        self.assertEqual(result, "a, b\nc, d\n")

    def test_detects_semicolon(self) -> None:
        # Verify a semicolon-separated buffer keeps the semicolon.
        result = format_csv("a;b\nc;d\n")
        self.assertEqual(result, "a; b\nc; d\n")

    def test_detects_tab_without_padding_after_tab(self) -> None:
        # Verify tabs stay the separator and gain no extra space.
        result = format_csv("aa\tb\nc\tdd\n")
        self.assertEqual(result, "aa\tb\nc \tdd\n")

    def test_detects_pipe(self) -> None:
        # Verify a pipe-separated buffer keeps the pipe.
        result = format_csv("aa|b\nc|dd\n")
        self.assertEqual(result, "aa| b\nc | dd\n")

    def test_tie_break_prefers_comma(self) -> None:
        # Verify comma wins when comma and semicolon score the same.
        result = format_csv("a;b,c\nd;e,f\n")
        self.assertEqual(result, "a;b, c\nd;e, f\n")

    def test_quoted_delimiter_does_not_decide_detection(self) -> None:
        # Verify a comma inside quotes is not an extra column.
        result = format_csv('"a,b",c\n"d,e",f\n')
        self.assertEqual(result, '"a,b", c\n"d,e", f\n')

    def test_explicit_delimiter_overrides_detection(self) -> None:
        # Verify a forced semicolon wins over the comma tie-break.
        source = "a;b,c\nd;e,f\n"
        self.assertEqual(format_csv(source, ";"), "a; b,c\nd; e,f\n")

    def test_forced_delimiter_quotes_cells_that_contain_it(self) -> None:
        # Verify a cell that contains the delimiter stays quoted.
        result = format_csv('a;"b;c"\nd;e\n', ";")
        self.assertEqual(result, 'a; "b;c"\nd; e\n')

    def test_currency_prefix_and_suffix_align_on_last_digit(self) -> None:
        # Verify currency stays in the cell and last digits share a column.
        result = format_csv("item,price\napple,$1.50\npear,20 €\n")
        self.assertEqual(result, "item , price\napple, $1.50\npear ,    20 €\n")

    def test_scientific_notation_is_right_aligned(self) -> None:
        # Verify scientific values align on the last digit.
        result = format_csv("n,v\na,1.2e-10\nb,-3E+6\n")
        self.assertEqual(result, "n, v\na, 1.2e-10\nb,   -3E+6\n")

    def test_us_thousands_and_decimal(self) -> None:
        # Verify 1,234.56 stays written the same way and aligns as a number.
        result = format_csv('k,v\na,"1,234.56"\nb,2\n')
        self.assertIn('"1,234.56"', result)
        self.assertEqual(format_csv(result), result)

    def test_quoted_german_decimal_in_comma_file_stays_quoted(self) -> None:
        # Verify 1,50 is a number and the quotes are not removed.
        result = format_csv('k,v\na,"1,50"\nb,2\n')
        self.assertEqual(result, 'k, v\na, "1,50"\nb,     2\n')

    def test_comma_file_dot_decimal_and_quoted_thousands(self) -> None:
        # Verify 1.234 is decimal and "1,234" is a thousands number.
        result = format_csv('k,v\na,1.234\nb,"1,234"\n')
        self.assertEqual(result, 'k, v\na,  1.234\nb, "1,234"\n')

    def test_semicolon_file_number_rules(self) -> None:
        # Verify German thousands, a non-number, and a comma decimal.
        result = format_csv("k;v\na;1.234\nb;1.23\nc;1,234\n")
        self.assertEqual(result, "k; v\na; 1.234\nb; 1.23\nc; 1,234\n")

    def test_french_thousands_spaces_are_preserved(self) -> None:
        # Verify regular, no-break, and narrow no-break spaces stay put.
        source = "k;v\na;1 234,56\nb;1\u00a0234,56\nc;1\u202f234,56\n"
        result = format_csv(source)
        self.assertEqual(
            result,
            "k; v\na; 1 234,56\nb; 1\u00a0234,56\nc; 1\u202f234,56\n",
        )
        self.assertIn("1 234,50\u00a0€", format_csv("k;v\na;1 234,50\u00a0€\n"))

    def test_uneven_rows_gain_empty_cells(self) -> None:
        # Verify a short row is padded with an empty cell.
        result = format_csv("a,b,c\nd,e\n")
        self.assertEqual(result, "a, b, c\nd, e,\n")
        self.assertEqual(format_csv(result), result)

    def test_blank_lines_stay_blank(self) -> None:
        # Verify a blank line is not turned into empty cells.
        result = format_csv("a,b\n\nc,d\n")
        self.assertEqual(result, "a, b\n\nc, d\n")

    def test_embedded_newline_stays_inside_quotes(self) -> None:
        # Verify a quoted newline is still inside the quotes.
        result = format_csv('a,b\n"hello\nworld",x\n')
        self.assertIn('"hello\nworld"', result)
        self.assertEqual(format_csv(result), result)

    def test_empty_input_raises(self) -> None:
        # Verify whitespace-only buffers are rejected.
        for source in ("", "   ", "\n\n", " \t\n"):
            with self.assertRaises(FormatError) as caught:
                format_csv(source)
            self.assertEqual(caught.exception.reason, "empty")

    def test_non_csv_raises(self) -> None:
        # Verify a single column is not a table.
        with self.assertRaises(FormatError) as caught:
            format_csv("hello\nworld\n")
        self.assertEqual(caught.exception.reason, "not_csv")

    def test_forced_delimiter_without_columns_raises(self) -> None:
        # Verify an explicit delimiter still has to produce a table.
        with self.assertRaises(FormatError) as caught:
            format_csv("hello\nworld\n", ",")
        self.assertEqual(caught.exception.reason, "not_csv")

    def test_unclosed_quote_raises(self) -> None:
        # Verify a missing closing quote is reported.
        with self.assertRaises(FormatError) as caught:
            format_csv('"hello,world\n')
        self.assertEqual(caught.exception.reason, "unclosed_quote")

    def test_unquoted_padding_is_trimmed_and_quoted_spaces_stay(self) -> None:
        # Verify padding spaces are removed and spaces inside quotes remain.
        self.assertEqual(format_csv("a  ,  b\n"), "a, b\n")
        result = format_csv('"  hi  ",b\n')
        self.assertIn('"  hi  "', result)
        self.assertEqual(format_csv(result), result)

    def test_crlf_is_preserved_when_dominant(self) -> None:
        # Verify Windows newlines are written back.
        result = format_csv("a,b\r\nc,d\r\n")
        self.assertEqual(result, "a, b\r\nc, d\r\n")

    def test_trailing_newline_is_preserved(self) -> None:
        # Verify a final newline is kept and a missing one is not added.
        self.assertTrue(format_csv("a,b\nc,d\n").endswith("\n"))
        self.assertFalse(format_csv("a,b\nc,d").endswith("\n"))

    def test_single_quotes_are_kept_when_they_are_more_common(self) -> None:
        # Verify single-quoted fields are not rewritten with double quotes.
        result = format_csv("'a','b'\n'c','d'\n")
        self.assertEqual(result, "'a', 'b'\n'c', 'd'\n")

    def test_text_is_left_aligned(self) -> None:
        # Verify a short word stays at the left of a wider column.
        result = format_csv("name,city\nAl,Berlin\n")
        self.assertEqual(result, "name, city\nAl  , Berlin\n")


if __name__ == "__main__":
    unittest.main()
