# TQLEX 股东研究固定下载 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add fixed raw JSON downloading for TQLEX 股东研究, including latest-date institution holding details.

**Architecture:** Follow the existing single-file CLI orchestration pattern in `src/zxtp/cli.py`. Add constants for 股东研究 modules, a `fetch_gdyj()` function that reuses `fetch_tqlex_raw()` and `fetch_tqlex_raw_json()`, then wire the command into parser, UI, `fetch-all`, README, and AI Context sources.

**Tech Stack:** Python stdlib `argparse`, existing `TqlexClient`, `RawCacheWriter`, and `unittest` tests.

---

### Task 1: CLI Fetch Function

**Files:**
- Modify: `src/zxtp/cli.py`
- Test: `tests/test_cli.py`

- [x] Write `test_fetch_gdyj_writes_core_raw_cache_and_returns_zero`.
- [x] Run that single test and confirm it fails because `fetch-gdyj` is not implemented.
- [x] Add `GDYJ_ENTRY`, module constants, `fetch-gdyj` parser, and `fetch_gdyj()`.
- [x] Run the single test and confirm it passes.

### Task 2: Integrations

**Files:**
- Modify: `src/zxtp/cli.py`
- Modify: `src/zxtp/ai_context.py`
- Modify: `README.md`
- Test: `tests/test_cli.py`
- Test: `tests/test_ai_context.py`

- [x] Add failing tests for `fetch-all`, UI menu, invalid stock code, and AI Context source listing.
- [x] Run targeted tests and confirm they fail for missing integration.
- [x] Wire `fetch_gdyj()` into `fetch_all()`, `run_fetch_all()`, `run_ui()`, and `main()`.
- [x] Add 股东研究 sources to AI Context.
- [x] Update README command list and `fetch-all` description.
- [x] Run the targeted tests and full test suite.
