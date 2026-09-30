# Relatório de Prontidão da V1

## Status Geral

V1_READY = YES

PASS_COUNT = 28  
PARTIAL_COUNT = 6  
FAIL_COUNT = 0  
CRITICAL_BLOCKERS = 0

Nenhum bloqueio CRITICAL ou HIGH foi encontrado. Os itens PARTIAL restantes são limitações de documentação/completude de artifacts, e não bloqueiam a validade experimental da V1.

> **Nota de status (atualização posterior, histórico preservado).** Este relatório reflete a inspeção de 2026-09-29, anterior à conclusão do experimento piloto Pilot V2. O resultado final do Pilot V2 é: `RESULT_INTERPRETATION=MIXED`, `RESULT_CONFIDENCE=MEDIUM`, `C1_GENERAL_SUPERIORITY_CLAIMED=NO`, `C1_SCENARIO_SPECIFIC_BENEFIT=S4`, `READY_FOR_TCC_USE=YES`. O Pilot V2 não provou superioridade geral do C1 sobre o B2: o C1 se beneficiou claramente no cenário saturado S4; o C1 piorou em S1 e S3; em S2 houve um trade-off (redução de atraso/fila, porém redução de vazão (throughput) e da razão de conclusão). Nada neste relatório deve ser lido como afirmação de superioridade geral do C1. Política do S4: `ALLOW_AND_MEASURE` (teleports devem ser reportados, mas não bloqueiam a validade do S4). Qualquer menção antiga de que o S3 bloquearia o piloto foi superada pelo gate composto.

## Data da Inspeção

2026-09-29

## Estado do Repositório

`git status --short` não retornou saída: árvore de trabalho limpa.

## Ambiente

PASS. Evidências:
- `pyproject.toml`: `requires-python = ">=3.12,<3.13"`, `traci==1.27.1`, `sumolib==1.27.1`.
- `uv.lock` está versionado.
- `Dockerfile`: imagem SUMO `ghcr.io/eclipse-sumo/sumo:v1_27_1`, Python `3.12.11`, `uv sync --frozen`, importa `traci`/`sumolib`.
- `compose.yaml`: sem modo privilegiado e sem montagem do socket do Docker.
- `.github/workflows/ci.yml`: Python 3.12, sincronização do lockfile, Ruff, format, mypy, pytest, build Docker, smoke/versão do SUMO.

## Arquitetura

PASS. A atuação é centralizada em:

`Controller -> PhaseSafetyManager -> PhaseCommand -> TrafficLightActuator -> TraCI`

Busca por `setPhase` / `setRedYellowGreenState`:
- `src/traffic_agents/traffic_light_actuator.py`: única chamada real de `setPhase` do TraCI.
- Somente em testes: `tests/test_fixed_time_controller.py`, `tests/test_local_adaptive_controller.py`, `tests/test_cooperative_compact_controller.py`, `tests/test_traffic_model.py`.
- Nenhum controlador chama diretamente a atuação bruta do TraCI.

## Modelo de Tráfego

PASS.
- Rede 3x3: `scenarios/grid_3x3/network.net.xml`.
- Mapeamento A1..A9: `scenarios/grid_3x3/metadata.json`, carregado por `traffic_model.py`.
- Modelo de movimentos e plano de fases explícitos em `src/traffic_agents/traffic_model.py`.
- Demanda de movimentos straight/left/right documentada em `docs/traffic-model.md`.
- Matriz de conflitos e validação de fases válidas cobertas por `tests/test_traffic_model.py` e `tests/test_phase_safety.py`.

O comando de validação dos artifacts de rota confirmou S1-S4:
- S1: seed 42, hashes OK, 12 janelas de fluxo.
- S2: seed 42, hashes OK, 12 janelas de fluxo.
- S3: seed 42, hashes OK, 24 janelas de fluxo.
- S4: seed 42, hashes OK, 18 janelas de fluxo.

## Controladores

