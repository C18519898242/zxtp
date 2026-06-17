from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "fetch-gsgk":
            data_path = fetch_gsgk(args.stock_code, args.data_root)
            print(f"saved gsgk raw JSON: {data_path}")
            return 0
    except TqlexError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
