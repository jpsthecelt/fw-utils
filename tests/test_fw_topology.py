#!/usr/bin/env python3
"""
Unit tests for fw_topology.py
"""

import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fw_topology


def _make_fake_sysfs(tmp_dir, devices):
    fw_dir = os.path.join(tmp_dir, "firewire", "devices")
    os.makedirs(fw_dir, exist_ok=True)
    for name, attrs in devices:
        dev_dir = os.path.join(fw_dir, name)
        os.makedirs(dev_dir, exist_ok=True)
        for attr, value in attrs.items():
            with open(os.path.join(dev_dir, attr), "w") as f:
                f.write(value + "\n")
    return fw_dir


class TestGetNodes(unittest.TestCase):
    def test_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = os.path.join(tmp, "firewire", "devices")
            os.makedirs(fw_dir)
            cards = fw_topology.get_nodes(fw_dir)
            self.assertEqual(cards, {})

    def test_nonexistent_path(self):
        cards = fw_topology.get_nodes("/nonexistent/does/not/exist")
        self.assertEqual(cards, {})

    def test_local_node_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(
                tmp, [("fw0", {"guid": "0xAABBCCDD00112233"})]
            )
            cards = fw_topology.get_nodes(fw_dir)
            self.assertIn(0, cards)
            node = cards[0][0]
            self.assertEqual(node["name"], "fw0")
            self.assertTrue(node["is_local"])
            self.assertIsNone(node["node_index"])

    def test_remote_nodes_grouped_by_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(
                tmp,
                [
                    ("fw0", {"guid": "0x0000000000000001"}),
                    ("fw0.0", {"guid": "0x0000000000000002"}),
                    ("fw0.1", {"guid": "0x0000000000000003"}),
                    ("fw1", {"guid": "0x0000000000000004"}),
                ],
            )
            cards = fw_topology.get_nodes(fw_dir)
            self.assertIn(0, cards)
            self.assertIn(1, cards)
            card0_names = {n["name"] for n in cards[0]}
            self.assertEqual(card0_names, {"fw0", "fw0.0", "fw0.1"})
            card1_names = {n["name"] for n in cards[1]}
            self.assertEqual(card1_names, {"fw1"})

    def test_non_fw_entries_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(
                tmp,
                [
                    ("fw0", {}),
                    ("scsi0", {}),  # non-firewire device
                ],
            )
            cards = fw_topology.get_nodes(fw_dir)
            # scsi0 should be ignored
            all_names = [n["name"] for nodes in cards.values() for n in nodes]
            self.assertNotIn("scsi0", all_names)

    def test_node_index_set_for_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(
                tmp, [("fw0.3", {"guid": "0x0000000000000001"})]
            )
            cards = fw_topology.get_nodes(fw_dir)
            node = cards[0][0]
            self.assertFalse(node["is_local"])
            self.assertEqual(node["node_index"], 3)


class TestRenderTopology(unittest.TestCase):
    def test_no_buses(self):
        buf = io.StringIO()
        fw_topology.render_topology({}, output=buf)
        self.assertIn("No FireWire buses found", buf.getvalue())

    def test_renders_bus_label(self):
        cards = {
            0: [
                {
                    "name": "fw0",
                    "card": 0,
                    "node_index": None,
                    "is_local": True,
                    "guid": "0xAABB",
                    "vendor_name": "VendorA",
                    "model_name": "ModelA",
                    "vendor": None,
                    "model": None,
                }
            ]
        }
        buf = io.StringIO()
        fw_topology.render_topology(cards, output=buf)
        output = buf.getvalue()
        self.assertIn("Bus fw0:", output)
        self.assertIn("fw0", output)
        self.assertIn("(local)", output)
        self.assertIn("0xAABB", output)

    def test_last_node_uses_corner_connector(self):
        cards = {
            0: [
                {
                    "name": "fw0",
                    "card": 0,
                    "node_index": None,
                    "is_local": True,
                    "guid": "0xA",
                    "vendor_name": None,
                    "model_name": None,
                    "vendor": None,
                    "model": None,
                },
            ]
        }
        buf = io.StringIO()
        fw_topology.render_topology(cards, output=buf)
        self.assertIn("└──", buf.getvalue())

    def test_multiple_nodes_uses_tee_and_corner(self):
        cards = {
            0: [
                {
                    "name": "fw0",
                    "card": 0,
                    "node_index": None,
                    "is_local": True,
                    "guid": "0xA",
                    "vendor_name": None,
                    "model_name": None,
                    "vendor": None,
                    "model": None,
                },
                {
                    "name": "fw0.0",
                    "card": 0,
                    "node_index": 0,
                    "is_local": False,
                    "guid": "0xB",
                    "vendor_name": None,
                    "model_name": None,
                    "vendor": None,
                    "model": None,
                },
            ]
        }
        buf = io.StringIO()
        fw_topology.render_topology(cards, output=buf)
        output = buf.getvalue()
        self.assertIn("├──", output)
        self.assertIn("└──", output)


if __name__ == "__main__":
    unittest.main()
