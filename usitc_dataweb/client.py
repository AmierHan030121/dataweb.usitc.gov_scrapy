from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from .config import ProxyConfig
from .constants import PRESENTATION_URL, SERVICE_BASE_URL


class DataWebError(RuntimeError):
    pass


class DataWebMaintenanceError(DataWebError):
    pass


class DataWebClient:
    def __init__(
        self,
        *,
        proxy: ProxyConfig,
        timeout_seconds: int = 240,
        retries: int = 2,
        retry_sleep_seconds: float = 15,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.retry_sleep_seconds = retry_sleep_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Origin": PRESENTATION_URL,
                "Referer": f"{PRESENTATION_URL}/",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
                ),
            }
        )
        if proxy.enabled:
            os.environ["HTTP_PROXY"] = proxy.http_proxy
            os.environ["HTTPS_PROXY"] = proxy.https_proxy
            os.environ["ALL_PROXY"] = proxy.all_proxy
            self.session.proxies.update(
                {
                    "http": proxy.http_proxy,
                    "https": proxy.https_proxy,
                }
            )

    def warmup(self) -> dict[str, Any]:
        self.session.get(
            f"{PRESENTATION_URL}/trade/search/Import/HTS",
            timeout=self.timeout_seconds,
        ).raise_for_status()
        global_vars = self.get_global_vars()
        xsrf = self._get_xsrf_token()
        if xsrf:
            self.session.headers.update({"X-XSRF-TOKEN": xsrf})
        self.session.headers.update(
            {
                "Cache-control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
        return global_vars

    def get_global_vars(self) -> dict[str, Any]:
        response = self.session.get(
            f"{SERVICE_BASE_URL}/query/getGlobalVars",
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def download_excel(self, payload: dict[str, Any], error_path: Path | None = None) -> bytes:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                return self._download_excel_once(payload, error_path)
            except DataWebMaintenanceError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.retry_sleep_seconds)
        raise DataWebError(f"Download failed after retries: {last_error}") from last_error

    def _download_excel_once(
        self,
        payload: dict[str, Any],
        error_path: Path | None = None,
    ) -> bytes:
        response = self.session.post(
            f"{SERVICE_BASE_URL}/report2/dataExport",
            json=payload,
            timeout=self.timeout_seconds,
        )

        content_type = response.headers.get("content-type", "")
        text = response.text
        if response.status_code != 200:
            self._write_error(error_path, response)
            if "Site under maintenance" in text or "undergoing maintenance" in text:
                raise DataWebMaintenanceError("USITC DataWeb download endpoint is under maintenance.")
            raise DataWebError(f"HTTP {response.status_code} from dataExport.")

        if "application/json" not in content_type:
            self._write_error(error_path, response)
            if "Site under maintenance" in text or "undergoing maintenance" in text:
                raise DataWebMaintenanceError("USITC DataWeb download endpoint is under maintenance.")
            raise DataWebError(f"Expected JSON response, got {content_type!r}.")

        data = response.json()
        if data.get("problemSql"):
            self._write_error(error_path, response)
            raise DataWebError(f"DataWeb problemSql: {data.get('problemSql')}")
        if "dto" not in data:
            self._write_error(error_path, response)
            raise DataWebError(f"DataWeb response has no dto field: {sorted(data.keys())}")
        return base64.b64decode(data["dto"])

    def _get_xsrf_token(self) -> str:
        for cookie in self.session.cookies:
            if cookie.name == "XSRF-TOKEN":
                return cookie.value
        return ""

    @staticmethod
    def _write_error(error_path: Path | None, response: requests.Response) -> None:
        if error_path is None:
            return
        error_path.parent.mkdir(parents=True, exist_ok=True)
        body = response.text
        payload = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body[:200000],
        }
        error_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
