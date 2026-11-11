> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/b2-vs-c1-final-comparison.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado abaixo (texto traduzido para português, sem alteração de números ou conclusões).

# B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT: comparação pareada do Pilot V2 (Prompt 50)

`campaign_role: PILOT`. Análise descritiva com 5 seeds; não é um resultado final, nem um teste de significância, sem ranking ou ajuste de controladores. O Pilot V1 não é usado.

## 1. Contexto da liberação

- Pilot V2: 100 execuções (4 cenários x 5 seeds x 5 controladores), 100 concluídas, 0 falhas, `metrics_finalized=true` em todas.
- S1, S2, S4 válidos (Prompt 46.8). S3 válido no gate composto (Prompts 47/48): 5/5 seeds válidas, seed 4517 `VALID_WITH_DIAGNOSTIC_WARNING`. Política do S4 `ALLOW_AND_MEASURE`. Decisão de liberação: `pilot-v2-release-decision.md` (Prompt 49).
- A antiga regra de 360 s NÃO foi usada para bloquear esta comparação; ela permanece como diagnóstico (a seed 4517 falha nela: variação projetada 6,51 veíc vs limite 5,00).

## 2. Dados utilizados

- `combined_metrics.parquet` de `artifacts/experiments/pilot_v2` (pipeline `experiment aggregate` do projeto), apenas os controladores `B2_LOCAL_PRESSURE` e `C1_COOPERATIVE_COMPACT`, 20 pares (cenário, seed). Nada foi recalculado a partir da telemetria; nenhuma nova simulação; repositório intocado.
- Valores completos por par e todos os resumos: `b2-vs-c1-final-comparison-table.csv`; sensibilidade: `b2-vs-c1-seed-sensitivity.csv`.

## 3. Método

- Pareamento: mesmo cenário, mesma seed (mesma rede, arquivo de rotas e demanda; a coorte ofertada é idêntica para os dois controladores). Diferença = C1 - B2.
- Por métrica: médias, diferença absoluta e percentual (relativa à média do B2), mediana, dp e IQR das diferenças pareadas, dp entre seeds de cada controlador, número de seeds em que o C1 é melhor, IC 95% bootstrap por percentil pareado da diferença média (10000 reamostragens, seed 20260930). Com n = 5 por cenário (n = 20 agrupado), os intervalos são descritivos.
- Direção: menor é melhor para espera, perda de tempo, tempo de viagem, fila, paradas, atraso de partida, nunca inseridos, não finalizados e teleportes; maior é melhor para throughput, chegados, partidos e razões de conclusão/partida.
- Regra de interpretação (declarada antes dos números): uma célula (cenário, métrica primária) é FAV se a diferença média é favorável e >= 4/5 seeds são favoráveis (UNFAV simétrico). POSITIVE: nenhuma UNFAV e >= 16 de 24 células FAV; NEGATIVE: nenhuma FAV e >= 16 UNFAV; INCONCLUSIVE: FAV + UNFAV < 8; caso contrário MIXED.

## 4. Resultados por cenário (leitura mais interpretável; n = 5 pares cada)

### S1_BALANCED

