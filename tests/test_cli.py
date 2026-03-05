"""Tests for fw_utils.cli."""

import json
import pytest
from tests.conftest import make_device_dir, make_config_rom
from fw_utils.cli import main, _format_devices
from fw_utils.device import FireWireDevice


class TestFormatDevices:
    """_format_devices() produces correct human-readable and JSON output."""

    def test_no_devices_message(self):
        out = _format_devices([])
        assert "No FireWire devices found" in out

    def test_text_output_contains_name(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0xAABB", "vendor_name": "ACME"})
        dev = FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0"))
        out = _format_devices([dev])
        assert "fw0" in out
        assert "ACME" in out

    def test_json_output_is_valid(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0xAABB"})
        dev = FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0"))
        out = _format_devices([dev], as_json=True)
        parsed = json.loads(out)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "fw0"

    def test_json_multiple_devices(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {})
        make_device_dir(tmp_sysfs, "fw1", {})
        devs = [
            FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0")),
            FireWireDevice("fw1", sysfs_path=str(tmp_sysfs / "fw1")),
        ]
        out = _format_devices(devs, as_json=True)
        parsed = json.loads(out)
        assert len(parsed) == 2


class TestMainCLI:
    """main() end-to-end tests using a fake sysfs tree."""

    def test_no_devices(self, tmp_sysfs, capsys):
        ret = main(["--sysfs", str(tmp_sysfs)])
        assert ret == 0
        captured = capsys.readouterr()
        assert "No FireWire devices found" in captured.out

    def test_lists_device(self, tmp_sysfs, capsys):
        make_device_dir(
            tmp_sysfs, "fw0",
            {"guid": "0x001122334455", "vendor_name": "TestVendor"},
        )
        ret = main(["--sysfs", str(tmp_sysfs)])
        assert ret == 0
        captured = capsys.readouterr()
        assert "fw0" in captured.out
        assert "TestVendor" in captured.out

    def test_json_flag(self, tmp_sysfs, capsys):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0x001122334455"})
        ret = main(["--sysfs", str(tmp_sysfs), "--json"])
        assert ret == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed[0]["name"] == "fw0"

    def test_guid_filter_found(self, tmp_sysfs, capsys):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0x001122334455"})
        make_device_dir(tmp_sysfs, "fw1", {"guid": "0x009988776655"})
        ret = main(["--sysfs", str(tmp_sysfs), "--guid", "0x001122334455"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "fw0" in captured.out
        assert "fw1" not in captured.out

    def test_guid_filter_not_found(self, tmp_sysfs, capsys):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0x001122334455"})
        ret = main(["--sysfs", str(tmp_sysfs), "--guid", "0xDEADBEEFDEAD"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "No FireWire devices found" in captured.out

    def test_rom_flag(self, tmp_sysfs, capsys):
        from fw_utils.rom import KEY_TYPE_IMMEDIATE, KEY_SPEC_VENDOR
        vendor_quad = (
            ((KEY_TYPE_IMMEDIATE << 6 | KEY_SPEC_VENDOR) << 24) | 0x00A045
        )
        rom_bytes = make_config_rom(root_dir_entries=[vendor_quad])
        dev_dir = make_device_dir(tmp_sysfs, "fw0", {})
        (dev_dir / "config_rom").write_bytes(rom_bytes)
        ret = main(["--sysfs", str(tmp_sysfs), "--rom"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Vendor_ID" in captured.out
