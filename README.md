# QuantumNet

## QuantumNet: Um Simulador de Redes Quânticas Baseado em Camadas

As redes quânticas são fundamentais para a futura Internet Quântica, mas sua implementação prática ainda enfrenta restrições físicas e operacionais que dificultam a avaliação de protocolos em ambientes reais. Nesse contexto, simuladores tornam-se ferramentas essenciais para investigar arquiteturas, mecanismos de comunicação e aplicações de forma controlada e reprodutível.

Este artefato apresenta o **QuantumNet**, um simulador de redes quânticas de código aberto orientado a eventos discretos. A ferramenta adota uma arquitetura explícita em camadas inspirada em modelos clássicos de rede, oferecendo um ambiente flexível para desenvolvimento, customização e avaliação de protocolos e algoritmos em diferentes níveis da pilha de comunicação.

# Estrutura do readme.md

Este README está organizado da seguinte forma:

1. Título do projeto e resumo do artigo/artefato.
2. Selos considerados no processo de avaliação.
3. Informações básicas do ambiente e requisitos.
4. Dependências e recursos de terceiros.
5. Preocupações com segurança.
6. Instalação (Docker e local).
7. Interface gráfica de configuração.
8. Teste mínimo de funcionamento.
9. Experimentos para reprodução das reivindicações.
10. Licença.

# Selos Considerados

Os selos considerados são: **Artefatos Disponíveis (SeloD), Artefatos Funcionais (SeloF), Artefatos Sustentáveis (SeloS) e Experimentos Reprodutíveis (SeloR)**.

# Informações básicas

Esta seção apresenta os componentes necessários para execução e replicação dos experimentos.

- Sistema operacional: Linux, macOS ou Windows.
- Linguagem: Python 3.10.
- Containerização (opcional, recomendada): Docker + Docker Compose.
- Recursos mínimos sugeridos: 1 vCPU, 2 GB de RAM, ~2 GB de espaço livre em disco para instalação e execução de testes básicos.

# Dependências

Informações relacionadas a dependências e recursos necessários para execução:

- **Python** 3.10.
- Dependências principais em `requirements.txt`.
- Dependências extras para notebooks em `requirements-notebook.txt`.
- Benchmarks e scripts de experimento devem ser executados a partir dos módulos e exemplos do repositório.

# Preocupações com segurança

A execução do artefato **não** envolve manipulação de dados sensíveis, elevação de privilégios de sistema ou acesso obrigatório a serviços externos críticos.

Cuidados recomendados:

- Execute em ambiente isolado (virtualenv ou Docker).
- Revise scripts próprios antes de executar.
- Não exponha serviços de notebook em rede pública sem autenticação.

# Instalação

Ao final desta seção, a ferramenta estará pronta para execução.

