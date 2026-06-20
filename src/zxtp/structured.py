from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from .tqlex import RawCacheWriter, TqlexError, now_shanghai_iso, validate_stock_code


COMPANY_OVERVIEW_ENTRY = "tdxf10_gg_gsgk"
COMPANY_OVERVIEW_MODULE = "gsgk"
RESEARCH_RATING_ENTRY = "tdxf10_gg_ybpj"
RESEARCH_RATING_SUMMARY_MODULE = "tzpjtj"
RESEARCH_REPORT_MODULE = "ycpjyjbg"
EARNINGS_FORECAST_MODULE = "ylyctj"

COMPANY_OVERVIEW_FIELDS = {
    "name": "T003",
    "board": "T038",
    "english_name": "T006",
    "website": "url",
    "industry": "yjhy",
    "social_credit_code": "shxydm",
    "business_summary": "T017",
    "products": "cpmc",
    "controlling_shareholder": "T036",
    "chairman": "T008",
    "general_manager": "T030",
    "legal_representative": "T023",
    "board_secretary": "dsz",
    "employee_count": "ygzs",
    "phone": "T024",
    "email": "T026",
    "accounting_firm": "T028",
    "law_firm": "T029",
    "registered_address": "T009",
    "office_address": "T012",
    "company_profile": "T019",
    "business_scope": "T018",
}

RESEARCH_RATING_SUMMARY_FIELDS = {
    "rating_date": "T016",
    "raw_sj": "sj",
    "raw_zj": "zj",
    "raw_mr": "mr",
    "raw_zc": "zc",
    "raw_zx": "zx",
    "raw_jc": "jc",
    "raw_mc": "mc",
    "rating_value": "pj",
    "raw_t006": "T006",
}

RESEARCH_REPORT_FIELDS = {
    "report_id": "T011",
    "report_date": "sj",
    "rating": "pj",
    "institution": "jg",
    "analysis_text": "ytxt",
    "rating_score": "T004",
    "title": "T039",
}

EARNINGS_FORECAST_WINDOW_FIELDS = {
    "forecast_year": "nyear",
    "raw_flag": "flag",
}

EARNINGS_FORECAST_CONSENSUS_FIELDS = {
    f"raw_{field.lower()}": field
    for field in (
        "T036",
        "T037",
        "T038",
        "T027",
        "T028",
        "T029",
        "T024",
        "T025",
        "T026",
        "T033",
        "T034",
        "T035",
        "T021",
        "T022",
        "T023",
        "T030",
        "T031",
        "T032",
    )
}

EARNINGS_FORECAST_HISTORY_FIELDS = {
    "fiscal_year": "T002",
    "raw_t055": "T055",
    "raw_t059": "T059",
    "raw_t064": "T064",
    "raw_t018": "T018",
    "raw_t003": "T003",
    "raw_t012": "T012",
    "raw_t118": "T118",
}

EARNINGS_FORECAST_SNAPSHOT_FIELDS = {
    "snapshot_date": "rq",
    "raw_jg": "jg",
    "raw_t019": "T019",
}

EARNINGS_FORECAST_METADATA_FIELDS = {
    "metadata_date": "rq",
    "raw_t023": "t023",
    "company_name": "T003",
}


def parse_company_overview(stock_code: str, data_root: Path) -> Path:
    valid_stock_code = validate_stock_code(stock_code)
    data_root = Path(data_root)
    writer = RawCacheWriter(data_root)
    paths = writer.paths(
        entry=COMPANY_OVERVIEW_ENTRY,
        stock_code=valid_stock_code,
        module=COMPANY_OVERVIEW_MODULE,
    )

    if not paths.data_path.exists():
        raise TqlexError(f"company overview raw JSON not found: {paths.data_path}")

    json_data = read_json_object(paths.data_path)
    metadata = read_json_object(paths.meta_path) if paths.meta_path.exists() else {}
    row = company_overview_row(json_data)
    database_path = data_root / "warehouse" / "research.duckdb"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(database_path)) as connection:
        connection.execute(COMPANY_OVERVIEW_SCHEMA)
        if row is None:
            return database_path
        connection.execute(
            COMPANY_OVERVIEW_UPSERT,
            [
                valid_stock_code,
                *(row[field] for field in COMPANY_OVERVIEW_FIELDS),
                paths.data_path.as_posix(),
                COMPANY_OVERVIEW_ENTRY,
                COMPANY_OVERVIEW_MODULE,
                metadata.get("fetched_at"),
                metadata.get("response_hash"),
                now_shanghai_iso(),
            ],
        )

    return database_path


