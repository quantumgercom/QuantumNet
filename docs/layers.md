# Layers

O módulo `layers` implementa a pilha de protocolos do QuantumNet. Cada camada encapsula um conjunto de responsabilidades e depende apenas das camadas abaixo dela, seguindo uma arquitetura em pilha.

```
ApplicationLayer    (depende de: TransportLayer)
       │
TransportLayer      (depende de: NetworkLayer, PhysicalLayer)
       │
NetworkLayer        (depende de: PhysicalLayer, LinkLayer)
       │
LinkLayer           (depende de: PhysicalLayer)
       │
PhysicalLayer       (depende de: NetworkContext)
```

Todas as camadas compartilham um `NetworkContext` para acessar hosts, o grafo, configuração e o relógio. Todas as operações assíncronas seguem o padrão **fire-and-forget**: são agendadas via `clock.schedule()` e notificam conclusão por callback (`on_complete`).

---

## Importação

```python
from quantumnet.layers import (
    PhysicalLayer,
    LinkLayer,
    NetworkLayer,
    TransportLayer,
    ApplicationLayer,
)
```

Na prática, as camadas são criadas automaticamente pelo `Network` — raramente é necessário instanciá-las diretamente.

---

## PhysicalLayer

A camada física é responsável pela criação e gerenciamento de qubits e pares EPR. Controla ciclo de vida (TTL), decoerência e regeneração periódica de qubits.

### Construtor

```python
PhysicalLayer(context: NetworkContext, physical_layer_id: int = 0)
```

| Parâmetro | Descrição |
|---|---|
| `context` | Contexto compartilhado da rede (`NetworkContext`) |
| `physical_layer_id` | Identificador numérico da camada (padrão 0) |

### Métodos Públicos

#### `create_qubit(host_id, increment_qubits=True)`

Cria um qubit e adiciona à memória do host especificado. Agenda um callback de expiração (TTL) baseado na taxa de decoerência configurada.

- Emite: `qubit_created`
- Levanta `HostNotFoundError` se o host não existir.

```python
net.physical.create_qubit(host_id=0)
```

#### `create_epr_pair(fidelity=1.0, increment_eprs=True) -> Epr`

Cria um par de qubits entrelaçados (EPR). Retorna o objeto `Epr`.

- Emite: `epr_created`

```python
epr = net.physical.create_epr_pair(fidelity=0.95)
```

#### `add_epr_to_channel(epr, channel)`

Adiciona um par EPR a um canal (aresta do grafo). Agenda callback de expiração (TTL).

```python
net.physical.add_epr_to_channel(epr, (0, 1))
```

#### `remove_epr_from_channel(epr, channel)`

Remove um par EPR do canal especificado.

#### `start_qubit_regen()`

Inicia a regeneração periódica de qubits para todos os hosts. Usa `config.defaults.qubit_regen_interval` e `config.defaults.qubit_regen_amount`. Não faz nada se o intervalo for 0.

#### `stop_qubit_regen()`

Para a regeneração periódica. Callbacks já agendados encerram sem efeito.

#### `fidelity_measurement_only_one(qubit) -> float`

Mede a fidelidade de um único qubit, aplicando decoerência por medição. Retorna o valor de fidelidade.

#### `fidelity_measurement(qubit1, qubit2) -> float`

Mede e aplica decoerência a dois qubits. Retorna a fidelidade combinada (`f1 * f2`).

#### `entanglement_creation_heralding_protocol(alice, bob, high_fidelity=True, on_complete=None)`

Agenda o protocolo de criação de entrelaçamento (ECHP). Fire-and-forget.

- Emite: `echp_success` ou `echp_low_fidelity`
- Callback: `on_complete(success=bool, epr_fidelity=float)`

#### `echp(alice_host_id, bob_host_id, mode, on_complete=None)`

Agenda ECHP no modo especificado. `mode` pode ser `'on_demand'` ou `'on_replay'`.

- Emite: `echp_{mode}_success` ou `echp_{mode}_failed`
- Callback: `on_complete(success=bool)`

