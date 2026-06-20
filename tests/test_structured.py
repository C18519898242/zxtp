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


if __name__ == "__main__":
    unittest.main()
