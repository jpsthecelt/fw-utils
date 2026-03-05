#!/usr/bin/env python3
"""
fw_info.py - Show detailed info and config ROM for a Linux FireWire device.

Reads data from /sys/bus/firewire/devices/<name>/ and parses the
config_rom binary file when available.
"""

import os
import sys
import struct
import argparse

SYSFS_FW_PATH = "/sys/bus/firewire/devices"

# Config ROM key types (IEEE 1212)
KEY_TYPE_IMMEDIATE = 0x00
KEY_TYPE_OFFSET = 0x01
KEY_TYPE_LEAF = 0x02
KEY_TYPE_DIRECTORY = 0x03

KEY_TYPE_NAMES = {
    KEY_TYPE_IMMEDIATE: "immediate",
    KEY_TYPE_OFFSET: "offset",
    KEY_TYPE_LEAF: "leaf",
    KEY_TYPE_DIRECTORY: "directory",
}

# Well-known key IDs
KEY_IDS = {
    0x01: "VENDOR",
    0x02: "HARDWARE_VERSION",
    0x03: "SPECIFIER_ID",
    0x04: "VERSION",
    0x0C: "NODE_CAPABILITIES",
    0x0D: "UNIT_DIRECTORY",
    0x11: "TEXTUAL_DESCRIPTOR",
    0x12: "BUS_DEPENDENT_INFO",
    0x13: "VENDOR_INFO",
    0x17: "MODEL",
    0x81: "TEXTUAL_DESCRIPTOR",
    0xD1: "UNIT_DIRECTORY",
}


def read_sysfs_attr(device_path, attr):
    """Read a sysfs attribute file and return its stripped content, or None."""
    attr_path = os.path.join(device_path, attr)
    try:
        with open(attr_path, "r") as f:
            return f.read().strip()
    except OSError:
        return None


def read_config_rom(device_path):
    """Read the raw config_rom bytes, or None if unavailable."""
    rom_path = os.path.join(device_path, "config_rom")
    try:
        with open(rom_path, "rb") as f:
            return f.read()
    except OSError:
        return None


def parse_config_rom(data):
    """
    Parse a FireWire config ROM binary blob.

    Returns a list of (key_type, key_id, value) tuples from the root directory.
    Only the root directory entries are decoded; sub-directories are noted but
    not recursed.
    """
    if len(data) < 4:
        return []

    # Bus info block: first quadlet of info_length
    bus_info_len = data[0] * 4  # info_length in quadlets → bytes
    if bus_info_len == 0:
        # Minimal ROM
        return []

    # Root directory starts after bus info block + first quadlet
    root_dir_offset = 4 + bus_info_len
    if root_dir_offset + 4 > len(data):
        return []

    dir_length_q = struct.unpack_from(">H", data, root_dir_offset)[0]
    dir_length = dir_length_q * 4  # in bytes

    entries = []
    for i in range(dir_length // 4):
        entry_offset = root_dir_offset + 4 + i * 4
        if entry_offset + 4 > len(data):
            break
        (quad,) = struct.unpack_from(">I", data, entry_offset)
        key_type = (quad >> 30) & 0x03
        key_id = (quad >> 24) & 0x3F
        value = quad & 0x00FFFFFF
        entries.append((key_type, key_id, value))

    return entries


def format_rom_entry(key_type, key_id, value):
    """Format a single config ROM entry as a human-readable string."""
    type_name = KEY_TYPE_NAMES.get(key_type, f"type{key_type}")
    id_name = KEY_IDS.get(key_id, f"0x{key_id:02X}")
    return f"  [{type_name}] {id_name} = 0x{value:06X}"


def print_device_info(name, sysfs_path=SYSFS_FW_PATH, output=sys.stdout):
    """Print full info for a named FireWire device."""
    device_path = os.path.join(sysfs_path, name)
    if not os.path.isdir(device_path):
        print(f"Error: device '{name}' not found in {sysfs_path}", file=sys.stderr)
        return False

    print(f"Device: {name}", file=output)
    print(f"  Path: {device_path}", file=output)

    attrs = [
        "guid",
        "vendor",
        "vendor_name",
        "model",
        "model_name",
        "specifier_id",
        "version",
        "hardware_version",
    ]
    for attr in attrs:
        val = read_sysfs_attr(device_path, attr)
        if val is not None:
            print(f"  {attr}: {val}", file=output)

    rom = read_config_rom(device_path)
    if rom:
        print(f"\n  Config ROM ({len(rom)} bytes):", file=output)
        # Hex dump (4 bytes per line)
        for i in range(0, len(rom), 4):
            chunk = rom[i : i + 4]
            hex_str = " ".join(f"{b:02x}" for b in chunk)
            print(f"    {i:04x}: {hex_str}", file=output)

        print("\n  Root directory entries:", file=output)
        entries = parse_config_rom(rom)
        if entries:
            for kt, kid, val in entries:
                print(format_rom_entry(kt, kid, val), file=output)
        else:
            print("  (unable to parse root directory)", file=output)
    else:
        print("\n  Config ROM: not available", file=output)

    return True


def list_device_names(sysfs_path=SYSFS_FW_PATH):
    """Return sorted list of FireWire device names in sysfs."""
    if not os.path.isdir(sysfs_path):
        return []
    return sorted(
        name
        for name in os.listdir(sysfs_path)
        if os.path.isdir(os.path.join(sysfs_path, name))
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Show detailed info and config ROM for a Linux FireWire device."
    )
    parser.add_argument(
        "device",
        nargs="?",
        metavar="DEVICE",
        help="Device name (e.g. fw0). If omitted, info for all devices is shown.",
    )
    parser.add_argument(
        "--sysfs",
        default=SYSFS_FW_PATH,
        metavar="PATH",
        help=f"sysfs firewire devices path (default: {SYSFS_FW_PATH})",
    )
    args = parser.parse_args(argv)

    if args.device:
        names = [args.device]
    else:
        names = list_device_names(args.sysfs)
        if not names:
            print("No FireWire devices found.", file=sys.stderr)
            sys.exit(1)

    first = True
    for name in names:
        if not first:
            print()
        print_device_info(name, sysfs_path=args.sysfs)
        first = False


if __name__ == "__main__":
    main()
