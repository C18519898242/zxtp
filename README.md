# ZXTP

ZXTP 是一个个人使用的 AI 投研辅助工具项目。它的目标不是做高频交易、自动荐股或替代投资判断，而是把券商 F10 / TQLEX 数据结构化、持久化，并整理成适合 AI 阅读和分析的上下文，帮助长期投资者更高效地研究股票基本面、成长性和潜在风险。

## 背景

项目使用者的投资目标偏长期、稳健和可持续现金流：

- 已有一定经济基础，希望通过长期投资逐步降低对工资收入的依赖。
- 偏好稳定收益，厌恶大幅波动和过度交易。
- 可以长期持有股票，不追求高频交易或短期技术分析。
- 有软件开发能力，也了解部分金融知识，但不把自己定位为专业金融从业研究员。
- 希望使用数据分析和 AI 辅助投资决策，重点关注基本面、成长性和风险。

第一阶段的重点是构建一个本地数据和 AI 研究基础设施，而不是直接构建交易系统。

## 第一阶段目标

先做一个本地优先的单人投研工具，核心能力包括：

1. 从券商 F10 页面背后的 TQLEX 接口获取股票基本面数据。
2. 对接口返回做原始缓存，避免每次重复下载。
3. 将常用数据解析为结构化表，支持简单 SQL 查询、排序和筛选。
4. 支持按 PE、PB、ROE、营收、净利润、现金流等指标查询和排序。
5. 将公司概要、财务指标、公告、机构调研、互动问答等内容整理为 AI 可读上下文。
6. 通过 Codex、CLI 或简单脚本交互，不强依赖 Web 页面。

## 暂不做的事情

第一阶段明确不做：

- 高频交易。
- 自动下单。
- 技术分析和短线信号。
- 基于回测优化参数的交易策略。
- 面向多用户的 SaaS 或商业化服务。
- 把 AI 输出直接当作买卖建议。

AI 的角色是辅助阅读、归纳、质疑和生成研究问题；最终投资判断仍由使用者完成。

## 数据源选择

当前优先探索券商 F10 页面使用的 TQLEX 接口。示例页面：

```text
http://zxtp.guosen.com.cn:7615/site/tdxf10/gg_zxts.html?vertype=0&style=black&gp=002648
```

页面 HTML 本身只包含结构，数据由 JavaScript 异步加载。核心链路为：

```text
gg_zxts.html
  -> ../lib/connect/req.js
  -> js/gg_zxts.js
  -> CallTQL(...)
  -> POST /TQLEX?Entry=CWServ.<entry>
  -> 返回 ResultSets / ColDes / Content
```

已经验证过的接口形态：

```text
POST http://zxtp.guosen.com.cn:7615/TQLEX?Entry=CWServ.tdxf10_gg_zxts
Body: {"Params":["002648","zxts",""]}
```

常见接口：

```text
公司概要:   tdxf10_gg_zxts      [stock_code, "gsgy", ""]
主要指标:   tdxf10_gg_zxts      [stock_code, "zxts", ""]
公司大事:   tdxf10_gg_zxts      [stock_code, "gsds", ""]
公司新闻:   tdxf10_gg_zxts      [stock_code, "gsxw", ""]
公司公告:   tdxf10_gg_zxts      [stock_code, "gsgg", ""]
公司研究:   tdxf10_gg_zxts      [stock_code, "gsyj", ""]
路演活动:   tdxf10_gg_zxts      [stock_code, "lyhd", ""]
机构调研:   tdxf10_gg_comreq    ["jgdy", stock_code]
互动问答:   tdxf10_gg_zxtstzzhd [stock_code, "1", "1", "5"]
公告详情:   tdxf10_gg_idreq     ["zx", rec_id]
```

TQLEX 不是公开行业标准，更像通达信 / 券商 F10 系统内部 RPC 网关。因此本项目会把它封装成可替换的数据源 adapter，避免业务逻辑直接绑定接口细节。

## 推荐技术架构

项目采用本地优先架构：

```text
Python CLI
  -> TQLEX Client
  -> Raw JSON Cache
  -> Parser / Normalizer
  -> DuckDB Warehouse
  -> AI Context Exporter
  -> Codex / LLM 分析
```

