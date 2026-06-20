# Earnings Forecast Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a typed annual earnings-forecast table from confirmed `ylyctj` fields and render a six-year actual-versus-forecast table in AI Context.

**Architecture:** Keep all current `earnings_forecast_*` raw tables unchanged. During the existing `ylyctj` transaction, derive `earnings_forecast_yearly_metrics` from result set 3 historical rows and result sets 1/2 forecast rows. AI Context reads the derived table only when it exists, so old databases retain their current raw summary without failure.

**Tech Stack:** Python 3, DuckDB, `unittest`, existing `RawCacheWriter` fixtures.

---

## File Structure

- Modify: `src/zxtp/structured.py` - derived table schema, typed mapping, forecast growth calculation, transactional replacement.
- Modify: `tests/test_structured.py` - raw-to-derived-table mapping and replacement tests.
- Modify: `src/zxtp/ai_context.py` - optional derived-table query and six-year Markdown renderer.
- Modify: `tests/test_ai_context.py` - raw-to-DuckDB-to-Markdown regression test for the table and old-table fallback.
- Modify: `docs/database-schema.md` - annual metrics table, units, source-field mapping, deferred PE note.
- Modify: `docs/superpowers/plans/2026-06-19-ybpj-structured-roadmap.md` - record confirmed `ylyctj` metric mappings.

### Task 1: Establish the annual metrics table contract

**Files:**
- Modify: `tests/test_structured.py`

- [ ] **Step 1: Write the failing derived-table test**

Add `test_derives_yearly_earnings_forecast_metrics`. Write empty required `tzpjtj` and `ycpjyjbg` caches plus this minimal `ylyctj` data:

```python
{
    "ResultSets": [
        {"ColDes": [{"Name": "nyear"}], "Content": [["2026"]]},
        {"ColDes": [
            {"Name": "T036"}, {"Name": "T037"}, {"Name": "T038"},
            {"Name": "T027"}, {"Name": "T028"}, {"Name": "T029"},
            {"Name": "T024"}, {"Name": "T025"}, {"Name": "T026"},
            {"Name": "T033"}, {"Name": "T034"}, {"Name": "T035"},
            {"Name": "T021"}, {"Name": "T022"}, {"Name": "T023"},
            {"Name": "T030"}, {"Name": "T031"}, {"Name": "T032"},
        ], "Content": [[
            "1.135", "1.258", "1.353", "12.04", "13.01", "14.05",
            "9.80", "10.25", "10.32", "1242640", "1385040", "1502060",
            "2639700", "2894380", "3112040", "1448200", "1613500", "1749660",
        ]]},
        {"ColDes": [
            {"Name": "T002"}, {"Name": "T055"}, {"Name": "T059"},
            {"Name": "T064"}, {"Name": "T018"}, {"Name": "T003"},
            {"Name": "T012"}, {"Name": "T118"},
        ], "Content": [[
            "2025", "1.0811", "9.5485", "8.43", "1107276.10",
            "2414329.66", "1299963.88", "34.76",
        ]]},
    ]
}
```

After parsing, query `earnings_forecast_yearly_metrics` and assert the actual 2025 row maps exactly, the 2026 row is `forecast`, and its growth is approximately `12.22` percent:

```python
actual = connection.execute("""
    SELECT period_type, earnings_per_share, net_profit_parent_wan,
           operating_revenue_wan, operating_profit_wan
    FROM earnings_forecast_yearly_metrics WHERE fiscal_year = 2025
""").fetchone()
forecast = connection.execute("""
    SELECT period_type, earnings_per_share, net_profit_growth_pct
    FROM earnings_forecast_yearly_metrics WHERE fiscal_year = 2026
""").fetchone()
self.assertEqual(actual, ("actual", 1.0811, 1107276.10, 2414329.66, 1299963.88))
self.assertEqual(forecast[:2], ("forecast", 1.135))
self.assertAlmostEqual(forecast[2], 12.22, places=2)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_structured.ResearchRatingStructuredTests.test_derives_yearly_earnings_forecast_metrics -v`

Expected: FAIL because `earnings_forecast_yearly_metrics` does not exist.

### Task 2: Derive and replace confirmed annual metrics

**Files:**
- Modify: `src/zxtp/structured.py`
- Test: `tests/test_structured.py`

- [ ] **Step 1: Add the schema**

Define `EARNINGS_FORECAST_YEARLY_METRICS_SCHEMA` with:

```sql
stock_code VARCHAR NOT NULL,
fiscal_year INTEGER NOT NULL,
period_type VARCHAR NOT NULL,
earnings_per_share DOUBLE,
book_value_per_share DOUBLE,
return_on_equity_pct DOUBLE,
net_profit_parent_wan DOUBLE,
net_profit_growth_pct DOUBLE,
operating_revenue_wan DOUBLE,
operating_profit_wan DOUBLE,
source_path VARCHAR NOT NULL,
source_entry VARCHAR NOT NULL,
source_module VARCHAR NOT NULL,
source_fetched_at VARCHAR,
source_response_hash VARCHAR,
structured_at VARCHAR NOT NULL,
PRIMARY KEY (stock_code, fiscal_year)
```

