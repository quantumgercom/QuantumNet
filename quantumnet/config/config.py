from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DecoherenceConfig:
    """Decoherence parameters."""
    per_timeslot: float = 0.9
    per_measurement: float = 0.99
    qubit_ttl_threshold: float = 0.1
    epr_ttl_threshold: float = 0.1


@dataclass
class FidelityConfig:
    """Fidelity thresholds used by protocols."""
    epr_threshold: float = 0.8
    purification_threshold: float = 0.8
    purification_min_probability: float = 0.5
    initial_epr_fidelity: float = 1.0


@dataclass
class ProbabilityConfig:
    """Probability limits for EPR creation."""
    epr_create_max: float = 1.0
    epr_create_min: float = 0.2


@dataclass
class ProtocolConfig:
    """Communication protocol parameters."""
    link_max_attempts: int = 10
    link_purification_after_failures: int = 2
    transport_max_attempts: int = 2
    entanglement_max_attempts: int = 5


@dataclass
class DefaultsConfig:
    """Default network initialization values."""
    qubits_per_host: int = 10
    eprs_per_channel: int = 10
    qubit_regen_interval: int = 0   # ticks between regeneration cycles (0 = disabled)
    qubit_regen_amount: int = 3     # qubits added per host per cycle
    channel_noise_type: str = 'random'  # 'bit-flip', 'werner', 'bitflip+werner', or 'random' (assigns one at random per channel)


@dataclass
class CostsConfig:
    """Timeslot costs for DES operations."""
    heralding: int = 1
    on_demand: int = 1
    replay: int = 1
    purification: int = 1
    swapping: int = 1
    qubit_creation: int = 1
    e91_round: int = 1
    nepr_measurement: int = 1


@dataclass
class TopologyConfig:
    """Optional topology inputs used by Network.set_ready_topology()."""
    name: str | None = None
    args: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        raw_name = self.name
        if isinstance(raw_name, bool):
            # Allow topology.name: false in YAML to explicitly disable topology loading.
            self.name = None if raw_name is False else str(raw_name)
        elif raw_name is None:
            self.name = None
        else:
            parsed_name = str(raw_name).strip()
            if parsed_name.lower() in {"", "false", "none", "null", "off"}:
                self.name = None
            else:
                self.name = parsed_name

        if self.args is None:
            raw_args = []
        elif isinstance(self.args, (list, tuple)):
            raw_args = list(self.args)
        else:
            raw_args = [self.args]

        self.args = raw_args


@dataclass
class SimulationConfig:
    """Centralized simulation configuration.

    Can be instantiated with default values or loaded from a YAML file.

    Examples::

        # Default values
        config = SimulationConfig()

        # From YAML
        config = SimulationConfig.from_yaml('scenario.yaml')

        # Programmatic override
        config = SimulationConfig()
        config.decoherence.per_timeslot = 0.95
    """
    decoherence: DecoherenceConfig = field(default_factory=DecoherenceConfig)
    fidelity: FidelityConfig = field(default_factory=FidelityConfig)
    probability: ProbabilityConfig = field(default_factory=ProbabilityConfig)
    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    costs: CostsConfig = field(default_factory=CostsConfig)
    topology: TopologyConfig = field(default_factory=TopologyConfig)

    @classmethod
    def from_yaml(cls, path: str) -> 'SimulationConfig':
        """Load configuration from a YAML file.

        Missing fields in YAML keep their default value.

        Args:
            path: Path to the YAML file.

        Returns:
            SimulationConfig with values from the file.
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        topology_data = data.get('topology', {})
        if not isinstance(topology_data, dict):
            topology_data = {}

        cfg = cls(
            decoherence=DecoherenceConfig(**data.get('decoherence', {})),
            fidelity=FidelityConfig(**data.get('fidelity', {})),
            probability=ProbabilityConfig(**data.get('probability', {})),
            protocol=ProtocolConfig(**data.get('protocol', {})),
            defaults=DefaultsConfig(**data.get('defaults', {})),
            costs=CostsConfig(**data.get('costs', {})),
            topology=TopologyConfig(**topology_data),
        )
        cfg._source_path = Path(path).resolve()
        return cfg
