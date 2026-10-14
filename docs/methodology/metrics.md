# Métricas Específicas por Cenário

Status: definições finais de métricas da V1 (revisadas no Prompt 46.6 após o diagnóstico forense
do Pilot V1). Essas definições devem ser congeladas antes da execução do Pilot V2 ou da campanha final.
Os números do Pilot V1 calculados com as definições anteriores foram substituídos (veja
`artifacts/experiments/pilot_v1/pilot-assessment-erratum.md`).

A campanha final não deve usar métricas calculadas manualmente. Toda execução (run) concluída é finalizada pelo
pipeline canônico (`run_metrics.json`, `metrics_finalized: true` no manifesto da run) e
o runner de experimentos agrega todas as runs finalizadas em `combined_metrics.parquet`
(`traffic-agents experiment aggregate <folder>` faz o mesmo para um experimento existente).
A geração de relatórios e a análise pareada leem esse arquivo. Uma run cuja finalização falha é uma
run FAILED: nunca é exportada como zeros e nunca é marcada como concluída.

## Política de medição e de população

Todos os cenários compartilham uma mesma temporização: `warmup_seconds = 300`, `measurement_duration_seconds = 3600`,
`step_length = 1.0` (total de 3900 s; o passo `i` executa o tempo de simulação de `i` a `i + 1`). Os passos
de medição são `300 <= i < 3900`. O cenário S3 posiciona seu choque (shock) em 50% da janela de MEDIÇÃO:
`shock_start_seconds = 300 + 3600 / 2 = 2100` (`shock_start_step = 2100`).

* **Coorte de medição (measurement cohort)**: os veículos ofertados (arquivo de rotas) cuja partida AGENDADA está em
  `[warmup, warmup + measurement_duration)`. As contagens de população e todas as métricas de viagens concluídas
  usam a coorte, de modo que a demanda do warmup nunca contamine as populações de medição.
* As contagens de **execução completa (full-run)** (`full_run_*`) cobrem todos os veículos ofertados de toda a run.
* As **populações** são persistidas como `offered` (ofertados), `departed` (inseridos), `arrived` (concluídos),
  `never_inserted` (offered - departed) e `unfinished_in_network` (departed - arrived), tanto
  para a coorte (`offered_vehicle_count`, ... e os nomes equivalentes `measurement_*`) quanto para
  a run inteira (`full_run_*`). Razões derivadas: `departure_ratio = departed / offered`,
  `completion_ratio_offered = arrived / offered`, `completion_ratio_departed = arrived / departed`
  (0.0 quando o denominador é 0).
* **`throughput`** (vazão) é uma contagem de fluxo: veículos que CHEGAM dentro da janela de medição (também
  conta veículos agendados durante o warmup que chegam dentro da janela).
* As **métricas de viagens concluídas** (`mean_travel_time`, `mean_waiting_time`, `mean_time_loss`,
  `mean_stops`, `mean_time_in_system_seconds`, `corridor_*`, `post_shock_time_loss`) são
  CONDICIONAIS à conclusão: fazem a média apenas dos veículos da coorte que chegaram antes do fim da run.
  A `duration` do SUMO começa na inserção, portanto o tempo de viagem, o tempo de espera e a perda de tempo (time loss) excluem o
  atraso de inserção e todo veículo nunca inserido. Um controlador que conclui menos viagens pode,
  portanto, apresentar menor atraso nas viagens concluídas sem ser melhor. A análise final deve sempre combinar
  essas métricas com `throughput`, `completion_ratio_offered`/`departure_ratio` e as métricas de fila
  (`COMPANION_METRICS` em `metric_definitions.py`) e não deve interpretar um menor
  atraso nas viagens concluídas como melhor quando as razões de conclusão diferem.
* **Atraso de inserção**: `mean_depart_delay_seconds` e `total_depart_delay_seconds` vêm do
  `departDelay` do SUMO para os veículos da coorte que efetivamente partiram. Os veículos nunca inseridos são
  reportados separadamente (`never_inserted_vehicle_count`), e um LIMITE INFERIOR documentado do atraso de
  backlog deles (`never_inserted_backlog_delay_lower_bound_seconds`: fim da run menos partida
  agendada) é fornecido; ele nunca é mesclado nas médias de viagens concluídas.

## Tabela canônica de métricas

Esta é a lista canônica de campos persistidos em `run_metrics.json` e agregados em
`combined_metrics.parquet`. Os nomes na coluna "Campo canônico" são os únicos que devem aparecer em
relatórios e no texto do TCC; aliases estão em "Aliases e nomes históricos". A seção
"Definições das métricas" mais abaixo espelha `src/traffic_agents/experiments/metric_definitions.py`
com todos os detalhes (janela, casos extremos).

Legenda: **Coorte** = veículos ofertados com partida AGENDADA em `[warmup, warmup + measurement_duration)`.
**Concluídas** = viagens da coorte que chegaram antes do fim da run (métrica condicional à conclusão:
ler junto com `throughput`, razões de conclusão e filas).