推荐技术栈：

- 语言：Python
- HTTP 客户端：requests 或 httpx
- 结构化分析库：DuckDB
- 原始响应缓存：本地 JSON 文件
- 文档正文：本地 TXT / Markdown 文件
- AI 上下文：Markdown + JSON 导出
- 交互方式：CLI 优先，Codex 直接读取项目文件；后续可选 Streamlit 或轻量 Web UI

## 开发环境和运行

本项目使用 `uv` 管理 Python 项目环境。可以把它理解为 Python 生态里偏项目级的依赖和运行工具，作用接近 Java 项目里的 Maven / Gradle 的一部分能力。

相关文件：

```text
pyproject.toml  # 项目声明，类似 pom.xml / build.gradle
uv.lock         # 锁定依赖解析结果，类似 package-lock.json
.venv/          # uv 创建的本地虚拟环境，通常不提交到 Git
```

首次拉取项目后，在项目根目录运行：

```powershell
uv sync
```

这会根据 `pyproject.toml` 和 `uv.lock` 创建/更新本地虚拟环境，并以 editable 方式安装当前项目。

运行 CLI：

```powershell
uv run python -m zxtp --help
uv run python -m zxtp fetch-gsgk 002736
```

运行测试：

```powershell
uv run python -m unittest discover -s tests -v
```

如果暂时不想使用 `uv`，也可以在 PowerShell 中临时把 `src` 加到 Python 模块搜索路径：

```powershell
$env:PYTHONPATH = "src"
python -m zxtp --help
python -m unittest discover -s tests -v
```

但长期建议使用 `uv run ...`，这样不需要手动处理 `PYTHONPATH`，也更容易保证不同机器上的依赖环境一致。

## 为什么用 DuckDB

本项目是单人本地投研工具，不需要一开始部署 PostgreSQL 或 MySQL 服务。DuckDB 的优势是：

- 一个 `.duckdb` 文件即可保存结构化分析数据。
- 不需要常驻数据库服务。
- 适合批量分析、聚合查询、排序筛选和时间序列研究。
- 与 Python、CSV、Parquet 集成自然。
- 便于备份和迁移。

JSON 文件仍然保留，但角色是原始证据归档；DuckDB 负责日常查询和分析。

## 数据分层

项目数据分三层：

```text
Raw 原始层:
保存 TQLEX 原始响应，不加工，便于追溯、重放和重新解析。

Structured 结构化层:
将财务指标、估值、公告列表、公司资料等解析为表。

AI Context 文档层:
将公告正文、公司概要、近期事件和关键指标整理为 AI 可读材料。
```

推荐目录结构：

```text
data/
  raw/
    tqlex/
      tdxf10_gg_zxts/
        stock=002648/
          module=zxts/
            latest.json
            history/              # 可选，仅在需要追溯接口变化时保留
              2026-06-16.json
          module=gsgy/
            latest.json
      tdxf10_gg_idreq/
        rec_id=21472158.json

  warehouse/
    research.duckdb

  documents/
    announcements/
      002648/
        21472158.txt
        21472158.pdf

  exports/
    ai_context/
      002648.md
      002648.json
```

第一版以 `latest.json` 为主，表示该接口和参数组合的最新原始响应。`history/` 是可选能力，用于调试 parser、追溯接口字段变化或保留重要时间点快照；日常查询和 AI 上下文默认不读取历史 raw 文件。

## 初始数据表设计

第一版表结构保持克制，先覆盖查询和 AI 分析需要。

### raw_requests

记录每次接口请求，保证数据可追溯。

```text
id
source
entry
params_json
stock_code
module
fetched_at
status
response_path
response_hash
error_message
```

### stocks

公司基础资料。

```text
stock_code
name
industry
sub_industry
business_summary
updated_at
source_request_id
```

### financial_metrics

主要财务指标。

```text
stock_code
report_period
revenue
profit_total
net_profit_parent
eps
book_value_per_share
roe
operating_cashflow_per_share
undistributed_profit_per_share
capital_reserve_per_share
updated_at
source_request_id
```

### valuation_snapshots

估值快照。

```text
stock_code
trade_date
pe_ttm
pe_lyr
pb
market_cap
total_shares
float_a_shares
updated_at
source_request_id
```

