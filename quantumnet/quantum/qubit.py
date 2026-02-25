import random

class Qubit():
    def __init__(self, qubit_id: int, initial_fidelity: float = None,
                 clock=None, decoherence_rate: float = 1.0) -> None:
        self.qubit_id = qubit_id
        self._qubit_state = 0  # Define the initial qubit state as 0
        self._initial_fidelity = initial_fidelity if initial_fidelity is not None else random.uniform(0, 1)

        # Lazy-evaluation state
        self._clock = clock
        self._decoherence_rate = decoherence_rate
        self._base_fidelity = self._initial_fidelity
        self._base_timeslot = clock.now if clock else 0

    def __str__(self):
        return f"Qubit {self.qubit_id} with state {self._qubit_state}"

    def get_initial_fidelity(self):
        return self._initial_fidelity

    def get_current_fidelity(self) -> float:
        """
        Compute current fidelity on demand, accounting for time-based decoherence.

        Formula: base_fidelity * (decoherence_rate ** elapsed)
        where elapsed = clock.now - base_timeslot.

        If no clock is attached (e.g., ephemeral E91 qubits), returns base_fidelity.
        """
        if self._clock is None or self._decoherence_rate >= 1.0:
            return self._base_fidelity
        elapsed = self._clock.now - self._base_timeslot
        if elapsed <= 0:
            return self._base_fidelity
        return self._base_fidelity * (self._decoherence_rate ** elapsed)

    def set_current_fidelity(self, new_fidelity: float):
        """
        Snapshot fidelity at the current timeslot.

        Resets the lazy-evaluation base so that future decoherence
        is computed from (new_fidelity, now) onward.
        """
        self._base_fidelity = new_fidelity
        if self._clock is not None:
            self._base_timeslot = self._clock.now

    def apply_x(self):
        """Apply X gate (NOT) to the qubit."""
        self._qubit_state = 1 if self._qubit_state == 0 else 0

    def apply_hadamard(self):
        """Apply Hadamard gate (H) to the qubit."""
        # Hadamard transforms state |0> into (|0> + |1>) / sqrt(2)
        # and |1> into (|0> - |1>) / sqrt(2). For simulation, probability is used.
        if self._qubit_state == 0:
            self._qubit_state = random.choice([0, 1])  # Simulates superposition
        else:
            self._qubit_state = random.choice([0, 1])  # Simulates superposition

    def measure(self):
        """Perform measurement of the qubit in its current state."""
        return self._qubit_state
