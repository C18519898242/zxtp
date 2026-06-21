# 经营分析 AI Context 首版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将主营介绍、经营数据和主营构成写入独立的 `business.duckdb`，并渲染到 AI Context 的经营分析章节。

**Architecture:** `structured.py` 负责把三个经营 Raw snapshot 解析成三个领域表，删除同一股票的旧 snapshot 后在一个事务中写入新数据。`cli.py` 在经营分析下载完成后调用解析器；`ai_context.py` 只读 `business.duckdb` 并输出文本和两张最新期表格，模板仅负责占位。

**Tech Stack:** Python 3、DuckDB、`unittest`、现有 `RawCacheWriter`、`uv`。

---

## 文件结构

- 修改 `src/zxtp/structured.py`：经营分析常量、三张 DuckDB 表、解析函数与行转换函数。
- 修改 `src/zxtp/cli.py`：导入并在三个下载入口调用 `parse_business_analysis`，输出英文进度日志。
- 修改 `src/zxtp/ai_context.py`：查询并渲染经营分析摘要，向模板传入内容。
- 修改 `src/zxtp/templates/ai_context/full_context.md.tpl`：用 `{business_analysis}` 替换占位说明。
- 修改 `tests/test_structured.py`：覆盖三类原始数据写入、去重与缺失输入。
- 修改 `tests/test_cli.py`：覆盖 `fetch-jyfx`、交互式模块 5 与 `fetch-all` 的结构化调用和日志。
- 修改 `tests/test_ai_context.py`：覆盖最新期经营数据、主营构成和两种降级提示。

### Task 1: 建立经营分析结构化解析器

**Files:**

- Modify: `tests/test_structured.py`
- Modify: `src/zxtp/structured.py`

- [ ] **Step 1: 写入失败的结构化解析测试。**

  在 `tests/test_structured.py` 增加 `BusinessAnalysisStructuredTests`，并用 `RawCacheWriter` 写入如下最小 fixture：

  ```python
  zyyw = {
      "ErrorCode": 0,
      "ResultSets": [
          {"ColDes": [{"Name": "T017"}], "Content": [["Network services"]]},
          {"ColDes": [{"Name": "cpmc"}], "Content": [["Broadband"]]},
      ],
  }
  jysj = {
      "ErrorCode": 0,
      "ResultSets": [
          {"ColDes": [{"Name": "N001"}], "Content": [["2026-04-21"]]},
          {"ColDes": [{"Name": name} for name in ("N001", "N002", "N003", "N004")],
           "Content": [["2026-03-31", "Mobile customers (10k)", "100900", "1001"]]},
          {"ColDes": [{"Name": name} for name in ("N001", "N002", "N003", "N004")],
           "Content": [["2026-03-31", "Mobile customers (10k)", "100900", "1001"]]},
      ],
  }
  zygc = {
      "ErrorCode": 0,
      "ResultSets": [
          {"ColDes": [{"Name": name} for name in ("N000", "N001", "N002", "N003", "N004", "N005", "N006", "N007", "N008", "N009")],
           "Content": [["按业务", "4", "Wireless", "369092000000", "35.145360", "200000000000", "20.0", "169092000000", "50.0", "45.811"]]},
          {"ColDes": [], "Content": []},
          {"ColDes": [{"Name": "rq"}], "Content": [["20251231"]]},
      ],
  }
  ```

  调用 `structured.parse_business_analysis("002736", data_root)`，断言返回 `data_root / "warehouse" / "business.duckdb"`，并断言：

  ```sql
  SELECT business_summary, products FROM business_profiles;
  -- ('Network services', 'Broadband')

  SELECT report_date, metric_name, metric_value, metric_group_code
  FROM business_operating_metrics;
  -- ('2026-03-31', 'Mobile customers (10k)', 100900.0, '1001')

  SELECT report_date, dimension, business_name, revenue_amount, gross_margin_pct
  FROM business_compositions;
  -- ('2025-12-31', '按业务', 'Wireless', 369092000000.0, 45.811)
  ```

  再断言经营指标计数为 `1`，确认重复 ResultSet 被去重；另加一个仅写空 `ResultSets` 的测试，断言三张表被创建且行数均为零。

