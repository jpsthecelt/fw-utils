"""
FireWire device scanner.

Discovers FireWire devices by walking the Linux sysfs bus directory
``/sys/bus/firewire/devices/``.  Each ``fwX`` entry (where *X* is a
digit) that does **not** contain a dot is treated as a device node;
entries that *do* contain a dot (e.g. ``fw0.0``) are unit directories
and are skipped here (they are surfaced via :attr:`FireWireDevice.units`).
"""

import os
import re

from .device import FireWireDevice


class FireWireScanner:
    """Scans the system for FireWire devices."""

    SYSFS_BUS_PATH = "/sys/bus/firewire/devices"

    # Match device nodes like "fw0", "fw1", … but not unit dirs "fw0.0"
    _DEVICE_RE = re.compile(r"^fw\d+$")

    def __init__(self, sysfs_path=None):
        """
        :param sysfs_path: Override the sysfs bus path (useful for testing).
        """
        self.sysfs_path = sysfs_path or self.SYSFS_BUS_PATH

    def list_devices(self):
        """
        Return a list of :class:`FireWireDevice` objects found on the system.

        Returns an empty list when no FireWire bus is present or the sysfs
        directory does not exist.
        """
        try:
            entries = os.listdir(self.sysfs_path)
        except OSError:
            return []

        devices = []
        for name in sorted(entries):
            if self._DEVICE_RE.match(name):
                path = os.path.join(self.sysfs_path, name)
                devices.append(FireWireDevice(name, sysfs_path=path))
        return devices

    def find_by_guid(self, guid):
        """
        Return the :class:`FireWireDevice` whose GUID matches *guid*, or
        ``None`` if no match is found.

        :param guid: GUID string (case-insensitive, with or without ``0x``
                     prefix).
        """
        guid_norm = guid.lower().lstrip("0x") if guid else ""
        for dev in self.list_devices():
            dev_guid = dev.guid
            if dev_guid and dev_guid.lower().lstrip("0x") == guid_norm:
                return dev
        return None
