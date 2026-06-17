from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Sequence, TextIO

from .tqlex import RawCacheWriter, TqlexClient, TqlexError, validate_stock_code


GSGK_ENTRY = "tdxf10_gg_gsgk"
GSGK_MODULE = "gsgk"
GSGK_PARAM_KIND = "0"


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
        default=Path("data"),
        help="Data root directory. Defaults to ./data.",
    )

    ui = subparsers.add_parser(
        "ui",
        help="Open an interactive command menu.",
    )
    ui.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
        help="Data root directory. Defaults to ./data.",
    )

    return parser


def fetch_gsgk(stock_code: str, data_root: Path) -> Path:
    valid_stock_code = validate_stock_code(stock_code)
    params = [GSGK_PARAM_KIND, valid_stock_code, ""]
    client = TqlexClient()
    response = client.call(GSGK_ENTRY, params)

    writer = RawCacheWriter(data_root)
    paths = writer.write(
        entry=GSGK_ENTRY,
        params=params,
        stock_code=valid_stock_code,
        module=GSGK_MODULE,
        source_url=client.source_url(GSGK_ENTRY),
        json_data=response.json_data,
    )
    return paths.data_path


def run_ui(
    data_root: Path,
    *,
    input_func: Callable[[str], str] = input,
    output: TextIO | None = None,
) -> int:
    output_stream = output if output is not None else sys.stdout

    print("ZXTP", file=output_stream)
    print("", file=output_stream)
    print("请选择操作：", file=output_stream)
    print("1. 下载数据", file=output_stream)
    print("0. 退出", file=output_stream)
    action = input_func("> ").strip()

    if action == "0":
        print("已退出", file=output_stream)
        return 0
    if action != "1":
        raise TqlexError("unsupported menu choice")

    print("", file=output_stream)
    print("请选择数据模块：", file=output_stream)
    print("1. 公司概况 gsgk", file=output_stream)
    print("0. 返回", file=output_stream)
    module = input_func("> ").strip()

    if module == "0":
        print("已返回", file=output_stream)
        return 0
    if module != "1":
        raise TqlexError("unsupported module choice")

    print("", file=output_stream)
    print("请输入股票代码：", file=output_stream)
    stock_code = input_func("> ").strip()

    print("", file=output_stream)
    print("开始下载公司概况 gsgk...", file=output_stream)
    data_path = fetch_gsgk(stock_code, data_root)
    print(f"saved gsgk raw JSON: {data_path}", file=output_stream)
    return 0


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
        if args.command == "fetch-gsgk":
            data_path = fetch_gsgk(args.stock_code, args.data_root)
            print(f"saved gsgk raw JSON: {data_path}", file=output_stream)
            return 0
        if args.command == "ui":
            run_ui(args.data_root, input_func=input_func, output=output_stream)
            return 0
    except TqlexError as exc:
        print(f"error: {exc}", file=error_stream)
        return 1

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
