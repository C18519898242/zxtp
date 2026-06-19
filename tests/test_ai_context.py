import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zxtp.ai_context import generate_full_context
from zxtp.structured import parse_company_overview
from zxtp.tqlex import RawCacheWriter


class AiContextGenerationTests(unittest.TestCase):
    def test_includes_structured_company_overview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            writer = RawCacheWriter(data_root)
            writer.write(
                entry="tdxf10_gg_gsgk",
                params=["0", "002736", ""],
                stock_code="002736",
                module="gsgk",
                source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk",
                json_data={
                    "ErrorCode": 0,
                    "ResultSetNum": 1,
                    "ResultSets": [
                        {
                            "ColDes": [
                                {"Name": "T003"},
                                {"Name": "yjhy"},
                                {"Name": "T017"},
                                {"Name": "cpmc"},
                                {"Name": "T036"},
                                {"Name": "T008"},
                                {"Name": "T030"},
                                {"Name": "ygzs"},
                                {"Name": "T024"},
                                {"Name": "T026"},
                                {"Name": "T009"},
                                {"Name": "T012"},
                                {"Name": "T019"},
                            ],
                            "Content": [
                                [
                                    "Example Securities",
                                    "Finance - Brokerage",
                                    "Wealth management and investment banking",
                                    "Securities brokerage",
                                    "Example Holdings",
                                    "Ada Chair",
                                    "Ben Manager",
                                    "11085",
                                    "0755-82130188",
                                    "ir@example.test",
                                    "Registered address",
                                    "Office address",
                                    "Company profile",
                                ]
                            ],
                        }
                    ],
                },
            )
            parse_company_overview("002736", data_root)

            output_path = generate_full_context("002736", data_root)

            text = output_path.read_text(encoding="utf-8")
            self.assertIn("Example Securities", text)
            self.assertIn("Finance - Brokerage", text)
            self.assertIn("Wealth management and investment banking", text)
            self.assertIn("Securities brokerage", text)
            self.assertIn("Example Holdings", text)
            self.assertIn("Ada Chair", text)
            self.assertIn("Ben Manager", text)
            self.assertIn("11085", text)
            self.assertIn("ir@example.test", text)
            self.assertIn("Company profile", text)
            company_section = text.split("## 2. 公司概况", 1)[1].split(
                "## 3. 财务分析", 1
            )[0]
            self.assertNotIn("暂无结构化摘要", company_section)

    def test_generates_stock_first_markdown_with_stable_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            writer = RawCacheWriter(data_root)
            writer.write(
                entry="tdxf10_gg_gsgk",
                params=["0", "002736", ""],
                stock_code="002736",
                module="gsgk",
                source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk",
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )

            output_path = generate_full_context("002736", data_root)

            self.assertEqual(
                output_path,
                data_root / "exports" / "ai_context" / "002736" / "full_context.md",
            )
            text = output_path.read_text(encoding="utf-8")
            self.assertIn('stock_code: "002736"', text)
            self.assertIn("# 002736 研究上下文", text)
            self.assertIn("## 1. 基本信息", text)
            self.assertIn("## 2. 公司概况", text)
            self.assertIn("## 3. 财务分析", text)
            self.assertIn("## 4. 经营分析", text)
            self.assertIn("## 5. 分红融资", text)
            self.assertIn("## 6. 研报评级", text)
            self.assertIn("## 7. 行业分析", text)
            self.assertIn("## 8. 风险与待验证问题", text)
            self.assertIn("## 9. 数据来源", text)
            self.assertIn("tdxf10_gg_gsgk", text)
            self.assertIn("module=gsgk", text)
            self.assertIn("tdxf10_gg_cwfx", text)
            self.assertIn("tdxf10_gg_hyfx", text)
            self.assertIn("tdxf10_gg_jyfx", text)
            self.assertIn("tdxf10_gg_fhrz", text)
            self.assertIn("tdxf10_gg_gdyj", text)
            self.assertIn("tdxf10_gg_gdyj_jgcgmx", text)
            self.assertIn("缺失", text)


if __name__ == "__main__":
    unittest.main()
