import math
from ..utils import Logger
from ..quantum import Qubit, Epr
from ..topology import Host
from ..exceptions import HostNotFoundError
from random import uniform
import random


def _compute_ttl(initial_fidelity, decoherence_rate, threshold):
    """
    Compute time-to-live (timeslots until fidelity drops below threshold).

    Returns:
        int: Number of timeslots from creation to death.
        None: If the entity never dies (no decoherence or rate >= 1.0).
    """
    if initial_fidelity <= threshold:
        return 0
    if decoherence_rate >= 1.0 or decoherence_rate <= 0.0:
        return None
    ttl = math.ceil(
        math.log(threshold / initial_fidelity) / math.log(decoherence_rate)
    )
    return max(0, ttl)


class PhysicalLayer:
    def __init__(self, context, physical_layer_id: int = 0):
        """
        Initialize the physical layer.

        Args:
            context (NetworkContext): Shared network context.
            physical_layer_id (int): Physical layer ID.
        """
        self._physical_layer_id = physical_layer_id
        self._context = context
        self._failed_eprs = []
        self._count_epr = 0
        self.logger = Logger.get_instance()


    def __str__(self):
        """ Return the string representation of the physical layer.

        Returns:
            str: String representation of the physical layer.
        """
        return f'Physical Layer {self.physical_layer_id}'

    @property
    def physical_layer_id(self):
        """Return the physical layer ID.

        Returns:
            int: Physical layer ID.
        """
        return self._physical_layer_id

    @property
    def failed_eprs(self):
        """Return the failed EPR pairs.

        Returns:
            dict: Dictionary of failed EPR pairs.
        """
        return self._failed_eprs

    def create_qubit(self, host_id: int, increment_qubits: bool = True):
        """Create a qubit and add it to the specified host's memory.

        Args:
            host_id (int): ID of the host where the qubit will be created.
            increment_qubits (bool): If True, increments the used qubits counter.

        Raises:
            Exception: If the specified host does not exist in the network.
        """
        if increment_qubits:
            self.logger.log(f'{self.__class__.__name__}: 1 qubit used')

        if host_id not in self._context.hosts:
            raise HostNotFoundError(f'Host {host_id} does not exist in the network.')

        qubit_id = self._context.generate_qubit_id()
        qubit = Qubit(
            qubit_id,
            clock=self._context.clock,
            decoherence_rate=self._context.config.decoherence.per_timeslot
        )
        self._context.hosts[host_id].add_qubit(qubit)

        self._context.clock.emit('qubit_created', host_id=host_id, qubit_id=qubit_id)
        self.logger.debug(f'Qubit {qubit_id} created with initial fidelity {qubit.initial_fidelity} and added to memory of Host {host_id}.')

        # Schedule TTL death
        ttl = _compute_ttl(
            qubit.initial_fidelity,
            self._context.config.decoherence.per_timeslot,
            self._context.config.decoherence.qubit_ttl_threshold
        )
        if ttl is not None and ttl > 0:
            self._context.clock.schedule(
                ttl, self._qubit_death_callback,
                qubit=qubit, host_id=host_id
            )
        elif ttl == 0:
            self._qubit_death_callback(qubit=qubit, host_id=host_id)

    def create_epr_pair(self, fidelity: float = 1.0, increment_eprs: bool = True):
        """Create an entangled qubit pair.

        Returns:
            Epr: Created EPR pair.
        """
        if increment_eprs:
            self.logger.log(f'{self.__class__.__name__}: 1 EPR used')

        epr = Epr(
            self._count_epr, fidelity,
            clock=self._context.clock,
            decoherence_rate=self._context.config.decoherence.per_timeslot
        )
        self._count_epr += 1
        self._context.clock.emit('epr_created', epr_id=epr.epr_id, fidelity=fidelity)
        return epr

    def add_epr_to_channel(self, epr: Epr, channel: tuple):
        """Add an EPR pair to the channel and schedule its TTL death.

        Args:
            epr (Epr): EPR pair.
            channel (tuple): Channel.
        """
        u, v = channel
        if not self._context.graph.has_edge(u, v):
            self._context.graph.add_edge(u, v, eprs=[])
        self._context.graph.edges[u, v]['eprs'].append(epr)
        self.logger.debug(f'EPR pair {epr} added to channel {channel}.')

        # Schedule TTL death
        ttl = _compute_ttl(
            epr.current_fidelity,
            self._context.config.decoherence.per_timeslot,
            self._context.config.decoherence.epr_ttl_threshold
        )
        if ttl is not None and ttl > 0:
            self._context.clock.schedule(
                ttl, self._epr_death_callback,
                epr=epr, channel=channel
            )

    def remove_epr_from_channel(self, epr: Epr, channel: tuple):
        """Remove an EPR pair from the channel.

        Args:
            epr (Epr): EPR pair to be removed.
            channel (tuple): Channel.
        """
        u, v = channel
        if not self._context.graph.has_edge(u, v):
            self.logger.debug(f'Channel {channel} does not exist.')
            return
        try:
            self._context.graph.edges[u, v]['eprs'].remove(epr)
            self.logger.debug(f'EPR pair {epr} removed from channel {channel}.')
        except ValueError:
            self.logger.debug(f'EPR pair {epr} not found in channel {channel}.')

    def _qubit_death_callback(self, qubit, host_id):
        """Remove an expired qubit from its host's memory (lazy deletion)."""
        host = self._context.hosts.get(host_id)
        if host is not None and qubit in host.memory:
            host.memory.remove(qubit)
            self._context.clock.emit(
                'qubit_expired', qubit_id=qubit.qubit_id, host_id=host_id
            )
            self.logger.debug(
                f'Qubit {qubit.qubit_id} expired and removed from Host {host_id} '
                f'at timeslot {self._context.clock.now}.'
            )

    def _epr_death_callback(self, epr, channel):
        """Remove an expired EPR from its channel (lazy deletion)."""
        u, v = channel
        try:
            eprs_list = self._context.graph.edges[u, v]['eprs']
            if epr in eprs_list:
                eprs_list.remove(epr)
                self._context.clock.emit(
                    'epr_expired', epr_id=epr.epr_id, channel=channel
                )
                self.logger.debug(
                    f'EPR {epr.epr_id} expired and removed from channel {channel} '
                    f'at timeslot {self._context.clock.now}.'
                )
        except (KeyError, ValueError):
            pass  # Channel or EPR already gone

    def fidelity_measurement_only_one(self, qubit: Qubit):
        """Measure the fidelity of a qubit.

        Args:
            qubit (Qubit): Qubit.

        Returns:
            float: Qubit fidelity.
        """
        fidelity = qubit.current_fidelity

        if self._context.clock.now > 0:
            # Apply decoherence factor per measurement
            new_fidelity = max(0, fidelity * self._context.config.decoherence.per_measurement)
            qubit.current_fidelity = new_fidelity
            self.logger.log(f'The fidelity of qubit {qubit} is {new_fidelity}')
            return new_fidelity

        self.logger.log(f'The fidelity of qubit {qubit} is {fidelity}')
        return fidelity

    def fidelity_measurement(self, qubit1: Qubit, qubit2: Qubit):
        """Measure and apply decoherence to two qubits, and log the result."""
        fidelity1 = self.fidelity_measurement_only_one(qubit1)
        fidelity2 = self.fidelity_measurement_only_one(qubit2)
        combined_fidelity = fidelity1 * fidelity2
        self.logger.log(f'The fidelity between qubit {fidelity1} and qubit {fidelity2} is {combined_fidelity}')
        return combined_fidelity

    def entanglement_creation_heralding_protocol(self, alice: Host, bob: Host, on_complete=None):
        """Schedule entanglement creation heralding protocol. Fire-and-forget.

        Result communicated via:
          - 'echp_success' or 'echp_low_fidelity' event
          - on_complete(success=True/False) callback if provided
        """
        cost = self._context.config.costs.heralding
        self._context.clock.schedule(
            cost, self._do_heralding,
            alice=alice, bob=bob, on_complete=on_complete
        )

    def _do_heralding(self, alice, bob, on_complete=None):
        """Execute heralding at the scheduled timeslot."""
        if not alice.memory or not bob.memory:
            self.logger.log(f'Timeslot {self._context.clock.now}: Heralding failed — insufficient qubits (Alice={alice.host_id}, Bob={bob.host_id}).')
            if on_complete is not None:
                on_complete(success=False)
            return

        self.logger.log(f'{self.__class__.__name__}: 2 qubits used')

        qubit1 = alice.consume_last_qubit()
        qubit2 = bob.consume_last_qubit()

        q1 = qubit1.current_fidelity
        q2 = qubit2.current_fidelity

        epr_fidelity = q1 * q2
        self.logger.log(f'Timeslot {self._context.clock.now}: EPR pair created with fidelity {epr_fidelity}')
        epr = self.create_epr_pair(epr_fidelity)

        alice_host_id = alice.host_id
        bob_host_id = bob.host_id

        if epr_fidelity >= self._context.config.fidelity.epr_threshold:
            self.add_epr_to_channel(epr, (alice_host_id, bob_host_id))
            self._context.clock.emit('echp_success', alice=alice_host_id, bob=bob_host_id, fidelity=epr_fidelity)
            self.logger.log(f'Timeslot {self._context.clock.now}: Entanglement creation protocol succeeded with required fidelity.')
            success = True
        else:
            self.add_epr_to_channel(epr, (alice_host_id, bob_host_id))
            self._failed_eprs.append(epr)
            self._context.clock.emit('echp_low_fidelity', alice=alice_host_id, bob=bob_host_id, fidelity=epr_fidelity)
            self.logger.log(f'Timeslot {self._context.clock.now}: Entanglement creation protocol succeeded, but with low fidelity.')
            success = False

        if on_complete is not None:
            on_complete(success=success, epr_fidelity=epr_fidelity)

    def echp(self, alice_host_id: int, bob_host_id: int, mode: str, on_complete=None):
        """Schedule ECHP. Fire-and-forget.

        Args:
            alice_host_id (int): Alice Host ID.
            bob_host_id (int): Bob Host ID.
            mode (str): 'on_demand' or 'on_replay'.
            on_complete: Optional callback(success=bool).
        """
        cost = self._context.config.costs.on_demand if mode == 'on_demand' else self._context.config.costs.replay
        self._context.clock.schedule(
            cost, self._do_echp,
            alice_host_id=alice_host_id, bob_host_id=bob_host_id,
            mode=mode, on_complete=on_complete
        )

    def _do_echp(self, alice_host_id, bob_host_id, mode, on_complete=None):
        """Execute ECHP at the scheduled timeslot."""
        alice = self._context.hosts[alice_host_id]
        bob = self._context.hosts[bob_host_id]

        if not alice.memory or not bob.memory:
            self.logger.log(f'Timeslot {self._context.clock.now}: {mode} ECHP failed — insufficient qubits (Alice={alice_host_id}, Bob={bob_host_id}).')
            if on_complete is not None:
                on_complete(success=False)
            return

        self.logger.log(f'{self.__class__.__name__}: 2 qubits used')

        qubit1 = alice.consume_last_qubit()
        qubit2 = bob.consume_last_qubit()

        fidelity_qubit1 = self.fidelity_measurement_only_one(qubit1)
        fidelity_qubit2 = self.fidelity_measurement_only_one(qubit2)

        prob_key = 'prob_on_demand_epr_create' if mode == 'on_demand' else 'prob_replay_epr_create'
        prob = self._context.graph.edges[alice_host_id, bob_host_id][prob_key]
        echp_success_probability = prob * fidelity_qubit1 * fidelity_qubit2

        if uniform(0, 1) < echp_success_probability:
            self.logger.log(f'Timeslot {self._context.clock.now}: EPR pair created with fidelity {fidelity_qubit1 * fidelity_qubit2}')
            epr = self.create_epr_pair(fidelity_qubit1 * fidelity_qubit2)
            self.add_epr_to_channel(epr, (alice_host_id, bob_host_id))
            self._context.clock.emit(f'echp_{mode}_success', alice=alice_host_id, bob=bob_host_id)
            self.logger.log(f'Timeslot {self._context.clock.now}: ECHP success probability is {echp_success_probability}')
            success = True
        else:
            self._context.clock.emit(f'echp_{mode}_failed', alice=alice_host_id, bob=bob_host_id)
            self.logger.log(f'Timeslot {self._context.clock.now}: ECHP success probability failed.')
            success = False

        if on_complete is not None:
            on_complete(success=success)
