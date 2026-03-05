"""Tests for fw_utils.scanner."""

import pytest
from tests.conftest import make_device_dir
from fw_utils.scanner import FireWireScanner
from fw_utils.device import FireWireDevice


class TestFireWireScannerListDevices:
    """FireWireScanner.list_devices() discovers devices in sysfs."""

    def test_empty_directory(self, tmp_sysfs):
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        assert scanner.list_devices() == []

    def test_nonexistent_directory(self, tmp_path):
        scanner = FireWireScanner(sysfs_path=str(tmp_path / "noexist"))
        assert scanner.list_devices() == []

    def test_single_device(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0x0011223344556677"})
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        devices = scanner.list_devices()
        assert len(devices) == 1
        assert devices[0].name == "fw0"

    def test_multiple_devices_sorted(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw2", {})
        make_device_dir(tmp_sysfs, "fw0", {})
        make_device_dir(tmp_sysfs, "fw1", {})
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        names = [d.name for d in scanner.list_devices()]
        assert names == ["fw0", "fw1", "fw2"]

    def test_unit_dirs_excluded(self, tmp_sysfs):
        """Unit subdirectories (fw0.0, fw0.1, …) must not appear as devices."""
        make_device_dir(tmp_sysfs, "fw0", {})
        make_device_dir(tmp_sysfs, "fw0.0", {})
        make_device_dir(tmp_sysfs, "fw0.1", {})
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        devices = scanner.list_devices()
        assert len(devices) == 1
        assert devices[0].name == "fw0"

    def test_non_fw_entries_excluded(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {})
        make_device_dir(tmp_sysfs, "somethingelse", {})
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        assert len(scanner.list_devices()) == 1

    def test_returns_firewiredevice_instances(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {})
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        for dev in scanner.list_devices():
            assert isinstance(dev, FireWireDevice)


class TestFireWireScannerFindByGuid:
    """FireWireScanner.find_by_guid() locates a specific device."""

    def test_found(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0x0011223344556677"})
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        dev = scanner.find_by_guid("0x0011223344556677")
        assert dev is not None
        assert dev.name == "fw0"

    def test_case_insensitive(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0xAABBCCDD11223344"})
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        assert scanner.find_by_guid("0xaabbccdd11223344") is not None

    def test_without_0x_prefix(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0x0011223344556677"})
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        assert scanner.find_by_guid("0011223344556677") is not None

    def test_not_found_returns_none(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0x0011223344556677"})
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        assert scanner.find_by_guid("0xDEADBEEFDEADBEEF") is None

    def test_empty_guid_returns_none(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0x0011223344556677"})
        scanner = FireWireScanner(sysfs_path=str(tmp_sysfs))
        assert scanner.find_by_guid("") is None
