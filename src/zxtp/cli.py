from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Sequence, TextIO

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
    return paths.data_path


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
            print("5. 全部下载 all", file=output_stream)
            print("0. 返回", file=output_stream)
            module = input_func("> ").strip()

            if module == "0":
                print("已返回", file=output_stream)
                return 0
            if module not in {"1", "2", "3", "4", "5"}:
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
