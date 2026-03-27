from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from quantumnet.gui.parameters.field_metadata import NOISE_OPTIONS, field_help
from quantumnet.gui.parameters.validation import safe_int, safe_probability


def _two_column_inputs() -> tuple[Any, Any]:
    return st.columns(2)


def _normalized_topology_name(name: Any) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "")


def _topology_disabled(name: Any) -> bool:
    if isinstance(name, bool):
        return not name
    normalized = _normalized_topology_name(name)
    return normalized in {"", "false", "none", "null", "off", "0"}


def _active_config_dir() -> Path:
    raw_path = st.session_state.get("qn_active_config_path")
    if isinstance(raw_path, str) and raw_path.strip():
        try:
            return Path(raw_path).resolve().parent
        except (OSError, RuntimeError, ValueError):
            pass
    return Path.cwd()


def _resolve_topology_json_path(raw_path: str) -> Path | None:
    clean_path = str(raw_path).strip()
    if not clean_path:
        return None
    try:
        topology_path = Path(clean_path)
        if not topology_path.is_absolute():
            topology_path = _active_config_dir() / topology_path
        return topology_path.resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def render_decoherence_section(current: dict[str, Any]) -> dict[str, float]:
    st.subheader("Decoherence")
    col1, col2 = _two_column_inputs()
    return {
        "per_timeslot": col1.number_input(
            "Decoherence per timeslot",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["decoherence"]["per_timeslot"]),
            help=field_help("decoherence", "per_timeslot"),
        ),
        "per_measurement": col2.number_input(
            "Decoherence per measurement",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["decoherence"]["per_measurement"]),
            help=field_help("decoherence", "per_measurement"),
        ),
        "qubit_ttl_threshold": col1.number_input(
            "Minimum qubit TTL",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["decoherence"]["qubit_ttl_threshold"]),
            help=field_help("decoherence", "qubit_ttl_threshold"),
        ),
        "epr_ttl_threshold": col2.number_input(
            "Minimum EPR TTL",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["decoherence"]["epr_ttl_threshold"]),
            help=field_help("decoherence", "epr_ttl_threshold"),
        ),
    }


def render_fidelity_section(current: dict[str, Any]) -> dict[str, float]:
    st.subheader("Fidelity")
    col1, col2 = _two_column_inputs()
    return {
        "epr_threshold": col1.number_input(
            "EPR fidelity threshold",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["fidelity"]["epr_threshold"]),
            help=field_help("fidelity", "epr_threshold"),
        ),
        "purification_threshold": col2.number_input(
            "Purification threshold",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["fidelity"]["purification_threshold"]),
            help=field_help("fidelity", "purification_threshold"),
        ),
        "purification_min_probability": col1.number_input(
            "Minimum purification probability",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["fidelity"]["purification_min_probability"]),
            help=field_help("fidelity", "purification_min_probability"),
        ),
        "initial_epr_fidelity": col2.number_input(
            "Initial EPR fidelity",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["fidelity"]["initial_epr_fidelity"]),
            help=field_help("fidelity", "initial_epr_fidelity"),
        ),
    }


def render_probability_section(current: dict[str, Any]) -> dict[str, float]:
    st.subheader("Probability")
    col1, col2 = _two_column_inputs()
    return {
        "epr_create_max": col1.number_input(
            "Maximum EPR creation probability",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["probability"]["epr_create_max"]),
            help=field_help("probability", "epr_create_max"),
        ),
        "epr_create_min": col2.number_input(
            "Minimum EPR creation probability",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["probability"]["epr_create_min"]),
            help=field_help("probability", "epr_create_min"),
        ),
    }


def render_protocol_section(current: dict[str, Any]) -> dict[str, int]:
    st.subheader("Protocol")
    col1, col2 = _two_column_inputs()
    return {
        "link_max_attempts": col1.number_input(
            "Maximum link attempts",
            min_value=0,
            step=1,
            value=safe_int(current["protocol"]["link_max_attempts"]),
            help=field_help("protocol", "link_max_attempts"),
        ),
        "link_purification_after_failures": col2.number_input(
            "Failures before purification",
            min_value=0,
            step=1,
            value=safe_int(current["protocol"]["link_purification_after_failures"]),
            help=field_help("protocol", "link_purification_after_failures"),
        ),
        "transport_max_attempts": col1.number_input(
            "Maximum transport attempts",
            min_value=0,
            step=1,
            value=safe_int(current["protocol"]["transport_max_attempts"]),
            help=field_help("protocol", "transport_max_attempts"),
        ),
        "entanglement_max_attempts": col2.number_input(
            "Maximum entanglement attempts",
            min_value=0,
            step=1,
            value=safe_int(current["protocol"].get("entanglement_max_attempts", 5)),
            help=field_help("protocol", "entanglement_max_attempts"),
        ),
    }


