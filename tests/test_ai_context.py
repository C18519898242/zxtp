import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zxtp.ai_context import generate_full_context
from zxtp.structured import (
    parse_company_overview,
    parse_financial_analysis,
    parse_research_ratings,
)
from zxtp.tqlex import RawCacheWriter


class AiContextGenerationTests(unittest.TestCase):
    def write_financial_context_raw(self, data_root: Path) -> None:
        writer = RawCacheWriter(data_root)
        periods = [
            ("2022-12-31", "1.000", "1000000000", "900000000", "9.0"),
            ("2023-12-31", "1.100", "1100000000", "1000000000", "10.0"),
            ("2024-12-31", "1.200", "1200000000", "1100000000", "10.25"),
            ("2025-12-31", "1.300", "1300000000", "1200000000", "10.50"),
            ("2026-03-31", "0.350", "350000000", "300000000", "2.75"),
        ]
        writer.write(
            entry="tdxf10_gg_cwfx",
            params=["002736", "zyzb", ""],
            stock_code="002736",
            module="zyzb",
            source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_cwfx",
            json_data={
                "ErrorCode": 0,
                "ResultSets": [
                    {
                        "ColDes": [
                            {"Name": name}
                            for name in (
                                "rq", "mgsy", "mgxjll", "lrze", "jyr", "jzzsyl",
                                "xsmll", "yysrtb", "jlrtbzzl",
                            )
                        ],
                        "Content": [
                            [date, eps, "0.500", total_profit, net_profit, roe, "30.0", "5.0", "8.0"]
                            for date, eps, total_profit, net_profit, roe in periods
                        ],
                    }
                ],
            },
        )
        writer.write(
            entry="tdxf10_gg_cwfx",
            params=["002736", "zcfzb", ""],
            stock_code="002736",
            module="zcfzb",
            source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_cwfx",
            json_data={
                "ErrorCode": 0,
                "ResultSets": [
                    {
                        "ColDes": [
                            {"Name": name} for name in ("rq", "T039", "T062", "T071")
                        ],
                        "Content": [
                            ["2022-12-31", "25000000000", "15000000000", "10000000000"],
                            ["2023-12-31", "30000000000", "18000000000", "12000000000"],
                            ["2024-12-31", "40000000000", "26000000000", "14000000000"],
                            ["2025-12-31", "50000000000", "35000000000", "15000000000"],
                            ["2026-03-31", "55000000000", "36000000000", "19000000000"],
                        ],
                    }
                ],
            },
        )
        for module in ("lyb", "xjllb"):
            writer.write(
                entry="tdxf10_gg_cwfx",
                params=["002736", module, ""],
                stock_code="002736",
                module=module,
                source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_cwfx",
                json_data={"ErrorCode": 0, "ResultSets": []},
            )

    def test_renders_yearly_earnings_forecast_metrics(self) -> None:
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
                        {"ColDes": [{"Name": "nyear"}], "Content": [["2026"]]},
                        {
                            "ColDes": [
                                {"Name": "T036"}, {"Name": "T037"}, {"Name": "T038"},
                                {"Name": "T033"}, {"Name": "T034"}, {"Name": "T035"},
                            ],
                            "Content": [["1.135", "1.258", "1.353", "1242640", "1385040", "1502060"]],
                        },
                        {
                            "ColDes": [
                                {"Name": "T002"}, {"Name": "T055"}, {"Name": "T018"}, {"Name": "T118"},
                            ],
                            "Content": [
                                ["2023", "0.669", "642729.41", "5.57"],
                                ["2024", "0.855", "821685.32", "27.84"],
                                ["2025", "1.081", "1107276.10", "34.76"],
                            ],
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
            self.assertIn("#### 年度指标", research_section)
            self.assertIn(
                "| 指标 | 2023 实际 | 2024 实际 | 2025 实际 | 2026 预测 | 2027 预测 | 2028 预测 |",
                research_section,
            )
            self.assertIn(
                "| 每股收益（元） | 0.669 | 0.855 | 1.081 | 1.135 | 1.258 | 1.353 |",
                research_section,
            )
            self.assertIn(
                "| 归母净利润（亿元） | 64.27 | 82.17 | 110.73 | 124.26 | 138.50 | 150.21 |",
                research_section,
            )
            self.assertIn(
                "| 归母净利润增长率（%） | 5.57 | 27.84 | 34.76 | 12.22 | 11.46 | 8.45 |",
                research_section,
            )
            self.assertNotIn("市盈率", research_section)

    def test_keeps_rating_content_when_stage_four_tables_are_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            database_path = data_root / "warehouse" / "research.duckdb"
            database_path.parent.mkdir(parents=True)
            with duckdb.connect(str(database_path)) as connection:
                connection.execute(
                    """
                    CREATE TABLE research_rating_summaries (
                        stock_code VARCHAR,
                        rating_date VARCHAR,
                        rating_value DOUBLE,
                        raw_sj BIGINT,
                        raw_zj BIGINT,
                        raw_mr BIGINT,
                        raw_zc BIGINT,
                        raw_zx BIGINT,
                        raw_jc BIGINT,
                        raw_mc BIGINT
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO research_rating_summaries VALUES
                    ('002736', '20260527', 4.5, 30, 1, 1, 0, 0, 0, 0)
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE research_reports (
                        stock_code VARCHAR,
                        report_id VARCHAR,
                        report_date VARCHAR,
                        institution VARCHAR,
                        rating VARCHAR,
                        title VARCHAR
                    )
                    """
                )

            output_path = generate_full_context("002736", data_root)

            text = output_path.read_text(encoding="utf-8")
            research_section = text.split("## 6. 研报评级", 1)[1].split(
                "## 7. 行业分析", 1
            )[0]
            self.assertIn("20260527", research_section)
            self.assertNotIn("业绩预期与价格（原始结构化）", research_section)

    def test_generates_ai_context_when_duckdb_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            database_path = data_root / "warehouse" / "research.duckdb"
            database_path.parent.mkdir(parents=True)
            database_path.touch()

            with patch(
                "zxtp.ai_context.duckdb.connect",
                side_effect=duckdb.IOException("database is locked"),
            ):
                output_path = generate_full_context("002736", data_root)

            text = output_path.read_text(encoding="utf-8")
            self.assertIn("结构化研报评级暂不可读取", text)
            self.assertIn("DBeaver", text)

    def test_includes_performance_expectation_and_price_raw_metadata(self) -> None:
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
                params=["002736", "yzyq"],
                stock_code="002736",
                module="yzyq",
                source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_ybpj",
                json_data={
                    "ErrorCode": 0,
                    "ResultSets": [
                        {
                            "ColDes": [{"Name": "defdate"}],
                            "Content": [["20261231"]],
                        },
                        {
                            "ColDes": [{"Name": "T026"}],
                            "Content": [["0"]],
                        },
                        {
                            "ColDes": [{"Name": "EndDate"}],
                            "Content": [["20260622"]],
                        },
                        {
                            "ColDes": [
                                {"Name": "TradingDay"},
                                {"Name": "ClosePrice"},
                            ],
                            "Content": [["20250620", "11.040"]],
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
            self.assertIn("### 业绩预期与价格（原始结构化）", research_section)
            self.assertIn("预期原始日期（defdate）：20261231", research_section)
            self.assertIn("最近交易日：20250620", research_section)
            self.assertIn("原始收盘价：11.040", research_section)
            self.assertIn("字段口径尚待确认", research_section)

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


    def test_renders_financial_context_for_recent_annuals_and_latest_period(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            self.write_financial_context_raw(data_root)
            parse_financial_analysis("002736", data_root)

            text = generate_full_context("002736", data_root).read_text(encoding="utf-8")
            financial_section = text.split("## 3. 财务分析", 1)[1].split(
                "## 4. 经营分析", 1
            )[0]

            self.assertIn("### 报告期说明", financial_section)
            self.assertIn("2023 年报", financial_section)
            self.assertIn("2024 年报", financial_section)
            self.assertIn("2025 年报", financial_section)
            self.assertIn("2026-03-31", financial_section)
            self.assertNotIn("2022 年报", financial_section)
            self.assertIn("净资产收益率（%）", financial_section)
            self.assertIn("10.50", financial_section)
            self.assertIn("每股经营现金流（元）", financial_section)
            self.assertIn("### 资产与负债", financial_section)
            self.assertIn(
                "| 资产总计（亿元） | 300.00 | 400.00 | 500.00 | 550.00 |",
                financial_section,
            )
            self.assertIn(
                "| 负债合计（亿元） | 180.00 | 260.00 | 350.00 | 360.00 |",
                financial_section,
            )
            self.assertIn(
                "| 所有者权益合计（亿元） | 120.00 | 140.00 | 150.00 | 190.00 |",
                financial_section,
            )
            self.assertIn(
                "| 资产负债率（%） | 60.00 | 65.00 | 70.00 | 65.45 |",
                financial_section,
            )
            self.assertNotIn("字段业务口径待确认", financial_section)

    def test_balance_sheet_table_uses_dash_for_missing_or_zero_asset_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            self.write_financial_context_raw(data_root)
            RawCacheWriter(data_root).write(
                entry="tdxf10_gg_cwfx",
                params=["002736", "zcfzb", ""],
                stock_code="002736",
                module="zcfzb",
                source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_cwfx",
                json_data={
                    "ErrorCode": 0,
                    "ResultSets": [
                        {
                            "ColDes": [
                                {"Name": name}
                                for name in ("rq", "T039", "T062", "T071")
                            ],
                            "Content": [
                                ["2023-12-31", None, "100000000", "50000000"],
                                ["2024-12-31", "100000000", None, "60000000"],
                                ["2025-12-31", "0", "100000000", "50000000"],
                                ["2026-03-31", "200000000", None, "80000000"],
                            ],
                        }
                    ],
                },
            )
            parse_financial_analysis("002736", data_root)

            text = generate_full_context("002736", data_root).read_text(encoding="utf-8")
            financial_section = text.split("## 3. 财务分析", 1)[1].split(
                "## 4. 经营分析", 1
            )[0]

            self.assertIn(
                "| 资产总计（亿元） | — | 1.00 | 0.00 | 2.00 |",
                financial_section,
            )
            self.assertIn(
                "| 资产负债率（%） | — | — | — | — |",
                financial_section,
            )

    def test_financial_context_degrades_when_database_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)

            text = generate_full_context("002736", data_root).read_text(encoding="utf-8")

            self.assertIn("暂无结构化财务分析", text)
            self.assertIn("tdxf10_gg_cwfx", text)

    def test_financial_context_degrades_when_database_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            database_path = data_root / "warehouse" / "financial.duckdb"
            database_path.parent.mkdir(parents=True)
            database_path.touch()

            with patch(
                "zxtp.ai_context.duckdb.connect",
                side_effect=duckdb.IOException("database is locked"),
            ):
                text = generate_full_context("002736", data_root).read_text(
                    encoding="utf-8"
                )

            self.assertIn("结构化财务分析暂不可读取", text)
            self.assertIn("tdxf10_gg_cwfx", text)


if __name__ == "__main__":
    unittest.main()
