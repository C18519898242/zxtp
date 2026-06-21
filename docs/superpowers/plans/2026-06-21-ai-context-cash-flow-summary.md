# AI Context Cash Flow Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render verified core cash flows, exchange effects, and beginning/ending cash balances in the AI Context financial-analysis section.

**Architecture:** Preserve the existing DuckDB schema and raw parsing. `render_financial_analysis()` will query seven verified `financial_cash_flows` fields, then a dedicated renderer will format the rows with the same report-period columns used by the existing key-metric and balance-sheet tables.

**Tech Stack:** Python 3.11, DuckDB, `unittest`, existing raw-cache fixtures.

---

## File structure

- Modify `tests/test_ai_context.py`: seed `xjllb` data and assert cash-flow Markdown values, negative amounts, and missing values.
- Modify `src/zxtp/ai_context.py`: query verified cash-flow facts and replace the cash-flow placeholder with a seven-row comparison table.

### Task 1: Define the cash-flow output with failing tests

**Files:**
- Modify: `tests/test_ai_context.py:79-87`, `tests/test_ai_context.py:539-640`

- [x] **Step 1: Add a verified `xjllb` fixture**

Replace the empty `xjllb` snapshot in `write_financial_context_raw()` with:

```python
"ColDes": [
    {"Name": name}
    for name in ("rq", "T017", "T029", "T038", "T039", "T041", "T042", "T043")
],
"Content": [
    ["2022-12-31", "1000000000", "-200000000", "100000000", "0", "900000000", "500000000", "1400000000"],
    ["2023-12-31", "1200000000", "-300000000", "200000000", "10000000", "1110000000", "2000000000", "3110000000"],
    ["2024-12-31", "1500000000", "-400000000", "-200000000", "20000000", "920000000", "3110000000", "4030000000"],
    ["2025-12-31", "-500000000", "-200000000", "300000000", "-10000000", "-410000000", "4030000000", "3620000000"],
    ["2026-03-31", "400000000", "-100000000", "-200000000", "5000000", "105000000", "3620000000", "3725000000"],
],
```

Keep `lyb` empty.

- [x] **Step 2: Add primary failing Markdown assertions**

In `test_renders_financial_context_for_recent_annuals_and_latest_period`, add:

```python
self.assertIn("### 现金流与效率", financial_section)
self.assertIn("| 经营活动产生的现金流量净额（亿元） | 12.00 | 15.00 | -5.00 | 4.00 |", financial_section)
self.assertIn("| 投资活动产生的现金流量净额（亿元） | -3.00 | -4.00 | -2.00 | -1.00 |", financial_section)
self.assertIn("| 筹资活动产生的现金流量净额（亿元） | 2.00 | -2.00 | 3.00 | -2.00 |", financial_section)
self.assertIn("| 汇率变动对现金及现金等价物的影响（亿元） | 0.10 | 0.20 | -0.10 | 0.05 |", financial_section)
self.assertIn("| 现金及现金等价物净增加额（亿元） | 11.10 | 9.20 | -4.10 | 1.05 |", financial_section)
self.assertIn("| 期初现金及现金等价物余额（亿元） | 20.00 | 31.10 | 40.30 | 36.20 |", financial_section)
self.assertIn("| 期末现金及现金等价物余额（亿元） | 31.10 | 40.30 | 36.20 | 37.25 |", financial_section)
self.assertNotIn("现金流量表明细已结构化", financial_section)
```

- [x] **Step 3: Add a failing missing-value test**

Create a test that overwrites the `xjllb` raw snapshot with the same columns and a `None` value for `T029` in `2026-03-31`, then asserts:

```python
self.assertIn(
    "| 投资活动产生的现金流量净额（亿元） | -3.00 | -4.00 | -2.00 | — |",
    financial_section,
)
```

- [x] **Step 4: Run the new tests and verify the expected failure**

Run:

```powershell
uv run python -m unittest -v tests.test_ai_context.AiContextGenerationTests.test_renders_financial_context_for_recent_annuals_and_latest_period tests.test_ai_context.AiContextGenerationTests.test_cash_flow_table_uses_dash_for_missing_values
```

Expected: FAIL because the financial section still contains only the cash-flow placeholder.

### Task 2: Query and render verified cash-flow facts

**Files:**
- Modify: `src/zxtp/ai_context.py:254-297`
- Test: `tests/test_ai_context.py`

- [x] **Step 1: Query the seven raw fields in `render_financial_analysis()`**

Inside the existing DuckDB connection, add:

```python
            cash_flow_rows = connection.execute(
                """
                SELECT report_date, raw_field_name, amount
                FROM financial_cash_flows
                WHERE stock_code = ?
                  AND raw_field_name IN (
                      'T017', 'T029', 'T038', 'T039', 'T041', 'T042', 'T043'
                  )
                """,
                [stock_code],
            ).fetchall()
```

- [x] **Step 2: Add the Markdown renderer**

Define `CASH_FLOW_CONTEXT_METRICS` in this order:

```python
("T017", "经营活动产生的现金流量净额（亿元）")
("T029", "投资活动产生的现金流量净额（亿元）")
("T038", "筹资活动产生的现金流量净额（亿元）")
("T039", "汇率变动对现金及现金等价物的影响（亿元）")
("T041", "现金及现金等价物净增加额（亿元）")
("T042", "期初现金及现金等价物余额（亿元）")
("T043", "期末现金及现金等价物余额（亿元）")
```

Add `render_cash_flow_table(cash_flow_rows, periods, labels) -> list[str]`. Build a value lookup by `(report_date, raw_field_name)` and return a `### 现金流与效率` Markdown table. For each configured field, format `None` as `—`; otherwise divide the value by `100_000_000` and format to two decimals.

- [x] **Step 3: Replace the placeholder subsection**

Replace:

```python
        "### 现金流与效率",
        "- 现金流量表明细已结构化为 raw 字段级事实；已确认的每股经营现金流见上表。",
```

With:

```python
        *render_cash_flow_table(cash_flow_rows, periods, labels),
```

- [x] **Step 4: Re-run the focused tests**

Run the command from Task 1 Step 4.

Expected: PASS. The table renders all seven rows, preserves negative values, and displays `—` for missing raw data.

- [x] **Step 5: Run the full test suite**

Run:

```powershell
uv run python -m unittest discover -s tests -q
```

Expected: exit code 0 with all tests passing.

- [x] **Step 6: Commit the implementation**

```powershell
git add src/zxtp/ai_context.py tests/test_ai_context.py docs/superpowers/plans/2026-06-21-ai-context-cash-flow-summary.md
git commit -m "feat: render AI context cash flow summary"
```