def parse_research_ratings(stock_code: str, data_root: Path) -> Path:
    valid_stock_code = validate_stock_code(stock_code)
    data_root = Path(data_root)
    writer = RawCacheWriter(data_root)
    summary_paths = writer.paths(
        entry=RESEARCH_RATING_ENTRY,
        stock_code=valid_stock_code,
        module=RESEARCH_RATING_SUMMARY_MODULE,
    )
    report_paths = writer.paths(
        entry=RESEARCH_RATING_ENTRY,
        stock_code=valid_stock_code,
        module=RESEARCH_REPORT_MODULE,
    )
    forecast_paths = writer.paths(
        entry=RESEARCH_RATING_ENTRY,
        stock_code=valid_stock_code,
        module=EARNINGS_FORECAST_MODULE,
    )
    for paths in (summary_paths, report_paths):
        if not paths.data_path.exists():
            raise TqlexError(f"research rating raw JSON not found: {paths.data_path}")

    summary_rows = result_set_rows(read_json_object(summary_paths.data_path))
    report_rows = result_set_rows(read_json_object(report_paths.data_path))
    forecast_rows_by_result_set = (
        all_result_set_rows(read_json_object(forecast_paths.data_path))
        if forecast_paths.data_path.exists()
        else None
    )
    summary_metadata = (
        read_json_object(summary_paths.meta_path)
        if summary_paths.meta_path.exists()
        else {}
    )
    report_metadata = (
        read_json_object(report_paths.meta_path)
        if report_paths.meta_path.exists()
        else {}
    )
    forecast_metadata = (
        read_json_object(forecast_paths.meta_path)
        if forecast_paths.meta_path.exists()
        else {}
    )
    database_path = data_root / "warehouse" / "research.duckdb"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    structured_at = now_shanghai_iso()

    with duckdb.connect(str(database_path)) as connection:
        connection.execute(RESEARCH_RATING_SUMMARIES_SCHEMA)
        connection.execute(RESEARCH_REPORTS_SCHEMA)
        connection.execute(EARNINGS_FORECAST_WINDOWS_SCHEMA)
        connection.execute(EARNINGS_FORECAST_CONSENSUSES_SCHEMA)
        connection.execute(EARNINGS_FORECAST_HISTORY_SCHEMA)
        connection.execute(EARNINGS_FORECAST_SNAPSHOTS_SCHEMA)
        connection.execute(EARNINGS_FORECAST_METADATA_SCHEMA)
        connection.execute("BEGIN")
        try:
            replace_research_rating_summaries(
                connection,
                stock_code=valid_stock_code,
                rows=summary_rows,
                paths=summary_paths,
                metadata=summary_metadata,
                structured_at=structured_at,
            )
            replace_research_reports(
                connection,
                stock_code=valid_stock_code,
                rows=report_rows,
                paths=report_paths,
                metadata=report_metadata,
                structured_at=structured_at,
            )
            if forecast_rows_by_result_set is not None:
                replace_earnings_forecast_result_sets(
                    connection,
                    stock_code=valid_stock_code,
                    rows_by_result_set=forecast_rows_by_result_set,
                    paths=forecast_paths,
                    metadata=forecast_metadata,
                    structured_at=structured_at,
                )
        except Exception:
            connection.execute("ROLLBACK")
            raise
        connection.execute("COMMIT")

    return database_path


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TqlexError(f"invalid JSON in {path}") from exc
    if not isinstance(value, dict):
        raise TqlexError(f"expected a JSON object in {path}")
    return value


