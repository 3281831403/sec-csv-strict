"""Strict CSV reader exercise.

The implementation is a small, dependency-free, quote-aware parser.  The
public functions are kept independent so each parsing guarantee can be tested
on its own; ``csv_batch`` wires them together without sharing any per-file
state.
"""

from __future__ import annotations

BOM = "\ufeff"  # U+FEFF byte-order mark / zero-width no-break space


def strip_bom(text: str) -> str:
    """Remove the byte-order mark at the very beginning of text.

    Only a leading run is normalized; U+FEFF occurring later must survive.
    """
    # Defects 1 & 2: drop the *entire* run of leading BOMs (not just one),
    # while leaving any U+FEFF in the body untouched.
    index = 0
    length = len(text)
    while index < length and text[index] == BOM:
        index += 1
    return text[index:]


def split_rows(text: str) -> list:
    """Split text into records without ending a record inside quoted text.

    LF, CRLF and lone CR are record separators.  A newline inside a quoted
    field stays in that field.  A single ending record separator must not
    create an extra empty record.
    """
    if text == "":
        return []

    rows: list[str] = []
    buffer: list[str] = []
    in_quotes = False
    at_field_start = True
    index = 0
    length = len(text)

    while index < length:
        char = text[index]

        if in_quotes:
            if char == '"':
                if index + 1 < length and text[index + 1] == '"':
                    # Doubled quote inside a quoted field: an escaped quote.
                    # Preserve the raw pair here; parse_row collapses it.
                    buffer.append('""')
                    index += 2
                    continue
                # Any other quote closes the quoted field.
                in_quotes = False
                at_field_start = False
                buffer.append(char)
                index += 1
                continue
            # Newlines (LF/CR/CRLF) fall through to plain accumulation here,
            # so separators inside quotes stay part of the field verbatim.
            buffer.append(char)
            index += 1
            continue

        # A quote only opens a quoted field when it is the first character of
        # a field.  A stray quote elsewhere is left for parse_row to reject
        # and must not swallow following newlines.
        if char == '"' and at_field_start:
            in_quotes = True
            at_field_start = False
            buffer.append(char)
            index += 1
            continue

        if char == ",":
            at_field_start = True
            buffer.append(char)
            index += 1
            continue

        if char == "\r" or char == "\n":
            # Defect 3 / convention 14: only newlines *outside* quotes reach
            # this branch.  CRLF is a single separator, not two.
            rows.append("".join(buffer))
            buffer = []
            at_field_start = True
            if char == "\r" and index + 1 < length and text[index + 1] == "\n":
                index += 2
            else:
                index += 1
            continue

        at_field_start = False
        buffer.append(char)
        index += 1

    tail = "".join(buffer)
    # Defect 6: when the text ends with a record separator the buffer is empty
    # and the preceding record was already appended, so do not append a
    # phantom empty record.  A non-empty tail is the final unterminated row.
    if tail != "":
        rows.append(tail)

    return rows


def parse_row(row: str) -> list:
    """Parse one record into fields.

    Commas inside quotes do not separate fields.  Two double quotes inside a
    quoted field become one literal quote.  Whitespace and empty fields are
    preserved.  Malformed quoting raises ValueError.
    """
    fields: list[str] = []
    buffer: list[str] = []
    index = 0
    length = len(row)

    # start  -> no character has been consumed for the current field
    # bare   -> inside an unquoted field
    # quoted -> inside an opening quote
    # closed -> the closing quote was seen; only ',' or end may follow
    state = "start"

    while index < length:
        char = row[index]

        if state == "start":
            if char == '"':
                state = "quoted"
            elif char == ",":
                # Empty field before this comma.
                fields.append("")
            else:
                buffer.append(char)
                state = "bare"
            index += 1
            continue

        if state == "bare":
            if char == ",":
                fields.append("".join(buffer))
                buffer = []
                state = "start"
            elif char == '"':
                # Convention: a quote is only legal at field start.
                raise ValueError(
                    "非法引号：未加引号的字段内容中不能出现双引号，"
                    "引号只能位于字段开头"
                )
            else:
                # Whitespace and every other character are preserved.
                buffer.append(char)
            index += 1
            continue

        if state == "quoted":
            if char == '"':
                if index + 1 < length and row[index + 1] == '"':
                    # Defect 4: "" -> one literal ".
                    buffer.append('"')
                    index += 2
                    continue
                # Single quote closes the field.
                state = "closed"
            else:
                buffer.append(char)
            index += 1
            continue

        # state == "closed"
        if char == ",":
            fields.append("".join(buffer))
            buffer = []
            state = "start"
            index += 1
        else:
            # Defect 9: anything but comma/end after the closing quote is an
            # illegal escape/quote sequence (e.g. "ok"x).
            raise ValueError(
                "非法转义：结束引号之后只允许逗号或行尾，"
                f"但在 {char!r} 处遇到普通字符"
            )

    if state == "quoted":
        raise ValueError("未闭合引号：引号字段缺少结束双引号")

    # Defect 5: always flush the current field.  When the row ends in a comma
    # state is "start" with an empty buffer, and this flush is exactly the
    # trailing empty field that must survive (a,b, -> ['a','b','']).
    fields.append("".join(buffer))
    return keep_empty_fields(fields)


