from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

@dataclass(frozen=True)
class RuntimeConfig:
    year: int
    months: tuple[int, ...]
    flows: tuple[str, ...]
    measures: dict[str, tuple[str, ...] | str]
    output_dir: Path
    payload_dir: Path
    log_dir: Path
    split_strategy: str
    hts2_chapters: tuple[str, ...]
    skip_existing: bool
    dry_run: bool
    timeout_seconds: int
    download_timeout_seconds: int
    headless: bool
    retries: int
    retry_sleep_seconds: float
    row_warning_threshold: int
    save_payloads: bool


def _as_tuple(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


def load_config(path: str | Path) -> RuntimeConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    measures_raw = raw.get("measures") or {}
    measures: dict[str, tuple[str, ...] | str] = {}
    for flow_key, value in measures_raw.items():
        if isinstance(value, str):
            measures[str(flow_key)] = value
        else:
            measures[str(flow_key)] = tuple(str(item) for item in _as_tuple(value))

    split_raw = raw.get("split") or {}
    dirs_raw = raw.get("directories") or {}
    runtime_raw = raw.get("runtime") or {}

    hts2_chapters = tuple(str(ch).zfill(2) for ch in _as_tuple(split_raw.get("hts2_chapters")))

    months = tuple(int(month) for month in _as_tuple(raw.get("months")))
    if not months:
        raise ValueError("Config must provide at least one month.")
    for month in months:
        if month < 1 or month > 12:
            raise ValueError(f"Invalid month: {month}")

    flows = tuple(str(flow) for flow in _as_tuple(raw.get("flows")))
    if not flows:
        raise ValueError("Config must provide at least one flow.")

    return RuntimeConfig(
        year=int(raw["year"]),
        months=months,
        flows=flows,
        measures=measures,
        output_dir=Path(dirs_raw.get("downloads", "downloads")),
        payload_dir=Path(dirs_raw.get("payloads", "output/payloads")),
        log_dir=Path(dirs_raw.get("logs", "logs")),
        split_strategy=str(split_raw.get("strategy", "none")).lower(),
        hts2_chapters=hts2_chapters,
        skip_existing=bool(runtime_raw.get("skip_existing", True)),
        dry_run=bool(runtime_raw.get("dry_run", False)),
        timeout_seconds=int(runtime_raw.get("timeout_seconds", 240)),
        download_timeout_seconds=int(runtime_raw.get("download_timeout_seconds", 240)),
        headless=bool(runtime_raw.get("headless", False)),
        retries=int(runtime_raw.get("retries", 2)),
        retry_sleep_seconds=float(runtime_raw.get("retry_sleep_seconds", 15)),
        row_warning_threshold=int(runtime_raw.get("row_warning_threshold", 300000)),
        save_payloads=bool(runtime_raw.get("save_payloads", True)),
    )
