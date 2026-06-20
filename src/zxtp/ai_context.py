from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import duckdb

from .tqlex import RawCacheWriter, now_shanghai_iso, validate_stock_code


@dataclass(frozen=True)
class RawSource:
    label: str
    entry: str
    module: str


@dataclass(frozen=True)
class RawSourceStatus:
    source: RawSource
    data_path: Path
    meta_path: Path
    exists: bool
    fetched_at: str | None
    response_hash: str | None


COMPANY_OVERVIEW_SOURCES = (
    RawSource("公司概况", "tdxf10_gg_gsgk", "gsgk"),
)

COMPANY_OVERVIEW_DISPLAY_FIELDS = (
    ("公司名称", "name"),
    ("英文名称", "english_name"),
    ("所属板块", "board"),
    ("所属行业", "industry"),
    ("主营业务", "business_summary"),
    ("产品与服务", "products"),
    ("控股股东", "controlling_shareholder"),
    ("董事长", "chairman"),
    ("总经理", "general_manager"),
    ("法定代表人", "legal_representative"),
    ("董事会秘书", "board_secretary"),
    ("员工人数", "employee_count"),
    ("公司网站", "website"),
    ("联系电话", "phone"),
    ("电子邮箱", "email"),
    ("注册地址", "registered_address"),
    ("办公地址", "office_address"),
    ("公司简介", "company_profile"),
    ("经营范围", "business_scope"),
    ("原始数据抓取时间", "source_fetched_at"),
    ("结构化写入时间", "structured_at"),
)

COMPANY_OVERVIEW_SELECT = ", ".join(
    field for _, field in COMPANY_OVERVIEW_DISPLAY_FIELDS
)

RESEARCH_RATING_COUNT_FIELDS = (
    "raw_sj",
    "raw_zj",
    "raw_mr",
    "raw_zc",
    "raw_zx",
    "raw_jc",
    "raw_mc",
)

FINANCIAL_ANALYSIS_SOURCES = (
    RawSource("公司类型", "tdxf10_gg_cwfx", "gptype"),
    RawSource("财务诊断", "tdxf10_gg_cwfx", "cwzd"),
    RawSource("资产堆积图", "tdxf10_gg_cwfx", "zcdjt"),
    RawSource("资产负债构成", "tdxf10_gg_cwfx", "cwgc"),
    RawSource("财务报告", "tdxf10_gg_cwfx", "cwbg"),
    RawSource("主要指标", "tdxf10_gg_cwfx", "zyzb"),
    RawSource("资产负债表", "tdxf10_gg_cwfx", "zcfzb"),
    RawSource("利润表", "tdxf10_gg_cwfx", "lyb"),
    RawSource("现金流量表", "tdxf10_gg_cwfx", "xjllb"),
    RawSource("银行专项指标", "tdxf10_gg_cwfx", "yhzxzb"),
    RawSource("券商专项指标", "tdxf10_gg_cwfx", "qszxzb"),
    RawSource("保险专项指标", "tdxf10_gg_cwfx", "bxzxzb"),
    RawSource("我的指标", "tdxf10_gg_cwfx", "wdzb"),
    RawSource("盈利能力", "tdxf10_gg_cwfx", "ylnl"),
    RawSource("收益质量", "tdxf10_gg_cwfx", "syzl"),
    RawSource("营运能力", "tdxf10_gg_cwfx", "yynl"),
    RawSource("资本结构", "tdxf10_gg_cwfx", "zbjg"),
    RawSource("偿债能力", "tdxf10_gg_cwfx", "cznl"),
    RawSource("现金流量", "tdxf10_gg_cwfx", "xjll"),
    RawSource("成长能力", "tdxf10_gg_cwfx", "cznl2"),
    RawSource("指标变动日期", "tdxf10_gg_comreq", "bdsm"),
    RawSource("财报点评", "tdxf10_gg_cwfx_cbdp", "cbdp"),
)