| Campo canônico | Nome de exibição (PT) | Unidade | Fonte | População | Denominador | Fórmula | Cenários | Ressalva de interpretação |
|---|---|---|---|---|---|---|---|---|
| `throughput` | Vazão | veículos | `tripinfo.xml` (instante de chegada) | Todo veículo que CHEGA na janela de medição (inclui agendados no warmup) | n/a | contagem de chegadas em `[300, 3900)` | S1-S5 | Contagem de fluxo, não coorte; não isolada de backlog. Ler com razões de conclusão. |
| `offered_vehicle_count` | Veículos ofertados | veículos | arquivo de rotas | Coorte | n/a | contagem de partidas agendadas na janela | S1-S4 | Idêntico entre controladores na mesma seed. |
| `departed_vehicle_count` | Veículos inseridos | veículos | rotas + `tripinfo.xml` | Coorte | n/a | ofertados que entraram na rede | S1-S4 | Menor que ofertados indica starvation de inserção. |
| `arrived_vehicle_count` | Veículos concluídos | veículos | rotas + `tripinfo.xml` | Coorte | n/a | inseridos que chegaram | S1-S4 | Difere de `throughput` (coorte vs. fluxo na janela). |
| `never_inserted_vehicle_count` | Veículos nunca inseridos | veículos | rotas + `tripinfo.xml` | Coorte | n/a | `offered - departed` | S1-S4 | Valor alto indica sobrecarga (no S4 é intencional). |
| `unfinished_in_network_count` | Veículos não concluídos na rede | veículos | rotas + `tripinfo.xml` | Coorte | n/a | `departed - arrived` | S1-S4 | Viagens não concluídas ficam fora das médias de viagem. |
| `departure_ratio` | Razão de inserção | razão | contagens | Coorte | `offered_vehicle_count` | `departed / offered` | S1-S4 | 0.0 se ofertados = 0. |
| `completion_ratio_offered` | Razão de conclusão (sobre ofertados) | razão | contagens | Coorte | `offered_vehicle_count` | `arrived / offered` | S1-S5 | Preferida para comparar controladores (inclui não inseridos). |
| `completion_ratio_departed` | Razão de conclusão (sobre inseridos) | razão | contagens | Coorte | `departed_vehicle_count` | `arrived / departed` | S1-S4 | Oculta starvation de inserção; não usar isolada. |
| `mean_depart_delay_seconds` | Atraso médio de inserção | s/veículo | `departDelay` do `tripinfo.xml` | Inseridos da coorte | inseridos | média de `departDelay` | S1-S4 | Exclui nunca inseridos (viés de sobrevivência). |
| `mean_waiting_time` | Tempo de espera médio | s/veículo | `waitingTime` do `tripinfo.xml` | Concluídas da coorte | concluídas | média | S1, S4, S5 | Condicional à conclusão. |
| `mean_time_loss` | Perda de tempo média | s/veículo | `timeLoss` do `tripinfo.xml` | Concluídas da coorte | concluídas | média | S1, S2, S4, S5 | Condicional à conclusão. |
| `mean_travel_time` | Tempo de viagem médio | s/veículo | `duration` do `tripinfo.xml` | Concluídas da coorte | concluídas | média de (chegada - inserção) | S1, S4 | Exclui atraso de inserção; condicional à conclusão. |
| `mean_stops` | Paradas médias | paradas/veículo | `waitingCount` do `tripinfo.xml` | Concluídas da coorte | concluídas | média | S1, S2 | Condicional à conclusão. |
| `mean_lane_queue_vehicles` | Fila média por lane | veículos | `lane_telemetry.parquet` | Lanes de entrada únicas, passos da medição | passos x lanes | média de `lane_queue` (veículos parados) | S1-S4 | Escala por lane; não comparar diretamente com a fila de rede. |
| `mean_network_queue_vehicles` | Fila média da rede | veículos | `lane_telemetry.parquet` | Lanes de entrada únicas, passos da medição | passos de medição | média de `network_total_queue` (soma das filas das lanes) | S1-S5 | Nunca somar linhas de movimento (duplicaria lanes). |
| `max_network_queue_vehicles` | Fila máxima da rede | veículos | `lane_telemetry.parquet` | idem | passos de medição | máximo de `network_total_queue` | S1-S4 | Estatística de pico, sensível a outliers. |
| `max_lane_queue_vehicles` | Fila máxima por lane | veículos | `lane_telemetry.parquet` | idem | passos x lanes | máximo de `lane_queue` | S1-S4 | Satura na capacidade física da lane (~30 veículos) em cenários sobrecarregados. |
| `internal_lane_persistence_events` | Eventos de persistência em lane interna | eventos | `junction_telemetry.parquet` | Lanes internas das interseções | n/a | veículos nas lanes internas em passos consecutivos, somado sobre interseções e passos de medição | S4 | Proxy; não é spillback nem gridlock medido diretamente. |
| `post_shock_queue_auc_vehicle_seconds` | AUC da fila pós-choque | veículo-s | `lane_telemetry.parquet` | `network_total_queue` pós-choque | n/a | integral de `network_total_queue` do choque ao fim da medição | S3 | Definição congelada (ver "AUC da fila pós-choque"). |
| `post_shock_time_loss` | Perda de tempo pós-choque | s/veículo | `timeLoss` do `tripinfo.xml` | Concluídas da coorte agendadas em/depois do choque | concluídas pós-choque | média | S3 | Condicional à conclusão; população definida por partida agendada. |
| `sumo_teleports_total` | Teleportes do SUMO | veículos | `sumo/statistics.xml` (`<teleports total>`) | Run inteira (não é coorte) | n/a | contagem de teleportes | S1-S5 (gate no S4) | S4 usa `ALLOW_AND_MEASURE`: reportar ao lado de todo resultado do S4. Persistido em `counts` do `run_metrics.json`. |
| `messages_sent` | Mensagens enviadas | mensagens | `MessageBus` | Run simulada completa (inclui warmup) | n/a | total publicado | S5 (C1/C2) | 0 para B0/B1/B2. |
| `messages_delivered` | Mensagens entregues | mensagens | `MessageBus` | idem | n/a | total entregue | S5 | Depende de `drop_probability` e `delay_steps`. |
| `messages_dropped` | Mensagens perdidas | mensagens | `MessageBus` | idem | n/a | total descartado por perda | S5 | Ver política de perda. |
| `messages_stale` | Mensagens obsoletas | mensagens | contabilização de atualidade dos cooperativos | idem | n/a | recebidas com `age > max_message_age_steps` | S5 | Ignoradas pelo ajuste cooperativo. |
| `bytes_sent` | Bytes enviados | bytes | `MessageBus` (mensagens serializadas) | idem | n/a | total serializado publicado | S5 | Custo de comunicação. |
| `bytes_delivered` | Bytes entregues | bytes | `MessageBus` | idem | n/a | total serializado entregue | S5 | idem |
| `mean_message_age_steps` | Idade média da mensagem | passos | atualidade dos cooperativos | idem | mensagens observadas | média de `current_step - created_step` | S5 | Nome canônico; ver aliases. |
| `max_message_age_steps` | Idade máxima da mensagem | passos | atualidade dos cooperativos | idem | n/a | máximo observado | S5 | Nome canônico; ver aliases. |
| `controller_decision_mean_ms` | Tempo médio de decisão do controlador | ms | `performance.json` / `run_metrics.json` | Todos os passos (inclui warmup) | passos | média do tempo de decisão | S1-S5 | Desempenho computacional, dependente da máquina; não é métrica de tráfego. |
| `controller_decision_max_ms` | Tempo máximo de decisão do controlador | ms | `performance.json` | idem | passos | máximo | S1-S5 | Implementado em `metrics/performance.py` e persistido em `performance.json`. Também existem `controller_decision_p50_ms` e `controller_decision_p95_ms`. |

