#!/usr/bin/env python3
"""
fw_topology.py - Display the Linux FireWire bus topology.

Reads node information from /sys/bus/firewire/devices/ and renders
a tree showing which nodes are on which bus (card).
"""

import os
import sys
import argparse
import re

SYSFS_FW_PATH = "/sys/bus/firewire/devices"


def read_sysfs_attr(device_path, attr):
    """Read a sysfs attribute file and return its stripped content, or None."""
    attr_path = os.path.join(device_path, attr)
    try:
        with open(attr_path, "r") as f:
            return f.read().strip()
    except OSError:
        return None


def get_nodes(sysfs_path=SYSFS_FW_PATH):
    """
    Return a dict mapping card index to a list of node dicts.

    Node names follow the pattern ``fw<card>`` (the local node) or
    ``fw<card>.<node>`` (remote nodes/units on that bus).
    """
    cards = {}
    if not os.path.isdir(sysfs_path):
        return cards

    # Regex for fw<N> (local node) and fw<N>.<M> (remote node or unit)
    node_re = re.compile(r"^fw(\d+)(?:\.(\d+))?$")

    for name in sorted(os.listdir(sysfs_path)):
        m = node_re.match(name)
        if not m:
            continue
        device_path = os.path.join(sysfs_path, name)
        if not os.path.isdir(device_path):
            continue

        card_idx = int(m.group(1))
        node_idx = m.group(2)  # None for local node

        info = {
            "name": name,
            "card": card_idx,
            "node_index": int(node_idx) if node_idx is not None else None,
            "is_local": node_idx is None,
            "guid": read_sysfs_attr(device_path, "guid"),
            "vendor_name": read_sysfs_attr(device_path, "vendor_name"),
            "model_name": read_sysfs_attr(device_path, "model_name"),
            "vendor": read_sysfs_attr(device_path, "vendor"),
            "model": read_sysfs_attr(device_path, "model"),
        }
        cards.setdefault(card_idx, []).append(info)

    return cards


def render_topology(cards, output=sys.stdout):
    """Render the bus topology as an ASCII tree to output."""
    if not cards:
        print("No FireWire buses found.", file=output)
        return

    for card_idx in sorted(cards):
        nodes = cards[card_idx]
        local_nodes = [n for n in nodes if n["is_local"]]
        remote_nodes = sorted(
            [n for n in nodes if not n["is_local"]],
            key=lambda n: n["node_index"] if n["node_index"] is not None else -1,
        )

        print(f"Bus fw{card_idx}:", file=output)
        all_nodes = local_nodes + remote_nodes
        for i, node in enumerate(all_nodes):
            is_last = i == len(all_nodes) - 1
            connector = "└──" if is_last else "├──"
            guid = node["guid"] or "unknown"
            vendor = node["vendor_name"] or node["vendor"] or "unknown"
            model = node["model_name"] or node["model"] or "unknown"
            label = "(local)" if node["is_local"] else ""
            print(
                f"  {connector} {node['name']} {label}  GUID={guid}"
                f"  Vendor={vendor}  Model={model}",
                file=output,
            )
        print(file=output)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Display the Linux FireWire bus topology."
    )
    parser.add_argument(
        "--sysfs",
        default=SYSFS_FW_PATH,
        metavar="PATH",
        help=f"sysfs firewire devices path (default: {SYSFS_FW_PATH})",
    )
    args = parser.parse_args(argv)

    cards = get_nodes(sysfs_path=args.sysfs)
    render_topology(cards)


if __name__ == "__main__":
    main()
