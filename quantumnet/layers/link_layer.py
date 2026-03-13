import networkx as nx
from ..topology import Host
from ..utils import Logger
from ..quantum import Epr
from random import uniform

class LinkLayer:
    def __init__(self, context, physical_layer):
        """
        Initialize the link layer.

        Args:
            context (NetworkContext): Shared network context.
            physical_layer (PhysicalLayer): Physical layer.
        """
        self._context = context
        self._physical_layer = physical_layer
        self._failed_request_count = 0
        self.logger = Logger.get_instance()

    @property
    def failed_request_count(self):
        return self._failed_request_count

    def __str__(self):
        """ Return the string representation of the link layer.

        Returns:
            str: String representation of the link layer.
        """
        return 'Link Layer'

    def request(self, alice_id: int, bob_id: int, on_complete=None):
        """
        Schedule entanglement creation between Alice and Bob. Fire-and-forget.

        Result communicated via:
          - 'link_request_success' or 'link_request_failed' event
          - on_complete(success=True/False) callback if provided

        Args:
            alice_id (int): Alice host ID.
            bob_id (int): Bob host ID.
            on_complete: Optional callback(success=bool).
        """
        self._start_attempt(alice_id, bob_id, attempt=1, failures=0, on_complete=on_complete)

    def _start_attempt(self, alice_id, bob_id, attempt, failures, on_complete):
        """Schedule the next heralding attempt or fall back to purification."""
        max_attempts = self._context.config.protocol.link_max_attempts

        if attempt > max_attempts:
            # All attempts failed; try purification if enough failures in this request
            if failures >= self._context.config.protocol.link_purification_after_failures:
                self.purification(alice_id, bob_id, on_complete=on_complete)
            else:
                self._context.clock.emit('link_request_failed',
                                          alice=alice_id, bob=bob_id)
                if on_complete is not None:
                    on_complete(success=False)
            return

        try:
            alice = self._context.get_host(alice_id)
            bob = self._context.get_host(bob_id)
        except KeyError:
            self.logger.log(f'Host {alice_id} or {bob_id} not found in network.')
            if on_complete is not None:
                on_complete(success=False)
            return

        self._context.clock.emit('link_request_attempt',
                                  alice=alice_id, bob=bob_id, attempt=attempt)
        self.logger.log(f'Timeslot {self._context.clock.now}: Entanglement attempt between {alice_id} and {bob_id}.')

        # Define what happens when heralding completes
        def on_heralding_done(success, epr_fidelity=None):
            if success:
                self.logger.log(f'{self.__class__.__name__}: 1 EPR used')
                self.logger.log(f'{self.__class__.__name__}: 2 qubits used')
                self.logger.log(f'Timeslot {self._context.clock.now}: Entanglement created between {alice_id} and {bob_id} on attempt {attempt}.')
                self._context.clock.emit('link_request_success',
                                          alice=alice_id, bob=bob_id, fidelity=epr_fidelity)
                if on_complete is not None:
                    on_complete(success=True)
            else:
                self.logger.log(f'Timeslot {self._context.clock.now}: Entanglement failed between {alice_id} and {bob_id} on attempt {attempt}.')
                self._failed_request_count += 1
                # Retry: schedule next attempt
                self._start_attempt(alice_id, bob_id, attempt + 1, failures + 1, on_complete)

        # Schedule heralding (async, result comes via on_heralding_done)
        self._physical_layer.entanglement_creation_heralding_protocol(
            alice, bob, on_complete=on_heralding_done
        )

    def purification_calculator(self, f1: float, f2: float, purification_type: int) -> float:
        """
        Purification formula calculation.

        Args:
            f1 (float): Fidelity of the first EPR.
            f2 (float): Fidelity of the second EPR.
            purification_type (int): Chosen formula (1 - Default, 2 - BBPSSW Protocol, 3 - DEJMPS Protocol).

        Returns:
            float: Fidelity after purification.
        """
        f1f2 = f1 * f2

        if purification_type == 1:
            self.logger.log('Purification type 1 was used.')
            return f1f2 / ((f1f2) + ((1 - f1) * (1 - f2)))

        elif purification_type == 2:
            result = (f1f2 + ((1 - f1) / 3) * ((1 - f2) / 3)) / (f1f2 + f1 * ((1 - f2) / 3) + f2 * ((1 - f1) / 3) + 5 * ((1 - f1) / 3) * ((1 - f2) / 3))
            self.logger.log('Purification type 2 was used.')
            return result

        elif purification_type == 3:
            result = (2 * f1f2 + 1 - f1 - f2) / ((1 / 4) * (f1 + f2 - f1f2) + 3 / 4)
            self.logger.log('Purification type 3 was used.')
            return result

        self.logger.log('Purification only accepts values (1, 2, or 3), formula 1 was chosen by default.')
        return f1f2 / ((f1f2) + ((1 - f1) * (1 - f2)))

    def purification(self, alice_id: int, bob_id: int, purification_type: int = 1, on_complete=None):
        """
        Schedule EPR purification. Fire-and-forget.

        Args:
            alice_id (int): Alice host ID.
            bob_id (int): Bob host ID.
            purification_type (int): Purification protocol type.
            on_complete: Optional callback(success=bool).
        """
        cost = self._context.config.costs.purification
        self._context.clock.schedule(
            cost, self._do_purification,
            alice_id=alice_id, bob_id=bob_id,
            purification_type=purification_type, on_complete=on_complete
        )

    def _do_purification(self, alice_id, bob_id, purification_type, on_complete):
        """Execute purification at the scheduled timeslot."""
        eprs_fail = self._physical_layer.failed_eprs

        if len(eprs_fail) < 2:
            self.logger.log(f'Timeslot {self._context.clock.now}: Not enough EPRs for purification on channel ({alice_id}, {bob_id}).')
            if on_complete is not None:
                on_complete(success=False)
            return

        eprs_fail1 = eprs_fail[-1]
        eprs_fail2 = eprs_fail[-2]
        f1 = eprs_fail1.current_fidelity
        f2 = eprs_fail2.current_fidelity

        purification_prob = (f1 * f2) + ((1 - f1) * (1 - f2))

        self.logger.log(f'{self.__class__.__name__}: 2 EPRs used')
        self.logger.log(f'{self.__class__.__name__}: 4 qubits used')

        success = False
        if purification_prob > self._context.config.fidelity.purification_min_probability:
            new_fidelity = self.purification_calculator(f1, f2, purification_type)

            if new_fidelity > self._context.config.fidelity.purification_threshold:
                epr_purified = Epr(
                    (alice_id, bob_id), new_fidelity,
                    clock=self._context.clock,
                    decoherence_rate=self._context.config.decoherence.per_timeslot
                )
                self._physical_layer.add_epr_to_channel(epr_purified, (alice_id, bob_id))
                self._physical_layer.failed_eprs.remove(eprs_fail1)
                self._physical_layer.failed_eprs.remove(eprs_fail2)
                self._context.clock.emit('purification_success', alice=alice_id, bob=bob_id, fidelity=new_fidelity)
                self.logger.log(f'Timeslot {self._context.clock.now}: Purification succeeded on channel ({alice_id}, {bob_id}) with new fidelity {new_fidelity}.')
                success = True
            else:
                self._physical_layer.failed_eprs.remove(eprs_fail1)
                self._physical_layer.failed_eprs.remove(eprs_fail2)
                self._context.clock.emit('purification_failed', alice=alice_id, bob=bob_id, reason='low_fidelity')
                self.logger.log(f'Timeslot {self._context.clock.now}: Purification failed on channel ({alice_id}, {bob_id}) due to low fidelity after purification.')
        else:
            self._physical_layer.failed_eprs.remove(eprs_fail1)
            self._physical_layer.failed_eprs.remove(eprs_fail2)
            self._context.clock.emit('purification_failed', alice=alice_id, bob=bob_id, reason='low_probability')
            self.logger.log(f'Timeslot {self._context.clock.now}: Purification failed on channel ({alice_id}, {bob_id}) due to low purification success probability.')

        if on_complete is not None:
            on_complete(success=success)

