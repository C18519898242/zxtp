# ZXTP DuckDB 数据字典

数据库文件：`<data-root>/warehouse/research.duckdb`。默认数据根目录为 `D:/zxtp_data`，因此通常打开：

```text
D:/zxtp_data/warehouse/research.duckdb
```

本文说明当前已经结构化的表。每次重新下载同一只股票的对应模块时，程序会用最新 raw JSON 更新这些表。

## 表一览

| 表名 | 一行代表什么 | 当前来源 |
| --- | --- | --- |
| `company_overviews` | 一家上市公司的公司概况 | `gsgk` 公司概况 |
| `research_rating_summaries` | 某日、某个统计窗口的一组研报评级原始统计值 | `ybpj/tzpjtj` 投资评级统计 |
| `research_reports` | 一篇机构研报 | `ybpj/ycpjyjbg` 预测评级研报 |
| `earnings_forecast_windows` | 盈利预测的起始年份和原始状态 | `ybpj/ylyctj` 结果集 1 |
| `earnings_forecast_consensuses` | 一组原始盈利预测汇总值 | `ybpj/ylyctj` 结果集 2 |
| `earnings_forecast_history` | 一年对应的一组原始历史指标 | `ybpj/ylyctj` 结果集 3 |
| `earnings_forecast_snapshots` | 一个日期对应的一组原始预测快照值 | `ybpj/ylyctj` 结果集 4 |
| `earnings_forecast_metadata` | 一条盈利预测的来源日期和公司名称元信息 | `ybpj/ylyctj` 结果集 5 |
| `earnings_forecast_yearly_metrics` | 一个财年的已确认盈利指标 | `ybpj/ylyctj` 结果集 1 至 3 |
| `performance_expectations` | 一条业绩预期原始记录 | `ybpj/yzyq` 结果集 1 |
| `performance_expectation_estimates` | 一条业绩预期估算原始记录 | `ybpj/yzyq` 结果集 2 |
| `adjustment_factors` | 一条调整因子原始记录 | `ybpj/yzyq` 结果集 3 |
| `daily_close_prices` | 一个交易日的原始收盘价记录 | `ybpj/yzyq` 结果集 4 |

## 所有表共有的溯源字段

这些字段用于判断数据来自哪里、何时抓取，通常不用于投资分析：

| 字段 | 含义 |
| --- | --- |
| `source_path` | 对应 raw JSON 在本机的完整路径 |
| `source_entry` | TQLEX 接口入口，例如 `tdxf10_gg_ybpj` |
| `source_module` | TQLEX 子模块，例如 `gsgk`、`tzpjtj`、`ycpjyjbg` |
| `source_fetched_at` | raw JSON 的抓取时间，上海时区 ISO 时间 |
| `source_response_hash` | 原始响应的 SHA-256 哈希，用于判断源数据是否变化 |
| `structured_at` | 程序写入 DuckDB 的时间，上海时区 ISO 时间 |

## `company_overviews`：公司概况

**主键：** `stock_code`。一只股票最多一行，每次下载公司概况会覆盖更新该行。

| 字段 | 含义 | 例子 |
| --- | --- | --- |
| `stock_code` | 六位股票代码 | `002736` |
| `name` | 公司中文名称 | 国信证券股份有限公司 |
| `board` | 所属板块 | 深圳板块 |
| `english_name` | 公司英文名称 | Guosen Securities Co., Ltd. |
| `website` | 公司官网 | `https://www.guosen.com.cn` |
| `industry` | 所属行业 | 非银金融-证券 |
| `social_credit_code` | 统一社会信用代码 | `9144...` |
| `business_summary` | 主营业务摘要 | 财富管理与投资银行等 |
| `products` | 产品或服务 | 证券经纪等 |
| `controlling_shareholder` | 控股股东 | 深圳市投资控股有限公司 |
| `chairman` | 董事长 | 人名 |
| `general_manager` | 总经理 | 人名 |
| `legal_representative` | 法定代表人 | 人名 |
| `board_secretary` | 董事会秘书 | 人名 |
| `employee_count` | 员工总数 | `11085` |
| `phone` | 联系电话 | 电话号码 |
| `email` | 联系邮箱 | 邮箱地址 |
| `accounting_firm` | 会计师事务所 | 事务所名称 |
| `law_firm` | 律师事务所 | 律所名称 |
| `registered_address` | 注册地址 | 地址文本 |
| `office_address` | 办公地址 | 地址文本 |
| `company_profile` | 公司简介 | 简介文本 |
| `business_scope` | 经营范围 | 范围文本 |

