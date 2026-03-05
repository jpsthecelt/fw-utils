#!/usr/bin/env python3
"""
Unit tests for fw_info.py
"""

import io
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fw_info


def _make_fake_sysfs(tmp_dir, devices):
    fw_dir = os.path.join(tmp_dir, "firewire", "devices")
    os.makedirs(fw_dir, exist_ok=True)
    for name, attrs, rom_bytes in devices:
        dev_dir = os.path.join(fw_dir, name)
        os.makedirs(dev_dir, exist_ok=True)
        for attr, value in attrs.items():
            with open(os.path.join(dev_dir, attr), "w") as f:
                f.write(value + "\n")
        if rom_bytes is not None:
            with open(os.path.join(dev_dir, "config_rom"), "wb") as f:
                f.write(rom_bytes)
    return fw_dir


def _build_config_rom(bus_info_quadlets, root_dir_entries):
    """
    Build a minimal config ROM binary.

    bus_info_quadlets: list of 4-byte ints for the bus info block
    root_dir_entries:  list of 4-byte ints for the root directory entries
    """
    # First quadlet: bus_info_length (in quadlets), crc_length, crc
    bus_info_len = len(bus_info_quadlets)
    # We write the header quadlet with info_length = bus_info_len
    header = struct.pack(">B", bus_info_len) + b"\x00\x00\x00"

    bus_info_bytes = b"".join(struct.pack(">I", q) for q in bus_info_quadlets)

    # Root directory: first quadlet = length in quadlets
    dir_len = len(root_dir_entries)
    root_dir = struct.pack(">HH", dir_len, 0)  # length, crc
    root_dir += b"".join(struct.pack(">I", e) for e in root_dir_entries)

    return header + bus_info_bytes + root_dir


class TestReadSysfsAttr(unittest.TestCase):
    def test_reads_existing_attr(self):
        with tempfile.TemporaryDirectory() as tmp:
            attr_path = os.path.join(tmp, "vendor")
            with open(attr_path, "w") as f:
                f.write("0x001234\n")
            val = fw_info.read_sysfs_attr(tmp, "vendor")
            self.assertEqual(val, "0x001234")

    def test_missing_attr_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            val = fw_info.read_sysfs_attr(tmp, "nonexistent")
            self.assertIsNone(val)


class TestReadConfigRom(unittest.TestCase):
    def test_reads_rom_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom_path = os.path.join(tmp, "config_rom")
            data = b"\x01\x02\x03\x04"
            with open(rom_path, "wb") as f:
                f.write(data)
            result = fw_info.read_config_rom(tmp)
            self.assertEqual(result, data)

    def test_missing_rom_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = fw_info.read_config_rom(tmp)
            self.assertIsNone(result)


class TestParseConfigRom(unittest.TestCase):
    def test_empty_data(self):
        self.assertEqual(fw_info.parse_config_rom(b""), [])
        self.assertEqual(fw_info.parse_config_rom(b"\x00\x00\x00"), [])

    def test_zero_bus_info_len(self):
        # info_length=0 means minimal ROM
        data = b"\x00\x00\x00\x00"
        self.assertEqual(fw_info.parse_config_rom(data), [])

    def test_parse_root_directory(self):
        # Build a ROM with 1 bus-info quadlet and 2 root-dir entries
        KEY_TYPE_IMMEDIATE = 0
        vendor_entry = (KEY_TYPE_IMMEDIATE << 30) | (0x01 << 24) | 0x001234
        model_entry = (KEY_TYPE_IMMEDIATE << 30) | (0x17 << 24) | 0x005678
        rom = _build_config_rom(
            bus_info_quadlets=[0xDEADBEEF],
            root_dir_entries=[vendor_entry, model_entry],
        )
        entries = fw_info.parse_config_rom(rom)
        self.assertEqual(len(entries), 2)
        # First entry: VENDOR immediate = 0x001234
        kt0, kid0, val0 = entries[0]
        self.assertEqual(kid0, 0x01)
        self.assertEqual(val0, 0x001234)
        # Second entry: MODEL immediate = 0x005678
        kt1, kid1, val1 = entries[1]
        self.assertEqual(kid1, 0x17)
        self.assertEqual(val1, 0x005678)

    def test_truncated_data_returns_partial(self):
        rom = _build_config_rom(
            bus_info_quadlets=[0x11111111],
            root_dir_entries=[0x01001234],
        )
        # Truncate to just after bus info block
        truncated = rom[:8]
        # Should return empty since root dir header is incomplete
        result = fw_info.parse_config_rom(truncated)
        self.assertIsInstance(result, list)


class TestFormatRomEntry(unittest.TestCase):
    def test_known_key(self):
        line = fw_info.format_rom_entry(0x00, 0x01, 0x001234)
        self.assertIn("VENDOR", line)
        self.assertIn("0x001234", line)
        self.assertIn("immediate", line)

    def test_unknown_key(self):
        line = fw_info.format_rom_entry(0x00, 0x7F, 0xABCDEF)
        self.assertIn("0x7F", line)
        self.assertIn("0xABCDEF", line)


class TestPrintDeviceInfo(unittest.TestCase):
    def test_nonexistent_device(self):
        buf = io.StringIO()
        result = fw_info.print_device_info(
            "fw_does_not_exist", sysfs_path="/nonexistent", output=buf
        )
        self.assertFalse(result)

    def test_prints_attrs(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(
                tmp,
                [
                    (
                        "fw0",
                        {"guid": "0xDEADBEEF12345678", "vendor_name": "MyVendor"},
                        None,
                    )
                ],
            )
            buf = io.StringIO()
            result = fw_info.print_device_info("fw0", sysfs_path=fw_dir, output=buf)
            self.assertTrue(result)
            output = buf.getvalue()
            self.assertIn("fw0", output)
            self.assertIn("0xDEADBEEF12345678", output)
            self.assertIn("MyVendor", output)

    def test_prints_config_rom(self):
        vendor_entry = (0x00 << 30) | (0x01 << 24) | 0x001111
        rom = _build_config_rom(
            bus_info_quadlets=[0xAAAABBBB],
            root_dir_entries=[vendor_entry],
        )
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(tmp, [("fw0", {}, rom)])
            buf = io.StringIO()
            fw_info.print_device_info("fw0", sysfs_path=fw_dir, output=buf)
            output = buf.getvalue()
            self.assertIn("Config ROM", output)
            self.assertIn("bytes", output)

    def test_no_rom_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(tmp, [("fw0", {}, None)])
            buf = io.StringIO()
            fw_info.print_device_info("fw0", sysfs_path=fw_dir, output=buf)
            output = buf.getvalue()
            self.assertIn("not available", output)


class TestListDeviceNames(unittest.TestCase):
    def test_nonexistent_path(self):
        self.assertEqual(fw_info.list_device_names("/nonexistent"), [])

    def test_returns_sorted_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            fw_dir = _make_fake_sysfs(
                tmp,
                [
                    ("fw1", {}, None),
                    ("fw0", {}, None),
                ],
            )
            names = fw_info.list_device_names(fw_dir)
            self.assertEqual(names, ["fw0", "fw1"])


if __name__ == "__main__":
    unittest.main()
