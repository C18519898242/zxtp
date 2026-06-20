import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import zxtp.structured as structured
from zxtp.structured import parse_company_overview
from zxtp.tqlex import RawCacheWriter


class CompanyOverviewStructuredTests(unittest.TestCase):
    def test_creates_empty_company_overviews_table_when_raw_has_no_rows(self) -> None:
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

            database_path = parse_company_overview("002736", data_root)

            with duckdb.connect(str(database_path), read_only=True) as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT count(*) FROM company_overviews"
                    ).fetchone(),
                    (0,),
                )

    def test_parses_company_overview_raw_json_into_duckdb(self) -> None:
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
                                {"Name": "T038"},
                                {"Name": "T006"},
                                {"Name": "url"},
                                {"Name": "yjhy"},
                                {"Name": "shxydm"},
                                {"Name": "T017"},
                                {"Name": "cpmc"},
                                {"Name": "T036"},
                                {"Name": "T008"},
                                {"Name": "T030"},
                                {"Name": "T023"},
                                {"Name": "dsz"},
                                {"Name": "ygzs"},
                                {"Name": "T024"},
                                {"Name": "T026"},
                                {"Name": "T028"},
                                {"Name": "T029"},
                                {"Name": "T009"},
                                {"Name": "T012"},
                                {"Name": "T019"},
                                {"Name": "T018"},
                            ],
                            "Content": [
                                [
                                    "国信证券股份有限公司",
                                    "深圳板块",
                                    "Guosen Securities Co., Ltd.",
                                    "https://www.guosen.com.cn",
                                    "非银金融-证券",
                                    "914403001922784445",
                                    "财富管理与投资银行",
                                    "证券经纪",
                                    "深圳市投资控股有限公司",
                                    "张纳沙",
                                    "邓舸",
                                    "张纳沙",
                                    "廖锐敏",
                                    "11085",
                                    "0755-82130188",
                                    "ir@guosen.com.cn",
                                    "容诚会计师事务所",
                                    "竞天公诚律师事务所",
                                    "深圳市罗湖区",
                                    "深圳市福田区",
                                    "公司简介",
                                    "证券经纪业务",
                                ]
                            ],
                        }
                    ],
                },
            )

            database_path = parse_company_overview("002736", data_root)

            self.assertEqual(database_path, data_root / "warehouse" / "research.duckdb")
            with duckdb.connect(str(database_path), read_only=True) as connection:
                row = connection.execute(
                    """
                    SELECT
                        stock_code,
                        name,
                        industry,
                        business_summary,
                        employee_count,
                        source_entry,
                        source_module
                    FROM company_overviews
                    """
                ).fetchone()

            self.assertEqual(
                row,
                (
                    "002736",
                    "国信证券股份有限公司",
                    "非银金融-证券",
                    "财富管理与投资银行",
                    11085,
                    "tdxf10_gg_gsgk",
                    "gsgk",
                ),
            )


