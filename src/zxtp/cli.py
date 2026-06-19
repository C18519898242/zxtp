from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Sequence, TextIO

from .ai_context import generate_full_context
from .config import resolve_data_root
from .tqlex import RawCacheWriter, TqlexClient, TqlexError, validate_stock_code


GSGK_ENTRY = "tdxf10_gg_gsgk"
GSGK_MODULE = "gsgk"
GSGK_PARAM_KIND = "0"
YBPJ_ENTRY = "tdxf10_gg_ybpj"
YBPJ_MODULES = ("tzpjtj", "yzyq", "ylyctj", "ylycmx", "ycpjyjbg")
CWFX_ENTRY = "tdxf10_gg_cwfx"
CWFX_MODULES = (
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
)
CWFX_BDSM_ENTRY = "tdxf10_gg_comreq"
CWFX_BDSM_MODULE = "bdsm"
CWFX_CBDP_ENTRY = "tdxf10_gg_cwfx_cbdp"
CWFX_CBDP_MODULE = "cbdp"
HYFX_ENTRY = "tdxf10_gg_hyfx"
HYFX_MODULES = ("tot", "hyxw", "hyyb", "scbx", "gsgm", "gzsp", "cwgz", "fhrzb")
JYFX_ENTRY = "tdxf10_gg_jyfx"
JYFX_JYSJ_ENTRY = "tdxf10_gg_jyfx_jysj"
JYFX_JYSJ_MODULE = "jysj"
JYFX_ZYYW_MODULE = "zyyw"
JYFX_DATE_DETAIL_MODULES = (
    ("zygcfx", "zygc", "zygc"),
    ("qwm", "qwm", "qwm"),
    ("qwmgys", "qwmgys", "qwmgys"),
    ("jyqk", "jyqk", "0"),
)
FHRZ_ENTRY = "tdxf10_gg_fhrz"
FHRZ_MODULES = (
    "pxmz",
    "fh",
    "fh_zzt",
    "fhlszs_glzfl",
    "fhlszs_gxl",
    "fhpm_glzfl",
    "fhpm_gxl",
    "fhpm_pxrzb",
    "pf",
)
FHRZ_ZFHPMX_ENTRY = "tdxf10_gg_fhrz_zfhpmx"
FHRZ_ZFPG_DATE_MODULE = "zfpg_bgq"
FHRZ_ZFPG_MODULE = "zfpg"
FHRZ_TRAILING_MODULES = ("zf", "gqjl", "kzzdfxyss")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zxtp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_gsgk = subparsers.add_parser(
        "fetch-gsgk",
        help="Fetch TQLEX company overview raw JSON for one stock.",
    )
    fetch_gsgk.add_argument("stock_code")
    fetch_gsgk.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root directory. Overrides config.toml [data].root.",
    )

    fetch_ybpj = subparsers.add_parser(
        "fetch-ybpj",
        help="Fetch TQLEX research rating raw JSON for one stock.",
    )
    fetch_ybpj.add_argument("stock_code")
    fetch_ybpj.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root directory. Overrides config.toml [data].root.",
    )

    fetch_cwfx = subparsers.add_parser(
        "fetch-cwfx",
        help="Fetch TQLEX financial analysis raw JSON for one stock.",
    )
    fetch_cwfx.add_argument("stock_code")
    fetch_cwfx.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root directory. Overrides config.toml [data].root.",
    )

    fetch_hyfx = subparsers.add_parser(
        "fetch-hyfx",
        help="Fetch TQLEX industry analysis raw JSON for one stock.",
    )
    fetch_hyfx.add_argument("stock_code")
    fetch_hyfx.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root directory. Overrides config.toml [data].root.",
    )

    fetch_jyfx = subparsers.add_parser(
        "fetch-jyfx",
        help="Fetch TQLEX business analysis raw JSON for one stock.",
    )
    fetch_jyfx.add_argument("stock_code")
    fetch_jyfx.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root directory. Overrides config.toml [data].root.",
    )

    fetch_fhrz = subparsers.add_parser(
        "fetch-fhrz",
        help="Fetch TQLEX dividend and financing raw JSON for one stock.",
    )
    fetch_fhrz.add_argument("stock_code")
    fetch_fhrz.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root directory. Overrides config.toml [data].root.",
    )

    fetch_all = subparsers.add_parser(
        "fetch-all",
        help="Fetch all supported TQLEX raw JSON modules for one stock.",
    )
    fetch_all.add_argument("stock_code")
    fetch_all.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root directory. Overrides config.toml [data].root.",
    )

    export_ai_context = subparsers.add_parser(
        "export-ai-context",
        help="Generate stock-first AI context Markdown from local raw cache.",
    )
    export_ai_context.add_argument("stock_code")
    export_ai_context.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root directory. Overrides config.toml [data].root.",
    )

    ui = subparsers.add_parser(
        "ui",
        help="Open an interactive command menu.",
    )
    ui.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root directory. Overrides config.toml [data].root.",
    )

    return parser


