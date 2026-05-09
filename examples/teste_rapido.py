from quantumnet.runtime import Clock
from quantumnet.topology import Network

# Cria o relogio e a rede com topologia em linha de 3 nos
clock = Clock()
net = Network(clock=clock)
net.config.topology.name = "Line"
net.config.topology.args = [3]
net.set_ready_topology()

# Verifica se a topologia foi criada
assert len(list(net.nodes)) == 3, "Deveria haver 3 nos"
assert len(list(net.edges)) == 2, "Deveria haver 2 arestas"

# Verifica se os hosts possuem qubits na memoria
for host_id in net.nodes:
    host = net.get_host(host_id)
    assert len(host.memory) > 0, f"Host {host_id} deveria ter qubits na memoria"

# Verifica se pares EPR foram distribuidos nos canais
for u, v in net.edges:
    assert len(net.get_eprs_from_edge(u, v)) > 0, f"Canal ({u},{v}) deveria ter pares EPR"

# Executa uma requisicao na camada de enlace
resultado = {}
net.linklayer.request(0, 1, on_complete=lambda **kwargs: resultado.update(kwargs))
clock.run()

assert "success" in resultado, "O callback da camada de enlace deveria ter sido chamado"
print("Todos os testes passaram! O simulador esta funcionando.")