def keep_empty_fields(fields: list) -> list:
    """Return the fields unchanged, including every trailing empty field."""
    # Identity on purpose: never trim trailing empties and never pad.
    return fields


def check_columns(rows: list, expected: int) -> list:
    """Return the 1-based row numbers whose width differs from expected."""
    # Defect 7: report ragged rows instead of silently padding/truncating.
    return [
        row_number
        for row_number, row in enumerate(rows, start=1)
        if len(row) != expected
    ]


def header_map(rows: list) -> dict:
    """Map each header name in the first row to its zero-based column index.

    Duplicate header names raise ValueError instead of overwriting an earlier
    entry.
    """
    if not rows:
        return {}

    mapping: dict = {}
    for column_index, name in enumerate(rows[0]):
        # Defect 8: reject duplicates rather than letting the later column
        # silently overwrite the earlier index.
        if name in mapping:
            raise ValueError(f"重复列名：{name!r} 在表头中出现了多次")
        mapping[name] = column_index
    return mapping


def _parse_document(text: object, has_header: bool) -> dict:
    """Parse one document with fully local state.

    Shared by validate() and csv_batch(); every call builds a fresh header
    mapping so batch files can never inherit each other's columns.
    """
    entry = {"header": [], "header_map": {}, "rows": [], "issues": []}

    if text is None:
        return entry

    cleaned = strip_bom(str(text))
    records = split_rows(cleaned)
    if not records:
        # Convention 15: empty input -> empty everything, no issues.
        return entry

    data_start = 0
    expected_width: int | None = None

    if has_header:
        data_start = 1
        try:
            header = parse_row(records[0])
        except ValueError as error:
            entry["issues"].append(f"第1行表头解析失败：{error}")
            header = []

        entry["header"] = header
        expected_width = len(header) if header else None
        if header:
            try:
                entry["header_map"] = header_map([header])
            except ValueError as error:
                # Keep the strict guarantee of header_map while giving batch
                # callers a per-file issue instead of aborting the batch.
                entry["issues"].append(f"第1行表头错误：{error}")

    for record_number, raw_record in enumerate(
        records[data_start:], start=data_start + 1
    ):
        try:
            fields = parse_row(raw_record)
        except ValueError as error:
            # validate() must never let a malformed record escape.
            entry["issues"].append(f"第{record_number}行：{error}")
            continue

        # Short rows are kept exactly as parsed (no default padding).
        entry["rows"].append(fields)

        if expected_width is not None and len(fields) != expected_width:
            entry["issues"].append(
                f"第{record_number}行列数不符："
                f"表头为 {expected_width} 列，本行实际为 {len(fields)} 列"
            )

    return entry


def validate(text: str) -> list[str]:
    """Return human-readable issues found while parsing text.

    Issues cover unclosed quotes, illegal escapes or quotes, and rows whose
    width differs from the header width.  Never raises for parse problems.
    """
    return _parse_document(text, has_header=True)["issues"]


def csv_batch(texts: list[str], policy: dict) -> dict:
    """Parse every input document independently under policy.

    policy supports has_header, defaulting to True.  The returned dict has a
    files list; each item contains header, header_map, rows and issues.  No
    state, especially no header mapping, is shared between files.
    """
    config = policy if isinstance(policy, dict) else {}
    has_header = config.get("has_header", True)

    # Defect 10: each element is produced by an independent function call with
    # only local variables, so the second file cannot reuse the first map.
    files = [_parse_document(text, has_header) for text in texts]
    return {"files": files}
