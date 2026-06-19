from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class TqlexError(RuntimeError):
    """Raised when TQLEX fetching or persistence fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


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
            response_body = decode_response_body(exc.read())
            message = http_error_message(exc.code, response_body)
            raise TqlexError(
                message,
                status_code=exc.code,
                response_body=response_body,
            ) from exc
        except URLError as exc:
            raise TqlexError(f"TQLEX request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TqlexError("TQLEX request timed out") from exc

        if status < 200 or status >= 300:
            response_body = decode_response_body(raw_bytes)
            raise TqlexError(
                http_error_message(status, response_body),
                status_code=status,
                response_body=response_body,
            )
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


def decode_response_body(raw_bytes: bytes) -> str:
    if not raw_bytes:
        return ""
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("gb18030", errors="replace")


def http_error_message(status_code: int, response_body: str) -> str:
    message = f"TQLEX returned HTTP {status_code}"
    body_excerpt = response_body.strip()
    if body_excerpt:
        message = f"{message}: {truncate_text(body_excerpt, 500)}"
    return message


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...<truncated>"


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
