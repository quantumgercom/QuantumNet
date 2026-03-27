from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import networkx as nx

from ..config import SimulationConfig
from ..control.network_context import NetworkContext
from ..exceptions import DuplicateHostError, TopologyError
from ..layers import *
from ..runtime import Clock
from ..utils import Logger
from .host import Host
from .topologies import BaseTopology, create_topology

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
        self._host_name_to_id: dict[str, int] = {}
        self._host_id_to_name: dict[int, str] = {}
        self._next_host_id = 0
        self._topology: BaseTopology | None = None
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
    def host_name_to_id(self) -> dict[str, int]:
        """Name -> ID mapping for current hosts."""
        return dict(self._host_name_to_id)

    @property
    def host_id_to_name(self) -> dict[int, str]:
        """ID -> name mapping for current hosts."""
        return dict(self._host_id_to_name)

    @property
    def topology(self) -> BaseTopology | None:
        """Currently applied topology object."""
        return self._topology

    @topology.setter
    def topology(self, value: BaseTopology | None) -> None:
        if value is None or value is False:
            self._topology = None
            return
        if not isinstance(value, BaseTopology):
            raise TopologyError(
                "network.topology must be a BaseTopology instance or None."
            )
        self.apply_topology(value)

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
        labels = {
            node: str(self._graph.nodes[node].get("label", self._host_id_to_name.get(int(node), node)))
            for node in self._graph.nodes()
        }
        nx.draw(self._graph, labels=labels, with_labels=True)

    def _register_host_identity(self, host: Host) -> None:
        existing_id = self._host_name_to_id.get(host.name)
        if existing_id is not None and existing_id != host.host_id:
            raise TopologyError(f"Duplicate host name: {host.name!r}")
        self._host_name_to_id[host.name] = host.host_id
        self._host_id_to_name[host.host_id] = host.name
        self._next_host_id = max(self._next_host_id, host.host_id + 1)

    def _clear_host_indexes(self) -> None:
        self._host_name_to_id.clear()
        self._host_id_to_name.clear()
        self._next_host_id = 0

    def generate_host_id(self) -> int:
        """Generate the next available integer host ID."""
        host_id = self._next_host_id
        while host_id in self._hosts:
            host_id += 1
        self._next_host_id = host_id + 1
        return host_id

    def create_host(self, name: str) -> Host:
        """Create a Host with an auto-generated integer ID."""
        return Host(self.generate_host_id(), name=name)

    def resolve_host_id(self, host_ref: int | str) -> int:
        """Resolve host references by integer ID, host name, or explicit ``id:<int>``."""
        if isinstance(host_ref, int):
            if host_ref not in self._hosts:
                raise TopologyError(f"Host ID {host_ref} does not exist in network.")
            return host_ref

        if isinstance(host_ref, str):
            normalized = host_ref.strip()
            if not normalized:
                raise TopologyError("Host name cannot be empty.")

            if normalized in self._host_name_to_id:
                return self._host_name_to_id[normalized]

            if normalized.lower().startswith("id:"):
                raw_id = normalized[3:].strip()
                if not raw_id or not raw_id.lstrip("-").isdigit():
                    raise TopologyError(
                        f"Invalid host ID reference '{host_ref}'. Use 'id:<integer>'."
                    )
                host_id = int(raw_id)
                if host_id in self._hosts:
                    return host_id
                raise TopologyError(f"Host ID {host_id} does not exist in network.")

            raise TopologyError(f"Host name '{host_ref}' does not exist in network.")

        raise TopologyError("Host reference must be an integer ID or host name string.")

    def get_host_name(self, host_ref: int | str) -> str:
        """Return the host name associated with the reference."""
        host_id = self.resolve_host_id(host_ref)
        return self._host_id_to_name[host_id]

    def get_host_id(self, host_name: str) -> int:
        """Return integer host ID for a given host name."""
        return self.resolve_host_id(host_name)

    def add_host(self, host: Host):
        """
        Add a host to the network hosts dictionary and the host_id to the network graph.

        Args:
            host (Host): The host to be added.
        """
        # Add host to hosts dictionary if it doesn't exist
        if host.host_id not in self._hosts:
            self._register_host_identity(host)
            self._hosts[host.host_id] = host
            Logger.get_instance().debug(f'Host {host.host_id} added to network hosts.')
        else:
            raise DuplicateHostError(f'Host {host.host_id} already exists in network hosts.')

        # Add node to network graph if it doesn't exist
        if not self._graph.has_node(host.host_id):
            self._graph.add_node(host.host_id, label=host.name)
            Logger.get_instance().debug(f'Node {host.host_id} added to network graph.')
        else:
            self._graph.nodes[host.host_id]['label'] = host.name

        # Add node connections to network graph if they don't exist
        for connection in host.connections:
            if not self._graph.has_edge(host.host_id, connection):
                self._graph.add_edge(host.host_id, connection)
                Logger.get_instance().debug(f'Connections of {host.host_id} added to network graph.')

    def get_host(self, host_ref: int | str) -> Host:
        """
        Return a host from the network.

        Args:
            host_ref (int | str): Host ID or host name.

        Returns:
            Host: The host with the given host_id.
        """
        host_id = self.resolve_host_id(host_ref)
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

    def get_eprs_from_edge(self, alice: int | str, bob: int | str) -> list:
        """
        Return the EPRs from a specific edge.

        Args:
            alice (int | str): Alice host ID or name.
            bob (int | str): Bob host ID or name.
        Returns:
            list: List of EPRs from the edge.
        """
        alice_id = self.resolve_host_id(alice)
        bob_id = self.resolve_host_id(bob)
        return self._context.get_eprs_from_edge(alice_id, bob_id)

    def remove_epr(self, alice: int | str, bob: int | str) -> list:
        """
        Remove an EPR from a channel.

        Args:
            channel (tuple): Communication channel.

        Returns:
            Epr: The removed EPR pair, or None if no EPR pairs are available.
        """
        alice_id = self.resolve_host_id(alice)
        bob_id = self.resolve_host_id(bob)
        channel = (alice_id, bob_id)
        try:
            epr = self._graph.edges[channel]['eprs'].pop(-1)
            return epr
        except (IndexError, KeyError):
            return None

    def _config_base_dir(self) -> Path | None:
        source_path = getattr(self.config, "_source_path", None)
        if source_path is None:
            return None
        try:
            return Path(source_path).resolve().parent
        except (TypeError, ValueError):
            return None

    def _topology_from_config(self) -> tuple[str, tuple[Any, ...]]:
        cfg = getattr(self.config, 'topology', None)
        if cfg is None or not getattr(cfg, 'name', None):
            raise TopologyError(
                "Topology name not provided. "
                "Configure topology.name and topology.args in SimulationConfig/YAML, "
                "then call set_ready_topology(). "
                "Set topology.name to false/null to disable config-driven topology."
            )
        return cfg.name, tuple(cfg.args)

    def _replace_graph(self, graph: nx.Graph) -> None:
        """Replace the current graph while preserving references used by layers."""
        if not isinstance(graph, nx.Graph):
            raise TopologyError("Topology must build a networkx.Graph instance.")
        if graph.number_of_nodes() == 0:
            raise TopologyError("Topology graph must contain at least one host.")

        normalized_graph = nx.convert_node_labels_to_integers(
            graph,
            first_label=0,
            ordering="default",
            label_attribute="_original_node",
        )
        self._graph.clear()
        self._graph.update(normalized_graph)

    def _rebuild_hosts_from_graph(self) -> None:
        """Recreate host objects from current graph nodes and edges."""
        self._hosts.clear()
        self._clear_host_indexes()
        for node in self._graph.nodes():
            host_id = int(node)
            raw_name = self._graph.nodes[node].get("label")
            if raw_name is None:
                raw_name = self._graph.nodes[node].get("_original_node", host_id)
            host_name = str(raw_name)
            host = Host(host_id, name=host_name)
            for neighbor in self._graph.neighbors(node):
                host.add_connection(int(neighbor))
            self._hosts[host_id] = host
            self._graph.nodes[node]["label"] = host.name
            self._register_host_identity(host)

    def apply_topology(
        self,
        topology: BaseTopology,
        num_qubits: int | None = None,
        num_eprs: int | None = None,
    ) -> None:
        """Apply a topology object to the network and initialize resources."""
        self._replace_graph(topology.build_graph())
        self._rebuild_hosts_from_graph()
        self._topology = topology
        self.initialize_resources(num_qubits=num_qubits, num_eprs=num_eprs)

    def set_topology(
        self,
        topology: BaseTopology,
        num_qubits: int | None = None,
        num_eprs: int | None = None,
    ) -> None:
        """Alias for apply_topology()."""
        self.apply_topology(topology, num_qubits=num_qubits, num_eprs=num_eprs)

    def set_ready_topology(self, topology_name: str | None = None, *args: Any) -> None:
        """
        Create and apply a topology using only config.topology.

        Args:
            topology_name: Deprecated. Must be None.
            *args: Deprecated. Must be empty.
        """
        if topology_name is not None or args:
            raise TopologyError(
                "set_ready_topology no longer accepts topology arguments in code. "
                "Configure topology.name/topology.args in SimulationConfig (or YAML) "
                "and call set_ready_topology() with no parameters."
            )

        topology_name, args = self._topology_from_config()
        topology = create_topology(
            topology_name,
            *args,
            base_dir=self._config_base_dir(),
        )
        self.apply_topology(topology)

    def initialize_resources(self, num_qubits: int = None, num_eprs: int = None) -> None:
        """
        Initialize hosts, channels and EPRs for the current topology.

        Args:
            num_qubits (int): Number of qubits to initialize per host. If None, uses config.
            num_eprs (int): Number of EPR pairs to initialize per channel. If None, uses config.
        """
        self.initialize_hosts(num_qubits=num_qubits)
        self.initialize_channels()
        self.initialize_eprs(num_eprs=num_eprs)

    def initialize_hosts(self, num_qubits: int = None):
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

    def initialize_channels(self):
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

    def initialize_eprs(self, num_eprs: int = None):
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

    def start_hosts(self, num_qubits: int = None):
        """Compatibility wrapper for initialize_hosts()."""
        self.initialize_hosts(num_qubits=num_qubits)

    def start_channels(self):
        """Compatibility wrapper for initialize_channels()."""
        self.initialize_channels()

    def start_eprs(self, num_eprs: int = None):
        """Compatibility wrapper for initialize_eprs()."""
        self.initialize_eprs(num_eprs=num_eprs)


    def get_timeslot(self):
        """
        Return the current network timeslot.
        Compatibility wrapper; prefer using self.clock.now directly.

        Returns:
            int: Current network timeslot.
        """
        return self.clock.now