| métrica | média B2 | média C1 | dif. (C1-B2) | dif. % | efeito | seeds com C1 melhor | dif. mediana | dp da dif. | IC 95% (dif. média) | célula |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean_waiting_time | 46.765 | 67.678 | 20.913 | 44.7% | C1_worse | 0/5 | 21.793 | 4.070 | [17.763, 24.004] | UNFAV |
| mean_time_loss | 66.151 | 87.716 | 21.566 | 32.6% | C1_worse | 0/5 | 21.934 | 4.269 | [18.163, 24.809] | UNFAV |
| throughput | 1811.000 | 1806.800 | -4.200 | -0.2% | C1_worse | 2/5 | -8.000 | 7.918 | [-10.000, 2.600] | NEUTRAL |
| mean_network_queue_vehicles | 23.795 | 34.296 | 10.501 | 44.1% | C1_worse | 0/5 | 11.012 | 1.946 | [9.084, 11.926] | UNFAV |
| mean_travel_time | 119.332 | 140.865 | 21.534 | 18.0% | C1_worse | 0/5 | 21.947 | 4.268 | [18.432, 24.748] | UNFAV |
| completion_ratio_offered | 0.970 | 0.965 | -0.006 | -0.6% | C1_worse | 0/5 | -0.005 | 0.002 | [-0.007, -0.004] | UNFAV |
| completion_ratio_departed | 0.970 | 0.965 | -0.006 | -0.6% | C1_worse | 0/5 | -0.005 | 0.002 | [-0.007, -0.004] |  |
| departure_ratio | 1.000 | 1.000 | 0.000 | 0.0% | no_difference | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| offered_vehicle_count | 1794.200 | 1794.200 | 0.000 | 0.0% | neutral_metric | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| departed_vehicle_count | 1794.200 | 1794.200 | 0.000 | 0.0% | no_difference | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| arrived_vehicle_count | 1740.600 | 1730.600 | -10.000 | -0.6% | C1_worse | 0/5 | -9.000 | 3.317 | [-12.600, -7.400] |  |
| never_inserted_vehicle_count | 0.000 | 0.000 | 0.000 | nan% | no_difference | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| unfinished_in_network_count | 53.600 | 63.600 | 10.000 | 18.7% | C1_worse | 0/5 | 9.000 | 3.317 | [7.400, 12.600] |  |
| mean_depart_delay_seconds | 0.495 | 0.495 | 0.000 | 0.0% | no_difference | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| mean_stops | 2.441 | 2.598 | 0.157 | 6.4% | C1_worse | 0/5 | 0.177 | 0.073 | [0.101, 0.212] |  |
| max_network_queue_vehicles | 40.400 | 51.400 | 11.000 | 27.2% | C1_worse | 0/5 | 10.000 | 1.414 | [10.000, 12.200] |  |
| max_lane_queue_vehicles | 7.200 | 8.200 | 1.000 | 13.9% | C1_worse | 0/5 | 1.000 | 1.225 | [0.200, 2.000] |  |
| internal_lane_persistence_events | 3798.800 | 3829.800 | 31.000 | 0.8% | C1_worse | 2/5 | 12.000 | 68.096 | [-18.800, 87.800] |  |
| sumo_teleports_total | 0.000 | 0.000 | 0.000 | nan% | no_difference | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| corridor_throughput | 105.000 | 104.400 | -0.600 | -0.6% | C1_worse | 2/5 | -1.000 | 1.517 | [-1.800, 0.600] |  |
| corridor_mean_travel_time | 147.046 | 175.841 | 28.795 | 19.6% | C1_worse | 0/5 | 32.022 | 6.747 | [22.648, 32.873] |  |

### S2_DIRECTIONAL_PEAK

