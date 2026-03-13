import random
from typing import Union

class Epr():
    def __init__(self, epr_id: Union[int, tuple], initial_fidelity: float = None,
                 clock=None, decoherence_rate: float = 1.0) -> None:
        self._epr_id = epr_id
        self._initial_fidelity = initial_fidelity if initial_fidelity is not None else random.uniform(0, 1)

        # Lazy-evaluation state
        self._clock = clock
        self._decoherence_rate = decoherence_rate
        self._base_fidelity = self._initial_fidelity
        self._base_timeslot = clock.now if clock else 0

    def __repr__(self):
        return f"Epr(id={self._epr_id}, fidelity={self.current_fidelity:.4f})"

    def __eq__(self, other):
        if not isinstance(other, Epr):
            return NotImplemented
        return self._epr_id == other._epr_id

    def __hash__(self):
        return hash(self._epr_id)

    @property
    def epr_id(self):
        return self._epr_id

    @property
    def id(self):
        return self._epr_id

    @property
    def initial_fidelity(self) -> float:
        return self._initial_fidelity

    @property
    def current_fidelity(self) -> float:
        """
        Compute current fidelity on demand, accounting for time-based decoherence.

        Formula: base_fidelity * (decoherence_rate ** elapsed)
        where elapsed = clock.now - base_timeslot.

        If no clock is attached, returns base_fidelity.
        """
        if self._clock is None or self._decoherence_rate >= 1.0:
            return self._base_fidelity
        elapsed = self._clock.now - self._base_timeslot
        if elapsed <= 0:
            return self._base_fidelity
        return self._base_fidelity * (self._decoherence_rate ** elapsed)

    @current_fidelity.setter
    def current_fidelity(self, new_fidelity: float):
        """
        Snapshot fidelity at the current timeslot.

        Resets the lazy-evaluation base so that future decoherence
        is computed from (new_fidelity, now) onward.
        """
        self._base_fidelity = new_fidelity
        if self._clock is not None:
            self._base_timeslot = self._clock.now

    @property
    def fidelity(self) -> float:
        return self.current_fidelity

    @fidelity.setter
    def fidelity(self, value: float):
        self.current_fidelity = value
