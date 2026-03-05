#!/usr/bin/env python3
"""
Unit tests for fw_devices.py
"""

import io
import os
import sys
import tempfile
import unittest

# Allow importing from parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fw_devices


def _make_fake_sysfs(tmp_dir, devices):
    """
    Create a fake sysfs tree under tmp_dir.

    devices is a list of (name, attrs_dict) where attrs_dict maps
    attribute name to string value.
    """
    fw_dir = os.path.join(tmp_dir, "firewire", "devices")
    os.makedirs(fw_dir, exist_ok=True)
    for name, attrs in devices:
        dev_dir = os.path.join(fw_dir, name)
        os.makedirs(dev_dir, exist_ok=True)
        for attr, value in attrs.items():
            with open(os.path.join(dev_dir, attr), "w") as f:
                f.write(value + "\n")
    return fw_dir


class TestGetDevices(unittest.TestCase):
    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = os.path.join(tmp, "firewire", "devices")
            os.makedirs(fw_dir)
            devices = fw_devices.get_devices(fw_dir)
            self.assertEqual(devices, [])

    def test_nonexistent_path(self):
        devices = fw_devices.get_devices("/nonexistent/path/that/does/not/exist")
        self.assertEqual(devices, [])

    def test_single_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(
                tmp,
                [
                    (
                        "fw0",
                        {
                            "guid": "0x00112233aabbccdd",
                            "vendor_name": "ACME Corp",
                            "model_name": "FW Camera",
                        },
                    )
                ],
            )
            devices = fw_devices.get_devices(fw_dir)
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]["name"], "fw0")
            self.assertEqual(devices[0]["guid"], "0x00112233aabbccdd")
            self.assertEqual(devices[0]["vendor_name"], "ACME Corp")
            self.assertEqual(devices[0]["model_name"], "FW Camera")

    def test_multiple_devices_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(
                tmp,
                [
                    ("fw1", {"guid": "0x0000000100000001"}),
                    ("fw0", {"guid": "0x0000000000000001"}),
                    ("fw0.0", {"guid": "0x0000000000000001"}),
                ],
            )
            devices = fw_devices.get_devices(fw_dir)
            names = [d["name"] for d in devices]
            self.assertEqual(names, ["fw0", "fw0.0", "fw1"])

    def test_missing_attrs_return_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(tmp, [("fw0", {})])
            devices = fw_devices.get_devices(fw_dir)
            self.assertEqual(len(devices), 1)
            self.assertIsNone(devices[0]["guid"])
            self.assertIsNone(devices[0]["vendor_name"])


class TestFormatDevice(unittest.TestCase):
    def _make_info(self, **kwargs):
        base = {
            "name": "fw0",
            "path": "/sys/bus/firewire/devices/fw0",
            "guid": None,
            "vendor_name": None,
            "model_name": None,
            "vendor": None,
            "model": None,
            "specifier_id": None,
            "version": None,
            "hardware_version": None,
        }
        base.update(kwargs)
        return base

    def test_basic_format(self):
        info = self._make_info(guid="0xaabbccdd", vendor_name="Vendor", model_name="Model")
        line = fw_devices.format_device(info)
        self.assertIn("fw0", line)
        self.assertIn("0xaabbccdd", line)
        self.assertIn("Vendor", line)
        self.assertIn("Model", line)

    def test_fallback_to_vendor_id(self):
        info = self._make_info(vendor="0x001234")
        line = fw_devices.format_device(info)
        self.assertIn("0x001234", line)

    def test_verbose_shows_path(self):
        info = self._make_info(path="/sys/bus/firewire/devices/fw0")
        line = fw_devices.format_device(info, verbose=True)
        self.assertIn("/sys/bus/firewire/devices/fw0", line)

    def test_unknown_fallback(self):
        info = self._make_info()
        line = fw_devices.format_device(info)
        self.assertIn("unknown", line)


class TestListDevices(unittest.TestCase):
    def test_no_devices(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = os.path.join(tmp, "empty")
            os.makedirs(fw_dir)
            buf = io.StringIO()
            fw_devices.list_devices(sysfs_path=fw_dir, output=buf)
            self.assertIn("No FireWire devices found", buf.getvalue())

    def test_list_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(
                tmp,
                [
                    ("fw0", {"guid": "0x1234567890abcdef", "vendor_name": "TestVendor"}),
                ],
            )
            buf = io.StringIO()
            fw_devices.list_devices(sysfs_path=fw_dir, output=buf)
            output = buf.getvalue()
            self.assertIn("fw0", output)
            self.assertIn("0x1234567890abcdef", output)
            self.assertIn("TestVendor", output)


if __name__ == "__main__":
    unittest.main()