### Eventos Emitidos

| Evento | Dados | Descrição |
|---|---|---|
| `qubit_created` | `host_id`, `qubit_id` | Qubit criado |
| `qubit_expired` | `host_id`, `qubit_id` | Qubit expirou (TTL) |
| `epr_created` | `epr_id`, `fidelity` | Par EPR criado |
| `epr_expired` | `epr_id`, `channel` | Par EPR expirou (TTL) |
| `echp_success` | `alice`, `bob`, `fidelity` | ECHP bem-sucedido |
| `echp_low_fidelity` | `alice`, `bob`, `fidelity` | ECHP com fidelidade baixa |
| `qubits_regenerated` | `host_id`, `count` | Qubits regenerados |

---

## LinkLayer

A camada de enlace gerencia as requisições de entrelaçamento entre hosts vizinhos e implementa os protocolos de purificação.

### Construtor

```python
LinkLayer(context: NetworkContext, physical_layer: PhysicalLayer)
```

### Métodos Públicos

#### `request(alice_id, bob_id, high_fidelity=True, on_complete=None)`

Solicita criação de entrelaçamento entre Alice e Bob. Tenta até `config.protocol.link_max_attempts` vezes. Fire-and-forget.

- Emite: `link_request_success` ou `link_request_failed`
- Callback: `on_complete(success=bool)`

```python
net.linklayer.request(0, 1, on_complete=lambda success: print(success))
```

#### `channel_error_engine(f1, f2, noise_type) -> (p_success, f_new)`

Motor de erro de canal probabilístico. Dadas duas fidelidades EPR e um tipo de ruído, calcula a probabilidade de sucesso e a nova fidelidade após purificação.

| Tipo de Ruído | Descrição |
|---|---|
| `'bit-flip'` | Ruído de inversão de bit |
| `'werner'` | Estado de Werner |
| `'bitflip+werner'` | Combinação dos dois |

```python
p_success, f_new = net.linklayer.channel_error_engine(0.85, 0.90, 'werner')
```

#### `run_purification(alice_id, bob_id, strategy='symmetric', num_rounds=2, pool_size=0, on_complete=None)`

Orquestrador híbrido de purificação. Provisiona pares EPR, reserva um pool de backup e delega para a estratégia escolhida.

- `strategy`: `'symmetric'` ou `'pumping'`
- `pool_size`: número de pares extras para recuperação de falhas
- Emite: `purification_provisioned`, `purification_success` ou `purification_failed`

```python
net.linklayer.run_purification(0, 1, strategy='pumping', num_rounds=3, pool_size=2)
```

#### `purification_symmetric(alice_id, bob_id, num_rounds, pool=None, on_complete=None)`

Estratégia simétrica (árvore). Começa com `2^r` pares EPR. A cada rodada, os pares são agrupados dois a dois e purificados.

#### `purification_pumping(alice_id, bob_id, num_rounds, pool=None, on_complete=None)`

Estratégia de bombeamento (linear). Começa com 2 pares; cada rodada subsequente combina o par purificado com 1 novo par.

#### `purification(alice_id, bob_id, purification_type=1, on_complete=None)`

Purificação legada de passo único. Consome dois pares EPR e produz um de maior fidelidade.

| Tipo | Protocolo |
|---|---|
| 1 | Bit-flip (padrão) |
| 2 | BBPSSW |
| 3 | DEJMPS |

#### `purification_calculator(f1, f2, purification_type) -> float`

Cálculo puro da fórmula de purificação. Retorna a fidelidade resultante.

#### `echp(alice_host_id, bob_host_id, mode, on_complete=None)`

Agenda ECHP via camada de enlace, delegando à camada física para medição de fidelidade e criação de EPR.

### Eventos Emitidos