Todas as métricas de tráfego acima são calculadas pelo pipeline canônico de finalização da run; a
campanha final não usa métricas calculadas manualmente.

## Aliases e nomes históricos

Os nomes canônicos são os da coluna "Campo canônico". `METRIC_DEFINITION_ALIASES`
(`src/traffic_agents/experiments/metric_definitions.py`) mapeia nomes alternativos para o canônico e
é usado para resolver definições; **nenhum campo persistido foi renomeado**, portanto artefatos
existentes continuam legíveis.

| Nome histórico / alias | Canônico | Onde ainda aparece e por quê |
|---|---|---|
| `average_message_age` | `mean_message_age_steps` | Atributo interno do resultado do ajuste cooperativo (`cooperative_compact.py`) e saída do `demo`; o trace usa `average`. Compatibilidade interna, não persistido como métrica. |
| `max_observed_message_age` | `max_message_age_steps` | idem |
| `mean_waiting_time_seconds`, `mean_time_loss_seconds`, `mean_travel_time_seconds` | `mean_waiting_time`, `mean_time_loss`, `mean_travel_time` | Nomes pedidos em prompts do Pilot V2; explicados em `pilot-assessment.md`. |
| `avg_waiting_time`, `average_waiting_time`, `avg_time_loss`, `average_time_loss` | `mean_waiting_time`, `mean_time_loss` | Listas de nomes candidatos de `TRAFFIC_METRIC_FIGURES` em `experiments/report.py`: alias de exibição **intencional** (tolerância de leitura para figuras), não campo obsoleto nem bug. |
| `network_throughput`, `vehicles_arrived`, `arrived` | `throughput` | Aliases de definição. |
| `corridor_travel_time`, `corridor_stops` | `corridor_mean_travel_time`, `corridor_mean_stops` | Aliases de definição. |

Nomes de fila ambíguos (`mean_queue`, `max_queue`, `queue`) NÃO são aliasados: toda métrica de fila
deve nomear seu escopo (lane / interseção / rede).

## Métricas futuras / opcionais (NÃO implementadas)

As métricas abaixo **não** fazem parte do conjunto central atual e não existem em `run_metrics.json`:

- `recovery_time_seconds`: nenhuma regra de limiar fixa foi congelada antes dos resultados. O S3 usa
  as métricas de fila e de perda de tempo pós-choque.
- Métrica agregada de ocupação a jusante: a ocupação downstream existe só como entrada da lógica dos
  controladores; não é agregada como métrica final por run.
- Tempo de viagem da rota de referência (`reference_route_*`): definida em
  [`reference-route.md`](reference-route.md) como futura; ainda não implementada.

## Métricas de fila

A telemetria de fila (queue) é produzida pelo runner da simulação para todo controlador (incluindo
`B0_FIXED`) após cada passo de simulação. Ela armazena uma linha por lane de entrada ÚNICA e por passo
(`lane_telemetry.parquet`) e uma linha por interseção e por passo (`junction_telemetry.parquet`).
O antigo rastreamento por movimento repetia a fila de uma lane uma vez para cada movimento que a usava; somas
sobre esse rastreamento superestimavam as filas em três vezes e não são mais usadas.

* `lane_queue`: contagem de veículos parados (halting) do SUMO em uma lane de entrada e um passo.
* `intersection_total_queue`: soma das filas das lanes de entrada únicas de uma interseção.
* `network_total_queue`: soma das filas das lanes de entrada únicas de todas as interseções.

Métricas finais de fila: `mean_network_queue_vehicles`, `max_network_queue_vehicles`,
`mean_intersection_queue_vehicles`, `max_intersection_queue_vehicles`,
`max_lane_queue_vehicles` (mais a `mean_lane_queue_vehicles`, de caráter diagnóstico). Não existe
`max_queue`/`mean_queue` sem escopo definido.

