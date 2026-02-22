import networkx as nx
from ..components import Network, Host

class Controller():
    def __init__(self, network):
        self.network = network
        self.hosts = None

    def create_routing_table(self, host_id: int) -> dict:
        """
        Create a routing table for a node in a graph.
        Args:
            host_id (int): The node ID to create the routing table for.
        Returns:
            dict: A routing table for the node.
        """
        shortest_paths = nx.shortest_path(self.network.graph, source=host_id)  # Get shortest paths from the node to all other nodes
        routing_table = {}

        for destination, path in shortest_paths.items():
            if len(path) > 1:  # Ensure there's a valid path
                routing_table[destination] = path  # Store the next hop on the shortest path
            else:
                routing_table[destination] = [host_id]  # Self-routing

        return routing_table

    def register_routing_tables(self):
        """
        Register routing tables for all hosts in the network.
        """
        self.hosts = self.network.hosts

        for host_id in self.hosts:
            routing_table = self.create_routing_table(host_id)
            self.hosts[host_id].set_routing_table(routing_table)

    def check_route(self, route):
        """
        Check if a route is valid.
        Args:
            route (list): A list of nodes in the route.
        Returns:
            bool: True if the route is valid, False otherwise.
        """       
        return True

    def announce_to_route_nodes(self, route):
        """
        Announce a message to all nodes in a route.
        Args:
            route (list): A list of nodes in the route.
        """

        if len(route) == 1:
            print(f'Nó {route[0]} informado.')
        for node in route[1:]:
            print(f'Nó {node} informado.')

    def announce_to_alice_and_bob(self, route):
        """
        Announce a message to Alice and Bob.
        Args:
            route (list): A list of nodes in the route.
        """

        print(f"Alice {route[0]} e Bob {route[-1]} informados.")