- [ ] **Step 2: 运行新测试，确认它因缺少 API 而失败。**

  运行：

  ```powershell
  uv run python -m unittest tests.test_structured.BusinessAnalysisStructuredTests -v
  ```

  预期：失败，原因是 `parse_business_analysis` 尚未定义。

- [ ] **Step 3: 在 `structured.py` 实现最小解析器和 schema。**

  在财务分析常量附近加入：

  ```python
  BUSINESS_ANALYSIS_ENTRY = "tdxf10_gg_jyfx"
  BUSINESS_OPERATING_DATA_ENTRY = "tdxf10_gg_jyfx_jysj"
  BUSINESS_PROFILE_MODULE = "zyyw"
  BUSINESS_OPERATING_METRICS_MODULE = "jysj"
  BUSINESS_COMPOSITION_MODULE = "zygc"
  ```

  在 schema 区新增 `BUSINESS_PROFILES_SCHEMA`、`BUSINESS_OPERATING_METRICS_SCHEMA`、`BUSINESS_COMPOSITIONS_SCHEMA`。三表都包含 `stock_code` 与标准来源字段；指标表额外包含 `report_date VARCHAR NOT NULL`、`metric_name VARCHAR NOT NULL`、`metric_value DOUBLE`、`metric_group_code VARCHAR`、`source_set_index INTEGER NOT NULL`；构成表包含 `report_date`、`dimension`、`business_name` 及八个金额/比例字段。

  新增：

  ```python
  def parse_business_analysis(stock_code: str, data_root: Path) -> Path:
      """Replace one stock's business-analysis snapshot in business.duckdb."""
  ```

  它必须：

  1. 使用 `RawCacheWriter.paths()` 获取 `zyyw`、`jysj`、`zygc` 的最新路径；
  2. 使用 `all_result_set_rows()`，而非只会读取第一个 ResultSet 的 `result_set_rows()`；
  3. 创建三张表，在一个 `BEGIN`/`COMMIT` 事务中按 `stock_code` 删除旧记录再插入新记录；异常时 `ROLLBACK` 后重新抛出；
  4. 以 `normalize_text` 和 `parse_float` 转换输入；`jysj` 只接受同时有 `N001`、`N002` 的行，不能转换的 `N003` 写入 `NULL`；用 `(report_date, metric_name, metric_value, metric_group_code)` 集合去重；
  5. 从 `zyyw` 的所有 ResultSet 查找 `T017`、`cpmc` 的第一条非空文本；
  6. 从 `zygc` 最后一个含 `rq` 的 ResultSet 取得日期，通过 `normalize_report_date` 将 `20251231` 转为 `2025-12-31`；只有取得日期时才插入构成行；映射 `N000..N009` 到设计文档约定列，跳过缺少 `N000` 或 `N002` 的行；
  7. 每个插入行写入 `paths.data_path.as_posix()`、入口、模块、metadata 的 `fetched_at`/`response_hash` 和同一个 `structured_at`。

  新增轻量帮助函数：

  ```python
  def normalize_report_date(value: str | None) -> str | None:
      if value is None:
          return None
      if len(value) == 8 and value.isdigit():
          return f"{value[:4]}-{value[4:6]}-{value[6:]}"
      return value
  ```

- [ ] **Step 4: 运行结构化测试，确认通过。**

  运行：

  ```powershell
  uv run python -m unittest tests.test_structured.BusinessAnalysisStructuredTests -v
  ```

  预期：两个新增测试均通过。