def render_defaults_section(current: dict[str, Any]) -> dict[str, int | str]:
    st.subheader("Defaults")
    col1, col2 = _two_column_inputs()
    defaults: dict[str, int | str] = {
        "qubits_per_host": col1.number_input(
            "Qubits per host",
            min_value=0,
            step=1,
            value=safe_int(current["defaults"]["qubits_per_host"]),
            help=field_help("defaults", "qubits_per_host"),
        ),
        "eprs_per_channel": col2.number_input(
            "EPRs per channel",
            min_value=0,
            step=1,
            value=safe_int(current["defaults"]["eprs_per_channel"]),
            help=field_help("defaults", "eprs_per_channel"),
        ),
        "qubit_regen_interval": col1.number_input(
            "Qubit regeneration interval",
            min_value=0,
            step=1,
            value=safe_int(current["defaults"].get("qubit_regen_interval", 0)),
            help=field_help("defaults", "qubit_regen_interval"),
        ),
        "qubit_regen_amount": col2.number_input(
            "Qubit regeneration amount",
            min_value=0,
            step=1,
            value=safe_int(current["defaults"].get("qubit_regen_amount", 3)),
            help=field_help("defaults", "qubit_regen_amount"),
        ),
    }

    current_noise = current["defaults"].get("channel_noise_type", "random")
    if current_noise not in NOISE_OPTIONS:
        current_noise = "random"

    defaults["channel_noise_type"] = col1.selectbox(
        "Channel noise type",
        options=NOISE_OPTIONS,
        index=NOISE_OPTIONS.index(current_noise),
        help=field_help("defaults", "channel_noise_type"),
    )
    return defaults


def render_costs_section(current: dict[str, Any]) -> dict[str, int]:
    st.subheader("Costs")
    col1, col2 = _two_column_inputs()
    return {
        "heralding": col1.number_input(
            "Heralding cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["heralding"]),
            help=field_help("costs", "heralding"),
        ),
        "on_demand": col2.number_input(
            "On-demand cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["on_demand"]),
            help=field_help("costs", "on_demand"),
        ),
        "replay": col1.number_input(
            "Replay cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["replay"]),
            help=field_help("costs", "replay"),
        ),
        "purification": col2.number_input(
            "Purification cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["purification"]),
            help=field_help("costs", "purification"),
        ),
        "swapping": col1.number_input(
            "Swapping cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["swapping"]),
            help=field_help("costs", "swapping"),
        ),
        "qubit_creation": col2.number_input(
            "Qubit creation cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["qubit_creation"]),
            help=field_help("costs", "qubit_creation"),
        ),
        "e91_round": col1.number_input(
            "Cost per E91 round",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["e91_round"]),
            help=field_help("costs", "e91_round"),
        ),
        "nepr_measurement": col2.number_input(
            "NEPR measurement cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"].get("nepr_measurement", 1)),
            help=field_help("costs", "nepr_measurement"),
        ),
    }


def render_topology_section(current: dict[str, Any]) -> dict[str, Any]:
    st.subheader("Topology")

    topology = current.get("topology", {})
    if not isinstance(topology, dict):
        topology = {}

    ready_options = ["Line", "Grid", "Star", "Ring", "Json"]
    current_name = topology.get("name", False)
    current_name_norm = _normalized_topology_name(current_name)

    use_ready_default = not _topology_disabled(current_name)
    if current_name_norm in {"line", "linetopology"}:
        selected_default = "Line"
    elif current_name_norm in {"grid", "gridtopology"}:
        selected_default = "Grid"
    elif current_name_norm in {"star", "startopology"}:
        selected_default = "Star"
    elif current_name_norm in {"ring", "ringtopology"}:
        selected_default = "Ring"
    elif current_name_norm in {"json", "jsontopology", "custom"}:
        selected_default = "Json"
    else:
        selected_default = "Line"

    use_ready = st.checkbox(
        "Set topology",
        value=use_ready_default,
        help=(
            "Enable topology selection from configuration. "
            "When disabled, topology.name is saved as false."
        ),
    )

    if not use_ready:
        st.caption("Ready topology disabled (topology.name = false).")
        return {"name": False, "args": []}

    selected = st.selectbox(
        "Topology type",
        options=ready_options,
        index=ready_options.index(selected_default),
        help="Choose a topology type and fill the required parameters.",
    )

    raw_args = topology.get("args", [])
    if not isinstance(raw_args, list):
        raw_args = []

    args: list[Any]
    col1, col2 = _two_column_inputs()
    if selected in {"Line", "Star", "Ring"}:
        default_nodes = str(raw_args[0]).strip() if len(raw_args) > 0 else "5"
        nodes = col1.text_input(
            f"{selected}: number of nodes",
            value=default_nodes,
            help="Integer value greater than or equal to 1.",
        )
        args = [nodes.strip()]
    elif selected == "Grid":
        rows_default = str(raw_args[0]).strip() if len(raw_args) > 0 else "3"
        cols_default = str(raw_args[1]).strip() if len(raw_args) > 1 else "3"
        cols = col1.text_input(
            "Grid: columns",
            value=cols_default,
            help="Integer value greater than or equal to 1.",
        )
        rows = col2.text_input(
            "Grid: rows",
            value=rows_default,
            help="Integer value greater than or equal to 1.",
        )
        args = [rows.strip(), cols.strip()]
    elif selected == "Json":
        default_filename = str(raw_args[0]).strip() if len(raw_args) > 0 else ""
        json_filename = col1.text_input(
            "JSON file name",
            value=default_filename,
            help="Exact file name or relative path to your custom topology JSON file.",
        )
        json_filename = json_filename.strip()
        args = [json_filename]

        if json_filename:
            topology_json_path = _resolve_topology_json_path(json_filename)
            if topology_json_path is None or not topology_json_path.is_file():
                col1.error("Arquivo JSON de topologia nao foi encontrado.")
    else:
        args = []

    return {"name": selected, "args": args}

