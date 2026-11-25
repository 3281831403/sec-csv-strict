"""Strict CSV reader exercise.

Every public function in this module is an intentionally unimplemented stub.
"""

from __future__ import annotations


def strip_bom(text: str) -> str:
    """Remove the byte-order mark at the very beginning of text.

    Only a leading run is normalized; U+FEFF occurring later must survive.
    """
    raise NotImplementedError


def split_rows(text: str) -> list:
    """Split text into records without ending a record inside quoted text.

    LF, CRLF and lone CR are record separators.  A newline inside a quoted
    field stays in that field.  A single ending record separator must not
    create an extra empty record.
    """
    raise NotImplementedError


def parse_row(row: str) -> list:
    """Parse one record into fields.

    Commas inside quotes do not separate fields.  Two double quotes inside a
    quoted field become one literal quote.  Whitespace and empty fields are
    preserved.  Malformed quoting raises ValueError.
    """
    raise NotImplementedError


def keep_empty_fields(fields: list) -> list:
    """Return the fields unchanged, including every trailing empty field."""
    raise NotImplementedError


def check_columns(rows: list, expected: int) -> list:
    """Return the 1-based row numbers whose width differs from expected."""
    raise NotImplementedError


def header_map(rows: list) -> dict:
    """Map each header name in the first row to its zero-based column index.

    Duplicate header names raise ValueError instead of overwriting an earlier
    entry.
    """
    raise NotImplementedError


def validate(text: str) -> list[str]:
    """Return human-readable issues found while parsing text.

    Issues cover unclosed quotes, illegal escapes or quotes, and rows whose
    width differs from the header width.
    """
    raise NotImplementedError


def csv_batch(texts: list[str], policy: dict) -> dict:
    """Parse every input document independently under policy.

    policy supports has_header, defaulting to True.  The returned dict has a
    files list; each item contains header, header_map, rows and issues.  No
    state, especially no header mapping, is shared between files.
    """
    raise NotImplementedError