from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

from .browser_downloader import BrowserDownloader, BrowserSettings, run_with_retries
from .config import load_config
from .tasks import build_tasks, task_output_path
from .xlsx import count_xlsx_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download USITC DataWeb monthly trade data.")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to YAML config.")
    parser.add_argument("--dry-run", action="store_true", help="List tasks; do not open browser or download.")
    parser.add_argument("--limit", type=int, default=None, help="Run at most N tasks, useful for smoke tests.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if args.dry_run:
        config = _replace_config(config, dry_run=True)

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

        downloader_cm: BrowserDownloader | None = None
        downloader: BrowserDownloader | None = None
        if not config.dry_run:
            downloader_cm = BrowserDownloader(
                BrowserSettings(
                    download_dir=config.output_dir,
                    headless=config.headless,
                    navigation_timeout_seconds=config.timeout_seconds,
                    download_timeout_seconds=config.download_timeout_seconds,
                    form_settle_seconds=config.form_settle_seconds,
                )
            )

        try:
            if downloader_cm is not None:
                downloader = downloader_cm.__enter__()
            for index, task in enumerate(tasks, start=1):
                output_path = task_output_path(config.output_dir, task)

                if config.dry_run:
                    print(f"[{index}/{len(tasks)}] dry-run {task.filename}")
                    _write_manifest(writer, "dry_run", task, output_path, None, "task listed")
                    manifest_file.flush()
                    continue

                if output_path.exists() and config.skip_existing:
                    print(f"[{index}/{len(tasks)}] skip existing {output_path}")
                    _write_manifest(writer, "skipped", task, output_path, None, "existing file")
                    manifest_file.flush()
                    continue

                output_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"[{index}/{len(tasks)}] browser download {task.filename}")
                try:
                    assert downloader is not None
                    actual_commodity_level = run_with_retries(
                        lambda: downloader.download_task(task, output_path),
                        retries=config.retries,
                        retry_sleep_seconds=config.retry_sleep_seconds,
                    )
                    rows = count_xlsx_rows(output_path)
                    message = _download_success_message(
                        requested_commodity_level=task.commodity_level,
                        actual_commodity_level=actual_commodity_level,
                        rows=rows,
                        row_warning_threshold=config.row_warning_threshold,
                    )
                    _write_manifest(writer, "ok", task, output_path, rows, message)
                    manifest_file.flush()
                except Exception as exc:
                    _write_manifest(writer, "error", task, output_path, None, str(exc))
                    manifest_file.flush()
                    print(f"ERROR {task.filename}: {exc}", file=sys.stderr)
                    continue
                finally:
                    _sleep_between_tasks(
                        current_index=index,
                        total_tasks=len(tasks),
                        seconds=config.task_sleep_seconds,
                    )
        finally:
            if downloader_cm is not None:
                downloader_cm.__exit__(None, None, None)

    return 0


def _replace_config(config, **changes):
    values = {field: getattr(config, field) for field in config.__dataclass_fields__}
    values.update(changes)
    return type(config)(**values)


def _download_success_message(
    *,
    requested_commodity_level: str,
    actual_commodity_level: str,
    rows: int | None,
    row_warning_threshold: int,
) -> str:
    messages: list[str] = []
    if actual_commodity_level != requested_commodity_level:
        messages.append(
            f"commodity level fallback: requested HTS-{requested_commodity_level}, "
            f"used HTS-{actual_commodity_level}"
        )
    if rows is not None and rows > row_warning_threshold:
        messages.append(f"row count {rows} exceeds configured threshold")
    return "; ".join(messages)


def _sleep_between_tasks(
    *,
    current_index: int,
    total_tasks: int,
    seconds: float,
    sleep=time.sleep,
) -> None:
    if current_index < total_tasks and seconds > 0:
        print(f"Waiting {seconds:g}s before next task...")
        sleep(seconds)


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