def company_overview_row(
    json_data: dict[str, Any],
) -> dict[str, str | int | None] | None:
    result_sets = json_data.get("ResultSets")
    if not isinstance(result_sets, list) or not result_sets:
        return None

    result_set = result_sets[0]
    if not isinstance(result_set, dict):
        raise TqlexError("company overview result set is invalid")

    columns = result_set.get("ColDes")
    content = result_set.get("Content")
    if not isinstance(columns, list) or not isinstance(content, list) or not content:
        return None
    if not isinstance(content[0], list):
        raise TqlexError("company overview row is invalid")

    values_by_column = {}
    for index, column in enumerate(columns):
        if not isinstance(column, dict):
            continue
        name = column.get("Name")
        if isinstance(name, str) and index < len(content[0]):
            values_by_column[name] = content[0][index]

    row = {
        field: normalize_text(values_by_column.get(source_name))
        for field, source_name in COMPANY_OVERVIEW_FIELDS.items()
    }
    row["employee_count"] = parse_integer(row["employee_count"])
    return row


def result_set_rows(json_data: dict[str, Any]) -> list[dict[str, Any]]:
    rows_by_result_set = all_result_set_rows(json_data)
    return rows_by_result_set[0] if rows_by_result_set else []


def all_result_set_rows(json_data: dict[str, Any]) -> list[list[dict[str, Any]]]:
    result_sets = json_data.get("ResultSets")
    if not isinstance(result_sets, list) or not result_sets:
        return []

    rows_by_result_set = []
    for result_set in result_sets:
        if not isinstance(result_set, dict):
            raise TqlexError("research rating result set is invalid")
        columns = result_set.get("ColDes")
        content = result_set.get("Content")
        if not isinstance(columns, list) or not isinstance(content, list):
            rows_by_result_set.append([])
            continue

        column_names = [
            column.get("Name") if isinstance(column, dict) else None
            for column in columns
        ]
        rows = []
        for values in content:
            if not isinstance(values, list):
                raise TqlexError("research rating row is invalid")
            rows.append(
                {
                    name: values[index]
                    for index, name in enumerate(column_names)
                    if isinstance(name, str) and index < len(values)
                }
            )
        rows_by_result_set.append(rows)
    return rows_by_result_set


def replace_research_rating_summaries(
    connection: duckdb.DuckDBPyConnection,
    *,
    stock_code: str,
    rows: list[dict[str, Any]],
    paths: Any,
    metadata: dict[str, Any],
    structured_at: str,
) -> None:
    connection.execute(
        "DELETE FROM research_rating_summaries WHERE stock_code = ?", [stock_code]
    )
    if not rows:
        return

    values = []
    for row in rows:
        normalized = {
            field: normalize_text(row.get(source_name))
            for field, source_name in RESEARCH_RATING_SUMMARY_FIELDS.items()
        }
        values.append(
            [
                stock_code,
                normalized["rating_date"],
                *(parse_integer(normalized[field]) for field in (
                    "raw_sj",
                    "raw_zj",
                    "raw_mr",
                    "raw_zc",
                    "raw_zx",
                    "raw_jc",
                    "raw_mc",
                )),
                parse_float(normalized["rating_value"]),
                normalized["raw_t006"],
                paths.data_path.as_posix(),
                RESEARCH_RATING_ENTRY,
                RESEARCH_RATING_SUMMARY_MODULE,
                metadata.get("fetched_at"),
                metadata.get("response_hash"),
                structured_at,
            ]
        )
    connection.executemany(RESEARCH_RATING_SUMMARIES_INSERT, values)


def replace_research_reports(
    connection: duckdb.DuckDBPyConnection,
    *,
    stock_code: str,
    rows: list[dict[str, Any]],
    paths: Any,
    metadata: dict[str, Any],
    structured_at: str,
) -> None:
    connection.execute("DELETE FROM research_reports WHERE stock_code = ?", [stock_code])
    if not rows:
        return

    values = []
    for row in rows:
        normalized = {
            field: normalize_text(row.get(source_name))
            for field, source_name in RESEARCH_REPORT_FIELDS.items()
        }
        values.append(
            [
                stock_code,
                *(normalized[field] for field in RESEARCH_REPORT_FIELDS),
                paths.data_path.as_posix(),
                RESEARCH_RATING_ENTRY,
                RESEARCH_REPORT_MODULE,
                metadata.get("fetched_at"),
                metadata.get("response_hash"),
                structured_at,
            ]
        )
    connection.executemany(RESEARCH_REPORTS_INSERT, values)


