import unittest

from usitc_dataweb.config import load_config
from usitc_dataweb.tasks import build_tasks, task_output_path


class DownloadTaskTests(unittest.TestCase):
    def test_default_config_builds_one_full_download_per_flow_measure(self):
        config = load_config("configs/default.yaml")

        tasks = build_tasks(config)

        self.assertEqual(23, len(tasks))
        self.assertTrue(all(task.hts_prefix is None for task in tasks))
        self.assertIn("IMP_General_Customs_202604.xlsx", {task.filename for task in tasks})
        self.assertIn("BAL_TradeBalance_FASMinusGenCustoms_202604.xlsx", {task.filename for task in tasks})
        self.assertFalse(any("_HTS" in task.filename for task in tasks))

    def test_task_output_path_groups_by_flow_and_month(self):
        config = load_config("configs/sample_small.yaml")
        task = build_tasks(config)[0]

        path = task_output_path(config.output_dir, task)

        self.assertEqual("downloads\\import_general\\202604\\IMP_General_CIF_202604.xlsx", str(path))


if __name__ == "__main__":
    unittest.main()
