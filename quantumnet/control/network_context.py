class NetworkContext:
    """Shared resources between network layers.

    Groups clock, graph, hosts and utility methods that layers need
    without exposing the entire Network object. All attributes are
    references to the same mutable objects maintained by Network,
    so changes made by layers are immediately visible.
    """

    def __init__(self, clock, graph, hosts, config):
        self.clock = clock
        self.graph = graph
        self.hosts = hosts
        self.config = config
        self._next_qubit_id = 0

    def get_host(self, host_id):
        """Return the host with the given id."""
        return self.hosts[host_id]

    def generate_qubit_id(self):
        """Generate a unique qubit ID across all layers."""
        qubit_id = self._next_qubit_id
        self._next_qubit_id += 1
        return qubit_id

    def get_eprs_from_edge(self, alice, bob):
        """Return the list of EPRs for a specific edge."""
        return self.graph.edges[(alice, bob)]['eprs']