def replace_earnings_forecast_result_sets(
    connection: duckdb.DuckDBPyConnection,
    *,
    stock_code: str,
    rows_by_result_set: list[list[dict[str, Any]]],
    paths: Any,
    metadata: dict[str, Any],
    structured_at: str,
) -> None:
    replace_earnings_forecast_table(
        connection,
        table_name="earnings_forecast_windows",
        fields=EARNINGS_FORECAST_WINDOW_FIELDS,
        stock_code=stock_code,
        rows=result_set_at(rows_by_result_set, 0),
        paths=paths,
        metadata=metadata,
        structured_at=structured_at,
    )
    replace_earnings_forecast_table(
        connection,
        table_name="earnings_forecast_consensuses",
        fields=EARNINGS_FORECAST_CONSENSUS_FIELDS,
        stock_code=stock_code,
        rows=result_set_at(rows_by_result_set, 1),
        paths=paths,
        metadata=metadata,
        structured_at=structured_at,
    )
    replace_earnings_forecast_table(
        connection,
        table_name="earnings_forecast_history",
        fields=EARNINGS_FORECAST_HISTORY_FIELDS,
        stock_code=stock_code,
        rows=result_set_at(rows_by_result_set, 2),
        paths=paths,
        metadata=metadata,
        structured_at=structured_at,
    )
    replace_earnings_forecast_table(
        connection,
        table_name="earnings_forecast_snapshots",
        fields=EARNINGS_FORECAST_SNAPSHOT_FIELDS,
        stock_code=stock_code,
        rows=result_set_at(rows_by_result_set, 3),
        paths=paths,
        metadata=metadata,
        structured_at=structured_at,
    )
    replace_earnings_forecast_table(
        connection,
        table_name="earnings_forecast_metadata",
        fields=EARNINGS_FORECAST_METADATA_FIELDS,
        stock_code=stock_code,
        rows=result_set_at(rows_by_result_set, 4),
        paths=paths,
        metadata=metadata,
        structured_at=structured_at,
    )


def result_set_at(
    rows_by_result_set: list[list[dict[str, Any]]], index: int
) -> list[dict[str, Any]]:
    return rows_by_result_set[index] if index < len(rows_by_result_set) else []


def replace_earnings_forecast_table(
    connection: duckdb.DuckDBPyConnection,
    *,
    table_name: str,
    fields: dict[str, str],
    stock_code: str,
    rows: list[dict[str, Any]],
    paths: Any,
    metadata: dict[str, Any],
    structured_at: str,
) -> None:
    connection.execute(f"DELETE FROM {table_name} WHERE stock_code = ?", [stock_code])
    if not rows:
        return

    source_columns = (
        "source_path",
        "source_entry",
        "source_module",
        "source_fetched_at",
        "source_response_hash",
        "structured_at",
    )
    columns = ("stock_code", *fields, *source_columns)
    placeholders = ", ".join("?" for _ in columns)
    statement = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    values = []
    for row in rows:
        values.append(
            [
                stock_code,
                *(normalize_text(row.get(source_name)) for source_name in fields.values()),
                paths.data_path.as_posix(),
                RESEARCH_RATING_ENTRY,
                EARNINGS_FORECAST_MODULE,
                metadata.get("fetched_at"),
                metadata.get("response_hash"),
                structured_at,
            ]
        )
    connection.executemany(statement, values)


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        repaired = text.encode("gb18030").decode("utf-8")
    except UnicodeError:
        return text
    return repaired


def parse_integer(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.replace(",", ""))
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


