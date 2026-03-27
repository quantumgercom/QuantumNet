# Clock

O `Clock` é o coração temporal do QuantumNet. Toda a simulação avança através deste módulo: nenhum tempo passa sozinho, nenhuma ação acontece sem estar agendada ou emitida pelo relógio.

---

## Conceito: Simulação por Eventos Discretos (DES)

O QuantumNet não simula tempo contínuo. O tempo é dividido em **timeslots** — unidades discretas e inteiras. O relógio só avança quando há um evento agendado para o futuro. Entre dois eventos consecutivos, o tempo "pula" diretamente para o próximo, sem gastar CPU com timeslots vazios.

```
timeslot:  0 ──────► 3 ──────► 7 ──────► 10 ──► fim
eventos:   A          B,C        D          E
```

Nesse exemplo, `step()` avança diretamente de 0 para 3 (onde B e C executam juntos), depois para 7, e assim por diante.

---

## Instanciação

```python
from quantumnet.runtime.clock import Clock

clock = Clock()
print(clock.now)  # 0
```

---

## Avançando o Tempo

### `schedule(delay, callback, **kwargs)`

Agenda uma função para ser chamada daqui a `delay` timeslots a partir do instante atual.

```python
def hello(msg):
    print(f"[t={clock.now}] {msg}")

clock.schedule(5, hello, msg="oi")   # dispara no timeslot 5
clock.schedule(0, hello, msg="já")  # dispara no timeslot atual (delay=0)
```

- `delay` deve ser `>= 0`. Valor negativo levanta `ValueError`.
- Múltiplos eventos no mesmo timeslot executam em ordem FIFO (primeiro agendado, primeiro executado).
- Callbacks agendados com `delay=0` dentro de outro callback são processados **no mesmo `step()`**.

### `step() → bool`

Avança o relógio até o próximo timeslot com eventos e executa todos eles.

Retorna `True` se ao menos um evento foi processado; `False` se a fila está vazia.

```python
while clock.step():
    pass  # processa event a event até esgotar
```

### `run()`

Atalho para executar `step()` até a fila esvaziar — equivalente ao laço acima.

```python
clock.run()
```

---

## Registrando Eventos

### `emit(event_name, **data)`

Grava um evento no histórico **sem** avançar o tempo. Usado pelas camadas da rede para sinalizar que algo aconteceu (EPR criado, qubit teleportado, rota encontrada etc.).

```python
clock.emit('epr_created', epr_id=42, fidelity=0.95)
# {'timeslot': <now>, 'event': 'epr_created', 'epr_id': 42, 'fidelity': 0.95}
```

O `emit` **não move o relógio** — apenas registra e dispara callbacks de escuta.

---

## Ouvindo Eventos

### `on(event_name, callback)`

Registra um callback para um evento específico. O callback recebe o relógio e os dados do evento.

```python
def on_epr(clock, epr_id, fidelity):
    print(f"[t={clock.now}] EPR {epr_id} criado com fidelidade {fidelity:.3f}")

clock.on('epr_created', on_epr)
```

Assinatura obrigatória: `callback(clock, **data)`.

### `listen_all(callback)`

Registra um callback que dispara em **todo** `emit`, independente do nome do evento. Útil para logging genérico ou coleta de métricas.

```python
def tudo(clock, event_name, **data):
    print(f"[t={clock.now}] {event_name}: {data}")

clock.listen_all(tudo)
```

Assinatura obrigatória: `callback(clock, event_name, **data)`.

---

## Histórico

Todos os eventos emitidos ficam acessíveis em `clock.history` — uma lista de dicionários em ordem cronológica.

```python
for entry in clock.history:
    print(entry['timeslot'], entry['event'])
```

Cada entrada tem pelo menos `timeslot` e `event`, mais os campos extras passados no `emit`.

---

## Fluxo Típico de Uso com a Rede

```python
from quantumnet.runtime.clock import Clock
from quantumnet.topology.network import Network

clock = Clock()
net = Network(clock=clock)
net.config.topology.name = 'Line'
net.config.topology.args = [5]
net.set_ready_topology()

# opcional: ouvir eventos antes de rodar
clock.on('epr_created', lambda c, **d: print(f"EPR criado: {d}"))

clock.run()

print(f"Simulação encerrada no timeslot {clock.now}")
print(f"Total de eventos: {len(clock.history)}")
```

### Com MetricsCollector (coleta automática para CSV)

```python
from quantumnet.utils import MetricsCollector

clock = Clock()
net = Network(clock=clock)

with MetricsCollector(clock, 'resultados.csv') as col:
    net.config.topology.name = 'Line'
    net.config.topology.args = [5]
    net.set_ready_topology()
    clock.run()
# CSV gravado ao sair do bloco with
```

O `MetricsCollector` usa `listen_all` internamente para capturar todos os eventos sem nenhuma configuração extra.

---

## Referência Rápida

| Método | O que faz | Move o tempo? |
|---|---|---|
| `schedule(delay, fn, **kw)` | Agenda `fn` para daqui `delay` ticks | Não |
| `step()` | Executa todos os eventos do próximo tick | Sim |
| `run()` | Executa todos os eventos até a fila esvaziar | Sim |
| `emit(name, **data)` | Registra evento no histórico e dispara listeners | Não |
| `on(name, fn)` | Registra listener para evento específico | Não |
| `listen_all(fn)` | Registra listener para todos os eventos | Não |
| `clock.now` | Timeslot atual | — |
| `clock.history` | Lista de todos os eventos emitidos | — |
