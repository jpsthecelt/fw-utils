# fw-utils

Experiments with FireWire (IEEE 1394) utilities on Linux.

`fw-utils` is a small Python library and command-line toolkit for listing and
inspecting FireWire devices via the Linux kernel's `sysfs` interface
(`/sys/bus/firewire/devices/`).

## Features

* List all detected FireWire devices with vendor/model info
* Look up a specific device by GUID
* Parse and display the Configuration ROM of each device
* JSON output for easy scripting

## Requirements

* Python 3.8+
* Linux with FireWire (IEEE 1394) support enabled in the kernel

## Installation

```bash
pip install .
```

For development (includes `pytest`):

```bash
pip install -e ".[dev]"
```

## Usage

### Command line

```bash
# List all FireWire devices
fw-list

# Output as JSON
fw-list --json

# Show only the device with a specific GUID
fw-list --guid 0x0011223344556677

# Also display parsed Configuration ROM entries
fw-list --rom
```

### Python API

```python
from fw_utils.scanner import FireWireScanner
from fw_utils.rom import read_config_rom

scanner = FireWireScanner()
for device in scanner.list_devices():
    print(device)
    for entry in read_config_rom(device):
        key_type, key_spec, value, name = entry
        print(f"  {name}: 0x{value:06X}")
```

## Running tests

```bash
pytest
```

## License

MIT – see [LICENSE](LICENSE).
