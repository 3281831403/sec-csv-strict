批量导入的表格文件里带引号的字段被截断，行尾空字段还悄悄少了一列：字节序标记不去除导致首列表头带隐藏字符；字节序标记出现两次时不去重导致第二处残留；按所有换行切分导致引号内换行被当成新行；双引号转义不处理导致连续两个引号原样保留；行尾空字段被裁剪导致列数少一；末尾换行产生一条空行并被当成数据行；列数不一致不报错且短行按缺省空值补齐；表头重复列名时后者覆盖前者；非法转义中的引号后跟普通字符被接受；批量解析复用表头映射导致第二个文件沿用第一个文件的列名。engine/csv/reader.py 是核心，tests/csv/test_reader.py 15个红。要修的是：按上面的顺序把 10 个缺陷逐个修掉。

## 题目定位

安全方向的解析边界题，同时覆盖漏洞检测与攻防中的输入变形，以及 Bugfix 场景中的静默数据损坏。语言与测试栈为 Python 3, pytest，无外部依赖。

| 字段 | 内容 |
| --- | --- |
| 安全 | 是 |
| 漏洞检测与攻防 | 是 |
| Bugfix | 是 |
| 语言与测试 | Python 3, pytest |
| 外部依赖 | 无 |

## 目录结构

```text
sec-csv-strict/
├── README.md
├── conftest.py
├── engine/
│   ├── __init__.py
│   └── csv/
│       ├── __init__.py
│       └── reader.py
└── tests/
    └── csv/
        └── test_reader.py
```

## engine 嵌套布局说明

engine 是顶层 Python 包，csv 是 engine 下的子包，导入路径固定为 from engine.csv import reader。conftest.py 把仓库根目录放入 sys.path，因此从仓库根运行 pytest 时无需安装包。不要新增顶层 csv.py 或 reader.py，也不要把 reader.py 放到 tests 下；唯一实现文件就是 engine/csv/reader.py，其中恰好保留 8 个桩，全部 raise NotImplementedError。

## 运行方式

在仓库根目录执行：

```powershell
python -m pytest tests -q
```

首次运行应恰好得到 15 failed，且 15 条失败全部来自 engine/csv/reader.py 的 NotImplementedError；不应出现 import error、syntax error 或 collection error。

```text
15 failed in 0.06s
```

## 接口约定

- strip_bom(text) -> str：只在文本绝对开头做一次 BOM 归一化，连续出现的 U+FEFF 全部清除；正文中间的 U+FEFF 不动。
- split_rows(text) -> list：按 LF、CRLF 或单独 CR 切记录；引号内的换行不切；单条末尾换行只终止最后一条记录，不追加空记录。
- parse_row(row) -> list：按逗号切字段；引号内的逗号不切；引号内的两个双引号合并为一个双引号；空白与空字段原样保留；非法引号或非法转义抛出 ValueError。
- keep_empty_fields(fields) -> list：原样返回字段列表，包括所有行尾空字段，不裁剪、不补默认值。
- check_columns(rows, expected) -> list：rows 为已解析字段列表；返回列数不等于 expected 的 1 基行号，升序。
- header_map(rows) -> dict：第一行是表头；返回列名到 0 基下标的映射；重复列名抛出 ValueError，不能后者覆盖前者。
- validate(text) -> list[str]：返回问题描述列表；覆盖未闭合引号、非法转义或非法引号、列数不符；列数期望值取表头宽度；不向调用方抛解析异常。
- csv_batch(texts, policy) -> dict：policy 支持 has_header，默认 True；每个文件独立去 BOM、切行、解析表头并建立自己的 header_map；返回 files 列表，每项含 header、header_map、rows、issues；短行保留原样并写入 issues，绝不复用前一个文件的表头映射。

csv_batch 的返回形状：

```python
{
    "files": [
        {
            "header": ["name", "age"],
            "header_map": {"name": 0, "age": 1},
            "rows": [["Alice", "30"]],
            "issues": []
        }
    ]
}
```

## 边角约定逐条