| métrica | média B2 | média C1 | dif. (C1-B2) | dif. % | efeito | seeds com C1 melhor | dif. mediana | dp da dif. | IC 95% (dif. média) | célula |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean_waiting_time | 164.483 | 143.524 | -20.959 | -12.7% | C1_better | 5/5 | -17.523 | 6.734 | [-26.290, -15.873] | FAV |
| mean_time_loss | 195.770 | 170.168 | -25.602 | -13.1% | C1_better | 5/5 | -21.984 | 7.150 | [-31.239, -20.196] | FAV |
| throughput | 976.600 | 916.800 | -59.800 | -6.1% | C1_worse | 0/5 | -47.000 | 37.838 | [-92.000, -35.400] | UNFAV |
| mean_network_queue_vehicles | 45.745 | 38.293 | -7.453 | -16.3% | C1_better | 5/5 | -7.714 | 1.277 | [-8.440, -6.461] | FAV |
| mean_travel_time | 248.298 | 222.769 | -25.529 | -10.3% | C1_better | 5/5 | -22.184 | 6.898 | [-30.918, -20.293] | FAV |
| completion_ratio_offered | 0.766 | 0.714 | -0.052 | -6.8% | C1_worse | 0/5 | -0.047 | 0.032 | [-0.080, -0.030] | UNFAV |
| completion_ratio_departed | 0.935 | 0.942 | 0.007 | 0.8% | C1_better | 4/5 | 0.006 | 0.006 | [0.003, 0.012] |  |
| departure_ratio | 0.820 | 0.758 | -0.062 | -7.5% | C1_worse | 0/5 | -0.063 | 0.031 | [-0.087, -0.039] |  |
| offered_vehicle_count | 1191.000 | 1191.000 | 0.000 | 0.0% | neutral_metric | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| departed_vehicle_count | 976.400 | 902.800 | -73.600 | -7.5% | C1_worse | 0/5 | -75.000 | 37.454 | [-103.600, -46.600] |  |
| arrived_vehicle_count | 912.600 | 850.200 | -62.400 | -6.8% | C1_worse | 0/5 | -56.000 | 38.585 | [-95.600, -35.200] |  |
| never_inserted_vehicle_count | 214.600 | 288.200 | 73.600 | 34.3% | C1_worse | 0/5 | 75.000 | 37.454 | [46.000, 103.600] |  |
| unfinished_in_network_count | 63.800 | 52.600 | -11.200 | -17.6% | C1_better | 5/5 | -11.000 | 4.712 | [-15.200, -8.000] |  |
| mean_depart_delay_seconds | 278.735 | 298.958 | 20.223 | 7.3% | C1_worse | 2/5 | 12.556 | 28.351 | [-0.775, 42.452] |  |
| mean_stops | 3.559 | 3.087 | -0.472 | -13.3% | C1_better | 5/5 | -0.472 | 0.055 | [-0.517, -0.436] |  |
| max_network_queue_vehicles | 75.600 | 58.800 | -16.800 | -22.2% | C1_better | 5/5 | -16.000 | 4.494 | [-20.200, -13.400] |  |
| max_lane_queue_vehicles | 16.600 | 11.400 | -5.200 | -31.3% | C1_better | 5/5 | -5.000 | 1.924 | [-6.800, -3.800] |  |
| internal_lane_persistence_events | 1864.800 | 1714.000 | -150.800 | -8.1% | C1_better | 5/5 | -137.000 | 46.510 | [-191.630, -124.200] |  |
| sumo_teleports_total | 0.000 | 0.000 | 0.000 | nan% | no_difference | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| corridor_throughput | 127.000 | 121.200 | -5.800 | -4.6% | C1_worse | 3/5 | 1.000 | 16.589 | [-20.000, 5.800] |  |
| corridor_mean_travel_time | 345.453 | 306.146 | -39.307 | -11.4% | C1_better | 5/5 | -48.810 | 24.713 | [-58.016, -19.183] |  |

### S3_DEMAND_SHIFT

| métrica | média B2 | média C1 | dif. (C1-B2) | dif. % | efeito | seeds com C1 melhor | dif. mediana | dp da dif. | IC 95% (dif. média) | célula |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean_waiting_time | 76.696 | 95.656 | 18.960 | 24.7% | C1_worse | 0/5 | 21.011 | 4.571 | [15.293, 22.270] | UNFAV |
| mean_time_loss | 102.601 | 120.737 | 18.136 | 17.7% | C1_worse | 0/5 | 20.358 | 5.254 | [13.952, 21.881] | UNFAV |
| throughput | 1943.000 | 1911.200 | -31.800 | -1.6% | C1_worse | 0/5 | -31.000 | 11.883 | [-40.600, -22.600] | UNFAV |
| mean_network_queue_vehicles | 43.926 | 53.528 | 9.602 | 21.9% | C1_worse | 0/5 | 10.565 | 2.566 | [7.428, 11.499] | UNFAV |
| mean_travel_time | 156.992 | 175.041 | 18.049 | 11.5% | C1_worse | 0/5 | 20.212 | 5.302 | [13.368, 21.836] | UNFAV |
| completion_ratio_offered | 0.927 | 0.909 | -0.019 | -2.0% | C1_worse | 0/5 | -0.019 | 0.004 | [-0.022, -0.016] | UNFAV |
| completion_ratio_departed | 0.938 | 0.932 | -0.007 | -0.7% | C1_worse | 0/5 | -0.006 | 0.003 | [-0.009, -0.005] |  |
| departure_ratio | 0.988 | 0.975 | -0.013 | -1.3% | C1_worse | 0/5 | -0.013 | 0.002 | [-0.014, -0.011] |  |
| offered_vehicle_count | 2019.200 | 2019.200 | 0.000 | 0.0% | neutral_metric | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| departed_vehicle_count | 1995.400 | 1969.400 | -26.000 | -1.3% | C1_worse | 0/5 | -27.000 | 4.062 | [-29.000, -22.600] |  |
| arrived_vehicle_count | 1872.600 | 1835.000 | -37.600 | -2.0% | C1_worse | 0/5 | -39.000 | 7.987 | [-43.600, -31.600] |  |
| never_inserted_vehicle_count | 23.800 | 49.800 | 26.000 | 109.2% | C1_worse | 0/5 | 27.000 | 4.062 | [22.600, 29.000] |  |
| unfinished_in_network_count | 122.800 | 134.400 | 11.600 | 9.4% | C1_worse | 0/5 | 11.000 | 5.550 | [7.400, 16.400] |  |
| mean_depart_delay_seconds | 6.223 | 13.559 | 7.336 | 117.9% | C1_worse | 0/5 | 6.928 | 2.440 | [5.501, 9.170] |  |
| mean_stops | 3.071 | 3.072 | 0.001 | 0.0% | C1_worse | 2/5 | 0.010 | 0.065 | [-0.055, 0.052] |  |
| max_network_queue_vehicles | 100.800 | 110.600 | 9.800 | 9.7% | C1_worse | 0/5 | 10.000 | 8.379 | [3.200, 16.400] |  |
| max_lane_queue_vehicles | 21.200 | 18.200 | -3.000 | -14.2% | C1_better | 5/5 | -3.000 | 1.581 | [-4.200, -1.800] |  |
| internal_lane_persistence_events | 4097.600 | 4014.800 | -82.800 | -2.0% | C1_better | 5/5 | -79.000 | 51.742 | [-120.200, -40.400] |  |
| sumo_teleports_total | 0.000 | 0.000 | 0.000 | nan% | no_difference | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| corridor_throughput | 196.400 | 195.400 | -1.000 | -0.5% | C1_worse | 2/5 | 0.000 | 6.595 | [-6.800, 3.400] |  |
| corridor_mean_travel_time | 313.754 | 268.650 | -45.104 | -14.4% | C1_better | 5/5 | -56.447 | 24.910 | [-59.271, -23.025] |  |
| post_shock_queue_auc_vehicle_seconds | 115239.700 | 131035.400 | 15795.700 | 13.7% | C1_worse | 0/5 | 14945.000 | 6811.959 | [11159.400, 21614.400] |  |
| post_shock_time_loss | 135.819 | 151.490 | 15.671 | 11.5% | C1_worse | 0/5 | 14.692 | 7.643 | [10.641, 22.277] |  |