COMPANY_OVERVIEW_SCHEMA = """
CREATE TABLE IF NOT EXISTS company_overviews (
    stock_code VARCHAR PRIMARY KEY,
    name VARCHAR,
    board VARCHAR,
    english_name VARCHAR,
    website VARCHAR,
    industry VARCHAR,
    social_credit_code VARCHAR,
    business_summary VARCHAR,
    products VARCHAR,
    controlling_shareholder VARCHAR,
    chairman VARCHAR,
    general_manager VARCHAR,
    legal_representative VARCHAR,
    board_secretary VARCHAR,
    employee_count BIGINT,
    phone VARCHAR,
    email VARCHAR,
    accounting_firm VARCHAR,
    law_firm VARCHAR,
    registered_address VARCHAR,
    office_address VARCHAR,
    company_profile VARCHAR,
    business_scope VARCHAR,
    source_path VARCHAR NOT NULL,
    source_entry VARCHAR NOT NULL,
    source_module VARCHAR NOT NULL,
    source_fetched_at VARCHAR,
    source_response_hash VARCHAR,
    structured_at VARCHAR NOT NULL
)
"""


COMPANY_OVERVIEW_UPSERT = """
INSERT INTO company_overviews (
    stock_code,
    name,
    board,
    english_name,
    website,
    industry,
    social_credit_code,
    business_summary,
    products,
    controlling_shareholder,
    chairman,
    general_manager,
    legal_representative,
    board_secretary,
    employee_count,
    phone,
    email,
    accounting_firm,
    law_firm,
    registered_address,
    office_address,
    company_profile,
    business_scope,
    source_path,
    source_entry,
    source_module,
    source_fetched_at,
    source_response_hash,
    structured_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (stock_code) DO UPDATE SET
    name = excluded.name,
    board = excluded.board,
    english_name = excluded.english_name,
    website = excluded.website,
    industry = excluded.industry,
    social_credit_code = excluded.social_credit_code,
    business_summary = excluded.business_summary,
    products = excluded.products,
    controlling_shareholder = excluded.controlling_shareholder,
    chairman = excluded.chairman,
    general_manager = excluded.general_manager,
    legal_representative = excluded.legal_representative,
    board_secretary = excluded.board_secretary,
    employee_count = excluded.employee_count,
    phone = excluded.phone,
    email = excluded.email,
    accounting_firm = excluded.accounting_firm,
    law_firm = excluded.law_firm,
    registered_address = excluded.registered_address,
    office_address = excluded.office_address,
    company_profile = excluded.company_profile,
    business_scope = excluded.business_scope,
    source_path = excluded.source_path,
    source_entry = excluded.source_entry,
    source_module = excluded.source_module,
    source_fetched_at = excluded.source_fetched_at,
    source_response_hash = excluded.source_response_hash,
    structured_at = excluded.structured_at
"""