def fetch_tqlex_raw(
    *,
    entry: str,
    params: list[str],
    stock_code: str,
    module: str,
    data_root: Path,
    client: TqlexClient,
) -> Path:
    data_path, _ = fetch_tqlex_raw_json(
        entry=entry,
        params=params,
        stock_code=stock_code,
        module=module,
        data_root=data_root,
        client=client,
    )
    return data_path


def fetch_tqlex_raw_json(
    *,
    entry: str,
    params: list[str],
    stock_code: str,
    module: str,
    data_root: Path,
    client: TqlexClient,
) -> tuple[Path, dict[str, Any]]:
    response = client.call(entry, params)

    writer = RawCacheWriter(data_root)
    paths = writer.write(
        entry=entry,
        params=params,
        stock_code=stock_code,
        module=module,
        source_url=client.source_url(entry),
        json_data=response.json_data,
    )
    return paths.data_path, response.json_data


def fetch_gsgk(stock_code: str, data_root: Path) -> Path:
    valid_stock_code = validate_stock_code(stock_code)
    params = [GSGK_PARAM_KIND, valid_stock_code, ""]
    client = TqlexClient()
    return fetch_tqlex_raw(
        entry=GSGK_ENTRY,
        params=params,
        stock_code=valid_stock_code,
        module=GSGK_MODULE,
        data_root=data_root,
        client=client,
    )


def fetch_ybpj(stock_code: str, data_root: Path) -> list[Path]:
    valid_stock_code = validate_stock_code(stock_code)
    client = TqlexClient()
    data_paths = []

    for module in YBPJ_MODULES:
        data_paths.append(
            fetch_tqlex_raw(
                entry=YBPJ_ENTRY,
                params=[valid_stock_code, module],
                stock_code=valid_stock_code,
                module=module,
                data_root=data_root,
                client=client,
            )
        )

    return data_paths


def fetch_cwfx(stock_code: str, data_root: Path) -> list[Path]:
    valid_stock_code = validate_stock_code(stock_code)
    client = TqlexClient()
    data_paths = []

    for module in CWFX_MODULES:
        data_paths.append(
            fetch_tqlex_raw(
                entry=CWFX_ENTRY,
                params=[valid_stock_code, module, ""],
                stock_code=valid_stock_code,
                module=module,
                data_root=data_root,
                client=client,
            )
        )

    data_paths.append(
        fetch_tqlex_raw(
            entry=CWFX_BDSM_ENTRY,
            params=[CWFX_BDSM_MODULE, valid_stock_code],
            stock_code=valid_stock_code,
            module=CWFX_BDSM_MODULE,
            data_root=data_root,
            client=client,
        )
    )
    data_paths.append(
        fetch_tqlex_raw(
            entry=CWFX_CBDP_ENTRY,
            params=[valid_stock_code, "1"],
            stock_code=valid_stock_code,
            module=CWFX_CBDP_MODULE,
            data_root=data_root,
            client=client,
        )
    )

    return data_paths


def fetch_hyfx(stock_code: str, data_root: Path) -> list[Path]:
    valid_stock_code = validate_stock_code(stock_code)
    client = TqlexClient()
    data_paths = []

    for module in HYFX_MODULES:
        data_paths.append(
            fetch_tqlex_raw(
                entry=HYFX_ENTRY,
                params=[module, valid_stock_code, ""],
                stock_code=valid_stock_code,
                module=module,
                data_root=data_root,
                client=client,
            )
        )

    return data_paths