### S4_LOCAL_SATURATION

| métrica | média B2 | média C1 | dif. (C1-B2) | dif. % | efeito | seeds com C1 melhor | dif. mediana | dp da dif. | IC 95% (dif. média) | célula |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean_waiting_time | 927.859 | 738.192 | -189.668 | -20.4% | C1_better | 5/5 | -195.635 | 24.183 | [-205.963, -168.610] | FAV |
| mean_time_loss | 1166.235 | 894.312 | -271.923 | -23.3% | C1_better | 5/5 | -278.618 | 26.867 | [-288.520, -247.894] | FAV |
| throughput | 1187.200 | 1329.800 | 142.600 | 12.0% | C1_better | 5/5 | 107.000 | 130.397 | [68.600, 258.800] | FAV |
| mean_network_queue_vehicles | 358.716 | 295.096 | -63.620 | -17.7% | C1_better | 5/5 | -63.676 | 8.386 | [-70.506, -57.397] | FAV |
| mean_travel_time | 1230.185 | 958.108 | -272.077 | -22.1% | C1_better | 5/5 | -278.449 | 27.081 | [-288.874, -247.363] | FAV |
| completion_ratio_offered | 0.265 | 0.306 | 0.041 | 15.3% | C1_better | 5/5 | 0.031 | 0.037 | [0.019, 0.073] | FAV |
| completion_ratio_departed | 0.664 | 0.741 | 0.077 | 11.6% | C1_better | 5/5 | 0.066 | 0.034 | [0.056, 0.107] |  |
| departure_ratio | 0.398 | 0.413 | 0.015 | 3.7% | C1_better | 3/5 | 0.004 | 0.038 | [-0.006, 0.048] |  |
| offered_vehicle_count | 3587.200 | 3587.200 | 0.000 | 0.0% | neutral_metric | 0/5 | 0.000 | 0.000 | [0.000, 0.000] |  |
| departed_vehicle_count | 1427.400 | 1479.800 | 52.400 | 3.7% | C1_better | 3/5 | 16.000 | 134.666 | [-22.400, 171.400] |  |
| arrived_vehicle_count | 951.000 | 1096.400 | 145.400 | 15.3% | C1_better | 5/5 | 112.000 | 131.963 | [67.200, 263.400] |  |
| never_inserted_vehicle_count | 2159.800 | 2107.400 | -52.400 | -2.4% | C1_better | 3/5 | -16.000 | 134.666 | [-171.400, 22.400] |  |
| unfinished_in_network_count | 476.400 | 383.400 | -93.000 | -19.5% | C1_better | 5/5 | -91.000 | 10.512 | [-101.400, -85.000] |  |
| mean_depart_delay_seconds | 709.282 | 852.606 | 143.324 | 20.2% | C1_worse | 0/5 | 97.898 | 80.457 | [84.442, 211.612] |  |
| mean_stops | 26.306 | 16.731 | -9.575 | -36.4% | C1_better | 5/5 | -9.405 | 1.110 | [-10.433, -8.718] |  |
| max_network_queue_vehicles | 456.000 | 353.000 | -103.000 | -22.6% | C1_better | 5/5 | -103.000 | 5.916 | [-107.600, -98.000] |  |
| max_lane_queue_vehicles | 32.000 | 31.000 | -1.000 | -3.1% | C1_better | 5/5 | -1.000 | 0.000 | [-1.000, -1.000] |  |
| internal_lane_persistence_events | 6983.800 | 3900.200 | -3083.600 | -44.2% | C1_better | 5/5 | -3043.000 | 581.487 | [-3562.000, -2611.000] |  |
| sumo_teleports_total | 0.600 | 0.000 | -0.600 | -100.0% | C1_better | 1/5 | 0.000 | 1.342 | [-1.800, 0.000] |  |
| corridor_throughput | 209.000 | 239.200 | 30.200 | 14.4% | C1_better | 5/5 | 30.000 | 15.611 | [18.600, 42.800] |  |
| corridor_mean_travel_time | 1384.350 | 984.206 | -400.144 | -28.9% | C1_better | 5/5 | -379.772 | 115.783 | [-492.038, -313.177] |  |