**适合回答：** 这家公司是谁、做什么、属于什么行业、由谁控制、管理层是谁。

## `research_rating_summaries`：研报评级统计

**粒度：** 一行是一组 TQLEX 返回的评级统计原始值。相同 `rating_date` 可能有多行，不能只把日期当作唯一键。

| 字段 | 当前含义 | 使用建议 |
| --- | --- | --- |
| `stock_code` | 六位股票代码 | 与其他表关联的键 |
| `rating_date` | 最新评级日期，TQLEX 字段 `T016` | 可按日期排序 |
| `raw_sj` | 时间段，单位为天 | `30/60/90/180/360` 分别对应 1/2/3/6/12 个月 |
| `raw_zj` | 买入评级数量 | 对应网页“买入”列 |
| `raw_zc` | 增持评级数量 | 对应网页“增持”列 |
| `raw_zx` | 中性评级数量 | 对应网页“中性”列 |
| `raw_jc` | 减持评级数量 | 对应网页“减持”列 |
| `raw_mc` | 卖出评级数量 | 对应网页“卖出”列 |
| `raw_mr` | 评级合计数量 | 对应网页“合计”列 |
| `rating_value` | 评级系数，TQLEX 字段 `pj` | 对应网页“评级系数”，如 `5.00`、`4.80` |
| `raw_t006` | TQLEX 原始字段 `T006` | 当前样本可为空；网页“综合评级”不是可靠地直接取自该列 |

**综合评级：** 网页展示“买入”等综合评级，但当前 raw 样本中没有可靠的直接对应字段，`T006` 也可能为空。因此 DuckDB 暂未单独保存 `composite_rating`；确认页面计算或接口映射规则后再增加该字段。

## `research_reports`：逐篇研报

**主键：** `stock_code + report_id`。重新下载同一股票时，会替换该股票已有的研报记录，避免重复。

| 字段 | 含义 | 例子 |
| --- | --- | --- |
| `stock_code` | 六位股票代码 | `002736` |
| `report_id` | TQLEX 研报标识 | `20675920` |
| `report_date` | 研报日期，格式通常为 `YYYYMMDD` | `20260527` |
| `rating` | 机构给出的评级 | 买入、增持、持有等 |
| `institution` | 发布研报的证券机构 | 申万宏源、开源证券等 |
| `analysis_text` | 研报正文或投资分析意见 | 长文本 |
| `rating_score` | TQLEX 返回的评分字段 `T004` | 常见为 `5`、`4`；具体尺度待确认 |
| `title` | 研报标题 | 国信证券 2025 年报点评等 |

**适合回答：** 最近有哪些机构覆盖、机构给了什么评级、报告标题是什么、正文观点写了什么。

**阅读建议：**

- 先按 `report_date` 倒序查看最近报告。
- 用 `institution` 对比不同机构的观点与评级。
- `analysis_text` 是原始机构观点，不是 ZXTP 或 AI 的投资建议。
- 同一日期的多篇报告并不表示独立验证，可能引用相同公开信息。

## `earnings_forecast_*`：盈利预测原始结构

这五张表来自同一份 `ylyctj` raw JSON 的五个结果集。它们的行粒度不同，不能横向拼成一张表；程序按每张表的股票代码整体替换，以保持与最新 raw 缓存一致。

原始表继续保留所有 `raw_t...`、`raw_jg` 字段。已确认指标会另外写入年度派生表，不会改变或覆盖 raw 字段。