| Evento | Dados |
|---|---|
| `link_request_success` | `alice`, `bob`, `fidelity` |
| `link_request_failed` | `alice`, `bob`, `attempts` |
| `purification_provisioned` | `alice`, `bob`, `strategy`, `rounds`, `estimated_pairs`, `pool_size` |
| `purification_started` | `alice`, `bob`, `strategy`, `rounds`, `initial_pairs`, `pool_size` |
| `purification_round_success` | `alice`, `bob`, `round`, `fidelity` |
| `purification_round_failed` | `alice`, `bob`, `round` |
| `purification_pool_recovery` | `alice`, `bob`, `round`, `fidelity`, `pool_remaining` |
| `purification_success` | `alice`, `bob`, `strategy`, `fidelity`, `surviving_pairs` |
| `purification_failed` | `alice`, `bob`, `strategy`, `reason` |

---

## NetworkLayer

A camada de rede é responsável pelo roteamento e entanglement swapping entre hosts não adjacentes.

### Construtor

```python
NetworkLayer(context: NetworkContext, physical_layer: PhysicalLayer, link_layer: LinkLayer)
```

### Métodos Públicos

#### `short_route_valid(alice, bob) -> list | None`

Encontra a melhor rota (mais curta) entre dois hosts que possua pares EPR disponíveis em cada salto. Retorna a rota como lista de IDs de nós, ou `None` se não existir rota válida.

- Emite: `route_lookup`, `route_found`

```python
route = net.networklayer.short_route_valid(0, 4)
# [0, 1, 2, 3, 4]
```

#### `entanglement_swapping(alice=None, bob=None, on_complete=None)`

Agenda entanglement swapping ao longo da rota válida mais curta. Seleciona o EPR de maior fidelidade em cada salto. A probabilidade de sucesso do swap é `f1 * f2`.

- Emite: `entanglement_swapping_complete`
- Callback: `on_complete(success=bool)`

#### `request_entanglement(alice, bob, high_fidelity=True, on_complete=None)`

Estabelece um par entrelaçado ponta-a-ponta entre Alice e Bob. Para nós adjacentes, delega diretamente à camada de enlace. Para nós distantes, cria EPRs em cada salto e realiza entanglement swapping.

- Callback: `on_complete(success=bool)`

```python
net.networklayer.request_entanglement(0, 4, on_complete=lambda s: print(s))
```

### Eventos Emitidos

| Evento | Dados |
|---|---|
| `route_lookup` | `alice`, `bob` |
| `route_found` | `alice`, `bob`, `route_len` |
| `entanglement_swapping_complete` | `alice`, `bob`, `fidelity` |

---

## TransportLayer

A camada de transporte implementa o teletransporte de qubits entre hosts distantes e a requisição de pares EPR ponta-a-ponta.

### Construtor

```python
TransportLayer(context: NetworkContext, network_layer: NetworkLayer, physical_layer: PhysicalLayer)
```

### Métodos Públicos

#### `run_transport_layer(alice_id, bob_id, num_qubits, on_complete=None)`

Agenda a transmissão e protocolo de teletransporte. Se Alice não possui qubits suficientes, cria mais via cadeia agendada. Busca rotas válidas, verifica fidelidade do EPR, e teletransporta qubits (remove da memória de Alice, adiciona à de Bob com fidelidade degradada: `f_alice * f_rota`).

- Emite: `qubit_teleported`, `transport_complete` ou `transport_failed`
- Callback: `on_complete(success=bool)`

```python
net.transportlayer.run_transport_layer(0, 4, num_qubits=3)
```

#### `request_epr_pairs(alice_id, bob_id, num_pairs, high_fidelity=True, on_complete=None)`

Solicita `num_pairs` pares entrelaçados ponta-a-ponta entre Alice e Bob. Delega à camada de rede com suporte a retentativas (`config.protocol.entanglement_max_attempts`).

- Emite: `epr_request_complete` ou `epr_request_failed`
- Callback: `on_complete(success=bool, count=int)`

### Eventos Emitidos