Execute this schema before the parser transaction begins.

- [ ] **Step 2: Implement raw-to-metric derivation**

Add a `replace_earnings_forecast_yearly_metrics` helper. Delete existing rows for the stock first. Build actual rows from result-set 3 using `T002/T055/T059/T064/T018/T118/T003/T012`. Read the first valid result-set-1 `nyear` and result-set-2 row; generate three `forecast` rows using the confirmed TQLEX triplets from the design specification.

Use `parse_integer` for years and `parse_float` for all numeric metrics. Sort all generated rows by `fiscal_year`; calculate each forecast `net_profit_growth_pct` from the immediately preceding generated actual or forecast row only when the preceding net profit is nonzero. Insert typed values and the normal `ylyctj` source metadata with one `executemany` call.

- [ ] **Step 3: Invoke the helper in the existing transaction**

After `replace_earnings_forecast_result_sets`, call the new helper with the same `rows_by_result_set`, paths, metadata and timestamp. A missing `ylyctj` cache must leave both its raw and derived tables unchanged; an empty existing `ylyctj` cache must clear only this stock's raw and derived earnings records.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_structured.ResearchRatingStructuredTests.test_derives_yearly_earnings_forecast_metrics -v`

Expected: PASS.

- [ ] **Step 5: Add replacement coverage**

Parse a second `ylyctj` fixture for the same stock with a changed 2026 EPS and no historical or consensus rows. Assert that the annual table no longer contains the former rows. This verifies stock-level replacement instead of append behavior.

- [ ] **Step 6: Run structured-data tests**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_structured -v`

Expected: PASS.

### Task 3: Render the six-year annual table in AI Context

**Files:**
- Modify: `tests/test_ai_context.py`
- Modify: `src/zxtp/ai_context.py`

- [ ] **Step 1: Write the failing Markdown test**

Add `test_renders_yearly_earnings_forecast_metrics`. Use the Task 1 raw fixture, generate full context, and assert it contains:

```python
self.assertIn("#### 年度指标", research_section)
self.assertIn("| 指标 | 2025 实际 | 2026 预测 | 2027 预测 | 2028 预测 |", research_section)
self.assertIn("| 每股收益（元） | 1.081 | 1.135 | 1.258 | 1.353 |", research_section)
self.assertIn("| 归母净利润（亿元） | 110.73 | 124.26 | 138.50 | 150.21 |", research_section)
self.assertIn("| 归母净利润增长率（%） | 34.76 | 12.22 | 11.46 | 8.45 |", research_section)
self.assertNotIn("市盈率", research_section)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_ai_context.AiContextGenerationTests.test_renders_yearly_earnings_forecast_metrics -v`

Expected: FAIL because the annual table is not rendered.

- [ ] **Step 3: Query and render the derived metrics**

In `render_research_ratings`, add a separate optional query for `earnings_forecast_yearly_metrics`, ordered by `fiscal_year`. Keep the current raw source summary. When metrics exist, append `#### 年度指标` and a Markdown table with ordered year columns. Format EPS and BPS to three decimals, percentage values to two decimals, and `*_wan` values divided by `10000` to two-decimal 亿元 strings. Render missing values as `-`.

Add small pure helpers: `format_metric(value, decimal_places)` and `format_wan_as_yi(value)`. Do not calculate or display PE.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_ai_context.AiContextGenerationTests.test_renders_yearly_earnings_forecast_metrics -v`

Expected: PASS.

- [ ] **Step 5: Preserve older databases**

Extend the existing old-schema AI Context test so it also asserts no annual-metrics table is emitted when `earnings_forecast_yearly_metrics` is absent, while existing rating output remains present.

- [ ] **Step 6: Run AI Context tests**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_ai_context -v`

Expected: PASS.

### Task 4: Document and validate the confirmed field semantics

**Files:**
- Modify: `docs/database-schema.md`
- Modify: `docs/superpowers/plans/2026-06-19-ybpj-structured-roadmap.md`

- [ ] **Step 1: Update the data dictionary**

Document `earnings_forecast_yearly_metrics`, all eight confirmed business metrics, the 万元 source unit and 亿元 AI display conversion. State that PE remains excluded because it cannot be reproduced from current raw data without guessing a price reference.

- [ ] **Step 2: Update the roadmap field record**

Replace the Stage 3 blanket “semantics unknown” note for the confirmed fields with the exact result-set-2 and result-set-3 mappings. Keep an unchecked follow-up for PE and any unconfirmed `ylyctj` fields.

- [ ] **Step 3: Validate real cached raw in a temporary database**

Copy only `002736` `tzpjtj`, `ycpjyjbg`, and `ylyctj` caches to a temporary data root. Parse there and verify `2023` through `2028` annual rows, 2026 EPS `1.135`, 2026 parent net profit `1242640`, and an AI Context table. Do not write to `D:/zxtp_data/warehouse/research.duckdb`.

- [ ] **Step 4: Run complete verification**

Run: `./.venv/Scripts/python.exe -m unittest discover -s tests -v`

Expected: all tests PASS.

Run: `git diff --check`

Expected: exit code 0 with no whitespace errors.
