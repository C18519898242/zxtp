# TQLEX GSGK Fetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `zxtp fetch-gsgk <stock_code>`，只抓取 TQLEX 公司概况 `gsgk` 并保存 raw JSON 与 metadata。

**Architecture:** 使用标准库实现最小闭环，避免新增运行时依赖。`src/zxtp/tqlex.py` 放 TQLEX client、股票代码校验、hash 和 raw cache writer；`src/zxtp/cli.py` 只负责 argparse、命令编排和退出码。

**Tech Stack:** Python 3.11, stdlib `argparse`, `urllib.request`, `json`, `hashlib`, `unittest`, `tempfile`, `unittest.mock`。

---

## 文件结构

- Create: `src/zxtp/tqlex.py`
  - 负责 TQLEX HTTP 调用、响应校验、hash、raw cache 路径和文件写入。
- Modify: `src/zxtp/cli.py`
  - 从 hello world 改为 argparse CLI，新增 `fetch-gsgk` 子命令。
- Create: `tests/test_tqlex.py`
  - 覆盖股票代码校验、请求组装、响应解析、raw cache 写入和失败不覆盖。
- Create: `tests/test_cli.py`
  - 覆盖 CLI 参数校验、成功路径和失败退出码。
- Modify: `src/zxtp/__main__.py`
  - 让 `python -m zxtp ...` 使用 `raise SystemExit(main())` 传递退出码。

## Task 1: 股票代码校验和 raw cache 路径

**Files:**
- Create: `tests/test_tqlex.py`
- Create: `src/zxtp/tqlex.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_tqlex.py` with:

```python
import json
import tempfile
import unittest
from pathlib import Path

from zxtp.tqlex import RawCacheWriter, TqlexError, validate_stock_code


class StockCodeValidationTests(unittest.TestCase):
    def test_accepts_six_digit_stock_code(self) -> None:
        self.assertEqual(validate_stock_code("002736"), "002736")

    def test_rejects_non_six_digit_stock_code(self) -> None:
        with self.assertRaisesRegex(TqlexError, "stock code must be exactly 6 digits"):
            validate_stock_code("2736")

        with self.assertRaisesRegex(TqlexError, "stock code must be exactly 6 digits"):
            validate_stock_code("00273A")


class RawCachePathTests(unittest.TestCase):
    def test_gsgk_cache_paths_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = RawCacheWriter(Path(tmp))

            paths = writer.paths(
                entry="tdxf10_gg_gsgk",
                stock_code="002736",
                module="gsgk",
            )

            self.assertEqual(
                paths.data_path,
                Path(tmp)
                / "raw"
                / "tqlex"
                / "tdxf10_gg_gsgk"
                / "stock=002736"
                / "module=gsgk"
                / "latest.json",
            )
            self.assertEqual(
                paths.meta_path,
                Path(tmp)
                / "raw"
                / "tqlex"
                / "tdxf10_gg_gsgk"
                / "stock=002736"
                / "module=gsgk"
                / "latest.meta.json",
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python -m unittest tests.test_tqlex -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'zxtp.tqlex'`.

- [ ] **Step 3: 写最小实现**

Create `src/zxtp/tqlex.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class TqlexError(RuntimeError):
    """Raised when TQLEX fetching or persistence fails."""


def validate_stock_code(stock_code: str) -> str:
    if len(stock_code) != 6 or not stock_code.isdigit():
        raise TqlexError("stock code must be exactly 6 digits")
    return stock_code


@dataclass(frozen=True)
class CachePaths:
    data_path: Path
    meta_path: Path


class RawCacheWriter:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root

    def paths(self, entry: str, stock_code: str, module: str) -> CachePaths:
        base_path = (
            self.data_root
            / "raw"
            / "tqlex"
            / entry
            / f"stock={stock_code}"
            / f"module={module}"
        )
        return CachePaths(
            data_path=base_path / "latest.json",
            meta_path=base_path / "latest.meta.json",
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python -m unittest tests.test_tqlex -v
```

Expected: PASS, 3 tests.

- [ ] **Step 5: 提交**

```bash
git add src/zxtp/tqlex.py tests/test_tqlex.py
git commit -m "test: add tqlex validation and cache paths"
```

## Task 2: TQLEX Client 请求和响应校验

