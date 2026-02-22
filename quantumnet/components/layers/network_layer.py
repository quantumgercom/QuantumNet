import networkx as nx
from quantumnet.components import Host
from quantumnet.objects import Logger, Epr
from random import uniform

class NetworkLayer:
    def __init__(self, context, physical_layer):
        """
        Inicializa a camada de rede.

        Args:
            context (NetworkContext): Contexto compartilhado da rede.
            physical_layer (PhysicalLayer): Camada física.
        """
        self._context = context
        self._physical_layer = physical_layer
        self.logger = Logger.get_instance()
        self.avg_size_routes = 0  # Inicializa o tamanho médio das rotas
        self.used_eprs = 0  # Inicializa o contador de EPRs utilizados
        self.used_qubits = 0  # Inicializa o contador de Qubits utilizados
        self.routes_used = {}  # Inicializa o dicionário de rotas usadas 
    def __str__(self):
        """ Retorna a representação em string da camada de rede. 
        
        returns:
            str : Representação em string da camada de rede."""
        return 'Network Layer'

    def get_used_eprs(self):
        """Retorna a contagem de EPRs utilizados na camada de rede."""
        self.logger.debug(f"Eprs usados na camada {self.__class__.__name__}: {self.used_eprs}")
        return self.used_eprs
    
    def get_used_qubits(self):
        self.logger.debug(f"Qubits usados na camada {self.__class__.__name__}: {self.used_qubits}")
        return self.used_qubits

    def short_route_valid(self, Alice: int, Bob: int) -> list:
        """
        Escolhe a melhor rota entre dois hosts com critérios adicionais.

        args:
            Alice (int): ID do host de origem.
            Bob (int): ID do host de destino.

        returns:
            list or None: Lista com a melhor rota entre os hosts ou None se não houver rota válida.
        """
        self._context.clock.emit('route_lookup', alice=Alice, bob=Bob)
        self.logger.log(f'Timeslot {self._context.clock.now}: Buscando rota válida entre {Alice} e {Bob}.')

        if Alice is None or Bob is None:
            self.logger.log('IDs de hosts inválidos fornecidos.')
            return None

        if not self._context.graph.has_node(Alice) or not self._context.graph.has_node(Bob):
            self.logger.log(f'Um dos nós ({Alice} ou {Bob}) não existe no grafo.')
            return None

        try:
            all_shortest_paths = list(nx.all_shortest_paths(self._context.graph, Alice, Bob))
        except nx.NetworkXNoPath:
            self.logger.log(f'Sem rota encontrada entre {Alice} e {Bob}')
            return None

        for path in all_shortest_paths:
            valid_path = True
            for i in range(len(path) - 1):
                node = path[i]
                next_node = path[i + 1]
                if len(self._context.get_eprs_from_edge(node, next_node)) < 1:
                    self.logger.log(f'Sem pares EPRs entre {node} e {next_node} na rota {path}')
                    valid_path = False
                    break

            if valid_path:
                self.logger.log(f'Rota válida encontrada: {path}')

                # Armazena a rota se for a primeira vez que é usada
                if (Alice, Bob) not in self.routes_used:
                    self.routes_used[(Alice, Bob)] = path.copy()

                return path

        self.logger.log('Nenhuma rota válida encontrada.')
        return None



    def entanglement_swapping(self, Alice: int = None, Bob: int = None) -> bool:
        """
        Realiza o Entanglement Swapping em toda a rota determinada pelo short_route_valid.
        
        args:
            Alice (int, optional): ID do host de origem. Se não fornecido, usa o primeiro nó da rota válida.
            Bob (int, optional): ID do host de destino. Se não fornecido, usa o último nó da rota válida.
                
        returns:
            bool: True se todos os Entanglement Swappings foram bem-sucedidos, False caso contrário.
        """
        # Obtém a rota válida entre Alice e Bob usando a função short_route_valid
        route = self.short_route_valid(Alice, Bob)
        
        # Verifica se uma rota válida foi encontrada e se ela tem pelo menos 2 nós
        if route is None or len(route) < 2:
            self.logger.log('Não foi possível determinar uma rota válida.')
            return False

        # Define Alice e Bob como o primeiro e o último nó da rota, respectivamente
        Alice = route[0]
        Bob = route[-1]

        # Itera sobre a rota realizando o entanglement swapping para cada segmento da rota
        while len(route) > 1:
            # Incrementa o timeslot antes de cada operação de entanglement swapping
            self._context.clock.tick()
            self.logger.log(f'Timeslot {self._context.clock.now}: Realizando Entanglement Swapping.')

            node1 = route[0]    # Primeiro nó na rota
            node2 = route[1]    # Segundo nó na rota
            node3 = route[2] if len(route) > 2 else None  # Terceiro nó na rota (se existir)

            # Verifica se existe um canal entre node1 e node2
            if not self._context.graph.has_edge(node1, node2):
                self.logger.log(f'Canal entre {node1}-{node2} não existe')
                return False

            try:
                # Obtém o primeiro par EPR entre node1 e node2
                epr1 = self._context.get_eprs_from_edge(node1, node2)[0]
            except IndexError:
                # Se não houver pares EPR suficientes, loga a falha e retorna False
                self.logger.log(f'Não há pares EPRs suficientes entre {node1}-{node2}')
                return False

            # Se houver um terceiro nó, realiza o swapping entre node1, node2 e node3
            if node3 is not None:
                # Verifica se existe um canal entre node2 e node3
                if not self._context.graph.has_edge(node2, node3):
                    self.logger.log(f'Canal entre {node2}-{node3} não existe')
                    return False

                try:
                    # Obtém o primeiro par EPR entre node2 e node3
                    epr2 = self._context.get_eprs_from_edge(node2, node3)[0]
                except IndexError:
                    # Se não houver pares EPR suficientes, loga a falha e retorna False
                    self.logger.log(f'Não há pares EPRs suficientes entre {node2}-{node3}')
                    return False

                # Mede a fidelidade dos pares EPR
                fidelity1 = epr1.get_current_fidelity()
                fidelity2 = epr2.get_current_fidelity()
                
                # Calcula a probabilidade de sucesso do entanglement swapping
                success_prob = fidelity1 * fidelity2 + (1 - fidelity1) * (1 - fidelity2)
                
                # Verifica se o swapping foi bem-sucedido com base na probabilidade de sucesso
                if uniform(0, 1) > success_prob:
                    self.logger.log(f'Entanglement Swapping falhou entre {node1}-{node2} e {node2}-{node3}')
                    return False

                # Calcula a nova fidelidade do par EPR virtual
                new_fidelity = (fidelity1 * fidelity2) / ((fidelity1 * fidelity2) + (1 - fidelity1) * (1 - fidelity2))
                epr_virtual = Epr((node1, node3), new_fidelity)

                # Se o canal entre node1 e node3 não existir, adiciona um novo canal
                if not self._context.graph.has_edge(node1, node3):
                    self._context.graph.add_edge(node1, node3, eprs=[])

                # Adiciona o par EPR virtual ao canal entre node1 e node3
                self._physical_layer.add_epr_to_channel(epr_virtual, (node1, node3))
                # Remove os pares EPR antigos dos canais entre node1-node2 e node2-node3
                self._physical_layer.remove_epr_from_channel(epr1, (node1, node2))
                self._physical_layer.remove_epr_from_channel(epr2, (node2, node3))

                # Atualiza o contador de EPRs utilizados
                self.used_eprs += 1

                # Remove o segundo nó da rota, pois o swapping foi realizado
                route.pop(1)
            else:
                # Se não há um terceiro nó, apenas remove o segundo nó da rota
                route.pop(1)

        # Loga o sucesso do entanglement swapping
        self._context.clock.emit('entanglement_swapping_complete', alice=Alice, bob=Bob)
        self.logger.log(f'Entanglement Swapping concluído com sucesso entre {Alice} e {Bob}')
        return True

    def get_avg_size_routes(self):
        """
        Calcula o tamanho médio das rotas utilizadas, considerando o número de saltos (arestas) entre os nós.
        
        returns:
            float: Tamanho médio das rotas utilizadas.
        """
        total_size = 0
        num_routes = 0
        
        # Itera sobre as rotas armazenadas no dicionário
        for route in self.routes_used.values():
            total_size += len(route) - 1  # Soma o número de arestas (saltos), que é o número de nós menos 1
            num_routes += 1  # Conta o número de rotas
        
        # Calcula a média, se houver rotas válidas
        if num_routes > 0:
            self.avg_size_routes = total_size / num_routes
        else:
            # Retorna 0 se não houver rotas válidas
            self.avg_size_routes = 0.0
        
        return self.avg_size_routes
