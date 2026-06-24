from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import PRESENTATION_URL
from .tasks import DownloadTask


@dataclass(frozen=True)
class BrowserSettings:
    download_dir: Path
    headless: bool
    navigation_timeout_seconds: int
    download_timeout_seconds: int


class BrowserDownloadError(RuntimeError):
    pass


def choose_commodity_level(requested_level: str, available_levels: list[str]) -> str:
    if requested_level in available_levels:
        return requested_level
    if "6" in available_levels:
        return "6"
    raise ValueError("DataWeb page supports neither HTS-10 nor HTS-6 for this trade flow.")


def run_with_retries(operation, *, retries: int, retry_sleep_seconds: float):
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(retry_sleep_seconds)
    assert last_error is not None
    raise last_error


class BrowserDownloader:
    def __init__(self, settings: BrowserSettings) -> None:
        self.settings = settings
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    def __enter__(self) -> "BrowserDownloader":
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError as exc:
            raise BrowserDownloadError(
                "Playwright is not installed. Run: python -m pip install -r requirements.txt "
                "and then python -m playwright install chromium"
            ) from exc

        self._timeout_error = PlaywrightTimeoutError
        self.settings.download_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.settings.headless)
        self._context = self._browser.new_context(
            accept_downloads=True,
            locale="en-US",
            viewport={"width": 1536, "height": 1000},
        )
        timeout_ms = self.settings.navigation_timeout_seconds * 1000
        self._context.set_default_timeout(timeout_ms)
        self._context.set_default_navigation_timeout(timeout_ms)
        self._page = self._context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def download_task(self, task: DownloadTask, output_path: Path) -> str:
        page = self._require_page()
        page.goto(f"{PRESENTATION_URL}/trade/search/Import/HTS", wait_until="domcontentloaded")
        self._dismiss_alerts(page)
        self._set_step_1(page, task)
        self._set_step_2(page, task)
        self._set_step_3(page)
        actual_level = self._set_step_4(page, task)
        self._set_step_9(page)
        self._set_step_10(page)
        self._download(page, output_path)
        return actual_level

    def _require_page(self) -> Any:
        if self._page is None:
            raise BrowserDownloadError("BrowserDownloader must be used as a context manager.")
        return self._page

    def _dismiss_alerts(self, page: Any) -> None:
        self._remove_survey_overlays(page)
        for button in page.get_by_role("button", name="close").all():
            try:
                if button.is_visible():
                    button.click(timeout=1000)
            except Exception:
                continue
        self._remove_survey_overlays(page)

    def _remove_survey_overlays(self, page: Any) -> None:
        try:
            page.evaluate(
                """() => {
                    for (const selector of [
                        '.QSIWebResponsive',
                        '[id^="QSI"]',
                        '[class*="QSI"]',
                        'iframe[src*="qualtrics"]'
                    ]) {
                        document.querySelectorAll(selector).forEach((el) => el.remove());
                    }
                }"""
            )
        except Exception:
            return

    def _set_step_1(self, page: Any, task: DownloadTask) -> None:
        self._remove_survey_overlays(page)
        self._select_by_value(page, "tradeFlow", task.flow.trade_type)
        self._select_by_value(page, "classificationSystem", "HTS")

    def _set_step_2(self, page: Any, task: DownloadTask) -> None:
        self._remove_survey_overlays(page)
        self._select_data_measure(page, task.measure.title)
        self._select_by_value(page, "timeframesSelectedTab", "specificDateRange")
        self._fill_by_id(page, "startDate", f"{task.month:02d}/{task.year}")
        self._fill_by_id(page, "endDate", f"{task.month:02d}/{task.year}")
        self._select_by_value(page, "timeframeAggregation", "Monthly")

    def _set_step_3(self, page: Any) -> None:
        self._remove_survey_overlays(page)
        self._select_by_value(page, "countriesSelectedTab", "all")
        self._select_by_value(page, "countryAggregation", "Break Out Countries")

    def _set_step_4(self, page: Any, task: DownloadTask) -> str:
        self._remove_survey_overlays(page)
        self._select_by_value(page, "commoditiesSelectedTab", "all")
        self._select_by_value(page, "commodityAggregation", "Break Out Commodities")
        actual_level = self._select_commodity_aggregation_level(page, task.commodity_level)
        self._uncheck_if_present(page, "Show Details")
        return actual_level

    def _set_step_9(self, page: Any) -> None:
        self._remove_survey_overlays(page)
        self._set_checkbox_by_id(page, "rowsOptionsCombineData", True)
        self._set_checkbox_by_id(page, "exportRawData", True)

    def _set_step_10(self, page: Any) -> None:
        self._remove_survey_overlays(page)
        self._select_by_value(page, "unitConversion", "0")

    def _download(self, page: Any, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        download_timeout_ms = self.settings.download_timeout_seconds * 1000
        button = page.locator("button[aria-label='downloadData'], button:has-text('Download Data')").first
        try:
            self._remove_survey_overlays(page)
            with page.expect_download(timeout=download_timeout_ms) as download_info:
                button.click()
            download = download_info.value
            download.save_as(str(output_path))
        except self._timeout_error as exc:
            raise BrowserDownloadError(
                f"Timed out waiting {self.settings.download_timeout_seconds}s for browser download."
            ) from exc

    def _select_data_measure(self, page: Any, title: str) -> None:
        self._remove_survey_overlays(page)
        combobox = page.locator("ng-select[aria-label='dataToReport']").first
        combobox.click(force=True)
        self._remove_survey_overlays(page)
        self._click_option(page, title)

    def _click_option(self, page: Any, text: str) -> None:
        option = self._first_visible(
            page.get_by_role("option", name=text),
            page.locator("[role='option']").filter(has_text=text),
            page.locator(".ng-option, option, mat-option").filter(has_text=text),
            page.get_by_text(text, exact=True),
        )
        self._remove_survey_overlays(page)
        option.click(force=True)

    def _fill_by_id(self, page: Any, element_id: str, value: str) -> None:
        page.locator(f"#{element_id}").fill(value)

    def _select_by_value(self, page: Any, element_id: str, value: str) -> None:
        page.locator(f"#{element_id}").select_option(value=value)

    def _select_commodity_aggregation_level(self, page: Any, requested_level: str) -> str:
        locator = page.locator("#commodityAggregationLevel")
        values = locator.locator("option").evaluate_all(
            """options => options.map((option) => option.value).filter(Boolean)"""
        )
        actual_level = choose_commodity_level(requested_level, values)
        locator.select_option(value=actual_level)
        return actual_level

    def _check_if_present(self, page: Any, label: str) -> None:
        try:
            checkbox = self._first_visible(
                page.get_by_role("checkbox", name=label),
                page.locator("label").filter(has_text=label).locator("xpath=preceding::input[@type='checkbox'][1]"),
            )
        except BrowserDownloadError:
            return
        if not checkbox.is_checked():
            checkbox.check(force=True)

    def _uncheck_if_present(self, page: Any, label: str) -> None:
        try:
            checkbox = self._first_visible(
                page.get_by_role("checkbox", name=label),
                page.locator("label").filter(has_text=label).locator("xpath=preceding::input[@type='checkbox'][1]"),
            )
        except BrowserDownloadError:
            return
        if checkbox.is_checked():
            checkbox.uncheck(force=True)

    def _set_checkbox_by_id(self, page: Any, element_id: str, checked: bool) -> None:
        locator = page.locator(f"#{element_id}")
        if locator.count() == 0:
            return
        locator.evaluate(
            """(el, checked) => {
                el.checked = checked;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            checked,
        )

    def _first_visible(self, *locators: Any) -> Any:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            for locator in locators:
                try:
                    first = locator.first if hasattr(locator, "first") else locator
                    if first.count() > 0 and first.is_visible(timeout=250):
                        return first
                except Exception:
                    continue
            time.sleep(0.25)
        raise BrowserDownloadError("Could not find a visible DataWeb control.")