BUSINESS_ANALYSIS_SOURCES = (
    RawSource("主营介绍", "tdxf10_gg_jyfx", "zyyw"),
    RawSource("经营数据分析", "tdxf10_gg_jyfx_jysj", "jysj"),
    RawSource("主营构成日期", "tdxf10_gg_comreq", "zygcfx"),
    RawSource("主营构成分析", "tdxf10_gg_jyfx", "zygc"),
    RawSource("前五大客户日期", "tdxf10_gg_comreq", "qwm"),
    RawSource("前五大客户", "tdxf10_gg_jyfx", "qwm"),
    RawSource("前五大供应商日期", "tdxf10_gg_comreq", "qwmgys"),
    RawSource("前五大供应商", "tdxf10_gg_jyfx", "qwmgys"),
    RawSource("经营情况评述日期", "tdxf10_gg_comreq", "jyqk"),
    RawSource("经营情况评述", "tdxf10_gg_jyfx", "jyqk"),
)

DIVIDEND_FINANCING_SOURCES = (
    RawSource("分红募资概览", "tdxf10_gg_fhrz", "pxmz"),
    RawSource("分红转增", "tdxf10_gg_fhrz", "fh"),
    RawSource("分红转增图表", "tdxf10_gg_fhrz", "fh_zzt"),
    RawSource("分红历史股利支付率", "tdxf10_gg_fhrz", "fhlszs_glzfl"),
    RawSource("分红历史股息率", "tdxf10_gg_fhrz", "fhlszs_gxl"),
    RawSource("分红排名股利支付率", "tdxf10_gg_fhrz", "fhpm_glzfl"),
    RawSource("分红排名股息率", "tdxf10_gg_fhrz", "fhpm_gxl"),
    RawSource("分红排名派现融资比", "tdxf10_gg_fhrz", "fhpm_pxrzb"),
    RawSource("配股", "tdxf10_gg_fhrz", "pf"),
    RawSource("增发获配日期", "tdxf10_gg_fhrz_zfhpmx", "zfpg_bgq"),
    RawSource("增发获配明细", "tdxf10_gg_fhrz_zfhpmx", "zfpg"),
    RawSource("增发", "tdxf10_gg_fhrz", "zf"),
    RawSource("股权激励", "tdxf10_gg_fhrz", "gqjl"),
    RawSource("可转债发行上市", "tdxf10_gg_fhrz", "kzzdfxyss"),
)

RESEARCH_RATING_SOURCES = (
    RawSource("投资评级统计", "tdxf10_gg_ybpj", "tzpjtj"),
    RawSource("业绩预期", "tdxf10_gg_ybpj", "yzyq"),
    RawSource("盈利预测统计", "tdxf10_gg_ybpj", "ylyctj"),
    RawSource("盈利预测明细", "tdxf10_gg_ybpj", "ylycmx"),
    RawSource("预测评级研报", "tdxf10_gg_ybpj", "ycpjyjbg"),
)

INDUSTRY_ANALYSIS_SOURCES = (
    RawSource("行业总览", "tdxf10_gg_hyfx", "tot"),
    RawSource("行业新闻", "tdxf10_gg_hyfx", "hyxw"),
    RawSource("行业研报", "tdxf10_gg_hyfx", "hyyb"),
    RawSource("市场表现", "tdxf10_gg_hyfx", "scbx"),
    RawSource("公司规模", "tdxf10_gg_hyfx", "gsgm"),
    RawSource("估值水平", "tdxf10_gg_hyfx", "gzsp"),
    RawSource("财务估值", "tdxf10_gg_hyfx", "cwgz"),
    RawSource("分红融资比", "tdxf10_gg_hyfx", "fhrzb"),
)

SHAREHOLDER_RESEARCH_SOURCES = (
    RawSource("控股股东与实际控制人", "tdxf10_gg_gdyj", "kggd"),
    RawSource("股东人数", "tdxf10_gg_gdyj", "gdrs"),
    RawSource("同行业股东人数排名", "tdxf10_gg_gdyj", "thygdrs"),
    RawSource("十大流通股东", "tdxf10_gg_gdyj", "ltgd"),
    RawSource("十大股东", "tdxf10_gg_gdyj", "sdgdbgq"),
    RawSource("十大债券持有人", "tdxf10_gg_gdyj", "sdzqcyr"),
    RawSource("重要股东增减持", "tdxf10_gg_gdyj", "cgbd"),
    RawSource("机构持股汇总", "tdxf10_gg_gdyj", "jgcg"),
    RawSource("机构持股日期", "tdxf10_gg_comreq", "jgcg"),
    RawSource("机构持股构成", "tdxf10_gg_gdyj", "jgcgz"),
    RawSource("机构持股明细", "tdxf10_gg_gdyj_jgcgmx", "jgcgmx"),
)


