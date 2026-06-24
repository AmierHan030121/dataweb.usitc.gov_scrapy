import unittest

from usitc_dataweb.browser_downloader import run_with_retries


class BrowserDownloaderTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
