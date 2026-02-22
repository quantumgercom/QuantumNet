from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DecoherenceConfig:
    """Parâmetros de decoerência."""
    per_timeslot: float = 0.9
    per_measurement: float = 0.99


@dataclass
class FidelityConfig:
    """Limiares de fidelidade usados pelos protocolos."""
    epr_threshold: float = 0.8
    purification_threshold: float = 0.8
    purification_min_probability: float = 0.5
    initial_epr_fidelity: float = 1.0


@dataclass
class ProbabilityConfig:
    """Limites de probabilidade para criação de EPRs."""
    epr_create_max: float = 1.0
    epr_create_min: float = 0.2


@dataclass
class ProtocolConfig:
    """Parâmetros dos protocolos de comunicação."""
    link_max_attempts: int = 2
    link_purification_after_failures: int = 2
    transport_max_attempts: int = 2


@dataclass
class DefaultsConfig:
    """Valores padrão de inicialização da rede."""
    qubits_per_host: int = 10
    eprs_per_channel: int = 10


@dataclass
class SimulationConfig:
    """Configuração centralizada da simulação.

    Pode ser instanciada com valores padrão ou carregada de um arquivo YAML.

    Exemplos::

        # Valores padrão
        config = SimulationConfig()

        # A partir de YAML
        config = SimulationConfig.from_yaml('cenario.yaml')

        # Override programático
        config = SimulationConfig()
        config.decoherence.per_timeslot = 0.95
    """
    decoherence: DecoherenceConfig = field(default_factory=DecoherenceConfig)
    fidelity: FidelityConfig = field(default_factory=FidelityConfig)
    probability: ProbabilityConfig = field(default_factory=ProbabilityConfig)
    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)

    @classmethod
    def from_yaml(cls, path: str) -> 'SimulationConfig':
        """Carrega configuração de um arquivo YAML.

        Campos ausentes no YAML mantêm o valor padrão.

        Args:
            path: Caminho para o arquivo YAML.

        Returns:
            SimulationConfig com os valores do arquivo.
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        return cls(
            decoherence=DecoherenceConfig(**data.get('decoherence', {})),
            fidelity=FidelityConfig(**data.get('fidelity', {})),
            probability=ProbabilityConfig(**data.get('probability', {})),
            protocol=ProtocolConfig(**data.get('protocol', {})),
            defaults=DefaultsConfig(**data.get('defaults', {})),
        )
