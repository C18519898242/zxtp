# 财务分析（cwfx）结构化数据与 AI Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 cwfx 的利润表、资产负债表、现金流量表和主要指标写入 DuckDB，并在 AI Context 第 3 章输出近三年年报和最新报告期的事实摘要。

**Architecture:** `structured.py` 把四份 raw snapshot 写入独立的 `financial.duckdb`：三张报表按“报告期 × 原始字段”存为长表，`zyzb` 按“报告期 × 已确认指标”存为长表。AI Context 只读取语义已确认的 `zyzb` 指标；三张报表的 TQLEX 字段保持 raw 标识，绝不猜测会计科目。

**Tech Stack:** Python 3.11、DuckDB、unittest、现有 `RawCacheWriter` 原始缓存。

---

## File structure

- Modify: `src/zxtp/structured.py` — cwfx 常量、DDL、raw 解析和替换逻辑。
- Modify: `src/zxtp/cli.py` — cwfx 下载入口自动解析。
- Modify: `src/zxtp/ai_context.py` — 金融数据库读取和财务章节渲染。
- Modify: `src/zxtp/templates/ai_context/full_context.md.tpl` — 动态财务章节占位。
- Modify: `tests/test_structured.py`、`tests/test_cli.py`、`tests/test_ai_context.py` — 解析、入口和渲染测试。
- Modify: `docs/database-schema.md` — 财务表的数据字典。

### Task 1: 为 cwfx 解析器写出失败测试

**Files:**
- Modify: `tests/test_structured.py`

- [ ] **Step 1: 增加 FinancialAnalysisStructuredTests**

用 `RawCacheWriter.write()` 写入 `zyzb`、`zcfzb`、`lyb`、`xjllb` 四个 `tdxf10_gg_cwfx` snapshot；每个结果集 0 含 `rq` 和两个报告期。zyzb 至少用：

```python
{
    "rq": "2025-12-31", "mgsy": "1.000", "kfjlr": "900000000",
    "mgxjll": "0.500", "lrze": "1200000000", "jyr": "1000000000",
    "jzzsyl": "10.5", "xsmll": "30.0", "yysrtb": "5.0",
    "jlrtbzzl": "8.0",
}
```

调用 `structured.parse_financial_analysis("002736", data_root)` 并断言文件路径为 `warehouse/financial.duckdb`、四张表存在。还要断言：

```python
key_metric == ("2025-12-31", "return_on_equity_pct", 10.5, "%", "jzzsyl")
income_item == ("2025-12-31", "T008", 1200000000.0)
periods == [("2025-12-31", 2025, "annual"), ("2026-03-31", 2026, "q1")]
```

- [ ] **Step 2: 运行失败测试**

Run: `uv run python -m unittest tests.test_structured.FinancialAnalysisStructuredTests -v`

Expected: FAIL，`parse_financial_analysis` 尚不存在。

- [ ] **Step 3: 增加替换与容错测试**

添加以下三个测试：

测试方法名依次为 `test_replaces_financial_rows_for_the_same_stock`、`test_creates_empty_tables_when_cwfx_raw_is_missing` 和 `test_skips_invalid_snapshot_and_preserves_other_modules`。

第一项重写同一个 `zyzb` snapshot（`mgsy` 从 `1.00` 改成 `2.00`），两次解析后断言 `basic_earnings_per_share` 仅一行、值为 `2.00`。第二项不写 raw，断言四张表均已创建且为空。第三项把 `lyb/latest.json` 写成 `{not-json`，其余模块有效；断言函数不抛异常、利润表为空、其余三张表仍有数据。

- [ ] **Step 4: 运行完整解析测试并确认失败**

Run: `uv run python -m unittest tests.test_structured.FinancialAnalysisStructuredTests -v`

Expected: FAIL，仅因尚未实现的财务解析功能。

### Task 2: 实现可追溯的财务结构化解析

**Files:**
- Modify: `src/zxtp/structured.py`
- Test: `tests/test_structured.py`

- [ ] **Step 1: 声明模块和已确认指标映射**

添加常量：

```python
FINANCIAL_ANALYSIS_ENTRY = "tdxf10_gg_cwfx"
FINANCIAL_INCOME_STATEMENT_MODULE = "lyb"
FINANCIAL_BALANCE_SHEET_MODULE = "zcfzb"
FINANCIAL_CASH_FLOW_MODULE = "xjllb"
FINANCIAL_KEY_METRICS_MODULE = "zyzb"

FINANCIAL_KEY_METRIC_FIELDS = {
    "basic_earnings_per_share": ("mgsy", "yuan"),
    "net_profit_excluding_non_recurring": ("kfjlr", "yuan"),
    "cash_flow_per_share": ("mgxjll", "yuan"),
    "total_profit": ("lrze", "yuan"),
    "net_profit": ("jyr", "yuan"),
    "return_on_equity_pct": ("jzzsyl", "%"),
    "gross_margin_pct": ("xsmll", "%"),
    "net_profit_yoy_pct": ("jlrtbzzl", "%"),
    "revenue_yoy_pct": ("yysrtb", "%"),
    "revenue_ytd_yoy_pct": ("yyzsrhb", "%"),
    "net_profit_ytd_yoy_pct": ("jlrhb", "%"),
    "average_return_on_equity_pct": ("pjjzcsyl", "%"),
    "net_profit_excluding_non_recurring_ytd_yoy_pct": ("kfjlrhb", "%"),
}
```

