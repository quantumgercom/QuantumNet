from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from quantumnet.gui.core.config import default_config_path


def default_topology_path() -> Path:
    return (default_config_path().parent / "default_topology.json").resolve()


def normalize_topology_filename(raw_name: str) -> str:
    clean_name = Path(raw_name.strip()).name
    if not clean_name:
        clean_name = "default_topology.json"
    if Path(clean_name).suffix.lower() != ".json":
        clean_name = f"{clean_name}.json"
    return clean_name


def topology_file_selector(default_path: Path) -> Path:
    mode = st.radio(
        "Topology JSON source",
        ["Default", "Custom"],
        key="qn_topology_file_mode",
        horizontal=True,
    )

    if mode == "Default":
        return default_path

    if "qn_topology_filename" not in st.session_state:
        st.session_state["qn_topology_filename"] = "custom_topology.json"

    custom_name_input = st.text_input(
        "Topology JSON filename",
        key="qn_topology_filename",
        help="File saved in the same folder as default_config.yaml.",
    )
    custom_name = normalize_topology_filename(custom_name_input)
    topology_path = (default_path.parent / custom_name).resolve()
    if not topology_path.is_file():
        st.error("Arquivo JSON de topologia nao foi encontrado.")
    return topology_path


def load_topology_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_topology_json(path: Path, spec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(spec, file, indent=2)
        file.write("\n")
