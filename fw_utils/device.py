"""
FireWire device representation.

Models a single FireWire (IEEE 1394) device as discovered through
the Linux kernel sysfs interface (/sys/bus/firewire/devices/).
"""

import os
import re


class FireWireDevice:
    """Represents a single FireWire device."""

    SYSFS_BUS_PATH = "/sys/bus/firewire/devices"

    def __init__(self, name, sysfs_path=None):
        """
        Initialise a FireWireDevice.

        :param name:       Device name as it appears in sysfs (e.g. ``fw0``).
        :param sysfs_path: Full path to the sysfs entry.  Defaults to
                           ``/sys/bus/firewire/devices/<name>``.
        """
        self.name = name
        self.sysfs_path = sysfs_path or os.path.join(self.SYSFS_BUS_PATH, name)

    # ------------------------------------------------------------------
    # Low-level sysfs helpers
    # ------------------------------------------------------------------

    def _read_attr(self, attr):
        """Return the stripped content of a sysfs attribute file, or None."""
        path = os.path.join(self.sysfs_path, attr)
        try:
            with open(path) as fh:
                return fh.read().strip()
        except OSError:
            return None

    # ------------------------------------------------------------------
    # Device properties
    # ------------------------------------------------------------------

    @property
    def guid(self):
        """64-bit GUID (as a hex string), or ``None`` if unavailable."""
        return self._read_attr("guid")

    @property
    def vendor_id(self):
        """24-bit vendor ID (as a hex string), or ``None`` if unavailable."""
        return self._read_attr("vendor")

    @property
    def model_id(self):
        """24-bit model ID (as a hex string), or ``None`` if unavailable."""
        return self._read_attr("model")

    @property
    def vendor_name(self):
        """Human-readable vendor name string, or ``None``."""
        return self._read_attr("vendor_name")

    @property
    def model_name(self):
        """Human-readable model name string, or ``None``."""
        return self._read_attr("model_name")

    @property
    def node_id(self):
        """Current bus node ID (as a hex string), or ``None``."""
        return self._read_attr("node_id")

    @property
    def generation(self):
        """Bus generation number (int), or ``None``."""
        val = self._read_attr("generation")
        if val is not None:
            try:
                return int(val, 0)
            except ValueError:
                pass
        return None

    @property
    def units(self):
        """
        List of unit subdirectory names for this device.

        FireWire devices may expose multiple *units* (functional blocks).
        Returns an empty list when none are present or the device path is
        inaccessible.
        """
        try:
            entries = os.listdir(self.sysfs_path)
        except OSError:
            return []
        unit_re = re.compile(r"^" + re.escape(self.name) + r"\.\d+$")
        return sorted(e for e in entries if unit_re.match(e))

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self):
        return (
            f"FireWireDevice(name={self.name!r}, guid={self.guid!r}, "
            f"vendor={self.vendor_name!r}, model={self.model_name!r})"
        )

    def to_dict(self):
        """Return a plain dictionary representation of this device."""
        return {
            "name": self.name,
            "guid": self.guid,
            "vendor_id": self.vendor_id,
            "model_id": self.model_id,
            "vendor_name": self.vendor_name,
            "model_name": self.model_name,
            "node_id": self.node_id,
            "generation": self.generation,
            "units": self.units,
        }