### announcements

公告列表和正文索引。

```text
stock_code
rec_id
title
publish_date
url
text_path
content_hash
updated_at
source_request_id
```

### research_events

机构调研、互动问答、路演、新闻、研究标题等事件型数据。

```text
stock_code
event_type
title
event_date
rec_id
text_path
updated_at
source_request_id
```

## 刷新策略

为避免重复下载，采用增量刷新和缓存优先策略：

```text
估值快照: 每个交易日刷新一次。
主要财务指标: 每周刷新；财报季可提高频率。
公司概要: 每月刷新，或手动刷新。
公告列表: 每天刷新。
公告正文: 只下载新的 rec_id。
机构调研 / 互动问答: 每天或每周刷新。
```

缓存判断原则：

- 同一接口、同一参数已有可用 `latest.json` 时，默认复用缓存；只有达到刷新周期或手动强制刷新时才重新请求。
- 公告正文以 rec_id 去重。
- 新响应写入 `latest.json` 前计算 hash；hash 未变化时不重复解析，必要时可把旧版本归档到 `history/`。
- 解析失败不删除原始响应，方便后续修复 parser 后重放。

## CLI 设想

第一版优先做 CLI，不急着做 Web 页面。

可能的命令：

```bash
zxtp fetch 002648
zxtp refresh-watchlist
zxtp query --sort pe_ttm --limit 50
zxtp query --where "roe > 10 and pe_ttm < 20"
zxtp brief 002648
zxtp ai-context 002648
```

其中：

- `fetch` 拉取并缓存指定股票数据。
- `refresh-watchlist` 批量刷新自选股。
- `query` 查询 DuckDB 中的结构化数据。
- `brief` 输出公司简报。
- `ai-context` 生成 AI 可读的 Markdown / JSON 上下文。

## AI 使用方式

AI 不直接调用 TQLEX 接口，而是读取已经落地的数据：

```text
DuckDB 结构化指标
+ 公告 / 调研 / 问答正文
+ 最近事件列表
+ 数据来源和时间戳
```

AI 输出应包含：

- 公司业务概要。
- 成长性观察。
- 盈利质量观察。
- 现金流和资产负债风险。
- 估值背景。
- 近期公告和事件影响。
- 需要继续人工验证的问题。
- 数据来源说明。

AI 不输出强制买入、卖出或目标价结论，除非后续明确设计估值模型和风险约束。

## 风险和边界

TQLEX 数据源存在不稳定性：

- 接口未公开承诺兼容性。
- 字段名和返回 ResultSet 顺序可能变化。
- 数据可能存在延迟、缺失或错误。
- 访问频率过高可能触发限制。
- 个人研究使用和商业再分发是不同边界。

因此项目需要：

- 低频、克制地请求接口。
- 保留原始响应和来源。
- 对关键结论提供证据链。
- 对重要数据与公告 PDF、交易所披露、其他数据源交叉验证。
- 将 TQLEX 作为 adapter，而不是系统唯一不可替换核心。

## 路线图

### Milestone 1: 数据链路最小闭环

- 实现 TQLEX Client。
- 支持抓取 `gsgy`、`zxts`、`gsgg`、公告详情。
- 保存 raw JSON。
- 初始化 DuckDB。
- 解析主要指标和估值快照。
- 支持单股票 `brief` 输出。

### Milestone 2: 查询和自选股

- 增加 watchlist 配置。
- 支持批量刷新。
- 支持按 PE、PB、ROE、营收、净利润排序。
- 支持简单条件过滤。

### Milestone 3: AI 上下文

- 导出单股票 AI Markdown。
- 汇总最近公告和关键财务变化。
- 生成基本面分析提示词模板。

### Milestone 4: 稳定性和可维护性

- 增加 parser 测试样例。
- 增加 raw response replay。
- 增加字段变化检测。
- 增加数据源 fallback 设计。

## 当前状态

项目处于设计和 README 起步阶段。下一步建议先实现最小数据链路：

```text
输入股票代码 002648
-> 调用 TQLEX 主要指标接口
-> 保存 raw JSON
-> 解析到 DuckDB
-> 用 SQL 查询 PE / PB / ROE
-> 生成一份 AI context Markdown
```

