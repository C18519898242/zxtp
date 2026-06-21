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

import zxtp.cli as cli
from zxtp.cli import main
from zxtp.tqlex import TqlexError, TqlexResponse


def assert_output_precedes(
    test_case: unittest.TestCase, output: str, before: str, after: str
) -> None:
    test_case.assertIn(before, output)
    test_case.assertIn(after, output)
    test_case.assertLess(output.index(before), output.index(after))


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
    def test_fetch_gsgk_parses_company_overview_into_duckdb(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.return_value = (
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            database_path = Path(tmp) / "warehouse" / "research.duckdb"
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with patch(
                    "zxtp.cli.parse_company_overview",
                    return_value=database_path,
                ) as parse_company_overview:
                    with redirect_stdout(stdout):
                        exit_code = main(["fetch-gsgk", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            parse_company_overview.assert_called_once_with("002736", Path(tmp))
            self.assertIn(
                f"saved company overview structured data: {database_path}",
                stdout.getvalue(),
            )
            assert_output_precedes(
                self,
                stdout.getvalue(),
                "saving company overview structured data...",
                "saved company overview structured data:",
            )

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
    def test_fetch_ybpj_parses_research_ratings_into_duckdb(self) -> None:
        self.assertTrue(hasattr(cli, "parse_research_ratings"))
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.return_value = (
                "http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_ybpj"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            database_path = Path(tmp) / "warehouse" / "research.duckdb"
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with patch(
                    "zxtp.cli.parse_research_ratings",
                    return_value=database_path,
                ) as parse_research_ratings:
                    with redirect_stdout(stdout):
                        exit_code = main(["fetch-ybpj", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            parse_research_ratings.assert_called_once_with("002736", Path(tmp))
            self.assertIn(
                f"saved research rating structured data: {database_path}",
                stdout.getvalue(),
            )
            assert_output_precedes(
                self,
                stdout.getvalue(),
                "saving research rating structured data...",
                "saved research rating structured data:",
            )

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

            with (
                patch("zxtp.cli.TqlexClient", return_value=fake_client),
                patch("zxtp.cli.parse_financial_analysis") as parse_financial_analysis,
            ):
                with redirect_stdout(stdout):
                    exit_code = main(["fetch-cwfx", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            parse_financial_analysis.assert_called_once_with("002736", Path(tmp))
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
            self.assertIn("saved financial analysis structured data:", output)
            assert_output_precedes(
                self,
                output,
                "saving financial analysis structured data...",
                "saved financial analysis structured data:",
            )
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

    def test_fetch_cwfx_retries_failed_subcategory_and_logs_each_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )
            failures_before_success = 3
            failing_params = ["002736", "cwzd", ""]

            def fake_call(entry: str, params: list[str]) -> TqlexResponse:
                nonlocal failures_before_success
                if entry == "tdxf10_gg_cwfx" and params == failing_params:
                    if failures_before_success > 0:
                        failures_before_success -= 1
                        raise TqlexError(
                            "TQLEX returned HTTP 400: backend busy",
                            status_code=400,
                            response_body='{"reason":"backend busy"}',
                        )
                return TqlexResponse(
                    raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                    json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
                )

            fake_client.call.side_effect = fake_call
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with redirect_stdout(stdout):
                    exit_code = main(["fetch-cwfx", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                fake_client.call.call_args_list.count(
                    call("tdxf10_gg_cwfx", failing_params)
                ),
                4,
            )
            self.assertEqual(
                fake_client.call.call_args_list.count(
                    call("tdxf10_gg_cwfx", ["002736", "gptype", ""])
                ),
                1,
            )
            output = stdout.getvalue()
            self.assertIn("重试: tdxf10_gg_cwfx/cwzd 第 1/4 次失败", output)
            self.assertIn("重试: tdxf10_gg_cwfx/cwzd 第 2/4 次失败", output)
            self.assertIn("重试: tdxf10_gg_cwfx/cwzd 第 3/4 次失败", output)
            self.assertNotIn("重试: tdxf10_gg_cwfx/cwzd 第 4/4 次失败", output)
            log_path = Path(tmp) / "logs" / "tqlex_failures.jsonl"
            log_records = [
                json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(log_records), 3)
            self.assertEqual([record["attempt"] for record in log_records], [1, 2, 3])
            self.assertTrue(all(record["max_attempts"] == 4 for record in log_records))
            self.assertTrue(all(record["stock_code"] == "002736" for record in log_records))
            self.assertTrue(all(record["entry"] == "tdxf10_gg_cwfx" for record in log_records))
            self.assertTrue(all(record["module"] == "cwzd" for record in log_records))
            self.assertTrue(all(record["params"] == failing_params for record in log_records))
            self.assertTrue(all(record["status_code"] == 400 for record in log_records))
            self.assertTrue(
                all(record["response_body"] == '{"reason":"backend busy"}' for record in log_records)
            )

    def test_fetch_cwfx_logs_final_failed_subcategory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )
            fake_client.call.side_effect = TqlexError(
                "TQLEX returned HTTP 400: bad request",
                status_code=400,
                response_body="bad request detail",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with redirect_stderr(stderr):
                    exit_code = main(
                        ["fetch-cwfx", "002736", "--data-root", tmp],
                        output=stdout,
                    )

            self.assertEqual(exit_code, 1)
            self.assertEqual(fake_client.call.call_count, 4)
            output = stdout.getvalue()
            self.assertIn("重试: tdxf10_gg_cwfx/gptype 第 4/4 次失败", output)
            self.assertIn("TQLEX returned HTTP 400", stderr.getvalue())
            log_path = Path(tmp) / "logs" / "tqlex_failures.jsonl"
            log_records = [
                json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(log_records), 4)
            self.assertEqual([record["attempt"] for record in log_records], [1, 2, 3, 4])
            self.assertTrue(all(record["module"] == "gptype" for record in log_records))


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


class CliFetchJyfxTests(unittest.TestCase):
    def test_fetch_jyfx_writes_core_raw_cache_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )

            def fake_call(entry: str, params: list[str]) -> TqlexResponse:
                json_data = {"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0}
                if entry == "tdxf10_gg_comreq":
                    json_data = {
                        "ErrorCode": 0,
                        "ResultSets": [
                            {
                                "ColDes": [{"Name": "T002"}],
                                "Content": [["20241231"]],
                            }
                        ],
                        "ResultSetNum": 1,
                    }
                return TqlexResponse(raw_text=json.dumps(json_data), json_data=json_data)

            fake_client.call.side_effect = fake_call
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with redirect_stdout(stdout):
                    exit_code = main(["fetch-jyfx", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                fake_client.call.call_args_list,
                [
                    call("tdxf10_gg_jyfx", ["002736", "zyyw", ""]),
                    call("tdxf10_gg_jyfx_jysj", ["002736"]),
                    call("tdxf10_gg_comreq", ["zygcfx", "002736"]),
                    call("tdxf10_gg_jyfx", ["002736", "zygc", "20241231"]),
                    call("tdxf10_gg_comreq", ["qwm", "002736"]),
                    call("tdxf10_gg_jyfx", ["002736", "qwm", "20241231"]),
                    call("tdxf10_gg_comreq", ["qwmgys", "002736"]),
                    call("tdxf10_gg_jyfx", ["002736", "qwmgys", "20241231"]),
                    call("tdxf10_gg_comreq", ["jyqk", "002736"]),
                    call("tdxf10_gg_jyfx", ["002736", "0", "20241231"]),
                ],
            )
            output = stdout.getvalue()
            self.assertIn("saved jyfx raw JSON", output)
            expected_paths = [
                ("tdxf10_gg_jyfx", "zyyw"),
                ("tdxf10_gg_jyfx_jysj", "jysj"),
                ("tdxf10_gg_comreq", "zygcfx"),
                ("tdxf10_gg_jyfx", "zygc"),
                ("tdxf10_gg_comreq", "qwm"),
                ("tdxf10_gg_jyfx", "qwm"),
                ("tdxf10_gg_comreq", "qwmgys"),
                ("tdxf10_gg_jyfx", "qwmgys"),
                ("tdxf10_gg_comreq", "jyqk"),
                ("tdxf10_gg_jyfx", "jyqk"),
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
                self.assertTrue(data_path.exists())

    def test_fetch_jyfx_rejects_invalid_stock_code(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["fetch-jyfx", "BAD"])

        self.assertEqual(exit_code, 1)
        self.assertIn("stock code must be exactly 6 digits", stderr.getvalue())


class CliFetchFhrzTests(unittest.TestCase):
    def test_fetch_fhrz_writes_core_raw_cache_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )

            def fake_call(entry: str, params: list[str]) -> TqlexResponse:
                json_data = {"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0}
                if entry == "tdxf10_gg_fhrz_zfhpmx" and params[0] == "zfpg_bgq":
                    json_data = {
                        "ErrorCode": 0,
                        "ResultSets": [
                            {
                                "ColDes": [{"Name": "rq"}],
                                "Content": [["2025-01-02"]],
                            }
                        ],
                        "ResultSetNum": 1,
                    }
                return TqlexResponse(raw_text=json.dumps(json_data), json_data=json_data)

            fake_client.call.side_effect = fake_call
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with redirect_stdout(stdout):
                    exit_code = main(["fetch-fhrz", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                fake_client.call.call_args_list,
                [
                    call("tdxf10_gg_fhrz", ["002736", "pxmz"]),
                    call("tdxf10_gg_fhrz", ["002736", "fh"]),
                    call("tdxf10_gg_fhrz", ["002736", "fh_zzt"]),
                    call("tdxf10_gg_fhrz", ["002736", "fhlszs_glzfl"]),
                    call("tdxf10_gg_fhrz", ["002736", "fhlszs_gxl"]),
                    call("tdxf10_gg_fhrz", ["002736", "fhpm_glzfl"]),
                    call("tdxf10_gg_fhrz", ["002736", "fhpm_gxl"]),
                    call("tdxf10_gg_fhrz", ["002736", "fhpm_pxrzb"]),
                    call("tdxf10_gg_fhrz", ["002736", "pf"]),
                    call("tdxf10_gg_fhrz_zfhpmx", ["zfpg_bgq", "002736", ""]),
                    call("tdxf10_gg_fhrz_zfhpmx", ["zfpg", "002736", "2025-01-02"]),
                    call("tdxf10_gg_fhrz", ["002736", "zf"]),
                    call("tdxf10_gg_fhrz", ["002736", "gqjl"]),
                    call("tdxf10_gg_fhrz", ["002736", "kzzdfxyss"]),
                ],
            )
            output = stdout.getvalue()
            self.assertIn("saved fhrz raw JSON", output)
            expected_paths = [
                ("tdxf10_gg_fhrz", "pxmz"),
                ("tdxf10_gg_fhrz", "fh"),
                ("tdxf10_gg_fhrz", "fh_zzt"),
                ("tdxf10_gg_fhrz", "fhlszs_glzfl"),
                ("tdxf10_gg_fhrz", "fhlszs_gxl"),
                ("tdxf10_gg_fhrz", "fhpm_glzfl"),
                ("tdxf10_gg_fhrz", "fhpm_gxl"),
                ("tdxf10_gg_fhrz", "fhpm_pxrzb"),
                ("tdxf10_gg_fhrz", "pf"),
                ("tdxf10_gg_fhrz_zfhpmx", "zfpg_bgq"),
                ("tdxf10_gg_fhrz_zfhpmx", "zfpg"),
                ("tdxf10_gg_fhrz", "zf"),
                ("tdxf10_gg_fhrz", "gqjl"),
                ("tdxf10_gg_fhrz", "kzzdfxyss"),
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
                self.assertTrue(data_path.exists())

    def test_fetch_fhrz_rejects_invalid_stock_code(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["fetch-fhrz", "BAD"])

        self.assertEqual(exit_code, 1)
        self.assertIn("stock code must be exactly 6 digits", stderr.getvalue())


class CliFetchGdyjTests(unittest.TestCase):
    def test_fetch_gdyj_writes_core_raw_cache_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )

            def fake_call(entry: str, params: list[str]) -> TqlexResponse:
                json_data = {"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0}
                if entry == "tdxf10_gg_comreq" and params == ["jgcg", "002736"]:
                    json_data = {
                        "ErrorCode": 0,
                        "ResultSets": [
                            {
                                "ColDes": [{"Name": "T002"}],
                                "Content": [["2025-03-31"], ["2024-12-31"]],
                            }
                        ],
                        "ResultSetNum": 1,
                    }
                return TqlexResponse(raw_text=json.dumps(json_data), json_data=json_data)

            fake_client.call.side_effect = fake_call
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                with redirect_stdout(stdout):
                    exit_code = main(["fetch-gdyj", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                fake_client.call.call_args_list,
                [
                    call("tdxf10_gg_gdyj", ["002736", "kggd", "", "", "1", "1", "20"]),
                    call("tdxf10_gg_gdyj", ["002736", "gdrs", "", "", "1", "1", "20"]),
                    call(
                        "tdxf10_gg_gdyj",
                        ["002736", "thygdrs", "", "", "1", "1", "20"],
                    ),
                    call("tdxf10_gg_gdyj", ["002736", "ltgd", "", "", "1", "1", "20"]),
                    call(
                        "tdxf10_gg_gdyj",
                        ["002736", "sdgdbgq", "", "", "1", "1", "20"],
                    ),
                    call(
                        "tdxf10_gg_gdyj",
                        ["002736", "sdzqcyr", "", "", "1", "1", "20"],
                    ),
                    call("tdxf10_gg_gdyj", ["002736", "cgbd", "", "", "1", "1", "20"]),
                    call("tdxf10_gg_gdyj", ["002736", "jgcg", "", "", "1", "1", "20"]),
                    call("tdxf10_gg_comreq", ["jgcg", "002736"]),
                    call(
                        "tdxf10_gg_gdyj",
                        ["002736", "jgcgz", "", "2025-03-31", "1", "1", "20"],
                    ),
                    call(
                        "tdxf10_gg_gdyj_jgcgmx",
                        ["002736", "000", "2025-03-31", "99", "1", "1", "30"],
                    ),
                ],
            )
            output = stdout.getvalue()
            self.assertIn("saved gdyj raw JSON", output)
            expected_paths = [
                ("tdxf10_gg_gdyj", "kggd"),
                ("tdxf10_gg_gdyj", "jgcgz"),
                ("tdxf10_gg_comreq", "jgcg"),
                ("tdxf10_gg_gdyj_jgcgmx", "jgcgmx"),
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
                self.assertTrue(data_path.exists())

    def test_fetch_gdyj_rejects_invalid_stock_code(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["fetch-gdyj", "BAD"])

        self.assertEqual(exit_code, 1)
        self.assertIn("stock code must be exactly 6 digits", stderr.getvalue())


class CliFetchAllTests(unittest.TestCase):
    def test_fetch_all_writes_every_raw_cache_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )

            def fake_call(entry: str, params: list[str]) -> TqlexResponse:
                json_data = {"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0}
                if entry == "tdxf10_gg_comreq" and params == ["jgcg", "002736"]:
                    json_data = {
                        "ErrorCode": 0,
                        "ResultSets": [
                            {
                                "ColDes": [{"Name": "T002"}],
                                "Content": [["2025-03-31"], ["2024-12-31"]],
                            }
                        ],
                        "ResultSetNum": 1,
                    }
                return TqlexResponse(raw_text=json.dumps(json_data), json_data=json_data)

            fake_client.call.side_effect = fake_call
            stdout = io.StringIO()

            with (
                patch("zxtp.cli.TqlexClient", return_value=fake_client),
                patch("zxtp.cli.parse_financial_analysis") as parse_financial_analysis,
            ):
                with redirect_stdout(stdout):
                    exit_code = main(["fetch-all", "002736", "--data-root", tmp])

            self.assertEqual(exit_code, 0)
            parse_financial_analysis.assert_called_once_with("002736", Path(tmp))
            fake_client.call.assert_any_call("tdxf10_gg_gsgk", ["0", "002736", ""])
            fake_client.call.assert_any_call("tdxf10_gg_ybpj", ["002736", "tzpjtj"])
            fake_client.call.assert_any_call("tdxf10_gg_cwfx", ["002736", "gptype", ""])
            fake_client.call.assert_any_call("tdxf10_gg_comreq", ["bdsm", "002736"])
            fake_client.call.assert_any_call("tdxf10_gg_cwfx_cbdp", ["002736", "1"])
            fake_client.call.assert_any_call("tdxf10_gg_hyfx", ["tot", "002736", ""])
            fake_client.call.assert_any_call("tdxf10_gg_jyfx", ["002736", "zyyw", ""])
            fake_client.call.assert_any_call("tdxf10_gg_jyfx_jysj", ["002736"])
            fake_client.call.assert_any_call("tdxf10_gg_fhrz", ["002736", "pxmz"])
            fake_client.call.assert_any_call(
                "tdxf10_gg_fhrz_zfhpmx", ["zfpg_bgq", "002736", ""]
            )
            fake_client.call.assert_any_call(
                "tdxf10_gg_gdyj", ["002736", "kggd", "", "", "1", "1", "20"]
            )
            fake_client.call.assert_any_call("tdxf10_gg_comreq", ["jgcg", "002736"])
            fake_client.call.assert_any_call(
                "tdxf10_gg_gdyj_jgcgmx",
                ["002736", "000", "2025-03-31", "99", "1", "1", "30"],
            )
            self.assertEqual(fake_client.call.call_count, 71)

            output = stdout.getvalue()
            self.assertIn("开始下载公司概况 gsgk", output)
            self.assertIn("开始下载研报评级 ybpj", output)
            self.assertIn("开始下载财务分析 cwfx", output)
            self.assertIn("开始下载行业分析 hyfx", output)
            self.assertIn("saved gsgk raw JSON", output)
            self.assertIn("saved ybpj raw JSON", output)
            self.assertIn("saved cwfx raw JSON", output)
            self.assertIn("saved hyfx raw JSON", output)
            assert_output_precedes(
                self,
                output,
                "saving company overview structured data...",
                "saved company overview structured data:",
            )
            assert_output_precedes(
                self,
                output,
                "saving research rating structured data...",
                "saved research rating structured data:",
            )
            assert_output_precedes(
                self,
                output,
                "saving financial analysis structured data...",
                "saved financial analysis structured data:",
            )
            self.assertIn("开始生成 AI Context", output)
            self.assertIn("saved AI context Markdown", output)

            expected_paths = [
                ("tdxf10_gg_gsgk", "gsgk"),
                ("tdxf10_gg_ybpj", "tzpjtj"),
                ("tdxf10_gg_cwfx", "gptype"),
                ("tdxf10_gg_comreq", "bdsm"),
                ("tdxf10_gg_cwfx_cbdp", "cbdp"),
                ("tdxf10_gg_hyfx", "tot"),
                ("tdxf10_gg_jyfx", "zyyw"),
                ("tdxf10_gg_jyfx_jysj", "jysj"),
                ("tdxf10_gg_fhrz", "pxmz"),
                ("tdxf10_gg_fhrz_zfhpmx", "zfpg_bgq"),
                ("tdxf10_gg_gdyj", "kggd"),
                ("tdxf10_gg_gdyj_jgcgmx", "jgcgmx"),
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
                self.assertTrue(data_path.exists())
            self.assertTrue(
                (
                    Path(tmp)
                    / "exports"
                    / "ai_context"
                    / "002736"
                    / "full_context.md"
                ).exists()
            )

    def test_fetch_all_rejects_invalid_stock_code(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["fetch-all", "BAD"])

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
            assert_output_precedes(
                self,
                output,
                "saving research rating structured data...",
                "saved research rating structured data:",
            )


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

            with (
                patch("zxtp.cli.TqlexClient", return_value=fake_client),
                patch("zxtp.cli.parse_financial_analysis") as parse_financial_analysis,
            ):
                exit_code = main(
                    ["ui", "--data-root", tmp],
                    input_func=lambda prompt="": next(inputs),
                    output=stdout,
                )

            self.assertEqual(exit_code, 0)
            parse_financial_analysis.assert_called_once_with("002736", Path(tmp))
            fake_client.call.assert_any_call("tdxf10_gg_cwfx", ["002736", "gptype", ""])
            fake_client.call.assert_any_call("tdxf10_gg_comreq", ["bdsm", "002736"])
            output = stdout.getvalue()
            self.assertIn("cwfx", output)
            self.assertIn("saved cwfx raw JSON", output)
            self.assertIn("saved financial analysis structured data:", output)
            assert_output_precedes(
                self,
                output,
                "saving financial analysis structured data...",
                "saved financial analysis structured data:",
            )


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


class CliUiJyfxTests(unittest.TestCase):
    def test_ui_fetches_jyfx_from_menu_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            inputs = iter(["1", "5", "002736"])
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                exit_code = main(
                    ["ui", "--data-root", tmp],
                    input_func=lambda prompt="": next(inputs),
                    output=stdout,
                )

            self.assertEqual(exit_code, 0)
            fake_client.call.assert_any_call("tdxf10_gg_jyfx", ["002736", "zyyw", ""])
            fake_client.call.assert_any_call("tdxf10_gg_jyfx_jysj", ["002736"])
            output = stdout.getvalue()
            self.assertIn("jyfx", output)
            self.assertIn("saved jyfx raw JSON", output)

    def test_ui_explains_known_jyfx_failure_for_600001(self) -> None:
        fake_client = Mock()
        fake_client.call.side_effect = TqlexError("TQLEX ErrorCode 1005: 数据库执行失败")
        inputs = iter(["1", "5", "600001", "0"])
        stdout = io.StringIO()

        with patch("zxtp.cli.TqlexClient", return_value=fake_client):
            exit_code = main(
                ["ui"],
                input_func=lambda prompt="": next(inputs),
                output=stdout,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(fake_client.call.call_count, 4)
        self.assertTrue(
            all(
                call_args == call("tdxf10_gg_jyfx", ["600001", "zyyw", ""])
                for call_args in fake_client.call.call_args_list
            )
        )
        output = stdout.getvalue()
        self.assertIn("经营分析 jyfx 下载失败", output)
        self.assertIn("重试: tdxf10_gg_jyfx/zyyw 第 1/4 次失败", output)
        self.assertIn("重试: tdxf10_gg_jyfx/zyyw 第 4/4 次失败", output)
        self.assertIn("002736 是正常的", output)
        self.assertIn("600001 是失败的", output)
        self.assertIn("TQLEX ErrorCode 1005", output)


class CliUiFhrzTests(unittest.TestCase):
    def test_ui_fetches_fhrz_from_menu_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )
            fake_client.call.return_value = TqlexResponse(
                raw_text='{"ErrorCode":0,"ResultSets":[],"ResultSetNum":0}',
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )
            inputs = iter(["1", "6", "002736"])
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                exit_code = main(
                    ["ui", "--data-root", tmp],
                    input_func=lambda prompt="": next(inputs),
                    output=stdout,
                )

            self.assertEqual(exit_code, 0)
            fake_client.call.assert_any_call("tdxf10_gg_fhrz", ["002736", "pxmz"])
            fake_client.call.assert_any_call(
                "tdxf10_gg_fhrz_zfhpmx", ["zfpg_bgq", "002736", ""]
            )
            output = stdout.getvalue()
            self.assertIn("fhrz", output)
            self.assertIn("saved fhrz raw JSON", output)


class CliUiGdyjTests(unittest.TestCase):
    def test_ui_fetches_gdyj_from_menu_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )

            def fake_call(entry: str, params: list[str]) -> TqlexResponse:
                json_data = {"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0}
                if entry == "tdxf10_gg_comreq" and params == ["jgcg", "002736"]:
                    json_data = {
                        "ErrorCode": 0,
                        "ResultSets": [
                            {
                                "ColDes": [{"Name": "T002"}],
                                "Content": [["2025-03-31"], ["2024-12-31"]],
                            }
                        ],
                        "ResultSetNum": 1,
                    }
                return TqlexResponse(raw_text=json.dumps(json_data), json_data=json_data)

            fake_client.call.side_effect = fake_call
            inputs = iter(["1", "7", "002736"])
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                exit_code = main(
                    ["ui", "--data-root", tmp],
                    input_func=lambda prompt="": next(inputs),
                    output=stdout,
                )

            self.assertEqual(exit_code, 0)
            fake_client.call.assert_any_call(
                "tdxf10_gg_gdyj", ["002736", "kggd", "", "", "1", "1", "20"]
            )
            fake_client.call.assert_any_call(
                "tdxf10_gg_gdyj_jgcgmx",
                ["002736", "000", "2025-03-31", "99", "1", "1", "30"],
            )
            output = stdout.getvalue()
            self.assertIn("gdyj", output)
            self.assertIn("saved gdyj raw JSON", output)


class CliUiFetchAllTests(unittest.TestCase):
    def test_ui_fetches_all_from_menu_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = Mock()
            fake_client.source_url.side_effect = (
                lambda entry: f"http://example.test/TQLEX?Entry=CWServ.{entry}"
            )

            def fake_call(entry: str, params: list[str]) -> TqlexResponse:
                json_data = {"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0}
                if entry == "tdxf10_gg_comreq" and params == ["jgcg", "002736"]:
                    json_data = {
                        "ErrorCode": 0,
                        "ResultSets": [
                            {
                                "ColDes": [{"Name": "T002"}],
                                "Content": [["2025-03-31"], ["2024-12-31"]],
                            }
                        ],
                        "ResultSetNum": 1,
                    }
                return TqlexResponse(raw_text=json.dumps(json_data), json_data=json_data)

            fake_client.call.side_effect = fake_call
            inputs = iter(["1", "8", "002736"])
            stdout = io.StringIO()

            with patch("zxtp.cli.TqlexClient", return_value=fake_client):
                exit_code = main(
                    ["ui", "--data-root", tmp],
                    input_func=lambda prompt="": next(inputs),
                    output=stdout,
                )

            self.assertEqual(exit_code, 0)
            fake_client.call.assert_any_call("tdxf10_gg_gsgk", ["0", "002736", ""])
            fake_client.call.assert_any_call("tdxf10_gg_ybpj", ["002736", "tzpjtj"])
            fake_client.call.assert_any_call("tdxf10_gg_cwfx", ["002736", "gptype", ""])
            fake_client.call.assert_any_call("tdxf10_gg_hyfx", ["tot", "002736", ""])
            fake_client.call.assert_any_call("tdxf10_gg_jyfx", ["002736", "zyyw", ""])
            fake_client.call.assert_any_call("tdxf10_gg_fhrz", ["002736", "pxmz"])
            fake_client.call.assert_any_call(
                "tdxf10_gg_gdyj", ["002736", "kggd", "", "", "1", "1", "20"]
            )
            fake_client.call.assert_any_call(
                "tdxf10_gg_gdyj_jgcgmx",
                ["002736", "000", "2025-03-31", "99", "1", "1", "30"],
            )
            self.assertEqual(fake_client.call.call_count, 71)
            output = stdout.getvalue()
            self.assertIn("all", output)
            self.assertIn("开始下载公司概况 gsgk", output)
            self.assertIn("开始下载研报评级 ybpj", output)
            self.assertIn("开始下载财务分析 cwfx", output)
            self.assertIn("开始下载行业分析 hyfx", output)
            self.assertIn("saved gsgk raw JSON", output)
            self.assertIn("saved ybpj raw JSON", output)
            self.assertIn("saved cwfx raw JSON", output)
            self.assertIn("saved hyfx raw JSON", output)
            self.assertIn("开始生成 AI Context", output)
            self.assertIn("saved AI context Markdown", output)


class CliUiInputErrorTests(unittest.TestCase):
    def test_ui_shows_hint_and_returns_to_menu_when_stock_code_is_invalid(self) -> None:
        fake_client = Mock()
        inputs = iter(["1", "7", "6000011", "0"])
        stdout = io.StringIO()

        with patch("zxtp.cli.TqlexClient", return_value=fake_client):
            exit_code = main(
                ["ui"],
                input_func=lambda prompt="": next(inputs),
                output=stdout,
            )

        self.assertEqual(exit_code, 0)
        fake_client.call.assert_not_called()
        output = stdout.getvalue()
        self.assertIn("提示: stock code must be exactly 6 digits", output)
        self.assertIn("请选择操作：", output)
        self.assertIn("已退出", output)


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
            assert_output_precedes(
                self,
                output,
                "saving company overview structured data...",
                "saved company overview structured data:",
            )