- [ ] **Step 5: 提交结构化解析器。**

  ```powershell
  git add src/zxtp/structured.py tests/test_structured.py
  git commit -m "feat: structure business analysis data"
  ```

### Task 2: 将解析器接入三个经营分析下载入口

**Files:**

- Modify: `tests/test_cli.py`
- Modify: `src/zxtp/cli.py`

- [ ] **Step 1: 写入失败的 CLI 接入测试。**

  在既有 `fetch-jyfx` 成功测试中 patch `zxtp.cli.parse_business_analysis`，使其返回 `Path(tmp) / "warehouse" / "business.duckdb"`。断言它以 `("002736", Path(tmp))` 被调用一次，且 `stdout` 包含：

  ```python
  "saving business analysis structured data..."
  "saved business analysis structured data:"
  ```

  对交互式选择模块 `"5"` 增加同样断言；对 `run_fetch_all` 的测试增加同样断言，确认它在 `saved jyfx raw JSON` 之后、开始分红融资下载之前调用解析器。

- [ ] **Step 2: 运行 CLI 测试，确认失败。**

  运行：

  ```powershell
  uv run python -m unittest tests.test_cli -v
  ```

  预期：新增 mock 的调用断言失败，因为三个入口尚未调用解析器。

- [ ] **Step 3: 接入解析器与英文日志。**

  在 `src/zxtp/cli.py` 的结构化导入列表中加入 `parse_business_analysis`。在以下三个 Raw 下载循环紧后加入对应代码：

  - `run_fetch_all()` 的经营分析段；
  - 交互式 `if module == "5"`；
  - 命令行 `if args.command == "fetch-jyfx"`。

  `run_fetch_all()` 使用：

  ```python
  print("saving business analysis structured data...", file=output_stream)
  database_path = parse_business_analysis(valid_stock_code, data_root)
  print(
      f"saved business analysis structured data: {database_path}",
      file=output_stream,
  )
  ```

  交互式模块 `"5"` 使用：

  ```python
  print("saving business analysis structured data...", file=output_stream)
  database_path = parse_business_analysis(stock_code, data_root)
  print(f"saved business analysis structured data: {database_path}", file=output_stream)
  ```

  命令行 `fetch-jyfx` 使用：

  ```python
  print("saving business analysis structured data...", file=output_stream)
  database_path = parse_business_analysis(args.stock_code, data_root)
  print(f"saved business analysis structured data: {database_path}", file=output_stream)
  ```

  三个入口均保持现有异常处理路径。

- [ ] **Step 4: 运行 CLI 测试，确认通过。**

  运行：

  ```powershell
  uv run python -m unittest tests.test_cli -v
  ```

  预期：所有 CLI 测试通过，原始下载调用次序保持不变。

- [ ] **Step 5: 提交下载接入。**

  ```powershell
  git add src/zxtp/cli.py tests/test_cli.py
  git commit -m "feat: persist business analysis after download"
  ```

### Task 3: 在 AI Context 渲染经营分析摘要

**Files:**

- Modify: `tests/test_ai_context.py`
- Modify: `src/zxtp/ai_context.py`
- Modify: `src/zxtp/templates/ai_context/full_context.md.tpl`

- [ ] **Step 1: 写入失败的 AI Context 测试。**

  在 `tests/test_ai_context.py` 新增 `write_business_context_raw(data_root)`，写入 Task 1 的 fixture、调用 `parse_business_analysis("002736", data_root)`，并生成 AI Context。把经营分析段切出：

  ```python
  business_section = text.split("## 4. 经营分析", 1)[1].split("## 5. 分红融资", 1)[0]
  ```

  断言该段包含：

  ```python
  "### 主营介绍"
  "Network services"
  "### 经营数据（截至 2026-03-31）"
  "| 指标 | 数值 |"
  "| Mobile customers (10k) | 100900.00 |"
  "### 主营构成（2025 年报，按业务）"
  "| Wireless | 3690.92 | 35.15 | 2000.00 | 20.00 | 1690.92 | 50.00 | 45.81 |"
  ```

  另加两项降级测试：没有 `business.duckdb` 时包含“暂无结构化经营分析”；创建空数据库并 patch `zxtp.ai_context.duckdb.connect` 抛出 `duckdb.IOException("database is locked")` 时包含“结构化经营分析暂不可读取”和 “DBeaver”。

