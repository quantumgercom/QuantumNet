import random

class Qubit():
    def __init__(self, qubit_id: int, initial_fidelity: float = None) -> None:
        self.qubit_id = qubit_id
        self._qubit_state = 0  # Define o estado inicial do qubit como 0
        self._initial_fidelity = initial_fidelity if initial_fidelity is not None else random.uniform(0, 1)
        self._current_fidelity = self._initial_fidelity

    def __str__(self):
        return f"Qubit {self.qubit_id} with state {self._qubit_state}"

    def get_initial_fidelity(self):
        return self._initial_fidelity

    def get_current_fidelity(self):
        return self._current_fidelity

    def set_current_fidelity(self, new_fidelity: float):
            """Define a fidelidade atual do qubit."""
            self._current_fidelity = new_fidelity

    def apply_x(self):
        """Aplica a porta X (NOT) ao qubit."""
        self._qubit_state = 1 if self._qubit_state == 0 else 0

    def apply_hadamard(self):
        """Aplica a porta Hadamard (H) ao qubit."""
        # Hadamard transforma o estado |0> em (|0> + |1>) / sqrt(2)
        # e |1> em (|0> - |1>) / sqrt(2). Para simulação, usa-se probabilidade.
        if self._qubit_state == 0:
            self._qubit_state = random.choice([0, 1])  # Simula a superposição
        else:
            self._qubit_state = random.choice([0, 1])  # Simula a superposição

    def measure(self):
        """Realiza a medição do qubit no estado atual."""
        return self._qubit_state