1. 字节序标记：U+FEFF 只在首部清除，首列字段不得残留隐藏字符；正文中间出现的 U+FEFF 必须保留。
2. 重复字节序标记：首部连续两个 U+FEFF 必须全部清除，不能只清一个而让第二个残留。
3. 引号内换行：引号内的 LF 或 CRLF 属于字段内容，不能当作记录边界；字段内保留原始换行序列。
4. 双引号转义：引号字段内的两个连续双引号表示一个字面双引号，不能被原样保留为两个字符。
5. 行尾空字段：a,b, 这种行必须解析为三个字段，最后一个为空字符串；禁止裁剪行尾空字段。
6. 末尾换行：文件末尾的单条换行只结束最后一条记录，不能生成一条空数据行，也不能把它当作列数不符的数据。
7. 列数不一致：短行不补齐缺省空值，长行不截断；check_columns 返回 1 基行号，validate 和 csv_batch 的 issues 必须报告列数不符。
8. 表头重复：重复列名必须抛出 ValueError，不能静默采用后一个下标而丢失前一个列名。
9. 非法转义：结束引号后只允许逗号或行尾；引号后跟普通字符属于非法转义，不能让解析器接受。
10. 批量隔离：每个文件的表头映射独立计算；第二个文件必须使用自己的列名，不能沿用第一个文件的 header_map。
11. 首行表头：默认把第一行作为表头而不是数据行；has_header 为 false 时 header 与 header_map 为空。
12. 空白保留：未加引号字段中的前后空格、加引号字段中的空格都原样保留，不做 strip。
13. 引号内逗号：逗号在引号内是普通字符，不能触发字段切分。
14. 回车换行组合：CRLF 是一个记录分隔符而不是两个；引号内的 CRLF 仍属于字段内容；单独 CR 也按记录分隔符处理。
15. 空文件：没有记录时返回空表头、空 header_map、空 rows 与空 issues，不产生异常。
16. 测试不可修改：tests/csv/test_reader.py 是验收标准，不得改动测试来迁就实现；只修改 engine/csv/reader.py。

## 15 个测试

1. test_bom_is_stripped_from_first_header_cell：缺陷 1，首列表头 BOM 必须消失。
2. test_repeated_leading_bom_is_removed：缺陷 2，首部重复 BOM 必须去重。
3. test_newline_inside_quotes_does_not_split_row：缺陷 3，引号内换行不切行。
4. test_doubled_quote_becomes_one_quote：缺陷 4，双引号转义合并。
5. test_trailing_empty_field_is_kept_by_helper：缺陷 5，行尾空字段保留。
6. test_terminal_newline_creates_no_empty_data_row：缺陷 6，末尾换行不产生空数据行。
7. test_ragged_row_is_reported_and_not_padded：缺陷 7，列数不符要报告且不补齐。
8. test_duplicate_header_is_rejected_not_overwritten：缺陷 8，重复表头必须报错。
9. test_illegal_escape_is_reported：缺陷 9，非法转义必须报告。
10. test_batch_headers_are_independent：缺陷 10，批量文件表头不串用。
11. test_simple_two_rows_two_columns：普通两行两列解析。
12. test_comma_inside_quotes_is_not_a_separator：引号内逗号不切分。
13. test_newline_inside_quotes_stays_in_one_field：引号内换行留在同一字段。
14. test_trailing_empty_field_survives_batch_parse：批量路径保留行尾空字段。
15. test_batch_results_match_separate_single_file_runs：两文件批量结果与各自单独解析一致。

## 约束

只允许修改 engine/csv/reader.py。不要改 tests/csv/test_reader.py，不要增加外部依赖，不要引入网络访问。自检命令固定为 python -m pytest tests -q，验收目标是 15 failed 且失败原因全部是 NotImplementedError。

## 字段表

| 字段 | 取值 |
| --- | --- |
| 所属领域 | 安全 |
| 子方向 | 漏洞检测与攻防 |
| 任务类型 | Bugfix |
| 语言/框架 | Python 3, pytest |
| 环境可复现等级 | 无外部依赖 |

