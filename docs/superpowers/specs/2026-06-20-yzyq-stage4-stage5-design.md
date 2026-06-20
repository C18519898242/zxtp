# yzyq 阶段 4 与阶段 5 设计

## 目标

将 `ybpj/yzyq` 的四个 raw JSON 结果集写入 DuckDB，并让 AI Context 在不猜测财务口径的前提下显示可追溯的业绩预期与价格摘要。

## 范围与原则

- 采用 raw-first：未确认业务含义与单位的源字段一律保存为 `raw_<source_column>`。
- 四个结果集保持独立表和独立行粒度，禁止按行号或位置合并。
- 每张表保留统一来源元数据：`source_path`、`source_entry`、`source_module`、`source_fetched_at`、`source_response_hash`、`structured_at`。
- 重新下载同一股票的 `yzyq` 后，以事务替换这四张表中该股票的旧记录；缺失或空结果集不删除其他 ybpj 模块的数据。
- AI Context 仅显示已确认日期、原始最近收盘价和记录数量。它不把原始数值描述为营收、利润、涨跌幅或投资建议。

## DuckDB 数据模型

| 表 | 来源结果集 | 行粒度 | 已确认字段 | 原始字段策略 |
| --- | --- | --- | --- | --- |
| `performance_expectations` | 1 | 一条当前业绩预期记录 | 仅保留可确认的日期字段 | 其他字段为 `raw_*` |
| `performance_expectation_estimates` | 2 | 一条预期估算记录 | 仅保留可确认的日期字段 | 其他字段为 `raw_*` |
| `adjustment_factors` | 3 | 一条复权或常数原始记录 | 仅保留可确认的日期字段 | 其他字段为 `raw_*` |
| `daily_close_prices` | 4 | 一个交易日价格记录 | `trading_day`、`raw_close_price` | 未确认的辅助字段为 `raw_*` |

`daily_close_prices` 以 `stock_code + trading_day` 作为逻辑唯一标识。其余三张表不假设稳定业务主键，按股票级整表替换，避免凭空构造键。

## 解析与 AI Context

`parse_research_ratings(stock_code, data_root)` 在现有 `tzpjtj`、`ycpjyjbg`、`ylyctj` 解析之后，读取可选的 `yzyq` 缓存。缓存不存在时，已有 ybpj 结构化表保持不变；缓存存在时，在同一 DuckDB 事务中替换这四张表的该股票记录。

AI Context 的“研报评级”章节继续保留阶段 1 和阶段 3 内容，并追加“业绩预期与价格（原始结构化）”：最新预期记录的可确认日期、价格表最近交易日与原始收盘价、四张表的记录数量，以及字段口径待确认说明。

连接 DuckDB 时，数据库不存在、表尚未创建、记录为空、或数据库被 DBeaver 占用，都返回具体可读提示；其他章节和 Markdown 文件仍可生成。

## 测试与验收

测试使用临时目录写入 `yzyq` raw 缓存，执行 `parse_research_ratings`，再断言：

1. 四张表均创建，且每个结果集只进入对应表。
2. 同一股票重复解析不会残留旧行；空结果集只清空自己的表。
3. `daily_close_prices` 的日期和原始收盘价可按交易日排序读取。
4. `raw -> DuckDB -> Markdown` 端到端样本包含价格摘要、记录数量和字段口径提示。
5. 数据库不存在、缺少阶段 4 表与 DuckDB 连接异常时，AI Context 仍生成可读 Markdown。

所有实现完成后运行 `python -m unittest discover -s tests -v` 与 `git diff --check`。
