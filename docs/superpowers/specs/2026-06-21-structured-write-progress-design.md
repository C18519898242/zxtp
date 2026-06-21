# 结构化数据写入进度提示

## 背景

CLI 当前只在结构化解析完成后打印 `saved ... structured data`。当下载与数据库写入连续发生时，用户无法从终端区分正在等待网络请求还是正在解析并提交 DuckDB 数据。

## 目标

在每个现有结构化写库步骤开始前输出一个领域级进度提示，并保留现有完成日志与输出路径。

## 设计

在以下解析器调用前分别打印提示：

- `parse_company_overview()` 前：`saving company overview structured data...`
- `parse_research_ratings()` 前：`saving research rating structured data...`
- `parse_financial_analysis()` 前：`saving financial analysis structured data...`

覆盖参数式命令、`fetch-all` 和交互式菜单中已有的结构化写入路径。提示写入与既有日志相同的 `output_stream`，并且严格位于解析器调用之前；成功后的 `saved ... structured data: <path>` 日志保持不变。

## 测试

对三个 CLI 入口的既有测试增加输出顺序断言：开始提示必须出现，且位于相应完成日志之前。

## 非目标

- 不增加每张表、每批记录或事务级进度；
- 不修改 DuckDB 表、解析器行为、错误处理或重试策略；
- 不改变 raw 下载日志。
