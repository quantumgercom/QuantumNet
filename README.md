# QuantumNet

**QuantumNet** é um simulador de redes quânticas escrito em Python. O projeto é organizado em camadas: física, enlace, rede, transporte e aplicação, seguindo o modelo de pilha de protocolos quânticos. Cada camada é independente e pode ser usada separadamente, tornando o simulador modular e extensível para experimentação com diferentes protocolos e topologias.

## Requisitos

- **Python** 3.10
- Dependências listadas em `requirements.txt`

## Execução com Docker

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado
- [Docker Compose](https://docs.docker.com/compose/install/) instalado (já incluso no Docker Desktop)

### Passo a passo

1. Clone o repositório:

```bash
git clone https://github.com/artuenric/QuantumNet.git
cd QuantumNet
```

2. Construa a imagem Docker:

```bash
docker compose build
```

3. Para iniciar o container com um shell interativo Python:

```bash
docker compose run --rm quantumnet
```

4. Para abrir um terminal bash dentro do container (útil para rodar scripts):

```bash
docker compose run --rm quantumnet bash
```

5. Dentro do container, execute seus scripts normalmente:

```bash
python3 seu_script.py
```

### Reconstruir a imagem

Se alterar o `requirements.txt` ou o `Dockerfile`, reconstrua a imagem:

```bash
docker compose build --no-cache
```

### Desinstalação e limpeza

Para remover completamente o ambiente Docker do projeto:

```bash
# Parar e remover containers em execução
docker compose down

# Remover a imagem do QuantumNet
docker rmi quantumnet-quantumnet

# (Opcional) Limpeza geral do Docker - remove imagens não utilizadas
docker system prune -a
```

> **Atenção:** O comando `docker system prune -a` remove **todas** as imagens, containers e redes não utilizados do Docker, não apenas do QuantumNet. Use com cuidado se tiver outros projetos Docker.

## Alternativa: execução local com Python 3.10

Se preferir não usar Docker, basta ter o Python 3.10 instalado na sua máquina.

1. Clone o repositório:

```bash
git https://github.com/quantumgercom/QuantumNet.git
cd QuantumNet
```

2. (Opcional) Crie e ative um ambiente virtual:

```bash
python3.10 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Execute seus scripts:

```bash
python3 seu_script.py
```

### Desinstalação (instalação local)

Para remover completamente o ambiente virtual e as dependências:

```bash
# Desative o ambiente virtual (se estiver ativado)
deactivate

# Remova o diretório do ambiente virtual
rm -rf venv  # Linux/macOS
# ou
rd /s venv   # Windows

# (Opcional) Remova o repositório completo
cd ..
rm -rf QuantumNet  # Linux/macOS
# ou
rd /s QuantumNet   # Windows
```

## Teste rápido

Após instalar as dependências, execute o trecho abaixo para verificar se o simulador está funcionando corretamente:

```python
from quantumnet.runtime import Clock
from quantumnet.topology import Network

# Cria o relógio e a rede com topologia em linha de 3 nós
clock = Clock()
net = Network(clock=clock)
net.set_ready_topology('Line', 3)

# Verifica se a topologia foi criada
assert len(list(net.nodes)) == 3, "Deveria haver 3 nós"
assert len(list(net.edges)) == 2, "Deveria haver 2 arestas"

# Verifica se os hosts possuem qubits na memória
for host_id in net.nodes:
    host = net.get_host(host_id)
    assert len(host.memory) > 0, f"Host {host_id} deveria ter qubits na memória"

# Verifica se pares EPR foram distribuídos nos canais
for u, v in net.edges:
    assert len(net.get_eprs_from_edge(u, v)) > 0, f"Canal ({u},{v}) deveria ter pares EPR"

# Executa uma requisição na camada de enlace
resultado = {}
net.linklayer.request(0, 1, on_complete=lambda **kwargs: resultado.update(kwargs))
clock.run()

assert 'success' in resultado, "O callback da camada de enlace deveria ter sido chamado"
print("Todos os testes passaram! O simulador está funcionando.")
```

Salve o trecho acima como `teste_rapido.py` e execute:

```bash
# Localmente
python3 teste_rapido.py

# Com Docker
docker compose run --rm quantumnet python3 teste_rapido.py
```

> **Nota:** o comando `docker compose run --rm quantumnet` (sem argumentos extras) abre o interpretador interativo do Python (`>>>`). Para rodar um script, passe o comando diretamente como mostrado acima. Se já estiver dentro do `>>>`, cole o código Python diretamente no terminal.

## Estrutura do projeto

```
QuantumNet/
├── requirements.txt
├── quantumnet/
│   ├── config.py               # Configurações globais da simulação
│   ├── exceptions.py           # Exceções customizadas
│   ├── control/
│   │   ├── controller.py       # Controlador central da simulação
│   │   └── network_context.py  # Estado compartilhado entre camadas
│   ├── layers/
│   │   ├── physical_layer.py
│   │   ├── link_layer.py
│   │   ├── network_layer.py
│   │   ├── transport_layer.py
│   │   └── application_layer.py
│   ├── quantum/
│   │   ├── qubit.py            # Representação de qubits
│   │   └── epr.py              # Pares EPR
│   ├── runtime/
│   │   ├── clock.py            # Relógio de eventos discretos
│   │   └── simulation.py       # Utilitários de execução
│   ├── topology/
│   │   ├── host.py             # Nó da rede
│   │   └── network.py          # Classe principal da rede
│   └── utils/
│       ├── logger.py           # Logger (desabilitado por padrão)
│       └── metrics.py          # MetricsCollector (saída em CSV)
└── docs/                       # Documentação e exemplos do Repositório
```
