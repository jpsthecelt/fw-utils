"""Tests for fw_utils.rom."""

import struct
import pytest
from tests.conftest import make_config_rom, make_device_dir
from fw_utils.rom import (
    parse_config_rom,
    read_config_rom,
    KEY_TYPE_IMMEDIATE,
    KEY_SPEC_VENDOR,
    KEY_SPEC_MODEL,
)
from fw_utils.device import FireWireDevice


class TestParseConfigRom:
    """parse_config_rom() correctly decodes ROM bytes."""

    def test_empty_bytes_returns_empty_list(self):
        # An empty byte string has no quadlets → no entries
        assert parse_config_rom(b"") == []

    def test_raises_on_unaligned_data(self):
        with pytest.raises(ValueError, match="multiple of 4"):
            parse_config_rom(b"\x00\x01")

    def test_vendor_and_model_entries(self):
        # Encode a Vendor_ID (key=0x03, immediate) and Model_ID (key=0x17)
        vendor_quad = (((KEY_TYPE_IMMEDIATE << 6) | KEY_SPEC_VENDOR) << 24) | 0x00A045
        model_quad = (((KEY_TYPE_IMMEDIATE << 6) | KEY_SPEC_MODEL) << 24) | 0x000001
        rom_bytes = make_config_rom(root_dir_entries=[vendor_quad, model_quad])
        entries = parse_config_rom(rom_bytes)
        assert len(entries) == 2

        kt0, ks0, val0, name0 = entries[0]
        assert ks0 == KEY_SPEC_VENDOR
        assert val0 == 0x00A045
        assert name0 == "Vendor_ID"

        kt1, ks1, val1, name1 = entries[1]
        assert ks1 == KEY_SPEC_MODEL
        assert val1 == 0x000001
        assert name1 == "Model_ID"

    def test_bus_info_block_skipped(self):
        """Entries in the bus info block must not appear in the result."""
        # bus_info_extra_quadlets=1 means the bus info block has 2 quadlets
        rom_bytes = make_config_rom(bus_info_extra_quadlets=1, root_dir_entries=[])
        entries = parse_config_rom(rom_bytes)
        assert entries == []

    def test_unknown_key_uses_hex_fallback(self):
        # Use an unusual key that has no human-readable name
        unknown_key = 0x3F  # key_type=0, key_spec=0x3F
        unknown_quad = (unknown_key << 24) | 0xABCDEF
        rom_bytes = make_config_rom(root_dir_entries=[unknown_quad])
        entries = parse_config_rom(rom_bytes)
        assert len(entries) == 1
        _, _, val, name = entries[0]
        assert val == 0xABCDEF
        assert name.startswith("0x")

    def test_truncated_root_dir_handled_gracefully(self):
        """If the root dir claims more entries than data available, stop early."""
        # Root directory length = 5, but we provide only 1 entry quadlet
        vendor_quad = (((KEY_TYPE_IMMEDIATE << 6) | KEY_SPEC_VENDOR) << 24) | 0x001234
        # Manually craft ROM with inflated length
        bus_info = struct.pack(">I", 0)                # bus info length = 0 (no extra quadlets)
        root_dir_header = struct.pack(">I", 5 << 16)   # claims 5 entries
        root_dir_entry = struct.pack(">I", vendor_quad)
        rom_bytes = bus_info + root_dir_header + root_dir_entry
        entries = parse_config_rom(rom_bytes)
        assert len(entries) == 1  # only 1 entry actually present


class TestReadConfigRom:
    """read_config_rom() reads and parses the config_rom sysfs file."""

    def test_reads_from_device_path(self, tmp_sysfs):
        vendor_quad = (((KEY_TYPE_IMMEDIATE << 6) | KEY_SPEC_VENDOR) << 24) | 0x00A045
        rom_bytes = make_config_rom(root_dir_entries=[vendor_quad])
        dev_dir = make_device_dir(tmp_sysfs, "fw0", {})
        (dev_dir / "config_rom").write_bytes(rom_bytes)

        dev = FireWireDevice("fw0", sysfs_path=str(dev_dir))
        entries = read_config_rom(dev)
        assert len(entries) == 1
        _, ks, val, name = entries[0]
        assert ks == KEY_SPEC_VENDOR
        assert val == 0x00A045

    def test_missing_config_rom_returns_empty(self, tmp_sysfs):
        dev_dir = make_device_dir(tmp_sysfs, "fw0", {})
        dev = FireWireDevice("fw0", sysfs_path=str(dev_dir))
        assert read_config_rom(dev) == []
