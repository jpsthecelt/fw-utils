# fw-utils

Linux FireWire (IEEE 1394) utility scripts for inspecting devices connected to
the FireWire bus on Linux systems.  The tools read information from the kernel's
sysfs interface (`/sys/bus/firewire/devices/`) and, where available, parse the
binary config ROM exposed by each device.

---

## Tools

### `fw_devices.py` – List connected FireWire devices

```
usage: fw_devices.py [-h] [-v] [--sysfs PATH]

List connected Linux FireWire devices.

optional arguments:
  -h, --help    show this help message and exit
  -v, --verbose Show additional device attributes
  --sysfs PATH  sysfs firewire devices path (default: /sys/bus/firewire/devices)
```

**Example output**

```
fw0: GUID=0x00a0450012345678  Vendor=ACME Inc  Model=FW Hard Drive
fw0.0: GUID=0x00a0450012345678  Vendor=ACME Inc  Model=FW Hard Drive
fw1: GUID=unknown  Vendor=unknown  Model=unknown
```

---

### `fw_topology.py` – Display FireWire bus topology

```
usage: fw_topology.py [-h] [--sysfs PATH]

Display the Linux FireWire bus topology.

optional arguments:
  -h, --help    show this help message and exit
  --sysfs PATH  sysfs firewire devices path (default: /sys/bus/firewire/devices)
```

**Example output**

```
Bus fw0:
  ├── fw0 (local)  GUID=0x00112233aabbccdd  Vendor=LocalHost  Model=unknown
  └── fw0.0        GUID=0x00a0450012345678  Vendor=ACME Inc   Model=FW Hard Drive

Bus fw1:
  └── fw1 (local)  GUID=0x00112233aabbccea  Vendor=LocalHost  Model=unknown
```

---

### `fw_info.py` – Show detailed device info and config ROM

```
usage: fw_info.py [-h] [--sysfs PATH] [DEVICE]

Show detailed info and config ROM for a Linux FireWire device.

positional arguments:
  DEVICE        Device name (e.g. fw0). If omitted, info for all devices is shown.

optional arguments:
  -h, --help    show this help message and exit
  --sysfs PATH  sysfs firewire devices path (default: /sys/bus/firewire/devices)
```

**Example output**

```
Device: fw0.0
  Path: /sys/bus/firewire/devices/fw0.0
  guid: 0x00a0450012345678
  vendor: 0x00a045
  vendor_name: ACME Inc
  model: 0x000001
  model_name: FW Hard Drive
  specifier_id: 0x00609e
  version: 0x010483

  Config ROM (256 bytes):
    0000: 04 04 6e b7
    0004: 31 33 39 34
    ...

  Root directory entries:
    [immediate] VENDOR = 0x00a045
    [immediate] MODEL = 0x000001
    [directory] UNIT_DIRECTORY = 0x000004
```

---

## Requirements

* Linux with a FireWire host controller and the `firewire-core` kernel module
  loaded.
* Python 3.6 or later (no third-party dependencies).

---

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```