**Files:**
- Modify: `tests/test_tqlex.py`
- Modify: `src/zxtp/tqlex.py`

- [ ] **Step 1: 写失败测试**

Append to `tests/test_tqlex.py` before the `if __name__ == "__main__"` block:

```python
from unittest.mock import Mock

from zxtp.tqlex import TqlexClient


class FakeHttpResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.body = body
        self.status = status

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class TqlexClientTests(unittest.TestCase):
    def test_posts_tqlex_request_and_parses_json(self) -> None:
        opener = Mock(
            return_value=FakeHttpResponse(
                b'{"ResultSets":[],"ErrorCode":0,"ResultSetNum":0}'
            )
        )
        client = TqlexClient(base_url="http://example.test", opener=opener)

        result = client.call("tdxf10_gg_gsgk", ["0", "002736", ""])

        self.assertEqual(result.json_data["ErrorCode"], 0)
        self.assertEqual(result.raw_text, '{"ResultSets":[],"ErrorCode":0,"ResultSetNum":0}')
        request = opener.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk",
        )
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.data, b'{"Params":["0","002736",""]}')
        self.assertEqual(request.headers["Content-type"], "application/json")

    def test_rejects_non_2xx_response(self) -> None:
        opener = Mock(return_value=FakeHttpResponse(b"server error", status=500))
        client = TqlexClient(base_url="http://example.test", opener=opener)

        with self.assertRaisesRegex(TqlexError, "TQLEX returned HTTP 500"):
            client.call("tdxf10_gg_gsgk", ["0", "002736", ""])

    def test_rejects_invalid_json(self) -> None:
        opener = Mock(return_value=FakeHttpResponse(b"not json"))
        client = TqlexClient(base_url="http://example.test", opener=opener)

        with self.assertRaisesRegex(TqlexError, "TQLEX response is not valid JSON"):
            client.call("tdxf10_gg_gsgk", ["0", "002736", ""])

    def test_rejects_non_zero_error_code(self) -> None:
        opener = Mock(
            return_value=FakeHttpResponse(b'{"ErrorCode":1,"ErrorInfo":"error"}')
        )
        client = TqlexClient(base_url="http://example.test", opener=opener)

        with self.assertRaisesRegex(TqlexError, "TQLEX ErrorCode 1"):
            client.call("tdxf10_gg_gsgk", ["0", "002736", ""])
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python -m unittest tests.test_tqlex -v
```

Expected: FAIL with `ImportError: cannot import name 'TqlexClient'`.

- [ ] **Step 3: 写最小实现**

Replace `src/zxtp/tqlex.py` with:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class TqlexError(RuntimeError):
    """Raised when TQLEX fetching or persistence fails."""


def validate_stock_code(stock_code: str) -> str:
    if len(stock_code) != 6 or not stock_code.isdigit():
        raise TqlexError("stock code must be exactly 6 digits")
    return stock_code


@dataclass(frozen=True)
class TqlexResponse:
    raw_text: str
    json_data: dict[str, Any]


