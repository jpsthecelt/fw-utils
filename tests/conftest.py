"""Shared test fixtures and helpers for fw_utils tests."""

import os
import tempfile
import struct

import pytest


@pytest.fixture
def tmp_sysfs(tmp_path):
    """
    Create a minimal fake sysfs tree under *tmp_path*.

    Returns the path to the ``devices`` directory.
    """
    devices_dir = tmp_path / "devices"
    devices_dir.mkdir()
    return devices_dir


def make_device_dir(devices_dir, name, attrs=None):
    """
    Create a fake device directory under *devices_dir*.

    :param devices_dir: :class:`pathlib.Path` to the devices dir.
    :param name:        Device name (e.g. ``"fw0"``).
    :param attrs:       Dict of attribute name → value pairs to write.
    :returns:           :class:`pathlib.Path` of the created directory.
    """
    dev_dir = devices_dir / name
    dev_dir.mkdir()
    for attr, value in (attrs or {}).items():
        (dev_dir / attr).write_text(str(value) + "\n")
    return dev_dir


def make_config_rom(bus_info_extra_quadlets=0, root_dir_entries=None):
    """
    Build a minimal well-formed Configuration ROM byte string.

    :param bus_info_extra_quadlets: Extra quadlets in the bus info block.
    :param root_dir_entries:        List of raw 32-bit quadlet ints for the
                                    root directory body.
    :returns:                       :class:`bytes`
    """
    if root_dir_entries is None:
        root_dir_entries = []

    # Bus info block header quadlet.  The length field stores the number of
    # quadlets that *follow* the header (i.e. extra quadlets only).
    bus_info_length = bus_info_extra_quadlets
    bus_info_header = (bus_info_length << 24)
    bus_info_quads = [bus_info_header] + [0] * bus_info_extra_quadlets

    # Root directory header quadlet (length in upper 16 bits)
    root_dir_length = len(root_dir_entries)
    root_dir_header = (root_dir_length << 16)
    root_dir_quads = [root_dir_header] + list(root_dir_entries)

    all_quads = bus_info_quads + root_dir_quads
    return struct.pack(f">{len(all_quads)}I", *all_quads)
