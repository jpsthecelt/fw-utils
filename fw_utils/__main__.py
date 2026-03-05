"""Allow the package to be invoked as ``python -m fw_utils``."""

from .cli import main
import sys

sys.exit(main())
