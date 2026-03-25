from __future__ import annotations

from typing import Any

from quantumnet.gui.parameters.field_metadata import INT_FIELDS, NOISE_OPTIONS, PROBABILITY_FIELDS


def validate_config(values: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for section, field in PROBABILITY_FIELDS:
        value = values[section][field]
        if value < 0 or value > 1:
            errors.append(f"{section}.{field} must be between 0 and 1.")

    for section, field in INT_FIELDS:
        value = values[section][field]
        if value < 0:
            errors.append(f"{section}.{field} cannot be negative.")

    if values["probability"]["epr_create_min"] > values["probability"]["epr_create_max"]:
        errors.append("probability.epr_create_min cannot be greater than probability.epr_create_max.")

    if values["protocol"]["link_purification_after_failures"] > values["protocol"]["link_max_attempts"]:
        errors.append(
            "protocol.link_purification_after_failures cannot be greater than protocol.link_max_attempts."
        )

    if values["defaults"]["channel_noise_type"] not in NOISE_OPTIONS:
        errors.append(
            "defaults.channel_noise_type must be 'random', 'bit-flip', 'werner', or 'bitflip+werner'."
        )

    return errors


def safe_probability(default: Any) -> float:
    try:
        value = float(default)
    except (TypeError, ValueError):
        value = 0.0
    return min(1.0, max(0.0, value))


def safe_int(default: Any) -> int:
    try:
        value = int(default)
    except (TypeError, ValueError):
        value = 0
    return max(0, value)

