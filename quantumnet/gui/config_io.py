"""Backward-compatible imports for GUI config helpers."""

from quantumnet.gui.core.config import (
    base_config_dict,
    default_config_path,
    load_config,
    normalize_custom_filename,
    save_config,
)

__all__ = [
    "base_config_dict",
    "default_config_path",
    "load_config",
    "normalize_custom_filename",
    "save_config",
]