Salvaguarda contra viés de sobrevivência: tempo de espera, perda de tempo, tempo de viagem e paradas são condicionais à conclusão. Leia-os junto com `offered_vehicle_count`, `departed_vehicle_count`, `arrived_vehicle_count`, `completion_ratio_*` e `departure_ratio` mostrados em cada tabela acima (o ofertado é idêntico para os dois controladores dentro de um par).

## 5. Leitura agregada (20 pares agrupados; mistura regimes, menos interpretável)

| métrica | média B2 | média C1 | dif. (C1-B2) | dif. % | efeito | seeds com C1 melhor | dif. mediana | dp da dif. | IC 95% (dif. média) | célula |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean_waiting_time | 303.951 | 261.262 | -42.688 | -14.0% | C1_better | 10/20 | -1.536 | 89.523 | [-82.308, -6.796] |  |
| mean_time_loss | 382.689 | 318.233 | -64.456 | -16.8% | C1_better | 10/20 | -4.703 | 125.056 | [-120.878, -15.245] |  |
| throughput | 1479.450 | 1491.150 | 11.700 | 0.8% | C1_better | 7/20 | -13.500 | 101.700 | [-25.401, 59.750] |  |
| mean_network_queue_vehicles | 118.046 | 105.303 | -12.742 | -10.8% | C1_better | 10/20 | 0.053 | 31.296 | [-26.941, -0.315] |  |
| mean_travel_time | 438.702 | 374.196 | -64.506 | -14.7% | C1_better | 10/20 | -4.855 | 125.116 | [-121.316, -15.830] |  |
| completion_ratio_offered | 0.732 | 0.723 | -0.009 | -1.2% | C1_worse | 5/20 | -0.011 | 0.041 | [-0.026, 0.009] |  |
| completion_ratio_departed | 0.877 | 0.895 | 0.018 | 2.1% | C1_better | 9/20 | -0.002 | 0.039 | [0.003, 0.036] |  |
| departure_ratio | 0.801 | 0.786 | -0.015 | -1.9% | C1_worse | 3/20 | -0.010 | 0.037 | [-0.031, 0.001] |  |
| offered_vehicle_count | 2147.900 | 2147.900 | 0.000 | 0.0% | neutral_metric | 0/20 | 0.000 | 0.000 | [0.000, 0.000] |  |
| departed_vehicle_count | 1548.350 | 1536.550 | -11.800 | -0.8% | C1_worse | 3/20 | -25.500 | 79.348 | [-39.950, 27.252] |  |
| arrived_vehicle_count | 1369.200 | 1378.050 | 8.850 | 0.6% | C1_better | 5/20 | -18.000 | 104.400 | [-28.551, 59.401] |  |
| never_inserted_vehicle_count | 599.550 | 611.350 | 11.800 | 2.0% | C1_worse | 3/20 | 25.500 | 79.348 | [-26.252, 40.051] |  |
| unfinished_in_network_count | 179.150 | 158.500 | -20.650 | -11.5% | C1_better | 10/20 | -1.000 | 44.257 | [-40.300, -2.799] |  |
| mean_depart_delay_seconds | 248.684 | 291.405 | 42.721 | 17.2% | C1_worse | 2/20 | 8.136 | 71.691 | [15.418, 76.234] |  |
| mean_stops | 8.845 | 6.372 | -2.472 | -28.0% | C1_better | 12/20 | -0.262 | 4.245 | [-4.444, -0.842] |  |
| max_network_queue_vehicles | 168.200 | 143.450 | -24.750 | -14.7% | C1_better | 10/20 | -5.000 | 48.013 | [-46.351, -5.800] |  |
| max_lane_queue_vehicles | 19.250 | 17.200 | -2.050 | -10.6% | C1_better | 15/20 | -1.000 | 2.685 | [-3.200, -0.900] |  |
| internal_lane_persistence_events | 4186.250 | 3364.700 | -821.550 | -19.6% | C1_better | 17/20 | -121.000 | 1368.581 | [-1434.662, -307.383] |  |
| sumo_teleports_total | 0.150 | 0.000 | -0.150 | -100.0% | C1_better | 1/20 | 0.000 | 0.671 | [-0.450, 0.000] |  |
| corridor_throughput | 159.350 | 165.050 | 5.700 | 3.6% | C1_better | 12/20 | 1.000 | 18.273 | [-1.951, 14.050] |  |
| corridor_mean_travel_time | 547.651 | 433.711 | -113.940 | -20.8% | C1_better | 15/20 | -52.629 | 180.890 | [-193.917, -40.670] |  |
| post_shock_queue_auc_vehicle_seconds | 115239.700 | 131035.400 | 15795.700 | 13.7% | C1_worse | 0/5 | 14945.000 | 6811.959 | [11159.400, 21331.000] |  |
| post_shock_time_loss | 135.819 | 151.490 | 15.671 | 11.5% | C1_worse | 0/5 | 14.692 | 7.643 | [10.641, 22.277] |  |