| Evento | Dados |
|---|---|
| `qubit_teleported` | `alice`, `bob`, `fidelity`, `fidelity_alice`, `fidelity_route`, `route_len` |
| `transport_complete` | `alice`, `bob`, `count` |
| `transport_failed` | `alice`, `bob`, `delivered`, `requested` |
| `epr_request_complete` | `alice`, `bob`, `count` |
| `epr_request_failed` | `alice`, `bob` |

---

## ApplicationLayer

A camada de aplicação implementa protocolos de alto nível que utilizam a infraestrutura das camadas inferiores.

### Construtor

```python
ApplicationLayer(context: NetworkContext, transport_layer: TransportLayer)
```

### Métodos Públicos

#### `run_app(app_name, *args, on_complete=None)`

Despachante. Agenda a aplicação desejada pelo nome. Aplicações disponíveis:

| Nome | Argumentos | Protocolo |
|---|---|---|
| `"QKD_E91"` | `alice_id, bob_id, num_qubits` | E91 QKD |
| `"NEPR"` | `alice_id, bob_id, num_pairs` | Network EPR |

```python
net.application_layer.run_app("QKD_E91", 0, 4, 10, on_complete=callback)
```

#### `qkd_e91_protocol(alice_id, bob_id, num_bits, on_complete=None)`

Protocolo E91 de distribuição quântica de chaves. Alice prepara qubits, transmite para Bob via camada de transporte, Bob mede com bases aleatórias, ambos comparam bases e extraem bits coincidentes. Repete em rodadas até obter `num_bits` bits de chave.

- Emite: `e91_complete` ou `e91_failed`
- Callback: `on_complete(success=bool, key=list|None)`

#### `nepr_protocol(alice_id, bob_id, num_pairs, high_fidelity=True, on_complete=None)`

Protocolo NEPR (Network EPR). Solicita `num_pairs` pares EPR ponta-a-ponta via camada de transporte, depois mede e consome os pares do canal.

- Emite: `nepr_complete` ou `nepr_failed`
- Callback: `on_complete(success=bool, measurements=list|None)`

#### `prepare_e91_qubits(key, bases) -> list`

Prepara qubits para o protocolo E91. Aplica porta X para bit=1 e porta Hadamard para base=1.

- Emite: `e91_qubits_prepared`

#### `apply_bases_and_measure_e91(qubits, bases) -> list`

Aplica bases de medição e mede qubits no E91. Aplica Hadamard antes da medição se base=1. Retorna lista de resultados de medição.

- Emite: `e91_measurement`

### Eventos Emitidos

| Evento | Dados |
|---|---|
| `e91_qubits_prepared` | `alice`, `count` |
| `e91_measurement` | `bob`, `count` |
| `e91_complete` | `alice`, `bob`, `key_length` |
| `e91_failed` | `alice`, `bob`, `reason` |
| `nepr_complete` | `alice`, `bob`, `count` |
| `nepr_failed` | `alice`, `bob`, `reason` |

---

## Acessando as Camadas

As camadas são acessadas como propriedades do objeto `Network`:

```python
from quantumnet.runtime.clock import Clock
from quantumnet.topology.network import Network

clock = Clock()
net = Network(clock=clock)
net.config.topology.name = 'Line'
net.config.topology.args = [5]
net.set_ready_topology()

net.physical            # PhysicalLayer
net.linklayer           # LinkLayer
net.networklayer        # NetworkLayer
net.transportlayer      # TransportLayer
net.application_layer   # ApplicationLayer
```

---

## Exemplo Completo

```python
from quantumnet.runtime.clock import Clock
from quantumnet.topology.network import Network
from quantumnet.utils import MetricsCollector

clock = Clock()
net = Network(clock=clock)

with MetricsCollector(clock, 'resultados.csv') as col:
    net.config.topology.name = 'Line'
    net.config.topology.args = [5]
    net.set_ready_topology()

    # Teleportar 3 qubits do nó 0 ao nó 4
    net.transportlayer.run_transport_layer(0, 4, num_qubits=3)

    # Executar E91 QKD entre nós 0 e 4
    net.application_layer.run_app("QKD_E91", 0, 4, 10)

    clock.run()
```
