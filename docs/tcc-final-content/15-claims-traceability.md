# Rastreabilidade das afirmações (claims traceability)

> Gerado programaticamente: cada valor numérico do conteúdo acadêmico foi avaliado a partir de `artifacts/final-analysis/`
> (análise final validada, N = 10) no momento da geração. Colunas: afirmação (valor no texto), arquivo de origem do dado, cenário,
> comparação de controladores, métrica, N, figura/tabela correspondente e o arquivo onde a afirmação aparece. As cópias versionadas das
> tabelas-fonte estão em `docs/evidencias/final-analysis/`. Identidade científica: fonte `176178e36eeafb329a5a1350161be61cf97902b0`;
> manifesto `de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec`.

## A. Afirmações científicas qualitativas (classificação por cenário)

| Afirmação | Fonte | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| S1: B2 favorecido sobre B0 e C1 | `final_scenario_pair_classification.csv` | S1 — balanceado | B2 → C1 / B0 → B2 | classificação (serviço × atraso/fila) | 10 pares | FIG04, FIG05, FIG19, TABLE03 |
| S2: B2 → C1 é trade-off | `final_scenario_pair_classification.csv` | S2 — pico direcional | B2 → C1 / B0 → B2 | classificação (serviço × atraso/fila) | 10 pares | FIG04, FIG05, FIG19, TABLE03 |
| S3: B2 favorecido sobre C1; B0 favorecido sobre B2 | `final_scenario_pair_classification.csv` | S3 — mudança de demanda | B2 → C1 / B0 → B2 | classificação (serviço × atraso/fila) | 10 pares | FIG04, FIG05, FIG19, TABLE03 |
| S4: C1 favorecido sobre B2 (métricas de congestionamento) | `final_scenario_pair_classification.csv` | S4 — saturação localizada | B2 → C1 / B0 → B2 | classificação (serviço × atraso/fila) | 10 pares | FIG04, FIG05, FIG19, TABLE03 |
| B0 favorecido sobre B2 em S2, S3 e S4; B2 favorecido em S1 | `final_scenario_pair_classification.csv` | S1–S4 | B0 → B2 | classificação | 10 pares | FIG03, FIG19 |
| O efeito da cooperação depende do cenário (sem superioridade geral) | `final_analysis.md`/`final_analysis.json` | S1–S4 | B2 → C1 | classificação | 10 pares | FIG19, FIG20 |
| Degradação da comunicação não monotônica; 100% de perda iguala B2 | `s5_pairwise.csv`, `s5_results.parquet` | S5 (tráfego S2) | C1, C2 vs 0% e vs B2 | vazão e demais métricas de tráfego | 10 seeds | FIG14, FIG15, TABLE05 |
| Rede e rota em S3 apontam direções diferentes | `network_vs_reference_route_direction.csv` | S3 — mudança de demanda | B2 → C1 | tempo de viagem | 10 pares | FIG13 |
| Teleports em S4: concentrados no B0; nenhuma execução excluída | `final_analysis.json` (s4_teleports) | S4 — saturação localizada | B0, B2, B1, C1, C2 | sumo_teleports_total | 10 por controlador | FIG10 |
| S3: critério composto de validade é refinamento post-hoc | `docs/methodology/scenario-validity-gates.md` | S3 — mudança de demanda | — | validade do cenário | Pilot V2 (5 seeds do B0) | — |
| B0 final = EMPIRICAL_FIXED_TIME (ciclo 84 s, DEMAND_PROPORTIONAL, ALTERNATE, offsets 0/42 s); não Webster | `docs/methodology/fixed-time-calibration.md`; `experiments/fixed_time/b0_fixed_calibrated.json` | calibração (seeds 101/1009/2029; validação 3011/4021/5003) | — | plano de tempo fixo | — | TABLE01 |
| Direção persistiu em 50/51 comparações; nenhuma conclusão central revertida | `pilot_vs_final.csv` | S1–S4 | B2 → C1 (piloto vs final) | diferença relativa | piloto 5 / final 10 | FIG18, FIG18B |

