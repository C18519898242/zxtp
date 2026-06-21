# 经营分析 AI Context 首版设计

**日期：** 2026-06-21
**分支：** `codex/business-analysis`

## 目标与范围

为 AI Context 的“4. 经营分析”提供可查询、可复用的结构化摘要。首版仅覆盖已下载的三个经营分析模块：

- `zyyw`：主营介绍与产品/服务；
- `jysj`：经营数据；
- `zygc`：主营构成。

前五大客户、前五大供应商和经营情况评述保留在 Raw 来源清单中，但不在本次解析和展示范围内。

## 架构决策

新增 `<data-root>/warehouse/business.duckdb`，不扩展 `research.duckdb`，也不在生成 Markdown 时直接解析 Raw JSON。

这样经营分析与财务分析一样，有独立的领域存储和稳定查询接口；原始响应字段变动时，兼容逻辑只需要维护在解析层。AI Context 只读取结构化表，且继续显示 Raw 文件、抓取时间和响应哈希用于追溯。

## 数据模型

### `business_profiles`

每只股票一行，保存 `zyyw` 的主营介绍与产品/服务：

- `stock_code`；
- `business_summary`（`T017`）；
- `products`（`cpmc`）；
- `source_path`、`source_entry`、`source_module`、`source_fetched_at`、`source_response_hash`、`structured_at`。

重新解析同一股票时，以最新 Raw snapshot 覆盖该股票现有记录。

### `business_operating_metrics`

每行表示一个“报告日 + 经营指标”的原始经营数据：

- `stock_code`、`report_date`、`metric_name`、`metric_value`；
- `metric_group_code`（保留 `N004` 原始分类码，暂不推断业务含义）；
- `source_set_index`（来源 ResultSet，便于追溯）；
- 通用来源与写入元数据。

同一 snapshot 中完全重复的“报告日、指标名、数值、分类码”只保留一行，避免 TQLEX 重复 ResultSet 导致 AI Context 重复展示。

### `business_compositions`

每行表示一个报告期内、按一种维度拆分的一项主营业务：

- `stock_code`、`report_date`、`dimension`（例如“按业务”）、`business_name`；
- `revenue_amount`、`revenue_ratio_pct`；
- `cost_amount`、`cost_ratio_pct`；
- `gross_profit_amount`、`gross_profit_ratio_pct`、`gross_margin_pct`；
- `source_path`、来源元数据与 `structured_at`。

`zygc` 中的报告日从其日期 ResultSet 的 `rq` 读取；无法取得日期时不写入构成明细，避免将未知期次误标为当前期。

## 下载与解析流程

`fetch-jyfx`、交互式“经营分析”以及 `fetch-all` 完成 Raw 下载后，调用 `parse_business_analysis(stock_code, data_root)`：

1. 读取本股票三个首版 Raw snapshot；
2. 验证表头和数据行长度，跳过空行与无法转换的数值；
3. 在单个事务中创建表、删除该股票旧记录、写入新 snapshot；
4. 成功后输出英文日志：`saved business analysis structured data: <path>`；开始写入前输出对应的 `saving ...` 日志。

缺少任一模块时，解析不把该模块伪造成空数据；其余可用模块仍可写入。数据库锁定或不可读错误沿用既有结构化模块的错误处理方式。

## AI Context 展示

生成 `full_context.md` 时，从 `business.duckdb` 读取：

1. “主营介绍”：显示可用的主营业务和产品/服务文本；
2. “经营数据”：选择存在数据的最新报告日，展示该期去重后的指标、数值；保留原始指标名称和原始单位文本，不臆测单位；
3. “主营构成”：选择最新报告日和“按业务”维度，展示业务名称、营业收入/占比、营业成本/占比、毛利/占比、毛利率。金额按亿元显示，百分比保留两位小数；
4. 没有结构化数据时，显示明确的下载提示；数据库不可读时，显示 DBeaver 可能占用数据库的现有风格提示；
5. Raw 来源区保持不变，仍列出完整经营分析下载集合。

## 测试与验收

新增单元测试，使用最小 Raw fixture 验证：

- 三类数据均写入 `business.duckdb`，并正确处理 `zygc` 的报告日和金额字段；
- `jysj` 的重复项被去重；
- `fetch-jyfx`、交互式路径和 `fetch-all` 都触发解析并输出写入前/后的英文日志；
- AI Context 渲染主营介绍、最新期经营数据和主营构成，且对缺失数据、数据库不存在、数据库被占用保持可读提示。

完整测试命令为：`uv run python -m unittest discover -s tests -q`。

## 非目标

- 不在本次为前五大客户、前五大供应商、经营情况评述新增表或摘要；
- 不解释 `jysj` 的 `N004` 分类码，也不将其推断为标准业务口径；
- 不修改现有财务、研究数据库的表结构或历史数据。
