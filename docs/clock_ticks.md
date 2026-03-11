# Passagem de Tempo no Simulador (Clock Ticks)

## Principio Geral

O tempo no simulador avanca **exclusivamente** por chamadas explicitas a `clock.tick()`. Operacoes primitivas (criar qubit, criar EPR, buscar rota, medir) **nunca** avancam o tempo — elas apenas registram eventos via `clock.emit()`.

Isso significa que:
- Quem controla o tempo e o **protocolo** (ou o usuario), nunca a operacao isolada.
- Criar 3 qubits "em paralelo" custa 0 ticks — o custo e decidido pelo contexto.
- Toda passagem de tempo dispara **decoerencia automatica** em todos os qubits e EPRs da rede.

---

## Tabela Resumo

| Operacao | Custo | Arquivo | Linha |
|----------|-------|---------|-------|
| `create_qubit()` | 0 ticks | `physical_layer.py` | ~61 |
| `create_epr_pair()` | 0 ticks | `physical_layer.py` | ~87 |
| `entanglement_creation_heralding_protocol()` | 1 tick | `physical_layer.py` | ~171 |
| `echp(mode='on_demand')` | 1 tick | `physical_layer.py` | ~283 |
| `echp(mode='on_replay')` | 1 tick | `physical_layer.py` | ~283 |
| `request()` | 1-2 ticks (indireto) | `link_layer.py` | ~63 |
| `purification()` | 1 tick | `link_layer.py` | ~145 |
| `short_route_valid()` | 0 ticks | `network_layer.py` | ~51 |
| `entanglement_swapping()` | 1 tick por swap | `network_layer.py` | ~120 |
| `run_transport_layer()` — criacao de qubits | 1 tick por qubit | `transport_layer.py` | ~101 |
| `run_transport_layer()` — transmissao | 0 ticks | `transport_layer.py` | ~122 |
| `prepare_e91_qubits()` | 0 ticks | `application_layer.py` | ~65 |
| `apply_bases_and_measure_e91()` | 0 ticks | `application_layer.py` | ~88 |
| `qkd_e91_protocol()` | 1 tick por rodada | `application_layer.py` | ~132 |

> Todos os arquivos estao em `quantumnet/components/layers/`.

---

## Detalhamento por Camada

### Physical Layer

**Arquivo:** `quantumnet/components/layers/physical_layer.py`

#### Operacoes que NAO avancam tempo (leaf)

- **`create_qubit(host_id)`** (linha ~61): Cria um qubit e adiciona a memoria do host. Emite `qubit_created`. Nao ticka porque a criacao de um qubit e uma operacao atomica — o custo de tempo, se houver, e decidido por quem chama.

- **`create_epr_pair(fidelity)`** (linha ~87): Cria um par EPR com a fidelidade informada. Emite `epr_created`. Mesma logica: operacao primitiva sem custo de tempo.

#### Protocolos que avancam tempo

- **`entanglement_creation_heralding_protocol(alice, bob)`** (linha ~171): Protocolo de criacao de emaranhamento com sinalizacao. Pega o ultimo qubit de cada host, calcula a fidelidade do par EPR resultante, e adiciona ao canal. **Custa 1 tick** porque representa uma rodada fisica completa de tentativa de emaranhamento.

- **`echp(alice_id, bob_id, mode)`** (linha ~283): Recriacao de emaranhamento unificada. Aceita `mode='on_demand'` (usa `prob_on_demand_epr_create`) ou `mode='on_replay'` (usa `prob_replay_epr_create`). A probabilidade do canal e multiplicada pela fidelidade dos qubits para determinar sucesso. **Custa 1 tick** — representa a tentativa de recriar o emaranhamento.

---

### Link Layer

**Arquivo:** `quantumnet/components/layers/link_layer.py`

#### `request(alice_id, bob_id)` — Custo indireto: 1-2 ticks (linha ~63)

O metodo `request` tenta criar emaranhamento ate 2 vezes. Ele **nao ticka diretamente** — quem ticka e o `entanglement_creation_heralding_protocol` chamado internamente. Portanto:
- Sucesso na 1a tentativa: 1 tick (do heralding)
- Sucesso na 2a tentativa: 2 ticks (2x heralding)
- Falha + purificacao: 2 ticks (heralding) + 1 tick (purificacao) = 3 ticks

O request em si apenas emite `link_request_attempt` a cada tentativa.

#### `purification(alice_id, bob_id)` — 1 tick (linha ~145)

Purificacao de pares EPR com fidelidade baixa. Combina 2 EPRs falhos calculando uma nova fidelidade. **Custa 1 tick** diretamente. Emite `purification_success` ou `purification_failed` conforme o resultado.

---

### Network Layer

**Arquivo:** `quantumnet/components/layers/network_layer.py`

#### `short_route_valid(Alice, Bob)` — 0 ticks (linha ~51)

Busca a menor rota valida (com EPRs disponiveis) entre dois hosts. **Nunca avanca tempo** — e uma query pura. Apenas emite `route_lookup`. Isso e intencional: consultar o estado da rede nao deveria custar tempo de simulacao.

#### `entanglement_swapping(Alice, Bob)` — 1 tick por swap (linha ~120)

