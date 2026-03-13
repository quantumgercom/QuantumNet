# QuantumNet

**QuantumNet** é um simulador de redes quânticas escrito em Python. O projeto é organizado em camadas: física, enlace, rede, transporte e aplicação, seguindo o modelo de pilha de protocolos quânticos. Cada camada é independente e pode ser usada separadamente, tornando o simulador modular e extensível para experimentação com diferentes protocolos e topologias.

## Funcionalidades

- Criação de nós com memória quântica e canais de comunicação
- Topologia personalizável: linha, anel, grade ou definida manualmente
- Arquitetura baseada em camadas (física, enlace, rede, transporte e aplicação)
- Suporte a protocolos quânticos como teletransporte e distribuição de chaves (QKD)
- Coleta de métricas por eventos com exportação para CSV
- Logging configurável para acompanhar a execução da simulação

## Requisitos

- **Python** 3.12.10
- Dependências listadas em `requirements.txt`

## Instalação

Clone o repositório e instale as dependências:

```bash
git clone https://github.com/artuenric/QuantumNet.git
cd QuantumNet
pip install -r requirements.txt
```

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
