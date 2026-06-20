# 研报评级 Structured 路线图

**目标：** 将 ybpj 的 5 类 raw JSON 分阶段写入 DuckDB，并在 AI Context 中呈现可读的评级与预测信息。

**当前状态：** 阶段 1 与阶段 3 已完成。DuckDB 已支持评级统计、逐篇研报，以及 `ylyctj` 的五个盈利预测原始结果集；阶段 2 与阶段 4 尚未结构化。

**共同约束：** 每一阶段都必须保留 `source_path`、`source_module`、`source_fetched_at`、`source_response_hash` 和 `structured_at`，并在下载后自动解析。DuckDB 被 DBeaver 占用时，下载或生成 AI Context 的提示必须明确说明原因。

---

## 目录

- [ ] 阶段 0：字段字典与样本基线
- [x] 阶段 1：评级统计与逐篇研报
- [ ] 阶段 2：机构盈利预测明细
- [x] 阶段 3：盈利预测汇总（原始字段优先）
- [ ] 阶段 4：业绩预期与价格序列
- [ ] 阶段 5：AI Context 完整展示与回归验证

## 阶段 0：字段字典与样本基线

**Raw 模块：** `tzpjtj`、`ycpjyjbg`、`ylycmx`、`ylyctj`、`yzyq`。

**已观察到的结果集：**

| 模块 | 结果集 | 当前样本字段 | 用途 |
| --- | --- | --- | --- |
| `tzpjtj` | 1 | `T016, sj, zj, mr, zc, zx, jc, mc, pj, T006` | 评级数量统计 |
| `ycpjyjbg` | 1 | `T011, sj, pj, jg, ytxt, T004, T039` | 逐篇研报 |
| `ylycmx` | 1 / 2 | `nyear` / `T012, T005, flag, T004, T006, T014, T015, T016, T003` | 机构盈利预测 |
| `ylyctj` | 1 至 5 | 年份、汇总预测、历史数据、日期与机构数据 | 盈利预测汇总 |
| `yzyq` | 1 至 4 | 预期日期、数值、复权因子、收盘价 | 业绩预期与价格序列 |

**任务：**

- [ ] 为每个字段记录中文业务含义、单位、日期格式和空值含义。
- [ ] 使用至少 `002736`、`600000`、`600018` 三只股票核对字段顺序；不以单一股票的空结果推断字段缺失。
- [ ] 将无法确认业务语义的字段暂时命名为 `raw_<source_column>`，不猜测含义。
- [ ] 将字段字典写入本文件的“字段确认记录”附录后，再进入相应解析阶段。

**验收：** 同一模块的非空样本具有一致的列集合；每个进入 DuckDB 的字段都有确定来源。

## 阶段 1：评级统计与逐篇研报

**目标表：**

```sql
CREATE TABLE research_rating_summaries (
    stock_code VARCHAR,
    rating_date VARCHAR,
    raw_sj BIGINT,
    raw_zj BIGINT,
    raw_mr BIGINT,
    raw_zc BIGINT,
    raw_zx BIGINT,
    raw_jc BIGINT,
    raw_mc BIGINT,
    rating_value DOUBLE,
    raw_t006 VARCHAR,
    source_path VARCHAR NOT NULL,
    source_module VARCHAR NOT NULL,
    source_fetched_at VARCHAR,
    source_response_hash VARCHAR,
    structured_at VARCHAR NOT NULL
);

CREATE TABLE research_reports (
    stock_code VARCHAR,
    report_id VARCHAR,
    report_date VARCHAR,
    rating VARCHAR,
    institution VARCHAR,
    analysis_text VARCHAR,
    rating_score VARCHAR,
    title VARCHAR,
    source_path VARCHAR NOT NULL,
    source_module VARCHAR NOT NULL,
    source_fetched_at VARCHAR,
    source_response_hash VARCHAR,
    structured_at VARCHAR NOT NULL,
    PRIMARY KEY (stock_code, report_id)
);
```

