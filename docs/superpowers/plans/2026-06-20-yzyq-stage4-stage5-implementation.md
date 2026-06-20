# yzyq Stage 4 and Stage 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store all four `ybpj/yzyq` result sets in DuckDB and render a fault-tolerant raw-first performance-and-price summary in AI Context.

**Architecture:** Extend the existing `parse_research_ratings` transaction with an optional `yzyq` cache. Each result set has an independent table and is replaced per stock through the existing generic raw-row writer. Extend the existing `render_research_ratings` function with nested, optional Stage 4 queries so an older database, a missing table, or an unavailable DuckDB file cannot prevent the rest of the Markdown from being generated.

**Tech Stack:** Python 3, DuckDB, `unittest`, existing `RawCacheWriter` test fixture.

---

## File Structure

- Modify: `src/zxtp/structured.py` - `yzyq` field maps, schemas, optional raw loading, transactional replacement.
- Modify: `tests/test_structured.py` - raw-to-DuckDB regression test for all four result sets and stock-level replacement.
- Modify: `src/zxtp/ai_context.py` - read and render raw-first Stage 4 summary without breaking existing rating sections.
- Modify: `tests/test_ai_context.py` - raw-to-DuckDB-to-Markdown and unavailable-database regression tests.
- Modify: `docs/database-schema.md` - document the four tables and the explicit no-semantic-guessing policy.
- Modify: `docs/superpowers/plans/2026-06-19-ybpj-structured-roadmap.md` - mark Stage 4 and Stage 5 implementation tasks complete, retaining deferred field semantics.

### Task 1: Define the Stage 4 contract with a failing structured-data test

**Files:**
- Modify: `tests/test_structured.py`

- [ ] **Step 1: Write the failing test**

Add `test_parses_yzyq_result_sets_into_separate_raw_tables`. Write empty required `tzpjtj` and `ycpjyjbg` fixtures, then write this `yzyq` payload through `RawCacheWriter`:

```python
{
    "ResultSets": [
        {"ColDes": [{"Name": "defdate"}, {"Name": "T003"}],
         "Content": [["20261231", "20260527"]]},
        {"ColDes": [{"Name": "T026"}, {"Name": "T030"}, {"Name": "T005"}],
         "Content": [["0", "20260522", "1.180"]]},
        {"ColDes": [{"Name": "EndDate"}, {"Name": "AdjustingFactor"}, {"Name": "AdjustingConst"}],
         "Content": [["20260622", "1", "3.54"]]},
        {"ColDes": [{"Name": "TradingDay"}, {"Name": "ClosePrice"}],
         "Content": [["20250620", "11.040"], ["20250619", "10.900"]]},
    ]
}
```

After `parse_research_ratings("002736", data_root)`, assert the four tables exist and query the exact values:

```python
self.assertEqual(connection.execute(
    "SELECT raw_defdate, raw_t003 FROM performance_expectations"
).fetchone(), ("20261231", "20260527"))
self.assertEqual(connection.execute(
    "SELECT raw_t026, raw_t030, raw_t005 FROM performance_expectation_estimates"
).fetchone(), ("0", "20260522", "1.180"))
self.assertEqual(connection.execute(
    "SELECT end_date, raw_adjusting_factor, raw_adjusting_const FROM adjustment_factors"
).fetchone(), ("20260622", "1", "3.54"))
self.assertEqual(connection.execute(
    "SELECT trading_day, raw_close_price FROM daily_close_prices ORDER BY trading_day DESC"
).fetchall(), [("20250620", "11.040"), ("20250619", "10.900")])
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_structured.ResearchRatingStructuredTests.test_parses_yzyq_result_sets_into_separate_raw_tables -v`

Expected: FAIL because the four Stage 4 tables are not created.

### Task 2: Add transactional Stage 4 raw storage

**Files:**
- Modify: `src/zxtp/structured.py`
- Test: `tests/test_structured.py`

- [ ] **Step 1: Define explicit raw-first field maps and schemas**

Add the module constant and these maps:

```python
PERFORMANCE_EXPECTATION_MODULE = "yzyq"
PERFORMANCE_EXPECTATION_FIELDS = {
    "raw_defdate": "defdate", "raw_mxdef": "mxdef", "raw_t003": "T003",
    "raw_t005": "T005", "raw_t024": "T024", "raw_t025": "T025",
    "raw_t031": "T031", "raw_t032": "T032", "raw_t033": "T033",
}
PERFORMANCE_EXPECTATION_ESTIMATE_FIELDS = {
    "raw_t026": "T026", "raw_t030": "T030", "raw_t005": "T005",
    "raw_t006": "T006", "raw_t007": "T007",
}
ADJUSTMENT_FACTOR_FIELDS = {
    "end_date": "EndDate", "raw_adjusting_factor": "AdjustingFactor",
    "raw_adjusting_const": "AdjustingConst",
}
DAILY_CLOSE_PRICE_FIELDS = {
    "trading_day": "TradingDay", "raw_close_price": "ClosePrice",
}
```

Create `CREATE TABLE IF NOT EXISTS` schemas for `performance_expectations`, `performance_expectation_estimates`, `adjustment_factors`, and `daily_close_prices`. All mapped values are `VARCHAR`; every schema includes the six shared source columns. `daily_close_prices` adds `PRIMARY KEY (stock_code, trading_day)`.

