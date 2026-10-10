"""Tests for CSV table formatting."""

import pytest

from csv_format import FormatError, format_csv, format_csv_with_delimiter

SPEC_INPUT = (
    "name;amount;city\n"
    'Alice;"1.234,56";Berlin\n'
    "Bob;42;Munich\n"
    "Cara;1 234,50 €;Paris\n"
)
SPEC_OUTPUT = (
    "name ; amount     ; city  \n"
    'Alice; "1.234,56" ; Berlin\n'
    "Bob  ;        42  ; Munich\n"
    "Cara ;  1 234,50 €; Paris \n"
)


def test_spec_example_aligns_digits_and_keeps_quotes() -> None:
    assert format_csv(SPEC_INPUT) == SPEC_OUTPUT


def test_format_twice_matches_once_for_auto_detect() -> None:
    once = format_csv(SPEC_INPUT)
    assert format_csv(once) == once


def test_format_twice_matches_once_for_forced_delimiter() -> None:
    source = "a;b,c\nd;e,f\n"
    once = format_csv(source, ";")
    assert format_csv(once, ";") == once


def test_detects_comma() -> None:
    assert format_csv("a,b\nc,d\n") == "a, b\nc, d\n"


def test_detects_semicolon() -> None:
    assert format_csv("a;b\nc;d\n") == "a; b\nc; d\n"


def test_detects_tab_without_padding_after_tab() -> None:
    assert format_csv("aa\tb\nc\tdd\n") == "aa\tb \nc \tdd\n"


def test_detects_pipe() -> None:
    assert format_csv("aa|b\nc|dd\n") == "aa| b \nc | dd\n"


def test_tie_break_prefers_comma() -> None:
    assert format_csv("a;b,c\nd;e,f\n") == "a;b, c\nd;e, f\n"


def test_quoted_delimiter_does_not_decide_detection() -> None:
    assert format_csv('"a,b",c\n"d,e",f\n') == '"a,b", c\n"d,e", f\n'


def test_explicit_delimiter_overrides_detection() -> None:
    source = "a;b,c\nd;e,f\n"
    assert format_csv(source, ";") == "a; b,c\nd; e,f\n"


def test_forced_delimiter_quotes_cells_that_contain_it() -> None:
    result = format_csv('a;"b;c"\nd;e\n', ";")
    assert result == 'a; "b;c"\nd; e    \n'


def test_currency_prefix_and_suffix_align_on_last_digit() -> None:
    result = format_csv("item,price\napple,$1.50\npear,20 €\n")
    assert result == "item , price  \napple, $1.50  \npear ,    20 €\n"


def test_scientific_notation_is_right_aligned() -> None:
    result = format_csv("n,v\na,1.2e-10\nb,-3E+6\n")
    assert result == "n, v      \na, 1.2e-10\nb,   -3E+6\n"


def test_us_thousands_and_decimal() -> None:
    result = format_csv('k,v\na,"1,234.56"\nb,2\n')
    assert '"1,234.56"' in result
    assert format_csv(result) == result


def test_quoted_german_decimal_in_comma_file_stays_quoted() -> None:
    result = format_csv('k,v\na,"1,50"\nb,2\n')
    assert result == 'k, v     \na, "1,50"\nb,     2 \n'


def test_comma_file_dot_decimal_and_quoted_thousands() -> None:
    result = format_csv('k,v\na,1.234\nb,"1,234"\n')
    assert result == 'k, v      \na,  1.234 \nb, "1,234"\n'


def test_semicolon_file_number_rules() -> None:
    result = format_csv("k;v\na;1.234\nb;1.23\nc;1,234\n")
    assert result == "k; v    \na; 1.234\nb; 1.23 \nc; 1,234\n"


