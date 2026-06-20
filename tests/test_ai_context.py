import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zxtp.ai_context import generate_full_context
from zxtp.structured import parse_company_overview, parse_research_ratings
from zxtp.tqlex import RawCacheWriter


class AiContextGenerationTests(unittest.TestCase):
    def test_includes_earnings_forecast_raw_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            writer = RawCacheWriter(data_root)
            for module in ("tzpjtj", "ycpjyjbg"):
                writer.write(
                    entry="tdxf10_gg_ybpj",
                    params=["002736", module],
                    stock_code="002736",
                    module=module,
                    source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_ybpj",
                    json_data={"ErrorCode": 0, "ResultSets": []},
                )
            writer.write(
                entry="tdxf10_gg_ybpj",
                params=["002736", "ylyctj"],
                stock_code="002736",
                module="ylyctj",
                source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_ybpj",
                json_data={
                    "ErrorCode": 0,
                    "ResultSets": [
                        {
                            "ColDes": [{"Name": "nyear"}, {"Name": "flag"}],
                            "Content": [["2026", "0"]],
                        },
                        {
                            "ColDes": [{"Name": "T036"}],
                            "Content": [["1.135"]],
                        },
                        {
                            "ColDes": [{"Name": "T002"}],
                            "Content": [["2023"]],
                        },
                        {
                            "ColDes": [{"Name": "rq"}],
                            "Content": [["20231231"]],
                        },
                        {
                            "ColDes": [{"Name": "rq"}, {"Name": "T003"}],
                            "Content": [["20260620", "Example Securities"]],
                        },
                    ],
                },
            )
            parse_research_ratings("002736", data_root)

            output_path = generate_full_context("002736", data_root)

            text = output_path.read_text(encoding="utf-8")
            research_section = text.split("## 6. 研报评级", 1)[1].split(
                "## 7. 行业分析", 1
            )[0]
            self.assertIn("预测起始年度：2026", research_section)
            self.assertIn("源数据日期：20260620", research_section)
            self.assertIn("原始预测汇总记录：1", research_section)
            self.assertIn("原始历史记录：1", research_section)
            self.assertIn("原始快照记录：1", research_section)

    def test_includes_structured_research_ratings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            writer = RawCacheWriter(data_root)
            writer.write(
                entry="tdxf10_gg_ybpj",
                params=["002736", "tzpjtj"],
                stock_code="002736",
                module="tzpjtj",
                source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_ybpj",
                json_data={
                    "ErrorCode": 0,
                    "ResultSets": [
                        {
                            "ColDes": [
                                {"Name": "T016"},
                                {"Name": "sj"},
                                {"Name": "zj"},
                                {"Name": "mr"},
                                {"Name": "zc"},
                                {"Name": "zx"},
                                {"Name": "jc"},
                                {"Name": "mc"},
                                {"Name": "pj"},
                                {"Name": "T006"},
                            ],
                            "Content": [
                                [
                                    "20260527",
                                    "30",
                                    "1",
                                    "20",
                                    "4",
                                    "3",
                                    "1",
                                    "1",
                                    "4.50",
                                    None,
                                ]
                            ],
                        }
                    ],
                },
            )
            writer.write(
                entry="tdxf10_gg_ybpj",
                params=["002736", "ycpjyjbg"],
                stock_code="002736",
                module="ycpjyjbg",
                source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_ybpj",
                json_data={
                    "ErrorCode": 0,
                    "ResultSets": [
                        {
                            "ColDes": [
                                {"Name": "T011"},
                                {"Name": "sj"},
                                {"Name": "pj"},
                                {"Name": "jg"},
                                {"Name": "ytxt"},
                                {"Name": "T004"},
                                {"Name": "T039"},
                            ],
                            "Content": [
                                [
                                    "report-new",
                                    "20260527",
                                    "Buy",
                                    "Example Securities",
                                    "New report analysis",
                                    "5",
                                    "Newest report title",
                                ],
                                [
                                    "report-old",
                                    "20260520",
                                    "Hold",
                                    "Another Securities",
                                    "Old report analysis",
                                    "3",
                                    "Older report title",
                                ],
                            ],
                        }
                    ],
                },
            )
            parse_research_ratings("002736", data_root)

            output_path = generate_full_context("002736", data_root)

            text = output_path.read_text(encoding="utf-8")
            research_section = text.split("## 6. 研报评级", 1)[1].split(
                "## 7. 行业分析", 1
            )[0]
            self.assertIn("20260527", research_section)
            self.assertIn("30", research_section)
            self.assertIn("原始字段：raw_sj=30", research_section)
            self.assertIn("Newest report title", research_section)
            self.assertIn("Example Securities", research_section)
            self.assertIn("Buy", research_section)
            self.assertLess(
                research_section.index("Newest report title"),
                research_section.index("Older report title"),
            )
            self.assertNotIn("暂无结构化摘要", research_section)

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
