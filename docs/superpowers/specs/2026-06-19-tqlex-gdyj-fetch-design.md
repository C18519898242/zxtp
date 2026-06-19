# TQLEX 股东研究固定下载设计

## Goal

为股东研究页面 `gg_gdyj.html` 增加固定下载能力，沿用现有 raw JSON 缓存、CLI、UI、`fetch-all` 和 AI Context 模式。

## Scope

新增命令 `zxtp fetch-gdyj <stock_code>`，下载页面初始化时会加载的股东研究数据，并额外抓取最近一期机构持股明细。

固定模块使用 `tdxf10_gg_gdyj`：

- `kggd`
- `gdrs`
- `thygdrs`
- `ltgd`
- `sdgdbgq`
- `sdzqcyr`
- `cgbd`
- `jgcg`
- `jgcgz`

参数统一为 `[stock_code, module, "", date, "1", "1", "20"]`，除 `jgcgz` 外 `date` 为空。`jgcgz` 先调用 `tdxf10_gg_comreq` 参数 `["jgcg", stock_code]` 获取日期列表，取第一条非空日期作为最近日期。

最近一期机构持股明细使用 `tdxf10_gg_gdyj_jgcgmx`，参数为 `[stock_code, "", latest_date, "99"]`，其中 `99` 表示全部机构。缓存 module 使用 `jgcgmx`。

## Integration

- CLI 新增 `fetch-gdyj`。
- UI 下载菜单新增“股东研究 gdyj”。
- `fetch-all` 增加股东研究下载，并在完成后继续生成 AI Context。
- AI Context 增加股东研究 raw source 清单。

## Testing

按现有 `tests/test_cli.py` 风格添加 mock TQLEX 测试，验证调用顺序、最近日期提取、缓存路径、非法股票代码、UI 菜单和 `fetch-all` 集成。
