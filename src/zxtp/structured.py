from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from .tqlex import RawCacheWriter, TqlexError, now_shanghai_iso, validate_stock_code


COMPANY_OVERVIEW_ENTRY = "tdxf10_gg_gsgk"
COMPANY_OVERVIEW_MODULE = "gsgk"

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
