#!/usr/bin/env python3
"""
fw_devices.py - List connected Linux FireWire (IEEE 1394) devices.

Reads device information from the Linux sysfs FireWire subsystem at
/sys/bus/firewire/devices/.
"""

import os
import sys
import argparse

SYSFS_FW_PATH = "/sys/bus/firewire/devices"


def read_sysfs_attr(device_path, attr):
    """Read a sysfs attribute file and return its stripped content, or None."""
    attr_path = os.path.join(device_path, attr)
    try:
        with open(attr_path, "r") as f:
            return f.read().strip()
    except OSError:
        return None


def get_devices(sysfs_path=SYSFS_FW_PATH):
    """Return a list of FireWire device info dicts found in sysfs."""
    devices = []
    if not os.path.isdir(sysfs_path):
        return devices

    for name in sorted(os.listdir(sysfs_path)):
        device_path = os.path.join(sysfs_path, name)
        if not os.path.isdir(device_path):
            continue

        # Only list fw nodes (e.g. fw0, fw1) and units (fw0.0, fw0.1, ...)
        info = {
            "name": name,
            "path": device_path,
            "guid": read_sysfs_attr(device_path, "guid"),
            "vendor_name": read_sysfs_attr(device_path, "vendor_name"),
            "model_name": read_sysfs_attr(device_path, "model_name"),
            "vendor": read_sysfs_attr(device_path, "vendor"),
            "model": read_sysfs_attr(device_path, "model"),
            "specifier_id": read_sysfs_attr(device_path, "specifier_id"),
            "version": read_sysfs_attr(device_path, "version"),
            "hardware_version": read_sysfs_attr(device_path, "hardware_version"),
        }
        devices.append(info)

    return devices


def format_device(info, verbose=False):
    """Format a device info dict as a human-readable string."""
    lines = []
    name = info["name"]
    guid = info["guid"] or "unknown"
    vendor = info["vendor_name"] or info["vendor"] or "unknown"
    model = info["model_name"] or info["model"] or "unknown"

    lines.append(f"{name}: GUID={guid}  Vendor={vendor}  Model={model}")
    if verbose:
        for key in ("specifier_id", "version", "hardware_version", "path"):
            val = info.get(key)
            if val:
                lines.append(f"  {key}: {val}")
    return "\n".join(lines)


def list_devices(sysfs_path=SYSFS_FW_PATH, verbose=False, output=sys.stdout):
    """Print all detected FireWire devices to output."""
    devices = get_devices(sysfs_path)
    if not devices:
        print("No FireWire devices found.", file=output)
        return

    for info in devices:
        print(format_device(info, verbose=verbose), file=output)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="List connected Linux FireWire devices."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show additional device attributes"
    )
    parser.add_argument(
        "--sysfs",
        default=SYSFS_FW_PATH,
        metavar="PATH",
        help=f"sysfs firewire devices path (default: {SYSFS_FW_PATH})",
    )
    args = parser.parse_args(argv)
    list_devices(sysfs_path=args.sysfs, verbose=args.verbose)


if __name__ == "__main__":
    main()
