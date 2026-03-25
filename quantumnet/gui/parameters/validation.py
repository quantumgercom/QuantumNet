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

    topology = values.get("topology", {})
    if not isinstance(topology, dict):
        errors.append("topology must be an object with name and args.")
        return errors

    name = topology.get("name", False)
    args = topology.get("args", [])
    if args is None:
        args = []
    if not isinstance(args, list):
        errors.append("topology.args must be a list.")
        args = []

    if _topology_disabled(name):
        if args:
            errors.append("topology.args must be empty when topology.name is false/null.")
        return errors

    normalized_name = _normalize_topology_name(name)

    if normalized_name in {"line", "linetopology", "star", "startopology", "ring", "ringtopology"}:
        if len(args) != 1:
            errors.append("topology.args must contain exactly 1 value for Line/Star/Ring.")
        else:
            _validate_positive_int_arg(errors, args[0], "topology.args[0]")
    elif normalized_name in {"grid", "gridtopology"}:
        if len(args) != 2:
            errors.append("topology.args must contain exactly 2 values for Grid.")
        else:
            _validate_positive_int_arg(errors, args[0], "topology.args[0]")
            _validate_positive_int_arg(errors, args[1], "topology.args[1]")
    elif normalized_name in {"json", "jsontopology", "custom"}:
        if len(args) != 1:
            errors.append("topology.args must contain exactly 1 value for Json.")
        else:
            json_file = str(args[0]).strip()
            if not json_file:
                errors.append("topology.args[0] must be the JSON file name for Json topology.")
    else:
        errors.append("topology.name must be false/null or one of: Line, Grid, Star, Ring, Json.")

    return errors


def _normalize_topology_name(name: Any) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "")


def _topology_disabled(name: Any) -> bool:
    if isinstance(name, bool):
        return not name
    return _normalize_topology_name(name) in {"", "false", "none", "null", "off", "0"}


def _validate_positive_int_arg(errors: list[str], value: Any, field: str) -> None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        errors.append(f"{field} must be an integer.")
        return
    if parsed < 1:
        errors.append(f"{field} must be >= 1.")


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
