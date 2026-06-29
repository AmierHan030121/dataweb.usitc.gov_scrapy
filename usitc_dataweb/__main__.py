from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from .browser_downloader import BrowserDownloader, BrowserSettings
from .config import load_config
from .tasks import build_tasks, task_output_path
from .xlsx import count_xlsx_rows


RECOVERABLE_ERROR_TEXT = (
    "Due to current high volume",
    "Timed out waiting",
    "Access Denied",
    "net::ERR_TIMED_OUT",
    "net::ERR_NETWORK_CHANGED",
    "0 Unknown Error",
    "Unknown Error",
    "Download failed",
    "Page.goto",
)


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

        browser_session: BrowserSession | None = None
        if not config.dry_run:
            browser_session = BrowserSession(
                BrowserSettings(
                    download_dir=config.output_dir,
                    headless=config.headless,
                    navigation_timeout_seconds=config.timeout_seconds,
                    download_timeout_seconds=config.download_timeout_seconds,
                    form_settle_seconds=config.form_settle_seconds,
                )
            )

        try:
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
                    assert browser_session is not None
                    actual_commodity_level = _download_with_browser_recovery(
                        browser_session,
                        task=task,
                        output_path=output_path,
                        max_attempts=config.retries,
                        cooldown_seconds=config.browser_cooldown_seconds,
                        restart_browser_on_error=config.restart_browser_on_error,
                        on_retry=lambda attempt, exc, task=task, output_path=output_path: _record_retry(
                            writer,
                            manifest_file,
                            task,
                            output_path,
                            attempt,
                            exc,
                        ),
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
            if browser_session is not None:
                browser_session.close()

    return 0


def _replace_config(config, **changes):
    values = {field: getattr(config, field) for field in config.__dataclass_fields__}
    values.update(changes)
    return type(config)(**values)


class BrowserSession:
    def __init__(self, settings: BrowserSettings) -> None:
        self.settings = settings
        self._cm: BrowserDownloader | None = None
        self._downloader: BrowserDownloader | None = None

    def get(self) -> BrowserDownloader:
        if self._downloader is None:
            self._cm = BrowserDownloader(self.settings)
            self._downloader = self._cm.__enter__()
        return self._downloader

    def restart(self) -> None:
        self.close()

    def close(self) -> None:
        if self._cm is not None:
            self._cm.__exit__(None, None, None)
        self._cm = None
        self._downloader = None


def _download_with_browser_recovery(
    browser_session,
    *,
    task,
    output_path: Path,
    max_attempts: int,
    cooldown_seconds: float,
    restart_browser_on_error: bool,
    sleep: Callable[[float], None] = time.sleep,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> str:
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            return browser_session.get().download_task(task, output_path)
        except Exception as exc:
            if not _is_recoverable_download_error(exc) or attempt >= attempts:
                raise
            if on_retry is not None:
                on_retry(attempt, exc)
            if restart_browser_on_error:
                browser_session.restart()
            if cooldown_seconds > 0:
                print(f"Recoverable DataWeb error; waiting {cooldown_seconds:g}s before retry {attempt + 1}/{attempts}...")
                sleep(cooldown_seconds)
    raise RuntimeError("unreachable download retry state")


def _is_recoverable_download_error(exc: Exception) -> bool:
    message = str(exc)
    return any(text in message for text in RECOVERABLE_ERROR_TEXT)


def _record_retry(writer, manifest_file, task, output_path: Path, attempt: int, exc: Exception) -> None:
    _write_manifest(writer, "retry", task, output_path, None, f"attempt {attempt} failed: {exc}")
    manifest_file.flush()
    print(f"RETRY {task.filename} attempt {attempt}: {exc}", file=sys.stderr)


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
