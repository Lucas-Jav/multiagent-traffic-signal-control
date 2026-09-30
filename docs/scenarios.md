# Cenários Experimentais V1

Todos os cenários V1 usam a mesma rede SUMO 3x3 versionada:
`scenarios/grid_3x3/network.net.xml` (uma lane por aproximação, arestas internas de 235,6 m,
arestas de borda de 92,8 m, uma aproximação atendida por vez pelo programa de tempo fixo de 98 s).

O YAML do cenário é a fonte de verdade para:

- seed da simulação;
- nome do arquivo de rotas;
- perfil e nível de demanda;
- razões de conversão (no nível do cenário e com sobrescrita opcional por entrada);
- cronograma da demanda;
- entradas de borda, suas taxas e janelas de tempo;
- o instante do choque do S3 (`traffic.shock_start_seconds`).

Os arquivos de cenário são gerados, não editados manualmente:

```powershell
uv run python scripts/generate_scenarios.py
```

O script (`scripts/generate_scenarios.py`) contém as definições de S1-S4, escreve os
YAMLs por seed e os artifacts de rotas para o conjunto fixo de seeds da V1 (`42, 2027, 3253, 4517, 5791`)
e escreve o arquivo da seed 42 como arquivo base do cenário.

Os controladores não devem receber configuração específica de cenário. Um controlador pode ser selecionado em
tempo de execução com `--controller`, mas os arquivos de cenário não definem parâmetros
especiais de controlador.

As intensidades de demanda abaixo foram CALIBRADAS no Prompt 46.7 com critérios independentes de controlador
(`scripts/calibrate_scenarios.py`, apenas `B0_FIXED`, seeds de calibração `101, 1009, 2029`, que
são disjuntas do conjunto fixo de seeds). Cada nível é o maior candidato de uma grade predeclarada
que satisfez todos os critérios predeclarados em todas as seeds de calibração; os critérios, os
resultados dos candidatos e a seleção estão em `artifacts/calibration/pilot_v2-scenario-calibration/`
(`calibration-plan.md`, `candidate-results.parquet`, `selected-scenario-levels.md`). A calibração
é calibração de cenário, não ajuste de controlador, e não é um resultado científico.

## Modelo de demanda

`traffic.entries` lista as arestas de entrada de borda (`left0A0`, `left1A1`, `left2A2`, `right0C0`, ...,
`bottom2C0`), cada uma com uma taxa por nível de demanda (`LOW`/`MEDIUM`/`HIGH`), uma janela de tempo em
segundos absolutos de simulação e um `group` (`base`, `dominant`, `residual`, `shock`, `hotspot`).

Os veículos são gerados por um percurso determinístico de conversões em junções, com seed
(`src/traffic_agents/simulation/route_walk.py`): as partidas são igualmente espaçadas na taxa da entrada
(fase com seed); em cada junção semaforizada o veículo escolhe `straight`/`left`/`right` com
as razões de conversão configuradas até sair por uma aresta de saída de borda. Somente movimentos
legais da rede são usados; conversões ilegais nunca são forçadas. Uma entrada pode definir
`via_intersection_id`: seus veículos primeiro seguem um caminho legal mais curto até essa interseção
(usado no choque do S3 e no hotspot do S4) e depois continuam com o percurso baseado nas razões de conversão.
As razões de conversão são, portanto, operacionais: elas moldam as rotas realizadas.

O arquivo de rotas lista elementos `<vehicle>` explícitos que compartilham definições de `<route>`; os ids
dos veículos são `<demand_id>.<index>`.

## Definição compartilhada

- `scenario_id: grid_3x3`
- `warmup_seconds: 300`, `measurement_duration_seconds: 3600`, `step_length: 1.0`
  (total de 3900 s; passos de medição `300 <= i < 3900`) - idêntico para S1-S4
- `turning_ratios`: straight `0.70`, left `0.15`, right `0.15` (valores aprovados no protocolo)
- `demand_level: MEDIUM`
- `controller_id: B0_FIXED` (apenas como padrão)
- `communication.delay_steps: 0`, `communication.drop_probability: 0.0`

`controller_id` é apenas um padrão. A validação deve executar pelo menos `B0_FIXED` e
`B2_LOCAL_PRESSURE` como sobrescritas de controlador para a execução de smoke.

## S1_BALANCED

Config: `scenarios/grid_3x3/scenario.yaml` (seed 42), arquivos por seed
`scenario_s1_balanced_seed_<seed>.yaml`. Rotas: `routes_s1_seed_<seed>.rou.xml`.

- Todas as 12 entradas de borda injetam a mesma taxa (MEDIUM 150 veh/h cada, calibrado).
- Toda rota segue o percurso 70/15/15; nenhuma interseção é forçada em todas as rotas.
- Cobertura esperada: cada uma das nove interseções concentra cerca de 11% de todas as passagens por junções
  (A1 10,9%, A5 10,9%, A9 11,2% para a seed 42); sem cantos ociosos.
- Carga máxima esperada por aproximação: 150 veh/h (toda aproximação carrega a mesma
  carga esperada).

## S2_DIRECTIONAL_PEAK

Config: `scenario_s2_directional_peak.yaml`. Rotas: `routes_s2_seed_<seed>.rou.xml`.

- Perfil dominante Oeste -> Leste: as três entradas de borda oeste (grupo `dominant`, MEDIUM 320
  veh/h cada) injetam cerca de 80% da demanda oferecida; as outras nove bordas (`residual`,
  320 / 12 = 26,67 veh/h cada) injetam os 20% restantes.
