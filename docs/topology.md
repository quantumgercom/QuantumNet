# Topology

O módulo `topology` define as duas abstrações estruturais centrais da simulação: o `Host` (nó da rede) e o `Network` (ponto de entrada principal).

---

## Importação

```python
from quantumnet.topology import Host, Network
```

---

## Host

Um `Host` representa um nó na rede quântica. É uma estrutura leve que possui um identificador inteiro, uma lista de conexões, uma memória de qubits e uma tabela de roteamento.

### Construtor

```python
Host(host_id: int)
```

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `host_id` | `int` | Identificador único do host |

### Propriedades (somente leitura)

| Propriedade | Tipo | Descrição |
|---|---|---|
| `host_id` | `int` | ID do host |
| `connections` | `list` | Lista de IDs dos hosts conectados |
| `memory` | `list` | Lista de qubits na memória |
| `routing_table` | `dict` | Tabela de roteamento |

### Métodos Públicos

#### `add_connection(host_id_for_connection)`

Adiciona uma conexão ao host. Não permite duplicatas.

- Levanta `TypeError` se o argumento não for inteiro.

```python
host = Host(0)
host.add_connection(1)
host.add_connection(2)
print(host.connections)  # [1, 2]
```

#### `add_qubit(qubit)`

Adiciona um qubit à memória do host.

```python
host.add_qubit(qubit)
```

#### `consume_last_qubit() -> Qubit | None`

Remove e retorna o último qubit da memória. Retorna `None` se a memória estiver vazia.

```python
q = host.consume_last_qubit()
```

#### `set_routing_table(routing_table)`

Define a tabela de roteamento do host, substituindo a anterior.

```python
host.set_routing_table({0: [0], 1: [0, 1], 2: [0, 1, 2]})
```

#### `info() -> dict`

Retorna informações sobre o host em formato de dicionário.

```python
host.info()
# {'host_id': 0, 'memory': 5, 'routing_table': {0: [0], 1: [0, 1]}}
```

#### `announce_to_controller_app_has_finished()`

Informa (via log) que a aplicação no host foi concluída.

---

## Network

O `Network` é o **ponto de entrada principal** da simulação. Encapsula um grafo NetworkX, cria e conecta todas as cinco camadas de protocolo (Physical, Link, Network, Transport, Application) através de um `NetworkContext` compartilhado.

### Construtor

```python
Network(clock: Clock = None, config: SimulationConfig = None)
```

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `clock` | `Clock` | Relógio DES. Se `None`, cria um novo `Clock()` |
| `config` | `SimulationConfig` | Configuração da simulação. Se `None`, cria um novo `SimulationConfig()` |

### Propriedades (somente leitura)

| Propriedade | Tipo | Descrição |
|---|---|---|
| `hosts` | `dict` | Dicionário de hosts (`{host_id: Host}`) |
| `graph` | `nx.Graph` | Grafo da rede |
| `nodes` | `NodeView` | Nós do grafo |
| `edges` | `EdgeView` | Arestas do grafo |
| `physical` | `PhysicalLayer` | Camada física |
| `linklayer` | `LinkLayer` | Camada de enlace |
| `networklayer` | `NetworkLayer` | Camada de rede |
| `transportlayer` | `TransportLayer` | Camada de transporte |
| `application_layer` | `ApplicationLayer` | Camada de aplicação |

### Métodos Públicos

#### `set_ready_topology()`

Cria o grafo com uma das topologias prontas definidas em `config.topology`. Após criar o grafo, inicializa hosts, canais e pares EPR automaticamente.

| `config.topology.name` | `config.topology.args` | Descrição |
|---|---|---|
| `'Line'` | `n` | Cadeia linear com `n` nós |
| `'Ring'` | `n` | Anel com `n` nós |
| `'Grid'` | `rows, cols` | Grade 2D com `rows × cols` nós |

Os nós são numerados de 0 a n-1.

```python
net.config.topology.name = 'Line'
net.config.topology.args = [5]
net.set_ready_topology() # 0 — 1 — 2 — 3 — 4
net.config.topology.name = 'Ring'
net.config.topology.args = [4]
net.set_ready_topology() # 0 — 1 — 2 — 3 — 0
net.config.topology.name = 'Grid'
net.config.topology.args = [3, 3]
net.set_ready_topology() # grade 3×3
```