建立 `financial_income_statements`、`financial_balance_sheets`、`financial_cash_flows`，每张都使用：

```sql
stock_code VARCHAR NOT NULL,
report_date VARCHAR NOT NULL,
report_year INTEGER,
report_type VARCHAR NOT NULL,
statement_scope VARCHAR NOT NULL,
raw_field_name VARCHAR NOT NULL,
amount DOUBLE,
source_path VARCHAR NOT NULL,
source_entry VARCHAR NOT NULL,
source_module VARCHAR NOT NULL,
source_fetched_at VARCHAR,
source_response_hash VARCHAR,
structured_at VARCHAR NOT NULL
```

建立 `financial_key_metrics`，共用溯源字段并加入 `metric_name VARCHAR NOT NULL`、`metric_value DOUBLE`、`metric_unit VARCHAR NOT NULL`。所有金额保持元，百分比和每股指标不换算。

- [ ] **Step 2: 实现解析函数**

新增以下函数：

新增函数为 `parse_financial_analysis(stock_code, data_root)`、`read_optional_result_set_rows(paths)`、`replace_financial_statement(connection, table_name, stock_code, source_module, rows, paths, metadata, structured_at)`、`replace_financial_key_metrics(connection, stock_code, rows, paths, metadata, structured_at)` 与 `financial_report_period(report_date)`。

`parse_financial_analysis()` 必须验证股票代码、无条件执行四张 DDL、打开 `data_root / "warehouse" / "financial.duckdb"`，并在一个事务内替换全部四表。对每个模块通过 `RawCacheWriter.paths()` 找到 raw 与 meta。缺失、无效 JSON 或非对象 JSON 的模块返回空行，而非抛出错误。

`replace_financial_statement()` 先删该股票所有旧行；对结果集 0 的每条含 `rq` 的记录，跳过 `rq`，其余字段各插入一行。用 `raw_field_name` 保留 TQLEX 名称，`statement_scope="unknown"`。不要把 `nhytype` 或其他元数据误判为报表口径。

`financial_report_period()` 的映射必须为 `03-31 → q1`、`06-30 → semiannual`、`09-30 → q3`、`12-31 → annual`，无法识别时为 `unknown`。关键指标仅写入上一步映射中存在、且 `parse_float()` 成功的字段。

- [ ] **Step 3: 运行解析测试**

Run: `uv run python -m unittest tests.test_structured.FinancialAnalysisStructuredTests -v`

Expected: PASS。

- [ ] **Step 4: 提交解析器**

```bash
git add src/zxtp/structured.py tests/test_structured.py
git commit -m "feat: structure core cwfx financial data"
```

### Task 3: 接入 cwfx 命令与菜单