PASS.
- B0 fixed-time (tempo fixo): `src/traffic_agents/controllers/fixed_time.py`.
- B1 adaptativo local: `src/traffic_agents/controllers/local_adaptive.py`.
- B2 pressão local: `src/traffic_agents/controllers/local_pressure.py`.
- C1/C2 cooperativos: `src/traffic_agents/controllers/cooperative_compact.py`.
- Fórmulas e parâmetros: `docs/methodology/controllers.md`.
- O B2 usa apenas estado local e não consome `NeighborMessage`.
- C1/C2 reutilizam o núcleo de pressão local do B2 e voltam ao comportamento local quando não há mensagens válidas disponíveis.
- Os controladores respeitam o `PhaseSafetyManager`.

## Comunicação Multiagente

PASS.
- Topologia implementada em `src/traffic_agents/communication/topology.py`.
- Topologia esperada verificada:
  A1=A2,A4; A2=A1,A3,A5; A3=A2,A6; A4=A1,A5,A7; A5=A2,A4,A6,A8; A6=A3,A5,A9; A7=A4,A8; A8=A5,A7,A9; A9=A6,A8.
- Message bus: `src/traffic_agents/communication/message_bus.py`.
- Entrega imediata, atraso, perda (drop), detecção de mensagens stale, ordenação determinística e RNG com seed cobertos por `tests/test_message_bus.py`.
- A topologia de comunicação é separada da topologia de tráfego, conforme o `README.md`.

## Reprodutibilidade dos Experimentos

PASS com limitação LOW indicada abaixo.
- A validação de rotas rejeita seed/hash/cenário/metadados divergentes em `src/traffic_agents/experiments/route_artifacts.py`.
- Mecanismo de freeze: `src/traffic_agents/experiments/freeze.py`.
- Invariantes de execução: `src/traffic_agents/experiments/run_invariants.py`.
- Status, resume e comportamento em caso de falha do experiment runner: `src/traffic_agents/experiments/runner.py`, `tests/test_experiment_runner.py`.
- Último mini experimento inspecionado: `artifacts/experiments/mvp1`.
- `mvp1`: 5 runs, 5 concluídas, 0 falhas, 0 pendentes, `run_status.jsonl` com 10 registros incrementais.

Os invariantes científicos no último batch do `mvp1` foram idênticos entre B0/B1/B2/C1/C2:
- `network_sha256`: 1 valor único.
- `route_sha256`: 1 valor único.
- `phase_plan_sha256`: 1 valor único.
- `movement_model_sha256`: 1 valor único.
- `turning_config_sha256`: 1 valor único.
- `communication_topology_sha256`: 1 valor único.
- `seed`: 1 valor único.
- `scenario_sha256`: 5 valores únicos, limitação semântica LOW conhecida.

## Métricas

PASS/PARTIAL.
- Existem métricas de tripinfo do SUMO: tempo de espera, perda de tempo (time loss), tempo de viagem, paradas.
- As definições e a política para veículos não finalizados estão registradas no manifest da run e em `src/traffic_agents/metrics/sumo_trip_metrics.py`.
- O último batch do `mvp1` inclui `sumo_traffic_metrics.json`, `performance.json`, `tripinfo.xml` do SUMO e `statistics.xml`.
- As métricas de comunicação persistem para C1/C2: sent, delivered, dropped, stale, bytes, idade média/máxima.
- Métricas de fila (queue) por movimento existem em `intersection_trace.csv`.

Limitação parcial: o README atual ainda registra que `config.snapshot.yaml`, `results.parquet` e `summary.json` não são gerados pelo código atual.

## Análise Estatística

PASS.
- `analysis/statistics.py` suporta comparações pareadas por invariantes de cenário/seed/rota/rede/fase/turning.
- Inclui contagem, média, mediana, desvio padrão, IQR, diferença absoluta pareada, diferença relativa somente quando válida, IC de 95% por bootstrap pareado e seed/configuração do bootstrap.
- Rejeita pares ausentes, pares duplicados, runs com falha tratadas como zero e invariantes divergentes.
- Testes: `tests/test_analysis_statistics.py`.

