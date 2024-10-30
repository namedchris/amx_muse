import unittest
import sys
from unittest.mock import MagicMock

# mock mojo import
sys.modules["mojo"] = MagicMock()

import index


class TestIndexFunctions(unittest.TestCase):
    def test_prune_devices(self):
        test_set = index.prune_devices(("a", "b", "c"), ("b", "c"))
        self.assertSetEqual(test_set, set("a"))

    def test_parse_device_id(self):
        device_id = "nsb-123-switcher-1"
        expected = "nsb-123"
        result = index.parse_device_id(device_id)
        self.assertEqual(expected, result)

    def test_populate_rooms(self):
        devices = (
            "nsb-123-switcher-1",
            "nsb-123-display-1",
            "nsb-124-switcher-1",
        )
        expected = set(("nsb-123", "nsb-124"))
        result = index.populate_rooms(devices)
        self.assertSetEqual(result, expected)