class ResearchRatingStructuredTests(unittest.TestCase):
    def test_derives_yearly_earnings_forecast_metrics(self) -> None:
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
                            "ColDes": [{"Name": "nyear"}],
                            "Content": [["2026"]],
                        },
                        {
                            "ColDes": [
                                {"Name": "T036"},
                                {"Name": "T037"},
                                {"Name": "T038"},
                                {"Name": "T027"},
                                {"Name": "T028"},
                                {"Name": "T029"},
                                {"Name": "T024"},
                                {"Name": "T025"},
                                {"Name": "T026"},
                                {"Name": "T033"},
                                {"Name": "T034"},
                                {"Name": "T035"},
                                {"Name": "T021"},
                                {"Name": "T022"},
                                {"Name": "T023"},
                                {"Name": "T030"},
                                {"Name": "T031"},
                                {"Name": "T032"},
                            ],
                            "Content": [
                                [
                                    "1.135",
                                    "1.258",
                                    "1.353",
                                    "12.04",
                                    "13.01",
                                    "14.05",
                                    "9.80",
                                    "10.25",
                                    "10.32",
                                    "1242640",
                                    "1385040",
                                    "1502060",
                                    "2639700",
                                    "2894380",
                                    "3112040",
                                    "1448200",
                                    "1613500",
                                    "1749660",
                                ]
                            ],
                        },
                        {
                            "ColDes": [
                                {"Name": "T002"},
                                {"Name": "T055"},
                                {"Name": "T059"},
                                {"Name": "T064"},
                                {"Name": "T018"},
                                {"Name": "T003"},
                                {"Name": "T012"},
                                {"Name": "T118"},
                            ],
                            "Content": [
                                [
                                    "2025",
                                    "1.0811",
                                    "9.5485",
                                    "8.43",
                                    "1107276.10",
                                    "2414329.66",
                                    "1299963.88",
                                    "34.76",
                                ]
                            ],
                        },
                    ],
                },
            )

            database_path = structured.parse_research_ratings("002736", data_root)

            with duckdb.connect(str(database_path), read_only=True) as connection:
                actual = connection.execute(
                    """
                    SELECT period_type, earnings_per_share, net_profit_parent_wan,
                           operating_revenue_wan, operating_profit_wan
                    FROM earnings_forecast_yearly_metrics
                    WHERE fiscal_year = 2025
                    """
                ).fetchone()
                forecast = connection.execute(
                    """
                    SELECT period_type, earnings_per_share, net_profit_growth_pct
                    FROM earnings_forecast_yearly_metrics
                    WHERE fiscal_year = 2026
                    """
                ).fetchone()

            self.assertEqual(
                actual,
                ("actual", 1.0811, 1107276.10, 2414329.66, 1299963.88),
            )
            self.assertEqual(forecast[:2], ("forecast", 1.135))
            self.assertAlmostEqual(forecast[2], 12.22, places=2)

    def test_parses_yzyq_result_sets_into_separate_raw_tables(self) -> None:
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
                            "ColDes": [
                                {"Name": "defdate"},
                                {"Name": "T003"},
                            ],
                            "Content": [["20261231", "20260527"]],
                        },
                        {
                            "ColDes": [
                                {"Name": "T026"},
                                {"Name": "T030"},
                                {"Name": "T005"},
                            ],
                            "Content": [["0", "20260522", "1.180"]],
                        },
                        {
                            "ColDes": [
                                {"Name": "EndDate"},
                                {"Name": "AdjustingFactor"},
                                {"Name": "AdjustingConst"},
                            ],
                            "Content": [["20260622", "1", "3.54"]],
                        },
                        {
                            "ColDes": [
                                {"Name": "TradingDay"},
                                {"Name": "ClosePrice"},
                            ],
                            "Content": [
                                ["20250620", "11.040"],
                                ["20250619", "10.900"],
                            ],
                        },
                    ],
                },
            )

            database_path = structured.parse_research_ratings("002736", data_root)

            with duckdb.connect(str(database_path), read_only=True) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT table_name FROM information_schema.tables"
                    ).fetchall()
                }
                self.assertTrue(
                    {
                        "performance_expectations",
                        "performance_expectation_estimates",
                        "adjustment_factors",
                        "daily_close_prices",
                    }.issubset(tables)
                )
                expectation = connection.execute(
                    "SELECT raw_defdate, raw_t003 FROM performance_expectations"
                ).fetchone()
                estimate = connection.execute(
                    "SELECT raw_t026, raw_t030, raw_t005 "
                    "FROM performance_expectation_estimates"
                ).fetchone()
                factor = connection.execute(
                    "SELECT end_date, raw_adjusting_factor, raw_adjusting_const "
                    "FROM adjustment_factors"
                ).fetchone()
                prices = connection.execute(
                    "SELECT trading_day, raw_close_price FROM daily_close_prices "
                    "ORDER BY trading_day DESC"
                ).fetchall()

            self.assertEqual(expectation, ("20261231", "20260527"))
            self.assertEqual(estimate, ("0", "20260522", "1.180"))
            self.assertEqual(factor, ("20260622", "1", "3.54"))
            self.assertEqual(
                prices,
                [("20250620", "11.040"), ("20250619", "10.900")],
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
                        {"ColDes": [], "Content": []},
                        {"ColDes": [], "Content": []},
                        {"ColDes": [], "Content": []},
                        {
                            "ColDes": [
                                {"Name": "TradingDay"},
                                {"Name": "ClosePrice"},
                            ],
                            "Content": [["20250623", "11.200"]],
                        },
                    ],
                },
            )
            structured.parse_research_ratings("002736", data_root)

            with duckdb.connect(str(database_path), read_only=True) as connection:
                replacement_prices = connection.execute(
                    "SELECT trading_day, raw_close_price FROM daily_close_prices"
                ).fetchall()
                empty_counts = connection.execute(
                    """
                    SELECT
                        (SELECT count(*) FROM performance_expectations),
                        (SELECT count(*) FROM performance_expectation_estimates),
                        (SELECT count(*) FROM adjustment_factors)
                    """
                ).fetchone()

            self.assertEqual(replacement_prices, [("20250623", "11.200")])
            self.assertEqual(empty_counts, (0, 0, 0))

    def test_parses_earnings_forecast_result_sets_into_separate_raw_tables(self) -> None:
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
                            "ColDes": [
                                {"Name": "T036"},
                                {"Name": "T037"},
                                {"Name": "T038"},
                            ],
                            "Content": [["1.135", "1.258", "1.353"]],
                        },
                        {
                            "ColDes": [
                                {"Name": "T002"},
                                {"Name": "T055"},
                                {"Name": "T059"},
                            ],
                            "Content": [["2023", "0.6686", "8.3704"]],
                        },
                        {
                            "ColDes": [
                                {"Name": "rq"},
                                {"Name": "jg"},
                                {"Name": "T019"},
                            ],
                            "Content": [["20231231", "8209014.6879580", "6427294103.14"]],
                        },
                        {
                            "ColDes": [
                                {"Name": "rq"},
                                {"Name": "t023"},
                                {"Name": "T003"},
                            ],
                            "Content": [["20260620", "4", "Example Securities"]],
                        },
                    ],
                },
            )

            database_path = structured.parse_research_ratings("002736", data_root)

            with duckdb.connect(str(database_path), read_only=True) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT table_name FROM information_schema.tables"
                    ).fetchall()
                }
                self.assertIn("earnings_forecast_windows", tables)
                self.assertIn("earnings_forecast_consensuses", tables)
                self.assertIn("earnings_forecast_history", tables)
                self.assertIn("earnings_forecast_snapshots", tables)
                self.assertIn("earnings_forecast_metadata", tables)

                window = connection.execute(
                    "SELECT forecast_year, raw_flag FROM earnings_forecast_windows"
                ).fetchone()
                consensus = connection.execute(
                    "SELECT raw_t036, raw_t037, raw_t038 "
                    "FROM earnings_forecast_consensuses"
                ).fetchone()
                history = connection.execute(
                    "SELECT fiscal_year, raw_t055, raw_t059 "
                    "FROM earnings_forecast_history"
                ).fetchone()
                snapshot = connection.execute(
                    "SELECT snapshot_date, raw_jg, raw_t019 "
                    "FROM earnings_forecast_snapshots"
                ).fetchone()
                metadata = connection.execute(
                    "SELECT metadata_date, raw_t023, company_name "
                    "FROM earnings_forecast_metadata"
                ).fetchone()

            self.assertEqual(window, ("2026", "0"))
            self.assertEqual(consensus, ("1.135", "1.258", "1.353"))
            self.assertEqual(history, ("2023", "0.6686", "8.3704"))
            self.assertEqual(
                snapshot,
                ("20231231", "8209014.6879580", "6427294103.14"),
            )
            self.assertEqual(metadata, ("20260620", "4", "Example Securities"))

    def test_parses_rating_summary_and_reports_into_duckdb(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            self.assertTrue(hasattr(structured, "parse_research_ratings"))
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
                                    "sample",
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
                                    "report-1",
                                    "20260527",
                                    "Buy",
                                    "Example Securities",
                                    "First report analysis",
                                    "5",
                                    "First report title",
                                ],
                                [
                                    "report-2",
                                    "20260526",
                                    "Hold",
                                    "Another Securities",
                                    "Second report analysis",
                                    "3",
                                    "Second report title",
                                ],
                            ],
                        }
                    ],
                },
            )

            database_path = structured.parse_research_ratings("002736", data_root)

            self.assertEqual(database_path, data_root / "warehouse" / "research.duckdb")
            with duckdb.connect(str(database_path), read_only=True) as connection:
                summary = connection.execute(
                    """
                    SELECT
                        stock_code,
                        rating_date,
                        raw_sj,
                        raw_mr,
                        rating_value,
                        source_module
                    FROM research_rating_summaries
                    """
                ).fetchone()
                reports = connection.execute(
                    """
                    SELECT report_id, report_date, rating, institution, title
                    FROM research_reports
                    ORDER BY report_id
                    """
                ).fetchall()

            self.assertEqual(summary, ("002736", "20260527", 30, 20, 4.5, "tzpjtj"))
            self.assertEqual(
                reports,
                [
                    (
                        "report-1",
                        "20260527",
                        "Buy",
                        "Example Securities",
                        "First report title",
                    ),
                    (
                        "report-2",
                        "20260526",
                        "Hold",
                        "Another Securities",
                        "Second report title",
                    ),
                ],
            )


