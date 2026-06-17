import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

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
