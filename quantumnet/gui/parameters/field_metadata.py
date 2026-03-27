from __future__ import annotations

from typing import Final


PROBABILITY_FIELDS: Final[set[tuple[str, str]]] = {
    ("decoherence", "per_timeslot"),
    ("decoherence", "per_measurement"),
    ("decoherence", "qubit_ttl_threshold"),
    ("decoherence", "epr_ttl_threshold"),
    ("fidelity", "epr_threshold"),
    ("fidelity", "purification_threshold"),
    ("fidelity", "purification_min_probability"),
    ("fidelity", "initial_epr_fidelity"),
    ("probability", "epr_create_max"),
    ("probability", "epr_create_min"),
}

INT_FIELDS: Final[set[tuple[str, str]]] = {
    ("protocol", "link_max_attempts"),
    ("protocol", "link_purification_after_failures"),
    ("protocol", "transport_max_attempts"),
    ("protocol", "entanglement_max_attempts"),
    ("defaults", "qubits_per_host"),
    ("defaults", "eprs_per_channel"),
    ("defaults", "qubit_regen_interval"),
    ("defaults", "qubit_regen_amount"),
    ("costs", "heralding"),
    ("costs", "on_demand"),
    ("costs", "replay"),
    ("costs", "purification"),
    ("costs", "swapping"),
    ("costs", "qubit_creation"),
    ("costs", "e91_round"),
    ("costs", "nepr_measurement"),
}

NOISE_OPTIONS: Final[list[str]] = ["random", "bit-flip", "werner", "bitflip+werner"]

FIELD_HELP: Final[dict[tuple[str, str], str]] = {
    ("decoherence", "per_timeslot"): "Factor applied at each tick; lower values degrade fidelity faster over time.",
    ("decoherence", "per_measurement"): "Factor applied whenever a fidelity measurement occurs; lower values increase observation loss.",
    ("decoherence", "qubit_ttl_threshold"): "When qubit fidelity drops below this threshold, it is discarded from memory.",
    ("decoherence", "epr_ttl_threshold"): "When EPR pair fidelity drops below this threshold, the pair is removed from the channel.",
    ("fidelity", "epr_threshold"): "Minimum fidelity required to treat an EPR as usable/successful in protocols.",
    ("fidelity", "purification_threshold"): "Minimum target fidelity after purification to accept the resulting pair.",
    ("fidelity", "purification_min_probability"): "Minimum probability required to attempt purification.",
    ("fidelity", "initial_epr_fidelity"): "Initial fidelity assigned to newly created EPR pairs.",
    ("probability", "epr_create_max"): "Upper bound for EPR creation probability on channels.",
    ("probability", "epr_create_min"): "Lower bound for EPR creation probability on channels.",
    ("protocol", "link_max_attempts"): "Maximum number of link attempts before terminating/failing the operation.",
    ("protocol", "link_purification_after_failures"): "Number of consecutive failures that triggers a purification attempt.",
    ("protocol", "transport_max_attempts"): "Maximum number of transmission attempts in the transport layer.",
    ("protocol", "entanglement_max_attempts"): "Maximum number of attempts to establish entanglement.",
    ("defaults", "qubits_per_host"): "Initial number of qubits allocated per host when creating the topology.",
    ("defaults", "eprs_per_channel"): "Initial number of EPR pairs provisioned per channel.",
    ("defaults", "qubit_regen_interval"): "Interval in ticks to regenerate qubits automatically (0 disables it).",
    ("defaults", "qubit_regen_amount"): "Number of qubits added per host in each regeneration cycle.",
    ("defaults", "channel_noise_type"): "Noise model applied to topology channels.",
    ("costs", "heralding"): "Cost in timeslots for the heralding protocol used to create entanglement.",
    ("costs", "on_demand"): "Cost in timeslots for the on-demand protocol.",
    ("costs", "replay"): "Cost in timeslots for replaying a link attempt.",
    ("costs", "purification"): "Cost in timeslots for one purification operation.",
    ("costs", "swapping"): "Cost in timeslots for each swapping operation.",
    ("costs", "qubit_creation"): "Cost in timeslots to create new qubits.",
    ("costs", "e91_round"): "Cost in timeslots for one E91 protocol round.",
    ("costs", "nepr_measurement"): "Cost in timeslots for measurement used in the NEPR flow.",
}


def field_help(section: str, field: str) -> str:
    return FIELD_HELP.get((section, field), "")