## 6. Sensibilidade

### 6.1 Sem o par S4 seed 5791 (o único par com teleportes no B2)

| métrica | dif. agrupada (todos) | dif. agrupada sem o par | IC agrupado sem o par | dif. S4 (todos) | dif. S4 sem o par | IC S4 sem o par | efeito mudou (agrupado) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mean_waiting_time | -42.688 | -33.717 | [-73.310, -0.864] | -189.668 | -183.796 | [-199.786, -161.854] | não |
| mean_time_loss | -64.456 | -52.944 | [-107.699, -6.059] | -271.923 | -269.109 | [-290.995, -239.073] | não |
| throughput | 11.700 | -7.211 | [-32.000, 19.158] | 142.600 | 85.500 | [59.500, 111.500] | SIM |
| mean_network_queue_vehicles | -12.742 | -9.437 | [-22.404, 1.998] | -63.620 | -60.641 | [-65.415, -55.867] | não |
| mean_travel_time | -64.506 | -52.996 | [-106.134, -6.629] | -272.077 | -269.296 | [-291.480, -238.849] | não |
| completion_ratio_offered | -0.009 | -0.015 | [-0.030, -0.002] | 0.041 | 0.025 | [0.016, 0.033] | não |
| completion_ratio_departed | 0.018 | 0.012 | [0.000, 0.025] | 0.077 | 0.063 | [0.052, 0.072] | não |
| departure_ratio | -0.015 | -0.020 | [-0.034, -0.008] | 0.015 | -0.002 | [-0.009, 0.005] | não |
| offered_vehicle_count | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | [0.000, 0.000] | não |
| departed_vehicle_count | -11.800 | -27.632 | [-44.526, -12.630] | 52.400 | -6.750 | [-32.000, 18.500] | não |
| arrived_vehicle_count | 8.850 | -10.421 | [-35.895, 17.317] | 145.400 | 88.000 | [58.500, 117.500] | SIM |
| never_inserted_vehicle_count | 11.800 | 27.632 | [12.579, 44.895] | -52.400 | 6.750 | [-18.500, 32.000] | não |
| unfinished_in_network_count | -20.650 | -17.211 | [-37.212, 0.526] | -93.000 | -94.750 | [-103.500, -85.750] | não |
| mean_depart_delay_seconds | 42.721 | 31.671 | [10.918, 58.092] | 143.324 | 115.989 | [73.968, 176.967] | não |
| mean_stops | -2.472 | -2.172 | [-4.100, -0.561] | -9.575 | -9.924 | [-10.689, -9.159] | não |
| max_network_queue_vehicles | -24.750 | -20.632 | [-42.370, -1.893] | -103.000 | -103.000 | [-108.000, -97.000] | não |
| max_lane_queue_vehicles | -2.050 | -2.105 | [-3.316, -0.947] | -1.000 | -1.000 | [-1.000, -1.000] | não |
| internal_lane_persistence_events | -821.550 | -659.105 | [-1226.388, -200.053] | -3083.600 | -2877.500 | [-3163.750, -2481.250] | não |
| sumo_teleports_total | -0.150 | 0.000 | [0.000, 0.000] | -0.600 | 0.000 | [0.000, 0.000] | SIM |
| corridor_throughput | 5.700 | 3.263 | [-3.368, 10.159] | 30.200 | 24.750 | [15.750, 33.500] | não |
| corridor_mean_travel_time | -113.940 | -101.241 | [-186.683, -32.031] | -400.144 | -411.376 | [-511.347, -302.668] | não |

