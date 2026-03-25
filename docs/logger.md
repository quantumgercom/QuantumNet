# Logger

O `Logger` é o sistema de log do QuantumNet. É um **singleton** — existe uma única instância em toda a simulação, compartilhada por todas as camadas da rede.

Por padrão, o Logger está **desativado**: todo output é descartado silenciosamente. É necessário chamá-lo explicitamente para habilitar o registro.


---

## Obtendo a instância

Nunca instancie `Logger()` diretamente fora do código interno. Use sempre `get_instance()`:

```python
from quantumnet.utils import Logger

logger = Logger.get_instance()
```

A primeira chamada cria a instância; as seguintes retornam a mesma.

---

## Ativando o Logger

Por padrão, `activate()` não é chamado e todos os logs são descartados. Para habilitar:

```python
logger.activate()
```

### Parâmetros de `activate(level, console, file_log, filename)`

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `level` | `'INFO'` | Nível mínimo: `'DEBUG'`, `'INFO'`, `'WARNING'`, `'ERROR'` |
| `console` | `False` | Exibe os logs no terminal |
| `file_log` | `True` | Grava os logs em arquivo |
| `filename` | `None` | Nome do arquivo. Se `None`, gera automaticamente: `quantumnet_YYYYMMDD_HHMMSS.log` |

### Exemplos

```python
# Apenas arquivo, nível INFO (padrão)
logger.activate()

# Arquivo + console, nível DEBUG
logger.activate(level='DEBUG', console=True)

# Apenas console, sem arquivo
logger.activate(console=True, file_log=False)

# Arquivo com nome fixo
logger.activate(filename='minha_simulacao.log')
```

Chamar `activate()` múltiplas vezes substitui os handlers anteriores — só o último conjunto de configurações vale.

---

## Registrando mensagens

| Método | Nível | Quando usar |
|---|---|---|
| `logger.log(msg)` | INFO | Progresso normal da simulação |
| `logger.warn(msg)` | WARNING | Situações inesperadas mas não fatais |
| `logger.error(msg)` | ERROR | Falhas que impedem uma operação |
| `logger.debug(msg)` | DEBUG | Detalhes internos para diagnóstico |

```python
logger.log("Transmissão concluída entre nós 0 e 4")
logger.warn("Fidelidade abaixo do limiar: 0.71")
logger.error("Rota não encontrada entre 2 e 5")
logger.debug(f"Qubit criado no timeslot {clock.now}")
```

Mensagens com nível abaixo do configurado em `activate()` são ignoradas silenciosamente.

---

## Formato do arquivo de log

```
2026-03-17 14:23:01,482 [INFO] Transmissão concluída entre nós 0 e 4
2026-03-17 14:23:01,483 [WARNING] Fidelidade abaixo do limiar: 0.71
2026-03-17 14:23:01,490 [DEBUG] Qubit criado no timeslot 7
```

---

## Fluxo típico de uso

```python
from quantumnet.utils import Logger
from quantumnet.runtime.clock import Clock
from quantumnet.topology.network import Network

logger = Logger.get_instance()
logger.activate(level='DEBUG', console=True, filename='sim.log')

clock = Clock()
net = Network(clock=clock)
net.config.topology.name = 'Line'
net.config.topology.args = [5]
net.set_ready_topology()
clock.run()
```

---

## Logger vs MetricsCollector

O Logger e o `MetricsCollector` são complementares e servem propósitos distintos:

| | Logger | MetricsCollector |
|---|---|---|
| **Finalidade** | Diagnóstico e depuração | Análise quantitativa |
| **Saída** | Arquivo `.log` / console | Arquivo `.csv` |
| **Ativação** | Manual (`activate()`) | Automática (bloco `with`) |
| **Padrão** | Desativado | Ativo enquanto no bloco `with` |
| **Conteúdo** | Mensagens de texto livres | Eventos estruturados do relógio |
