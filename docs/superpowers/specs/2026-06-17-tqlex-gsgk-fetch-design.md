# TQLEX GSGK Fetch Design

Date: 2026-06-17

## Purpose

Implement the first minimal data-link step for ZXTP: fetch the company overview
module (`gsgk`) from the TQLEX endpoint and persist the raw response locally.
This design intentionally stops before parsing, DuckDB loading, or brief output.

## Scope

The first implementation supports one command:

```bash
zxtp fetch-gsgk 002736
```

It sends one TQLEX request:

```text
POST http://zxtp.guosen.com.cn:7615/TQLEX?Entry=CWServ.tdxf10_gg_gsgk
Body: {"Params":["0","002736",""]}
```

The values are derived from the `gg_gsgk.html` page and its
`site/tdxf10/js/gg_gsgk.js` script. For this page, the company overview grid
uses call name `tdxf10_gg_gsgk` and parameters `["0", stock_code, ""]`.

## Non-Goals

This milestone does not:

- Fetch `gsgy`, `zxts`, `gsgg`, announcement detail, or other modules.
- Parse `ResultSets` into structured business fields.
- Initialize or write DuckDB.
- Generate `brief` output.
- Implement watchlists, batch refresh, filtering, sorting, or AI context export.

## Architecture

The implementation has three small units.

### TqlexClient

`TqlexClient` owns HTTP communication with TQLEX.

Responsibilities:

- Build the request URL from a base URL and an entry name.
- POST a JSON body containing `Params`.
- Apply a short, explicit timeout.
- Return the raw response text and parsed JSON when valid.
- Surface network failures, non-2xx responses, timeouts, and invalid JSON as
  command failures.

The client should not know about `gsgk`, file paths, DuckDB, or CLI formatting.

### Raw Cache Writer

The raw cache writer owns local persistence.

For stock `002736`, it writes:

```text
data/raw/tqlex/tdxf10_gg_gsgk/
  stock=002736/
    module=gsgk/
      latest.json
      latest.meta.json
```

`latest.json` stores the TQLEX response JSON after validation and pretty
printing. It must not rename fields, drop fields, or extract structured business
records. `latest.meta.json` stores request and provenance metadata:

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

If a response is not valid JSON, the command must not overwrite an existing
`latest.json`.

### CLI Command

`fetch-gsgk` is the only user-facing command in this design.

Responsibilities:

- Validate that `stock_code` is a six-digit string.
- Compose `entry = "tdxf10_gg_gsgk"` and `params = ["0", stock_code, ""]`.
- Call `TqlexClient`.
- Save the raw response and metadata through the raw cache writer.
- Print a short success line with the output path.
- Return a non-zero exit code on failure.

## Data Flow

```text
zxtp fetch-gsgk 002736
  -> validate stock code
  -> TqlexClient.call("tdxf10_gg_gsgk", ["0", "002736", ""])
  -> parse response as JSON
  -> compute response hash
  -> write latest.json
  -> write latest.meta.json
  -> print output path
```

## Error Handling

The command fails without overwriting `latest.json` when:

- The stock code is not exactly six digits.
- The HTTP request times out.
- The server returns a non-2xx status.
- The response body is empty.
- The response body is not valid JSON.
- The response JSON contains a non-zero `ErrorCode`.
- The cache directory or files cannot be written.

Failures should produce concise messages that include the stock code and the
failed step. Sensitive or large response bodies should not be printed in full.

## Testing

Tests should cover:

- Request URL and body for `fetch-gsgk 002736`.
- Six-digit stock code validation.
- Raw cache path generation.
- Successful write of `latest.json` and `latest.meta.json`.
- Metadata fields including `entry`, `params`, `stock_code`, `module`,
  `fetched_at`, and `response_hash`.
- Invalid JSON does not overwrite an existing `latest.json`.
- Non-zero `ErrorCode` is treated as failure.

Network access should be mocked in unit tests. A live smoke test may be run
manually, but it is not required for ordinary automated test runs.

## Acceptance Criteria

- Running `zxtp fetch-gsgk 002736` fetches `tdxf10_gg_gsgk` with params
  `["0", "002736", ""]`.
- The command writes raw JSON and metadata under the expected `gsgk` path.
- The command does not create or modify DuckDB files.
- The command does not fetch any non-`gsgk` module.
- Unit tests verify request composition, cache path generation, successful
  persistence, and failure behavior.
