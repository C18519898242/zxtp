# Financial Key Metrics Report Date Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse real `cwfx/zyzb` responses that use `T002` as their report-date column so that `financial_key_metrics` is populated and usable by AI Context.

**Architecture:** Keep the existing `financial_key_metrics` schema and AI Context query unchanged. At the financial-key-metric parser boundary, normalize the report date from `rq` when present and otherwise from the real TQLEX field `T002`. A regression test uses the real `T002` shape and proves records are written.

**Tech Stack:** Python 3.11, DuckDB, `unittest`, existing `RawCacheWriter` fixtures.

---

## File structure

- Modify `tests/test_structured.py`: add a focused regression test for a `zyzb` response that names its report-date column `T002`.
- Modify `src/zxtp/structured.py`: use `T002` as the fallback source for the key-metric report date.

### Task 1: Reproduce the real `T002` response with a failing test

**Files:**
- Modify: `tests/test_structured.py` in `FinancialAnalysisStructuredTests`

- [x] **Step 1: Add the failing regression test**

```python
    def test_parses_key_metrics_when_zyzb_uses_t002_for_report_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            self.write_financial_raw(
                data_root,
                "zyzb",
                ["T002", "mgsy", "jyr"],
                [["2026-03-31", "0.2856", "4483918670.00"]],
            )

            database_path = structured.parse_financial_analysis("002736", data_root)

            with duckdb.connect(str(database_path), read_only=True) as connection:
                rows = connection.execute(
                    """
                    SELECT report_date, report_type, metric_name, metric_value
                    FROM financial_key_metrics
                    ORDER BY metric_name
                    """
                ).fetchall()

            self.assertEqual(
                rows,
                [
                    ("2026-03-31", "q1", "basic_earnings_per_share", 0.2856),
                    ("2026-03-31", "q1", "net_profit", 4483918670.0),
                ],
            )
```

- [x] **Step 2: Run the focused test and verify the expected failure**

Run:

```powershell
uv run python tests/test_structured.py FinancialAnalysisStructuredTests.test_parses_key_metrics_when_zyzb_uses_t002_for_report_date
```

Expected: the test fails because `financial_key_metrics` has no rows; the current parser only reads `rq`.

### Task 2: Add the minimal report-date fallback

**Files:**
- Modify: `src/zxtp/structured.py:495-497`
- Test: `tests/test_structured.py`

- [x] **Step 1: Change only the report-date lookup in `replace_financial_key_metrics()`**

Replace:

```python
        report_date = normalize_text(row.get("rq"))
```

With:

```python
        report_date = normalize_text(row.get("rq")) or normalize_text(row.get("T002"))
```

Keep the existing `if report_date is None: continue` guard and all metric mappings unchanged.

- [x] **Step 2: Re-run the focused regression test**

Run:

```powershell
uv run python tests/test_structured.py FinancialAnalysisStructuredTests.test_parses_key_metrics_when_zyzb_uses_t002_for_report_date
```

Expected: PASS. The two rows have `2026-03-31` and `q1`, proving that real `T002` data reaches the table.

- [x] **Step 3: Run the full test suite**

Run:

```powershell
uv run python -m unittest discover -s tests -q
```

Expected: exit code 0 with all tests passing, including existing `rq`-based fixtures.

- [x] **Step 4: Commit the implementation**

```powershell
git add src/zxtp/structured.py tests/test_structured.py
git commit -m "fix: parse T002 financial metric report dates"
```