def fetch_jyfx(stock_code: str, data_root: Path) -> list[Path]:
    valid_stock_code = validate_stock_code(stock_code)
    client = TqlexClient()
    data_paths = []

    data_paths.append(
        fetch_tqlex_raw(
            entry=JYFX_ENTRY,
            params=[valid_stock_code, JYFX_ZYYW_MODULE, ""],
            stock_code=valid_stock_code,
            module=JYFX_ZYYW_MODULE,
            data_root=data_root,
            client=client,
        )
    )
    data_paths.append(
        fetch_tqlex_raw(
            entry=JYFX_JYSJ_ENTRY,
            params=[valid_stock_code],
            stock_code=valid_stock_code,
            module=JYFX_JYSJ_MODULE,
            data_root=data_root,
            client=client,
        )
    )

    for date_module, detail_module, detail_param_module in JYFX_DATE_DETAIL_MODULES:
        date_path, date_json = fetch_tqlex_raw_json(
            entry=CWFX_BDSM_ENTRY,
            params=[date_module, valid_stock_code],
            stock_code=valid_stock_code,
            module=date_module,
            data_root=data_root,
            client=client,
        )
        data_paths.append(date_path)
        report_date = first_result_value(date_json, ("T002", "N001", "rq", "date"))
        data_paths.append(
            fetch_tqlex_raw(
                entry=JYFX_ENTRY,
                params=[valid_stock_code, detail_param_module, report_date],
                stock_code=valid_stock_code,
                module=detail_module,
                data_root=data_root,
                client=client,
            )
        )

    return data_paths


def fetch_fhrz(stock_code: str, data_root: Path) -> list[Path]:
    valid_stock_code = validate_stock_code(stock_code)
    client = TqlexClient()
    data_paths = []

    for module in FHRZ_MODULES:
        data_paths.append(
            fetch_tqlex_raw(
                entry=FHRZ_ENTRY,
                params=[valid_stock_code, module],
                stock_code=valid_stock_code,
                module=module,
                data_root=data_root,
                client=client,
            )
        )

    date_path, date_json = fetch_tqlex_raw_json(
        entry=FHRZ_ZFHPMX_ENTRY,
        params=[FHRZ_ZFPG_DATE_MODULE, valid_stock_code, ""],
        stock_code=valid_stock_code,
        module=FHRZ_ZFPG_DATE_MODULE,
        data_root=data_root,
        client=client,
    )
    data_paths.append(date_path)
    report_date = first_result_value(date_json, ("rq", "T002", "N001", "date"))
    data_paths.append(
        fetch_tqlex_raw(
            entry=FHRZ_ZFHPMX_ENTRY,
            params=[FHRZ_ZFPG_MODULE, valid_stock_code, report_date],
            stock_code=valid_stock_code,
            module=FHRZ_ZFPG_MODULE,
            data_root=data_root,
            client=client,
        )
    )

    for module in FHRZ_TRAILING_MODULES:
        data_paths.append(
            fetch_tqlex_raw(
                entry=FHRZ_ENTRY,
                params=[valid_stock_code, module],
                stock_code=valid_stock_code,
                module=module,
                data_root=data_root,
                client=client,
            )
        )

    return data_paths


def first_result_value(json_data: dict[str, Any], keys: tuple[str, ...]) -> str:
    result_sets = json_data.get("ResultSets", [])
    if not isinstance(result_sets, list):
        return ""
    for result_set in result_sets:
        if not isinstance(result_set, dict):
            continue
        rows = result_set.get("Content") or result_set.get("Rows") or []
        if not isinstance(rows, list):
            continue
        column_indexes = result_column_indexes(result_set)
        for row in rows:
            if isinstance(row, dict):
                for key in keys:
                    value = row.get(key)
                    if value is not None and str(value):
                        return str(value)
            if isinstance(row, list):
                for key in keys:
                    index = column_indexes.get(key)
                    if index is None or index >= len(row):
                        continue
                    value = row[index]
                    if value is not None and str(value):
                        return str(value)
    return ""


def result_column_indexes(result_set: dict[str, Any]) -> dict[str, int]:
    columns = result_set.get("ColDes", [])
    if not isinstance(columns, list):
        return {}
    indexes = {}
    for index, column in enumerate(columns):
        if not isinstance(column, dict):
            continue
        name = column.get("Name")
        if isinstance(name, str) and name:
            indexes[name] = index
    return indexes


