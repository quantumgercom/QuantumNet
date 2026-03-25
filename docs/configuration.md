# Configuration

Este documento descreve todos os parametros da configuracao central do QuantumNet (`SimulationConfig`), usados no arquivo `quantumnet/default_config.yaml`.

## Visao Geral

A configuracao e dividida em 6 seções:

- `decoherence`
- `fidelity`
- `probability`
- `protocol`
- `defaults`
- `costs`

Se um campo nao existir no YAML, o valor padrao da dataclass em `quantumnet/config.py` e usado automaticamente.

## Regras Gerais de Validacao

- Probabilidades devem ficar entre `0` e `1`.
- Campos inteiros de contagem/custo devem ser `>= 0`.
- `probability.epr_create_min` deve ser `<= probability.epr_create_max`.
- `protocol.link_purification_after_failures` deve ser `<= protocol.link_max_attempts`.
- `defaults.channel_noise_type` deve ser um entre:
  - `random`
  - `bit-flip`
  - `werner`
  - `bitflip+werner`

## seção `decoherence`

| Parametro | Tipo | Padrao | Efeito |
|---|---|---|---|
| `per_timeslot` | `float` | `0.9` | Fator aplicado por tick; menor valor acelera degradacao de fidelidade ao longo do tempo. |
| `per_measurement` | `float` | `0.99` | Fator aplicado quando ha medicao de fidelidade; menor valor aumenta impacto da observacao. |
| `qubit_ttl_threshold` | `float` | `0.1` | Qubit e removido quando fidelidade cai abaixo deste limiar. |
| `epr_ttl_threshold` | `float` | `0.1` | Par EPR e removido quando fidelidade cai abaixo deste limiar. |

## seção `fidelity`

| Parametro | Tipo | Padrao | Efeito |
|---|---|---|---|
| `epr_threshold` | `float` | `0.8` | Limiar minimo para considerar EPR adequado/sucesso em protocolos. |
| `purification_threshold` | `float` | `0.8` | Limiar minimo de fidelidade para aceitar EPR apos purificacao. |
| `purification_min_probability` | `float` | `0.5` | Probabilidade minima para tentar purificacao. |
| `initial_epr_fidelity` | `float` | `1.0` | Fidelidade inicial dos pares EPR recem-criados. |

## seção `probability`

| Parametro | Tipo | Padrao | Efeito |
|---|---|---|---|
| `epr_create_max` | `float` | `1.0` | Limite superior da probabilidade de criacao de EPR nos canais. |
| `epr_create_min` | `float` | `0.2` | Limite inferior da probabilidade de criacao de EPR nos canais. |

## seção `protocol`

| Parametro | Tipo | Padrao | Efeito |
|---|---|---|---|
| `link_max_attempts` | `int` | `10` | Numero maximo de tentativas de enlace antes de falhar/encerrar. |
| `link_purification_after_failures` | `int` | `2` | Numero de falhas para acionar purificacao. |
| `transport_max_attempts` | `int` | `2` | Numero maximo de tentativas na camada de transporte. |
| `entanglement_max_attempts` | `int` | `5` | Numero maximo de tentativas para estabelecer emaranhamento. |

Observacao: no `default_config.yaml` atual pode nao existir `entanglement_max_attempts`. Nesse caso, o valor `5` da dataclass e aplicado.

## seção `defaults`

| Parametro | Tipo | Padrao | Efeito |
|---|---|---|---|
| `qubits_per_host` | `int` | `10` | Quantidade inicial de qubits por host. |
| `eprs_per_channel` | `int` | `10` | Quantidade inicial de pares EPR por canal. |
| `qubit_regen_interval` | `int` | `0` | Intervalo em ticks para regeneracao automatica de qubits (`0` desativa). |
| `qubit_regen_amount` | `int` | `3` | Quantidade de qubits adicionada por host em cada ciclo de regeneracao. |
| `channel_noise_type` | `str` | `random` | Modelo de ruido no canal: `bit-flip`, `werner`, `bitflip+werner` ou `random`. |

Observacao: no `default_config.yaml` atual pode nao existir `qubit_regen_interval` e `qubit_regen_amount`. Nesses casos, os valores padrao da dataclass sao usados.

## seção `costs`

| Parametro | Tipo | Padrao | Efeito |
|---|---|---|---|
| `heralding` | `int` | `1` | Custo em timeslots do protocolo de heralding. |
| `on_demand` | `int` | `1` | Custo em timeslots de operacoes on-demand. |
| `replay` | `int` | `1` | Custo em timeslots de repeticao/replay. |
| `purification` | `int` | `1` | Custo em timeslots de uma purificacao. |
| `swapping` | `int` | `1` | Custo em timeslots de um entanglement swapping. |
| `qubit_creation` | `int` | `1` | Custo em timeslots para criar qubits. |
| `e91_round` | `int` | `1` | Custo em timeslots por rodada E91. |
| `nepr_measurement` | `int` | `1` | Custo em timeslots da medicao no fluxo NEPR. |

Observacao: no `default_config.yaml` atual pode nao existir `nepr_measurement`. Nesse caso, o valor padrao `1` e aplicado.