Realiza entanglement swapping ao longo de toda a rota. A cada par de segmentos processados, **ticka 1 vez**. Para uma rota `[A, B, C, D]`:
- Swap B (conecta A-C): 1 tick
- Swap C (conecta A-D): 1 tick
- Total: 2 ticks

Ao final, emite `entanglement_swapping_complete`.

---

### Transport Layer

**Arquivo:** `quantumnet/components/layers/transport_layer.py`

#### `run_transport_layer(alice_id, bob_id, num_qubits)` — custo variavel

Este metodo tem dois momentos distintos:

1. **Criacao de qubits sob demanda** (linha ~101): Quando Alice nao tem qubits suficientes na memoria, cada qubit criado **custa 1 tick** (`clock.tick()` + `create_qubit()`). Se Alice ja tem os qubits, custo = 0.

2. **Transmissao/teletransporte** (linha ~122): O loop de transmissao usa `short_route_valid` (0 ticks) e apenas manipula memorias e emite eventos (`qubit_teleported`, `transport_complete` ou `transport_failed`). **Nao ticka diretamente**.

**Custo total**: `max(0, qubits_necessarios - qubits_disponiveis)` ticks.

---

### Application Layer

**Arquivo:** `quantumnet/components/layers/application_layer.py`

#### `prepare_e91_qubits(key, bases)` — 0 ticks (linha ~65)

Prepara qubits para o protocolo E91 aplicando portas X e Hadamard conforme a chave e bases. **Nao avanca tempo** — e preparacao local. Emite `e91_qubits_prepared`.

#### `apply_bases_and_measure_e91(qubits, bases)` — 0 ticks (linha ~88)

Aplica bases de medicao e mede os qubits. **Nao avanca tempo** — medicao e operacao local. Emite `e91_measurement`.

#### `qkd_e91_protocol(alice_id, bob_id, num_bits)` — 1 tick por rodada (linha ~132)

Protocolo completo E91. Cada rodada do loop `while` (preparar qubits, transmitir, medir, comparar bases) termina com **1 tick** apos a transmissao. O custo total depende de quantas rodadas sao necessarias para gerar `num_bits` bits de chave.

> **Nota**: A transmissao interna via `run_transport_layer` pode adicionar ticks proprios se precisar criar qubits sob demanda.

---

## Decoerencia Automatica

**Arquivo:** `quantumnet/components/network.py`, metodo `_decoherence_on_tick()` (linha ~398)

A cada chamada de `clock.tick()`, o callback de decoerencia e disparado automaticamente. Ele aplica:

- **Fator 0.9** na fidelidade de todos os qubits na memoria de cada host (apenas qubits criados em timeslots anteriores ao atual)
- **Fator 0.9** na fidelidade de todos os EPRs em todos os canais da rede

Isso garante que quanto mais tempo passa, mais os recursos quanticos degradam — sem precisar chamar decoerencia manualmente em cada camada.

---

## Eventos Emitidos (sem avancar tempo)

Eventos registrados via `clock.emit()` nao avancam o tempo. Servem para rastreamento e analise.

| Evento | Emitido por | Descricao |
|--------|-------------|-----------|
| `qubit_created` | `physical_layer.create_qubit()` | Qubit criado na memoria de um host |
| `epr_created` | `physical_layer.create_epr_pair()` | Par EPR criado |
| `echp_success` | `physical_layer.heralding_protocol()` | Emaranhamento criado com fidelidade >= 0.8 |
| `echp_low_fidelity` | `physical_layer.heralding_protocol()` | Emaranhamento criado com fidelidade < 0.8 |
| `echp_on_demand_success` | `physical_layer.echp(mode='on_demand')` | ECHP sob demanda bem-sucedido |
| `echp_on_demand_failed` | `physical_layer.echp(mode='on_demand')` | ECHP sob demanda falhou |
| `echp_on_replay_success` | `physical_layer.echp(mode='on_replay')` | ECHP replay bem-sucedido |
| `echp_on_replay_failed` | `physical_layer.echp(mode='on_replay')` | ECHP replay falhou |
| `link_request_attempt` | `link_layer.request()` | Tentativa de emaranhamento na camada de enlace |
| `purification_success` | `link_layer.purification()` | Purificacao bem-sucedida |
| `purification_failed` | `link_layer.purification()` | Purificacao falhou |
| `route_lookup` | `network_layer.short_route_valid()` | Busca de rota realizada |
| `entanglement_swapping_complete` | `network_layer.entanglement_swapping()` | Swapping concluido |
| `qubit_teleported` | `transport_layer.run_transport_layer()` | Qubit teletransportado com sucesso |
| `transport_complete` | `transport_layer.run_transport_layer()` | Transmissao completa |
| `transport_failed` | `transport_layer.run_transport_layer()` | Transmissao falhou |
| `e91_qubits_prepared` | `application_layer.prepare_e91_qubits()` | Qubits E91 preparados |
| `e91_measurement` | `application_layer.apply_bases_and_measure_e91()` | Medicao E91 realizada |

Todos os eventos ficam acessiveis em `clock.history`, uma lista de dicionarios com `timeslot`, `event` e dados adicionais.