**解析映射：**

- `tzpjtj`：`T016` 写入 `rating_date`；`sj` 至 `mc` 原样写入 `raw_*` 列；`pj` 写入 `rating_value`；`T006` 写入 `raw_t006`。阶段 0 完成后，可将已确认的 `raw_*` 列改名为业务字段。
- `ycpjyjbg`：`T011` -> `report_id`，`sj` -> `report_date`，`pj` -> `rating`，`jg` -> `institution`，`ytxt` -> `analysis_text`，`T004` -> `rating_score`，`T039` -> `title`。

**任务：**

- [x] 在 `tests/test_structured.py` 增加：raw 统计和两篇研报写入后，DuckDB 返回正确行数、日期、评级、机构和标题。
- [x] 运行该测试，确认当前没有 `parse_research_ratings` 实现时失败。
- [x] 在 `src/zxtp/structured.py` 新增 `parse_research_ratings(stock_code, data_root)`，创建两张表并以事务替换该股票对应模块的旧行。
- [x] 将 `fetch-ybpj`、UI 的“研报评级 ybpj”、以及 `fetch-all` 接入解析器，打印 `saved research rating structured data`。
- [x] 在 `tests/test_cli.py` 断言下载完成后调用 `parse_research_ratings`。
- [x] 运行 `python -m unittest discover -s tests -v`。

**AI Context：** 在“研报评级”章节显示最近一次评级统计，以及按日期倒序的最近 5 篇研报（日期、机构、评级、标题）。正文只保留 raw 来源，避免文档过长。

**验收：** 自动化测试覆盖两张表、下载触发和 AI Context；真实 002736 raw 样本已在临时 DuckDB 验证。真实 `research.duckdb` 被外部锁占用时需关闭占用程序后再次转换。

## 阶段 2：机构盈利预测明细

**Raw 模块：** `ylycmx`。

**目标表：** `earnings_forecast_details`，一行代表一个机构在当前预测年份窗口的一次预测。

**初始字段：** `stock_code`、`forecast_year`、`forecast_date`、`rating_change`、`flag`、`rating`、`target_price`、`forecast_value_year_1`、`forecast_value_year_2`、`forecast_value_year_3`、`institution` 与全部来源元数据。

**映射：** 结果集 1 的 `nyear` -> `forecast_year`；结果集 2 的 `T012, T005, flag, T004, T006, T014, T015, T016, T003` 按上述字段顺序写入。阶段 0 负责确认后三个预测值的实际口径和单位。

**任务：**

- [ ] 写入覆盖空 `T006`、缺失预测值和多机构记录的失败测试。
- [ ] 实现模块级删旧写新，主键使用 `stock_code + forecast_year + forecast_date + institution`。
- [ ] 更新 `parse_research_ratings`，使 `ylycmx` 缺失或空数组时仍保留其余 ybpj 表的数据。
- [ ] 在 AI Context 增加“机构预测明细”小节，按最新预测日期展示最多 10 条。
- [ ] 运行完整测试套件。

**验收：** 同一机构的同一日期预测可稳定更新，不因重复解析产生重复行。

## 阶段 3：盈利预测汇总

**Raw 模块：** `ylyctj`。

**目标表：**

- `earnings_forecast_windows`：结果集 1 的预测起始年份和原始状态。
- `earnings_forecast_consensuses`：结果集 2 的原始汇总预测数值。
- `earnings_forecast_history`：结果集 3 的年度历史原始指标。
- `earnings_forecast_snapshots`：结果集 4 的日期原始快照值。
- `earnings_forecast_metadata`：结果集 5 的来源日期、原始值与公司名称。

**任务：**

