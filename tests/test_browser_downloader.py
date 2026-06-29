import unittest

from usitc_dataweb.browser_downloader import choose_commodity_level, run_with_retries, wait_if_needed
from usitc_dataweb.__main__ import _download_success_message, _sleep_between_tasks


class BrowserDownloaderTests(unittest.TestCase):
    def test_choose_commodity_level_prefers_requested_level(self):
        selected = choose_commodity_level("10", ["2", "4", "6", "8", "10"])

        self.assertEqual("10", selected)

    def test_choose_commodity_level_falls_back_to_hts6(self):
        selected = choose_commodity_level("10", ["2", "4", "6"])

        self.assertEqual("6", selected)

    def test_choose_commodity_level_fails_when_no_usable_level_exists(self):
        with self.assertRaisesRegex(ValueError, "HTS-10 nor HTS-6"):
            choose_commodity_level("10", ["2", "4"])

    def test_run_with_retries_retries_transient_failures(self):
        attempts = []

        def operation():
            attempts.append(1)
            if len(attempts) < 3:
                raise RuntimeError("temporary")
            return "ok"

        result = run_with_retries(operation, retries=2, retry_sleep_seconds=0)

        self.assertEqual("ok", result)
        self.assertEqual(3, len(attempts))

    def test_run_with_retries_raises_last_error_after_retries(self):
        attempts = []

        def operation():
            attempts.append(1)
            raise RuntimeError(f"temporary {len(attempts)}")

        with self.assertRaisesRegex(RuntimeError, "temporary 3"):
            run_with_retries(operation, retries=2, retry_sleep_seconds=0)

        self.assertEqual(3, len(attempts))

    def test_download_success_message_records_commodity_level_fallback(self):
        message = _download_success_message(
            requested_commodity_level="10",
            actual_commodity_level="6",
            rows=100,
            row_warning_threshold=300000,
        )

        self.assertEqual("commodity level fallback: requested HTS-10, used HTS-6", message)

    def test_download_success_message_combines_row_warning(self):
        message = _download_success_message(
            requested_commodity_level="10",
            actual_commodity_level="6",
            rows=300001,
            row_warning_threshold=300000,
        )

        self.assertEqual(
            "commodity level fallback: requested HTS-10, used HTS-6; "
            "row count 300001 exceeds configured threshold",
            message,
        )

    def test_wait_if_needed_calls_sleep_for_positive_seconds(self):
        calls = []

        wait_if_needed(5, sleep=calls.append)

        self.assertEqual([5], calls)

    def test_wait_if_needed_skips_zero_seconds(self):
        calls = []

        wait_if_needed(0, sleep=calls.append)

        self.assertEqual([], calls)

    def test_sleep_between_tasks_skips_last_task(self):
        calls = []

        _sleep_between_tasks(
            current_index=3,
            total_tasks=3,
            seconds=60,
            sleep=calls.append,
        )

        self.assertEqual([], calls)

    def test_sleep_between_tasks_waits_before_next_task(self):
        calls = []

        _sleep_between_tasks(
            current_index=2,
            total_tasks=3,
            seconds=60,
            sleep=calls.append,
        )

        self.assertEqual([60], calls)


if __name__ == "__main__":
    unittest.main()