- [ ] **Step 2: Load the optional `yzyq` raw cache and create schemas**

In `parse_research_ratings`, build `yzyq_paths` with entry `tdxf10_gg_ybpj`, module `yzyq`; read it using `all_result_set_rows` only when the JSON cache exists; read metadata only when its metadata cache exists. Execute all four schemas before `BEGIN`.

- [ ] **Step 3: Replace only the Stage 4 tables for the current stock**

Add `replace_performance_expectation_result_sets`, routing result-set indexes 0 through 3 to the four tables. Generalize `replace_earnings_forecast_table` to accept `source_module`, rename it `replace_raw_result_set_table`, and pass `ylyctj` from its existing callers and `yzyq` from the new callers. Invoke the Stage 4 replacement only when `yzyq_rows_by_result_set is not None`.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_structured.ResearchRatingStructuredTests.test_parses_yzyq_result_sets_into_separate_raw_tables -v`

Expected: PASS.

- [ ] **Step 5: Add replacement and empty-result assertions**

In the same test class, parse a second `yzyq` payload for `002736` with one new `TradingDay` and empty result sets 1-3. Assert the price table has only the new row and the other three tables have zero rows. This proves stock-level replacement and result-set isolation.

- [ ] **Step 6: Run the focused structured test module**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_structured -v`

Expected: PASS.

### Task 3: Render a raw-first Stage 4 AI Context summary

**Files:**
- Modify: `tests/test_ai_context.py`
- Modify: `src/zxtp/ai_context.py`

- [ ] **Step 1: Write the failing end-to-end AI Context test**

Add `test_includes_performance_expectation_and_price_raw_metadata`. Create the required rating raw caches plus the Task 1 `yzyq` fixture, call `parse_research_ratings`, generate the full context, then assert:

```python
self.assertIn("### 业绩预期与价格（原始结构化）", content)
self.assertIn("预期原始日期（defdate）：20261231", content)
self.assertIn("最近交易日：20250620", content)
self.assertIn("原始收盘价：11.040", content)
self.assertIn("字段口径尚待确认", content)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_ai_context.AiContextGenerationTests.test_includes_performance_expectation_and_price_raw_metadata -v`

Expected: FAIL because the Stage 4 section is absent.

- [ ] **Step 3: Add optional Stage 4 queries and rendering**

Within the nested optional-table `try` in `render_research_ratings`, query the most recent expectation by `raw_defdate DESC`, the latest price by `trading_day DESC`, and counts for all four Stage 4 tables. If a DuckDB error occurs, set all Stage 4 values to `None`, preserving the existing Stage 1/3 output.

When data exists, append this Markdown section:

```python
performance_lines = ["### 业绩预期与价格（原始结构化）"]
performance_lines.append(f"- 预期原始日期（defdate）：{raw_defdate}")
performance_lines.append(f"- 最近交易日：{trading_day}")
performance_lines.append(f"- 原始收盘价：{raw_close_price}")
performance_lines.append(f"- 当前预期记录：{expectation_count}")
performance_lines.append(f"- 原始估算记录：{estimate_count}")
performance_lines.append(f"- 复权原始记录：{factor_count}")
performance_lines.append(f"- 收盘价记录：{price_count}")
performance_lines.append("- 字段口径尚待确认，数值按 TQLEX 原始字段保存。")
```

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_ai_context.AiContextGenerationTests.test_includes_performance_expectation_and_price_raw_metadata -v`

Expected: PASS.

- [ ] **Step 5: Add availability regression coverage**

Add a test that creates a DuckDB with only the Stage 1 tables, calls `generate_full_context`, and asserts that the current Stage 1 content remains while the Stage 4 section is absent. Patch `zxtp.ai_context.duckdb.connect` to raise `duckdb.IOException` and assert the research section contains the existing DBeaver-readable error message instead of aborting generation.

- [ ] **Step 6: Run the focused AI Context test module**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_ai_context -v`

Expected: PASS.

### Task 4: Document and verify the completed stages

**Files:**
- Modify: `docs/database-schema.md`
- Modify: `docs/superpowers/plans/2026-06-19-ybpj-structured-roadmap.md`

- [ ] **Step 1: Update the data dictionary**

Add the four tables to the overview and document each mapped column. Mark `trading_day` as trading date and `raw_close_price` as the unconverted raw close-price value. Describe every other Stage 4 field as raw, with no asserted business meaning or unit.

- [ ] **Step 2: Update the roadmap**

Mark Stage 4 and Stage 5 implementation and test tasks complete. Retain a separate unchecked field-dictionary follow-up for semantic and unit confirmation, so completion does not claim that raw fields are understood.

- [ ] **Step 3: Run the full regression suite and whitespace check**

Run: `./.venv/Scripts/python.exe -m unittest discover -s tests -v`

Expected: all tests PASS.

Run: `git diff --check`

Expected: exit code 0 with no whitespace errors.

- [ ] **Step 4: Inspect the final worktree deliberately**

Run: `git status --short`

Expected: only Stage 3/4/5 source, test, and documentation changes are present; leave the pre-existing untracked `tmp/` untouched.
