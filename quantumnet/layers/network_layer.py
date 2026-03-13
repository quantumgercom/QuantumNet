import networkx as nx
from ..topology import Host
from ..utils import Logger
from ..quantum import Epr
from random import uniform

class NetworkLayer:
    def __init__(self, context, physical_layer):
        """
        Initialize the network layer.

        Args:
            context (NetworkContext): Shared network context.
            physical_layer (PhysicalLayer): Physical layer.
        """
        self._context = context
        self._physical_layer = physical_layer
        self.logger = Logger.get_instance()

    def __str__(self):
        """ Return the string representation of the network layer.

        Returns:
            str: String representation of the network layer."""
        return 'Network Layer'

    def short_route_valid(self, alice: int, bob: int) -> list:
        """
        Choose the best route between two hosts with additional criteria.

        Args:
            alice (int): Source host ID.
            bob (int): Destination host ID.

        Returns:
            list or None: List with the best route between hosts or None if no valid route exists.
        """
        self._context.clock.emit('route_lookup', alice=alice, bob=bob)
        self.logger.log(f'Timeslot {self._context.clock.now}: Looking for valid route between {alice} and {bob}.')

        if alice is None or bob is None:
            self.logger.log('Invalid host IDs provided.')
            return None

        if not self._context.graph.has_node(alice) or not self._context.graph.has_node(bob):
            self.logger.log(f'One of the nodes ({alice} or {bob}) does not exist in the graph.')
            return None

        try:
            all_shortest_paths = list(nx.all_shortest_paths(self._context.graph, alice, bob))
        except nx.NetworkXNoPath:
            self.logger.log(f'No route found between {alice} and {bob}')
            return None

        for path in all_shortest_paths:
            valid_path = True
            for i in range(len(path) - 1):
                node = path[i]
                next_node = path[i + 1]
                if len(self._context.get_eprs_from_edge(node, next_node)) < 1:
                    self.logger.log(f'No EPR pairs between {node} and {next_node} in route {path}')
                    valid_path = False
                    break

            if valid_path:
                self.logger.log(f'Valid route found: {path}')
                self._context.clock.emit(
                    'route_found', alice=alice, bob=bob, route_len=len(path) - 1
                )
                return path

        self.logger.log('No valid route found.')
        return None

    def entanglement_swapping(self, alice: int = None, bob: int = None, on_complete=None):
        """
        Schedule entanglement swapping across the shortest valid route. Fire-and-forget.

        Result communicated via:
          - 'entanglement_swapping_complete' event on success
          - on_complete(success=True/False) callback if provided

        Args:
            alice (int, optional): Source host ID.
            bob (int, optional): Destination host ID.
            on_complete: Optional callback(success=bool).
        """
        route = self.short_route_valid(alice, bob)

        if route is None or len(route) < 2:
            self.logger.log('Could not determine a valid route.')
            if on_complete is not None:
                on_complete(success=False)
            return

        alice = route[0]
        bob = route[-1]
        self._swap_next(route, alice, bob, on_complete)

    def _swap_next(self, route, alice, bob, on_complete):
        """Schedule the next swap step, or finish if route is done."""
        if len(route) <= 1:
            self._context.clock.emit('entanglement_swapping_complete',
                                      alice=alice, bob=bob)
            self.logger.log(f'Entanglement Swapping completed successfully between {alice} and {bob}')
            if on_complete is not None:
                on_complete(success=True)
            return

        cost = self._context.config.costs.swapping
        self._context.clock.schedule(
            cost, self._do_one_swap,
            route=route, alice=alice, bob=bob, on_complete=on_complete
        )

    def _do_one_swap(self, route, alice, bob, on_complete):
        """Execute one entanglement swap at the scheduled timeslot."""
        self.logger.log(f'Timeslot {self._context.clock.now}: Performing Entanglement Swapping.')

        node1 = route[0]
        node2 = route[1]
        node3 = route[2] if len(route) > 2 else None

        if not self._context.graph.has_edge(node1, node2):
            self.logger.log(f'Channel between {node1}-{node2} does not exist')
            if on_complete is not None:
                on_complete(success=False)
            return

        try:
            epr1 = self._context.get_eprs_from_edge(node1, node2)[0]
        except IndexError:
            self.logger.log(f'Not enough EPR pairs between {node1}-{node2}')
            if on_complete is not None:
                on_complete(success=False)
            return

        if node3 is not None:
            if not self._context.graph.has_edge(node2, node3):
                self.logger.log(f'Channel between {node2}-{node3} does not exist')
                if on_complete is not None:
                    on_complete(success=False)
                return

            try:
                epr2 = self._context.get_eprs_from_edge(node2, node3)[0]
            except IndexError:
                self.logger.log(f'Not enough EPR pairs between {node2}-{node3}')
                if on_complete is not None:
                    on_complete(success=False)
                return

            fidelity1 = epr1.current_fidelity
            fidelity2 = epr2.current_fidelity

            success_prob = fidelity1 * fidelity2 + (1 - fidelity1) * (1 - fidelity2)

            if uniform(0, 1) > success_prob:
                self.logger.log(f'Entanglement Swapping failed between {node1}-{node2} and {node2}-{node3}')
                if on_complete is not None:
                    on_complete(success=False)
                return

            new_fidelity = (fidelity1 * fidelity2) / ((fidelity1 * fidelity2) + (1 - fidelity1) * (1 - fidelity2))
            epr_virtual = Epr(
                (node1, node3), new_fidelity,
                clock=self._context.clock,
                decoherence_rate=self._context.config.decoherence.per_timeslot
            )

            if not self._context.graph.has_edge(node1, node3):
                self._context.graph.add_edge(node1, node3, eprs=[])

            self._physical_layer.add_epr_to_channel(epr_virtual, (node1, node3))
            self._physical_layer.remove_epr_from_channel(epr1, (node1, node2))
            self._physical_layer.remove_epr_from_channel(epr2, (node2, node3))

            self.logger.log(f'{self.__class__.__name__}: 1 EPR used')

            route.pop(1)
        else:
            route.pop(1)

        # Continue to next swap
        self._swap_next(route, alice, bob, on_complete)