## B. Afirmações numéricas (valores gerados a partir dos artefatos)

### `00-outline-final.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| +12,0% | `pilot_vs_final.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT (piloto vs final) | throughput | piloto 5 / final 10 | FIG18, FIG18B |
| +8,8% | `pilot_vs_final.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT (piloto vs final) | throughput | piloto 5 / final 10 | FIG18, FIG18B |

### `01-resumo.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| 200 | `analysis-validation.json` | — | — | FINAL_MAIN_RUNS_ANALYZED | 290 | — |
| 90 | `analysis-validation.json` | — | — | FINAL_S5_RUNS_ANALYZED | 290 | — |
| 290 | `analysis-validation.json` | — | — | TOTAL_FINAL_SCIENTIFIC_RUNS_ANALYZED | 290 | — |
| −15,2% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −18,3% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −5,7% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG06 |
| +8,8% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −19,5% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −17,3% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| 2,3 | `communication_overhead_ratio.csv` | FINAL_S5 S2_DIRECTIONAL_PEAK | C2/C1 | bytes_sent | 10 | FIG16, FIG17, TABLE06 |

### `02-abstract.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| 200 | `analysis-validation.json` | — | — | FINAL_MAIN_RUNS_ANALYZED | 290 | — |
| 90 | `analysis-validation.json` | — | — | FINAL_S5_RUNS_ANALYZED | 290 | — |
| 290 | `analysis-validation.json` | — | — | TOTAL_FINAL_SCIENTIFIC_RUNS_ANALYZED | 290 | — |
| −15,2% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −18,3% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −5,7% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG06 |
| +8,8% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −19,5% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −17,3% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| 2,3 | `communication_overhead_ratio.csv` | FINAL_S5 S2_DIRECTIONAL_PEAK | C2/C1 | bytes_sent | 10 | FIG16, FIG17, TABLE06 |

### `05-metodologia.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| 65–72% | `final_controller_summary.csv` | S4_LOCAL_SATURATION | B0–C2 | 1 − completion_ratio_offered | 10 | FIG02 |
| 93.600 | `s5_communication_summary.csv` | FINAL_S5 S2_DIRECTIONAL_PEAK | C1_COOPERATIVE_COMPACT@0.0 | mean_messages_sent | 10 | FIG16, FIG17, TABLE06 |
| 323 | `s5_communication_summary.csv` | S5 loss 0% | C1_COOPERATIVE_COMPACT | mean_bytes_per_message_sent | 10 | FIG16, FIG17, TABLE06 |
| 751 | `s5_communication_summary.csv` | S5 loss 0% | C2_COOPERATIVE_EXPANDED | mean_bytes_per_message_sent | 10 | FIG16, FIG17, TABLE06 |
| 200 | `analysis-validation.json` | — | — | FINAL_MAIN_RUNS_ANALYZED | 290 | — |
| 90 | `analysis-validation.json` | — | — | FINAL_S5_RUNS_ANALYZED | 290 | — |
| 11 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | todos | sumo_teleports_total | 50 | FIG10 |
| 31 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | todos | sumo_teleports_total | 50 | FIG10 |
| 28 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED | sumo_teleports_total | 10 | FIG10 |
| 3 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE | sumo_teleports_total | 10 | FIG10 |

### `07-validacao-experimental.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| 744 | `artifacts/tcc-content-validation/test_counts.json` | — | — | pytest_total | — | — |
| 744 | `artifacts/tcc-content-validation/test_counts.json` | — | — | pytest_passed | — | — |
| 120 | `artifacts/tcc-content-validation/test_counts.json` | — | — | pytest_seconds | — | — |
| Success: no issues found in 63 source files | `artifacts/tcc-content-validation/test_counts.json` | — | — | mypy | — | — |
| All checks passed (src, analysis, tests e scripts de congelamento/calibração/geração) | `artifacts/tcc-content-validation/test_counts.json` | — | — | ruff_check_scientific | — | — |
| 113 files already formatted (src, analysis, tests) | `artifacts/tcc-content-validation/test_counts.json` | — | — | ruff_format_scientific | — | — |
| 57/57 | `pilot_vs_final.csv` | todos | piloto vs final (5 primeiras seeds) | final_first5_identical_to_pilot | 5 | FIG18, FIG18B |
| 11 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | todos | sumo_teleports_total | 50 | FIG10 |
| 31 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | todos | sumo_teleports_total | 50 | FIG10 |