## Execução com Docker

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado.
- [Docker Compose](https://docs.docker.com/compose/install/) instalado (já incluso no Docker Desktop).

### Passo a passo

1. Clone o repositório:

```bash
git clone https://github.com/quantumgercom/QuantumNet.git
cd QuantumNet
```

2. Construa a imagem Docker:

```bash
docker compose build
```

3. Inicie o container com shell Python interativo:

```bash
docker compose run --rm quantumnet
```

4. Para abrir terminal bash no container:

```bash
docker compose run --rm quantumnet bash
```

5. Dentro do container, execute scripts:

```bash
python3 seu_script.py
```

### Executar notebooks Jupyter com Docker

1. Construa a imagem de notebook:

```bash
docker compose build quantumnet-notebook
```

2. Inicie o serviço:

```bash
docker compose up quantumnet-notebook
```

3. Acesse no navegador:

```text
http://localhost:8888
```

4. Para encerrar:

```bash
docker compose down
```

### Reconstruir a imagem

Se alterar `requirements.txt`, `requirements-notebook.txt`, `Dockerfile` ou `Dockerfile.notebook`:

```bash
docker compose build --no-cache
```

## Alternativa: execução local com Python 3.10

1. Clone o repositório:

```bash
git clone https://github.com/quantumgercom/QuantumNet.git
cd QuantumNet
```

2. (Opcional) Crie e ative ambiente virtual:

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

4. Execute scripts:

```bash
python3 seu_script.py
```

# Interface gráfica de configuração (Streamlit)

A interface gráfica permite editar o arquivo padrão `quantumnet/default_config.yaml` por meio de uma sidebar com as seções **Parâmetros** e **Versão**.

## Rodar localmente

```bash
python -m quantumnet gui
```

## Rodar com Docker

```bash
docker compose run --rm --service-ports quantumnet python -m quantumnet gui --host 0.0.0.0 --port 8501
```

Depois, acesse:

```text
http://localhost:8501
```

# Teste mínimo

Esta seção apresenta um passo a passo para validar a instalação e execução básica.

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

Salve como `teste_rapido.py` e execute:

```bash
# Localmente
python3 teste_rapido.py

# Com Docker
docker compose run --rm quantumnet python3 teste_rapido.py
```

# Experimentos

Esta seção descreve como reproduzir, a partir do artefato disponibilizado, as principais reivindicações associadas ao artigo.

## Reivindicação #1 — Execução de uma aplicação sobre a arquitetura em camadas

Esta reivindicação demonstra que o QuantumNet permite executar uma aplicação de alto nível sobre sua arquitetura em camadas. No cenário apresentado, o protocolo NEPR solicita pares EPR entre dois nós da rede, e o simulador processa essa requisição ao longo da pilha de comunicação, produzindo eventos, métricas e visualizações compatíveis com o comportamento do sistema.

Notebook correspondente: `examples/demo_nepr.ipynb`.

Considerando o ambiente do projeto previamente configurado, seja via Docker conforme descrito na seção de **Instalação** ou por instalação local das dependências, a reprodução deste caso de uso consiste na abertura do notebook Jupyter correspondente e na execução sequencial de todas as suas células.

### Passo a passo para rodar no Jupyter

1. Inicie o Jupyter:
```bash
# Docker
docker compose up quantumnet-notebook

# Local
jupyter notebook
```
2. Abra o notebook ``examples/demo_nepr.ipynb.``

3. Execute todas as células em sequência (Run All).

4. Aguarde o término completo das execuções.

5. Verifique as saídas geradas no próprio notebook.

Tempo esperado: 1 a 10 minutos, dependendo da topologia e da quantidade de operações executadas.
Recursos esperados: aproximadamente 1 GB de RAM e baixo uso de disco.
Resultado esperado: execução bem-sucedida de múltiplas requisições NEPR entre dois nós da topologia, com geração de métricas de sucesso/falha, fidelidade média dos pares distribuídos, eventos de aplicação registrados em CSV e visualizações que evidenciam efeitos da infraestrutura subjacente, como decoerência e regeneração de qubits.

## Reivindicação #2 — Reprodução do agendamento de purificação na camada de enlace

Esta reivindicação demonstra que o artefato permite reproduzir um cenário de purificação em canal ruidoso, evidenciando o comportamento do agendamento híbrido e seu efeito sobre a continuidade do processo e a fidelidade final do enlace.

Notebook correspondente: ``examples/demo_purification.ipynb.``

Considerando o ambiente do projeto previamente configurado, seja via Docker conforme descrito na seção de Instalação ou por instalação local das dependências, a reprodução deste caso de uso consiste na abertura do notebook Jupyter correspondente e na execução sequencial de todas as suas células.

### Passo a passo para rodar no Jupyter

1. Inicie o Jupyter:
```
# Docker
docker compose up quantumnet-notebook

# Local
jupyter notebook
```
2. Abra o notebook ``examples/demo_purification.ipynb.``

3. Execute todas as células em sequência (Run All).

4. Aguarde o término completo das execuções.

5. Analise a saída textual final produzida pelo notebook.

Tempo esperado: 5 a 30 minutos, conforme o tamanho do cenário e o número de repetições.
Recursos esperados: 1 a 2 GB de RAM e baixo uso de disco para logs e arquivos auxiliares.
Resultado esperado: saída textual detalhando o processo de purificação, incluindo provisionamento inicial, falhas probabilísticas, tentativas de recuperação e conclusão bem-sucedida do agendamento híbrido, com fidelidade final compatível com o cenário configurado.

## Reivindicação #3 — Reprodução do cenário de ataque a repetidores quânticos

Esta reivindicação demonstra que o artefato permite reproduzir um cenário de ataque do tipo black hole repeater, evidenciando o impacto de um repetidor malicioso sobre a taxa de sucesso da comunicação quântica.

Notebook correspondente: ``examples/demo_attack.ipynb.``

Considerando o ambiente do projeto previamente configurado, seja via Docker conforme descrito na seção de Instalação ou por instalação local das dependências, a reprodução deste caso de uso consiste na abertura do notebook Jupyter correspondente e na execução sequencial de todas as suas células.

### Passo a passo para rodar no Jupyter

1. Inicie o Jupyter:
```
# Docker
docker compose up quantumnet-notebook

# Local
jupyter notebook
```
2. Abra o notebook ``examples/demo_attack.ipynb.``

3. Execute todas as células em sequência (Run All).

4. Aguarde o término completo das execuções.

5. Verifique os gráficos e métricas gerados ao final da execução.

Tempo esperado: 5 a 20 minutos, conforme os parâmetros do cenário.
Recursos esperados: 1 a 2 GB de RAM e baixo uso de disco para saídas do experimento.
Resultado esperado: geração de visualizações comparativas mostrando a diferença entre a rede íntegra e a rede com repetidor malicioso, bem como a degradação da taxa de sucesso à medida que aumenta a intensidade do ataque.


# LICENSE

Este projeto está licenciado sob os termos descritos no arquivo `LICENSE` do repositório.
