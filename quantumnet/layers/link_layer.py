import random
import math
from ..utils import Logger


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

    # ------------------------------------------------------------------ #
    #  Link Request (existing)                                            #
    # ------------------------------------------------------------------ #

    def request(self, alice_id: int, bob_id: int, high_fidelity: bool = True, on_complete=None):
        """
        Schedule entanglement creation between Alice and Bob. Fire-and-forget.

        Result communicated via:
          - 'link_request_success' or 'link_request_failed' event
          - on_complete(success=True/False) callback if provided

        Args:
            alice_id (int): Alice host ID.
            bob_id (int): Bob host ID.
            high_fidelity (bool): If True (default), only accept EPR pairs above the
                fidelity threshold and attempt purification on failure. If False,
                accept any successfully created EPR pair regardless of fidelity.
            on_complete: Optional callback(success=bool).
        """
        self._start_attempt(alice_id, bob_id, attempt=1, failures=0, high_fidelity=high_fidelity, on_complete=on_complete)

    def _start_attempt(self, alice_id, bob_id, attempt, failures, high_fidelity, on_complete):
        """Schedule the next heralding attempt or give up."""
        max_attempts = self._context.config.protocol.link_max_attempts

        if attempt > max_attempts:
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
                self._start_attempt(alice_id, bob_id, attempt + 1, failures + 1, high_fidelity, on_complete)

        # Schedule heralding (async, result comes via on_heralding_done)
        self._physical_layer.entanglement_creation_heralding_protocol(
            alice, bob, high_fidelity=high_fidelity, on_complete=on_heralding_done
        )

    # ------------------------------------------------------------------ #
    #  RF1 — Motor Probabilístico de Erro de Canal                       #
    # ------------------------------------------------------------------ #

    def channel_error_engine(self, f1: float, f2: float, noise_type: str):
        """
        Probabilistic channel error engine (Calculator).

        Given two EPR fidelities and a channel noise type, computes the
        success probability and the new fidelity after purification.

        Args:
            f1: Fidelity of the first EPR pair.
            f2: Fidelity of the second EPR pair.
            noise_type: Channel noise type — 'bit-flip', 'werner', or 'bitflip+werner'.

        Returns:
            tuple: (p_success, f_new)
        """
        if noise_type == 'bitflip+werner':
            # Mixed: randomly pick one of the two formulas (50/50)
            noise_type = random.choice(['bit-flip', 'werner'])

        if noise_type == 'bit-flip':
            p_success = f1 * f2 + (1 - f1) * (1 - f2)
            f_new = (f1 * f2) / p_success if p_success > 0 else 0.0
        elif noise_type == 'werner':
            p_success = ((f1 + (1 - f1) / 3) * (f2 + (1 - f2) / 3)
                         + (2 * (1 - f1) / 3) * (2 * (1 - f2) / 3))
            # Werner new fidelity
            f1f2 = f1 * f2
            numer = f1f2 + ((1 - f1) / 3) * ((1 - f2) / 3)
            f_new = numer / p_success if p_success > 0 else 0.0
        else:
            # Default to bit-flip for unknown types
            self.logger.log(f'Unknown noise type "{noise_type}", defaulting to bit-flip.')
            p_success = f1 * f2 + (1 - f1) * (1 - f2)
            f_new = (f1 * f2) / p_success if p_success > 0 else 0.0

        return p_success, f_new

    def _attempt_purification(self, epr1, epr2, noise_type: str):
        """
        Attempt a single purification step (RF1.3).

        Consumes two EPR pairs, rolls a random number against the success
        probability, and returns the result.

        Args:
            epr1: First EPR pair.
            epr2: Second EPR pair.
            noise_type: Channel noise type.

        Returns:
            tuple: (success: bool, f_new: float or None)
        """
        f1 = epr1.current_fidelity
        f2 = epr2.current_fidelity
        p_success, f_new = self.channel_error_engine(f1, f2, noise_type)

        roll = random.random()
        if roll <= p_success:
            return True, f_new
        else:
            return False, None

    # ------------------------------------------------------------------ #
    #  RF2 — Estratégias de Purificação Básicas                          #
    # ------------------------------------------------------------------ #

    def _get_noise_type(self, alice_id: int, bob_id: int) -> str:
        """Retrieve the noise type for the channel between alice and bob."""
        try:
            return self._context.graph.edges[alice_id, bob_id]['noise_type']
        except KeyError:
            return self._context.config.defaults.channel_noise_type

    def _apply_decoherence_to_pool(self, eprs):
        """
        Apply one timeslot of decoherence to idle EPR pairs waiting between
        rounds (RF2.3). Mutates the fidelity in-place via the setter so the
        lazy-evaluation base is reset.
        """
        rate = self._context.config.decoherence.per_timeslot
        for epr in eprs:
            epr.current_fidelity = epr.current_fidelity * rate

    def purification_symmetric(self, alice_id: int, bob_id: int, num_rounds: int,
                                pool=None, on_complete=None):
        """
        Symmetric (tree) purification strategy (RF2.1).

        Starts with 2^r EPR pairs (where r = num_rounds). In each round,
        pairs are grouped two-by-two and purified. Only successful pairs
        advance to the next round.

        Uses the hybrid scheduler backup pool (RF3) if provided.

        Args:
            alice_id: Alice host ID.
            bob_id: Bob host ID.
            num_rounds: Number of purification rounds (r).
            pool: Optional list of backup EPR pairs (RF3).
            on_complete: Optional callback(success: bool, epr=Epr or None).
        """
        needed = 2 ** num_rounds
        noise_type = self._get_noise_type(alice_id, bob_id)
        channel = (alice_id, bob_id)
        if pool is None:
            pool = []

        def _run():
            # Collect initial EPR pairs from channel
            eprs_on_channel = self._context.get_eprs_from_edge(alice_id, bob_id)
            initial_pairs = []
            for _ in range(min(needed, len(eprs_on_channel))):
                epr = eprs_on_channel[-1]
                self._physical_layer.remove_epr_from_channel(epr, channel)
                initial_pairs.append(epr)

            # Fill from pool if not enough
            while len(initial_pairs) < needed and pool:
                initial_pairs.append(pool.pop(0))

            if len(initial_pairs) < needed:
                self._context.clock.emit(
                    'purification_failed', alice=alice_id, bob=bob_id,
                    strategy='symmetric', reason='insufficient_eprs',
                    needed=needed, available=len(initial_pairs))
                if on_complete:
                    on_complete(success=False, epr=None)
                return

            self._context.clock.emit(
                'purification_started', alice=alice_id, bob=bob_id,
                strategy='symmetric', rounds=num_rounds,
                initial_pairs=len(initial_pairs), pool_size=len(pool))

            current = initial_pairs

            for rnd in range(1, num_rounds + 1):
                # Apply decoherence to idle pairs waiting between rounds
                if rnd > 1:
                    self._apply_decoherence_to_pool(current)

                next_round = []
                i = 0
                while i + 1 < len(current):
                    success, f_new = self._attempt_purification(
                        current[i], current[i + 1], noise_type)
                    if success:
                        new_epr = self._physical_layer.create_epr_pair(fidelity=f_new)
                        next_round.append(new_epr)
                        self._context.clock.emit(
                            'purification_round_success', alice=alice_id, bob=bob_id,
                            round=rnd, fidelity=f_new)
                    else:
                        # RF3.2/3.3 — Try backup from pool
                        replaced = False
                        while len(pool) >= 2:
                            backup1 = pool.pop(0)
                            backup2 = pool.pop(0)
                            s2, f2 = self._attempt_purification(backup1, backup2, noise_type)
                            if s2:
                                new_epr = self._physical_layer.create_epr_pair(fidelity=f2)
                                next_round.append(new_epr)
                                self._context.clock.emit(
                                    'purification_pool_recovery', alice=alice_id, bob=bob_id,
                                    round=rnd, fidelity=f2, pool_remaining=len(pool))
                                replaced = True
                                break
                        if not replaced:
                            self._context.clock.emit(
                                'purification_round_failed', alice=alice_id, bob=bob_id,
                                round=rnd)
                    i += 2

                current = next_round
                if not current:
                    self._context.clock.emit(
                        'purification_failed', alice=alice_id, bob=bob_id,
                        strategy='symmetric', reason='all_rounds_failed', round=rnd)
                    if on_complete:
                        on_complete(success=False, epr=None)
                    return

            # After all rounds, place surviving EPRs on channel
            for epr in current:
                self._physical_layer.add_epr_to_channel(epr, channel)

            best = max(current, key=lambda e: e.current_fidelity)
            self._context.clock.emit(
                'purification_success', alice=alice_id, bob=bob_id,
                strategy='symmetric', fidelity=best.current_fidelity,
                surviving_pairs=len(current))
            if on_complete:
                on_complete(success=True, epr=best)

        cost = self._context.config.costs.purification
        self._context.clock.schedule(cost, _run)

    def purification_pumping(self, alice_id: int, bob_id: int, num_rounds: int,
                              pool=None, on_complete=None):
        """
        Pumping (linear) purification strategy (RF2.2).

        Starts with 2 EPR pairs in the first round. At each subsequent round
        the purified pair from the previous iteration is combined with 1 new
        EPR pair.

        Uses the hybrid scheduler backup pool (RF3) if provided.

        Args:
            alice_id: Alice host ID.
            bob_id: Bob host ID.
            num_rounds: Number of purification rounds.
            pool: Optional list of backup EPR pairs (RF3).
            on_complete: Optional callback(success: bool, epr=Epr or None).
        """
        needed = num_rounds + 1  # 2 for first round + 1 per subsequent round
        noise_type = self._get_noise_type(alice_id, bob_id)
        channel = (alice_id, bob_id)
        if pool is None:
            pool = []

        def _run():
            eprs_on_channel = self._context.get_eprs_from_edge(alice_id, bob_id)
            collected = []
            for _ in range(min(needed, len(eprs_on_channel))):
                epr = eprs_on_channel[-1]
                self._physical_layer.remove_epr_from_channel(epr, channel)
                collected.append(epr)

            while len(collected) < needed and pool:
                collected.append(pool.pop(0))

            if len(collected) < 2:
                self._context.clock.emit(
                    'purification_failed', alice=alice_id, bob=bob_id,
                    strategy='pumping', reason='insufficient_eprs',
                    needed=2, available=len(collected))
                if on_complete:
                    on_complete(success=False, epr=None)
                return

            self._context.clock.emit(
                'purification_started', alice=alice_id, bob=bob_id,
                strategy='pumping', rounds=num_rounds,
                initial_pairs=len(collected), pool_size=len(pool))

            # First round: combine first two pairs
            main_pair = collected.pop(0)
            feed_pair = collected.pop(0)

            for rnd in range(1, num_rounds + 1):
                # Apply decoherence to main pair between rounds
                if rnd > 1:
                    self._apply_decoherence_to_pool([main_pair])

                success, f_new = self._attempt_purification(main_pair, feed_pair, noise_type)

                if success:
                    main_pair = self._physical_layer.create_epr_pair(fidelity=f_new)
                    self._context.clock.emit(
                        'purification_round_success', alice=alice_id, bob=bob_id,
                        round=rnd, fidelity=f_new)
                else:
                    # RF3.2/3.3 — Try to recover from pool
                    recovered = False
                    while pool:
                        backup = pool.pop(0)
                        # Get another pair: from collected or pool
                        partner = None
                        if collected:
                            partner = collected.pop(0)
                        elif pool:
                            partner = pool.pop(0)

                        if partner is None:
                            break

                        s2, f2 = self._attempt_purification(backup, partner, noise_type)
                        if s2:
                            main_pair = self._physical_layer.create_epr_pair(fidelity=f2)
                            self._context.clock.emit(
                                'purification_pool_recovery', alice=alice_id, bob=bob_id,
                                round=rnd, fidelity=f2, pool_remaining=len(pool))
                            recovered = True
                            break

                    if not recovered:
                        self._context.clock.emit(
                            'purification_failed', alice=alice_id, bob=bob_id,
                            strategy='pumping', reason='pool_exhausted', round=rnd)
                        if on_complete:
                            on_complete(success=False, epr=None)
                        return

                # Get next feed pair for the next round
                if rnd < num_rounds:
                    if collected:
                        feed_pair = collected.pop(0)
                    elif pool:
                        feed_pair = pool.pop(0)
                    else:
                        # No more pairs, but the current round succeeded
                        # so we stop early with what we have
                        self._context.clock.emit(
                            'purification_early_stop', alice=alice_id, bob=bob_id,
                            strategy='pumping', reason='no_more_pairs',
                            completed_rounds=rnd, fidelity=main_pair.current_fidelity)
                        break

            # Place the surviving pair on the channel
            self._physical_layer.add_epr_to_channel(main_pair, channel)
            self._context.clock.emit(
                'purification_success', alice=alice_id, bob=bob_id,
                strategy='pumping', fidelity=main_pair.current_fidelity,
                surviving_pairs=1)
            if on_complete:
                on_complete(success=True, epr=main_pair)

        cost = self._context.config.costs.purification
        self._context.clock.schedule(cost, _run)

    # ------------------------------------------------------------------ #
    #  RF3 — Agendador Híbrido (Controlador com Backup)                  #
    # ------------------------------------------------------------------ #

    def _estimate_initial_pairs(self, strategy: str, num_rounds: int) -> int:
        """
        Estimate the number of EPR pairs needed for a purification run (RF4.3).

        Args:
            strategy: 'symmetric' or 'pumping'.
            num_rounds: Number of rounds.

        Returns:
            int: Estimated number of required pairs.
        """
        if strategy == 'symmetric':
            return 2 ** num_rounds
        else:  # pumping
            return num_rounds + 1

    def run_purification(self, alice_id: int, bob_id: int,
                          strategy: str = 'symmetric',
                          num_rounds: int = 2,
                          pool_size: int = 0,
                          on_complete=None):
        """
        Hybrid scheduler: orchestrates purification with a backup pool (RF3).

        Provisions the required EPR pairs, allocates a backup pool, and
        delegates to the chosen strategy. If the strategy encounters a
        failure, it transparently consumes backup pairs from the pool before
        aborting.

        Args:
            alice_id: Alice host ID.
            bob_id: Bob host ID.
            strategy: 'symmetric' or 'pumping'.
            num_rounds: Number of purification rounds (r).
            pool_size: Number of extra backup EPR pairs to pre-allocate.
            on_complete: Optional callback(success: bool, epr=Epr or None).
        """
        channel = (alice_id, bob_id)
        needed = self._estimate_initial_pairs(strategy, num_rounds)

        def _provision():
            eprs_on_channel = self._context.get_eprs_from_edge(alice_id, bob_id)
            total_needed = needed + pool_size
            available = len(eprs_on_channel)

            if available < total_needed:
                self._context.clock.emit(
                    'purification_provision_warning', alice=alice_id, bob=bob_id,
                    needed=total_needed, available=available)

            # Build backup pool from channel EPRs beyond the needed ones
            pool = []
            # Take pool_size pairs for backup (from the end of available pairs)
            take_for_pool = min(pool_size, max(0, available - needed))
            for _ in range(take_for_pool):
                epr = eprs_on_channel[-1]
                self._physical_layer.remove_epr_from_channel(epr, channel)
                pool.append(epr)

            # If we couldn't fill the pool from beyond the needed pairs,
            # create additional EPR pairs
            remaining_pool = pool_size - len(pool)
            for _ in range(remaining_pool):
                epr = self._physical_layer.create_epr_pair(
                    fidelity=self._context.config.fidelity.initial_epr_fidelity)
                pool.append(epr)

            self._context.clock.emit(
                'purification_provisioned', alice=alice_id, bob=bob_id,
                strategy=strategy, rounds=num_rounds,
                estimated_pairs=needed, pool_size=len(pool))

            # Dispatch to strategy
            if strategy == 'symmetric':
                self.purification_symmetric(
                    alice_id, bob_id, num_rounds, pool=pool, on_complete=on_complete)
            elif strategy == 'pumping':
                self.purification_pumping(
                    alice_id, bob_id, num_rounds, pool=pool, on_complete=on_complete)
            else:
                self.logger.log(f'Unknown strategy "{strategy}", defaulting to symmetric.')
                self.purification_symmetric(
                    alice_id, bob_id, num_rounds, pool=pool, on_complete=on_complete)

        # Schedule provisioning at the current timeslot
        self._context.clock.schedule(0, _provision)

    # ------------------------------------------------------------------ #
    #  Legacy purification (single-step, kept for backwards compat)       #
    # ------------------------------------------------------------------ #

    def purification(self, alice_id: int, bob_id: int, purification_type: int = 1, on_complete=None):
        """
        Single-step purification: consumes two EPR pairs from the channel and
        replaces them with one higher-fidelity pair.

        Result communicated via:
          - 'purification_success' or 'purification_failed' event
          - on_complete(success=True/False) callback if provided

        Args:
            alice_id (int): Alice host ID.
            bob_id (int): Bob host ID.
            purification_type (int): Protocol variant (1=Default, 2=BBPSSW, 3=DEJMPS).
            on_complete: Optional callback(success=bool).
        """
        def _run():
            eprs = self._context.get_eprs_from_edge(alice_id, bob_id)
            if len(eprs) < 2:
                self._context.clock.emit('purification_failed',
                                          alice=alice_id, bob=bob_id, reason='insufficient_eprs')
                if on_complete is not None:
                    on_complete(success=False)
                return

            epr1, epr2 = eprs[-1], eprs[-2]
            self._physical_layer.remove_epr_from_channel(epr1, (alice_id, bob_id))
            self._physical_layer.remove_epr_from_channel(epr2, (alice_id, bob_id))

            f_purified = self.purification_calculator(
                epr1.current_fidelity, epr2.current_fidelity, purification_type
            )
            epr_new = self._physical_layer.create_epr_pair(fidelity=f_purified)
            self._physical_layer.add_epr_to_channel(epr_new, (alice_id, bob_id))

            self._context.clock.emit('purification_success',
                                      alice=alice_id, bob=bob_id, fidelity=f_purified)
            if on_complete is not None:
                on_complete(success=True)

        cost = self._context.config.costs.purification
        self._context.clock.schedule(cost, _run)

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
        # Bit-flip
        if purification_type == 1:
            self.logger.log('Purification type 1 was used.')
            return f1f2 / ((f1f2) + ((1 - f1) * (1 - f2)))
        # BBPSSW
        elif purification_type == 2:
            result = (f1f2 + ((1 - f1) / 3) * ((1 - f2) / 3)) / (f1f2 + f1 * ((1 - f2) / 3) + f2 * ((1 - f1) / 3) + 5 * ((1 - f1) / 3) * ((1 - f2) / 3))
            self.logger.log('Purification type 2 was used.')
            return result
        #DEJMPS
        elif purification_type == 3:
            result = (2 * f1f2 + 1 - f1 - f2) / ((1 / 4) * (f1 + f2 - f1f2) + 3 / 4)
            self.logger.log('Purification type 3 was used.')
            return result

        self.logger.log('Purification only accepts values (1, 2, or 3), formula 1 was chosen by default.')
        return f1f2 / ((f1f2) + ((1 - f1) * (1 - f2)))

    # ------------------------------------------------------------------ #
    #  ECHP (existing)                                                    #
    # ------------------------------------------------------------------ #

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

        fidelity_qubit1 = self._physical_layer.fidelity_measurement_only_one(qubit1)
        fidelity_qubit2 = self._physical_layer.fidelity_measurement_only_one(qubit2)

        prob_key = 'prob_on_demand_epr_create' if mode == 'on_demand' else 'prob_replay_epr_create'
        prob = self._context.graph.edges[alice_host_id, bob_host_id][prob_key]
        echp_success_probability = prob * fidelity_qubit1 * fidelity_qubit2

        if random.uniform(0, 1) < echp_success_probability:
            self.logger.log(f'Timeslot {self._context.clock.now}: EPR pair created with fidelity {fidelity_qubit1 * fidelity_qubit2}')
            epr = self._physical_layer.create_epr_pair(fidelity_qubit1 * fidelity_qubit2)
            self._physical_layer.add_epr_to_channel(epr, (alice_host_id, bob_host_id))
            self._context.clock.emit(f'echp_{mode}_success', alice=alice_host_id, bob=bob_host_id)
            self.logger.log(f'Timeslot {self._context.clock.now}: ECHP success probability is {echp_success_probability}')
            success = True
        else:
            self._context.clock.emit(f'echp_{mode}_failed', alice=alice_host_id, bob=bob_host_id)
            self.logger.log(f'Timeslot {self._context.clock.now}: ECHP success probability failed.')
            success = False

        if on_complete is not None:
            on_complete(success=success)