### `08-resultados.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| (tabela completa) | `final_controller_summary.csv` | S1_BALANCED | B0–C2 | resumo descritivo | 10 | FIG02 |
| (tabela completa) | `final_controller_summary.csv` | S2_DIRECTIONAL_PEAK | B0–C2 | resumo descritivo | 10 | FIG02 |
| (tabela completa) | `final_controller_summary.csv` | S3_DEMAND_SHIFT | B0–C2 | resumo descritivo | 10 | FIG02 |
| (tabela completa) | `final_controller_summary.csv` | S4_LOCAL_SATURATION | B0–C2 | resumo descritivo | 10 | FIG02 |
| (tabela completa) | `final_scenario_pair_classification.csv` | S1–S4 | 4 comparações congeladas | classificação | 10 | FIG05, FIG19 |
| −15,2% | `final_pairwise_summary.csv` | S1_BALANCED | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_waiting_time | 10 | FIG03, FIG19 |
| IC95% [−19,9%; −9,8%] | `final_pairwise_summary.csv` | S1_BALANCED | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_waiting_time | 10 | FIG03, FIG19 |
| −12,7% | `final_pairwise_summary.csv` | S1_BALANCED | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_time_loss | 10 | FIG03, FIG19 |
| −14,4% | `final_pairwise_summary.csv` | S1_BALANCED | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_network_queue_vehicles | 10 | FIG03, FIG19 |
| +0,3% | `final_pairwise_summary.csv` | S1_BALANCED | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | throughput | 10 | FIG03, FIG19 |
| +35,0% | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03 |
| IC95% [+29,2%; +41,0%] | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03 |
| +34,2% | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03 |
| IC95% [+28,4%; +40,2%] | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03 |
| +26,1% | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_time_loss | 10 | FIG04, FIG05, TABLE03 |
| −0,5 p.p. | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | completion_ratio_offered | 10 | FIG04, FIG05, TABLE03 |
| 0/10 | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03 |
| (tabela completa) | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | comparação pareada | 10 | FIG04, FIG05, TABLE03 |
| −15,2% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG06 |
| IC95% [−18,6%; −12,2%] | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −15,3% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_time_loss | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −18,3% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG06 |
| IC95% [−20,9%; −16,1%] | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −21,5% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | max_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG06 |
| 10/10 | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −5,7% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG06 |
| IC95% [−7,8%; −4,0%] | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −6,1 p.p. | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | departure_ratio | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −4,9 p.p. | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | completion_ratio_offered | 10 | FIG04, FIG05, TABLE03, FIG06 |
| 73,1 | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | never_inserted_vehicle_count | 10 | FIG04, FIG05, TABLE03, FIG06 |
| 211,9 | `final_controller_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE | never_inserted_vehicle_count | 10 | FIG02 |
| 285,0 | `final_controller_summary.csv` | S2_DIRECTIONAL_PEAK | C1_COOPERATIVE_COMPACT | never_inserted_vehicle_count | 10 | FIG02 |
| −18,9% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | throughput | 10 | FIG03, FIG19 |
| −20,5 p.p. | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | completion_ratio_offered | 10 | FIG03, FIG19 |
| +192,4% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_waiting_time | 10 | FIG03, FIG19 |
| +142,1% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_network_queue_vehicles | 10 | FIG03, FIG19 |
| 0,0 | `final_controller_summary.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED | never_inserted_vehicle_count | 10 | FIG02 |
| +26,4% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED→B1_LOCAL_ADAPTIVE | mean_waiting_time | 10 | FIG05 (classificação) |
| +26,9% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED→B1_LOCAL_ADAPTIVE | mean_network_queue_vehicles | 10 | FIG05 (classificação) |
| (tabela completa) | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | comparação pareada | 10 | FIG04, FIG05, TABLE03, FIG06 |
| +21,4% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| IC95% [+18,4%; +24,6%] | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| +18,5% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| −1,7% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| −1,7 p.p. | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | completion_ratio_offered | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| +13,5% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | post_shock_queue_auc_vehicle_seconds | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| IC95% [+11,2%; +16,2%] | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | post_shock_queue_auc_vehicle_seconds | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| 0/10 | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | post_shock_queue_auc_vehicle_seconds | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| 56,0 | `final_controller_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED | post_shock_mean_network_queue_vehicles | 10 | FIG02 |
| 64,1 | `final_controller_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE | post_shock_mean_network_queue_vehicles | 10 | FIG02 |
| 72,8 | `final_controller_summary.csv` | S3_DEMAND_SHIFT | C1_COOPERATIVE_COMPACT | post_shock_mean_network_queue_vehicles | 10 | FIG02 |
| −0,7 p.p. | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | completion_ratio_offered | 10 | FIG03, FIG19 |
| −1,0 p.p. | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | departure_ratio | 10 | FIG03, FIG19 |
| +8,6% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_waiting_time | 10 | FIG03, FIG19 |
| +5,0% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_network_queue_vehicles | 10 | FIG03, FIG19 |
| −0,6% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | throughput | 10 | FIG03, FIG19 |
| IC95% [−1,3%; +0,1%] | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | throughput | 10 | FIG03, FIG19 |
| +14,5% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | post_shock_queue_auc_vehicle_seconds | 10 | FIG03, FIG19 |
| IC95% [+9,5%; +19,7%] | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | post_shock_queue_auc_vehicle_seconds | 10 | FIG03, FIG19 |
| 100.739 | `final_controller_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED | post_shock_queue_auc_vehicle_seconds | 10 | FIG02 |
| 115.334 | `final_controller_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE | post_shock_queue_auc_vehicle_seconds | 10 | FIG02 |
| 130.943 | `final_controller_summary.csv` | S3_DEMAND_SHIFT | C1_COOPERATIVE_COMPACT | post_shock_queue_auc_vehicle_seconds | 10 | FIG02 |
| (tabela completa) | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | comparação pareada | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| +8,8% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| IC95% [+5,6%; +13,8%] | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −19,5% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| IC95% [−21,5%; −17,4%] | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −22,6% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_time_loss | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −17,3% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| IC95% [−18,4%; −16,2%] | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −21,0% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | max_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| +3,0 p.p. | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | completion_ratio_offered | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| 10/10 | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| +16,8% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_depart_delay_seconds | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| IC95% [+12,2%; +22,1%] | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_depart_delay_seconds | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| +0,2 p.p. | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | departure_ratio | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −8,9 | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | never_inserted_vehicle_count | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| 65–72% | `final_controller_summary.csv` | S4_LOCAL_SATURATION | B0–C2 | 1 − completion_ratio_offered | 10 | FIG02 |
| 0,277–0,352 | `final_controller_summary.csv` | S4_LOCAL_SATURATION | B0–C2 | completion_ratio_offered | 10 | FIG02 |
| 1.899–2.129 | `final_controller_summary.csv` | S4_LOCAL_SATURATION | B0–C2 | never_inserted_vehicle_count | 10 | FIG02 |
| −16,9% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | throughput | 10 | FIG03, FIG19 |
| +40,6% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_waiting_time | 10 | FIG03, FIG19 |
| 11 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | todos | sumo_teleports_total | 50 | FIG10 |
| 31 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | todos | sumo_teleports_total | 50 | FIG10 |
| 28 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED | sumo_teleports_total | 10 | FIG10 |
| 10 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED | sumo_teleports_total | 10 | FIG10 |
| 3 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE | sumo_teleports_total | 10 | FIG10 |
| 1 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE | sumo_teleports_total | 10 | FIG10 |
| (tabela completa) | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | comparação pareada | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| +187,4% | `final_pairwise_summary.csv` | S1_BALANCED | C1_COOPERATIVE_COMPACT→C2_COOPERATIVE_EXPANDED | mean_waiting_time | 10 | FIG17 |
| +121,2% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | C1_COOPERATIVE_COMPACT→C2_COOPERATIVE_EXPANDED | mean_waiting_time | 10 | FIG17 |
| −16,5% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | C1_COOPERATIVE_COMPACT→C2_COOPERATIVE_EXPANDED | mean_waiting_time | 10 | FIG17 |
| −13,7% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | C1_COOPERATIVE_COMPACT→C2_COOPERATIVE_EXPANDED | mean_network_queue_vehicles | 10 | FIG17 |
| +2,2% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | C1_COOPERATIVE_COMPACT→C2_COOPERATIVE_EXPANDED | throughput | 10 | FIG17 |
| +16,3% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | C1_COOPERATIVE_COMPACT→C2_COOPERATIVE_EXPANDED | mean_depart_delay_seconds | 10 | FIG17 |
| 52,0 | `reference_route_cohort_summary.csv` | S1_BALANCED | B0_FIXED_CALIBRATED | reference_route_offered | 10 | FIG11, FIG12, TABLE04 |
| 108,7 | `reference_route_cohort_summary.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED | reference_route_offered | 10 | FIG11, FIG12, TABLE04 |
| 113,1 | `reference_route_cohort_summary.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED | reference_route_offered | 10 | FIG11, FIG12, TABLE04 |
| 200,2 | `reference_route_cohort_summary.csv` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED | reference_route_offered | 10 | FIG11, FIG12, TABLE04 |
| (tabela completa) | `reference_route_pairwise.csv + reference_route_summary.csv` | S1–S4 | B0, B2, C1 | tempo de viagem e conclusão da rota | 10 | FIG11, FIG12, TABLE04 |
| −12,5 | `reference_route_pairwise.csv` | S1_BALANCED | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| [−16,9; −8,8] | `reference_route_pairwise.csv` | S1_BALANCED | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| −0,7 p.p. | `reference_route_pairwise.csv` | S1_BALANCED | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | reference_route_completion_ratio_offered | 10 | FIG11, FIG12, TABLE04 |
| +193,2 | `reference_route_pairwise.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| +52,0 | `reference_route_pairwise.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| +795,2 | `reference_route_pairwise.csv` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| −29,4 p.p. | `reference_route_pairwise.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | reference_route_completion_ratio_offered | 10 | FIG11, FIG12, TABLE04 |
| −4,1 p.p. | `reference_route_pairwise.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | reference_route_completion_ratio_offered | 10 | FIG11, FIG12, TABLE04 |
| −69,7 p.p. | `reference_route_pairwise.csv` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | reference_route_completion_ratio_offered | 10 | FIG11, FIG12, TABLE04 |
| 0,899 | `reference_route_summary.csv` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED | reference_route_completion_ratio_offered | 10 | FIG11, FIG12, TABLE04 |
| 0,202 | `reference_route_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE | reference_route_completion_ratio_offered | 10 | FIG11, FIG12, TABLE04 |
| +23,2 | `reference_route_pairwise.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| [+17,4; +28,9] | `reference_route_pairwise.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| −39,4 | `reference_route_pairwise.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| −46,2 | `reference_route_pairwise.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| −385,5 | `reference_route_pairwise.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| +9,1 p.p. | `reference_route_pairwise.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 10 | FIG11, FIG12, TABLE04 |
| 0,293 | `reference_route_summary.csv` | S4_LOCAL_SATURATION | C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 10 | FIG11, FIG12, TABLE04 |
| +15,9 | `network_vs_reference_route_direction.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE->C1_COOPERATIVE_COMPACT | network_mean_travel_time_diff | 10 | FIG13 |
| [−54,4; −33,9] | `reference_route_pairwise.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 10 | FIG11, FIG12, TABLE04 |
| +0,9 p.p. | `reference_route_pairwise.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 10 | FIG11, FIG12, TABLE04 |
| 2.019 | `final_controller_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE | offered_vehicle_count | 10 | FIG02 |
| 113,1 | `reference_route_cohort_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE | reference_route_offered | 10 | FIG11, FIG12, TABLE04 |
| 19,9% | `s5_communication_summary.csv` | S5 | loss 0.2 | observed_drop_ratio_min | 20 | FIG16, FIG17, TABLE06 |
| 20,2% | `s5_communication_summary.csv` | S5 | loss 0.2 | observed_drop_ratio_max | 20 | FIG16, FIG17, TABLE06 |
| 49,7% | `s5_communication_summary.csv` | S5 | loss 0.5 | observed_drop_ratio_min | 20 | FIG16, FIG17, TABLE06 |
| 50,2% | `s5_communication_summary.csv` | S5 | loss 0.5 | observed_drop_ratio_max | 20 | FIG16, FIG17, TABLE06 |
| 1.872.000 | `s5_communication_summary.csv` | S5 loss 100% | C1+C2 | total_messages_sent | 20 | FIG16, FIG17, TABLE06 |
| 1.872.000 | `s5_communication_summary.csv` | S5 loss 100% | C1+C2 | total_messages_dropped | 20 | FIG16, FIG17, TABLE06 |
| 0 | `communication_by_run.csv` | S5 loss 100% | C1+C2 | bytes_delivered | 20 | FIG16, FIG17, TABLE06 |
| (tabela completa) | `s5_pairwise.csv` | S5 (tráfego S2) | degradação vs 0% | variação relativa | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| +8,6% | `s5_pairwise.csv` | S5 (tráfego S2) | C1_COOPERATIVE_COMPACT@0.00→C1_COOPERATIVE_COMPACT@0.20 | throughput | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| +10,3% | `s5_pairwise.csv` | S5 (tráfego S2) | C1_COOPERATIVE_COMPACT@0.00→C1_COOPERATIVE_COMPACT@0.50 | throughput | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| +2,7% | `s5_pairwise.csv` | S5 (tráfego S2) | C1_COOPERATIVE_COMPACT@0.00→C1_COOPERATIVE_COMPACT@0.20 | mean_network_queue_vehicles | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| +6,7% | `s5_pairwise.csv` | S5 (tráfego S2) | C1_COOPERATIVE_COMPACT@0.00→C1_COOPERATIVE_COMPACT@0.50 | mean_network_queue_vehicles | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| +15,9% | `s5_pairwise.csv` | S5 (tráfego S2) | C2_COOPERATIVE_EXPANDED@0.00→C2_COOPERATIVE_EXPANDED@0.20 | throughput | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| +19,5% | `s5_pairwise.csv` | S5 (tráfego S2) | C2_COOPERATIVE_EXPANDED@0.00→C2_COOPERATIVE_EXPANDED@0.50 | throughput | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| −13,9% | `s5_pairwise.csv` | S5 (tráfego S2) | C2_COOPERATIVE_EXPANDED@0.00→C2_COOPERATIVE_EXPANDED@0.20 | mean_waiting_time | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| −14,3% | `s5_pairwise.csv` | S5 (tráfego S2) | C2_COOPERATIVE_EXPANDED@0.00→C2_COOPERATIVE_EXPANDED@0.50 | mean_waiting_time | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| 380/380 | `s5_results.parquet` | S5 loss 100% | C1,C2 vs B2 (mesma seed) | métricas de tráfego idênticas | 20 | FIG14, FIG14B, FIG15, TABLE05 |
| +2,4% | `s5_pairwise.csv` | S5 (tráfego S2) | B2@REF→C1_COOPERATIVE_COMPACT@0.20 | throughput | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| −18,0% | `s5_pairwise.csv` | S5 (tráfego S2) | B2@REF→C1_COOPERATIVE_COMPACT@0.20 | mean_waiting_time | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| −5,7% | `s5_pairwise.csv` | S5 (tráfego S2) | B2@REF→C1_COOPERATIVE_COMPACT@0.00 | throughput | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| −15,2% | `s5_pairwise.csv` | S5 (tráfego S2) | B2@REF→C1_COOPERATIVE_COMPACT@0.00 | mean_waiting_time | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| −13,5% | `s5_pairwise.csv` | S5 (tráfego S2) | B2@REF→C2_COOPERATIVE_EXPANDED@0.00 | throughput | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| (tabela completa) | `s5_controller_summary.csv + s5_communication_summary.csv` | S5 (tráfego S2) | B2, C1, C2 | resumo S5 | 10 | FIG14, FIG14B, FIG15, TABLE05 |
| 93.600 | `s5_communication_summary.csv` | FINAL_S5 S2_DIRECTIONAL_PEAK | C1_COOPERATIVE_COMPACT@0.0 | mean_messages_sent | 10 | FIG16, FIG17, TABLE06 |
| 93.600 | `s5_communication_summary.csv` | FINAL_S5 S2_DIRECTIONAL_PEAK | C2_COOPERATIVE_EXPANDED@0.0 | mean_messages_sent | 10 | FIG16, FIG17, TABLE06 |
| (tabela completa) | `s5_communication_summary.csv` | S5 loss 0% | C1, C2 | custo de comunicação | 10 | FIG16, FIG17, TABLE06 |
| 2,32 | `communication_overhead_ratio.csv` | FINAL_S5 S2_DIRECTIONAL_PEAK | C2/C1 | bytes_sent | 10 | FIG16, FIG17, TABLE06 |
| 2,27–2,36 | `communication_overhead_ratio.csv` | todos | C2/C1 | bytes_sent | 10 | FIG16, FIG17, TABLE06 |
| 57/57 | `pilot_vs_final.csv` | todos | piloto vs final (5 primeiras seeds) | final_first5_identical_to_pilot | 5 | FIG18, FIG18B |
| (tabela completa) | `pilot_vs_final.csv` | S1–S4 | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | piloto vs final | 5/10 | FIG18, FIG18B |
| 50/51 | `pilot_vs_final.csv` | todos | piloto vs final | direction_persisted | piloto 5 / final 10 | FIG18, FIG18B |
| 2 | `pilot_vs_final.csv` | todos | piloto vs final | verdict_changed | piloto 5 / final 10 | FIG18, FIG18B |
| S1 vazão (veículos concluídos); S2 atraso de partida médio (s) | `pilot_vs_final.csv` | todos | piloto vs final | verdict_changed | piloto 5 / final 10 | FIG18, FIG18B |
| +12,0% | `pilot_vs_final.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT (piloto vs final) | throughput | piloto 5 / final 10 | FIG18, FIG18B |
| +8,8% | `pilot_vs_final.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT (piloto vs final) | throughput | piloto 5 / final 10 | FIG18, FIG18B |
| 0,65 | `pilot_vs_final.csv` | S2_DIRECTIONAL_PEAK | final/piloto | throughput | 5/10 | FIG18, FIG18B |
| 0,64 | `pilot_vs_final.csv` | S3_DEMAND_SHIFT | final/piloto | throughput | 5/10 | FIG18, FIG18B |
| 0,53 | `pilot_vs_final.csv` | S4_LOCAL_SATURATION | final/piloto | throughput | 5/10 | FIG18, FIG18B |

