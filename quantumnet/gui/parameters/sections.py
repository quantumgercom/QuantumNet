from __future__ import annotations

from typing import Any

import streamlit as st

from quantumnet.gui.parameters.field_metadata import NOISE_OPTIONS, field_help
from quantumnet.gui.parameters.validation import safe_int, safe_probability


def render_decoherence_section(current: dict[str, Any]) -> dict[str, float]:
    st.subheader("Decoherence")
    return {
        "per_timeslot": st.number_input(
            "Decoherence per timeslot",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["decoherence"]["per_timeslot"]),
            help=field_help("decoherence", "per_timeslot"),
        ),
        "per_measurement": st.number_input(
            "Decoherence per measurement",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["decoherence"]["per_measurement"]),
            help=field_help("decoherence", "per_measurement"),
        ),
        "qubit_ttl_threshold": st.number_input(
            "Minimum qubit TTL",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["decoherence"]["qubit_ttl_threshold"]),
            help=field_help("decoherence", "qubit_ttl_threshold"),
        ),
        "epr_ttl_threshold": st.number_input(
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
    return {
        "epr_threshold": st.number_input(
            "EPR fidelity threshold",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["fidelity"]["epr_threshold"]),
            help=field_help("fidelity", "epr_threshold"),
        ),
        "purification_threshold": st.number_input(
            "Purification threshold",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["fidelity"]["purification_threshold"]),
            help=field_help("fidelity", "purification_threshold"),
        ),
        "purification_min_probability": st.number_input(
            "Minimum purification probability",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["fidelity"]["purification_min_probability"]),
            help=field_help("fidelity", "purification_min_probability"),
        ),
        "initial_epr_fidelity": st.number_input(
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
    return {
        "epr_create_max": st.number_input(
            "Maximum EPR creation probability",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=safe_probability(current["probability"]["epr_create_max"]),
            help=field_help("probability", "epr_create_max"),
        ),
        "epr_create_min": st.number_input(
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
    return {
        "link_max_attempts": st.number_input(
            "Maximum link attempts",
            min_value=0,
            step=1,
            value=safe_int(current["protocol"]["link_max_attempts"]),
            help=field_help("protocol", "link_max_attempts"),
        ),
        "link_purification_after_failures": st.number_input(
            "Failures before purification",
            min_value=0,
            step=1,
            value=safe_int(current["protocol"]["link_purification_after_failures"]),
            help=field_help("protocol", "link_purification_after_failures"),
        ),
        "transport_max_attempts": st.number_input(
            "Maximum transport attempts",
            min_value=0,
            step=1,
            value=safe_int(current["protocol"]["transport_max_attempts"]),
            help=field_help("protocol", "transport_max_attempts"),
        ),
        "entanglement_max_attempts": st.number_input(
            "Maximum entanglement attempts",
            min_value=0,
            step=1,
            value=safe_int(current["protocol"].get("entanglement_max_attempts", 5)),
            help=field_help("protocol", "entanglement_max_attempts"),
        ),
    }


def render_defaults_section(current: dict[str, Any]) -> dict[str, int | str]:
    st.subheader("Defaults")
    defaults: dict[str, int | str] = {
        "qubits_per_host": st.number_input(
            "Qubits per host",
            min_value=0,
            step=1,
            value=safe_int(current["defaults"]["qubits_per_host"]),
            help=field_help("defaults", "qubits_per_host"),
        ),
        "eprs_per_channel": st.number_input(
            "EPRs per channel",
            min_value=0,
            step=1,
            value=safe_int(current["defaults"]["eprs_per_channel"]),
            help=field_help("defaults", "eprs_per_channel"),
        ),
        "qubit_regen_interval": st.number_input(
            "Qubit regeneration interval",
            min_value=0,
            step=1,
            value=safe_int(current["defaults"].get("qubit_regen_interval", 0)),
            help=field_help("defaults", "qubit_regen_interval"),
        ),
        "qubit_regen_amount": st.number_input(
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

    defaults["channel_noise_type"] = st.selectbox(
        "Channel noise type",
        options=NOISE_OPTIONS,
        index=NOISE_OPTIONS.index(current_noise),
        help=field_help("defaults", "channel_noise_type"),
    )
    return defaults


def render_costs_section(current: dict[str, Any]) -> dict[str, int]:
    st.subheader("Costs")
    return {
        "heralding": st.number_input(
            "Heralding cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["heralding"]),
            help=field_help("costs", "heralding"),
        ),
        "on_demand": st.number_input(
            "On-demand cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["on_demand"]),
            help=field_help("costs", "on_demand"),
        ),
        "replay": st.number_input(
            "Replay cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["replay"]),
            help=field_help("costs", "replay"),
        ),
        "purification": st.number_input(
            "Purification cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["purification"]),
            help=field_help("costs", "purification"),
        ),
        "swapping": st.number_input(
            "Swapping cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["swapping"]),
            help=field_help("costs", "swapping"),
        ),
        "qubit_creation": st.number_input(
            "Qubit creation cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["qubit_creation"]),
            help=field_help("costs", "qubit_creation"),
        ),
        "e91_round": st.number_input(
            "Cost per E91 round",
            min_value=0,
            step=1,
            value=safe_int(current["costs"]["e91_round"]),
            help=field_help("costs", "e91_round"),
        ),
        "nepr_measurement": st.number_input(
            "NEPR measurement cost",
            min_value=0,
            step=1,
            value=safe_int(current["costs"].get("nepr_measurement", 1)),
            help=field_help("costs", "nepr_measurement"),
        ),
    }