Métricas primárias cuja direção agrupada muda quando o par é removido: ['throughput'].

### 6.2 Remover uma seed por vez (agrupado entre cenários): direção da diferença média por métrica primária

| métrica | sem 42 | sem 2027 | sem 3253 | sem 4517 | sem 5791 |
| --- | --- | --- | --- | --- | --- |
| mean_waiting_time | -43.133 (C1_better) | -41.919 (C1_better) | -44.885 (C1_better) | -42.601 (C1_better) | -40.904 (C1_better) |
| mean_time_loss | -64.915 (C1_better) | -63.098 (C1_better) | -67.132 (C1_better) | -63.755 (C1_better) | -63.378 (C1_better) |
| throughput | 15.000 (C1_better) | 12.750 (C1_better) | 14.812 (C1_better) | 22.312 (C1_better) | -6.375 (C1_worse) |
| mean_network_queue_vehicles | -13.068 (C1_better) | -13.109 (C1_better) | -13.394 (C1_better) | -12.054 (C1_better) | -12.087 (C1_better) |
| mean_travel_time | -64.974 (C1_better) | -63.116 (C1_better) | -67.227 (C1_better) | -63.744 (C1_better) | -63.469 (C1_better) |
| completion_ratio_offered | -0.008 (C1_worse) | -0.009 (C1_worse) | -0.009 (C1_worse) | -0.004 (C1_worse) | -0.015 (C1_worse) |

### 6.3 Teleportes (métrica auxiliar, soma das 5 seeds)

| cenário | B2 | C1 |
| --- | --- | --- |
| S1_BALANCED | 0 | 0 |
| S2_DIRECTIONAL_PEAK | 0 | 0 |
| S3_DEMAND_SHIFT | 0 | 0 |
| S4_LOCAL_SATURATION | 3 | 0 |

Apenas o B2 S4 seed 5791 tem teleportes nesta comparação (3); o C1 não tem nenhum. O par foi removido em 6.1; a comparação também aparece nas linhas do S4 da seção 4.

## 7. Interpretação

- Contagem de células sobre 6 métricas primárias x 4 cenários = 24 células: **FAV 10**, **UNFAV 13**, NEUTRAL 1.
  - S1_BALANCED: mean_waiting_time UNFAV, mean_time_loss UNFAV, throughput NEUTRAL, mean_network_queue_vehicles UNFAV, mean_travel_time UNFAV, completion_ratio_offered UNFAV
  - S2_DIRECTIONAL_PEAK: mean_waiting_time FAV, mean_time_loss FAV, throughput UNFAV, mean_network_queue_vehicles FAV, mean_travel_time FAV, completion_ratio_offered UNFAV
  - S3_DEMAND_SHIFT: mean_waiting_time UNFAV, mean_time_loss UNFAV, throughput UNFAV, mean_network_queue_vehicles UNFAV, mean_travel_time UNFAV, completion_ratio_offered UNFAV
  - S4_LOCAL_SATURATION: mean_waiting_time FAV, mean_time_loss FAV, throughput FAV, mean_network_queue_vehicles FAV, mean_travel_time FAV, completion_ratio_offered FAV