### `09-discussao.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| B0 favorecido | `final_scenario_pair_classification.csv` | S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | classificação (métricas de serviço × atraso/fila) | 10 pares | FIG05, FIG19 |
| B0 favorecido | `final_scenario_pair_classification.csv` | S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | classificação (métricas de serviço × atraso/fila) | 10 pares | FIG05, FIG19 |
| B0 favorecido | `final_scenario_pair_classification.csv` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | classificação (métricas de serviço × atraso/fila) | 10 pares | FIG05, FIG19 |
| −15,2% | `final_pairwise_summary.csv` | S1_BALANCED | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_waiting_time | 10 | FIG03, FIG19 |
| −14,4% | `final_pairwise_summary.csv` | S1_BALANCED | B0_FIXED_CALIBRATED→B2_LOCAL_PRESSURE | mean_network_queue_vehicles | 10 | FIG03, FIG19 |
| +8,8% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −19,5% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −17,3% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| +9,1 p.p. | `reference_route_pairwise.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 10 | FIG11, FIG12, TABLE04 |
| +35,0% | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03 |
| +34,2% | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03 |
| +21,4% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| +18,5% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| +13,5% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | post_shock_queue_auc_vehicle_seconds | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| 2,3 | `communication_overhead_ratio.csv` | FINAL_S5 S2_DIRECTIONAL_PEAK | C2/C1 | bytes_sent | 10 | FIG16, FIG17, TABLE06 |
| +187,4% | `final_pairwise_summary.csv` | S1_BALANCED | C1_COOPERATIVE_COMPACT→C2_COOPERATIVE_EXPANDED | mean_waiting_time | 10 | FIG17 |
| +121,2% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | C1_COOPERATIVE_COMPACT→C2_COOPERATIVE_EXPANDED | mean_waiting_time | 10 | FIG17 |
| 28 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED | sumo_teleports_total | 10 | FIG10 |
| 31 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | todos | sumo_teleports_total | 50 | FIG10 |

### `10-limitacoes.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| 65–72% | `final_controller_summary.csv` | S4_LOCAL_SATURATION | B0–C2 | 1 − completion_ratio_offered | 10 | FIG02 |
| 31 | `final_analysis.json (s4_teleports)` | S4_LOCAL_SATURATION | todos | sumo_teleports_total | 50 | FIG10 |

