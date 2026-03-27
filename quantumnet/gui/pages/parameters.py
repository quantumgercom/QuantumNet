from __future__ import annotations

from pathlib import Path

import streamlit as st

from quantumnet.gui.core.config import load_config, save_config
from quantumnet.gui.core.layout import config_selector
from quantumnet.gui.parameters.sections import (
    render_costs_section,
    render_decoherence_section,
    render_defaults_section,
    render_fidelity_section,
    render_probability_section,
    render_protocol_section,
    render_topology_section,
)
from quantumnet.gui.parameters.validation import validate_config


def render_parameters_page(default_config_path: Path) -> None:
    st.title("Parameters")
    config_path = config_selector(default_config_path)
    st.caption(f"Configuration file: `{config_path}`")
    st.session_state["qn_active_config_path"] = str(config_path)

    current = load_config(config_path)
    current_errors = validate_config(current)

    if current_errors:
        st.error(
            "Inconsistent values were detected in the current file. "
            "Adjust the fields below to save a valid version."
        )
        for err in current_errors:
            st.markdown(f"- {err}")

    decoherence = render_decoherence_section(current)
    fidelity = render_fidelity_section(current)
    probability = render_probability_section(current)
    protocol = render_protocol_section(current)
    defaults = render_defaults_section(current)
    costs = render_costs_section(current)
    topology = render_topology_section(current)
    submitted = st.button("Save configuration", type="primary")

    if not submitted:
        return

    new_values = dict(current)
    new_values.update(
        {
            "decoherence": decoherence,
            "fidelity": fidelity,
            "probability": probability,
            "protocol": protocol,
            "defaults": defaults,
            "costs": costs,
            "topology": topology,
        }
    )
    errors = validate_config(new_values)
    if errors:
        st.error("Could not save: there are invalid values.")
        for err in errors:
            st.markdown(f"- {err}")
        return

    save_config(config_path, new_values)
    st.success("Configuration saved successfully.")
