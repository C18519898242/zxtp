from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .tqlex import TqlexError


DEFAULT_CONFIG_PATH = Path("config.toml")
DEFAULT_DATA_ROOT = Path("data")


def resolve_data_root(
    cli_data_root: Path | None,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> Path:
    if cli_data_root is not None:
        return cli_data_root

    config = load_config(config_path)
    configured_root = read_data_root(config)
    if configured_root is None:
        return DEFAULT_DATA_ROOT
    if configured_root.is_absolute():
        return configured_root
    return config_path.parent / configured_root


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    try:
        with config_path.open("rb") as config_file:
            config = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        raise TqlexError(f"invalid config.toml: {exc}") from exc
    if not isinstance(config, dict):
        raise TqlexError("config.toml must contain a TOML table")
    return config


def read_data_root(config: dict[str, Any]) -> Path | None:
    data_config = config.get("data", {})
    if data_config is None:
        return None
    if not isinstance(data_config, dict):
        raise TqlexError("config.toml [data] must be a table")

    data_root = data_config.get("root")
    if data_root is None:
        return None
    if not isinstance(data_root, str) or not data_root.strip():
        raise TqlexError("config.toml data.root must be a non-empty string")
    return Path(data_root)
