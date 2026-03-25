"""Core building blocks shared by GUI pages."""

from quantumnet.gui.core.config import (
    base_config_dict,
    default_config_path,
    load_config,
    normalize_custom_filename,
    save_config,
)
from quantumnet.gui.core.layout import config_selector, setup_page

__all__ = [
    "base_config_dict",
    "config_selector",
    "default_config_path",
    "load_config",
    "normalize_custom_filename",
    "save_config",
    "setup_page",
]

