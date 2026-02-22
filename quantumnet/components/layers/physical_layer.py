from ...objects import Logger, Qubit, Epr
from ...components import Host
from random import uniform
import random

class PhysicalLayer:
    def __init__(self, context, physical_layer_id: int = 0):
        """
        Inicializa a camada física.

        Args:
            context (NetworkContext): Contexto compartilhado da rede.
            physical_layer_id (int): Id da camada física.
        """
        self._physical_layer_id = physical_layer_id
        self._context = context
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
    
    def create_qubit(self, host_id: int, increment_qubits: bool = True):
        """Cria um qubit e adiciona à memória do host especificado.

        Args:
            host_id (int): ID do host onde o qubit será criado.
            increment_qubits (bool): Se True, incrementa o contador de qubits usados.

        Raises:
            Exception: Se o host especificado não existir na rede.
        """
        if increment_qubits:
            self.used_qubits += 1

        if host_id not in self._context.hosts:
            raise Exception(f'Host {host_id} não existe na rede.')

        qubit_id = self._count_qubit
        qubit = Qubit(qubit_id)
        self._context.hosts[host_id].add_qubit(qubit)

        self._context.register_qubit_creation(qubit_id, "Physical Layer")

        self._count_qubit += 1
        self._context.clock.emit('qubit_created', host_id=host_id, qubit_id=qubit_id)
        self.logger.debug(f'Qubit {qubit_id} criado com fidelidade inicial {qubit.get_initial_fidelity()} e adicionado à memória do Host {host_id}.')

    def create_epr_pair(self, fidelity: float = 1.0, increment_eprs: bool = True):
        """Cria um par de qubits entrelaçados.

        Returns:
            Epr: Par EPR criado.
        """
        if increment_eprs:
            self.used_eprs += 1

        epr = Epr(self._count_epr, fidelity)
        self._count_epr += 1
        self._context.clock.emit('epr_created', epr_id=epr.epr_id, fidelity=fidelity)
        return epr

    def add_epr_to_channel(self, epr: Epr, channel: tuple):
        """Adiciona um par EPR ao canal.

        Args:
            epr (Epr): Par EPR.
            channel (tuple): Canal.
        """
        u, v = channel
        if not self._context.graph.has_edge(u, v):
            self._context.graph.add_edge(u, v, eprs=[])
        self._context.graph.edges[u, v]['eprs'].append(epr)
        self.logger.debug(f'Par EPR {epr} adicionado ao canal {channel}.')

    def remove_epr_from_channel(self, epr: Epr, channel: tuple):
        """Remove um par EPR do canal.

        Args:
            epr (Epr): Par EPR a ser removido.
            channel (tuple): Canal.
        """
        u, v = channel
        if not self._context.graph.has_edge(u, v):
            self.logger.debug(f'Canal {channel} não existe.')
            return
        try:
            self._context.graph.edges[u, v]['eprs'].remove(epr)
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
        
        if self._context.clock.now > 0:
            # Aplica um fator de decoerência por medição
            new_fidelity = max(0, fidelity * self._context.config.decoherence.per_measurement)
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
        self._context.clock.tick()
        self.used_qubits += 2

        qubit1 = alice.get_last_qubit()
        qubit2 = bob.get_last_qubit()

        q1 = qubit1.get_current_fidelity()
        q2 = qubit2.get_current_fidelity()

        epr_fidelity = q1 * q2
        self.logger.log(f'Timeslot {self._context.clock.now}: Par epr criado com fidelidade {epr_fidelity}')
        epr = self.create_epr_pair(epr_fidelity)

        # Armazena o EPR criado na lista de EPRs criados
        self.created_eprs.append(epr)

        alice_host_id = alice.host_id
        bob_host_id = bob.host_id

        if epr_fidelity >= self._context.config.fidelity.epr_threshold:
            # Se a fidelidade for adequada, adiciona o EPR ao canal da rede
            self._context.graph.edges[(alice_host_id, bob_host_id)]['eprs'].append(epr)
            self._context.clock.emit('echp_success', alice=alice_host_id, bob=bob_host_id, fidelity=epr_fidelity)
            self.logger.log(f'Timeslot {self._context.clock.now}: O protocolo de criação de emaranhamento foi bem sucedido com a fidelidade necessária.')
            return True
        else:
            # Adiciona o EPR ao canal mesmo com baixa fidelidade
            self._context.graph.edges[(alice_host_id, bob_host_id)]['eprs'].append(epr)
            self._failed_eprs.append(epr)
            self._context.clock.emit('echp_low_fidelity', alice=alice_host_id, bob=bob_host_id, fidelity=epr_fidelity)
            self.logger.log(f'Timeslot {self._context.clock.now}: O protocolo de criação de emaranhamento foi bem sucedido, mas com fidelidade baixa.')
            return False

    def echp_on_demand(self, alice_host_id: int, bob_host_id: int):
        """Protocolo para a recriação de um entrelaçamento entre os qubits de acordo com a probabilidade de sucesso de demanda do par EPR criado.

        Args: 
            alice_host_id (int): ID do Host de Alice.
            bob_host_id (int): ID do Host de Bob.
            
        Returns:
            bool: True se o protocolo foi bem sucedido, False caso contrário.
        """
        self._context.clock.tick()
        self.used_qubits += 2

        qubit1 = self._context.hosts[alice_host_id].get_last_qubit()
        qubit2 = self._context.hosts[bob_host_id].get_last_qubit()

        fidelity_qubit1 = self.fidelity_measurement_only_one(qubit1)
        fidelity_qubit2 = self.fidelity_measurement_only_one(qubit2)

        prob_on_demand_epr_create = self._context.graph.edges[alice_host_id, bob_host_id]['prob_on_demand_epr_create']
        echp_success_probability = prob_on_demand_epr_create * fidelity_qubit1 * fidelity_qubit2

        if uniform(0, 1) < echp_success_probability:
            self.logger.log(f'Timeslot {self._context.clock.now}: Par EPR criado com a fidelidade de {fidelity_qubit1 * fidelity_qubit2}')
            epr = self.create_epr_pair(fidelity_qubit1 * fidelity_qubit2)
            self._context.graph.edges[alice_host_id, bob_host_id]['eprs'].append(epr)
            self._context.clock.emit('echp_on_demand_success', alice=alice_host_id, bob=bob_host_id)
            self.logger.log(f'Timeslot {self._context.clock.now}: A probabilidade de sucesso do ECHP é {echp_success_probability}')
            return True
        self._context.clock.emit('echp_on_demand_failed', alice=alice_host_id, bob=bob_host_id)
        self.logger.log(f'Timeslot {self._context.clock.now}: A probabilidade de sucesso do ECHP falhou.')
        return False

    def echp_on_replay(self, alice_host_id: int, bob_host_id: int):
        """Protocolo para a recriação de um entrelaçamento entre os qubits de que já estavam perdendo suas características.

        Args: 
            alice_host_id (int): ID do Host de Alice.
            bob_host_id (int): ID do Host de Bob.
        
        Returns:
            bool: True se o protocolo foi bem sucedido, False caso contrário.
        """
        self._context.clock.tick()
        self.used_qubits += 2

        qubit1 = self._context.hosts[alice_host_id].get_last_qubit()
        qubit2 = self._context.hosts[bob_host_id].get_last_qubit()

        fidelity_qubit1 = self.fidelity_measurement_only_one(qubit1)
        fidelity_qubit2 = self.fidelity_measurement_only_one(qubit2)

        prob_replay_epr_create = self._context.graph.edges[alice_host_id, bob_host_id]['prob_replay_epr_create']
        echp_success_probability = prob_replay_epr_create * fidelity_qubit1 * fidelity_qubit2

        if uniform(0, 1) < echp_success_probability:
            self.logger.log(f'Timeslot {self._context.clock.now}: Par EPR criado com a fidelidade de {fidelity_qubit1 * fidelity_qubit2}')
            epr = self.create_epr_pair(fidelity_qubit1 * fidelity_qubit2)
            self._context.graph.edges[alice_host_id, bob_host_id]['eprs'].append(epr)
            self._context.clock.emit('echp_on_replay_success', alice=alice_host_id, bob=bob_host_id)
            self.logger.log(f'Timeslot {self._context.clock.now}: A probabilidade de sucesso do ECHP é {echp_success_probability}')
            return True
        self._context.clock.emit('echp_on_replay_failed', alice=alice_host_id, bob=bob_host_id)
        self.logger.log(f'Timeslot {self._context.clock.now}: A probabilidade de sucesso do ECHP falhou.')
        return False