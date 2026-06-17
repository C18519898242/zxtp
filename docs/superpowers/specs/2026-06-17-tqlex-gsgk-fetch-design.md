# TQLEX 公司概况抓取设计

日期：2026-06-17

## 目标

实现 ZXTP 的第一个最小数据链路步骤：从 TQLEX 接口抓取公司概况模块
`gsgk`，并把原始响应持久化到本地。

本设计刻意停在 raw JSON 落盘，不做解析、不写 DuckDB、不生成 `brief`。

## 范围

第一版只支持一个命令：

```bash
zxtp fetch-gsgk 002736
```

该命令只发送一个 TQLEX 请求：

```text
POST http://zxtp.guosen.com.cn:7615/TQLEX?Entry=CWServ.tdxf10_gg_gsgk
Body: {"Params":["0","002736",""]}
```

接口形态来自 `gg_gsgk.html` 页面及其脚本
`site/tdxf10/js/gg_gsgk.js`。该页面的“公司基本情况”区块使用
`tdxf10_gg_gsgk`，参数为 `["0", stock_code, ""]`。

## 不做事项

本里程碑不做：

- 抓取 `gsgy`、`zxts`、`gsgg`、公告详情或其他模块。
- 把 `ResultSets` 解析为结构化业务字段。
- 初始化或写入 DuckDB。
- 生成 `brief` 输出。
- 实现自选股、批量刷新、查询筛选、排序或 AI 上下文导出。

## 架构

实现拆成三个小单元。

### TqlexClient

`TqlexClient` 负责和 TQLEX 通信。

职责：

- 根据 base URL 和 entry 组装请求 URL。
- POST 包含 `Params` 的 JSON body。
- 使用明确、较短的超时时间。
- 在响应合法时返回原始响应文本和解析后的 JSON。
- 将网络失败、非 2xx 状态码、超时、非法 JSON 作为命令失败暴露出来。

`TqlexClient` 不应知道 `gsgk`、文件路径、DuckDB 或 CLI 展示格式。

### Raw Cache Writer

raw cache writer 负责本地持久化。

以股票 `002736` 为例，落盘路径为：

```text
data/raw/tqlex/tdxf10_gg_gsgk/
  stock=002736/
    module=gsgk/
      latest.json
      latest.meta.json
```

`latest.json` 保存经过 JSON 校验并格式化后的 TQLEX 响应。它不能重命名字段、
删除字段，也不能抽取结构化业务记录。`latest.meta.json` 保存请求和来源元数据：

```json
{
  "source": "tqlex",
  "entry": "tdxf10_gg_gsgk",
  "params": ["0", "002736", ""],
  "stock_code": "002736",
  "module": "gsgk",
  "source_url": "http://zxtp.guosen.com.cn:7615/TQLEX?Entry=CWServ.tdxf10_gg_gsgk",
  "fetched_at": "2026-06-17T00:00:00+08:00",
  "response_hash": "sha256:..."
}
```

如果响应不是合法 JSON，命令不能覆盖已有的 `latest.json`。

### CLI 命令

`fetch-gsgk` 是本设计唯一的用户可见命令。

职责：

- 校验 `stock_code` 必须是 6 位数字字符串。
- 组装 `entry = "tdxf10_gg_gsgk"` 和 `params = ["0", stock_code, ""]`。
- 调用 `TqlexClient`。
- 通过 raw cache writer 保存原始响应和 metadata。
- 成功时打印简短结果和输出路径。
- 失败时返回非零退出码。

## 数据流

```text
zxtp fetch-gsgk 002736
  -> 校验股票代码
  -> TqlexClient.call("tdxf10_gg_gsgk", ["0", "002736", ""])
  -> 将响应解析为 JSON
  -> 计算响应 hash
  -> 写入 latest.json
  -> 写入 latest.meta.json
  -> 打印输出路径
```

## 错误处理

以下情况命令失败，并且不能覆盖已有的 `latest.json`：

- 股票代码不是 6 位数字。
- HTTP 请求超时。
- 服务端返回非 2xx 状态码。
- 响应 body 为空。
- 响应 body 不是合法 JSON。
- 响应 JSON 包含非零 `ErrorCode`。
- cache 目录或文件无法写入。

失败信息应简洁，包含股票代码和失败步骤。不要完整打印敏感或过大的响应 body。

## 测试

测试应覆盖：

- `fetch-gsgk 002736` 的请求 URL 和 body。
- 6 位股票代码校验。
- raw cache 路径生成规则。
- 成功写入 `latest.json` 和 `latest.meta.json`。
- metadata 字段，包括 `entry`、`params`、`stock_code`、`module`、
  `fetched_at` 和 `response_hash`。
- 非法 JSON 不覆盖已有 `latest.json`。
- 非零 `ErrorCode` 被视为失败。

单元测试应 mock 网络请求。可以手动运行 live smoke test，但普通自动化测试不依赖真实网络。

## 验收标准

- 运行 `zxtp fetch-gsgk 002736` 会请求 `tdxf10_gg_gsgk`，参数为
  `["0", "002736", ""]`。
- 命令会在预期的 `gsgk` 路径下写入 raw JSON 和 metadata。
- 命令不会创建或修改 DuckDB 文件。
- 命令不会抓取任何非 `gsgk` 模块。
- 单元测试验证请求组装、cache 路径生成、成功持久化和失败行为。
