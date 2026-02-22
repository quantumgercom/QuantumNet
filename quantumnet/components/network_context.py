class NetworkContext:
    """Recursos compartilhados entre as camadas da rede.

    Agrupa clock, graph, hosts e métodos utilitários que as camadas
    precisam, sem expor o objeto Network inteiro. Todos os atributos
    são referências aos mesmos objetos mutáveis mantidos pelo Network,
    portanto mudanças feitas pelas camadas são visíveis imediatamente.
    """

    def __init__(self, clock, graph, hosts, qubit_timeslots, config):
        self.clock = clock
        self.graph = graph
        self.hosts = hosts
        self.config = config
        self._qubit_timeslots = qubit_timeslots

    def get_host(self, host_id):
        """Retorna o host com o id fornecido."""
        return self.hosts[host_id]

    def get_eprs_from_edge(self, alice, bob):
        """Retorna a lista de EPRs de uma aresta específica."""
        return self.graph.edges[(alice, bob)]['eprs']

    def register_qubit_creation(self, qubit_id, layer_name):
        """Registra a criação de um qubit no timeslot atual."""
        self._qubit_timeslots[qubit_id] = {
            'timeslot': self.clock.now,
            'layer': layer_name,
        }