**Files:**
- Modify: `src/zxtp/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 写入失败测试**

在 `CliFetchCwfxTests` 的成功测试中 patch `zxtp.cli.parse_financial_analysis`，断言：

```python
parse_financial_analysis.assert_called_once_with("002736", Path(tmp))
self.assertIn("saved financial analysis structured data:", stdout.getvalue())
```

在 `CliFetchAllTests` 和 `CliUiCwfxTests` 各加等价断言，覆盖 `run_fetch_all()` 和 UI 菜单选项 3。

- [ ] **Step 2: 运行失败测试**

Run: `uv run python -m unittest tests.test_cli.CliFetchCwfxTests tests.test_cli.CliFetchAllTests tests.test_cli.CliUiCwfxTests -v`

Expected: FAIL，mock 尚未调用。

- [ ] **Step 3: 实现三个入口调用**

扩展 import：

```python
from .structured import (
    parse_company_overview,
    parse_financial_analysis,
    parse_research_ratings,
)
```

在 `main()` 的 `fetch-cwfx` 分支、`run_fetch_all()` 的 cwfx 下载循环之后以及 `run_ui()` 的 `module == "3"` 分支循环之后执行：

```python
database_path = parse_financial_analysis(stock_code, data_root)
print(f"saved financial analysis structured data: {database_path}", file=output_stream)
```

`run_fetch_all()` 用已有的 `valid_stock_code`；不得改变当前下载、重试或错误日志逻辑。

- [ ] **Step 4: 运行 CLI 集成测试**

Run: `uv run python -m unittest tests.test_cli.CliFetchCwfxTests tests.test_cli.CliFetchAllTests tests.test_cli.CliUiCwfxTests -v`

Expected: PASS。

- [ ] **Step 5: 提交 CLI 集成**

```bash
git add src/zxtp/cli.py tests/test_cli.py
git commit -m "feat: parse cwfx data after fetch"
```

### Task 4: 实现财务 AI Context

**Files:**
- Modify: `src/zxtp/ai_context.py`
- Modify: `src/zxtp/templates/ai_context/full_context.md.tpl`
- Modify: `tests/test_ai_context.py`

- [ ] **Step 1: 写入失败测试**

使用四个 cwfx raw 文件创建 `2022-12-31` 至 `2025-12-31` 四个年报以及 `2026-03-31` 季报，解析后调用 `generate_full_context()`。截取第 3 章并断言：

```python
self.assertIn("### 报告期说明", financial_section)
self.assertIn("2023 年报", financial_section)
self.assertIn("2024 年报", financial_section)
self.assertIn("2025 年报", financial_section)
self.assertIn("2026-03-31", financial_section)
self.assertNotIn("2022 年报", financial_section)
self.assertIn("净资产收益率（%）", financial_section)
self.assertIn("10.50", financial_section)
self.assertIn("每股经营现金流（元）", financial_section)
```

新增无 `financial.duckdb` 时返回“暂无结构化财务分析”的测试；将 `duckdb.connect` patch 成抛出 `duckdb.IOException` 时返回“结构化财务分析暂不可读取”的测试。两种情形都要保留 raw source 清单。

- [ ] **Step 2: 运行失败测试**

Run: `uv run python -m unittest tests.test_ai_context.AiContextGenerationTests -v`

Expected: FAIL，新动态内容尚未渲染。

- [ ] **Step 3: 实现受限渲染器**

在 `generate_full_context()` 添加：

```python
financial_analysis = render_financial_analysis(data_root, valid_stock_code)
```

并把它作为 `financial_analysis` 传给模板。新增：

新增函数为 `render_financial_analysis(data_root, stock_code)`、`financial_context_periods(rows)` 与 `render_financial_metric_table(rows)`。

查询 `financial_key_metrics` 的 `report_date, report_type, metric_name, metric_value, metric_unit`。选择最近三个 `annual` 日期，并加入最新任意报告期，去重后按日期升序。只渲染：

```python
FINANCIAL_CONTEXT_METRICS = (
    ("basic_earnings_per_share", "基本每股收益（元）", 3),
    ("total_profit", "利润总额（亿元）", 2),
    ("net_profit", "净利润（亿元）", 2),
    ("return_on_equity_pct", "净资产收益率（%）", 2),
    ("gross_margin_pct", "销售毛利率（%）", 2),
    ("revenue_yoy_pct", "营业收入同比（%）", 2),
    ("net_profit_yoy_pct", "净利润同比（%）", 2),
    ("cash_flow_per_share", "每股经营现金流（元）", 3),
)
```

仅将 `total_profit` 与 `net_profit` 的元值除以 `100_000_000`；缺值显示 `—`。输出“资产与负债”“现金流与效率”小节时，只说明三张报表明细已按 raw 字段结构化，未经确认的字段不显示猜测的金额。数据库缺失、锁定、表不存在或无股票记录，都返回固定降级文本。

模板第 3 章替换为：

```markdown
## 3. 财务分析

{financial_analysis}

### Raw 来源
```

- [ ] **Step 4: 运行 Context 测试**

Run: `uv run python -m unittest tests.test_ai_context.AiContextGenerationTests -v`

Expected: PASS。

- [ ] **Step 5: 提交 Context**

```bash
git add src/zxtp/ai_context.py src/zxtp/templates/ai_context/full_context.md.tpl tests/test_ai_context.py
git commit -m "feat: add cwfx financial AI context"
```

### Task 5: 更新数据字典并完整验证

**Files:**
- Modify: `docs/database-schema.md`

- [ ] **Step 1: 补齐数据字典**

在表一览增加四张财务表。三张报表注明粒度为“股票 + 报告期 + 原始字段名”，并声明 `raw_field_name` 不是已确认会计科目。为 `financial_key_metrics` 逐项列出 Task 2 的 `metric_name`、源字段和单位。记录金额以元存储，Context 只将确认的利润金额换算为亿元。

- [ ] **Step 2: 执行完整测试**

Run: `uv run python -m unittest discover -s tests -v`

Expected: PASS，既有与新增测试均通过。

- [ ] **Step 3: 检查提交前状态**

Run: `git diff --check && git status --short`

Expected: 没有 whitespace 错误；只包含本任务尚未提交的文档变更。

- [ ] **Step 4: 提交数据字典**

```bash
git add docs/database-schema.md
git commit -m "docs: document cwfx financial schema"
```

## Self-review

- **Spec coverage:** Task 2 处理四表、替换、raw 缺失与局部损坏；Task 3 覆盖 CLI、fetch-all 和 UI；Task 4 覆盖三年年报加最新期、格式和降级；Task 5 更新数据字典并全量验证。
- **Scope:** 不结构化其他 cwfx 子模块，不解析 PDF，不生成预测或投资建议。
- **Consistency:** 数据库固定为 `warehouse/financial.duckdb`，入口函数固定为 `parse_financial_analysis()`，Context 只消费已确认的关键指标。
