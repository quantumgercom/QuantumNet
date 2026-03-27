from __future__ import annotations

import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from quantumnet.config import SimulationConfig


def _package_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _new_default_config_path() -> Path:
    return (_package_root() / "config" / "default_config.yaml").resolve()


def _legacy_default_config_path() -> Path:
    return (_package_root() / "default_config.yaml").resolve()


def _migrate_legacy_default_file() -> None:
    legacy_path = _legacy_default_config_path()
    new_path = _new_default_config_path()
    if not legacy_path.exists():
        return

    new_path.parent.mkdir(parents=True, exist_ok=True)
    if not new_path.exists() or legacy_path.read_bytes() != new_path.read_bytes():
        shutil.copyfile(legacy_path, new_path)


def normalize_config_path(path: Path) -> Path:
    resolved = Path(path).resolve()
    if resolved == _legacy_default_config_path():
        _migrate_legacy_default_file()
        return _new_default_config_path()
    return resolved


def default_config_path() -> Path:
    env_path = os.getenv("QUANTUMNET_CONFIG_PATH")
    if env_path:
        return normalize_config_path(Path(env_path))
    _migrate_legacy_default_file()
    return _new_default_config_path()


def normalize_custom_filename(raw_name: str) -> str:
    clean_name = Path(raw_name.strip()).name
    if not clean_name:
        clean_name = "custom_config.yaml"
    suffix = Path(clean_name).suffix.lower()
    if suffix not in {".yaml", ".yml"}:
        clean_name = f"{clean_name}.yaml"
    return clean_name


def base_config_dict() -> dict[str, Any]:
    return asdict(SimulationConfig())


def load_config(config_path: Path) -> dict[str, Any]:
    config_path = normalize_config_path(config_path)
    if not config_path.exists():
        return base_config_dict()

    with config_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    cfg = base_config_dict()
    for section_name, section_values in raw.items():
        if section_name not in cfg or not isinstance(section_values, dict):
            continue
        for field_name, value in section_values.items():
            if field_name in cfg[section_name]:
                cfg[section_name][field_name] = value
    return cfg


def save_config(config_path: Path, values: dict[str, Any]) -> None:
    config_path = normalize_config_path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(values, file, sort_keys=False, allow_unicode=True)