## Docker e CI

PASS.
- Reprodutibilidade com Docker: `Dockerfile`, `compose.yaml`.
- O CI valida sincronização de dependências, Ruff, format, mypy, pytest, build Docker, versão/imports do SUMO e smoke run.
- Não exige segredos nem serviços externos pagos.

## Quality Gates

PASS.

Comandos executados:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
uv run traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B0_FIXED --seed 42 --max-steps 5 --no-manifest
```

Resultados:
- Ruff check: `All checks passed!`
- Ruff format check: `87 files already formatted`
- mypy: `Success: no issues found in 40 source files`
- pytest: `279 passed in 10.81s`
- SUMO smoke: PASS, 5 steps, total departed 12, nenhum manifest gravado.

A contagem de testes permanece inalterada em relação à baseline anterior: 279.

## Limitações Conhecidas

LOW:
- `scenario_sha256` ainda tem semântica ampla e pode diferir entre controladores porque campos de controlador/comunicação são incluídos. Isso não invalida a equidade (fairness), pois a comparação científica usa invariantes independentes: `network_sha256`, `route_sha256`, `phase_plan_sha256`, `movement_model_sha256` e `turning_config_sha256`.

PARTIAL:
- O S5 existe como configurações de experimento de degradação de comunicação usando a demanda base do S2, e não como um novo cenário de demanda de tráfego independente.
- Os manifests de run registram a maior parte da proveniência, mas a limpeza da árvore de trabalho é registrada nos manifests de freeze, e não em todo manifest de run.
- Alguns artifacts de conveniência esperados para a campanha final estão documentados como ainda não gerados pelo código atual.
- Figuras e comportamento de GUI/demo foram inspecionados via código-fonte/testes; nenhuma nova validação visual da GUI foi executada durante esta inspeção somente leitura.

## Tabela da Definition of Done

| Requirement | Status | Evidence | Notes |
|---|---:|---|---|
| 1. Environment | PASS | `pyproject.toml`, `uv.lock`, `Dockerfile`, CI, quality commands | Python 3.12 e SUMO/traci/sumolib 1.27.1 fixados |
| 2. Network | PASS | `network.net.xml`, `metadata.json`, manifests | 3x3/A1..A9/hash da rede consistentes |
| 3. Movement Model | PASS | `traffic_model.py`, `docs/traffic-model.md`, tests | Straight/left/right explícitos |
| 4. Phase Safety | PASS | `phase_safety.py`, `traffic_light_actuator.py`, tests | Conflitos/mínimo/amarelo/all-red aplicados |
| 5. Agents | PASS | `traffic_agent.py`, `tests/test_traffic_agent.py` | 9 entidades via registry, IDs de interseção próprios |
| 6. B0 Fixed | PASS | `fixed_time.py`, tests | Tempo fixo, sem lógica adaptativa |
| 7. B1 Local Adaptive | PASS | `local_adaptive.py`, docs/tests | Observações locais, parâmetros versionados |
| 8. B2 Local Pressure | PASS | `local_pressure.py`, docs/tests | Pressão apenas local, sem NeighborMessage |
| 9. Communication Topology | PASS | `topology.py`, README, tests | Mapa de vizinhos esperado e hash |
| 10. Message Bus | PASS | `message_bus.py`, tests | Métricas de delay/drop/stale/seed/ordem |
| 11. C1 Compact | PASS | `compact_message.py`, `cooperative_compact.py`, tests | Mensagens compactas específicas por destino |
| 12. C2 Expanded | PASS | `expanded_message.py`, docs/tests | Sinais adicionais permitidos e métricas de custo |
| 13. Scenarios | PARTIAL | YAML/rotas S1-S4 validados; configs/docs do S5 | S5 é matriz de degradação sobre a base S2 |
| 14. Turning Ratios | PASS | scenario YAML, manifests, route validation | Mesmas proporções por cenário+seed |
| 15. Warmup/Window | PASS | `scenario.py`, `sumo_runner.py`, tests | Warmup excluído das métricas |
| 16. Run Manifest | PARTIAL | `sumo_runner.py`, tests, freeze manifest | Status da árvore de trabalho no freeze, não em todo manifest de run |
| 17. Artifact Integrity | PARTIAL | runner `exist_ok=False`, status tests, artifacts | Sem sobrescrita silenciosa; alguns artifacts de conveniência ausentes |
| 18. Traffic Metrics | PARTIAL | `sumo_trip_metrics.py`, `step_telemetry.py`, artifacts | Métricas finais presentes; alguns campos agregados de conveniência incompletos |
| 19. Communication Metrics | PASS | `cooperative_compact.py`, artifacts/tests | Métricas persistem sem exigência de tracing detalhado |
| 20. Internal-Lane Proxy | PASS | `docs/methodology/controllers.md`, telemetry/tests | Sem afirmação enganosa de spillback direto |
| 21. Experiment Runner | PASS | `runner.py`, `tests/test_experiment_runner.py` | RUNNING/COMPLETED/FAILED/INTERRUPTED, resume/retry explícitos |
| 22. Route Validation | PASS | `route_artifacts.py`, comando de validação S1-S4 | Validação de hash/seed/cenário/janela passa |
| 23. Freeze | PASS | `freeze.py`, tests | O freeze final verifica os SHA-256 de entrada relevantes |
| 24. Statistics | PASS | `analysis/statistics.py`, tests | Bootstrap pareado; duplicados/ausentes/falhas rejeitados |
| 25. Figures | PARTIAL | `experiments/report.py`, tests | Figuras automáticas existem; conjunto final completo aguarda a campanha |
| 26. Scientific Summary | PASS | `experiments/report.py`, tests | Derivado de artifacts, evita afirmações de superioridade |
| 27. Demo/SUMO-GUI | PARTIAL | `demo.py`, README, tests | Usa o mesmo runner; nenhuma nova checagem visual da GUI |
| 28. Agent Trace | PASS | `agent_trace.py`, `tests/test_agent_trace.py` | Reconstrução opcional de decisões |
| 29. Performance | PASS | `performance.py`, `performance.json`, tests | Métricas p50/p95/média/wall/steps |
| 30. Quality Gates | PASS | Comandos acima | Tudo verde, pytest 279 |
| 31. CI | PASS | `.github/workflows/ci.yml` | Lock sync, Ruff, format, mypy, pytest, Docker, SUMO smoke |
| 32. Security/Scope | PASS | `Dockerfile`, `compose.yaml`, varredura com `rg` | Nenhum segredo encontrado; sem socket do Docker/infra privilegiada |
| 33. Scientific Fairness | PASS | manifests do `mvp1`, invariantes | Mesmas entradas científicas por controlador |
| 34. Repository/Docs | PASS | README/docs/rg/git status | Setup/execução/metodologia documentados; árvore limpa |

## Bloqueios Críticos

Nenhum.

## Comandos Exatos de Reprodução

```powershell
git status --short
rg -n "setPhase|setRedYellowGreenState" src tests docs README.md
rg -n "SECRET|TOKEN|PASSWORD|API_KEY|PRIVATE KEY|BEGIN .*KEY|AWS_ACCESS|AWS_SECRET|DATABASE_URL|REDIS_URL|RABBITMQ|KAFKA|KUBERNETES|POSTGRES|LLM|MARL|GNN" .
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
uv run traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B0_FIXED --seed 42 --max-steps 5 --no-manifest
```

A validação de rotas foi realizada em modo somente leitura por meio de:
`validate_route_artifacts(...)` para S1-S4, verificando seed, hash de configuração, hash do cenário, hash das rotas, hash da rede e janelas de demanda.

## Decisão Final

V1_READY = YES

O protótipo V1 satisfaz a Definition of Done quanto à prontidão científica/técnica. As limitações restantes são questões LOW/PARTIAL de documentação ou de acabamento de artifacts e não invalidam as comparações da V1.
