# AI Context Balance Sheet Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render verified assets, liabilities, equity, and debt ratio in the AI Context financial-analysis section.

**Architecture:** Keep raw parsing and the DuckDB schema unchanged. `render_financial_analysis()` will read the three verified raw fields from `financial_balance_sheets`, then a focused renderer will format them against the existing key-metric report-period columns. The debt ratio is derived only when both total assets and total liabilities exist and assets are non-zero.

**Tech Stack:** Python 3.11, DuckDB, `unittest`, existing raw-cache fixtures.

---

## File structure

- Modify `tests/test_ai_context.py`: seed verified `zcfzb` fields and add Markdown assertions for values, ratio, missing values, and zero assets.
- Modify `src/zxtp/ai_context.py`: query balance-sheet raw facts and render the four-row Markdown comparison table.

### Task 1: Specify balance-sheet rendering with failing tests

**Files:**
- Modify: `tests/test_ai_context.py:21-76`, `tests/test_ai_context.py:539-558`

- [x] **Step 1: Add verified balance-sheet raw facts to the existing fixture**

Replace the empty `zcfzb` snapshot in `write_financial_context_raw()` with a result set using these columns and rows:

```python
"ColDes": [{"Name": name} for name in ("rq", "T039", "T062", "T071")],
"Content": [
    ["2022-12-31", "25000000000", "15000000000", "10000000000"],
    ["2023-12-31", "30000000000", "18000000000", "12000000000"],
    ["2024-12-31", "40000000000", "26000000000", "14000000000"],
    ["2025-12-31", "50000000000", "35000000000", "15000000000"],
    ["2026-03-31", "55000000000", "36000000000", "19000000000"],
],
```

Keep `lyb` and `xjllb` empty.

- [x] **Step 2: Add the primary failing Markdown assertions**

In `test_renders_financial_context_for_recent_annuals_and_latest_period`, add:

```python
self.assertIn("### 资产与负债", financial_section)
self.assertIn("| 资产总计（亿元） | 300.00 | 400.00 | 500.00 | 550.00 |", financial_section)
self.assertIn("| 负债合计（亿元） | 180.00 | 260.00 | 350.00 | 360.00 |", financial_section)
self.assertIn("| 所有者权益合计（亿元） | 120.00 | 140.00 | 150.00 | 190.00 |", financial_section)
self.assertIn("| 资产负债率（%） | 60.00 | 65.00 | 70.00 | 65.45 |", financial_section)
self.assertNotIn("字段业务口径待确认", financial_section)
```

- [x] **Step 3: Add a failing edge-case unit test for missing values and zero assets**

Import `render_balance_sheet_table` and add:

```python
    def test_balance_sheet_table_uses_dash_for_missing_or_zero_asset_ratio(self) -> None:
        lines = render_balance_sheet_table(
            [
                ("2025-12-31", "T039", 0.0),
                ("2025-12-31", "T062", 100.0),
                ("2025-12-31", "T071", 50.0),
                ("2026-03-31", "T039", 200_000_000.0),
                ("2026-03-31", "T062", None),
                ("2026-03-31", "T071", 80_000_000.0),
            ],
            ["2025-12-31", "2026-03-31"],
            ["2025 年报", "2026-03-31"],
        )

        self.assertIn("| 资产总计（亿元） | 0.00 | 2.00 |", lines)
        self.assertIn("| 资产负债率（%） | — | — |", lines)
```

- [x] **Step 4: Run the new tests and verify the expected failure**

Run:

```powershell
uv run python -m unittest -v tests.test_ai_context.AiContextGenerationTests.test_renders_financial_context_for_recent_annuals_and_latest_period tests.test_ai_context.AiContextGenerationTests.test_balance_sheet_table_uses_dash_for_missing_or_zero_asset_ratio
```

Expected: FAIL because the balance table renderer does not exist and the financial section still contains the placeholder explanation.

### Task 2: Read and render the verified balance-sheet facts

**Files:**
- Modify: `src/zxtp/ai_context.py:248-284`
- Test: `tests/test_ai_context.py`

- [x] **Step 1: Query the three balance-sheet fields alongside key metrics**

Inside the existing DuckDB connection in `render_financial_analysis()`, add:

```python
            balance_rows = connection.execute(
                """
                SELECT report_date, raw_field_name, amount
                FROM financial_balance_sheets
                WHERE stock_code = ?
                  AND raw_field_name IN ('T039', 'T062', 'T071')
                """,
                [stock_code],
            ).fetchall()
```

- [x] **Step 2: Add the pure Markdown renderer**

Add `render_balance_sheet_table(balance_rows, periods, labels) -> list[str]` with this behavior:

```python
values = {(date, field): amount for date, field, amount in balance_rows}

def format_amount(value: float | None) -> str:
    return "—" if value is None else f"{float(value) / 100_000_000:.2f}"

def format_debt_ratio(asset: float | None, liability: float | None) -> str:
    if asset is None or liability is None or float(asset) == 0:
        return "—"
    return f"{float(liability) / float(asset) * 100:.2f}"
```

Return a Markdown table headed by `### 资产与负债`, with rows for `T039`, `T062`, `T071`, and the derived ratio, using these labels in order:

```python
"资产总计（亿元）"
"负债合计（亿元）"
"所有者权益合计（亿元）"
"资产负债率（%）"
```

- [x] **Step 3: Replace the placeholder subsection**

Replace these lines in `render_financial_analysis()`:

```python
        "### 资产与负债",
        "- 资产负债表明细已结构化为 raw 字段级事实；字段业务口径待确认，暂不展示猜测的金额。",
```

With:

```python
        *render_balance_sheet_table(balance_rows, periods, labels),
```

- [x] **Step 4: Re-run the focused tests**

Run the command from Task 1 Step 4.

Expected: PASS. The main test confirms the four recent-period rows, while the edge-case test confirms safe `—` handling.

- [x] **Step 5: Run the full test suite**

Run:

```powershell
uv run python -m unittest discover -s tests -q
```

Expected: exit code 0 with all tests passing.

- [x] **Step 6: Commit the implementation**

```powershell
git add src/zxtp/ai_context.py tests/test_ai_context.py docs/superpowers/plans/2026-06-21-ai-context-balance-sheet-summary.md
git commit -m "feat: render AI context balance sheet summary"
```