def generate_full_context(stock_code: str, data_root: Path) -> Path:
    valid_stock_code = validate_stock_code(stock_code)
    data_root = Path(data_root)
    generated_at = now_shanghai_iso()

    company_statuses = source_statuses(
        data_root, valid_stock_code, COMPANY_OVERVIEW_SOURCES
    )
    company_overview = render_company_overview(data_root, valid_stock_code)
    financial_statuses = source_statuses(
        data_root, valid_stock_code, FINANCIAL_ANALYSIS_SOURCES
    )
    business_statuses = source_statuses(
        data_root, valid_stock_code, BUSINESS_ANALYSIS_SOURCES
    )
    dividend_statuses = source_statuses(
        data_root, valid_stock_code, DIVIDEND_FINANCING_SOURCES
    )
    research_statuses = source_statuses(
        data_root, valid_stock_code, RESEARCH_RATING_SOURCES
    )
    research_ratings = render_research_ratings(data_root, valid_stock_code)
    industry_statuses = source_statuses(
        data_root, valid_stock_code, INDUSTRY_ANALYSIS_SOURCES
    )
    shareholder_statuses = source_statuses(
        data_root, valid_stock_code, SHAREHOLDER_RESEARCH_SOURCES
    )
    all_statuses = (
        company_statuses
        + financial_statuses
        + business_statuses
        + dividend_statuses
        + research_statuses
        + industry_statuses
        + shareholder_statuses
    )

    template = load_template()
    rendered = render_template(
        template,
        {
            "stock_code": valid_stock_code,
            "generated_at": generated_at,
            "coverage_summary": coverage_summary(all_statuses),
            "company_overview": company_overview,
            "company_overview_sources": render_sources(company_statuses),
            "financial_analysis_sources": render_sources(financial_statuses),
            "business_analysis_sources": render_sources(business_statuses),
            "dividend_financing_sources": render_sources(dividend_statuses),
            "research_ratings": research_ratings,
            "research_rating_sources": render_sources(research_statuses),
            "industry_analysis_sources": render_sources(industry_statuses),
            "shareholder_research_sources": render_sources(shareholder_statuses),
            "all_sources": render_sources(all_statuses),
        },
    )

    output_path = (
        data_root / "exports" / "ai_context" / valid_stock_code / "full_context.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def render_company_overview(data_root: Path, stock_code: str) -> str:
    database_path = data_root / "warehouse" / "research.duckdb"
    if not database_path.exists():
        return "暂无结构化公司概况。请先下载公司概况数据。"

    try:
        with duckdb.connect(str(database_path), read_only=True) as connection:
            row = connection.execute(
                f"SELECT {COMPANY_OVERVIEW_SELECT} "
                "FROM company_overviews WHERE stock_code = ?",
                [stock_code],
            ).fetchone()
    except duckdb.Error:
        return (
            "结构化公司概况暂不可读取：DuckDB 数据库可能正被其他程序占用。"
            "请断开 DBeaver 连接后重新生成 AI Context。"
        )

    if row is None:
        return "暂无结构化公司概况。请先下载公司概况数据。"

    details = []
    for index, (label, _) in enumerate(COMPANY_OVERVIEW_DISPLAY_FIELDS):
        value = format_context_value(row[index])
        if value is not None:
            details.append(f"- {label}：{value}")
    return "\n".join(details)


def render_research_ratings(data_root: Path, stock_code: str) -> str:
    database_path = data_root / "warehouse" / "research.duckdb"
    if not database_path.exists():
        return "暂无结构化研报评级。请先下载研报评级数据。"

    try:
        with duckdb.connect(str(database_path), read_only=True) as connection:
            summary = connection.execute(
                """
                SELECT rating_date, rating_value, raw_sj, raw_zj, raw_mr, raw_zc,
                       raw_zx, raw_jc, raw_mc
                FROM research_rating_summaries
                WHERE stock_code = ?
                ORDER BY rating_date DESC NULLS LAST
                LIMIT 1
                """,
                [stock_code],
            ).fetchone()
            reports = connection.execute(
                """
                SELECT report_date, institution, rating, title
                FROM research_reports
                WHERE stock_code = ?
                ORDER BY report_date DESC NULLS LAST, report_id DESC
                LIMIT 5
                """,
                [stock_code],
            ).fetchall()
    except duckdb.Error:
        return (
            "结构化研报评级暂不可读取：DuckDB 数据库可能正被其他程序占用，"
            "或尚未生成相关数据表。请断开 DBeaver 连接后重新生成 AI Context。"
        )

    if summary is None and not reports:
        return "暂无结构化研报评级。请先下载研报评级数据。"

    sections = []
    if summary is not None:
        values = dict(
            zip(("rating_date", "rating_value", *RESEARCH_RATING_COUNT_FIELDS), summary)
        )
        summary_lines = ["### 评级统计"]
        rating_date = format_context_value(values["rating_date"])
        if rating_date is not None:
            summary_lines.append(f"- 统计日期：{rating_date}")
        rating_value = format_context_value(values["rating_value"])
        if rating_value is not None:
            summary_lines.append(f"- 评分数值：{rating_value}")
        raw_counts = ", ".join(
            f"{field}={value}"
            for field in RESEARCH_RATING_COUNT_FIELDS
            if (value := format_context_value(values[field])) is not None
        )
        if raw_counts:
            summary_lines.append(f"- 原始字段：{raw_counts}")
        sections.append("\n".join(summary_lines))

    if reports:
        report_lines = ["### 最近研报"]
        for report_date, institution, rating, title in reports:
            fields = [
                format_context_value(report_date),
                format_context_value(institution),
                format_context_value(rating),
                format_context_value(title),
            ]
            report_lines.append("- " + " | ".join(value or "-" for value in fields))
        sections.append("\n".join(report_lines))

    return "\n\n".join(sections)


def format_context_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return text or None


def source_statuses(
    data_root: Path, stock_code: str, sources: tuple[RawSource, ...]
) -> list[RawSourceStatus]:
    writer = RawCacheWriter(data_root)
    statuses = []
    for source in sources:
        paths = writer.paths(
            entry=source.entry,
            stock_code=stock_code,
            module=source.module,
        )
        metadata = read_metadata(paths.meta_path)
        statuses.append(
            RawSourceStatus(
                source=source,
                data_path=paths.data_path,
                meta_path=paths.meta_path,
                exists=paths.data_path.exists(),
                fetched_at=metadata.get("fetched_at"),
                response_hash=metadata.get("response_hash"),
            )
        )
    return statuses


def read_metadata(meta_path: Path) -> dict[str, Any]:
    if not meta_path.exists():
        return {}
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(metadata, dict):
        return {}
    return metadata


def load_template() -> str:
    return (
        resources.files("zxtp")
        .joinpath("templates", "ai_context", "full_context.md.tpl")
        .read_text(encoding="utf-8")
    )


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def coverage_summary(statuses: list[RawSourceStatus]) -> str:
    found = sum(1 for status in statuses if status.exists)
    total = len(statuses)
    return f"{found}/{total} 个 raw 模块已缓存"


def render_sources(statuses: list[RawSourceStatus]) -> str:
    return "\n\n".join(render_source(status) for status in statuses)


def render_source(status: RawSourceStatus) -> str:
    source = status.source
    header = f"- [{'x' if status.exists else ' '}] {source.label} (`{source.entry}` / `{source.module}`)"
    if not status.exists:
        return "\n".join(
            [
                header,
                "  - 状态：缺失",
                f"  - expected_raw: `{format_path(status.data_path)}`",
            ]
        )

    details = [
        header,
        f"  - raw: `{format_path(status.data_path)}`",
    ]
    if status.fetched_at:
        details.append(f"  - fetched_at: `{status.fetched_at}`")
    if status.response_hash:
        details.append(f"  - response_hash: `{status.response_hash}`")
    return "\n".join(details)


def format_path(path: Path) -> str:
    return path.as_posix()