def fetch_all(stock_code: str, data_root: Path) -> list[tuple[str, Path]]:
    data_paths: list[tuple[str, Path]] = []

    data_paths.append(("gsgk", fetch_gsgk(stock_code, data_root)))
    data_paths.extend(
        ("ybpj", data_path) for data_path in fetch_ybpj(stock_code, data_root)
    )
    data_paths.extend(
        ("cwfx", data_path) for data_path in fetch_cwfx(stock_code, data_root)
    )
    data_paths.extend(
        ("jyfx", data_path) for data_path in fetch_jyfx(stock_code, data_root)
    )
    data_paths.extend(
        ("fhrz", data_path) for data_path in fetch_fhrz(stock_code, data_root)
    )
    data_paths.extend(
        ("hyfx", data_path) for data_path in fetch_hyfx(stock_code, data_root)
    )

    return data_paths


def run_fetch_all(stock_code: str, data_root: Path, output_stream: TextIO) -> Path:
    valid_stock_code = validate_stock_code(stock_code)

    print("开始下载公司概况 gsgk...", file=output_stream)
    data_path = fetch_gsgk(valid_stock_code, data_root)
    print(f"saved gsgk raw JSON: {data_path}", file=output_stream)

    print("开始下载研报评级 ybpj...", file=output_stream)
    for data_path in fetch_ybpj(valid_stock_code, data_root):
        print(f"saved ybpj raw JSON: {data_path}", file=output_stream)

    print("开始下载财务分析 cwfx...", file=output_stream)
    for data_path in fetch_cwfx(valid_stock_code, data_root):
        print(f"saved cwfx raw JSON: {data_path}", file=output_stream)

    print("开始下载经营分析 jyfx...", file=output_stream)
    for data_path in fetch_jyfx(valid_stock_code, data_root):
        print(f"saved jyfx raw JSON: {data_path}", file=output_stream)

    print("开始下载分红融资 fhrz...", file=output_stream)
    for data_path in fetch_fhrz(valid_stock_code, data_root):
        print(f"saved fhrz raw JSON: {data_path}", file=output_stream)

    print("开始下载行业分析 hyfx...", file=output_stream)
    for data_path in fetch_hyfx(valid_stock_code, data_root):
        print(f"saved hyfx raw JSON: {data_path}", file=output_stream)

    print("开始生成 AI Context...", file=output_stream)
    output_path = generate_full_context(valid_stock_code, data_root)
    print(f"saved AI context Markdown: {output_path}", file=output_stream)
    return output_path