**Nota sobre capacidade física.** `max_lane_queue_vehicles` pode saturar no limite de armazenamento físico de uma
lane: uma aresta de faixa única de 235,6 m comporta cerca de 30 veículos parados (comprimento do veículo de 5 m mais
distância mínima de 2,5 m, deslocamento de parada de 7 m), e uma aresta de borda de 92,8 m cerca de 12. Portanto, cerca de 30 é
um limite físico, não um teto imposto pelo software. Em cenários sobrecarregados, `max_lane_queue_vehicles` perde
poder discriminatório (todas as runs atingem o mesmo máximo); por isso, os agregados de rede e de interseção
permanecem disponíveis e devem ser reportados junto com ela.

## AUC da fila pós-choque (S3, definição congelada)

`post_shock_queue_auc_vehicle_seconds` é a integral da `network_total_queue` canônica
ao longo do intervalo de medição pós-choque, com integração trapezoidal sobre o tempo de simulação:

```text
auc = sum((Q_i + Q_{i+1}) / 2 * (t_{i+1} - t_i))     [vehicle-seconds]
```

* `Q_i` = `network_total_queue` = soma, sobre as lanes de entrada ÚNICAS, da contagem de veículos parados amostrada
  após o passo `i` (nunca linhas em nível de movimento, de modo que nenhuma lane seja contada duas vezes);
* `t_i` = timestamp de telemetria do passo `i` (`(i + 1) * step_length`);
* as amostras são os passos `shock_start_step <= i < measurement_end_step`, onde
  `shock_start_step = shock_start_seconds / step_length` e `shock_start_seconds` é o
  `traffic.shock_start_seconds` congelado do cenário (2100 s para S3 = 50% da janela de
  medição);
* menos de duas amostras -> 0. As métricas relacionadas `post_shock_mean_network_queue_vehicles` e
  `post_shock_max_network_queue_vehicles` usam as mesmas amostras.

`post_shock_time_loss` usa viagens concluídas de veículos da coorte AGENDADOS no início do choque ou depois
(não veículos inseridos depois dele), de modo que um backlog de entrada pré-choque não possa se passar por
demanda pós-choque.

## Definição do corredor

Versão da definição do corredor: `west-east-middle-corridor-v2`

Caminho operacional:

```text
West -> A4 -> A5 -> A6 -> East
```

Identificadores do SUMO:

- aresta de entrada: `left1A1`
- caminho de interseções controladas: `A1 -> B1 -> C1`
- arestas de passagem: `A1B1`, `B1C1`
- aresta de saída: `C1right1`

Pertencimento ao corredor: a rota do veículo percorre a aresta `A1B1` seguida imediatamente pela aresta
`B1C1`. As métricas do corredor são calculadas apenas para esses veículos; o alvo do corredor é uma
demanda direcional, não uma afirmação de que todo veículo atravessa toda a rede em linha reta.

## Contabilização por entrada

`run_metrics.json` também armazena, por aresta de entrada e por grupo de demanda (`base`, `dominant`,
`residual`, `shock`, `hotspot`), os valores da coorte `offered`, `departed`, `arrived` e
`entry_departure_ratio` (`by_entry`, `by_group`), além de `min_entry_departure_ratio`. Eles permitem que uma
run valide que o padrão de demanda pretendido (por exemplo, a parcela dominante de 80% do oeste em S2)
ainda chega à rede e não é ocultado por starvation de inserção.

## Conjuntos de métricas por cenário

| Cenário | Métricas |
|---|---|
| `S1_BALANCED` | `throughput`, `mean_travel_time`, `mean_waiting_time`, `mean_time_loss`, `mean_stops`, `mean_network_queue_vehicles`, `max_network_queue_vehicles`, `mean_intersection_queue_vehicles`, `max_intersection_queue_vehicles`, `max_lane_queue_vehicles`, `offered_vehicle_count`, `departed_vehicle_count`, `arrived_vehicle_count`, `never_inserted_vehicle_count`, `unfinished_in_network_count`, `departure_ratio`, `completion_ratio_offered`, `completion_ratio_departed`, `mean_depart_delay_seconds` |
| `S2_DIRECTIONAL_PEAK` | `throughput`, `mean_stops`, `mean_time_loss`, `corridor_throughput`, `corridor_mean_travel_time`, `corridor_mean_stops`, `min_entry_departure_ratio`, `mean_network_queue_vehicles`, `max_network_queue_vehicles`, `mean_intersection_queue_vehicles`, `max_intersection_queue_vehicles`, `max_lane_queue_vehicles`, `offered_vehicle_count`, `departed_vehicle_count`, `arrived_vehicle_count`, `never_inserted_vehicle_count`, `unfinished_in_network_count`, `departure_ratio`, `completion_ratio_offered`, `completion_ratio_departed`, `mean_depart_delay_seconds` |
| `S3_DEMAND_SHIFT` | `post_shock_mean_network_queue_vehicles`, `post_shock_max_network_queue_vehicles`, `post_shock_time_loss`, `post_shock_queue_auc_vehicle_seconds`, `throughput`, `offered_vehicle_count`, `departed_vehicle_count`, `arrived_vehicle_count`, `never_inserted_vehicle_count`, `unfinished_in_network_count`, `departure_ratio`, `completion_ratio_offered`, `completion_ratio_departed`, `mean_depart_delay_seconds` |
| `S4_LOCAL_SATURATION` | `throughput`, `mean_time_loss`, `mean_travel_time`, `internal_lane_persistence_events`, `mean_network_queue_vehicles`, `max_network_queue_vehicles`, `mean_intersection_queue_vehicles`, `max_intersection_queue_vehicles`, `max_lane_queue_vehicles`, `offered_vehicle_count`, `departed_vehicle_count`, `arrived_vehicle_count`, `never_inserted_vehicle_count`, `unfinished_in_network_count`, `departure_ratio`, `completion_ratio_offered`, `completion_ratio_departed`, `mean_depart_delay_seconds` |
| `S5_COMMUNICATION_DEGRADATION` | `throughput`, `mean_waiting_time`, `mean_time_loss`, `mean_network_queue_vehicles`, `messages_sent`, `messages_delivered`, `messages_dropped`, `messages_stale`, `bytes_sent`, `bytes_delivered`, `mean_message_age_steps`, `max_message_age_steps`, `throughput_change_vs_zero_loss`, `completion_ratio_offered` |

