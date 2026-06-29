import unittest

from usitc_dataweb.browser_downloader import choose_commodity_level, run_with_retries, wait_if_needed
from usitc_dataweb.__main__ import (
    _download_success_message,
    _download_with_browser_recovery,
    _is_recoverable_download_error,
    _sleep_between_tasks,
)


class FakeBrowserSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.download_calls = 0
        self.restart_calls = 0

    def get(self):
        return self

    def download_task(self, task, output_path):
        self.download_calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def restart(self):
        self.restart_calls += 1


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

    def test_recoverable_download_restarts_browser_and_retries_same_task(self):
        session = FakeBrowserSession(
            [
                RuntimeError("Due to current high volume"),
                RuntimeError("net::ERR_TIMED_OUT"),
                "10",
            ]
        )
        sleeps = []
        retry_messages = []

        result = _download_with_browser_recovery(
            session,
            task=object(),
            output_path=object(),
            max_attempts=8,
            cooldown_seconds=60,
            restart_browser_on_error=True,
            sleep=sleeps.append,
            on_retry=lambda attempt, exc: retry_messages.append((attempt, str(exc))),
        )

        self.assertEqual("10", result)
        self.assertEqual(3, session.download_calls)
        self.assertEqual(2, session.restart_calls)
        self.assertEqual([60, 60], sleeps)
        self.assertEqual([1, 2], [attempt for attempt, _ in retry_messages])

    def test_recoverable_download_stops_after_max_attempts(self):
        session = FakeBrowserSession([RuntimeError("Timed out waiting")] * 8)
        sleeps = []

        with self.assertRaisesRegex(RuntimeError, "Timed out waiting"):
            _download_with_browser_recovery(
                session,
                task=object(),
                output_path=object(),
                max_attempts=8,
                cooldown_seconds=60,
                restart_browser_on_error=True,
                sleep=sleeps.append,
            )

        self.assertEqual(8, session.download_calls)
        self.assertEqual(7, session.restart_calls)
        self.assertEqual([60] * 7, sleeps)

    def test_non_recoverable_download_error_is_not_retried(self):
        session = FakeBrowserSession([ValueError("Unknown measure")])

        with self.assertRaisesRegex(ValueError, "Unknown measure"):
            _download_with_browser_recovery(
                session,
                task=object(),
                output_path=object(),
                max_attempts=8,
                cooldown_seconds=60,
                restart_browser_on_error=True,
                sleep=lambda seconds: None,
            )

        self.assertEqual(1, session.download_calls)
        self.assertEqual(0, session.restart_calls)

    def test_recoverable_error_detection_covers_dataweb_volume_message(self):
        self.assertTrue(_is_recoverable_download_error(RuntimeError("Due to current high volume")))
        self.assertTrue(_is_recoverable_download_error(RuntimeError("0 Unknown Error")))
        self.assertTrue(_is_recoverable_download_error(RuntimeError("net::ERR_NETWORK_CHANGED")))
        self.assertFalse(_is_recoverable_download_error(ValueError("Unknown measure")))


if __name__ == "__main__":
    unittest.main()
