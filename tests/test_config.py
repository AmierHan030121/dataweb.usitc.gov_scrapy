import unittest

from usitc_dataweb.config import load_config


class RuntimeConfigTests(unittest.TestCase):
    def test_default_config_uses_browser_download_without_hts_split(self):
        config = load_config("configs/default.yaml")

        self.assertEqual("none", config.split_strategy)
        self.assertEqual((), config.hts2_chapters)
        self.assertEqual(360, config.download_timeout_seconds)
        self.assertFalse(config.headless)
        self.assertFalse(config.save_payloads)
        self.assertEqual(2, config.retries)
        self.assertEqual(30, config.retry_sleep_seconds)


if __name__ == "__main__":
    unittest.main()
