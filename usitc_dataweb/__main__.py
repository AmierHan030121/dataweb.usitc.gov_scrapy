from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from .client import DataWebClient, DataWebMaintenanceError
from .config import load_config
from .payload import build_payload
from .tasks import build_tasks, task_output_path
from .xlsx import count_xlsx_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download USITC DataWeb monthly trade data.")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to YAML config.")
    parser.add_argument("--dry-run", action="store_true", help="Only write payloads; do not call dataExport.")
    parser.add_argument("--no-split", action="store_true", help="Disable HTS2 chunking for this run.")
    parser.add_argument("--limit", type=int, default=None, help="Run at most N tasks, useful for smoke tests.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if args.dry_run:
        config = _replace_config(config, dry_run=True)
    if args.no_split:
        config = _replace_config(config, split_strategy="none")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.payload_dir.mkdir(parents=True, exist_ok=True)
    config.log_dir.mkdir(parents=True, exist_ok=True)

    tasks = build_tasks(config)
    if args.limit is not None:
        tasks = tasks[: args.limit]

    manifest_path = config.log_dir / "manifest.csv"
    write_header = not manifest_path.exists()
    with manifest_path.open("a", encoding="utf-8", newline="") as manifest_file:
        writer = csv.DictWriter(
            manifest_file,
            fieldnames=[
                "timestamp",
                "status",
                "flow",
                "measure",
                "yyyymm",
                "hts_prefix",
                "path",
                "rows",
                "message",
            ],
        )
        if write_header:
            writer.writeheader()

        client: DataWebClient | None = None
        if not config.dry_run:
            client = DataWebClient(
                proxy=config.proxy,
                timeout_seconds=config.timeout_seconds,
                retries=config.retries,
                retry_sleep_seconds=config.retry_sleep_seconds,
            )
            global_vars = client.warmup()
            print(f"Connected. DataWeb current month: {global_vars.get('currentYear')}-{global_vars.get('currentMonth')}")

        for index, task in enumerate(tasks, start=1):
            output_path = task_output_path(config.output_dir, task)
            payload_path = config.payload_dir / output_path.with_suffix(".json").name
            error_path = config.log_dir / output_path.with_suffix(".error.json").name
            payload = build_payload(
                flow=task.flow,
                measure=task.measure,
                year=task.year,
                month=task.month,
                commodity_level=task.commodity_level,
                hts_prefix=task.hts_prefix,
            )
            if config.save_payloads:
                payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            if config.dry_run:
                print(f"[{index}/{len(tasks)}] dry-run {task.filename}")
                _write_manifest(writer, "dry_run", task, output_path, None, "payload written")
                manifest_file.flush()
                continue

            if output_path.exists() and config.skip_existing:
                print(f"[{index}/{len(tasks)}] skip existing {output_path}")
                _write_manifest(writer, "skipped", task, output_path, None, "existing file")
                manifest_file.flush()
                continue

            output_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"[{index}/{len(tasks)}] downloading {task.filename}")
            try:
                assert client is not None
                content = client.download_excel(payload, error_path=error_path)
                output_path.write_bytes(content)
                rows = count_xlsx_rows(output_path)
                message = ""
                if rows is not None and rows > config.row_warning_threshold:
                    message = f"row count {rows} exceeds configured threshold"
                _write_manifest(writer, "ok", task, output_path, rows, message)
                manifest_file.flush()
            except DataWebMaintenanceError as exc:
                _write_manifest(writer, "maintenance", task, output_path, None, str(exc))
                manifest_file.flush()
                print(f"Stopped: {exc}")
                return 2
            except Exception as exc:
                _write_manifest(writer, "error", task, output_path, None, str(exc))
                manifest_file.flush()
                print(f"ERROR {task.filename}: {exc}", file=sys.stderr)
                continue

    return 0


def _replace_config(config, **changes):
    values = {field: getattr(config, field) for field in config.__dataclass_fields__}
    values.update(changes)
    return type(config)(**values)


def _write_manifest(writer, status, task, path: Path, rows: int | None, message: str) -> None:
    writer.writerow(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "status": status,
            "flow": task.flow.key,
            "measure": task.measure.label,
            "yyyymm": task.yyyymm,
            "hts_prefix": task.hts_prefix or "",
            "path": str(path),
            "rows": "" if rows is None else rows,
            "message": message,
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
