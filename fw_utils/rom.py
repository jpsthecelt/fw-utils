"""
FireWire Configuration ROM parser.

The Configuration ROM is a mandatory data structure carried by every
IEEE 1394 device.  It describes the device's capabilities, vendor, and
model in a structured tree of *directories* and *leaf* entries.

On Linux the raw 32-bit quadlets are exposed in
``/sys/bus/firewire/devices/fwX/config_rom``.

References
----------
* IEEE Std 1394-2008, Clause 8 – Configuration ROM
* ANSI/IEEE Std 1212-2001 – Control & Status Registers (CSR) Architecture
"""

import struct

# ---------------------------------------------------------------------------
# Key-type codes (bits 7-6 of the 8-bit key field in each ROM entry)
# ---------------------------------------------------------------------------
KEY_TYPE_IMMEDIATE = 0x00   # value is stored in the entry itself
KEY_TYPE_OFFSET = 0x01      # value is a CSR offset
KEY_TYPE_LEAF = 0x02        # value is an offset to a leaf block
KEY_TYPE_DIRECTORY = 0x03   # value is an offset to a directory block

# ---------------------------------------------------------------------------
# Commonly-used key specifiers (bits 5-0)
# ---------------------------------------------------------------------------
KEY_SPEC_VENDOR = 0x03
KEY_SPEC_MODEL = 0x17
KEY_SPEC_NODE_CAPABILITIES = 0x0C
KEY_SPEC_TEXTUAL_LEAF = 0x01   # used together with KEY_TYPE_LEAF

# Human-readable names for well-known (key_type, key_spec) pairs
_KEY_NAMES = {
    (KEY_TYPE_IMMEDIATE, KEY_SPEC_VENDOR): "Vendor_ID",
    (KEY_TYPE_IMMEDIATE, KEY_SPEC_MODEL): "Model_ID",
    (KEY_TYPE_IMMEDIATE, KEY_SPEC_NODE_CAPABILITIES): "Node_Capabilities",
    (KEY_TYPE_LEAF, KEY_SPEC_TEXTUAL_LEAF): "Textual_Leaf",
    (KEY_TYPE_DIRECTORY, 0x00): "Root_Directory",
    (KEY_TYPE_DIRECTORY, 0x02): "Unit_Directory",
}


def _key_name(key_type, key_spec):
    name = _KEY_NAMES.get((key_type, key_spec))
    if name:
        return name
    return f"0x{(key_type << 6 | key_spec):02X}"


def parse_config_rom(data):
    """
    Parse raw Configuration ROM bytes.

    :param data: :class:`bytes` or :class:`bytearray` containing the raw
                 quadlet data from sysfs.  Must be a multiple of 4 bytes.
    :returns:    A list of ``(key_type, key_spec, value, name)`` tuples for
                 every entry in the root directory.
    :raises ValueError: if *data* is not aligned to 4 bytes.
    """
    if len(data) % 4 != 0:
        raise ValueError(
            f"Configuration ROM size must be a multiple of 4 bytes, "
            f"got {len(data)}"
        )

    quadlets = struct.unpack(f">{len(data) // 4}I", data)

    entries = []
    # The bus info block is the first quadlet (length) plus further quadlets.
    # Its length is encoded in the upper byte of quadlet[0].
    if not quadlets:
        return entries

    bus_info_length = (quadlets[0] >> 24) & 0xFF  # in quadlets
    # Root directory starts immediately after the bus info block.
    root_dir_start = 1 + bus_info_length

    if root_dir_start >= len(quadlets):
        return entries

    root_dir_length = (quadlets[root_dir_start] >> 16) & 0xFFFF
    for i in range(1, root_dir_length + 1):
        idx = root_dir_start + i
        if idx >= len(quadlets):
            break
        q = quadlets[idx]
        key = (q >> 24) & 0xFF
        key_type = (key >> 6) & 0x03
        key_spec = key & 0x3F
        value = q & 0x00FFFFFF
        name = _key_name(key_type, key_spec)
        entries.append((key_type, key_spec, value, name))

    return entries


def read_config_rom(device):
    """
    Read and parse the Configuration ROM for a :class:`~fw_utils.device.FireWireDevice`.

    :param device: A :class:`~fw_utils.device.FireWireDevice` instance.
    :returns: Parsed entries as returned by :func:`parse_config_rom`, or an
              empty list when the file cannot be read.
    """
    import os

    rom_path = os.path.join(device.sysfs_path, "config_rom")
    try:
        with open(rom_path, "rb") as fh:
            data = fh.read()
    except OSError:
        return []

    return parse_config_rom(data)
