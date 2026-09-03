# Multi-Agent Traffic Signal Control

[![CI](https://github.com/Lucas-Jav/multiagent-traffic-signal-control/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Lucas-Jav/multiagent-traffic-signal-control/actions/workflows/ci.yml)

## 1. Project Overview

MVP1 implementa um ambiente reproduzivel para controle semaforico multiagente em uma rede sintetica 3x3 no Eclipse SUMO. O projeto executa simulacoes headless via TraCI, controladores locais e cooperativos, experimentos pequenos declarados em YAML e coleta de artifacts por run.

O SUMO-GUI continua sendo usado localmente para debugging e demonstracao com `--gui`. O container Docker do MVP1 e headless e nao executa GUI.

## 2. Scientific Question

Em uma rede urbana simulada, a troca local de informações entre controladores semafóricos descentralizados melhora o desempenho da rede em comparação com estratégias sem cooperação, e qual é o custo e a robustez dessa comunicação?

O MVP1 executa a infraestrutura experimental para investigar essa pergunta. Ele nao afirma uma resposta.

## 3. Architecture

Fluxo principal de simulacao:

```text
SUMO
 ↓
TraCI
 ↓
SensorProvider
 ↓
IntersectionState
 ↓
TrafficAgent
 ↓
Controller
 ↓
PhaseSafetyManager
 ↓
SUMO
```

Fluxo de cooperacao local:

```text
Agent
 ↓
CompactNeighborMessage
 ↓
MessageBus
 ↓
Neighbor Agent
```

A execucao usa o mesmo `TraCISimulationRunner`, os mesmos controladores, o mesmo `MessageBus` e o mesmo `ExperimentRunner` em ambiente local e no container.

## 4. Requirements

- Python 3.12.
- `uv`.
- Eclipse SUMO 1.27.1 para execucao local.
- Docker e Docker Compose para execucao containerizada.

As dependencias Python sao controladas por `pyproject.toml` e `uv.lock`. `traci` e `sumolib` sao dependencias explicitas do ambiente Python.

## 5. Project Setup

Quickstart local:

```powershell
uv sync --frozen
uv run python scripts/check_sumo.py
uv run traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B0_FIXED --seed 42 --max-steps 300
uv run traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B0_FIXED --seed 42 --gui --step-delay-ms 40 --max-steps 900
uv run traffic-agents experiment run --config experiments/configs/mvp1.yaml
```

`scripts/check_sumo.py` valida que o SUMO local encontrado e a versao esperada pelo projeto.

Alternativa equivalente para GUI usando o script diretamente no Windows, depois de ativar a `.venv`:

```powershell
.venv\Scripts\activate
python scripts\run_simulation.py --scenario scenarios\grid_3x3\scenario.yaml --gui --step-delay-ms 40 --max-steps 900
```

## 6. Local Development

Validar SUMO:

```powershell
uv run python scripts/check_sumo.py
```

Gerar novamente a rede 3x3 versionada:

```powershell
uv run python scripts/generate_grid.py
```

Gerar novamente as rotas do cenario:

```powershell
uv run python scripts/generate_routes.py scenarios/grid_3x3/scenario.yaml
```

Validar o YAML do cenario:

```powershell
uv run python scripts/validate_scenario.py scenarios/grid_3x3/scenario.yaml
```

Executar o entrypoint do pacote:

```powershell
uv run traffic-agents
```

## 7. Docker

O container usa a imagem base versionada `ghcr.io/eclipse-sumo/sumo:v1_27_1`, com SUMO 1.27.1. A imagem instala Python 3.12 via `uv`, usa `uv.lock` com `--frozen`, roda como usuario non-root e grava artifacts em `/app/artifacts`.

Build:

```powershell
docker compose build
```

Verificar SUMO dentro do container:

```powershell
docker compose run --rm simulator sumo --version
```

Executar simulacao headless:

```powershell
docker compose run --rm simulator traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B0_FIXED --seed 42 --max-steps 300
```

Executar experimento MVP1:

```powershell
docker compose run --rm simulator traffic-agents experiment run --config experiments/configs/mvp1.yaml
```

Volumes declarados no Compose:

- `./scenarios:/app/scenarios`
- `./experiments:/app/experiments`
- `./artifacts:/app/artifacts`
- `./docs:/app/docs:ro`

SUMO-GUI nao e necessario para experimentos headless. Para visualizacao, use a execucao local com `--gui`.

## 8. Traffic Model

O modelo de trafego do MVP1 representa as intersecoes `A1` a `A9`. Cada intersecao possui movimentos derivados da rede SUMO, incluindo movimentos `straight`, `left` e `right`.

O projeto constroi e valida uma matriz de conflitos de movimentos a partir da rede. Movimentos conflitantes nunca podem receber verde simultaneamente. Movimentos compativeis podem coexistir na mesma fase.

O plano de fases inclui fases seguras, tempo minimo de verde, amarelo e all-red/clearance. O `PhaseSafetyManager` aplica restricoes de seguranca antes de enviar a fase ao SUMO. Veiculos que ja estao comprometidos com a junction podem concluir a travessia conforme a dinamica do SUMO.

Os turning ratios sao parametros do cenario. No cenario 3x3 versionado, os valores sao:

- `straight: 0.60`
- `left: 0.20`
- `right: 0.20`

## 9. 3x3 Scenario

O cenario principal esta em `scenarios/grid_3x3/scenario.yaml`.

Arquivos versionados do cenario:

- `network.net.xml`
- `routes_s1_seed_42.rou.xml`
- `metadata.json`
- `viewsettings.xml`

Configuracao atual:

- `scenario_id: grid_3x3`
- duracao de 3600 segundos
- warmup de 300 segundos
- `step_length: 1.0`
- `seed: 42`
- perfil de demanda `S1_BALANCED`
- nivel de demanda `MEDIUM`

Traffic topology e a topologia fisica da rede SUMO: lanes, edges, junctions, movimentos e conflitos de movimentos. Communication topology e a topologia logica de troca de mensagens entre agentes vizinhos. Elas sao conceitos separados.

## 10. Controllers

`B0_FIXED`: baseline fixed-time. Nao aplica decisao adaptativa e preserva o plano semaforico definido no SUMO.

`B1_LOCAL_ADAPTIVE`: controlador local adaptativo. Usa estado local da intersecao e nao usa comunicacao.

`B2_LOCAL_PRESSURE`: controlador local por pressao. Usa medidas locais de filas/pressao e nao usa comunicacao.

`C1_COOPERATIVE_COMPACT`: controlador cooperativo compacto. Conceitualmente e:

```text
B2
+
informacao compacta dos vizinhos
```

Quando mensagens de vizinhos nao estao disponiveis, o comportamento volta para a decisao local.

## 11. Multi-Agent Communication

A comunicacao do MVP1 usa `CompactNeighborMessage` e `MessageBus`.

`CompactNeighborMessage` carrega informacao compacta sobre o estado local relevante para um vizinho. `MessageBus` entrega mensagens entre agentes respeitando a communication topology configurada para a rede 3x3.

A communication topology define quais agentes podem trocar mensagens. Ela nao altera a traffic topology e nao cria novas conexoes fisicas na rede SUMO.

O atraso de comunicacao e configurado no cenario:

```yaml
communication:
  delay_steps: 0
  drop_probability: 0.0
  rng_seed: null
  max_message_age_steps: 1
```

O tempo de entrega usa apenas simulation step. O `MessageBus` nao usa relogio de parede para entrega cientifica de mensagens. Uma mensagem criada no step `t` e primeiro contabilizada como sent. A decisao de perda acontece imediatamente no `publish(...)`, usando um RNG dedicado do canal de comunicacao. Se a mensagem for perdida, ela nunca entra na agenda de entrega nem chega ao inbox. Se nao for perdida, ela e agendada para `t + delay_steps`. Em cada simulation step, o controlador cooperativo publica as mensagens locais, chama `receive(...)` e so depois decide a fase; portanto, uma mensagem agendada para o step `s` fica disponivel antes da decisao tomada no proprio step `s`. Com `delay_steps: 0` e `drop_probability: 0.0`, isso preserva o comportamento atual: uma mensagem criada no step corrente pode ser usada na decisao do mesmo step.

`rng_seed: null` faz a seed efetiva ser derivada deterministicamente de `simulation.seed`, `communication.delay_steps` e `communication.drop_probability`. Um inteiro em `rng_seed` substitui essa derivacao. A seed efetiva do canal e registrada no manifest da run.

Cada mensagem registra `created_step`, `scheduled_delivery_step` e `delivered_step`. O bus mantem mensagens internamente por delivery step e preserva ordenacao deterministica por `delivery_step`, `created_step`, `sequence`, `source` e `destination`. As metricas de transporte incluem `messages_sent`, `messages_delivered`, `messages_dropped`, `observed_drop_rate`, `message_delay_steps`, `average_message_delay` e `max_message_delay`.

A idade cientifica da informacao e `current_simulation_step - created_step`, medida pelo `C1_COOPERATIVE_COMPACT` quando a mensagem chega ao agente. Mensagens com `age <= max_message_age_steps` sao fresh; mensagens com `age > max_message_age_steps` sao stale. A fronteira e inclusiva: `age == max_message_age_steps` ainda e fresh. Mensagens stale sao ignoradas pelo ajuste cooperativo, sem exception, e o controlador segue com a informacao local/B2 quando nao houver mensagem cooperativa util. As metricas de utilidade da informacao incluem `messages_fresh`, `messages_stale`, `average_message_age` e `max_observed_message_age`. O registro preparado para agent tracing guarda `message_age_steps`, `used` e `reason=STALE` quando uma mensagem entregue e descartada por idade.

## 12. Running a Simulation

Headless:

```powershell
uv run traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B0_FIXED --seed 42 --max-steps 300
```

Com SUMO-GUI local:

```powershell
uv run traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B0_FIXED --seed 42 --gui --step-delay-ms 40 --max-steps 900
```

Forma equivalente pelo script, com a `.venv` ativa:

```powershell
python scripts\run_simulation.py --scenario scenarios\grid_3x3\scenario.yaml --gui --step-delay-ms 40 --max-steps 900
```

Controlador alternativo:

```powershell
uv run traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B2_LOCAL_PRESSURE --seed 42 --max-steps 300
```

## 13. Running an Experiment

O experimento MVP1 esta em `experiments/configs/mvp1.yaml`. Ele executa os controladores `B0_FIXED`, `B1_LOCAL_ADAPTIVE`, `B2_LOCAL_PRESSURE` e `C1_COOPERATIVE_COMPACT` com seed 42 e `max_steps: 300`.

```powershell
uv run traffic-agents experiment run --config experiments/configs/mvp1.yaml
```

Esse comando nao executa campanhas cientificas longas nem multiplas seeds.

## 14. Artifacts

Runs individuais gravam artifacts em:

```text
artifacts/runs/<run_id>/
```

Arquivos atualmente gerados por run:

- `manifest.json`
- `intersection_trace.csv`, quando o controlador emite telemetria por intersecao

Experimentos gravam:

```text
artifacts/experiments/<experiment_id>/manifest.json
artifacts/experiments/<experiment_id>/runs/<batch_id>/<run_id>/manifest.json
```

Os arquivos abaixo nao sao produzidos pelo codigo MVP1 atual:

- `config.snapshot.yaml`
- `results.parquet`
- `summary.json`

## 15. Reproducibility

O `manifest.json` registra os principais dados de reproducibilidade da run:

- seed
- network hash
- route hash
- scenario hash
- phase plan version
- phase plan hash
- movement model version
- turning ratio config
- controller version
- SUMO version
- Python version
- communication topology hash
- git SHA quando disponivel

No container, o git SHA so fica disponivel se o contexto de execucao incluir metadados `.git`.

## 16. Testing

Quality gates locais:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
```

Se o Windows bloquear o diretorio temporario padrao do pytest, use um `basetemp` dentro do workspace:

```powershell
uv run pytest -q --basetemp artifacts/pytest-tmp -p no:cacheprovider
```

Executar somente testes sem SUMO:

```powershell
uv run pytest -q -m "not sumo"
```

Executar testes marcados como SUMO:

```powershell
uv run pytest -q -m sumo
```

Auditoria de dependencias usada no CI:

```powershell
uv run pip-audit --skip-editable --cache-dir .pip-audit-cache
```

O CI principal valida qualidade, testes nao-SUMO, auditoria Python e build Docker. Ele nao executa campanhas experimentais pesadas.

## 17. Current Limitations

- A rede e sintetica.
- Nao ha sensores reais.
- Nao ha hardware semaforico real.
- Nao ha MARL no MVP1.
- Resultados nao generalizam automaticamente para cidades reais.
- Turning ratios sao parametros de cenario.
- Sim-to-real permanece fora do MVP.
- O container MVP1 e headless e nao executa SUMO-GUI.
- `config.snapshot.yaml`, `results.parquet` e `summary.json` ainda nao sao artifacts gerados pelo codigo atual.
