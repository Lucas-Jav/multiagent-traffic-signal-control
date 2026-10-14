# Controle Semafórico Multiagente (Multi-Agent Traffic Signal Control)

[![CI](https://github.com/Lucas-Jav/multiagent-traffic-signal-control/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Lucas-Jav/multiagent-traffic-signal-control/actions/workflows/ci.yml)

> **Nota de status (histórico preservado).** Este README descreve principalmente o MVP1. O resultado final do experimento piloto Pilot V2 é: `RESULT_INTERPRETATION=MIXED`, `RESULT_CONFIDENCE=MEDIUM`, `C1_GENERAL_SUPERIORITY_CLAIMED=NO`, `C1_SCENARIO_SPECIFIC_BENEFIT=S4`, `READY_FOR_TCC_USE=YES`. O Pilot V2 não provou superioridade geral do C1 sobre o B2: o C1 se beneficiou claramente no cenário saturado S4, piorou em S1 e S3 e, em S2, apresentou um trade-off (redução de atraso/fila, porém redução de vazão (throughput) e da razão de conclusão). Política do S4: `ALLOW_AND_MEASURE` (teleports devem ser reportados, mas não bloqueiam a validade do S4). Qualquer menção histórica de que o S3 bloquearia o piloto foi superada pelo gate composto.

> **Documentos canônicos (a documentação metodológica vigente).** Este README é em grande parte
> **HISTÓRICO (MVP1)**. Em caso de divergência, valem os documentos abaixo:
> `docs/methodology/baselines.md` (controladores; B0 histórico = `STATIC_DEFAULT`; B0 final = `B0_FIXED_CALIBRATED`, ver `docs/methodology/fixed-time-calibration.md`),
> `docs/methodology/metrics.md` (métricas canônicas e aliases),
> `docs/methodology/intersection-glossary.md` (A1-A9 lógicos x IDs SUMO; A5 = `B1`),
> `docs/methodology/scenario-validity-gates.md` (gates S1-S4, gate composto do S3, post-hoc),
> `docs/methodology/reference-route.md` (rota de referência W->E por A5),
> `docs/methodology/tcc-scope-alignment.md` (escopo: controle **reativo**, sem ML/previsão),
> `docs/experiments.md` (S5 canônico: perda 0/20/50/100%, atraso 0; **não executado**),
> `docs/evidencias/pilot-v2/` (evidências versionadas do Pilot V2),
> `docs/advisor-feedback-checklist.md`.

## 1. Visão Geral do Projeto

O MVP1 implementa um ambiente reproduzível para controle semafórico multiagente em uma rede sintética 3x3 no Eclipse SUMO. O projeto executa simulações headless via TraCI, controladores locais e cooperativos, experimentos pequenos declarados em YAML e coleta de artifacts por run.

O SUMO-GUI continua sendo usado localmente para debugging e demonstração com `--gui`. O container Docker do MVP1 é headless e não executa GUI.

## 2. Pergunta Científica

Em uma rede urbana simulada, a troca local de informações entre controladores semafóricos descentralizados melhora o desempenho da rede em comparação com estratégias sem cooperação, e qual é o custo e a robustez dessa comunicação?

O MVP1 executa a infraestrutura experimental para investigar essa pergunta. Ele não afirma uma resposta.

## 3. Arquitetura

Fluxo principal de simulação:

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

Fluxo de cooperação local:

```text
Agent
 ↓
CompactNeighborMessage
 ↓
MessageBus
 ↓
Neighbor Agent
```

A execução usa o mesmo `TraCISimulationRunner`, os mesmos controladores, o mesmo `MessageBus` e o mesmo `ExperimentRunner` em ambiente local e no container.

## 4. Requisitos

- Python 3.12.
- `uv`.
- Eclipse SUMO 1.27.1 para execução local.
- Docker e Docker Compose para execução containerizada.

As dependências Python são controladas por `pyproject.toml` e `uv.lock`. `traci` e `sumolib` são dependências explícitas do ambiente Python.

## 5. Configuração do Projeto

Quickstart local:

```powershell
uv sync --frozen
uv run python scripts/check_sumo.py
uv run traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B0_FIXED --seed 42 --max-steps 300
uv run traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B0_FIXED --seed 42 --gui --step-delay-ms 40 --max-steps 900
uv run traffic-agents experiment run --config experiments/configs/mvp1.yaml
```

`scripts/check_sumo.py` valida que o SUMO local encontrado é a versão esperada pelo projeto.

Alternativa equivalente para GUI usando o script diretamente no Windows, depois de ativar a `.venv`:

```powershell
.venv\Scripts\activate
python scripts\run_simulation.py --scenario scenarios\grid_3x3\scenario.yaml --gui --step-delay-ms 40 --max-steps 900
```

## 6. Desenvolvimento Local

Validar SUMO:

```powershell
uv run python scripts/check_sumo.py
```

Gerar novamente a rede 3x3 versionada:

```powershell
uv run python scripts/generate_grid.py
```

Gerar novamente as rotas do cenário:

```powershell
uv run python scripts/generate_routes.py scenarios/grid_3x3/scenario.yaml
```

Validar o YAML do cenário:

```powershell
uv run python scripts/validate_scenario.py scenarios/grid_3x3/scenario.yaml
```

Executar o entrypoint do pacote:

```powershell
uv run traffic-agents
```

## 7. Docker

O container usa a imagem base versionada `ghcr.io/eclipse-sumo/sumo:v1_27_1`, com SUMO 1.27.1. A imagem instala Python 3.12 via `uv`, usa `uv.lock` com `--frozen`, roda como usuário non-root e grava artifacts em `/app/artifacts`.

Build:

```powershell
docker compose build
```

Verificar SUMO dentro do container:

```powershell
docker compose run --rm simulator sumo --version
```

Executar simulação headless:

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

O SUMO-GUI não é necessário para experimentos headless. Para visualização, use a execução local com `--gui`.

## 8. Modelo de Tráfego

O modelo de tráfego do MVP1 representa as interseções `A1` a `A9`. Cada interseção possui movimentos derivados da rede SUMO, incluindo movimentos `straight`, `left` e `right`.

O projeto constrói e valida uma matriz de conflitos de movimentos a partir da rede. Movimentos conflitantes nunca podem receber verde simultaneamente. Movimentos compatíveis podem coexistir na mesma fase.

O plano de fases inclui fases seguras, tempo mínimo de verde, amarelo e all-red/clearance. O `PhaseSafetyManager` aplica restrições de segurança antes de enviar a fase ao SUMO. Veículos que já estão comprometidos com a junction podem concluir a travessia conforme a dinâmica do SUMO.

Os turning ratios são parâmetros do cenário e controlam de fato as rotas geradas (caminhada
sorteada por seed, determinística, em cada junção semaforizada). Nos cenários 3x3
versionados (S1-S4), os valores são os do protocolo aprovado:

- `straight: 0.70`
- `left: 0.15`
- `right: 0.15`

Os cenários são gerados por `uv run python scripts/generate_scenarios.py` (ver
`docs/scenarios.md`). As métricas finais são calculadas por um pipeline canônico
(`run_metrics.json` por run e `combined_metrics.parquet` por experimento; ver
`docs/methodology/metrics.md`).

## 9. Cenário 3x3

O cenário principal está em `scenarios/grid_3x3/scenario.yaml`.

Arquivos versionados do cenário:

- `network.net.xml`
- `routes_s1_seed_42.rou.xml`
- `metadata.json`
- `viewsettings.xml`

Configuração atual:

- `scenario_id: grid_3x3`
- duração de 3600 segundos
- warmup de 300 segundos
- `step_length: 1.0`
- `seed: 42`
- perfil de demanda `S1_BALANCED`
- nível de demanda `MEDIUM`

Traffic topology é a topologia física da rede SUMO: lanes, edges, junctions, movimentos e conflitos de movimentos. Communication topology é a topologia lógica de troca de mensagens entre agentes vizinhos. Elas são conceitos separados.

## 10. Controladores

`B0_FIXED`: baseline fixed-time (tempo fixo). Não aplica decisão adaptativa e preserva o plano semafórico definido no SUMO (ciclo de 98 s, verdes 18/20/20/20 s, amarelo 3 s, all-red 2 s). Este é o baseline **histórico** (`B0_FIXED_STATIC`, Pilot V2): não é Webster nem foi calibrado a partir da demanda (`B0_FIXED_METHOD = STATIC_DEFAULT`). O baseline final é o `B0_FIXED_CALIBRATED` (ciclo de 84 s, `EMPIRICAL_FIXED_TIME`).

`B1_LOCAL_ADAPTIVE`: controlador local adaptativo. Usa estado local da interseção e não usa comunicação.

`B2_LOCAL_PRESSURE`: controlador local por pressão. Usa medidas locais de filas/pressão e não usa comunicação.

`C1_COOPERATIVE_COMPACT`: controlador cooperativo compacto. Conceitualmente é:

```text
B2
+
informacao compacta dos vizinhos
```

`C2_COOPERATIVE_EXPANDED`: controlador cooperativo expandido. Ele reutiliza o mesmo núcleo cooperativo do `C1_COOPERATIVE_COMPACT`, incluindo cálculo de pressão, ajuste cooperativo, segurança de fase e fallback local. A diferença experimental principal é a informação disponível: C1 troca `CompactNeighborMessage`, enquanto C2 troca `ExpandedNeighborMessage`.

Quando mensagens de vizinhos não estão disponíveis, o comportamento volta para a decisão local.

## 11. Comunicação Multiagente

A comunicação do MVP1 usa `CompactNeighborMessage` e `MessageBus`.

`CompactNeighborMessage` carrega informação compacta sobre o estado local relevante para um vizinho. `ExpandedNeighborMessage` carrega os campos compactos e informação destination-specific adicional, como filas por movimento de saída relevante, ocupação por conexão downstream, taxa estimada de chegada por movimento relevante, resumo direcional de demanda, phase group e phase elapsed. Ela não inclui lista de veículos, estado global, dados de agentes terceiros nem informação local sem relação com o destino. `MessageBus` entrega mensagens entre agentes respeitando a communication topology configurada para a rede 3x3.

A communication topology define quais agentes podem trocar mensagens. Ela não altera a traffic topology e não cria novas conexões físicas na rede SUMO.

O atraso de comunicação é configurado no cenário:

```yaml
communication:
  delay_steps: 0
  drop_probability: 0.0
  rng_seed: null
  max_message_age_steps: 1
```

O tempo de entrega usa apenas simulation step. O `MessageBus` não usa relógio de parede para entrega científica de mensagens. Uma mensagem criada no step `t` é primeiro contabilizada como sent. A decisão de perda acontece imediatamente no `publish(...)`, usando um RNG dedicado do canal de comunicação. Se a mensagem for perdida, ela nunca entra na agenda de entrega nem chega ao inbox. Se não for perdida, ela é agendada para `t + delay_steps`. Em cada simulation step, o controlador cooperativo publica as mensagens locais, chama `receive(...)` e só depois decide a fase; portanto, uma mensagem agendada para o step `s` fica disponível antes da decisão tomada no próprio step `s`. Com `delay_steps: 0` e `drop_probability: 0.0`, isso preserva o comportamento atual: uma mensagem criada no step corrente pode ser usada na decisão do mesmo step.

`rng_seed: null` faz a seed efetiva ser derivada deterministicamente de `simulation.seed`, `communication.delay_steps` e `communication.drop_probability`. Um inteiro em `rng_seed` substitui essa derivação. A seed efetiva do canal é registrada no manifest da run.

Cada mensagem registra `created_step`, `scheduled_delivery_step` e `delivered_step`. O bus mantém mensagens internamente por delivery step e preserva ordenação determinística por `delivery_step`, `created_step`, `sequence`, `source` e `destination`. As métricas de transporte incluem `messages_sent`, `messages_delivered`, `messages_dropped`, `observed_drop_rate`, `message_delay_steps`, `average_message_delay` e `max_message_delay`.

A idade científica da informação é `current_simulation_step - created_step`, medida pelo `C1_COOPERATIVE_COMPACT` quando a mensagem chega ao agente. Mensagens com `age <= max_message_age_steps` são fresh; mensagens com `age > max_message_age_steps` são stale. A fronteira é inclusiva: `age == max_message_age_steps` ainda é fresh. Mensagens stale são ignoradas pelo ajuste cooperativo, sem exception, e o controlador segue com a informação local/B2 quando não houver mensagem cooperativa útil. As métricas de utilidade da informação incluem `messages_fresh`, `messages_stale`, `mean_message_age_steps` e `max_message_age_steps` (nomes canônicos; `average_message_age` e `max_observed_message_age` são nomes internos/históricos, ver `docs/methodology/metrics.md`). O registro preparado para agent tracing guarda `message_age_steps`, `used` e `reason=STALE` quando uma mensagem entregue é descartada por idade.

## 12. Executando uma Simulação

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

## 13. Executando um Experimento

O experimento MVP1 está em `experiments/configs/mvp1.yaml`. Ele executa os controladores `B0_FIXED`, `B1_LOCAL_ADAPTIVE`, `B2_LOCAL_PRESSURE`, `C1_COOPERATIVE_COMPACT` e `C2_COOPERATIVE_EXPANDED` com seed 42 e `max_steps: 300`.

```powershell
uv run traffic-agents experiment run --config experiments/configs/mvp1.yaml
```

Esse comando não executa campanhas científicas longas nem múltiplas seeds.

## 14. Artifacts

Runs individuais gravam artifacts em:

```text
artifacts/runs/<run_id>/
```

Arquivos atualmente gerados por run:

- `manifest.json` (`metrics_finalized: true` somente após a finalização canônica de métricas)
- `run_metrics.json`: métricas finais do run (populações, atraso de inserção, filas por escopo, throughput, métricas por cenário)
- `lane_telemetry.parquet` e `junction_telemetry.parquet`: telemetria canônica (uma linha por faixa única e passo; produzida pelo runner para todos os controladores, inclusive `B0_FIXED`)
- `performance.json`, `sumo_traffic_metrics.json` e `sumo/tripinfo.xml`/`sumo/statistics.xml`
- `intersection_trace.csv`: apenas para depuração, quando `tracing.intersection_trace: true` (não usado por métricas científicas)

Experimentos gravam:

```text
artifacts/experiments/<experiment_id>/manifest.json
artifacts/experiments/<experiment_id>/combined_metrics.parquet
artifacts/experiments/<experiment_id>/runs/<batch_id>/<run_id>/manifest.json
```

`combined_metrics.parquet` é gerado automaticamente ao fim do experimento (ou por
`traffic-agents experiment aggregate <pasta>`) a partir dos `run_metrics.json` finalizados.

Os arquivos abaixo não são produzidos pelo código MVP1 atual:

- `config.snapshot.yaml`
- `results.parquet`
- `summary.json`

## 15. Reprodutibilidade

O `manifest.json` registra os principais dados de reprodutibilidade da run:

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
- git SHA quando disponível

No container, o git SHA só fica disponível se o contexto de execução incluir metadados `.git`.

## 16. Testes

Quality gates locais:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
```

Se o Windows bloquear o diretório temporário padrão do pytest, use um `basetemp` dentro do workspace:

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

Auditoria de dependências usada no CI:

```powershell
uv run pip-audit --skip-editable --cache-dir .pip-audit-cache
```

O CI principal valida qualidade, testes não-SUMO, auditoria Python e build Docker. Ele não executa campanhas experimentais pesadas.

## 17. Limitações Atuais

- A rede é sintética.
- Não há sensores reais.
- Não há hardware semafórico real.
- Não há MARL no MVP1.
- Resultados não generalizam automaticamente para cidades reais.
- Turning ratios são parâmetros de cenário.
- Sim-to-real permanece fora do MVP.
- O container MVP1 é headless e não executa SUMO-GUI.
- `config.snapshot.yaml`, `results.parquet` e `summary.json` ainda não são artifacts gerados pelo código atual.
