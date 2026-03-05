"""
Command-line interface for fw-utils.

Usage::

    python -m fw_utils [--sysfs PATH] [--json] [--guid GUID]

Or, after installation::

    fw-list [options]
"""

import argparse
import json
import sys

from .scanner import FireWireScanner
from .rom import read_config_rom


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="fw-list",
        description="List FireWire (IEEE 1394) devices detected on this system.",
    )
    parser.add_argument(
        "--sysfs",
        metavar="PATH",
        default=None,
        help="Override sysfs bus path (default: /sys/bus/firewire/devices).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output device information as JSON.",
    )
    parser.add_argument(
        "--guid",
        metavar="GUID",
        default=None,
        help="Show only the device with this GUID.",
    )
    parser.add_argument(
        "--rom",
        action="store_true",
        default=False,
        help="Include parsed Configuration ROM entries.",
    )
    return parser


def _format_devices(devices, include_rom=False, as_json=False):
    """Return a formatted string for *devices*."""
    if not devices:
        return "No FireWire devices found."

    records = []
    for dev in devices:
        rec = dev.to_dict()
        if include_rom:
            rom_entries = read_config_rom(dev)
            rec["config_rom"] = [
                {
                    "key_type": kt,
                    "key_spec": ks,
                    "value": f"0x{v:06X}",
                    "name": nm,
                }
                for kt, ks, v, nm in rom_entries
            ]
        records.append(rec)

    if as_json:
        return json.dumps(records, indent=2)

    lines = []
    for rec in records:
        lines.append(f"Device: {rec['name']}")
        lines.append(f"  GUID        : {rec['guid'] or 'N/A'}")
        lines.append(f"  Vendor ID   : {rec['vendor_id'] or 'N/A'}")
        lines.append(f"  Vendor name : {rec['vendor_name'] or 'N/A'}")
        lines.append(f"  Model ID    : {rec['model_id'] or 'N/A'}")
        lines.append(f"  Model name  : {rec['model_name'] or 'N/A'}")
        lines.append(f"  Node ID     : {rec['node_id'] or 'N/A'}")
        lines.append(f"  Generation  : {rec['generation']}")
        if rec.get("units"):
            lines.append(f"  Units       : {', '.join(rec['units'])}")
        if "config_rom" in rec:
            lines.append("  Config ROM  :")
            for entry in rec["config_rom"]:
                lines.append(
                    f"    {entry['name']:<26} {entry['value']}"
                )
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv=None):
    """Entry point for the ``fw-list`` command."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    scanner = FireWireScanner(sysfs_path=args.sysfs)

    if args.guid:
        device = scanner.find_by_guid(args.guid)
        devices = [device] if device else []
    else:
        devices = scanner.list_devices()

    print(_format_devices(devices, include_rom=args.rom, as_json=args.json))
    return 0


if __name__ == "__main__":
    sys.exit(main())
