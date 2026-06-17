import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zxtp.tqlex import RawCacheWriter, TqlexClient, TqlexError, validate_stock_code


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


if __name__ == "__main__":
    unittest.main()