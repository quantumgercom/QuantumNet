
from ..utils import Logger
from ..quantum import Qubit

class Host():
    def __init__(self, host_id: int) -> None:
        # Network information
        self._host_id = host_id
        self._connections = []
        # Host information
        self._memory = []
        self._routing_table = {}
        self._routing_table[host_id] = [host_id]
        # Execution information
        self.logger = Logger.get_instance()
    def __str__(self):
        return f'{self.host_id}'

    @property
    def host_id(self):
        """
        Host ID. Always an integer.

        Returns:
            int: Host name.
        """
        return self._host_id

    @property
    def connections(self):
        """
        Host connections.

        Returns:
            list: List of connections.
        """
        return self._connections

    @property
    def memory(self):
        """
        Host memory.

        Returns:
            list: List of qubits.
        """
        return self._memory

    @property
    def routing_table(self):
        """
        Host routing table.
        Returns:
            dict: Routing table.
        """
        return self._routing_table


    def consume_last_qubit(self):
        """
        Remove and return the last qubit from memory.

        Returns:
            Qubit: Last qubit from memory, or None if memory is empty.
        """
        if not self.memory:
            return None
        return self.memory.pop()

    def add_connection(self, host_id_for_connection: int):
        """
        Add a connection to the host. A connection is a host_id, an integer.

        Args:
            host_id_for_connection (int): Host ID of the host to be connected.
        """

        if not isinstance(host_id_for_connection, int):
            raise TypeError('Value provided for host_id_for_connection must be an integer.')

        if host_id_for_connection not in self.connections:
            self.connections.append(host_id_for_connection)

    def add_qubit(self, qubit: Qubit):
        """
        Add a qubit to the host memory.

        Args:
            qubit (Qubit): The qubit to be added.
        """

        self.memory.append(qubit)
        Logger.get_instance().debug(f'Qubit {qubit.qubit_id} added to memory of Host {self.host_id}.')



    def set_routing_table(self, routing_table: dict):
        """
        Set the host routing table.
        Args:
            routing_table (dict): Routing table.
        """

        self._routing_table = routing_table

    def info(self):
        """
        Return information about the host.
        Returns:
            dict: Host information.
        """

        return {
            'host_id': self.host_id,
            'memory': len(self.memory),
            'routing_table': "No registration" if self.routing_table is None else self.routing_table
        }

    def announce_to_controller_app_has_finished(self):
        """
        Inform the controller that the application has finished.
        """

        Logger.get_instance().log(f'Host {self.host_id} informed controller that application has finished.')
