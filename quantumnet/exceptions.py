class QuantumNetError(Exception):
    """Base exception for all QuantumNet errors."""


class SingletonError(QuantumNetError):
    """Raised when attempting to instantiate a singleton class more than once."""


class HostNotFoundError(QuantumNetError, KeyError):
    """Raised when a host is not found in the network."""


class DuplicateHostError(QuantumNetError, ValueError):
    """Raised when adding a host that already exists in the network."""


class TopologyError(QuantumNetError, ValueError):
    """Raised for invalid topology configuration or arguments."""