def test_french_thousands_spaces_are_preserved() -> None:
    source = "k;v\na;1 234,56\nb;1\u00a0234,56\nc;1\u202f234,56\n"
    result = format_csv(source)
    assert result == (
        "k; v       \na; 1 234,56\nb; 1\u00a0234,56\nc; 1\u202f234,56\n"
    )
    assert "1 234,50\u00a0€" in format_csv("k;v\na;1 234,50\u00a0€\n")


def test_uneven_rows_gain_empty_cells() -> None:
    result = format_csv("a,b,c\nd,e\n")
    assert result == "a, b, c\nd, e,  \n"
    assert format_csv(result) == result


def test_blank_lines_stay_blank() -> None:
    assert format_csv("a,b\n\nc,d\n") == "a, b\n\nc, d\n"


def test_embedded_newline_stays_inside_quotes() -> None:
    result = format_csv('a,b\n"hello\nworld",x\n')
    assert '"hello\nworld"' in result
    assert format_csv(result) == result


@pytest.mark.parametrize("source", ["", "   ", "\n\n", " \t\n"])
def test_empty_input_raises(source: str) -> None:
    with pytest.raises(FormatError) as caught:
        format_csv(source)
    assert caught.value.reason == "empty"


def test_non_csv_raises() -> None:
    with pytest.raises(FormatError) as caught:
        format_csv("hello\nworld\n")
    assert caught.value.reason == "not_csv"


def test_forced_delimiter_without_columns_raises() -> None:
    with pytest.raises(FormatError) as caught:
        format_csv("hello\nworld\n", ",")
    assert caught.value.reason == "not_csv"


def test_unclosed_quote_raises() -> None:
    with pytest.raises(FormatError) as caught:
        format_csv('"hello,world\n')
    assert caught.value.reason == "unclosed_quote"


def test_unquoted_padding_is_trimmed_and_quoted_spaces_stay() -> None:
    assert format_csv("a  ,  b\n") == "a, b\n"
    result = format_csv('"  hi  ",b\n')
    assert '"  hi  "' in result
    assert format_csv(result) == result


def test_crlf_is_preserved_when_dominant() -> None:
    assert format_csv("a,b\r\nc,d\r\n") == "a, b\r\nc, d\r\n"


def test_trailing_newline_is_preserved() -> None:
    assert format_csv("a,b\nc,d\n").endswith("\n")
    assert not format_csv("a,b\nc,d").endswith("\n")


def test_single_quotes_are_kept_when_they_are_more_common() -> None:
    result = format_csv("'a','b'\n'c','d'\n")
    assert result == "'a', 'b'\n'c', 'd'\n"


def test_text_is_left_aligned() -> None:
    result = format_csv("name,city\nAl,Berlin\n")
    assert result == "name, city  \nAl  , Berlin\n"


def test_numbers_are_left_padded_to_the_header() -> None:
    result = format_csv("name,amount,city\nAlice,42,Berlin\nBob,1000,Munich\n")
    assert result == (
        "name , amount, city  \nAlice,     42, Berlin\nBob  ,   1000, Munich\n"
    )


def test_with_delimiter_reports_detected_delimiter() -> None:
    assert format_csv_with_delimiter("a;b\nc;d\n") == ("a; b\nc; d\n", ";")


def test_with_delimiter_reports_forced_delimiter() -> None:
    assert format_csv_with_delimiter("a|b\nc|d\n", "|") == ("a| b\nc| d\n", "|")


def test_rows_are_padded_to_the_table_width() -> None:
    result = format_csv("a,b,c\n1,2,3\n4,5\n")
    assert result == "a, b, c\n1, 2, 3\n4, 5,  \n"


def test_multi_line_cell_continues_under_its_opening_quote() -> None:
    result = format_csv('a,b,c\nlong text,"x\nyyyy",1\nc,dd,2\n')
    # The editor shows "yyyy" just after the opening quote, at column 12.
    assert result == (
        'a        , b     , c\nlong text, "x\nyyyy", 1\nc        , dd    , 2\n'
    )
    assert format_csv(result) == result