- Levanta `TopologyError` se `config.topology` estiver inválido (nome ausente/desconhecido ou argumentos incorretos).
- Levanta `TopologyError` se `set_ready_topology` receber argumentos diretamente.

#### `add_host(host)`

Adiciona um host à rede. Registra no dicionário de hosts e como nó do grafo. Também adiciona as arestas das conexões do host.

- Levanta `DuplicateHostError` se o host ID já existir.

```python
h0 = Host(0)
h1 = Host(1)
h0.add_connection(1)
h1.add_connection(0)
net.add_host(h0)
net.add_host(h1)
```

#### `get_host(host_id) -> Host`

Retorna o host com o ID especificado.

```python
host = net.get_host(0)
```

#### `get_eprs() -> dict`

Retorna um dicionário mapeando cada aresta à sua lista de pares EPR.

```python
eprs = net.get_eprs()
# {(0, 1): [<Epr>, <Epr>], (1, 2): [<Epr>], ...}
```

#### `get_eprs_from_edge(alice, bob) -> list`

Retorna a lista de pares EPR de uma aresta específica.

```python
eprs_01 = net.get_eprs_from_edge(0, 1)
```

#### `remove_epr(alice, bob) -> Epr | None`

Remove e retorna o último par EPR da aresta. Retorna `None` se não houver pares.

#### `start_hosts(num_qubits=None)`

Inicializa os hosts com qubits. Usa `config.defaults.qubits_per_host` se `num_qubits` for `None`. Também inicia a regeneração periódica de qubits.

#### `start_channels()`

Inicializa os canais (arestas do grafo) com probabilidades de criação EPR, lista vazia de EPRs e tipo de ruído.

#### `start_eprs(num_eprs=None)`

Inicializa pares EPR nos canais. Usa `config.defaults.eprs_per_channel` se `num_eprs` for `None`.

#### `draw()`

Desenha o grafo da rede usando matplotlib.

```python
net.draw()
```

#### `get_timeslot() -> int`

Retorna o timeslot atual da simulação. Wrapper de compatibilidade — prefira usar `clock.now` diretamente.

---

## Fluxo Típico de Uso

### Com topologia pronta

```python
from quantumnet.runtime.clock import Clock
from quantumnet.topology.network import Network

clock = Clock()
net = Network(clock=clock)
net.config.topology.name = 'Line'
net.config.topology.args = [5]
net.set_ready_topology()

# Acessar hosts e camadas
print(net.get_host(0).info())
print(len(net.get_eprs_from_edge(0, 1)), "pares EPR no canal 0-1")

clock.run()
```

### Com topologia manual

```python
from quantumnet.runtime.clock import Clock
from quantumnet.topology import Host, Network

clock = Clock()
net = Network(clock=clock)

# Criar hosts manualmente
for i in range(3):
    h = Host(i)
    if i > 0:
        h.add_connection(i - 1)
    if i < 2:
        h.add_connection(i + 1)
    net.add_host(h)

# Inicializar manualmente
net.start_hosts()
net.start_channels()
net.start_eprs()

clock.run()
```

---

## Referência Rápida

| Método (`Host`) | O que faz |
|---|---|
| `add_connection(id)` | Adiciona conexão |
| `add_qubit(qubit)` | Adiciona qubit à memória |
| `consume_last_qubit()` | Remove e retorna último qubit |
| `set_routing_table(table)` | Define tabela de roteamento |
| `info()` | Retorna informações do host |

| Método (`Network`) | O que faz |
|---|---|
| `set_ready_topology()` | Cria topologia pronta via `config.topology` |
| `add_host(host)` | Adiciona host à rede |
| `get_host(id)` | Retorna host pelo ID |
| `get_eprs()` | Retorna todos os EPRs por aresta |
| `get_eprs_from_edge(a, b)` | Retorna EPRs de uma aresta |
| `remove_epr(a, b)` | Remove e retorna último EPR |
| `start_hosts(n)` | Inicializa hosts com qubits |
| `start_channels()` | Inicializa canais |
| `start_eprs(n)` | Inicializa EPRs nos canais |
| `draw()` | Desenha o grafo |