### `12-conclusao.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| +35,0% | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03 |
| +34,2% | `final_pairwise_summary.csv` | S1_BALANCED | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03 |
| −15,2% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −18,3% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −5,7% | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG06 |
| −4,9 p.p. | `final_pairwise_summary.csv` | S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | completion_ratio_offered | 10 | FIG04, FIG05, TABLE03, FIG06 |
| +21,4% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| +18,5% | `final_pairwise_summary.csv` | S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG07/FIG08 |
| +8,8% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | throughput | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −19,5% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_waiting_time | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| −17,3% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_network_queue_vehicles | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| +16,8% | `final_pairwise_summary.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT | mean_depart_delay_seconds | 10 | FIG04, FIG05, TABLE03, FIG09/FIG10 |
| 2,3 | `communication_overhead_ratio.csv` | FINAL_S5 S2_DIRECTIONAL_PEAK | C2/C1 | bytes_sent | 10 | FIG16, FIG17, TABLE06 |
| 50/51 | `pilot_vs_final.csv` | todos | piloto vs final | direction_persisted | piloto 5 / final 10 | FIG18, FIG18B |
| +12,0% | `pilot_vs_final.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT (piloto vs final) | throughput | piloto 5 / final 10 | FIG18, FIG18B |
| +8,8% | `pilot_vs_final.csv` | S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE→C1_COOPERATIVE_COMPACT (piloto vs final) | throughput | piloto 5 / final 10 | FIG18, FIG18B |

### `13-figure-table-placement.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| / Figura/Tabela / Seção sugerida / Capítulo / Papel / N / Arquivo vetorial (PDF) /
/---/---/---/---/---/---/
/ `FIG01_FINAL_OVERVIEW` / 3.2 Rede e visão gera... | `artifacts/tcc-visuals/final/figure-manifest.json` | — | — | figuras e tabelas | — | — |

### `14-advisor-checklist-final.md`

| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |
|---|---|---|---|---|---|---|
| 200/200 | `analysis-validation.json` | — | — | FINAL_MAIN_RUNS_ANALYZED | 290 | — |
| 90/90 | `analysis-validation.json` | — | — | FINAL_S5_RUNS_ANALYZED | 290 | — |
| 290/290 | `analysis-validation.json` | — | — | TOTAL_FINAL_SCIENTIFIC_RUNS_ANALYZED | 290 | — |
