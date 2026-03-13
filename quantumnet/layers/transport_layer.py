from ..utils import Logger

class TransportLayer:
    def __init__(self, context, network_layer, physical_layer):
        """
        Initialize the transport layer.

        Args:
            context (NetworkContext): Shared network context.
            network_layer (NetworkLayer): Network layer.
            physical_layer (PhysicalLayer): Physical layer.
        """
        self._context = context
        self._physical_layer = physical_layer
        self._network_layer = network_layer
        self.logger = Logger.get_instance()

    def __str__(self):
        """ Return the string representation of the transport layer.

        Returns:
            str: String representation of the transport layer."""
        return f'Transport Layer'

    def run_transport_layer(self, alice_id: int, bob_id: int, num_qubits: int, on_complete=None):
        """
        Schedule the transmission request and teleportation protocol. Fire-and-forget.

        Result communicated via:
          - 'transport_complete' or 'transport_failed' event
          - on_complete(success=True/False) callback if provided

        Args:
            alice_id (int): Alice host ID.
            bob_id (int): Bob host ID.
            num_qubits (int): Number of qubits to transmit.
            on_complete: Optional callback(success=bool).
        """
        alice = self._context.get_host(alice_id)
        available_qubits = len(alice.memory)

        # If Alice has fewer qubits than needed, create more via scheduled chain
        if available_qubits < num_qubits:
            qubits_needed = num_qubits - available_qubits
            self.logger.log(f'Insufficient qubits in Alice memory (Host {alice_id}). Creating {qubits_needed} more qubits to complete the {num_qubits} needed.')
            self._create_qubits_chain(alice_id, bob_id, num_qubits, qubits_needed, 0, on_complete)
        else:
            # All qubits available, proceed directly to transmission
            self._do_transmission(alice_id, bob_id, num_qubits, on_complete)

    def _create_qubits_chain(self, alice_id, bob_id, num_qubits, total_to_create, created_so_far, on_complete):
        """Schedule creation of one qubit, then chain to the next or to transmission."""
        if created_so_far >= total_to_create:
            # All qubits created, proceed to transmission
            self._do_transmission(alice_id, bob_id, num_qubits, on_complete)
            return

        cost = self._context.config.costs.qubit_creation
        self._context.clock.schedule(
            cost, self._create_one_qubit,
            alice_id=alice_id, bob_id=bob_id, num_qubits=num_qubits,
            total_to_create=total_to_create, created_so_far=created_so_far,
            on_complete=on_complete
        )

    def _create_one_qubit(self, alice_id, bob_id, num_qubits, total_to_create, created_so_far, on_complete):
        """Create one qubit at the scheduled timeslot, then continue the chain."""
        self._physical_layer.create_qubit(alice_id)
        self.logger.log(f"Qubit created for Alice (Host {alice_id}) at timeslot: {self._context.clock.now}")

        self._create_qubits_chain(
            alice_id, bob_id, num_qubits, total_to_create,
            created_so_far + 1, on_complete
        )

    def _do_transmission(self, alice_id, bob_id, num_qubits, on_complete):
        """Execute the actual qubit transmission/teleportation logic."""
        alice = self._context.get_host(alice_id)
        bob = self._context.get_host(bob_id)
        available_qubits = len(alice.memory)

        # Ensure Alice has enough qubits
        if available_qubits < num_qubits:
            self.logger.log(f'Error: Alice has {available_qubits} qubits, but needs {num_qubits}. Aborting transmission.')
            self._context.clock.emit('transport_failed', alice=alice_id, bob=bob_id, delivered=0, requested=num_qubits)
            if on_complete is not None:
                on_complete(success=False)
            return

        # Start qubit transmission
        max_attempts = self._context.config.protocol.transport_max_attempts
        attempts = 0
        success_count = 0

        while attempts < max_attempts and success_count < num_qubits:
            self.logger.log(f'Attempt {attempts + 1} of qubit transmission between {alice_id} and {bob_id}.')

            for _ in range(num_qubits - success_count):
                # Try to find a valid route
                route = self._network_layer.short_route_valid(alice_id, bob_id)

                if route is None:
                    self.logger.log(f'Could not find a valid route on attempt {attempts + 1}. Timeslot: {self._context.clock.now}')
                    break

                # Check EPR pair fidelity along the route
                fidelities = []
                for i in range(len(route) - 1):
                    node1 = route[i]
                    node2 = route[i + 1]

                    epr_pairs = self._context.get_eprs_from_edge(node1, node2)
                    if len(epr_pairs) == 0:
                        self.logger.log(f'Could not find enough EPR pairs on route {route[i]} -> {route[i + 1]}.')
                        break
                    fidelities.extend([epr.current_fidelity for epr in epr_pairs])

                # If failed to find enough EPR pairs, try on next attempt
                if len(fidelities) == 0:
                    attempts += 1
                    continue

                f_route = sum(fidelities) / len(fidelities)

                # If route is found, transmit the qubit immediately
                if len(alice.memory) > 0:  # Check if Alice still has qubits in memory
                    qubit_alice = alice.memory.pop(0)  # REMOVE qubit from Alice
                    f_alice = qubit_alice.current_fidelity
                    F_final = f_alice * f_route

                    # Add transmitted qubit to Bob's memory
                    qubit_alice.current_fidelity = F_final
                    bob.memory.append(qubit_alice)

                    success_count += 1
                    self.logger.log(f'{self.__class__.__name__}: 1 qubit used')
                    self._context.clock.emit(
                        'qubit_teleported',
                        alice=alice_id, bob=bob_id,
                        fidelity=F_final,
                        fidelity_alice=f_alice,
                        fidelity_route=f_route,
                        route_len=len(route) - 1,
                    )
                    self.logger.log(f'Qubit teleportation from {alice_id} to {bob_id} on route {route} succeeded with final fidelity {F_final}.')
                else:
                    self.logger.log(f'Alice does not have enough qubits to continue transmission.')
                    break

            attempts += 1

        if success_count == num_qubits:
            self._context.clock.emit('transport_complete', alice=alice_id, bob=bob_id, count=num_qubits)
            self.logger.log(f'Transmission and teleportation of {num_qubits} qubits between {alice_id} and {bob_id} completed successfully. Timeslot: {self._context.clock.now}')
            if on_complete is not None:
                on_complete(success=True)
        else:
            self._context.clock.emit('transport_failed', alice=alice_id, bob=bob_id, delivered=success_count, requested=num_qubits)
            self.logger.log(f'Failed to transmit {num_qubits} qubits between {alice_id} and {bob_id}. Only {success_count} qubits were transmitted successfully. Timeslot: {self._context.clock.now}')
            if on_complete is not None:
                on_complete(success=False)