- O IC agrupado exclui zero em 4 das 6 métricas primárias.
- Classe de resultado pela regra pré-declarada: **MIXED**; confiança **MÉDIA** (nunca ALTA para um piloto de 5 seeds).
- O C1 supera o B2: **MISTO**.
- A leitura por cenário é a que deve ser usada; a direção pode diferir entre cenários e o número agrupado mistura regimes.

## 8. Limitações

- O Pilot V2 é um piloto: os resultados não entram na campanha final e o Pilot V1 não é combinado com o V2.
- Amostra pequena: 5 seeds por cenário; os intervalos bootstrap são descritivos, não um teste de significância.
- O S3 foi aprovado pelo gate composto (Prompts 47/48); a janela de 1800 s foi escolhida após observar os diagnósticos do 46.9.
- A regra de 360 s é mantida como diagnóstico: a seed 4517 do S3 falha nela (VALID_WITH_DIAGNOSTIC_WARNING).
- O S4 é aceito como ALLOW_AND_MEASURE: os teleportes são reportados (B2: 3 na seed 5791; C1: 0) e a sensibilidade sem esse par é mostrada. A escala 2,0 do S4 é o topo da grade de calibração e cerca de metade da demanda do S4 nunca entra.
- O contrafactual de zero teleportes foi testado apenas com o B0; o comportamento de B2 e C1 sem teleportes é desconhecido.
- A validade de cenário foi julgada em execuções de referência do B0; os controladores podem alterar o regime realizado.
- Tempo de espera, perda de tempo, tempo de viagem e paradas são condicionais à conclusão e dependem de ofertados/partidos/chegados e das razões de conclusão.
- Apenas uma configuração de atraso/descarte de comunicação (atraso 0, descarte 0); o custo do C1 (mensagens) não é analisado aqui.

## 9. Conclusão do Pilot V2

Sob a regra descritiva pré-declarada, o resultado B2-vs-C1 é **MISTO** com confiança **MÉDIA**. Esta é uma observação de piloto para subsidiar a decisão sobre o número de seeds (use as larguras dos ICs acima), não evidência de benefício cooperativo.

## 10. Leitura das tabelas (resumo em linguagem simples, números das seções 4-6)

- S1 (balanceado) e S3 (mudança de demanda): o C1 é pior que o B2 em todas as 5 seeds em tempo de espera (+44,7% e +24,7%), perda de tempo, tempo de viagem e fila da rede; a razão de conclusão é ligeiramente menor. A direção do S3 é a mesma após o choque (perda de tempo pós-choque +11,5%, AUC da fila pós-choque pior).
- S2 (pico direcional): misto dentro do cenário. O C1 tem menor tempo de espera (-12,7%), perda de tempo, tempo de viagem e fila em 5/5 seeds, mas menor throughput (-6,1%) e menor razão de conclusão (-0,052) em 5/5 seeds; a vantagem de atraso das viagens concluídas, portanto, vem com menos viagens concluídas e não deve ser lida isoladamente.
- S4 (saturação em A5): o C1 é melhor em 5/5 seeds em todas as seis métricas primárias (espera -20,4%, perda de tempo -23,3%, fila -17,7%, throughput +12,0%, conclusão +0,041). Sem o par S4 seed 5791 a direção se mantém e todos os intervalos do S4 ainda excluem zero, mas o ganho de throughput cai de +142,6 para +85,5 veíc e a direção agrupada do throughput se inverte, de modo que o sinal agrupado do throughput depende desse par.
- Em resumo: o C1 não supera o B2 de forma consistente; sua vantagem se concentra no S4 sobrecarregado (e em parte nos atrasos do S2), enquanto S1 e S3 favorecem o B2 em toda seed. Classe MIXED. O agregado agrupado (diferenças negativas de espera/perda de tempo/tempo de viagem) é conduzido pelas magnitudes muito grandes do S4 e não deve ser lido como um benefício geral.
