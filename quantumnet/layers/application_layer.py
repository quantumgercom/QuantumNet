import random
from ..topology import Host
from ..quantum import Qubit
from ..utils import Logger

class ApplicationLayer:
    def __init__(self, context, transport_layer):
        """
        Initialize the QKD (Quantum Key Distribution) application layer.

        Args:
            context (NetworkContext): Shared network context.
            transport_layer (TransportLayer): Network transport layer.
        """
        self._context = context
        self._transport_layer = transport_layer
        self.logger = Logger.get_instance()

    def __str__(self):
        return 'Application Layer'

    def run_app(self, app_name, *args, on_complete=None):
        """
        Schedule the desired application by the given name. Fire-and-forget.

        Args:
            app_name (str): The name of the application to execute.
            *args: Variable arguments for the specific application: alice_id, bob_id, and num_qubits.
            on_complete: Optional callback(success=bool, key=list or None).
        """
        if app_name == "QKD_E91":
            alice_id, bob_id, num_qubits = args
            self.qkd_e91_protocol(alice_id, bob_id, num_qubits, on_complete=on_complete)
        else:
            self.logger.log(f"Application not executed or not found.")
            if on_complete is not None:
                on_complete(success=False, key=None)


    def prepare_e91_qubits(self, key, bases):
        """
        Prepare qubits according to the key and bases provided for the E91 protocol.

        Args:
            key (list): Key containing the bit sequence.
            bases (list): Bases used to measure the qubits.

        Returns:
            list: List of prepared qubits.
        """
        self._context.clock.emit('e91_qubits_prepared', num_qubits=len(key))
        self.logger.debug(f"E91 qubits prepared at timeslot: {self._context.clock.now}")
        qubits = []
        for bit, base in zip(key, bases):
            qubit = Qubit(qubit_id=self._context.generate_qubit_id())  # Create new qubit with unique ID
            if bit == 1:
                qubit.apply_x()  # Apply X gate (NOT) to qubit if bit is 1
            if base == 1:
                qubit.apply_hadamard()  # Apply Hadamard gate to qubit if base is 1
            qubits.append(qubit)  # Add prepared qubit to list
        return qubits

    def apply_bases_and_measure_e91(self, qubits, bases):
        """
        Apply measurement bases and measure qubits in the E91 protocol.

        Args:
            qubits (list): List of qubits to be measured.
            bases (list): List of bases to apply for measurement.

        Returns:
            list: Measurement results.
        """
        self._context.clock.emit('e91_measurement', num_qubits=len(qubits))
        self.logger.debug(f"E91 measurements performed at timeslot: {self._context.clock.now}")
        results = []
        for qubit, base in zip(qubits, bases):
            if base == 1:
                qubit.apply_hadamard()  # Apply Hadamard gate before measurement if base is 1
            measurement = qubit.measure()  # Measure the qubit
            results.append(measurement)  # Add measurement result to results list
        return results

    def qkd_e91_protocol(self, alice_id, bob_id, num_bits, on_complete=None):
        """
        Schedule the E91 protocol for Quantum Key Distribution (QKD). Fire-and-forget.

        Result communicated via:
          - 'e91_complete' or 'e91_failed' event
          - on_complete(success=bool, key=list or None) callback if provided

        Args:
            alice_id (int): Alice host ID.
            bob_id (int): Bob host ID.
            num_bits (int): Number of bits for the key.
            on_complete: Optional callback(success=bool, key=list or None).
        """
        final_key = []
        self._e91_loop(alice_id, bob_id, num_bits, final_key, on_complete)

    def _e91_loop(self, alice_id, bob_id, num_bits, final_key, on_complete):
        """One iteration of the E91 protocol loop."""
        if len(final_key) >= num_bits:
            final_key = final_key[:num_bits]
            self.logger.log(f"E91 protocol succeeded. Final shared key: {final_key}")
            self._context.clock.emit('e91_complete', alice=alice_id, bob=bob_id, key_length=num_bits)
            if on_complete is not None:
                on_complete(success=True, key=final_key)
            return

        num_qubits = int((num_bits - len(final_key)) * 2)
        self.logger.log(f'{self.__class__.__name__}: {num_qubits} qubits used')
        self.logger.log(f'Starting E91 protocol with {num_qubits} qubits.')

        # Step 1: Alice prepares the qubits
        key = [random.choice([0, 1]) for _ in range(num_qubits)]
        bases_alice = [random.choice([0, 1]) for _ in range(num_qubits)]
        qubits = self.prepare_e91_qubits(key, bases_alice)
        self.logger.log(f'Qubits prepared with key: {key} and bases: {bases_alice}')

        # Step 2: Transmit qubits from Alice to Bob (async)
        def on_transport_done(success):
            if not success:
                self.logger.log(f'Failed to transmit qubits from Alice to Bob.')
                self._context.clock.emit('e91_failed', alice=alice_id, bob=bob_id, reason='transport_failed')
                if on_complete is not None:
                    on_complete(success=False, key=None)
                return

            # Schedule the E91 round processing with its time cost
            cost = self._context.config.costs.e91_round
            self._context.clock.schedule(
                cost, self._e91_round_complete,
                alice_id=alice_id, bob_id=bob_id, num_bits=num_bits,
                final_key=final_key, key=key, bases_alice=bases_alice,
                qubits=qubits, num_qubits=num_qubits, on_complete=on_complete
            )

        self._transport_layer.run_transport_layer(alice_id, bob_id, num_qubits, on_complete=on_transport_done)

    def _e91_round_complete(self, alice_id, bob_id, num_bits, final_key, key, bases_alice, qubits, num_qubits, on_complete):
        """Process E91 round results at the scheduled timeslot, then loop."""
        self.logger.debug(f"E91 round completed at timeslot: {self._context.clock.now}")

        # Step 3: Bob chooses random bases and measures the qubits
        bases_bob = [random.choice([0, 1]) for _ in range(num_qubits)]
        results_bob = self.apply_bases_and_measure_e91(qubits, bases_bob)
        self.logger.log(f'Measurement results: {results_bob} with bases: {bases_bob}')

        # Step 4: Alice and Bob share their bases and find common indices
        common_indices = [i for i in range(len(bases_alice)) if bases_alice[i] == bases_bob[i]]
        self.logger.log(f'Common indices: {common_indices}')

        # Step 5: Key extraction based on common indices
        shared_key_alice = [key[i] for i in common_indices]
        shared_key_bob = [results_bob[i] for i in common_indices]

        # Step 6: Verify if keys match
        for a, b in zip(shared_key_alice, shared_key_bob):
            if a == b and len(final_key) < num_bits:
                final_key.append(a)

        self.logger.log(f"Keys obtained so far: {final_key}")

        # Continue loop (will check if we have enough bits)
        self._e91_loop(alice_id, bob_id, num_bits, final_key, on_complete)
