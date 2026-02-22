import networkx as nx
from quantumnet.components import Host
from quantumnet.objects import Logger, Epr
from random import uniform

class TransportLayer:
    def __init__(self, context, network_layer, physical_layer):
        """
        Inicializa a camada de transporte.

        Args:
            context (NetworkContext): Contexto compartilhado da rede.
            network_layer (NetworkLayer): Camada de rede.
            physical_layer (PhysicalLayer): Camada física.
        """
        self._context = context
        self._physical_layer = physical_layer
        self._network_layer = network_layer
        self.logger = Logger.get_instance()
        self.transmitted_qubits = []
        self.used_eprs = 0
        self.used_qubits = 0
        self.created_eprs = []  # Lista para armazenar EPRs criados

    def __str__(self):
        """ Retorna a representação em string da camada de transporte. 
        
        returns:
            str : Representação em string da camada de transporte."""
        return f'Transport Layer'
    
    def get_used_eprs(self):
        self.logger.debug(f"Eprs usados na camada {self.__class__.__name__}: {self.used_eprs}")
        return self.used_eprs
    
    def get_used_qubits(self):
        self.logger.debug(f"Qubits usados na camada {self.__class__.__name__}: {self.used_qubits}")
        return self.used_qubits
    
    def avg_fidelity_on_transportlayer(self):
        """
        Calcula a fidelidade média de todos os qubits realmente utilizados na camada de transporte.

        returns:
            float : Fidelidade média dos qubits utilizados na camada de transporte.
        """
        total_fidelity = 0
        total_qubits_used = 0

        # Calcula a fidelidade dos qubits transmitidos e registrados no log de qubits transmitidos
        for qubit_info in self.transmitted_qubits:
            fidelity = qubit_info['F_final']
            total_fidelity += fidelity
            total_qubits_used += 1
            self.logger.log(f'Fidelidade do qubit utilizado de {qubit_info["alice_id"]} para {qubit_info["bob_id"]}: {fidelity}')

        # Considera apenas os qubits efetivamente transmitidos (não inclui os qubits que permanecem na memória dos hosts)
        if total_qubits_used == 0:
            self.logger.log('Nenhum qubit foi utilizado na camada de transporte.')
            return 0.0

        avg_fidelity = total_fidelity / total_qubits_used
        self.logger.log(f'A fidelidade média de todos os qubits utilizados na camada de transporte é {avg_fidelity}')
        
        return avg_fidelity


    def get_teleported_qubits(self):
        """
        Retorna a lista de qubits teletransportados.
        
        returns:
            list : Lista de dicionários contendo informações dos qubits teletransportados.
        """
        return self.transmitted_qubits

    def run_transport_layer(self, alice_id: int, bob_id: int, num_qubits: int):
        """
        Executa a requisição de transmissão e o protocolo de teletransporte.

        args:
            alice_id : int : Id do host Alice.
            bob_id : int : Id do host Bob.
            num_qubits : int : Número de qubits a serem transmitidos.

        returns:
            bool : True se a operação foi bem-sucedida, False caso contrário.
        """
        alice = self._context.get_host(alice_id)
        bob = self._context.get_host(bob_id)
        available_qubits = len(alice.memory)

        # Se Alice tiver menos qubits do que o necessário, crie mais qubits
        if available_qubits < num_qubits:
            qubits_needed = num_qubits - available_qubits
            self.logger.log(f'Número insuficiente de qubits na memória de Alice (Host {alice_id}). Criando mais {qubits_needed} qubits para completar os {num_qubits} necessários.')

            for _ in range(qubits_needed):
                self._context.clock.tick()
                self._physical_layer.create_qubit(alice_id)
                self.logger.log(f"Qubit criado para Alice (Host {alice_id}) no timeslot: {self._context.clock.now}")

            # Atualiza a quantidade de qubits disponíveis após a criação
            available_qubits = len(alice.memory)

        # Certifique-se de que Alice tenha exatamente o número de qubits necessários após a criação
        if available_qubits != num_qubits:
            self.logger.log(f'Erro: Alice tem {available_qubits} qubits, mas deveria ter {num_qubits} qubits. Abortando transmissão.')
            return False

        # Começa a transmissão dos qubits
        max_attempts = self._context.config.protocol.transport_max_attempts
        attempts = 0
        success_count = 0

        while attempts < max_attempts and success_count < num_qubits:
            self.logger.log(f'Tentativa {attempts + 1} de transmissão de qubits entre {alice_id} e {bob_id}.')

            for _ in range(num_qubits - success_count):
                # Tenta encontrar uma rota válida
                route = self._network_layer.short_route_valid(alice_id, bob_id)

                if route is None:
                    self.logger.log(f'Não foi possível encontrar uma rota válida na tentativa {attempts + 1}. Timeslot: {self._context.clock.now}')
                    break

                # Verifica a fidelidade dos pares EPR ao longo da rota
                fidelities = []
                for i in range(len(route) - 1):
                    node1 = route[i]
                    node2 = route[i + 1]


                    epr_pairs = self._context.get_eprs_from_edge(node1, node2)
                    if len(epr_pairs) == 0:
                        self.logger.log(f'Não foi possível encontrar pares EPR suficientes na rota {route[i]} -> {route[i + 1]}.')
                        break
                    fidelities.extend([epr.get_current_fidelity() for epr in epr_pairs])

                # Se falhar em encontrar pares EPR suficientes, tenta na próxima tentativa
                if len(fidelities) == 0:
                    attempts += 1
                    continue

                f_route = sum(fidelities) / len(fidelities)

                # Se a rota for encontrada, transmite o qubit imediatamente
                if len(alice.memory) > 0:  # Verifica se ainda há qubits na memória de Alice
                    qubit_alice = alice.memory.pop(0)  # REMOVE o qubit de Alice
                    f_alice = qubit_alice.get_current_fidelity()
                    F_final = f_alice * f_route

                    # Armazena informações sobre o qubit transmitido
                    qubit_info = {
                        'alice_id': alice_id,
                        'bob_id': bob_id,
                        'route': route,
                        'fidelity_alice': f_alice,
                        'fidelity_route': f_route,
                        'F_final': F_final,
                        'timeslot': self._context.clock.now,
                        'qubit': qubit_alice
                    }

                    # Adiciona o qubit transmitido à memória de Bob
                    qubit_alice.set_current_fidelity(F_final)
                    bob.memory.append(qubit_alice)

                    # Incrementa o contador de qubits e timeslot
                    success_count += 1
                    self.used_qubits += 1
                    self._context.clock.emit('qubit_teleported', alice=alice_id, bob=bob_id, fidelity=F_final)
                    self.logger.log(f'Teletransporte de qubit de {alice_id} para {bob_id} na rota {route} foi bem-sucedido com fidelidade final de {F_final}.')

                    # Armazena as informações do qubit transmitido
                    self.transmitted_qubits.append(qubit_info)
                else:
                    self.logger.log(f'Alice não possui qubits suficientes para continuar a transmissão.')
                    break

            attempts += 1

        if success_count == num_qubits:
            self._context.clock.emit('transport_complete', alice=alice_id, bob=bob_id, count=num_qubits)
            self.logger.log(f'Transmissão e teletransporte de {num_qubits} qubits entre {alice_id} e {bob_id} concluídos com sucesso. Timeslot: {self._context.clock.now}')
            return True
        else:
            self._context.clock.emit('transport_failed', alice=alice_id, bob=bob_id, delivered=success_count, requested=num_qubits)
            self.logger.log(f'Falha na transmissão de {num_qubits} qubits entre {alice_id} e {bob_id}. Apenas {success_count} qubits foram transmitidos com sucesso. Timeslot: {self._context.clock.now}')
            return False