RESEARCH_RATING_SUMMARIES_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_rating_summaries (
    stock_code VARCHAR NOT NULL,
    rating_date VARCHAR,
    raw_sj BIGINT,
    raw_zj BIGINT,
    raw_mr BIGINT,
    raw_zc BIGINT,
    raw_zx BIGINT,
    raw_jc BIGINT,
    raw_mc BIGINT,
    rating_value DOUBLE,
    raw_t006 VARCHAR,
    source_path VARCHAR NOT NULL,
    source_entry VARCHAR NOT NULL,
    source_module VARCHAR NOT NULL,
    source_fetched_at VARCHAR,
    source_response_hash VARCHAR,
    structured_at VARCHAR NOT NULL
)
"""


RESEARCH_RATING_SUMMARIES_INSERT = """
INSERT INTO research_rating_summaries (
    stock_code, rating_date, raw_sj, raw_zj, raw_mr, raw_zc, raw_zx, raw_jc,
    raw_mc, rating_value, raw_t006, source_path, source_entry, source_module,
    source_fetched_at, source_response_hash, structured_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


RESEARCH_REPORTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_reports (
    stock_code VARCHAR NOT NULL,
    report_id VARCHAR NOT NULL,
    report_date VARCHAR,
    rating VARCHAR,
    institution VARCHAR,
    analysis_text VARCHAR,
    rating_score VARCHAR,
    title VARCHAR,
    source_path VARCHAR NOT NULL,
    source_entry VARCHAR NOT NULL,
    source_module VARCHAR NOT NULL,
    source_fetched_at VARCHAR,
    source_response_hash VARCHAR,
    structured_at VARCHAR NOT NULL,
    PRIMARY KEY (stock_code, report_id)
)
"""


RESEARCH_REPORTS_INSERT = """
INSERT INTO research_reports (
    stock_code, report_id, report_date, rating, institution, analysis_text,
    rating_score, title, source_path, source_entry, source_module,
    source_fetched_at, source_response_hash, structured_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


EARNINGS_FORECAST_WINDOWS_SCHEMA = """
CREATE TABLE IF NOT EXISTS earnings_forecast_windows (
    stock_code VARCHAR NOT NULL,
    forecast_year VARCHAR,
    raw_flag VARCHAR,
    source_path VARCHAR NOT NULL,
    source_entry VARCHAR NOT NULL,
    source_module VARCHAR NOT NULL,
    source_fetched_at VARCHAR,
    source_response_hash VARCHAR,
    structured_at VARCHAR NOT NULL
)
"""


EARNINGS_FORECAST_CONSENSUSES_SCHEMA = """
CREATE TABLE IF NOT EXISTS earnings_forecast_consensuses (
    stock_code VARCHAR NOT NULL,
    raw_t036 VARCHAR,
    raw_t037 VARCHAR,
    raw_t038 VARCHAR,
    raw_t027 VARCHAR,
    raw_t028 VARCHAR,
    raw_t029 VARCHAR,
    raw_t024 VARCHAR,
    raw_t025 VARCHAR,
    raw_t026 VARCHAR,
    raw_t033 VARCHAR,
    raw_t034 VARCHAR,
    raw_t035 VARCHAR,
    raw_t021 VARCHAR,
    raw_t022 VARCHAR,
    raw_t023 VARCHAR,
    raw_t030 VARCHAR,
    raw_t031 VARCHAR,
    raw_t032 VARCHAR,
    source_path VARCHAR NOT NULL,
    source_entry VARCHAR NOT NULL,
    source_module VARCHAR NOT NULL,
    source_fetched_at VARCHAR,
    source_response_hash VARCHAR,
    structured_at VARCHAR NOT NULL
)
"""


EARNINGS_FORECAST_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS earnings_forecast_history (
    stock_code VARCHAR NOT NULL,
    fiscal_year VARCHAR,
    raw_t055 VARCHAR,
    raw_t059 VARCHAR,
    raw_t064 VARCHAR,
    raw_t018 VARCHAR,
    raw_t003 VARCHAR,
    raw_t012 VARCHAR,
    raw_t118 VARCHAR,
    source_path VARCHAR NOT NULL,
    source_entry VARCHAR NOT NULL,
    source_module VARCHAR NOT NULL,
    source_fetched_at VARCHAR,
    source_response_hash VARCHAR,
    structured_at VARCHAR NOT NULL
)
"""


EARNINGS_FORECAST_SNAPSHOTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS earnings_forecast_snapshots (
    stock_code VARCHAR NOT NULL,
    snapshot_date VARCHAR,
    raw_jg VARCHAR,
    raw_t019 VARCHAR,
    source_path VARCHAR NOT NULL,
    source_entry VARCHAR NOT NULL,
    source_module VARCHAR NOT NULL,
    source_fetched_at VARCHAR,
    source_response_hash VARCHAR,
    structured_at VARCHAR NOT NULL
)
"""


EARNINGS_FORECAST_METADATA_SCHEMA = """
CREATE TABLE IF NOT EXISTS earnings_forecast_metadata (
    stock_code VARCHAR NOT NULL,
    metadata_date VARCHAR,
    raw_t023 VARCHAR,
    company_name VARCHAR,
    source_path VARCHAR NOT NULL,
    source_entry VARCHAR NOT NULL,
    source_module VARCHAR NOT NULL,
    source_fetched_at VARCHAR,
    source_response_hash VARCHAR,
    structured_at VARCHAR NOT NULL
)
"""
