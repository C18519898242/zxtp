# Structured Write Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show English progress logs immediately before every company-overview, research-rating, and financial-analysis DuckDB write.

**Architecture:** Retain the existing CLI control flow and complete logs. Insert one `print(..., file=output_stream)` immediately before each existing parser invocation in the command, bulk-download, and interactive-menu paths. Tests verify the start log precedes its existing completion log.

**Tech Stack:** Python 3.11, `unittest`, existing `io.StringIO` CLI tests.

---

## File structure

- Modify `tests/test_cli.py`: assert progress messages and output ordering for direct commands, `fetch-all`, and the corresponding interactive menu paths.
- Modify `src/zxtp/cli.py`: print the three English progress messages before calling the three structured-data parsers.

### Task 1: Add failing progress-log assertions

**Files:**
- Modify: `tests/test_cli.py:33-59`, `tests/test_cli.py:180-207`, `tests/test_cli.py:790-892`, `tests/test_cli.py:966-997`, `tests/test_cli.py:1274-1302`

- [x] **Step 1: Add an output-order helper near the test imports**

```python
def assert_output_precedes(
    test_case: unittest.TestCase, output: str, before: str, after: str
) -> None:
    test_case.assertIn(before, output)
    test_case.assertIn(after, output)
    test_case.assertLess(output.index(before), output.index(after))
```

- [x] **Step 2: Assert direct command and `fetch-all` output before implementation**

Add these assertions to the existing tests after `output = stdout.getvalue()`:

```python
assert_output_precedes(
    self,
    output,
    "saving company overview structured data...",
    "saved company overview structured data:",
)
assert_output_precedes(
    self,
    output,
    "saving research rating structured data...",
    "saved research rating structured data:",
)
assert_output_precedes(
    self,
    output,
    "saving financial analysis structured data...",
    "saved financial analysis structured data:",
)
```

Use the company assertion in `test_fetch_gsgk_parses_company_overview_into_duckdb`, the research assertion in `test_fetch_ybpj_parses_research_ratings_into_duckdb`, and all three assertions in `test_fetch_all_writes_every_raw_cache_and_returns_zero`.

- [x] **Step 3: Assert the interactive paths before implementation**

Add the company assertion to `CliUiTests.test_ui_fetches_gsgk_from_menu_choices`, the research assertion to `CliUiYbpjTests.test_ui_fetches_ybpj_from_menu_choices`, and the financial assertion to `CliUiCwfxTests.test_ui_fetches_cwfx_from_menu_choices`.

- [x] **Step 4: Run the affected tests and verify the expected failure**

Run:

```powershell
uv run python tests/test_cli.py CliFetchGsgkTests.test_fetch_gsgk_parses_company_overview_into_duckdb CliFetchYbpjTests.test_fetch_ybpj_parses_research_ratings_into_duckdb CliFetchAllTests.test_fetch_all_writes_every_raw_cache_and_returns_zero CliUiYbpjTests.test_ui_fetches_ybpj_from_menu_choices CliUiCwfxTests.test_ui_fetches_cwfx_from_menu_choices CliUiTests.test_ui_fetches_gsgk_from_menu_choices
```

Expected: FAIL because none of the `saving ... structured data...` messages exists yet.

### Task 2: Emit start logs before each parser call

**Files:**
- Modify: `src/zxtp/cli.py:746`, `src/zxtp/cli.py:755`, `src/zxtp/cli.py:764`, `src/zxtp/cli.py:854`, `src/zxtp/cli.py:866`, `src/zxtp/cli.py:878`, `src/zxtp/cli.py:940`, `src/zxtp/cli.py:949`, `src/zxtp/cli.py:958`
- Test: `tests/test_cli.py`

- [x] **Step 1: Insert each progress log immediately before its parser**

Use these exact pairs at every matching call site:

```python
print("saving company overview structured data...", file=output_stream)
database_path = parse_company_overview(stock_code, data_root)

print("saving research rating structured data...", file=output_stream)
database_path = parse_research_ratings(stock_code, data_root)

print("saving financial analysis structured data...", file=output_stream)
database_path = parse_financial_analysis(stock_code, data_root)
```

For the argument-parser command paths, use `args.stock_code`; for `run_fetch_all`, use `valid_stock_code`; for the interactive paths, use `stock_code`. Do not alter the existing `saved ... structured data` prints.

- [x] **Step 2: Re-run the affected tests**

Run the command from Task 1 Step 4.

Expected: PASS. Each start message appears before its paired completion message across direct, bulk, and UI flows.

- [x] **Step 3: Run the full test suite**

Run:

```powershell
uv run python -m unittest discover -s tests -q
```

Expected: exit code 0 with all tests passing.

- [x] **Step 4: Commit the implementation**

```powershell
git add src/zxtp/cli.py tests/test_cli.py docs/superpowers/plans/2026-06-21-structured-write-progress.md
git commit -m "feat: log structured write progress"
```
