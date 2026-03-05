"""Tests for fw_utils.device."""

import pytest
from tests.conftest import make_device_dir
from fw_utils.device import FireWireDevice


class TestFireWireDeviceAttrs:
    """FireWireDevice reads attributes from the sysfs directory."""

    def test_guid(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0x00a0450012345678"})
        dev = FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0"))
        assert dev.guid == "0x00a0450012345678"

    def test_vendor_and_model(self, tmp_sysfs):
        make_device_dir(
            tmp_sysfs,
            "fw0",
            {
                "vendor": "0x00a045",
                "model": "0x000001",
                "vendor_name": "ACME Corp",
                "model_name": "Widgetron 3000",
            },
        )
        dev = FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0"))
        assert dev.vendor_id == "0x00a045"
        assert dev.model_id == "0x000001"
        assert dev.vendor_name == "ACME Corp"
        assert dev.model_name == "Widgetron 3000"

    def test_node_id_and_generation(self, tmp_sysfs):
        make_device_dir(
            tmp_sysfs, "fw0", {"node_id": "0xffc0", "generation": "5"}
        )
        dev = FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0"))
        assert dev.node_id == "0xffc0"
        assert dev.generation == 5

    def test_missing_attr_returns_none(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {})
        dev = FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0"))
        assert dev.guid is None
        assert dev.vendor_id is None

    def test_generation_invalid_returns_none(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"generation": "not-a-number"})
        dev = FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0"))
        assert dev.generation is None

    def test_units_detected(self, tmp_sysfs):
        dev_dir = make_device_dir(tmp_sysfs, "fw0", {})
        (dev_dir / "fw0.0").mkdir()
        (dev_dir / "fw0.1").mkdir()
        dev = FireWireDevice("fw0", sysfs_path=str(dev_dir))
        assert dev.units == ["fw0.0", "fw0.1"]

    def test_units_empty_when_none(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {})
        dev = FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0"))
        assert dev.units == []

    def test_repr_contains_name(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {})
        dev = FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0"))
        assert "fw0" in repr(dev)

    def test_to_dict_keys(self, tmp_sysfs):
        make_device_dir(tmp_sysfs, "fw0", {"guid": "0xaabbccdd11223344"})
        dev = FireWireDevice("fw0", sysfs_path=str(tmp_sysfs / "fw0"))
        d = dev.to_dict()
        expected_keys = {
            "name", "guid", "vendor_id", "model_id",
            "vendor_name", "model_name", "node_id", "generation", "units",
        }
        assert set(d.keys()) == expected_keys
        assert d["name"] == "fw0"
        assert d["guid"] == "0xaabbccdd11223344"