- [ ] **Step 2: 运行 AI Context 测试，确认失败。**

  运行：

  ```powershell
  uv run python -m unittest tests.test_ai_context -v
  ```

  预期：新增文字和表格断言失败，模板仍显示旧占位文本。

- [ ] **Step 3: 实现只读查询和 Markdown 渲染。**

  在 `ai_context.py` 新增：

  ```python
  def render_business_analysis(data_root: Path, stock_code: str) -> str:
      """Render the first structured business-analysis summary for one stock."""
  ```

  使用只读连接查询：

  ```sql
  SELECT business_summary, products
  FROM business_profiles WHERE stock_code = ?

  SELECT report_date, metric_name, metric_value
  FROM business_operating_metrics
  WHERE stock_code = ?
    AND report_date = (
      SELECT max(report_date) FROM business_operating_metrics WHERE stock_code = ?
    )
  ORDER BY metric_name

  SELECT report_date, dimension, business_name, revenue_amount, revenue_ratio_pct,
         cost_amount, cost_ratio_pct, gross_profit_amount, gross_profit_ratio_pct,
         gross_margin_pct
  FROM business_compositions
  WHERE stock_code = ? AND dimension = '按业务'
    AND report_date = (
      SELECT max(report_date) FROM business_compositions
      WHERE stock_code = ? AND dimension = '按业务'
    )
  ORDER BY revenue_amount DESC NULLS LAST, business_name
  ```

  单独实现 `render_business_profile`、`render_operating_metrics_table`、`render_business_composition_table`，并按下列规则生成 Markdown：

  - 主营介绍仅输出非空项目；
  - 经营指标按测试所示两列表格，数值为 `—` 或两位小数；不输出分类码；
  - 构成金额除以 `100_000_000`，比例使用两位小数或 `—`；`2025-12-31` 的标题显示为 `2025 年报`，其他日期原样显示；
  - 没有任何可展示内容时返回“暂无结构化经营分析。请先下载经营分析数据。”；
  - 数据库不存在与连接错误分别返回上述测试要求的文本，连接错误信息包含“请断开 DBeaver 连接后重新生成 AI Context”。

  在 `generate_full_context()` 取得 `business_analysis = render_business_analysis(...)`，并向模板变量传入 `"business_analysis": business_analysis`。在模板中把经营分析的固定占位段改成：

  ```markdown
  {business_analysis}
  ```

- [ ] **Step 4: 运行 AI Context 测试，确认通过。**

  运行：

  ```powershell
  uv run python -m unittest tests.test_ai_context -v
  ```

  预期：所有 AI Context 测试通过，财务、公司概况与 Raw 来源的既有断言不变。

- [ ] **Step 5: 运行完整回归并提交。**

  运行：

  ```powershell
  uv run python -m unittest discover -s tests -q
  ```

  预期：退出码 `0`。

  ```powershell
  git add src/zxtp/ai_context.py src/zxtp/templates/ai_context/full_context.md.tpl tests/test_ai_context.py
  git commit -m "feat: render business analysis in AI context"
  ```

## 实施后验证

- [ ] 在工作区数据根目录执行 `uv run zxtp fetch-jyfx 600941`，确认 `D:/zxtp_data/warehouse/business.duckdb` 创建，日志包含保存前和保存后两条英文信息。
- [ ] 执行 `uv run zxtp export-ai-context 600941`，打开导出的 `full_context.md`，确认“经营分析”不再显示占位文案，且 Raw 来源段仍列出十个经营模块。