| 表名 | 一行代表什么 | 已确认字段 | 原始字段 |
| --- | --- | --- | --- |
| `earnings_forecast_windows` | 一个预测起始年份窗口 | `forecast_year`：预测起始年度；`raw_flag`：原始状态值 | `nyear`、`flag` |
| `earnings_forecast_consensuses` | 一组预测汇总原始值 | 暂无 | `T021` 至 `T038`（存为 `raw_t021` 至 `raw_t038`） |
| `earnings_forecast_history` | 一个财年对应的历史原始值 | `fiscal_year`：财年 | `T055`、`T059`、`T064`、`T018`、`T003`、`T012`、`T118` |
| `earnings_forecast_snapshots` | 一个数据日期对应的原始快照 | `snapshot_date`：数据日期 | `jg`、`T019`（存为 `raw_jg`、`raw_t019`） |
| `earnings_forecast_metadata` | 一条数据来源元信息 | `metadata_date`：数据日期；`company_name`：公司名称 | `t023`（存为 `raw_t023`） |
| `earnings_forecast_yearly_metrics` | 一个财年指标集合 | `fiscal_year`、`period_type`，以及下方列出的确认指标 | 由结果集 1 至 3 派生，raw 表仍保留来源 |

### `earnings_forecast_yearly_metrics`：年度可读指标

`period_type` 为 `actual` 表示历史实际值，为 `forecast` 表示未来预测值。金额源数据单位是万元，AI Context 展示时换算为亿元；DuckDB 中仍保存 `*_wan` 的万元原值。

| 字段 | 含义 | 来源字段 |
| --- | --- | --- |
| `earnings_per_share` | 每股收益，元 | 实际 `T055`；预测 `T036/T037/T038` |
| `book_value_per_share` | 每股净资产，元 | 实际 `T059`；预测 `T027/T028/T029` |
| `return_on_equity_pct` | 净资产收益率，% | 实际 `T064`；预测 `T024/T025/T026` |
| `net_profit_parent_wan` | 归属母公司净利润，万元 | 实际 `T018`；预测 `T033/T034/T035` |
| `net_profit_growth_pct` | 归母净利润同比增长率，% | 实际 `T118`；预测由相邻年度净利润计算 |
| `operating_revenue_wan` | 营业收入，万元 | 实际 `T003`；预测 `T021/T022/T023` |
| `operating_profit_wan` | 营业利润，万元 | 实际 `T012`；预测 `T030/T031/T032` |

市盈率不进入本表：当前 raw 数据无法稳定复现来源页面的预测市盈率，不能仅用当前收盘价和预测每股收益猜测口径。

**使用建议：**

- 在 DBeaver 中先按 `stock_code` 过滤；再分别查看这五张表，不要依赖行号把它们关联起来。
- AI Context 只显示预测起始年度、来源日期与各表记录数，避免把未确认口径的数值误写成投资结论。
- 后续字段字典确认后，可在保留 `raw_*` 原始列的基础上新增语义明确的业务列。

## `performance_*` 与 `daily_close_prices`：业绩预期和价格原始结构

这四张表来自 `yzyq` raw JSON 的四个结果集。它们按结果集分表保存，并在重新下载同一股票的 `yzyq` 后仅替换该股票在这四张表中的记录；空结果集只清空自己的表，不影响评级、研报或盈利预测统计。

| 表名 | 一行代表什么 | 已确认字段 | 原始字段 |
| --- | --- | --- | --- |
| `performance_expectations` | 一条当前业绩预期原始记录 | 暂无 | `defdate`、`mxdef`、`T003`、`T005`、`T024`、`T025`、`T031`、`T032`、`T033`（存为 `raw_*`） |
| `performance_expectation_estimates` | 一条业绩预期估算原始记录 | 暂无 | `T026`、`T030`、`T005`、`T006`、`T007`（存为 `raw_*`） |
| `adjustment_factors` | 一条调整因子原始记录 | `end_date`：源字段 `EndDate` 的日期值 | `AdjustingFactor`、`AdjustingConst`（存为 `raw_*`） |
| `daily_close_prices` | 一个交易日的原始收盘价 | `trading_day`：交易日 | `ClosePrice`（存为 `raw_close_price`，尚未确认复权和单位口径） |

