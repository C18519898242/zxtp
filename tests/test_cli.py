import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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


class CliFetchYbpjTests(unittest.TestCase):
    def test_fetch_ybpj_writes_each_raw_cache_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.return_value = (
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_ybpj"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with redirect_stdout(stdout):
                    exit_code = main(["fetch-ybpj", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            expected_modules = ["tzpjtj", "yzyq", "ylyctj", "ylycmx", "ycpjyjbg"]
            self.assertEqual(
                fake_client.call.call_args_list,
                [
                    call("tdxf10_gg_ybpj", ["002736", module])
                    for module in expected_modules
                ],
            )
            output = stdout.getvalue()
            self.assertIn("saved ybpj raw JSON", output)
            for module in expected_modules:
                data_path = (
                    Path(tmp)
                    / "raw"
                    / "tqlex"
                    / "tdxf10_gg_ybpj"
                    / "stock=002736"
                    / f"module={module}"
                    / "latest.json"
                )
                self.assertEqual(
                    json.loads(data_path.read_text(encoding="utf-8")),
                    {"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
                )

    def test_fetch_ybpj_rejects_invalid_stock_code(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["fetch-ybpj", "BAD"])

        self.assertEqual(exit_code, 1)
        self.assertIn("stock code must be exactly 6 digits", stderr.getvalue())


class CliFetchCwfxTests(unittest.TestCase):
    def test_fetch_cwfx_writes_each_raw_cache_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with redirect_stdout(stdout):
                    exit_code = main(["fetch-cwfx", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            cwfx_modules = [
                "gptype",
                "cwzd",
                "zcdjt",
                "cwgc",
                "cwbg",
                "zyzb",
                "zcfzb",
                "lyb",
                "xjllb",
                "yhzxzb",
                "qszxzb",
                "bxzxzb",
                "wdzb",
                "ylnl",
                "syzl",
                "yynl",
                "zbjg",
                "cznl",
                "xjll",
                "cznl2",
            ]
            expected_calls = [
                call("tdxf10_gg_cwfx", ["002736", module, ""])
                for module in cwfx_modules
            ]
            expected_calls.extend(
                [
                    call("tdxf10_gg_comreq", ["bdsm", "002736"]),
                    call("tdxf10_gg_cwfx_cbdp", ["002736", "1"]),
                ]
            )
            self.assertEqual(fake_client.call.call_args_list, expected_calls)
            output = stdout.getvalue()
            self.assertIn("saved cwfx raw JSON", output)
            self.assertIn("tdxf10_gg_cwfx_cbdp", output)

            expected_paths = [
                (
                    "tdxf10_gg_cwfx",
                    "zyzb",
                ),
                (
                    "tdxf10_gg_cwfx",
                    "cznl2",
                ),
                (
                    "tdxf10_gg_comreq",
                    "bdsm",
                ),
                (
                    "tdxf10_gg_cwfx_cbdp",
                    "cbdp",
                ),
            ]
            for entry, module in expected_paths:
                data_path = (
                    Path(tmp)
                    / "raw"
                    / "tqlex"
                    / entry
                    / "stock=002736"
                    / f"module={module}"
                    / "latest.json"
                )
                self.assertEqual(
                    json.loads(data_path.read_text(encoding="utf-8")),
                    {"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
                )

    def test_fetch_cwfx_rejects_invalid_stock_code(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["fetch-cwfx", "BAD"])

        self.assertEqual(exit_code, 1)
        self.assertIn("stock code must be exactly 6 digits", stderr.getvalue())


class CliUiYbpjTests(unittest.TestCase):
    def test_ui_fetches_ybpj_from_menu_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.return_value = (
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_ybpj"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            inputs = iter(["1", "2", "002736"])
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                exit_code = main(
                    ["ui", "--data-root", tmp],
                    input_func=lambda prompt="": next(inputs),
                    output=stdout,
                )

            self.assertEqual(exit_code, 0)
            fake_client.call.assert_any_call("tdxf10_gg_ybpj", ["002736", "tzpjtj"])
            output = stdout.getvalue()
            self.assertIn("ybpj", output)
            self.assertIn("saved ybpj raw JSON", output)


class CliUiCwfxTests(unittest.TestCase):
    def test_ui_fetches_cwfx_from_menu_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            inputs = iter(["1", "3", "002736"])
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                exit_code = main(
                    ["ui", "--data-root", tmp],
                    input_func=lambda prompt="": next(inputs),
                    output=stdout,
                )

            self.assertEqual(exit_code, 0)
            fake_client.call.assert_any_call("tdxf10_gg_cwfx", ["002736", "gptype", ""])
            fake_client.call.assert_any_call("tdxf10_gg_comreq", ["bdsm", "002736"])
            output = stdout.getvalue()
            self.assertIn("cwfx", output)
            self.assertIn("saved cwfx raw JSON", output)


class CliUiTests(unittest.TestCase):
    def test_ui_fetches_gsgk_from_menu_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.return_value = (
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            inputs = iter(["1", "1", "002736"])
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                exit_code = main(
                    ["ui", "--data-root", tmp],
                    input_func=lambda prompt="": next(inputs),
                    output=stdout,
                )

            self.assertEqual(exit_code, 0)
            fake_client.call.assert_called_once_with(
                "tdxf10_gg_gsgk", ["0", "002736", ""]
            )
            output = stdout.getvalue()
            self.assertIn("ZXTP", output)
            self.assertIn("下载数据", output)
            self.assertIn("公司概况 gsgk", output)
            self.assertIn("saved gsgk raw JSON", output)