class TqlexClient:
    def __init__(
        self,
        base_url: str = "http://zxtp.guosen.com.cn:7615",
        timeout_seconds: float = 20.0,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    def call(self, entry: str, params: list[str]) -> TqlexResponse:
        url = f"{self.base_url}/TQLEX?Entry=CWServ.{entry}"
        body = json.dumps({"Params": params}, ensure_ascii=False, separators=(",", ":"))
        request = Request(
            url,
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                raw_bytes = response.read()
        except HTTPError as exc:
            raise TqlexError(f"TQLEX returned HTTP {exc.code}") from exc
        except URLError as exc:
            raise TqlexError(f"TQLEX request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TqlexError("TQLEX request timed out") from exc

        if status < 200 or status >= 300:
            raise TqlexError(f"TQLEX returned HTTP {status}")
        if not raw_bytes:
            raise TqlexError("TQLEX response body is empty")

        raw_text = raw_bytes.decode("utf-8")
        try:
            json_data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise TqlexError("TQLEX response is not valid JSON") from exc

        error_code = json_data.get("ErrorCode", 0)
        if error_code != 0:
            error_info = json_data.get("ErrorInfo", "")
            suffix = f": {error_info}" if error_info else ""
            raise TqlexError(f"TQLEX ErrorCode {error_code}{suffix}")

        return TqlexResponse(raw_text=raw_text, json_data=json_data)


@dataclass(frozen=True)
class CachePaths:
    data_path: Path
    meta_path: Path


class RawCacheWriter:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root

    def paths(self, entry: str, stock_code: str, module: str) -> CachePaths:
        base_path = (
            self.data_root
            / "raw"
            / "tqlex"
            / entry
            / f"stock={stock_code}"
            / f"module={module}"
        )
        return CachePaths(
            data_path=base_path / "latest.json",
            meta_path=base_path / "latest.meta.json",
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python -m unittest tests.test_tqlex -v
```

Expected: PASS, 7 tests.

- [ ] **Step 5: 提交**

```bash
git add src/zxtp/tqlex.py tests/test_tqlex.py
git commit -m "feat: add tqlex client"
```

## Task 3: Raw JSON 与 metadata 写入

**Files:**
- Modify: `tests/test_tqlex.py`
- Modify: `src/zxtp/tqlex.py`

- [ ] **Step 1: 写失败测试**

Append to `tests/test_tqlex.py` before the `if __name__ == "__main__"` block:

```python

class RawCacheWriteTests(unittest.TestCase):
    def test_writes_latest_json_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = RawCacheWriter(Path(tmp))

            paths = writer.write(
                entry="tdxf10_gg_gsgk",
                params=["0", "002736", ""],
                stock_code="002736",
                module="gsgk",
                source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk",
                json_data={"ResultSets": [], "ErrorCode": 0, "ResultSetNum": 0},
            )

            self.assertTrue(paths.data_path.exists())
            self.assertTrue(paths.meta_path.exists())
            self.assertEqual(
                json.loads(paths.data_path.read_text(encoding="utf-8")),
                {"ResultSets": [], "ErrorCode": 0, "ResultSetNum": 0},
            )
            metadata = json.loads(paths.meta_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["source"], "tqlex")
            self.assertEqual(metadata["entry"], "tdxf10_gg_gsgk")
            self.assertEqual(metadata["params"], ["0", "002736", ""])
            self.assertEqual(metadata["stock_code"], "002736")
            self.assertEqual(metadata["module"], "gsgk")
            self.assertEqual(
                metadata["source_url"],
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk",
            )
            self.assertTrue(metadata["fetched_at"].endswith("+08:00"))
            self.assertRegex(metadata["response_hash"], r"^sha256:[0-9a-f]{64}$")

    def test_does_not_overwrite_existing_latest_when_json_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = RawCacheWriter(Path(tmp))
            paths = writer.paths(
                entry="tdxf10_gg_gsgk",
                stock_code="002736",
                module="gsgk",
            )
            paths.data_path.parent.mkdir(parents=True)
            paths.data_path.write_text('{"old": true}', encoding="utf-8")

            with self.assertRaisesRegex(TqlexError, "json_data must be a dict"):
                writer.write(
                    entry="tdxf10_gg_gsgk",
                    params=["0", "002736", ""],
                    stock_code="002736",
                    module="gsgk",
                    source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk",
                    json_data=None,
                )

            self.assertEqual(paths.data_path.read_text(encoding="utf-8"), '{"old": true}')
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python -m unittest tests.test_tqlex -v
```

Expected: FAIL with `AttributeError: 'RawCacheWriter' object has no attribute 'write'`.

- [ ] **Step 3: 写最小实现**

Modify `src/zxtp/tqlex.py`:

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class TqlexError(RuntimeError):
    """Raised when TQLEX fetching or persistence fails."""


def validate_stock_code(stock_code: str) -> str:
    if len(stock_code) != 6 or not stock_code.isdigit():
        raise TqlexError("stock code must be exactly 6 digits")
    return stock_code


def serialize_json(json_data: dict[str, Any]) -> str:
    return json.dumps(json_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_json(json_data: dict[str, Any]) -> str:
    encoded = serialize_json(json_data).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def now_shanghai_iso() -> str:
    shanghai = timezone(timedelta(hours=8))
    return datetime.now(tz=shanghai).isoformat(timespec="seconds")


@dataclass(frozen=True)
class TqlexResponse:
    raw_text: str
    json_data: dict[str, Any]


class TqlexClient:
    def __init__(
        self,
        base_url: str = "http://zxtp.guosen.com.cn:7615",
        timeout_seconds: float = 20.0,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    def source_url(self, entry: str) -> str:
        return f"{self.base_url}/TQLEX?Entry=CWServ.{entry}"

    def call(self, entry: str, params: list[str]) -> TqlexResponse:
        body = json.dumps({"Params": params}, ensure_ascii=False, separators=(",", ":"))
        request = Request(
            self.source_url(entry),
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                raw_bytes = response.read()
        except HTTPError as exc:
            raise TqlexError(f"TQLEX returned HTTP {exc.code}") from exc
        except URLError as exc:
            raise TqlexError(f"TQLEX request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TqlexError("TQLEX request timed out") from exc

        if status < 200 or status >= 300:
            raise TqlexError(f"TQLEX returned HTTP {status}")
        if not raw_bytes:
            raise TqlexError("TQLEX response body is empty")

        raw_text = raw_bytes.decode("utf-8")
        try:
            json_data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise TqlexError("TQLEX response is not valid JSON") from exc

        error_code = json_data.get("ErrorCode", 0)
        if error_code != 0:
            error_info = json_data.get("ErrorInfo", "")
            suffix = f": {error_info}" if error_info else ""
            raise TqlexError(f"TQLEX ErrorCode {error_code}{suffix}")

        return TqlexResponse(raw_text=raw_text, json_data=json_data)


@dataclass(frozen=True)
class CachePaths:
    data_path: Path
    meta_path: Path


class RawCacheWriter:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root

    def paths(self, entry: str, stock_code: str, module: str) -> CachePaths:
        base_path = (
            self.data_root
            / "raw"
            / "tqlex"
            / entry
            / f"stock={stock_code}"
            / f"module={module}"
        )
        return CachePaths(
            data_path=base_path / "latest.json",
            meta_path=base_path / "latest.meta.json",
        )

    def write(
        self,
        *,
        entry: str,
        params: list[str],
        stock_code: str,
        module: str,
        source_url: str,
        json_data: dict[str, Any],
    ) -> CachePaths:
        if not isinstance(json_data, dict):
            raise TqlexError("json_data must be a dict")

        paths = self.paths(entry=entry, stock_code=stock_code, module=module)
        paths.data_path.parent.mkdir(parents=True, exist_ok=True)

        data_text = serialize_json(json_data)
        metadata = {
            "source": "tqlex",
            "entry": entry,
            "params": params,
            "stock_code": stock_code,
            "module": module,
            "source_url": source_url,
            "fetched_at": now_shanghai_iso(),
            "response_hash": sha256_json(json_data),
        }

        paths.data_path.write_text(data_text, encoding="utf-8")
        paths.meta_path.write_text(serialize_json(metadata), encoding="utf-8")
        return paths
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python -m unittest tests.test_tqlex -v
```

Expected: PASS, 9 tests.

- [ ] **Step 5: 提交**

```bash
git add src/zxtp/tqlex.py tests/test_tqlex.py
git commit -m "feat: persist tqlex raw cache"
```

## Task 4: CLI `fetch-gsgk`

**Files:**
- Create: `tests/test_cli.py`
- Modify: `src/zxtp/cli.py`
- Modify: `src/zxtp/__main__.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_cli.py` with:

```python
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from zxtp.cli import main
from zxtp.tqlex import TqlexResponse


class CliFetchGsgkTests(unittest.TestCase):
    def test_fetch_gsgk_writes_raw_cache_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.return_value = (
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with redirect_stdout(stdout):
                    exit_code = main(["fetch-gsgk", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            fake_client.call.assert_called_once_with(
                "tdxf10_gg_gsgk", ["0", "002736", ""]
            )
            output = stdout.getvalue()
            self.assertIn("saved gsgk raw JSON", output)
            self.assertIn("latest.json", output)
            data_path = (
                Path(tmp)
                / "raw"
                / "tqlex"
                / "tdxf10_gg_gsgk"
                / "stock=002736"
                / "module=gsgk"
                / "latest.json"
            )
            self.assertEqual(
                json.loads(data_path.read_text(encoding="utf-8")),
                {"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )

    def test_fetch_gsgk_rejects_invalid_stock_code(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["fetch-gsgk", "BAD"])

        self.assertEqual(exit_code, 1)
        self.assertIn("stock code must be exactly 6 digits", stderr.getvalue())
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python -m unittest tests.test_cli -v
```

Expected: FAIL because `main()` does not accept an argv list and `fetch-gsgk` is not implemented.

- [ ] **Step 3: 写最小实现**

Replace `src/zxtp/cli.py` with:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .tqlex import RawCacheWriter, TqlexClient, TqlexError, validate_stock_code


GSGK_ENTRY = "tdxf10_gg_gsgk"
GSGK_MODULE = "gsgk"
GSGK_PARAM_KIND = "0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zxtp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_gsgk = subparsers.add_parser(
        "fetch-gsgk",
        help="Fetch TQLEX company overview raw JSON for one stock.",
    )
    fetch_gsgk.add_argument("stock_code")
    fetch_gsgk.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
        help="Data root directory. Defaults to ./data.",
    )

    return parser


def fetch_gsgk(stock_code: str, data_root: Path) -> Path:
    valid_stock_code = validate_stock_code(stock_code)
    params = [GSGK_PARAM_KIND, valid_stock_code, ""]
    client = TqlexClient()
    response = client.call(GSGK_ENTRY, params)

    writer = RawCacheWriter(data_root)
    paths = writer.write(
        entry=GSGK_ENTRY,
        params=params,
        stock_code=valid_stock_code,
        module=GSGK_MODULE,
        source_url=client.source_url(GSGK_ENTRY),
        json_data=response.json_data,
    )
    return paths.data_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "fetch-gsgk":
            data_path = fetch_gsgk(args.stock_code, args.data_root)
            print(f"saved gsgk raw JSON: {data_path}")
            return 0
    except TqlexError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 修正 `python -m zxtp` 退出码传递**

Replace `src/zxtp/__main__.py` with:

```python
from .cli import main

raise SystemExit(main())
```

- [ ] **Step 5: 运行 CLI 测试确认通过**

Run:

```bash
python -m unittest tests.test_cli -v
```

Expected: PASS, 2 tests.

- [ ] **Step 6: 运行全部单元测试确认通过**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: PASS, 11 tests.

- [ ] **Step 7: 提交**

```bash
git add src/zxtp/cli.py src/zxtp/__main__.py tests/test_cli.py
git commit -m "feat: add fetch-gsgk cli"
```

## Task 5: 手动 smoke test 和分支推送

**Files:**
- No planned source changes.

- [ ] **Step 1: 运行全部测试**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: PASS, 11 tests.

- [ ] **Step 2: 运行 live smoke test**

Run:

```bash
python -m zxtp fetch-gsgk 002736
```

Expected: command exits `0` and prints a path ending with:

```text
data\raw\tqlex\tdxf10_gg_gsgk\stock=002736\module=gsgk\latest.json
```

- [ ] **Step 3: 检查落盘文件**

Run:

```bash
Test-Path data\raw\tqlex\tdxf10_gg_gsgk\stock=002736\module=gsgk\latest.json
Test-Path data\raw\tqlex\tdxf10_gg_gsgk\stock=002736\module=gsgk\latest.meta.json
```

Expected:

```text
True
True
```

- [ ] **Step 4: 确认没有 DuckDB 文件**

Run:

```bash
Get-ChildItem -Recurse data\warehouse
```

Expected: only `.gitkeep` is present; no `.duckdb` file exists.

- [ ] **Step 5: 推送分支**

Run:

```bash
git status --short
git push
```

Expected: source and test changes are committed; only intentionally untracked local artifacts remain; branch pushes to `origin/dev/tqlex-gsgk-fetch`.

## 自审

- Spec coverage:
  - `fetch-gsgk` command: Task 4.
  - `tdxf10_gg_gsgk` and `["0", stock_code, ""]`: Task 2 and Task 4.
  - raw JSON path: Task 1 and Task 3.
  - metadata fields: Task 3.
  - no DuckDB and no other module fetch: Task 4 and Task 5.
  - mocked unit tests plus manual live smoke test: Tasks 2 through 5.
- Placeholder scan:
  - The red-flag scan was run and any hit caused by the plan text itself was removed.
- Type consistency:
  - `TqlexClient.call()` returns `TqlexResponse`.
  - `RawCacheWriter.write()` returns `CachePaths`.
  - CLI uses the same `GSGK_ENTRY`, `GSGK_MODULE`, and params shape used by tests.
