import networkx as nx
from ..utils import Logger
from ..quantum import Qubit
from ..runtime import Clock
from ..config import SimulationConfig
from .host import Host
from ..control.network_context import NetworkContext
from ..layers import *
from ..exceptions import DuplicateHostError, TopologyError
import random

class Network():
    """
    An object to use as a network.
    """
    def __init__(self, clock: 'Clock' = None, config: 'SimulationConfig' = None) -> None:
        # Simulation configuration
        self.config = config if config is not None else SimulationConfig()
        # Simulation clock
        self.clock = clock if clock is not None else Clock()
        # Network
        self._graph = nx.Graph()
        self._hosts = {}
        # Execution
        self.logger = Logger.get_instance()
        # Shared context between layers (without Network reference)
        self._context = NetworkContext(self.clock, self._graph, self._hosts, self.config)
        # Layers
        self._physical = PhysicalLayer(self._context)
        self._link = LinkLayer(self._context, self._physical)
        self._network = NetworkLayer(self._context, self._physical, self._link)
        self._transport = TransportLayer(self._context, self._network, self._physical)
        self._application = ApplicationLayer(self._context, self._transport)

    @property
    def hosts(self):
        """
        Dictionary of network hosts. Format: {host_id: host}.

        Returns:
            dict: Dictionary of network hosts.
        """
        return self._hosts

    @property
    def graph(self):
        """
        Network graph.

        Returns:
            nx.Graph: Network graph.
        """
        return self._graph

    @property
    def nodes(self):
        """
        Network graph nodes.

        Returns:
            list: List of graph nodes.
        """
        return self._graph.nodes()

    @property
    def edges(self):
        """
        Network graph edges.

        Returns:
            list: List of graph edges.
        """
        return self._graph.edges()

    # Layers
    @property
    def physical(self):
        """
        Network physical layer.

        Returns:
            PhysicalLayer: Network physical layer.
        """
        return self._physical

    @property
    def linklayer(self):
        """
        Network link layer.

        Returns:
            LinkLayer: Network link layer.
        """
        return self._link

    @property
    def networklayer(self):
        """
        Network layer.

        Returns:
            NetworkLayer: Network layer.
        """
        return self._network

    @property
    def transportlayer(self):
        """
        Transport layer.

        Returns:
            TransportLayer: Transport layer.
        """
        return self._transport

    @property
    def application_layer(self):
        """
        Application layer.

        Returns:
            ApplicationLayer: Application layer.
        """
        return self._application

    def draw(self):
        """
        Draw the network.
        """
        nx.draw(self._graph, with_labels=True)

    def add_host(self, host: Host):
        """
        Add a host to the network hosts dictionary and the host_id to the network graph.

        Args:
            host (Host): The host to be added.
        """
        # Add host to hosts dictionary if it doesn't exist
        if host.host_id not in self._hosts:
            self._hosts[host.host_id] = host
            Logger.get_instance().debug(f'Host {host.host_id} added to network hosts.')
        else:
            raise DuplicateHostError(f'Host {host.host_id} already exists in network hosts.')

        # Add node to network graph if it doesn't exist
        if not self._graph.has_node(host.host_id):
            self._graph.add_node(host.host_id)
            Logger.get_instance().debug(f'Node {host.host_id} added to network graph.')

        # Add node connections to network graph if they don't exist
        for connection in host.connections:
            if not self._graph.has_edge(host.host_id, connection):
                self._graph.add_edge(host.host_id, connection)
                Logger.get_instance().debug(f'Connections of {host.host_id} added to network graph.')

    def get_host(self, host_id: int) -> Host:
        """
        Return a host from the network.

        Args:
            host_id (int): ID of the host to be returned.

        Returns:
            Host: The host with the given host_id.
        """
        return self._context.get_host(host_id)

    def get_eprs(self):
        """
        Create a list of entangled qubits (EPRs) associated with each graph edge.

        Returns:
            dict: Dictionary where keys are graph edges and values are
              lists of entangled qubits (EPRs) associated with each edge.
        """
        eprs = {}
        for edge in self.edges:
            eprs[edge] = self._graph.edges[edge]['eprs']
        return eprs

    def get_eprs_from_edge(self, alice: int, bob: int) -> list:
        """
        Return the EPRs from a specific edge.

        Args:
            alice (int): Alice host ID.
            bob (int): Bob host ID.
        Returns:
            list: List of EPRs from the edge.
        """
        return self._context.get_eprs_from_edge(alice, bob)

    def remove_epr(self, alice: int, bob: int) -> list:
        """
        Remove an EPR from a channel.

        Args:
            channel (tuple): Communication channel.

        Returns:
            Epr: The removed EPR pair, or None if no EPR pairs are available.
        """
        channel = (alice, bob)
        try:
            epr = self._graph.edges[channel]['eprs'].pop(-1)
            return epr
        except (IndexError, KeyError):
            return None

    def set_ready_topology(self, topology_name: str, *args: int) -> str:
        """
        Create a graph with one of the ready-to-use topologies.
        Available: Grid, Line, Ring. Nodes are numbered from 0 to n-1, where n is the number of nodes.

        Args:
            topology_name (str): Name of the topology to use.
            **args (int): Arguments for the topology. Usually the number of hosts.

        """
        # Create the graph for the chosen topology
        if topology_name == 'Grid':
            if len(args) != 2:
                raise TopologyError('Grid topology requires two arguments.')
            new_graph = nx.grid_2d_graph(*args)
        elif topology_name == 'Line':
            if len(args) != 1:
                raise TopologyError('Line topology requires one argument.')
            new_graph = nx.path_graph(*args)
        elif topology_name == 'Ring':
            if len(args) != 1:
                raise TopologyError('Ring topology requires one argument.')
            new_graph = nx.cycle_graph(*args)
        else:
            raise ValueError(f"Unknown topology '{topology_name}'. Available: Grid, Line, Ring.")

        # Update graph in-place to preserve existing references (context, layers)
        new_graph = nx.convert_node_labels_to_integers(new_graph)
        self._graph.clear()
        self._graph.update(new_graph)

        # Create hosts and add to hosts dictionary
        for node in self._graph.nodes():
            self._hosts[node] = Host(node)
        self.start_hosts()
        self.start_channels()
        self.start_eprs()

    def start_hosts(self, num_qubits: int = None):
        """
        Initialize network hosts.

        Args:
            num_qubits (int): Number of qubits to initialize. If None, uses config.
        """
        if num_qubits is None:
            num_qubits = self.config.defaults.qubits_per_host
        for host_id in self._hosts:
            for i in range(num_qubits):
                self.physical.create_qubit(host_id, increment_qubits=False)
        self.physical.start_qubit_regen()
        self.logger.debug("Hosts initialized")

    def start_channels(self):
        """
        Initialize network channels.
        """
        prob_cfg = self.config.probability
        cfg_noise = self.config.defaults.channel_noise_type
        _noise_types = ['bit-flip', 'werner', 'bitflip+werner']
        for edge in self.edges:
            self._graph.edges[edge]['prob_on_demand_epr_create'] = random.uniform(prob_cfg.epr_create_min, prob_cfg.epr_create_max)
            self._graph.edges[edge]['prob_replay_epr_create'] = random.uniform(prob_cfg.epr_create_min, prob_cfg.epr_create_max)
            self._graph.edges[edge]['eprs'] = list()
            self._graph.edges[edge]['noise_type'] = (
                random.choice(_noise_types) if cfg_noise == 'random' else cfg_noise
            )
        self.logger.debug("Channels initialized")

    def start_eprs(self, num_eprs: int = None):
        """
        Initialize EPR pairs on network edges.

        Args:
            num_eprs (int): Number of EPR pairs to initialize per channel. If None, uses config.
        """
        if num_eprs is None:
            num_eprs = self.config.defaults.eprs_per_channel
        for edge in self.edges:
            for i in range(num_eprs):
                epr = self.physical.create_epr_pair(increment_eprs=False)
                self.physical.add_epr_to_channel(epr, edge)
        self.logger.debug("EPR pairs added")


    def get_timeslot(self):
        """
        Return the current network timeslot.
        Compatibility wrapper; prefer using self.clock.now directly.

        Returns:
            int: Current network timeslot.
        """
        return self.clock.now
