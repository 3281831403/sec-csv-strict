"""Strict acceptance tests for engine.csv.reader."""

from __future__ import annotations

import pytest

from engine.csv import reader

POLICY = {"has_header": True}


def test_bom_is_stripped_from_first_header_cell() -> None:
    assert reader.strip_bom("\ufeffname") == "name"
    batch = reader.csv_batch(["\ufeffname,age\nAlice,30\n"], POLICY)
    assert batch["files"][0]["header"] == ["name", "age"]


def test_repeated_leading_bom_is_removed() -> None:
    assert reader.strip_bom("\ufeff\ufeffname") == "name"
    assert reader.strip_bom("na\ufeffme") == "na\ufeffme"


def test_newline_inside_quotes_does_not_split_row() -> None:
    text = 'a,"b\r\nc",d\r\n'
    assert reader.split_rows(text) == ['a,"b\r\nc",d']


def test_doubled_quote_becomes_one_quote() -> None:
    assert reader.parse_row('"a""b",c') == ['a"b', "c"]


def test_trailing_empty_field_is_kept_by_helper() -> None:
    assert reader.keep_empty_fields(["a", "b", ""]) == ["a", "b", ""]
    assert reader.parse_row("a,b,") == ["a", "b", ""]


def test_terminal_newline_creates_no_empty_data_row() -> None:
    result = reader.csv_batch(["name,age\r\nAlice,30\r\n"], POLICY)
    assert result["files"][0]["rows"] == [["Alice", "30"]]


def test_ragged_row_is_reported_and_not_padded() -> None:
    rows = [["name", "age"], ["Alice", "30"], ["Bob"]]
    assert reader.check_columns(rows, 2) == [3]

    issues = reader.validate("name,age\nAlice,30\nBob\n")
    assert any("列数不符" in issue for issue in issues)

    result = reader.csv_batch(["name,age\nAlice,30\nBob\n"], POLICY)
    assert result["files"][0]["rows"] == [["Alice", "30"], ["Bob"]]
    assert any("列数不符" in issue for issue in result["files"][0]["issues"])


def test_duplicate_header_is_rejected_not_overwritten() -> None:
    with pytest.raises(ValueError):
        reader.header_map([["name", "name"], ["A", "B"]])


def test_illegal_escape_is_reported() -> None:
    issues = reader.validate('name,note\nAlice,"ok"x\n')
    assert any("非法转义" in issue for issue in issues)


def test_batch_headers_are_independent() -> None:
    result = reader.csv_batch(
        ["name,qty\nA,1\n", "sku,total\nB,2\n"],
        POLICY,
    )
    assert result["files"][0]["header"] == ["name", "qty"]
    assert result["files"][0]["header_map"] == {"name": 0, "qty": 1}
    assert result["files"][1]["header"] == ["sku", "total"]
    assert result["files"][1]["header_map"] == {"sku": 0, "total": 1}


def test_simple_two_rows_two_columns() -> None:
    result = reader.csv_batch(["name,age\nAlice,30\nBob,25\n"], POLICY)
    assert result["files"][0]["header"] == ["name", "age"]
    assert result["files"][0]["rows"] == [["Alice", "30"], ["Bob", "25"]]


def test_comma_inside_quotes_is_not_a_separator() -> None:
    assert reader.parse_row('"Doe, Jane",42') == ["Doe, Jane", "42"]


def test_newline_inside_quotes_stays_in_one_field() -> None:
    assert reader.parse_row('"line1\nline2",x') == ["line1\nline2", "x"]


def test_trailing_empty_field_survives_batch_parse() -> None:
    result = reader.csv_batch(["a,b,c\n1,2,\n"], POLICY)
    assert result["files"][0]["header"] == ["a", "b", "c"]
    assert result["files"][0]["rows"] == [["1", "2", ""]]


def test_batch_results_match_separate_single_file_runs() -> None:
    first = "name,age\nAlice,30\n"
    second = "city,zip\nParis,75001\n"
    combined = reader.csv_batch([first, second], POLICY)
    alone_first = reader.csv_batch([first], POLICY)["files"][0]
    alone_second = reader.csv_batch([second], POLICY)["files"][0]
    assert combined["files"] == [alone_first, alone_second]