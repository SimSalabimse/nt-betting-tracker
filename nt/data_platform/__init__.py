"""Optional integration with the sibling ``nt-data-platform`` package.

The tracker works without ``nt_data`` installed. Enable via
``config.yaml`` → ``data_platform.enabled: true`` after an editable install.
"""

from __future__ import annotations

from nt.data_platform.client import get_client, is_available
from nt.defaults import data_platform_cfg

__all__ = [
    "data_platform_cfg",
    "get_client",
    "is_available",
]
