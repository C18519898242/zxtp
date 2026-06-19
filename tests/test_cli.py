import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zxtp.cli import main
from zxtp.tqlex import TqlexResponse


class WorkingDirectory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.previous: Path | None = None

    def __enter__(self) -> None:
        self.previous = Path.cwd()
        os.chdir(self.path)

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.previous is not None:
            os.chdir(self.previous)


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

    def test_fetch_gsgk_uses_configured_data_root_when_no_cli_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config.toml").write_text(
                '[data]\nroot = "configured-data"\n',
                encoding="utf-8",
            )
            fake_client = Mock()
            fake_client.source_url.return_value = (
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )

            with WorkingDirectory(workspace):
                with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                    exit_code = main(["fetch-gsgk", "002736"])

            self.assertEqual(exit_code, 0)
            self.assertTrue(
                (
                    workspace
                    / "configured-data"
                    / "raw"
                    / "tqlex"
                    / "tdxf10_gg_gsgk"
                    / "stock=002736"
                    / "module=gsgk"
                    / "latest.json"
                ).exists()
            )

    def test_fetch_gsgk_data_root_argument_overrides_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            explicit_root = workspace / "explicit-data"
            (workspace / "config.toml").write_text(
                '[data]\nroot = "configured-data"\n',
                encoding="utf-8",
            )
            fake_client = Mock()
            fake_client.source_url.return_value = (
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )

            with WorkingDirectory(workspace):
                with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                    exit_code = main(
                        ["fetch-gsgk", "002736", "--data-root", str(explicit_root)]
                    )

            self.assertEqual(exit_code, 0)
            self.assertTrue(
                (
                    explicit_root
                    / "raw"
                    / "tqlex"
                    / "tdxf10_gg_gsgk"
                    / "stock=002736"
                    / "module=gsgk"
                    / "latest.json"
                ).exists()
            )
            self.assertFalse((workspace / "configured-data").exists())


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


class CliFetchHyfxTests(unittest.TestCase):
    def test_fetch_hyfx_writes_each_raw_cache_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.return_value = (
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_hyfx"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with redirect_stdout(stdout):
                    exit_code = main(["fetch-hyfx", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            expected_modules = [
                "tot",
                "hyxw",
                "hyyb",
                "scbx",
                "gsgm",
                "gzsp",
                "cwgz",
                "fhrzb",
            ]
            self.assertEqual(
                fake_client.call.call_args_list,
                [
                    call("tdxf10_gg_hyfx", [module, "002736", ""])
                    for module in expected_modules
                ],
            )
            output = stdout.getvalue()
            self.assertIn("saved hyfx raw JSON", output)
            for module in expected_modules:
                data_path = (
                    Path(tmp)
                    / "raw"
                    / "tqlex"
                    / "tdxf10_gg_hyfx"
                    / "stock=002736"
                    / f"module={module}"
                    / "latest.json"
                )
                self.assertEqual(
                    json.loads(data_path.read_text(encoding="utf-8")),
                    {"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
                )

    def test_fetch_hyfx_rejects_invalid_stock_code(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["fetch-hyfx", "BAD"])

        self.assertEqual(exit_code, 1)
        self.assertIn("stock code must be exactly 6 digits", stderr.getvalue())


class CliExportAiContextTests(unittest.TestCase):
    def test_export_ai_context_writes_full_context_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["export-ai-context", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("saved AI context Markdown", output)
            output_path = (
                Path(tmp)
                / "exports"
                / "ai_context"
                / "002736"
                / "full_context.md"
            )
            self.assertTrue(output_path.exists())
            self.assertIn(
                "# 002736 研究上下文",
                output_path.read_text(encoding="utf-8"),
            )

    def test_export_ai_context_rejects_invalid_stock_code(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["export-ai-context", "BAD"])

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


class CliUiHyfxTests(unittest.TestCase):
    def test_ui_fetches_hyfx_from_menu_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.return_value = (
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_hyfx"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            inputs = iter(["1", "4", "002736"])
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                exit_code = main(
                    ["ui", "--data-root", tmp],
                    input_func=lambda prompt="": next(inputs),
                    output=stdout,
                )

            self.assertEqual(exit_code, 0)
            fake_client.call.assert_any_call("tdxf10_gg_hyfx", ["tot", "002736", ""])
            output = stdout.getvalue()
            self.assertIn("hyfx", output)
            self.assertIn("saved hyfx raw JSON", output)


class CliUiAiContextTests(unittest.TestCase):
    def test_ui_exports_ai_context_from_menu_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = iter(["2", "002736"])
            stdout = io.StringIO()

            exit_code = main(
                ["ui", "--data-root", tmp],
                input_func=lambda prompt="": next(inputs),
                output=stdout,
            )

            self.assertEqual(exit_code, 0)
            output_path = (
                Path(tmp)
                / "exports"
                / "ai_context"
                / "002736"
                / "full_context.md"
            )
            self.assertTrue(output_path.exists())
            output = stdout.getvalue()
            self.assertIn("AI Context", output)
            self.assertIn("saved AI context Markdown", output)


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