class FinancialAnalysisStructuredTests(unittest.TestCase):
    def write_financial_raw(
        self,
        data_root: Path,
        module: str,
        columns: list[str],
        rows: list[list[str | None]],
    ) -> None:
        RawCacheWriter(data_root).write(
            entry="tdxf10_gg_cwfx",
            params=["002736", module, ""],
            stock_code="002736",
            module=module,
            source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_cwfx",
            json_data={
                "ErrorCode": 0,
                "ResultSets": [
                    {
                        "ColDes": [{"Name": column} for column in columns],
                        "Content": rows,
                    }
                ],
            },
        )

    def write_core_financial_raw(self, data_root: Path, eps: str = "1.000") -> None:
        self.write_financial_raw(
            data_root,
            "zyzb",
            ["rq", "mgsy", "kfjlr", "mgxjll", "lrze", "jyr", "jzzsyl", "xsmll", "yysrtb", "jlrtbzzl"],
            [
                ["2025-12-31", eps, "900000000", "0.500", "1200000000", "1000000000", "10.5", "30.0", "5.0", "8.0"],
                ["2026-03-31", "0.250", "250000000", "0.125", "300000000", "250000000", "2.5", "28.0", "4.0", "6.0"],
            ],
        )
        for module, columns in (
            ("lyb", ["rq", "T008"]),
            ("zcfzb", ["rq", "T008"]),
            ("xjllb", ["rq", "T013"]),
        ):
            self.write_financial_raw(
                data_root,
                module,
                columns,
                [["2025-12-31", "1200000000"], ["2026-03-31", "300000000"]],
            )

    def test_parses_core_financial_raw_into_duckdb(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            self.write_core_financial_raw(data_root)

            database_path = structured.parse_financial_analysis("002736", data_root)

            self.assertEqual(database_path, data_root / "warehouse" / "financial.duckdb")
            with duckdb.connect(str(database_path), read_only=True) as connection:
                tables = {
                    row[0]
                    for row in connection.execute("SHOW TABLES").fetchall()
                }
                key_metric = connection.execute(
                    """
                    SELECT report_date, metric_name, metric_value, metric_unit, raw_field_name
                    FROM financial_key_metrics
                    WHERE metric_name = 'return_on_equity_pct'
                    """
                ).fetchone()
                income_item = connection.execute(
                    """
                    SELECT report_date, raw_field_name, amount
                    FROM financial_income_statements
                    WHERE report_date = '2025-12-31' AND raw_field_name = 'T008'
                    """
                ).fetchone()
                periods = connection.execute(
                    """
                    SELECT report_date, report_year, report_type
                    FROM financial_key_metrics
                    WHERE metric_name = 'basic_earnings_per_share'
                    ORDER BY report_date
                    """
                ).fetchall()

            self.assertEqual(
                tables,
                {
                    "financial_balance_sheets",
                    "financial_cash_flows",
                    "financial_income_statements",
                    "financial_key_metrics",
                },
            )
            self.assertEqual(
                key_metric,
                ("2025-12-31", "return_on_equity_pct", 10.5, "%", "jzzsyl"),
            )
            self.assertEqual(income_item, ("2025-12-31", "T008", 1200000000.0))
            self.assertEqual(
                periods,
                [("2025-12-31", 2025, "annual"), ("2026-03-31", 2026, "q1")],
            )

    def test_replaces_financial_rows_for_the_same_stock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            self.write_core_financial_raw(data_root, eps="1.000")
            structured.parse_financial_analysis("002736", data_root)
            self.write_core_financial_raw(data_root, eps="2.000")

            database_path = structured.parse_financial_analysis("002736", data_root)

            with duckdb.connect(str(database_path), read_only=True) as connection:
                rows = connection.execute(
                    """
                    SELECT metric_value
                    FROM financial_key_metrics
                    WHERE report_date = '2025-12-31'
                      AND metric_name = 'basic_earnings_per_share'
                    """
                ).fetchall()
            self.assertEqual(rows, [(2.0,)])

    def test_creates_empty_tables_when_cwfx_raw_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)

            database_path = structured.parse_financial_analysis("002736", data_root)

            with duckdb.connect(str(database_path), read_only=True) as connection:
                counts = connection.execute(
                    """
                    SELECT
                        (SELECT count(*) FROM financial_income_statements),
                        (SELECT count(*) FROM financial_balance_sheets),
                        (SELECT count(*) FROM financial_cash_flows),
                        (SELECT count(*) FROM financial_key_metrics)
                    """
                ).fetchone()
            self.assertEqual(counts, (0, 0, 0, 0))

    def test_skips_invalid_snapshot_and_preserves_other_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            self.write_core_financial_raw(data_root)
            RawCacheWriter(data_root).paths(
                entry="tdxf10_gg_cwfx", stock_code="002736", module="lyb"
            ).data_path.write_text("{not-json", encoding="utf-8")

            database_path = structured.parse_financial_analysis("002736", data_root)

            with duckdb.connect(str(database_path), read_only=True) as connection:
                counts = connection.execute(
                    """
                    SELECT
                        (SELECT count(*) FROM financial_income_statements),
                        (SELECT count(*) FROM financial_balance_sheets),
                        (SELECT count(*) FROM financial_cash_flows),
                        (SELECT count(*) FROM financial_key_metrics)
                    """
                ).fetchone()
            self.assertEqual(counts[0], 0)
            self.assertGreater(counts[1], 0)
            self.assertGreater(counts[2], 0)
            self.assertGreater(counts[3], 0)


if __name__ == "__main__":
    unittest.main()