def run_ui(
    data_root: Path,
    *,
    input_func: Callable[[str], str] = input,
    output: TextIO | None = None,
) -> int:
    output_stream = output if output is not None else sys.stdout

    while True:
        try:
            print("ZXTP", file=output_stream)
            print("", file=output_stream)
            print("请选择操作：", file=output_stream)
            print("1. 下载数据", file=output_stream)
            print("2. 生成 AI Context", file=output_stream)
            print("0. 退出", file=output_stream)
            action = input_func("> ").strip()

            if action == "0":
                print("已退出", file=output_stream)
                return 0
            if action == "2":
                print("", file=output_stream)
                print("请输入股票代码：", file=output_stream)
                stock_code = validate_stock_code(input_func("> ").strip())

                print("", file=output_stream)
                print("开始生成 AI Context...", file=output_stream)
                output_path = generate_full_context(stock_code, data_root)
                print(f"saved AI context Markdown: {output_path}", file=output_stream)
                return 0
            if action != "1":
                raise TqlexError("unsupported menu choice")

            print("", file=output_stream)
            print("请选择数据模块：", file=output_stream)
            print("1. 公司概况 gsgk", file=output_stream)
            print("2. 研报评级 ybpj", file=output_stream)
            print("3. 财务分析 cwfx", file=output_stream)
            print("4. 行业分析 hyfx", file=output_stream)
            print("5. 经营分析 jyfx", file=output_stream)
            print("6. 分红融资 fhrz", file=output_stream)
            print("7. 全部下载 all", file=output_stream)
            print("0. 返回", file=output_stream)
            module = input_func("> ").strip()

            if module == "0":
                print("已返回", file=output_stream)
                return 0
            if module not in {"1", "2", "3", "4", "5", "6", "7"}:
                raise TqlexError("unsupported module choice")

            print("", file=output_stream)
            print("请输入股票代码：", file=output_stream)
            stock_code = validate_stock_code(input_func("> ").strip())

            if module == "1":
                print("", file=output_stream)
                print("开始下载公司概况 gsgk...", file=output_stream)
                data_path = fetch_gsgk(stock_code, data_root)
                print(f"saved gsgk raw JSON: {data_path}", file=output_stream)
                return 0

            if module == "2":
                print("", file=output_stream)
                print("开始下载研报评级 ybpj...", file=output_stream)
                for data_path in fetch_ybpj(stock_code, data_root):
                    print(f"saved ybpj raw JSON: {data_path}", file=output_stream)
                return 0

            if module == "3":
                print("", file=output_stream)
                print("开始下载财务分析 cwfx...", file=output_stream)
                for data_path in fetch_cwfx(stock_code, data_root):
                    print(f"saved cwfx raw JSON: {data_path}", file=output_stream)
                return 0

            if module == "4":
                print("", file=output_stream)
                print("开始下载行业分析 hyfx...", file=output_stream)
                for data_path in fetch_hyfx(stock_code, data_root):
                    print(f"saved hyfx raw JSON: {data_path}", file=output_stream)
                return 0

            if module == "5":
                print("", file=output_stream)
                print("开始下载经营分析 jyfx...", file=output_stream)
                for data_path in fetch_jyfx(stock_code, data_root):
                    print(f"saved jyfx raw JSON: {data_path}", file=output_stream)
                return 0

            if module == "6":
                print("", file=output_stream)
                print("开始下载分红融资 fhrz...", file=output_stream)
                for data_path in fetch_fhrz(stock_code, data_root):
                    print(f"saved fhrz raw JSON: {data_path}", file=output_stream)
                return 0

            print("", file=output_stream)
            print("开始全部下载 all...", file=output_stream)
            run_fetch_all(stock_code, data_root, output_stream)
            return 0
        except TqlexError as exc:
            print(f"提示: {exc}", file=output_stream)
            print("", file=output_stream)


def main(
    argv: Sequence[str] | None = None,
    *,
    input_func: Callable[[str], str] = input,
    output: TextIO | None = None,
    error: TextIO | None = None,
) -> int:
    output_stream = output if output is not None else sys.stdout
    error_stream = error if error is not None else sys.stderr
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data_root = resolve_data_root(getattr(args, "data_root", None))
        if args.command == "fetch-gsgk":
            data_path = fetch_gsgk(args.stock_code, data_root)
            print(f"saved gsgk raw JSON: {data_path}", file=output_stream)
            return 0
        if args.command == "fetch-ybpj":
            for data_path in fetch_ybpj(args.stock_code, data_root):
                print(f"saved ybpj raw JSON: {data_path}", file=output_stream)
            return 0
        if args.command == "fetch-cwfx":
            for data_path in fetch_cwfx(args.stock_code, data_root):
                print(f"saved cwfx raw JSON: {data_path}", file=output_stream)
            return 0
        if args.command == "fetch-hyfx":
            for data_path in fetch_hyfx(args.stock_code, data_root):
                print(f"saved hyfx raw JSON: {data_path}", file=output_stream)
            return 0
        if args.command == "fetch-jyfx":
            for data_path in fetch_jyfx(args.stock_code, data_root):
                print(f"saved jyfx raw JSON: {data_path}", file=output_stream)
            return 0
        if args.command == "fetch-fhrz":
            for data_path in fetch_fhrz(args.stock_code, data_root):
                print(f"saved fhrz raw JSON: {data_path}", file=output_stream)
            return 0
        if args.command == "fetch-all":
            run_fetch_all(args.stock_code, data_root, output_stream)
            return 0
        if args.command == "export-ai-context":
            output_path = generate_full_context(args.stock_code, data_root)
            print(f"saved AI context Markdown: {output_path}", file=output_stream)
            return 0
        if args.command == "ui":
            run_ui(data_root, input_func=input_func, output=output_stream)
            return 0
    except TqlexError as exc:
        print(f"error: {exc}", file=error_stream)
        return 1

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