`recovery_time_seconds` não é implementada na V1 porque nenhuma regra de limiar fixa e definida antes
dos resultados foi congelada. O S3 usa, em vez dela, as métricas de fila e de perda de tempo (time loss) pós-choque.

A ocupação downstream está disponível para a lógica do controlador, mas não é agregada como métrica final
da campanha a partir dos artifacts das runs. Ela não deve ser reportada como métrica final do S4 até que uma
agregação em nível de artifact seja implementada e congelada.

## Definições das métricas

| Nome | Unidade | Fonte | População / denominador | Janela de medição | Agregação | Casos extremos | Somente viagens concluídas |
|---|---|---|---|---|---|---|---|
| `offered_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Contagem de veículos ofertados na coorte de medição (alias de measurement_offered_vehicle_count). | As contagens são 0 quando a população está vazia. | não |
| `departed_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Veículos da coorte que foram inseridos na rede antes do fim da run. | As contagens são 0 quando a população está vazia. | não |
| `arrived_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Veículos da coorte que chegaram antes do fim da run. | As contagens são 0 quando a população está vazia. | não |
| `never_inserted_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Veículos da coorte que nunca entraram na rede (offered - departed). | As contagens são 0 quando a população está vazia. | não |
| `unfinished_in_network_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Veículos da coorte inseridos, mas que não chegaram ao fim da run (departed - arrived). | As contagens são 0 quando a população está vazia. | não |
| `full_run_offered_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Todos os veículos ofertados. | Run inteira, incluindo o warmup (offered/departed/arrived sobre todos os veículos). | Todos os veículos ofertados pelo arquivo de rotas ao longo da run inteira. | As contagens são 0 quando a população está vazia. | não |
| `full_run_departed_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Todos os veículos ofertados. | Run inteira, incluindo o warmup (offered/departed/arrived sobre todos os veículos). | Todos os veículos inseridos na rede ao longo da run inteira. | As contagens são 0 quando a população está vazia. | não |
| `full_run_arrived_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Todos os veículos ofertados. | Run inteira, incluindo o warmup (offered/departed/arrived sobre todos os veículos). | Todos os veículos que chegaram ao longo da run inteira. | As contagens são 0 quando a população está vazia. | não |
| `full_run_never_inserted_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Todos os veículos ofertados. | Run inteira, incluindo o warmup (offered/departed/arrived sobre todos os veículos). | Veículos ofertados que nunca entraram na rede ao longo da run inteira. | As contagens são 0 quando a população está vazia. | não |
| `full_run_unfinished_in_network_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Todos os veículos ofertados. | Run inteira, incluindo o warmup (offered/departed/arrived sobre todos os veículos). | Veículos inseridos, mas que não chegaram ao fim da run. | As contagens são 0 quando a população está vazia. | não |
| `measurement_offered_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Veículos ofertados agendados dentro da janela de medição. | As contagens são 0 quando a população está vazia. | não |
| `measurement_departed_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Veículos da coorte inseridos antes do fim da run. | As contagens são 0 quando a população está vazia. | não |
| `measurement_arrived_vehicle_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Veículos da coorte que chegaram antes do fim da run. | As contagens são 0 quando a população está vazia. | não |
| `departure_ratio` | ratio | Contagens de população do arquivo de rotas e do tripinfo do SUMO. | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | departed_vehicle_count / offered_vehicle_count. | Reportada como 0.0 quando o denominador é 0. | não |
| `completion_ratio_offered` | ratio | Contagens de população do arquivo de rotas e do tripinfo do SUMO. | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | arrived_vehicle_count / offered_vehicle_count. | Reportada como 0.0 quando o denominador é 0. | não |
| `completion_ratio_departed` | ratio | Contagens de população do arquivo de rotas e do tripinfo do SUMO. | Coorte de medição. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | arrived_vehicle_count / departed_vehicle_count. | Reportada como 0.0 quando o denominador é 0. | não |
| `throughput` | vehicles | Tempos de chegada do tripinfo do SUMO (igual às contagens de arrived do SUMO por passo). | Contagem de fluxo: todo veículo que chega na janela, incluindo veículos agendados durante o warmup. | Warmup excluído; intervalo de medição vindo da configuração do cenário. | Contagem de veículos que chegam durante a janela de medição. | Se nenhum veículo chega, reportar 0. | não |
| `completed_trip_count` | vehicles | Arquivo de rotas (partidas agendadas) combinado com o tripinfo do SUMO (departed/arrived). | Coorte de medição, viagens concluídas. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Veículos da coorte usados nas métricas de viagens concluídas (chegaram antes do fim da run). | As contagens são 0 quando a população está vazia. | não |
| `mean_depart_delay_seconds` | seconds/vehicle | departDelay do tripinfo do SUMO (instante de inserção - partida agendada). | Veículos da coorte que efetivamente partiram (veículos nunca inseridos excluídos). | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Média aritmética sobre os veículos da coorte que foram inseridos. | Omitida se nenhum veículo da coorte foi inserido. | não |
| `total_depart_delay_seconds` | seconds | departDelay do tripinfo do SUMO. | Veículos da coorte que efetivamente partiram. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Soma sobre os veículos da coorte que foram inseridos. | 0 quando nenhum veículo da coorte foi inserido. | não |
| `never_inserted_backlog_delay_lower_bound_seconds` | seconds | Partida agendada do arquivo de rotas e fim da run simulada. | Veículos da coorte que nunca entraram na rede. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Soma, sobre os veículos da coorte nunca inseridos, de (fim da run - partida agendada); um LIMITE INFERIOR do atraso de backlog deles, nunca mesclado nas médias de viagens concluídas. | 0 quando todo veículo da coorte foi inserido. | não |
| `mean_travel_time` | seconds/vehicle | duration do tripinfo do SUMO (chegada - inserção; exclui o atraso de inserção). | Viagens concluídas da coorte de medição (condicional à conclusão). | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Média aritmética sobre as viagens concluídas da coorte. | Se nenhum veículo da coorte conclui a viagem, omitir a métrica para essa run. | sim |
| `mean_waiting_time` | seconds/vehicle | waitingTime do tripinfo do SUMO para viagens concluídas. | Viagens concluídas da coorte de medição (condicional à conclusão). | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Média aritmética sobre as viagens concluídas da coorte. | Se nenhum veículo da coorte conclui a viagem, omitir a métrica para essa run. | sim |
| `mean_time_loss` | seconds/vehicle | timeLoss do tripinfo do SUMO para viagens concluídas. | Viagens concluídas da coorte de medição (condicional à conclusão). | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Média aritmética sobre as viagens concluídas da coorte. | Se nenhum veículo da coorte conclui a viagem, omitir a métrica para essa run. | sim |
| `mean_stops` | stops/vehicle | waitingCount do tripinfo do SUMO para viagens concluídas. | Viagens concluídas da coorte de medição (condicional à conclusão). | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Média aritmética sobre as viagens concluídas da coorte. | Se nenhum veículo da coorte conclui a viagem, omitir a métrica para essa run. | sim |
| `mean_time_in_system_seconds` | seconds/vehicle | duration + departDelay do tripinfo do SUMO para viagens concluídas. | Viagens concluídas da coorte de medição (condicional à conclusão). | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Média aritmética de (tempo de viagem + atraso de inserção) sobre as viagens concluídas. | Se nenhum veículo da coorte conclui a viagem, omitir a métrica para essa run. | sim |
| `corridor_throughput` | vehicles | Pertencimento ao corredor no arquivo de rotas (west-east-middle-corridor-v2) e tripinfo. | Contagem de fluxo de veículos cuja rota percorre o corredor da linha central. | Warmup excluído; intervalo de medição vindo da configuração do cenário. | Contagem de veículos do corredor que chegam durante a janela de medição. | Se nenhum veículo do corredor chega, reportar 0. | não |
| `corridor_mean_travel_time` | seconds/vehicle | duration do tripinfo do SUMO filtrada para west-east-middle-corridor-v2. | Viagens concluídas do corredor na coorte de medição (condicional). | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Média aritmética sobre as viagens concluídas da coorte. | Se nenhum veículo da coorte conclui a viagem, omitir a métrica para essa run. | sim |
| `corridor_mean_stops` | stops/vehicle | waitingCount do tripinfo do SUMO filtrado para west-east-middle-corridor-v2. | Viagens concluídas do corredor na coorte de medição (condicional). | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Média aritmética sobre as viagens concluídas da coorte. | Se nenhum veículo da coorte conclui a viagem, omitir a métrica para essa run. | sim |
| `post_shock_time_loss` | seconds/vehicle | timeLoss do tripinfo do SUMO de viagens concluídas agendadas no instante do choque ou depois. | Viagens concluídas de veículos da coorte AGENDADOS no início do choque ou depois (condicional à conclusão; população definida pelo instante agendado, não pelo de inserção). | Subconjunto pós-choque da janela de medição. | Média aritmética sobre as viagens concluídas da coorte. | Se nenhum veículo da coorte conclui a viagem, omitir a métrica para essa run. | sim |
| `pre_shock_time_loss` | seconds/vehicle | timeLoss do tripinfo do SUMO de viagens concluídas agendadas antes do instante do choque. | Viagens concluídas de veículos da coorte agendados antes do início do choque (condicional à conclusão). | Subconjunto pré-choque da janela de medição. | Média aritmética sobre as viagens concluídas da coorte. | Se nenhum veículo da coorte conclui a viagem, omitir a métrica para essa run. | sim |
| `mean_network_queue_vehicles` | vehicles | lane_telemetry.parquet / junction_telemetry.parquet canônicos (contagem de veículos parados do SUMO por lane de entrada ÚNICA, amostrada pelo runner da simulação para todo controlador). | Todos os veículos parados nas lanes de entrada; cada lane física contada uma vez. | Apenas os passos da janela de medição (warmup excluído); uma amostra por passo de simulação. | Média, sobre os passos de medição, de network_total_queue (soma das contagens de veículos parados das lanes de entrada únicas). | Omitida somente se não existirem amostras de telemetria na janela (a run falha). | não |
| `max_network_queue_vehicles` | vehicles | lane_telemetry.parquet / junction_telemetry.parquet canônicos (contagem de veículos parados do SUMO por lane de entrada ÚNICA, amostrada pelo runner da simulação para todo controlador). | Todos os veículos parados nas lanes de entrada; cada lane física contada uma vez. | Apenas os passos da janela de medição (warmup excluído); uma amostra por passo de simulação. | Máximo, sobre os passos de medição, de network_total_queue. | Omitida somente se não existirem amostras de telemetria na janela (a run falha). | não |
| `mean_intersection_queue_vehicles` | vehicles | lane_telemetry.parquet / junction_telemetry.parquet canônicos (contagem de veículos parados do SUMO por lane de entrada ÚNICA, amostrada pelo runner da simulação para todo controlador). | Todos os veículos parados nas lanes de entrada; cada lane física contada uma vez. | Apenas os passos da janela de medição (warmup excluído); uma amostra por passo de simulação. | Média, sobre os passos de medição e as interseções, de intersection_total_queue (soma das contagens de veículos parados das lanes de entrada únicas de uma interseção). | Omitida somente se não existirem amostras de telemetria na janela (a run falha). | não |
| `max_intersection_queue_vehicles` | vehicles | lane_telemetry.parquet / junction_telemetry.parquet canônicos (contagem de veículos parados do SUMO por lane de entrada ÚNICA, amostrada pelo runner da simulação para todo controlador). | Todos os veículos parados nas lanes de entrada; cada lane física contada uma vez. | Apenas os passos da janela de medição (warmup excluído); uma amostra por passo de simulação. | Máximo, sobre os passos de medição e as interseções, de intersection_total_queue. | Omitida somente se não existirem amostras de telemetria na janela (a run falha). | não |
| `mean_lane_queue_vehicles` | vehicles | lane_telemetry.parquet / junction_telemetry.parquet canônicos (contagem de veículos parados do SUMO por lane de entrada ÚNICA, amostrada pelo runner da simulação para todo controlador). | Todos os veículos parados nas lanes de entrada; cada lane física contada uma vez. | Apenas os passos da janela de medição (warmup excluído); uma amostra por passo de simulação. | Média, sobre os passos de medição e as lanes, de lane_queue (diluída por lanes ociosas; somente diagnóstica). | Omitida somente se não existirem amostras de telemetria na janela (a run falha). | não |
| `max_lane_queue_vehicles` | vehicles | lane_telemetry.parquet / junction_telemetry.parquet canônicos (contagem de veículos parados do SUMO por lane de entrada ÚNICA, amostrada pelo runner da simulação para todo controlador). | Todos os veículos parados nas lanes de entrada; cada lane física contada uma vez. | Apenas os passos da janela de medição (warmup excluído); uma amostra por passo de simulação. | Máximo de lane_queue sobre os passos de medição e as lanes. Pode saturar na capacidade física de armazenamento de uma lane (cerca de 30 veículos em uma aresta de 235,6 m) em cenários sobrecarregados e então perde poder discriminatório; use os agregados de rede/interseção em conjunto com ela. | Omitida somente se não existirem amostras de telemetria na janela (a run falha). | não |
| `post_shock_mean_network_queue_vehicles` | vehicles | lane_telemetry.parquet / junction_telemetry.parquet canônicos (contagem de veículos parados do SUMO por lane de entrada ÚNICA, amostrada pelo runner da simulação para todo controlador). | Todos os veículos parados nas lanes de entrada; cada lane física contada uma vez. | Subconjunto pós-choque da janela de medição (passo >= passo de início do choque). | Média de network_total_queue sobre os passos de medição pós-choque. | Omitida somente se não existirem amostras de telemetria na janela (a run falha). | não |
| `post_shock_max_network_queue_vehicles` | vehicles | lane_telemetry.parquet / junction_telemetry.parquet canônicos (contagem de veículos parados do SUMO por lane de entrada ÚNICA, amostrada pelo runner da simulação para todo controlador). | Todos os veículos parados nas lanes de entrada; cada lane física contada uma vez. | Subconjunto pós-choque da janela de medição (passo >= passo de início do choque). | Máximo de network_total_queue sobre os passos de medição pós-choque. | Omitida somente se não existirem amostras de telemetria na janela (a run falha). | não |
| `pre_shock_mean_network_queue_vehicles` | vehicles | lane_telemetry.parquet / junction_telemetry.parquet canônicos (contagem de veículos parados do SUMO por lane de entrada ÚNICA, amostrada pelo runner da simulação para todo controlador). | Todos os veículos parados nas lanes de entrada; cada lane física contada uma vez. | Subconjunto pré-choque da janela de medição. | Média de network_total_queue sobre os passos de medição pré-choque. | Omitida somente se não existirem amostras de telemetria na janela (a run falha). | não |
| `pre_shock_max_network_queue_vehicles` | vehicles | lane_telemetry.parquet / junction_telemetry.parquet canônicos (contagem de veículos parados do SUMO por lane de entrada ÚNICA, amostrada pelo runner da simulação para todo controlador). | Todos os veículos parados nas lanes de entrada; cada lane física contada uma vez. | Subconjunto pré-choque da janela de medição. | Máximo de network_total_queue sobre os passos de medição pré-choque. | Omitida somente se não existirem amostras de telemetria na janela (a run falha). | não |
| `post_shock_queue_auc_vehicle_seconds` | vehicle-seconds | lane_telemetry.parquet canônico (contagens de veículos parados por lane única). | network_total_queue = soma sobre as lanes de entrada únicas; nunca linhas de movimento. | Subconjunto pós-choque da janela de medição. | Integral trapezoidal de network_total_queue sobre o tempo de simulação, do passo de início do choque até o último passo de medição: sum((Q_i + Q_{i+1}) / 2 * (t_{i+1} - t_i)), com t_i o timestamp de telemetria do passo i. | 0 se existirem menos de duas amostras pós-choque. | não |
| `internal_lane_persistence_events` | events | junction_telemetry.parquet canônico: veículos presentes nas lanes internas de uma interseção em dois passos consecutivos. | Veículos nas lanes internas das interseções. | Apenas os passos da janela de medição (warmup excluído); uma amostra por passo de simulação. | Soma sobre os passos de medição e as interseções (uma linha por interseção e por passo). Proxy da ocupação interna da interseção, não uma medida de spillback ou de gridlock. | Reportar 0 quando nenhum evento de persistência é observado. | não |
| `offered_by_entry` | vehicles | Arestas de entrada do arquivo de rotas (partidas agendadas). | Coorte de medição agrupada por aresta de entrada. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Exportada por aresta de entrada como `offered_by_entry__<entry_edge>`: veículos da coorte ofertados naquela entrada de borda. | 0 para uma entrada sem veículos ofertados. | não |
| `departed_by_entry` | vehicles | Arestas de entrada do arquivo de rotas combinadas com o tripinfo do SUMO. | Coorte de medição agrupada por aresta de entrada. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Exportada por aresta de entrada como `departed_by_entry__<entry_edge>`: veículos da coorte daquela entrada que foram inseridos. | 0 para uma entrada sem partidas. | não |
| `arrived_by_entry` | vehicles | Arestas de entrada do arquivo de rotas combinadas com o tripinfo do SUMO. | Coorte de medição agrupada por aresta de entrada. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Exportada por aresta de entrada como `arrived_by_entry__<entry_edge>`: veículos da coorte daquela entrada que chegaram antes do fim da run. | 0 para uma entrada sem chegadas. | não |
| `entry_departure_ratio` | ratio | Arestas de entrada do arquivo de rotas combinadas com o tripinfo do SUMO. | Coorte de medição agrupada por aresta de entrada. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Exportada por aresta de entrada como `entry_departure_ratio__<entry_edge>`: departed / offered naquela entrada; mostra se o padrão de demanda pretendido chega à rede ou é ocultado por starvation de inserção. | Reportada como 0.0 quando a entrada não ofertou veículos. | não |
| `min_entry_departure_ratio` | ratio | Arestas de entrada do arquivo de rotas combinadas com o tripinfo do SUMO. | Coorte de medição agrupada por aresta de entrada. | Janela de medição; coorte = veículos agendados para partir dentro de [warmup, warmup + measurement_duration). | Mínimo, sobre as arestas de entrada, de departed / offered (coorte). | 0.0 para uma entrada sem partidas. | não |
| `messages_sent` | messages | Métricas de comunicação do MessageBus. | Não depende de população. | Run simulada completa, incluindo o warmup, a menos que o relatório indique o contrário. | Total de mensagens publicadas pelos controladores cooperativos. | Para controladores que não se comunicam, reportar 0 ou omitir das tabelas de comunicação. | não |
| `messages_delivered` | messages | Métricas de comunicação do MessageBus. | Não depende de população. | Run simulada completa, incluindo o warmup, a menos que o relatório indique o contrário. | Total de mensagens entregues às caixas de entrada de destino. | Para controladores que não se comunicam, reportar 0 ou omitir das tabelas de comunicação. | não |
| `messages_dropped` | messages | Métricas de comunicação do MessageBus. | Não depende de população. | Run simulada completa, incluindo o warmup, a menos que o relatório indique o contrário. | Total de mensagens descartadas pelo processo de perda configurado. | Reportar 0 quando nenhum descarte é observado. | não |
| `messages_stale` | messages | Contabilização de atualidade das mensagens dos controladores cooperativos. | Não depende de população. | Run simulada completa, incluindo o warmup, a menos que o relatório indique o contrário. | Total de mensagens recebidas rejeitadas por estarem obsoletas (stale). | Reportar 0 quando nenhuma mensagem obsoleta é observada. | não |
| `bytes_sent` | bytes | Contabilização de mensagens serializadas do MessageBus. | Não depende de população. | Run simulada completa, incluindo o warmup, a menos que o relatório indique o contrário. | Total de bytes serializados publicados. | Reportar 0 quando nenhuma mensagem é enviada. | não |
| `bytes_delivered` | bytes | Contabilização de mensagens serializadas do MessageBus. | Não depende de população. | Run simulada completa, incluindo o warmup, a menos que o relatório indique o contrário. | Total de bytes serializados entregues. | Reportar 0 quando nenhuma mensagem é entregue. | não |
| `mean_message_age_steps` | simulation steps/message | Contabilização de atualidade das mensagens dos controladores cooperativos. | Não depende de população. | Run simulada completa, incluindo o warmup, a menos que o relatório indique o contrário. | Idade média aritmética das mensagens observadas. | Reportar 0 quando nenhuma mensagem é observada. | não |
| `max_message_age_steps` | simulation steps | Contabilização de atualidade das mensagens dos controladores cooperativos. | Não depende de população. | Run simulada completa, incluindo o warmup, a menos que o relatório indique o contrário. | Idade máxima observada das mensagens. | Reportar 0 quando nenhuma mensagem é observada. | não |
| `throughput_change_vs_zero_loss` | vehicles | Derivada das linhas de throughput agrupadas por cenário, controlador e seed. | Não depende de população. | Mesma janela de medição do throughput. | throughput(drop_probability=x) - throughput(drop_probability=0). | Exportada somente quando existe um baseline de perda zero para o mesmo cenário/controlador/seed. | não |

## Política do proxy de lane interna do S4

`internal_lane_persistence_events` é um proxy da ocupação persistente interna da interseção. É
o número de veículos presentes nas lanes internas de uma interseção em dois passos consecutivos,
somado sobre as interseções e os passos de medição (um valor por interseção e por passo; não
é replicado por movimento). Não é uma duração de spillback, uma duração de gridlock, nem uma
medição direta universal de interseções bloqueadas.

## Política da métrica derivada do S5

`throughput_change_vs_zero_loss` é uma comparação descritiva, dentro do mesmo controlador, contra a
condição de perda zero para o mesmo cenário e seed. Não descreva o valor como degradação
causada pela comunicação sem o contexto experimental completo e os controles.