**使用建议：**

- 用 `stock_code` 过滤后，按 `daily_close_prices.trading_day` 倒序查看最近价格；`raw_close_price` 是接口原始值，不应在未确认口径前用于收益率或估值计算。
- `raw_defdate`、`raw_t030` 等看起来像日期或数值的字段仍只表示源字段，不代表已经确认的财务业务含义。
- AI Context 只展示 `raw_defdate`、最近交易日、原始收盘价和记录数，避免将这些原始值误读为投资结论。

## 表之间如何关联

所有表都使用 `stock_code` 表示同一家公司。DBeaver 中可用它建立联表或过滤：

```text
company_overviews.stock_code
    = research_rating_summaries.stock_code
    = research_reports.stock_code
    = earnings_forecast_*.stock_code
    = earnings_forecast_yearly_metrics.stock_code
    = performance_*.stock_code
    = adjustment_factors.stock_code
    = daily_close_prices.stock_code
```

## `financial_*`：核心财务分析

财务分析数据写入独立的 `<data-root>/warehouse/financial.duckdb`。重新解析同一股票时，程序会以该股票最新的 raw snapshot 替换旧记录。

| 表名 | 一行代表什么 | 来源 |
| --- | --- | --- |
| `financial_income_statements` | 一个报告期的利润表原始字段 | `cwfx/lyb` |
| `financial_balance_sheets` | 一个报告期的资产负债表原始字段 | `cwfx/zcfzb` |
| `financial_cash_flows` | 一个报告期的现金流量表原始字段 | `cwfx/xjllb` |
| `financial_key_metrics` | 一个报告期的一项已确认主要指标 | `cwfx/zyzb` |

前三张表的共同粒度是 `stock_code + report_date + raw_field_name`。`raw_field_name` 是 TQLEX 原始字段标识，不代表已确认的会计科目；金额以元存储。共同的 `report_year`、`report_type`、`source_*` 和 `structured_at` 列用于筛选报告期及追溯 raw snapshot，`statement_scope` 当前固定为 `unknown`。

`financial_key_metrics` 的 `metric_name`、原始字段和单位如下：

| metric_name | 原始字段 | 单位 |
| --- | --- | --- |
| `basic_earnings_per_share` | `mgsy` | yuan |
| `net_profit_excluding_non_recurring` | `kfjlr` | yuan |
| `cash_flow_per_share` | `mgxjll` | yuan |
| `total_profit` | `lrze` | yuan |
| `net_profit` | `jyr` | yuan |
| `return_on_equity_pct` | `jzzsyl` | % |
| `gross_margin_pct` | `xsmll` | % |
| `net_profit_yoy_pct` | `jlrtbzzl` | % |
| `revenue_yoy_pct` | `yysrtb` | % |
| `revenue_ytd_yoy_pct` | `yyzsrhb` | % |
| `net_profit_ytd_yoy_pct` | `jlrhb` | % |
| `average_return_on_equity_pct` | `pjjzcsyl` | % |
| `net_profit_excluding_non_recurring_ytd_yoy_pct` | `kfjlrhb` | % |

AI Context 默认展示最近三个完整年度和最新报告期。展示时仅将 `total_profit` 与 `net_profit` 从元换算为亿元；其他数值沿用源单位。未确认口径的三表字段不在 AI Context 中解释为标准会计项目。

常见查看顺序：先打开 `company_overviews` 了解公司，再在 `research_reports` 按日期查看最近机构观点；`research_rating_summaries` 作为评级统计的原始数据补充；需要核对预测来源时，再查看 `earnings_forecast_*` 和 `performance_*` 表；查看近期价格时使用 `daily_close_prices`。

## 后续会新增的表

研报评级路线图中，阶段 2 尚未实施，预计会增加：

- `earnings_forecast_details`：机构盈利预测明细。

这些表完成后会继续补充到本文；在字段口径确认前，不会用含糊的 TQLEX 字段名伪装成确定的业务指标。
