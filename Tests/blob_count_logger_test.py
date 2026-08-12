import csv
from pathlib import Path
import tempfile
import unittest

from plugins.loggers.blob_count_logger import (
    BlobCountLogger,
    BlobCountRecordKey,
)


class _Region:
    def get_blob_count(self):
        return 1


class _Node:
    contained_blobs = [object()]


class _Graph:
    def __init__(self):
        self.region_dict = {"A": _Region()}
        self.node_dict = {"A//home": _Node()}
        self.count = 0

    def get_blob_count(self):
        return self.count


class _TimeStatus:
    cycle_length = 24


class _Simulation:
    def __init__(self):
        self.env_graph = _Graph()
        self.time_status = _TimeStatus()
        self.experiment_name = "blob-count-test"


class BlobCountLoggerLifecycleTest(unittest.TestCase):
    def test_configuration_counts_csv_and_metadata_survive_loading(self):
        simulation = _Simulation()
        logger = BlobCountLogger({BlobCountRecordKey.BLOB_COUNT_GLOBAL})
        logger.load_plugin(simulation)

        self.assertEqual(
            {BlobCountRecordKey.BLOB_COUNT_GLOBAL}, logger.data_to_record
        )
        self.assertEqual({"A"}, set(logger.blob_region_count))
        self.assertEqual({"A//home"}, set(logger.blob_node_count))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            logger.base_path = str(root) + "/"
            logger.data_frames_path = str(root / "data_frames") + "/"
            logger.setup_logger()
            for count in (3, 7, 5):
                simulation.env_graph.count = count
                logger.log_simulation_step()
            logger.stop_logger()

            global_csv = root / "data_frames" / "blob_count_global.csv"
            self.assertTrue(global_csv.is_file())
            with global_csv.open(
                encoding="utf-8-sig", newline=""
            ) as stream:
                rows = list(csv.DictReader(stream, delimiter=";"))
            self.assertEqual([3, 7, 5], [int(row["Blob Count"]) for row in rows])
            self.assertFalse((root / "data_frames" / "blob_count_region.csv").exists())
            self.assertFalse((root / "data_frames" / "blob_count_node.csv").exists())

        metadata = {}
        returned = logger.add_max_blob_count_to_metadata(metadata)
        self.assertIs(metadata, returned)
        self.assertEqual(7, metadata["max_blob_count"])


if __name__ == "__main__":
    unittest.main()
