import unittest

from usitc_dataweb.client import DataWebClient


class DataWebClientTests(unittest.TestCase):
    def test_session_does_not_inherit_system_proxy_settings(self):
        client = DataWebClient()

        self.assertFalse(client.session.trust_env)


if __name__ == "__main__":
    unittest.main()