- O mesmo percurso 70/15/15 se aplica, então existem movimentos straight, left e right no fluxo
  dominante; a parcela de 80% refere-se à demanda oferecida pelo perfil dominante, não a veículos
  que seguem em frente por toda a rede.
- As entradas dominantes permanecem abaixo da capacidade de entrada (calibradas para que a razão de partida dominante permaneça >= 0,90), de modo que o viés de demanda oferecida não seja escondido
  por starvation de entrada; `run_metrics.json` reporta `offered/departed/arrived` e
  `entry_departure_ratio` por entrada e grupo para verificar isso em tempo de execução.

## S3_DEMAND_SHIFT

Config: `scenario_s3_demand_shift.yaml`. Rotas: `routes_s3_seed_<seed>.rou.xml`.

- Primeira metade: a base balanceada do S1 (mesmas 12 entradas e taxas, desde t = 0).
- Segunda metade: a base continua e um choque abrupto em UMA borda (oeste) é adicionado nas três
  entradas oeste (grupo `shock`, MEDIUM 150 veh/h cada, com viés para straight 0,90/0,05/0,05) com
  `via_intersection_id: A5`, de modo que os veículos do choque são roteados pela interseção central.
- O choque começa em 50% da janela de MEDIÇÃO: `traffic.shock_start_seconds = 2100`
  (`warmup_seconds + measurement_duration_seconds / 2`), 1800 s após o início da medição.
  O validador de cenário rejeita qualquer outro valor.
- A fase base é exatamente igual ao nível S1 calibrado (estável, sem backlog de inserção), de modo que o
  choque fica visível logo após seu início, em vez de ser mascarado por um backlog de entrada.

## S4_LOCAL_SATURATION

Config: `scenario_s4_local_saturation.yaml`. Rotas: `routes_s4_seed_<seed>.rou.xml`.

- Demanda de fundo leve, semelhante ao S1 (`base`, MEDIUM 80 veh/h em todas as 12 bordas), mais demanda `hotspot`
  (MEDIUM 220 veh/h em todas as 12 bordas, com viés para straight 0,90/0,05/0,05) roteada por A5
  (`via_intersection_id: A5`).
- Parcela esperada de passagens por junções: A5 23,0%, vizinhas A2/A4/A6/A8 cerca de 13%
  cada, cantos cerca de 6% cada (seed 42). As quatro aproximações de entrada de A5 carregam uma carga esperada de
  740,173 veh/h, acima da capacidade nominal da aproximação, de modo que a congestão se concentra em torno de
  A5 e pode se propagar para A2/A4/A6/A8. A capacidade não é modificada artificialmente e o cenário
  não exige um deadlock total.
- Política do S4: `ALLOW_AND_MEASURE`. Os teleports devem ser reportados, mas não bloqueiam a validade do S4.

## Reprodutibilidade

Para cada arquivo de rotas gerado, o `*.metadata.json` adjacente registra:

- `seed`, `demand_profile`, `demand_level`, `shock_start_seconds`, `schedule`;
- `routing` (`turning_ratio_walk`) e as `entries` (taxa, janela, razões de conversão efetivas,
  `via_intersection_id`, grupo);
- `turning`: razões configuradas, proporções esperadas e as contagens e proporções de movimentos REALIZADAS
  (também por grupo);
- `offered`: contagens de veículos oferecidos (total, na janela de medição, por entrada, por grupo,
  por item de demanda);
- `coverage`: passagens por junções e parcelas por interseção;
- `expected_approach_load_veh_per_hour` e seu máximo;
- `config_hash`, `scenario_hash`, `route_hash`, `network_hash`.

A mesma seed e a mesma config de cenário recriam arquivos de rotas idênticos byte a byte (`route_hash`).

Hashes gerados atuais (seed 42):

| Perfil | Scenario hash | Route hash |
| --- | --- | --- |
| `S1_BALANCED` | `c89f2064578bc07cf351110bbe5c490ff3a942175f8de0b642576ba5e1f1ae69` | `00860fbd03473c5a5c9552e18ce09003d097603f917f3f443f43dfa22f7d4354` |
| `S2_DIRECTIONAL_PEAK` | `bea562c329950a32a74f5c68478d6d1fa7ac50357faae36ac56f60adf6a18d34` | `75e1c16967c6b35389dd923e535a82935bf9d9611dcd48ee1d448d3d4c596a85` |
| `S3_DEMAND_SHIFT` | `a3a87ddfa970030f000e4577196028ee36fac5698f2192b4d50d00b178555ff7` | `897daabad4bd947643e0d9bea251d97d78062108c36b8234f7392475e243b21f` |
| `S4_LOCAL_SATURATION` | `55426d1f4ca02cd8af5e636bc440c1a49152986277f9ab09a5d61e1a4693cf62` | `df6aaf38486f3515a9b0f48af8c93b6fa053ed157b15a3d467502d742517fee2` |

## Procedimento de Validação

Para cada arquivo de cenário:

1. Regenerar com `uv run python scripts/generate_scenarios.py` e confirmar que `git status`
   não mostra mudança inesperada (seed determinística).
2. Validar os artifacts de rotas (`validate_route_artifacts`: hashes, janelas de entrada, contagens de veículos).
3. Confirmar que as proporções de movimentos realizadas estão a até 0,03 das razões configuradas.
4. Confirmar as expectativas estruturais acima (cobertura do S1, parcela dominante de 80% do S2, momento e
   roteamento do choque do S3, concentração em A5 do S4); `tests/test_route_walk.py` as verifica.
5. Executar uma simulação de smoke com `B0_FIXED`, `B2_LOCAL_PRESSURE` e um controlador cooperativo
   (`tests/test_pipeline_sumo.py`).
