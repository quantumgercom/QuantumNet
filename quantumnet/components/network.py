import networkx as nx
from ..objects import Logger, Qubit
from ..components import Host
from .layers import *
import random
import os
import csv

class Network():
    """
    Um objeto para utilizar como rede.
    """
    def __init__(self) -> None:
        # Sobre a rede
        self._graph = nx.Graph()
        self._hosts = {}
        # Camadas
        self._physical = PhysicalLayer(self)
        self._link = LinkLayer(self, self._physical)
        self._network = NetworkLayer(self, self._link, self._physical)
        self._transport = TransportLayer(self, self._network, self._link, self._physical)
        self._application = ApplicationLayer(self, self._transport, self._network, self._link, self._physical)
        # Sobre a execução
        self.logger = Logger.get_instance()
        #minimo e maximo
        self.max_prob = 1
        self.min_prob = 0.2
        self.timeslot_total = 0
        self.qubit_timeslots = {}  # Dicionário para armazenar qubits criados e seus timeslots

    @property
    def hosts(self):
        """
        Dicionário com os hosts da rede. No padrão {host_id: host}.

        Returns:
            dict : Dicionário com os hosts da rede.
        """
        return self._hosts
    
    @property
    def graph(self):
        """
        Grafo da rede.

        Returns:
            nx.Graph : Grafo da rede.
        """
        return self._graph
    
    @property
    def nodes(self):
        """
        Nós do grafo da rede.

        Returns:
            list : Lista de nós do grafo.
        """
        return self._graph.nodes()
    
    @property
    def edges(self):
        """
        Arestas do grafo da rede.

        Returns:
            list : Lista de arestas do grafo.
        """
        return self._graph.edges()
    
    # Camadas
    @property
    def physical(self):
        """
        Camada física da rede.

        Returns:
            PhysicalLayer : Camada física da rede.
        """
        return self._physical
    
    @property
    def linklayer(self):
        """
        Camada de enlace da rede.

        Returns:
            LinkLayer : Camada de enlace da rede.
        """
        return self._link
    
    @property 
    def networklayer(self):
        """
        Camada de rede da rede.

        Returns:
            NetworkLayer : Camada de rede da rede.
        """
        return self._network
    
    @property   
    def transportlayer(self):
        """
        Camada de transporte de transporte.

        Returns:
            TransportLayer : Camada de transporte de transporte.
        """
        return self._transport
    
    @property
    def application_layer(self):
        """
        Camada de transporte de aplicação.

        Returns:
            ApplicationLayer : Camada de aplicação.
        """
        return self._application

    def draw(self):
        """
        Desenha a rede.
        """
        nx.draw(self._graph, with_labels=True)
    
    def add_host(self, host: Host):
        """
        Adiciona um host à rede no dicionário de hosts, e o host_id ao grafo da rede.
            
        Args:
            host (Host): O host a ser adicionado.
        """
        # Adiciona o host ao dicionário de hosts, se não existir
        if host.host_id not in self._hosts:        
            self._hosts[host.host_id] = host
            Logger.get_instance().debug(f'Host {host.host_id} adicionado aos hosts da rede.')
        else:
            raise Exception(f'Host {host.host_id} já existe nos hosts da rede.')
            
        # Adiciona o nó ao grafo da rede, se não existir
        if not self._graph.has_node(host.host_id):
            self._graph.add_node(host.host_id)
            Logger.get_instance().debug(f'Nó {host.host_id} adicionado ao grafo da rede.')
            
        # Adiciona as conexões do nó ao grafo da rede, se não existirem
        for connection in host.connections:
            if not self._graph.has_edge(host.host_id, connection):
                self._graph.add_edge(host.host_id, connection)
                Logger.get_instance().debug(f'Conexões do {host.host_id} adicionados ao grafo da rede.')
    
    def get_host(self, host_id: int) -> Host:
        """
        Retorna um host da rede.

        Args:
            host_id (int): ID do host a ser retornado.

        Returns:
            Host : O host com o host_id fornecido.
        """
        return self._hosts[host_id]

    def get_eprs(self):
        """
        Cria uma lista de qubits entrelaçados (EPRs) associadas a cada aresta do grafo.

        Returns:
            Um dicionários que armazena as chaves que são as arestas do grafo e os valores são as
              listas de qubits entrelaçados (EPRs) associadas a cada aresta. 
        """
        eprs = {}
        for edge in self.edges:
            eprs[edge] = self._graph.edges[edge]['eprs']
        return eprs
    
    def get_eprs_from_edge(self, alice: int, bob: int) -> list:
        """
        Retorna os EPRs de uma aresta específica.

        Args:
            alice (int): ID do host Alice.
            bob (int): ID do host Bob.
        Returns:
            list : Lista de EPRs da aresta.
        """
        edge = (alice, bob)
        return self._graph.edges[edge]['eprs']
    
    def remove_epr(self, alice: int, bob: int) -> list:
        """
        Remove um EPR de um canal.

        Args:
            channel (tuple): Canal de comunicação.
        """
        channel = (alice, bob)
        try:
            epr = self._graph.edges[channel]['eprs'].pop(-1)   
            return epr
        except IndexError:
            raise Exception('Não há Pares EPRs.')   
        
    def set_ready_topology(self, topology_name: str, *args: int) -> str:
        """
        Cria um grafo com uma das topologias prontas para serem utilizadas. 
        São elas: Grade, Linha, Anel. Os nós são numerados de 0 a n-1, onde n é o número de nós.

        Args: 
            topology_name (str): Nome da topologia a ser utilizada.
            **args (int): Argumentos para a topologia. Geralmente, o número de hosts.
        
        """
        # Cria o grafo da topologia escolhida
        if topology_name == 'Grade':
            if len(args) != 2:
                raise Exception('Para a topologia Grade, são necessários dois argumentos.')
            self._graph = nx.grid_2d_graph(*args)
        elif topology_name == 'Linha':
            if len(args) != 1:
                raise Exception('Para a topologia Linha, é necessário um argumento.')
            self._graph = nx.path_graph(*args)
        elif topology_name == 'Anel':
            if len(args) != 1:
                raise Exception('Para a topologia Anel, é necessário um argumento.')
            self._graph = nx.cycle_graph(*args)

        # Converte os labels dos nós para inteiros
        self._graph = nx.convert_node_labels_to_integers(self._graph)

        # Cria os hosts e adiciona ao dicionário de hosts
        for node in self._graph.nodes():
            self._hosts[node] = Host(node)
        self.start_hosts()
        self.start_channels()
        self.start_eprs()
    
    def start_hosts(self, num_qubits: int = 10):
        """
        Inicializa os hosts da rede.
        
        Args:
            num_qubits (int): Número de qubits a serem inicializados.
        """
        for host_id in self._hosts:
            for i in range(num_qubits):
                self.physical.create_qubit(host_id, increment_timeslot=False,increment_qubits=False)
        print("Hosts inicializados")    

    def start_channels(self):
        """
        Inicializa os canais da rede.
        
        Args:
            prob_on_demand_epr_create (float): Probabilidade de criar um EPR sob demanda.
            prob_replay_epr_create (float): Probabilidade de criar um EPR de replay.
        """
        for edge in self.edges:
            self._graph.edges[edge]['prob_on_demand_epr_create'] = random.uniform(self.min_prob, self.max_prob)
            self._graph.edges[edge]['prob_replay_epr_create'] = random.uniform(self.min_prob, self.max_prob)
            self._graph.edges[edge]['eprs'] = list()
        print("Canais inicializados")
        
    def start_eprs(self, num_eprs: int = 10):
        """
        Inicializa os pares EPRs nas arestas da rede.

        Args:
            num_eprs (int): Número de pares EPR a serem inicializados para cada canal.
        """
        for edge in self.edges:
            for i in range(num_eprs):
                epr = self.physical.create_epr_pair(increment_timeslot=False,increment_eprs=False)
                self._graph.edges[edge]['eprs'].append(epr)
                self.logger.debug(f'Par EPR {epr} adicionado ao canal.')
        print("Pares EPRs adicionados")

        
    def timeslot(self):
        """
        Incrementa o timeslot da rede.
        """
        self.timeslot_total += 1
        self.apply_decoherence_to_all_layers()

    def get_timeslot(self):
        """
        Retorna o timeslot atual da rede.

        Returns:
            int : Timeslot atual da rede.
        """
        return self.timeslot_total

    def register_qubit_creation(self, qubit_id, timeslot, layer_name):
        """
        Registra a criação de um qubit associando-o ao timeslot em que foi criado.
    
        Args:
            qubit_id (int): ID do qubit criado.
            timeslot (int): Timeslot em que o qubit foi criado.
        """
        self.qubit_timeslots[qubit_id] = {'timeslot': timeslot, 'layer': layer_name}
        
    def display_all_qubit_timeslots(self):
        """
        Exibe o timeslot de todos os qubits criados nas diferentes camadas da rede.
        Se nenhum qubit foi criado, exibe uma mensagem apropriada.
        """
        if not self.qubit_timeslots:
            print("Nenhum qubit foi criado.")
        else:
            for qubit_id, info in self.qubit_timeslots.items():
                print(f"Qubit {qubit_id} foi criado no timeslot {info['timeslot']} na camada {info['layer']}")
                
                
    def get_total_useds_eprs(self):
        """
        Retorna o número total de EPRs (pares entrelaçados) utilizados na rede.

        Returns:
            int: Total de EPRs usados nas camadas física, de enlace e de rede.
        """
        total_eprs = (self._physical.get_used_eprs()+
                      self._link.get_used_eprs() +
                      self._network.get_used_eprs()
        )
        return total_eprs
    
    def get_total_useds_qubits(self):
        """
        Retorna o número total de qubits utilizados em toda a rede.

        Returns:
            int: Total de qubits usados nas camadas física, de enlace, transporte e aplicação.
        """

        total_qubits = (self._physical.get_used_qubits() +
                        self._link.get_used_qubits() +
                        self._transport.get_used_qubits() +
                        self._application.get_used_qubits()
                     
        )
        return total_qubits

    def get_metrics(self, metrics_requested=None, output_type="csv", file_name="metrics_output.csv"):
            """
            Obtém as métricas da rede conforme solicitado e as exporta, printa ou armazena.
            
            Args:
                metrics_requested: Lista de métricas a serem retornadas (opcional). 
                                Se None, todas as métricas serão consideradas.
                output_type: Especifica como as métricas devem ser retornadas.
                            "csv" para exportar em arquivo CSV (padrão),
                            "print" para exibir no console,
                            "variable" para retornar as métricas em uma variável.
                file_name: Nome do arquivo CSV (usado somente quando output_type="csv").
            
            Returns:
                Se output_type for "variable", retorna um dicionário com as métricas solicitadas.
            """
            # Dicionário com todas as métricas possíveis
            available_metrics = {
                "Timeslot Total": self.get_timeslot(),
                "EPRs Usados": self.get_total_useds_eprs(),
                "Qubits Usados": self.get_total_useds_qubits(),
                "Fidelidade na Camada de Transporte": self.transportlayer.avg_fidelity_on_transportlayer(),
                "Fidelidade na Camada de Enlace": self.linklayer.avg_fidelity_on_linklayer(),
                "Média de Rotas": self.networklayer.get_avg_size_routes()
            }
            
            # Se não foram solicitadas métricas específicas, use todas
            if metrics_requested is None:
                metrics_requested = available_metrics.keys()
            
            # Filtra as métricas solicitadas
            metrics = {metric: available_metrics[metric] for metric in metrics_requested if metric in available_metrics}

            # Tratamento conforme o tipo de saída solicitado
            if output_type == "print":
                for metric, value in metrics.items():
                    print(f"{metric}: {value}")
            elif output_type == "csv":
                current_directory = os.getcwd()
                file_path = os.path.join(current_directory, file_name)
                with open(file_path, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['Métrica', 'Valor'])
                    for metric, value in metrics.items():
                        writer.writerow([metric, value])
                print(f"Métricas exportadas com sucesso para {file_path}")
            elif output_type == "variable":
                return metrics
            else:
                raise ValueError("Tipo de saída inválido. Escolha entre 'print', 'csv' ou 'variable'.")

    def apply_decoherence_to_all_layers(self, decoherence_factor: float = 0.9):
        """
        Aplica decoerência a todos os qubits e EPRs nas camadas da rede que já avançaram nos timeslots.
        """
        current_timeslot = self.get_timeslot()

        # Aplicar decoerência nos qubits de cada host
        for host_id, host in self.hosts.items():
            for qubit in host.memory:
                creation_timeslot = self.qubit_timeslots[qubit.qubit_id]['timeslot']
                if creation_timeslot < current_timeslot:
                    current_fidelity = qubit.get_current_fidelity()
                    new_fidelity = current_fidelity * decoherence_factor
                    qubit.set_current_fidelity(new_fidelity)

        # Aplicar decoerência nos EPRs em todos os canais (arestas da rede)
        for edge in self.edges:
            if 'eprs' in self._graph.edges[edge]:
                for epr in self._graph.edges[edge]['eprs']:
                    current_fidelity = epr.get_current_fidelity()
                    new_fidelity = current_fidelity * decoherence_factor
                    epr.set_fidelity(new_fidelity)