- [x] 为每个结果集建立独立测试样本，验证没有将不同粒度的数据合并成一行。
- [x] 在 `parse_research_ratings` 中按结果集分别写入五张表，并在一次事务中更新。
- [x] 在 AI Context 增加“盈利预测统计（原始结构化）”小节，显示预测起始年度、来源日期与各表记录数。
- [x] 运行完整测试套件。
- [ ] 后续字段字典确认 `T021` 至 `T038`、`T002`、`T055`、`T059`、`T064`、`T118` 的业务口径和单位；确认前继续保留 `raw_*` 命名，不展示为财务指标。

**验收：** 年度、快照和汇总数据保留各自粒度；空结果集不会删除其他模块的历史数据；未经字段字典确认的数值不被解释为财务指标。

## 阶段 4：业绩预期与价格序列

**Raw 模块：** `yzyq`。

**目标表：**

- `performance_expectations`：结果集 1 的当前业绩预期。
- `performance_expectation_estimates`：结果集 2 的预测值。
- `adjustment_factors`：结果集 3 的复权因子与常数。
- `daily_close_prices`：结果集 4 的交易日收盘价。

**任务：**

- [ ] 在字段字典中确认 `T003, T005, T024, T025, T031, T032, T033` 与 `T026, T030, T005, T006, T007` 的口径。
- [ ] 使用多日期、空值和非交易日样本编写失败测试。
- [ ] 分表实现解析与股票级模块替换，价格序列主键使用 `stock_code + trading_day`。
- [ ] 仅在 AI Context 展示当前业绩预期和最近收盘价；完整价格序列保留给 DuckDB 分析，避免 Markdown 膨胀。
- [ ] 运行完整测试套件。

**验收：** 日频价格没有重复日期；AI Context 不会嵌入完整历史价格列表。

## 阶段 5：AI Context 完整展示与回归验证

**任务：**

- [ ] 在 `src/zxtp/ai_context.py` 增加 `render_research_ratings(data_root, stock_code)`；数据库不存在、表不存在、记录为空和 DBeaver 占用时返回可读提示，不让全文生成失败。
- [ ] 在 `src/zxtp/templates/ai_context/full_context.md.tpl` 用 `{research_ratings}` 替换“研报评级”的空占位。
- [ ] 在 `tests/test_ai_context.py` 构造 raw -> Structured -> Markdown 端到端样本，断言最近研报标题、机构和评级出现。
- [ ] 检查 `fetch-all` 先完成 ybpj 解析再生成 AI Context，确保一次下载得到最新文档。
- [ ] 运行 `python -m unittest discover -s tests -v` 和 `git diff --check`。

**验收：** 在关闭 DBeaver 后，UI 的“下载数据 -> 研报评级”会更新 DuckDB；随后“生成 AI Context”能展示最近研报与评级概览。

## 字段确认记录

| 日期 | 模块 | 已确认字段 | 依据 |
| --- | --- | --- | --- |
| 2026-06-19 | `ycpjyjbg` | `T011` 研报标识、`sj` 日期、`pj` 评级、`jg` 机构、`ytxt` 正文、`T004` 评分、`T039` 标题 | 002736 raw 样本 |
| 2026-06-19 | `ylycmx` | `nyear` 预测起始年份，结果集 2 含日期、评级、目标价、三列预测值和机构 | 002736 raw 样本；具体预测值口径待跨股票核验 |
| 2026-06-20 | `tzpjtj` | `T016` 为最新评级日期；`sj` 为时间段天数；`zj/zc/zx/jc/mc` 依次为买入/增持/中性/减持/卖出数量；`mr` 为合计；`pj` 为评级系数 | 投资评级统计页面与 002736 raw 样本逐行对照 |
| 2026-06-20 | `ylyctj` | 结果集 1 的 `nyear` 为预测起始年份；结果集 4 的 `rq` 为数据日期；结果集 5 的 `rq` 为来源日期、`T003` 为公司名称。其余字段按 `raw_*` 保存，未确认财务口径和单位。 | 002736 raw 样本与阶段 3 独立结果集测试 |
