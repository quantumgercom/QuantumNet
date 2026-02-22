import networkx as nx
from quantumnet.components import Host
from quantumnet.objects import Logger, Epr
from random import uniform

class LinkLayer:
    def __init__(self, context, physical_layer):
        """
        Inicializa a camada de enlace.

        Args:
            context (NetworkContext): Contexto compartilhado da rede.
            physical_layer (PhysicalLayer): Camada física.
        """
        self._context = context
        self._physical_layer = physical_layer
        self._requests = []
        self._failed_requests = []
        self.logger = Logger.get_instance()
        self.used_eprs = 0  # Inicializa o contador de EPRs utilizados
        self.used_qubits = 0  # Inicializa o contador de Qubits utilizados
        self.created_eprs = []  # Armazenar os EPRs criados pela camada física

    @property
    def requests(self):
        return self._requests

    @property
    def failed_requests(self):
        return self._failed_requests

    def __str__(self):
        """ Retorna a representação em string da camada de enlace. 
        
        Returns:
            str : Representação em string da camada de enlace.
        """
        return 'Link Layer'
    
    def get_used_eprs(self):
        self.logger.debug(f"Eprs usados na camada {self.__class__.__name__}: {self.used_eprs}")
        return self.used_eprs
    
    def get_used_qubits(self):
        self.logger.debug(f"Qubits usados na camada {self.__class__.__name__}: {self.used_qubits}")
        return self.used_qubits
    
    def request(self, alice_id: int, bob_id: int):
        """
        Solicitação de criação de emaranhamento entre Alice e Bob.
        
        Args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
        """
        try:
            alice = self._context.get_host(alice_id)
            bob = self._context.get_host(bob_id)
        except KeyError:
            self.logger.log(f'Host {alice_id} ou {bob_id} não encontrado na rede.')
            return False

        for attempt in range(1, self._context.config.protocol.link_max_attempts + 1):
            self._context.clock.emit('link_request_attempt', alice=alice_id, bob=bob_id, attempt=attempt)
            self.logger.log(f'Timeslot {self._context.clock.now}: Tentativa de emaranhamento entre {alice_id} e {bob_id}.')

            entangle = self._physical_layer.entanglement_creation_heralding_protocol(alice, bob)

            # Após cada tentativa de emaranhamento, transferimos os EPRs criados para a camada de enlace
            if entangle:
                self.used_eprs += 1
                self.used_qubits += 2
                self._requests.append((alice_id, bob_id))

                # Adiciona os EPRs criados pela camada física à lista de EPRs criados da camada de enlace
                if self._physical_layer.created_eprs:
                    self.created_eprs.extend(self._physical_layer.created_eprs)
                    self._physical_layer.created_eprs.clear()  # Limpa a lista da camada física

                self.logger.log(f'Timeslot {self._context.clock.now}: Entrelaçamento criado entre {alice} e {bob} na tentativa {attempt}.')
                return True
            else:
                self.logger.log(f'Timeslot {self._context.clock.now}: Entrelaçamento falhou entre {alice} e {bob} na tentativa {attempt}.')
                self._failed_requests.append((alice_id, bob_id))

        # Verifica se deve realizar a purificação após duas falhas
        if len(self._failed_requests) >= self._context.config.protocol.link_purification_after_failures:
            purification_success = self.purification(alice_id, bob_id)
            
            # Independente de a purificação ser bem-sucedida ou não, sempre transferimos os EPRs criados
            if self._physical_layer.created_eprs:
                self.created_eprs.extend(self._physical_layer.created_eprs)
                self._physical_layer.created_eprs.clear()  # Limpa a lista da camada física
            
            return purification_success

        # Após a segunda tentativa, garante que todos os EPRs criados sejam transferidos
        if self._physical_layer.created_eprs:
            self.created_eprs.extend(self._physical_layer.created_eprs)
            self._physical_layer.created_eprs.clear()  # Limpa a lista da camada física
            
        return False

    def purification_calculator(self, f1: int, f2: int, purification_type: int) -> float:
        """
        Cálculo das fórmulas de purificação.
        
        Args:
            f1: int : Fidelidade do primeiro EPR.
            f2: int : Fidelidade do segundo EPR.
            purification_type: int : Fórmula escolhida (1 - Default, 2 - BBPSSW Protocol, 3 - DEJMPS Protocol).
        
        Returns:
            float : Fidelidade após purificação.
        """
        f1f2 = f1 * f2

        if purification_type == 1:
            self.logger.log('A purificação utilizada foi tipo 1.')
            return f1f2 / ((f1f2) + ((1 - f1) * (1 - f2)))

        elif purification_type == 2:
            result = (f1f2 + ((1 - f1) / 3) * ((1 - f2) / 3)) / (f1f2 + f1 * ((1 - f2) / 3) + f2 * ((1 - f1) / 3) + 5 * ((1 - f1) / 3) * ((1 - f2) / 3))
            self.logger.log('A purificação utilizada foi tipo 2.')
            return result

        elif purification_type == 3:
            result = (2 * f1f2 + 1 - f1 - f2) / ((1 / 4) * (f1 + f2 - f1f2) + 3 / 4)
            self.logger.log('A purificação utilizada foi tipo 3.')
            return result
        
        self.logger.log('Purificação só pode aceitar os valores (1, 2 ou 3), a fórmula 1 foi escolhida por padrão.')
        return f1f2 / ((f1f2) + ((1 - f1) * (1 - f2)))


    def purification(self, alice_id: int, bob_id: int, purification_type: int = 1):
        """
        Purificação de EPRs.

        Args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
            purification_type : int : Tipo de protocolo de purificação.
        """
        self._context.clock.tick()

        eprs_fail = self._physical_layer.failed_eprs

        if len(eprs_fail) < 2:
            self.logger.log(f'Timeslot {self._context.clock.now}: Não há EPRs suficientes para purificação no canal ({alice_id}, {bob_id}).')
            return False

        eprs_fail1 = eprs_fail[-1]
        eprs_fail2 = eprs_fail[-2]
        f1 = eprs_fail1.get_current_fidelity()
        f2 = eprs_fail2.get_current_fidelity()

        purification_prob = (f1 * f2) + ((1 - f1) * (1 - f2))

        # Incrementa a contagem de EPRs utilizados, pois ambos serão usados na tentativa de purificação
        self.used_eprs += 2
        self.used_qubits += 4

        if purification_prob > self._context.config.fidelity.purification_min_probability:
            new_fidelity = self.purification_calculator(f1, f2, purification_type)

            if new_fidelity > self._context.config.fidelity.purification_threshold:
                epr_purified = Epr((alice_id, bob_id), new_fidelity)
                self._physical_layer.add_epr_to_channel(epr_purified, (alice_id, bob_id))
                self._physical_layer.failed_eprs.remove(eprs_fail1)
                self._physical_layer.failed_eprs.remove(eprs_fail2)
                self.logger.log(f'EPRS Usados {self.used_eprs}')
                self._context.clock.emit('purification_success', alice=alice_id, bob=bob_id, fidelity=new_fidelity)
                self.logger.log(f'Timeslot {self._context.clock.now}: Purificação bem sucedida no canal ({alice_id}, {bob_id}) com nova fidelidade {new_fidelity}.')
                return True
            else:
                self._physical_layer.failed_eprs.remove(eprs_fail1)
                self._physical_layer.failed_eprs.remove(eprs_fail2)
                self._context.clock.emit('purification_failed', alice=alice_id, bob=bob_id, reason='low_fidelity')
                self.logger.log(f'Timeslot {self._context.clock.now}: Purificação falhou no canal ({alice_id}, {bob_id}) devido a baixa fidelidade após purificação.')
                return False
        else:
            self._physical_layer.failed_eprs.remove(eprs_fail1)
            self._physical_layer.failed_eprs.remove(eprs_fail2)
            self._context.clock.emit('purification_failed', alice=alice_id, bob=bob_id, reason='low_probability')
            self.logger.log(f'Timeslot {self._context.clock.now}: Purificação falhou no canal ({alice_id}, {bob_id}) devido a baixa probabilidade de sucesso da purificação.')
            return False
        
    def avg_fidelity_on_linklayer(self):
        """
        Calcula a fidelidade média dos EPRs criados na camada de enlace.
        
        Returns:
            float : Fidelidade média dos EPRs da camada de enlace.
        """
        total_fidelity = 0
        total_eprs = len(self.created_eprs)

        for epr in self.created_eprs:   
            total_fidelity += epr.get_current_fidelity()

        if total_eprs == 0:
            self.logger.log('Não há EPRs criados na camada de enlace.')
            return 0


        self.logger.debug(f'Total de EPRs criados na camada de enlace: {total_eprs}')
        self.logger.debug(f'Total de fidelidade dos EPRs criados na camada de enlace: {total_fidelity}')
        avg_fidelity = total_fidelity / total_eprs
        self.logger.log(f'A fidelidade média dos EPRs criados na camada de enlace é {avg_fidelity}')
        return avg_fidelity
