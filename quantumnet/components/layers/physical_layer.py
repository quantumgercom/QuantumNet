from ...objects import Logger, Qubit, Epr
from ...components import Host
from random import uniform
import random

class PhysicalLayer:
    def __init__(self, network, physical_layer_id: int = 0):
        """
        Inicializa a camada física.
        
        Args:
            physical_layer_id (int): Id da camada física.
        """
        self.max_prob = 1
        self.min_prob = 0.2
        self._physical_layer_id = physical_layer_id
        self._network = network
        self._failed_eprs = []
        self.created_eprs = []  # Lista para armazenar todos os EPRs criados
        self._count_qubit = 0
        self._count_epr = 0
        self.logger = Logger.get_instance()
        self.used_eprs = 0
        self.used_qubits = 0
        
        
    def __str__(self):
        """ Retorna a representação em string da camada física. 
        
        Returns:
            str: Representação em string da camada física.
        """
        return f'Physical Layer {self.physical_layer_id}'
      
    @property
    def physical_layer_id(self):
        """Retorna o id da camada física.
        
        Returns:
            int: Id da camada física.
        """
        return self._physical_layer_id

    @property
    def failed_eprs(self):
        """Retorna os pares EPR que falharam.
        
        Returns:
            dict: Dicionário de pares EPR que falharam.
        """
        return self._failed_eprs
    
    def get_used_eprs(self):
        self.logger.debug(f"Eprs usados na camada {self.__class__.__name__}: {self.used_eprs}")
        return self.used_eprs
    
    def get_used_qubits(self):
        self.logger.debug(f"Qubits usados na camada {self.__class__.__name__}: {self.used_qubits}")
        return self.used_qubits
    
    def create_qubit(self, host_id: int, increment_timeslot: bool = True, increment_qubits : bool = True):
        """Cria um qubit e adiciona à memória do host especificado.

        Args:
            host_id (int): ID do host onde o qubit será criado.

        Raises:
            Exception: Se o host especificado não existir na rede.
        """
        if increment_timeslot:
            self._network.timeslot()

        if increment_qubits:
            self.used_qubits += 1

        if host_id not in self._network.hosts:
            raise Exception(f'Host {host_id} não existe na rede.')

        qubit_id = self._count_qubit
        qubit = Qubit(qubit_id)
        self._network.hosts[host_id].add_qubit(qubit)
        
        current_timeslot = self._network.get_timeslot()
        self._network.register_qubit_creation(qubit_id, current_timeslot, "Physical Layer")
    
        self._count_qubit += 1
        self.logger.debug(f'Qubit {qubit_id} criado com fidelidade inicial {qubit.get_initial_fidelity()} e adicionado à memória do Host {host_id}.')

    def create_epr_pair(self, fidelity: float = 1.0, increment_timeslot: bool = True, increment_eprs: bool = True):
        """Cria um par de qubits entrelaçados.

        Returns:
            Qubit, Qubit: Par de qubits entrelaçados.
        """
        if increment_timeslot:
            self._network.timeslot() 

        if increment_eprs:
            self.used_eprs += 1
            
            
        epr = Epr(self._count_epr, fidelity)
        self._count_epr += 1
        return epr

    def add_epr_to_channel(self, epr: Epr, channel: tuple):
        """Adiciona um par EPR ao canal.

        Args:
            epr (Epr): Par EPR.
            channel (tuple): Canal.
        """
        u, v = channel
        if not self._network.graph.has_edge(u, v):
            self._network.graph.add_edge(u, v, eprs=[])
        self._network.graph.edges[u, v]['eprs'].append(epr)
        self.logger.debug(f'Par EPR {epr} adicionado ao canal {channel}.')

    def remove_epr_from_channel(self, epr: Epr, channel: tuple):
        """Remove um par EPR do canal.

        Args:
            epr (Epr): Par EPR a ser removido.
            channel (tuple): Canal.
        """
        u, v = channel
        if not self._network.graph.has_edge(u, v):
            self.logger.debug(f'Canal {channel} não existe.')
            return
        try:
            self._network.graph.edges[u, v]['eprs'].remove(epr)
            self.logger.debug(f'Par EPR {epr} removido do canal {channel}.')
        except ValueError:
            self.logger.debug(f'Par EPR {epr} não encontrado no canal {channel}.')

    def fidelity_measurement_only_one(self, qubit: Qubit):
        """Mede a fidelidade de um qubit.

        Args:
            qubit (Qubit): Qubit.

        Returns:
            float: Fidelidade do qubit.
        """
        fidelity = qubit.get_current_fidelity()  # Inicializa a variável 'fidelity' no início
        
        if self._network.get_timeslot() > 0:
            # Aplica um fator de decoerência (0.99 neste exemplo)
            new_fidelity = max(0, fidelity * 0.99)  
            qubit.set_current_fidelity(new_fidelity)  # Atualiza a fidelidade do qubit
            self.logger.log(f'A fidelidade do qubit {qubit} é {new_fidelity}')
            return new_fidelity

        self.logger.log(f'A fidelidade do qubit {qubit} é {fidelity}')
        return fidelity

    def fidelity_measurement(self, qubit1: Qubit, qubit2: Qubit):
        """Mede e aplica a decoerência em dois qubits, e loga o resultado."""
        fidelity1 = self.fidelity_measurement_only_one(qubit1)
        fidelity2 = self.fidelity_measurement_only_one(qubit2)
        combined_fidelity = fidelity1 * fidelity2
        self.logger.log(f'A fidelidade entre o qubit {fidelity1} e o qubit {fidelity2} é {combined_fidelity}')
        return combined_fidelity
    
    def entanglement_creation_heralding_protocol(self, alice: Host, bob: Host):
        """Protocolo de criação de emaranhamento com sinalização.

        Returns:
            bool: True se o protocolo foi bem sucedido, False caso contrário.
        """
        self._network.timeslot() # Incrementa o timeslot
        self.used_qubits += 2

        qubit1 = alice.get_last_qubit()
        qubit2 = bob.get_last_qubit()

        q1 = qubit1.get_current_fidelity()
        q2 = qubit2.get_current_fidelity()

        epr_fidelity = q1 * q2
        self.logger.log(f'Timeslot {self._network.get_timeslot()}: Par epr criado com fidelidade {epr_fidelity}')
        epr = self.create_epr_pair(epr_fidelity)

        # Armazena o EPR criado na lista de EPRs criados
        self.created_eprs.append(epr)

        alice_host_id = alice.host_id
        bob_host_id = bob.host_id

        if epr_fidelity >= 0.8:
            # Se a fidelidade for adequada, adiciona o EPR ao canal da rede
            self._network.graph.edges[(alice_host_id, bob_host_id)]['eprs'].append(epr)
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: O protocolo de criação de emaranhamento foi bem sucedido com a fidelidade necessária.')
            return True
        else:
            # Adiciona o EPR ao canal mesmo com baixa fidelidade
            self._network.graph.edges[(alice_host_id, bob_host_id)]['eprs'].append(epr)
            self._failed_eprs.append(epr)
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: O protocolo de criação de emaranhamento foi bem sucedido, mas com fidelidade baixa.')
            return False

    def echp_on_demand(self, alice_host_id: int, bob_host_id: int):
        """Protocolo para a recriação de um entrelaçamento entre os qubits de acordo com a probabilidade de sucesso de demanda do par EPR criado.

        Args: 
            alice_host_id (int): ID do Host de Alice.
            bob_host_id (int): ID do Host de Bob.
            
        Returns:
            bool: True se o protocolo foi bem sucedido, False caso contrário.
        """
        self._network.timeslot()  # Incrementa o timeslot
        self.used_qubits += 2

        qubit1 = self._network.hosts[alice_host_id].get_last_qubit()
        qubit2 = self._network.hosts[bob_host_id].get_last_qubit()
            
        fidelity_qubit1 = self.fidelity_measurement_only_one(qubit1)
        fidelity_qubit2 = self.fidelity_measurement_only_one(qubit2)
                
        prob_on_demand_epr_create = self._network.graph.edges[alice_host_id, bob_host_id]['prob_on_demand_epr_create']
        echp_success_probability = prob_on_demand_epr_create * fidelity_qubit1 * fidelity_qubit2

        if uniform(0, 1) < echp_success_probability:
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: Par EPR criado com a fidelidade de {fidelity_qubit1 * fidelity_qubit2}')
            epr = self.create_epr_pair(fidelity_qubit1 * fidelity_qubit2)
            self._network.graph.edges[alice_host_id, bob_host_id]['eprs'].append(epr)
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: A probabilidade de sucesso do ECHP é {echp_success_probability}')
            return True
        self.logger.log(f'Timeslot {self._network.get_timeslot()}: A probabilidade de sucesso do ECHP falhou.')
        return False

    def echp_on_replay(self, alice_host_id: int, bob_host_id: int):
        """Protocolo para a recriação de um entrelaçamento entre os qubits de que já estavam perdendo suas características.

        Args: 
            alice_host_id (int): ID do Host de Alice.
            bob_host_id (int): ID do Host de Bob.
        
        Returns:
            bool: True se o protocolo foi bem sucedido, False caso contrário.
        """
        self._network.timeslot()  # Incrementa o timeslot
        self.used_qubits += 2
        
        qubit1 = self._network.hosts[alice_host_id].get_last_qubit()
        qubit2 = self._network.hosts[bob_host_id].get_last_qubit()
        
        fidelity_qubit1 = self.fidelity_measurement_only_one(qubit1)
        fidelity_qubit2 = self.fidelity_measurement_only_one(qubit2)
               
        prob_replay_epr_create = self._network.graph.edges[alice_host_id, bob_host_id]['prob_replay_epr_create']
        echp_success_probability = prob_replay_epr_create * fidelity_qubit1 * fidelity_qubit2

        if uniform(0, 1) < echp_success_probability:
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: Par EPR criado com a fidelidade de {fidelity_qubit1 * fidelity_qubit2}')
            epr = self.create_epr_pair(fidelity_qubit1 * fidelity_qubit2)
            self._network.graph.edges[alice_host_id, bob_host_id]['eprs'].append(epr)
            self.logger.log(f'Timeslot {self._network.get_timeslot()}: A probabilidade de sucesso do ECHP é {echp_success_probability}')
            return True
        self.logger.log(f'Timeslot {self._network.get_timeslot()}: A probabilidade de sucesso do ECHP falhou.')
        return False