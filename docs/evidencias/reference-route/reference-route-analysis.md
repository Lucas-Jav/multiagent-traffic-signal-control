# Experimento da rota de referência: B0 calibrado vs B2 vs C1

`campaign_role: REFERENCE_ROUTE_B0_CALIBRATED`. Evidência PRÉ-FINAL e validação de metodologia; 5 seeds do Pilot V2; resultados descritivos. Não é a campanha final.

- Rota (arestas SUMO): `left1A1 -> A1B1 -> B1C1 -> C1right1`.
- Rota (lógica): entrada oeste -> A4 -> A5 -> A6 -> saída leste.
- Coorte: veículos ofertados com essa sequência exata de arestas planejada, partida agendada em [300, 3900) s. Seleção por sequência de arestas, nunca por id de rota.
- Tempo de viagem = média sobre viagens CONCLUÍDAS; viagem não concluída nunca recebe duração. A razão de conclusão é mostrada ao lado de todo tempo de viagem.
- Diferença = tratamento - base (negativo = tratamento mais rápido). IC 95% por bootstrap pareado (10.000 reamostragens de seeds, RNG determinístico).

## Tabela para o orientador (tempo de viagem médio da rota, segundos)

| Cenário | B0 calibrado | B2 | C1 | B0 -> B2 (adaptação local) | B2 -> C1 (cooperação) | Interpretação B0 -> B2 | Interpretação B2 -> C1 |
|---|---|---|---|---|---|---|---|
| S1_BALANCED | 126.5 (concl. 0.98) | 112.0 (concl. 0.98) | 138.9 (concl. 0.97) | -14.5 s (-11.5%) IC95 [-20.8; -10.7] | +27.0 s (+24.1%) IC95 [+19.8; +33.7] | tempo de viagem menor (-14.5 s, IC exclui 0) | tempo de viagem maior (+27.0 s, IC exclui 0) |
| S2_DIRECTIONAL_PEAK | 127.9 (concl. 0.96) | 327.3 (concl. 0.66) | 283.4 (concl. 0.64) | +199.4 s (+155.9%) IC95 [+179.6; +215.4] | -43.9 s (-13.4%) IC95 [-63.4; -22.4] | tempo de viagem maior (+199.4 s, IC exclui 0); conclusão -29.8 p.p. (IC exclui 0): ler com cautela | tempo de viagem menor (-43.9 s, IC exclui 0) |
| S3_DEMAND_SHIFT | 213.4 (concl. 0.86) | 275.3 (concl. 0.82) | 235.3 (concl. 0.82) | +61.9 s (+29.0%) IC95 [+43.7; +76.6] | -40.0 s (-14.5%) IC95 [-53.7; -17.0] | tempo de viagem maior (+61.9 s, IC exclui 0); conclusão -3.8 p.p. (IC exclui 0): ler com cautela | tempo de viagem menor (-40.0 s, IC exclui 0) |
| S4_LOCAL_SATURATION | 364.6 (concl. 0.91) | 1220.6 (concl. 0.19) | 758.5 (concl. 0.31) | +856.0 s (+234.8%) IC95 [+686.6; +1039.2] | -462.1 s (-37.9%) IC95 [-608.6; -333.5] | tempo de viagem maior (+856.0 s, IC exclui 0); conclusão -72.1 p.p. (IC exclui 0): ler com cautela | tempo de viagem menor (-462.1 s, IC exclui 0); conclusão +12.1 p.p. (IC exclui 0): ler com cautela |

## B0 calibrado vs C1 (efeito total)

| Cenário | B0 -> C1 | Interpretação |
|---|---|---|
| S1_BALANCED | +12.4 s (+9.8%) IC95 [+7.3; +17.1] | tempo de viagem maior (+12.4 s, IC exclui 0); conclusão -1.2 p.p. (IC exclui 0): ler com cautela |
| S2_DIRECTIONAL_PEAK | +155.5 s (+121.5%) IC95 [+149.9; +160.2] | tempo de viagem maior (+155.5 s, IC exclui 0); conclusão -32.7 p.p. (IC exclui 0): ler com cautela |
| S3_DEMAND_SHIFT | +21.9 s (+10.2%) IC95 [-8.5; +58.1] | sem diferença distinguível (+21.9 s, IC inclui 0); conclusão -4.6 p.p. (IC exclui 0): ler com cautela |
| S4_LOCAL_SATURATION | +393.9 s (+108.0%) IC95 [+337.0; +455.9] | tempo de viagem maior (+393.9 s, IC exclui 0); conclusão -60.0 p.p. (IC exclui 0): ler com cautela |

## Amostra (veículos da coorte por run, ofertados)

| Cenário | Ofertados por run | Faixa de sanidade (Prompt 54) |
|---|---|---|
| S1_BALANCED | [45, 46, 52, 59] | 45-59 |
| S2_DIRECTIONAL_PEAK | [97, 110, 112, 114, 127] | 97-127 |
| S3_DEMAND_SHIFT | [106, 109, 114, 115, 116] | 106-116 |
| S4_LOCAL_SATURATION | [188, 198, 201, 205] | 188-205 |

Desvios da faixa de sanidade: 0 (run, controlador).

## Contagens e conclusão por seed

| Cenário | Seed | Controlador | Ofert. | Inser. | Concl. | Nunca ins. | Não concl. | TV médio | TV mediano | Espera | Perda | Paradas | Concl./ofert. | Concl./inser. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_BALANCED | 42 | B0_FIXED_CALIBRATED | 52 | 52 | 52 | 0 | 0 | 121.0 | 118.5 | 47.5 | 67.9 | 2.65 | 1.000 | 1.000 |
| S1_BALANCED | 42 | B2_LOCAL_PRESSURE | 52 | 52 | 52 | 0 | 0 | 110.7 | 110.0 | 36.8 | 57.6 | 2.52 | 1.000 | 1.000 |
| S1_BALANCED | 42 | C1_COOPERATIVE_COMPACT | 52 | 52 | 52 | 0 | 0 | 141.5 | 143.0 | 68.6 | 88.4 | 2.63 | 1.000 | 1.000 |
| S1_BALANCED | 2027 | B0_FIXED_CALIBRATED | 46 | 46 | 45 | 0 | 1 | 133.4 | 131.0 | 59.2 | 80.7 | 2.93 | 0.978 | 0.978 |
| S1_BALANCED | 2027 | B2_LOCAL_PRESSURE | 46 | 46 | 45 | 0 | 1 | 106.6 | 104.0 | 34.3 | 53.9 | 2.40 | 0.978 | 0.978 |
| S1_BALANCED | 2027 | C1_COOPERATIVE_COMPACT | 46 | 46 | 44 | 0 | 2 | 145.2 | 142.0 | 73.2 | 92.4 | 2.50 | 0.957 | 0.957 |
| S1_BALANCED | 3253 | B0_FIXED_CALIBRATED | 45 | 45 | 45 | 0 | 0 | 125.2 | 123.0 | 50.8 | 71.8 | 2.78 | 1.000 | 1.000 |
| S1_BALANCED | 3253 | B2_LOCAL_PRESSURE | 45 | 45 | 45 | 0 | 0 | 111.8 | 113.0 | 40.0 | 58.4 | 1.98 | 1.000 | 1.000 |
| S1_BALANCED | 3253 | C1_COOPERATIVE_COMPACT | 45 | 45 | 44 | 0 | 1 | 137.5 | 137.0 | 64.0 | 84.1 | 2.80 | 0.978 | 0.978 |
| S1_BALANCED | 4517 | B0_FIXED_CALIBRATED | 59 | 59 | 57 | 0 | 2 | 125.7 | 125.0 | 51.5 | 73.0 | 2.75 | 0.966 | 0.966 |
| S1_BALANCED | 4517 | B2_LOCAL_PRESSURE | 59 | 59 | 56 | 0 | 3 | 114.5 | 114.0 | 42.4 | 61.9 | 2.54 | 0.949 | 0.949 |
| S1_BALANCED | 4517 | C1_COOPERATIVE_COMPACT | 59 | 59 | 56 | 0 | 3 | 140.0 | 139.5 | 67.6 | 87.4 | 2.70 | 0.949 | 0.949 |
| S1_BALANCED | 5791 | B0_FIXED_CALIBRATED | 52 | 52 | 50 | 0 | 2 | 127.1 | 126.0 | 53.1 | 74.7 | 2.86 | 0.962 | 0.962 |
| S1_BALANCED | 5791 | B2_LOCAL_PRESSURE | 52 | 52 | 50 | 0 | 2 | 116.2 | 115.0 | 44.2 | 63.7 | 2.64 | 0.962 | 0.962 |
| S1_BALANCED | 5791 | C1_COOPERATIVE_COMPACT | 52 | 52 | 50 | 0 | 2 | 130.4 | 133.0 | 58.3 | 77.9 | 2.60 | 0.962 | 0.962 |
| S2_DIRECTIONAL_PEAK | 42 | B0_FIXED_CALIBRATED | 97 | 97 | 89 | 0 | 8 | 123.8 | 122.0 | 46.6 | 71.1 | 2.88 | 0.918 | 0.918 |
| S2_DIRECTIONAL_PEAK | 42 | B2_LOCAL_PRESSURE | 97 | 75 | 68 | 22 | 7 | 286.4 | 286.0 | 195.4 | 233.7 | 4.01 | 0.701 | 0.907 |
| S2_DIRECTIONAL_PEAK | 42 | C1_COOPERATIVE_COMPACT | 97 | 69 | 61 | 28 | 8 | 282.3 | 277.0 | 193.5 | 229.6 | 3.85 | 0.629 | 0.884 |
| S2_DIRECTIONAL_PEAK | 2027 | B0_FIXED_CALIBRATED | 114 | 114 | 110 | 0 | 4 | 128.7 | 129.0 | 51.9 | 75.9 | 2.83 | 0.965 | 0.965 |
| S2_DIRECTIONAL_PEAK | 2027 | B2_LOCAL_PRESSURE | 114 | 85 | 78 | 29 | 7 | 338.8 | 345.0 | 242.4 | 285.9 | 4.69 | 0.684 | 0.918 |
| S2_DIRECTIONAL_PEAK | 2027 | C1_COOPERATIVE_COMPACT | 114 | 82 | 76 | 32 | 6 | 291.9 | 289.5 | 202.3 | 239.2 | 4.00 | 0.667 | 0.927 |
| S2_DIRECTIONAL_PEAK | 3253 | B0_FIXED_CALIBRATED | 112 | 112 | 110 | 0 | 2 | 128.6 | 128.0 | 51.3 | 75.8 | 2.85 | 0.982 | 0.982 |
| S2_DIRECTIONAL_PEAK | 3253 | B2_LOCAL_PRESSURE | 112 | 74 | 63 | 38 | 11 | 319.5 | 312.0 | 227.7 | 266.4 | 4.38 | 0.562 | 0.851 |
| S2_DIRECTIONAL_PEAK | 3253 | C1_COOPERATIVE_COMPACT | 112 | 80 | 72 | 32 | 8 | 286.0 | 283.5 | 195.9 | 232.8 | 3.88 | 0.643 | 0.900 |
| S2_DIRECTIONAL_PEAK | 4517 | B0_FIXED_CALIBRATED | 110 | 110 | 107 | 0 | 3 | 128.9 | 128.0 | 52.4 | 76.2 | 2.89 | 0.973 | 0.973 |
| S2_DIRECTIONAL_PEAK | 4517 | B2_LOCAL_PRESSURE | 110 | 90 | 83 | 20 | 7 | 350.4 | 358.0 | 253.3 | 297.7 | 4.81 | 0.755 | 0.922 |
| S2_DIRECTIONAL_PEAK | 4517 | C1_COOPERATIVE_COMPACT | 110 | 67 | 62 | 43 | 5 | 281.5 | 280.5 | 192.7 | 228.7 | 3.85 | 0.564 | 0.925 |
| S2_DIRECTIONAL_PEAK | 5791 | B0_FIXED_CALIBRATED | 127 | 127 | 124 | 0 | 3 | 129.6 | 128.5 | 51.8 | 76.8 | 2.85 | 0.976 | 0.976 |
| S2_DIRECTIONAL_PEAK | 5791 | B2_LOCAL_PRESSURE | 127 | 89 | 79 | 38 | 10 | 341.7 | 328.0 | 245.3 | 288.9 | 4.77 | 0.622 | 0.888 |
| S2_DIRECTIONAL_PEAK | 5791 | C1_COOPERATIVE_COMPACT | 127 | 93 | 86 | 34 | 7 | 275.4 | 276.0 | 183.7 | 222.7 | 4.01 | 0.677 | 0.925 |
| S3_DEMAND_SHIFT | 42 | B0_FIXED_CALIBRATED | 114 | 114 | 99 | 0 | 15 | 209.6 | 225.0 | 121.2 | 156.7 | 3.74 | 0.868 | 0.868 |
| S3_DEMAND_SHIFT | 42 | B2_LOCAL_PRESSURE | 114 | 112 | 96 | 2 | 16 | 278.1 | 317.0 | 172.7 | 225.2 | 5.51 | 0.842 | 0.857 |
| S3_DEMAND_SHIFT | 42 | C1_COOPERATIVE_COMPACT | 114 | 108 | 97 | 6 | 11 | 228.5 | 251.0 | 137.2 | 175.5 | 4.19 | 0.851 | 0.898 |
| S3_DEMAND_SHIFT | 2027 | B0_FIXED_CALIBRATED | 109 | 109 | 90 | 0 | 19 | 227.5 | 209.5 | 136.3 | 174.7 | 4.06 | 0.826 | 0.826 |
| S3_DEMAND_SHIFT | 2027 | B2_LOCAL_PRESSURE | 109 | 102 | 85 | 7 | 17 | 284.2 | 332.0 | 177.7 | 231.4 | 5.40 | 0.780 | 0.833 |
| S3_DEMAND_SHIFT | 2027 | C1_COOPERATIVE_COMPACT | 109 | 101 | 88 | 8 | 13 | 227.4 | 244.5 | 137.3 | 174.5 | 4.02 | 0.807 | 0.871 |
| S3_DEMAND_SHIFT | 3253 | B0_FIXED_CALIBRATED | 106 | 106 | 96 | 0 | 10 | 187.4 | 173.0 | 101.7 | 134.5 | 3.55 | 0.906 | 0.906 |
| S3_DEMAND_SHIFT | 3253 | B2_LOCAL_PRESSURE | 106 | 104 | 89 | 2 | 15 | 272.0 | 310.0 | 168.8 | 219.2 | 5.26 | 0.840 | 0.856 |
| S3_DEMAND_SHIFT | 3253 | C1_COOPERATIVE_COMPACT | 106 | 96 | 82 | 10 | 14 | 276.6 | 296.5 | 178.0 | 223.6 | 4.79 | 0.774 | 0.854 |
| S3_DEMAND_SHIFT | 4517 | B0_FIXED_CALIBRATED | 116 | 116 | 100 | 0 | 16 | 245.1 | 257.0 | 148.8 | 192.0 | 4.27 | 0.862 | 0.862 |
| S3_DEMAND_SHIFT | 4517 | B2_LOCAL_PRESSURE | 116 | 109 | 97 | 7 | 12 | 272.1 | 322.0 | 167.3 | 219.2 | 5.21 | 0.836 | 0.890 |
| S3_DEMAND_SHIFT | 4517 | C1_COOPERATIVE_COMPACT | 116 | 109 | 98 | 7 | 11 | 223.1 | 235.5 | 134.2 | 170.1 | 4.10 | 0.845 | 0.899 |
| S3_DEMAND_SHIFT | 5791 | B0_FIXED_CALIBRATED | 115 | 115 | 98 | 0 | 17 | 197.3 | 185.0 | 110.6 | 144.4 | 3.68 | 0.852 | 0.852 |
| S3_DEMAND_SHIFT | 5791 | B2_LOCAL_PRESSURE | 115 | 112 | 95 | 3 | 17 | 269.9 | 297.0 | 169.7 | 217.0 | 5.18 | 0.826 | 0.848 |
| S3_DEMAND_SHIFT | 5791 | C1_COOPERATIVE_COMPACT | 115 | 106 | 93 | 9 | 13 | 220.8 | 229.0 | 132.9 | 167.8 | 3.90 | 0.809 | 0.877 |
| S4_LOCAL_SATURATION | 42 | B0_FIXED_CALIBRATED | 198 | 198 | 178 | 0 | 20 | 400.4 | 406.0 | 277.0 | 347.6 | 6.36 | 0.899 | 0.899 |
| S4_LOCAL_SATURATION | 42 | B2_LOCAL_PRESSURE | 198 | 43 | 27 | 155 | 16 | 1436.3 | 1621.0 | 1157.7 | 1381.5 | 27.19 | 0.136 | 0.628 |
| S4_LOCAL_SATURATION | 42 | C1_COOPERATIVE_COMPACT | 198 | 57 | 44 | 141 | 13 | 900.4 | 889.0 | 702.0 | 846.5 | 16.07 | 0.222 | 0.772 |
| S4_LOCAL_SATURATION | 2027 | B0_FIXED_CALIBRATED | 188 | 188 | 169 | 0 | 19 | 374.3 | 374.0 | 253.8 | 322.1 | 6.01 | 0.899 | 0.899 |
| S4_LOCAL_SATURATION | 2027 | B2_LOCAL_PRESSURE | 188 | 39 | 28 | 149 | 11 | 1528.9 | 1735.0 | 1204.6 | 1476.9 | 32.18 | 0.149 | 0.718 |
| S4_LOCAL_SATURATION | 2027 | C1_COOPERATIVE_COMPACT | 188 | 66 | 56 | 122 | 10 | 808.8 | 763.0 | 621.7 | 757.2 | 14.84 | 0.298 | 0.848 |
| S4_LOCAL_SATURATION | 3253 | B0_FIXED_CALIBRATED | 205 | 205 | 187 | 0 | 18 | 364.6 | 368.0 | 246.1 | 312.0 | 5.87 | 0.912 | 0.912 |
| S4_LOCAL_SATURATION | 3253 | B2_LOCAL_PRESSURE | 205 | 69 | 48 | 136 | 21 | 1012.0 | 1006.5 | 772.5 | 959.6 | 19.90 | 0.234 | 0.696 |
| S4_LOCAL_SATURATION | 3253 | C1_COOPERATIVE_COMPACT | 205 | 77 | 63 | 128 | 14 | 749.8 | 730.0 | 569.7 | 697.4 | 13.25 | 0.307 | 0.818 |
| S4_LOCAL_SATURATION | 4517 | B0_FIXED_CALIBRATED | 198 | 198 | 186 | 0 | 12 | 347.9 | 343.0 | 233.4 | 295.3 | 5.67 | 0.939 | 0.939 |
| S4_LOCAL_SATURATION | 4517 | B2_LOCAL_PRESSURE | 198 | 60 | 47 | 138 | 13 | 1044.1 | 1070.0 | 814.2 | 991.3 | 19.38 | 0.237 | 0.783 |
| S4_LOCAL_SATURATION | 4517 | C1_COOPERATIVE_COMPACT | 198 | 88 | 71 | 110 | 17 | 693.2 | 701.0 | 523.9 | 640.8 | 11.92 | 0.359 | 0.807 |
| S4_LOCAL_SATURATION | 5791 | B0_FIXED_CALIBRATED | 201 | 201 | 180 | 0 | 21 | 335.8 | 335.5 | 222.8 | 283.3 | 5.48 | 0.896 | 0.896 |
| S4_LOCAL_SATURATION | 5791 | B2_LOCAL_PRESSURE | 201 | 61 | 37 | 140 | 24 | 1081.7 | 1154.0 | 835.9 | 1029.8 | 23.38 | 0.184 | 0.607 |
| S4_LOCAL_SATURATION | 5791 | C1_COOPERATIVE_COMPACT | 201 | 91 | 72 | 110 | 19 | 640.5 | 643.0 | 485.3 | 588.9 | 10.03 | 0.358 | 0.791 |

## Comparações pareadas (todas as métricas)

| Cenário | Comparação | Métrica | N | Média base | Média trat. | Dif. média | Dif. mediana | Dif. relativa | IC95 |
|---|---|---|---|---|---|---|---|---|---|
| S1_BALANCED | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_travel_time_seconds | 5 | 126.483 | 111.956 | -14.527 | -11.255 | -11.5% | [-20.802; -10.749] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_median_travel_time_seconds | 5 | 124.700 | 111.200 | -13.500 | -11.000 | -10.8% | [-20.400; -9.400] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_waiting_time_seconds | 5 | 52.423 | 39.565 | -12.858 | -10.731 | -24.5% | [-18.912; -9.257] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_time_loss_seconds | 5 | 73.621 | 59.114 | -14.506 | -11.066 | -19.7% | [-20.835; -10.708] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_stops | 5 | 2.796 | 2.415 | -0.381 | -0.220 | -13.6% | [-0.630; -0.185] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_completion_ratio_offered | 5 | 0.981 | 0.978 | -0.003 | +0.000 | -0.3% | [-0.010; +0.000] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_completion_ratio_departed | 5 | 0.981 | 0.978 | -0.003 | +0.000 | -0.3% | [-0.010; +0.000] |
| S1_BALANCED | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 5 | 111.956 | 138.917 | +26.961 | +25.701 | +24.1% | [+19.789; +33.688] |
| S1_BALANCED | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_median_travel_time_seconds | 5 | 111.200 | 138.900 | +27.700 | +25.500 | +24.9% | [+21.900; +34.200] |
| S1_BALANCED | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_waiting_time_seconds | 5 | 39.565 | 66.339 | +26.773 | +25.143 | +67.7% | [+19.810; +33.905] |
| S1_BALANCED | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_time_loss_seconds | 5 | 59.114 | 86.045 | +26.931 | +25.744 | +45.6% | [+19.804; +33.398] |
| S1_BALANCED | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_stops | 5 | 2.415 | 2.645 | +0.231 | +0.115 | +9.6% | [+0.028; +0.534] |
| S1_BALANCED | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 5 | 0.978 | 0.969 | -0.009 | +0.000 | -0.9% | [-0.018; +0.000] |
| S1_BALANCED | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_departed | 5 | 0.978 | 0.969 | -0.009 | +0.000 | -0.9% | [-0.018; +0.000] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 5 | 126.483 | 138.917 | +12.434 | +12.323 | +9.8% | [+7.309; +17.102] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_median_travel_time_seconds | 5 | 124.700 | 138.900 | +14.200 | +14.000 | +11.4% | [+9.800; +19.800] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_waiting_time_seconds | 5 | 52.423 | 66.339 | +13.915 | +13.960 | +26.5% | [+9.000; +18.092] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_time_loss_seconds | 5 | 73.621 | 86.045 | +12.425 | +12.333 | +16.9% | [+7.160; +17.081] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_stops | 5 | 2.796 | 2.645 | -0.151 | -0.058 | -5.4% | [-0.308; -0.013] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 5 | 0.981 | 0.969 | -0.012 | -0.017 | -1.2% | [-0.021; -0.003] |
| S1_BALANCED | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_departed | 5 | 0.981 | 0.969 | -0.012 | -0.017 | -1.2% | [-0.021; -0.003] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_travel_time_seconds | 5 | 127.941 | 327.339 | +199.398 | +210.056 | +155.9% | [+179.552; +215.416] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_median_travel_time_seconds | 5 | 127.100 | 325.800 | +198.700 | +199.500 | +156.3% | [+178.400; +218.300] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_waiting_time_seconds | 5 | 50.799 | 232.790 | +181.991 | +190.468 | +358.3% | [+164.706; +195.824] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_time_loss_seconds | 5 | 75.141 | 274.545 | +199.403 | +210.078 | +265.4% | [+179.423; +215.493] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_stops | 5 | 2.858 | 4.533 | +1.675 | +1.865 | +58.6% | [+1.374; +1.908] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_completion_ratio_offered | 5 | 0.963 | 0.665 | -0.298 | -0.281 | -30.9% | [-0.366; -0.230] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_completion_ratio_departed | 5 | 0.963 | 0.897 | -0.066 | -0.051 | -6.8% | [-0.099; -0.033] |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 5 | 327.339 | 283.444 | -43.895 | -46.809 | -13.4% | [-63.395; -22.383] |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_median_travel_time_seconds | 5 | 325.800 | 281.300 | -44.500 | -52.000 | -13.7% | [-63.600; -24.600] |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_waiting_time_seconds | 5 | 232.790 | 193.607 | -39.183 | -40.030 | -16.8% | [-56.894; -19.803] |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_time_loss_seconds | 5 | 274.545 | 230.605 | -43.940 | -46.774 | -16.0% | [-63.441; -22.426] |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_stops | 5 | 4.533 | 3.919 | -0.615 | -0.692 | -13.6% | [-0.825; -0.368] |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 5 | 0.665 | 0.636 | -0.029 | -0.018 | -4.4% | [-0.118; +0.051] |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_departed | 5 | 0.897 | 0.912 | +0.015 | +0.009 | +1.7% | [-0.006; +0.037] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 5 | 127.941 | 283.444 | +155.503 | +157.373 | +121.5% | [+149.898; +160.169] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_median_travel_time_seconds | 5 | 127.100 | 281.300 | +154.200 | +155.000 | +121.3% | [+150.500; +157.900] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_waiting_time_seconds | 5 | 50.799 | 193.607 | +142.808 | +144.607 | +281.1% | [+136.939; +147.853] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_time_loss_seconds | 5 | 75.141 | 230.605 | +155.463 | +157.053 | +206.9% | [+149.891; +160.125] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_stops | 5 | 2.858 | 3.919 | +1.060 | +1.030 | +37.1% | [+0.983; +1.138] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 5 | 0.963 | 0.636 | -0.327 | -0.299 | -34.0% | [-0.367; -0.295] |
| S2_DIRECTIONAL_PEAK | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_departed | 5 | 0.963 | 0.912 | -0.051 | -0.047 | -5.2% | [-0.067; -0.038] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_travel_time_seconds | 5 | 213.394 | 275.284 | +61.890 | +68.499 | +29.0% | [+43.650; +76.607] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_median_travel_time_seconds | 5 | 209.900 | 315.600 | +105.700 | +112.000 | +50.4% | [+81.900; +126.200] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_waiting_time_seconds | 5 | 123.711 | 171.237 | +47.526 | +51.526 | +38.4% | [+32.202; +60.812] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_time_loss_seconds | 5 | 160.458 | 222.385 | +61.927 | +68.563 | +38.6% | [+43.695; +76.675] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_stops | 5 | 3.860 | 5.311 | +1.451 | +1.495 | +37.6% | [+1.172; +1.691] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_completion_ratio_offered | 5 | 0.863 | 0.825 | -0.038 | -0.026 | -4.4% | [-0.054; -0.026] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_completion_ratio_departed | 5 | 0.863 | 0.857 | -0.006 | -0.004 | -0.7% | [-0.031; +0.015] |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 5 | 275.284 | 235.260 | -40.024 | -49.132 | -14.5% | [-53.740; -17.002] |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_median_travel_time_seconds | 5 | 315.600 | 251.300 | -64.300 | -68.000 | -20.4% | [-83.200; -38.600] |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_waiting_time_seconds | 5 | 171.237 | 143.914 | -27.323 | -35.481 | -16.0% | [-38.236; -8.669] |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_time_loss_seconds | 5 | 222.385 | 182.303 | -40.082 | -49.117 | -18.0% | [-53.753; -17.138] |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_stops | 5 | 5.311 | 4.201 | -1.110 | -1.276 | -20.9% | [-1.336; -0.776] |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 5 | 0.825 | 0.817 | -0.008 | +0.009 | -0.9% | [-0.038; +0.016] |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_departed | 5 | 0.857 | 0.880 | +0.023 | +0.029 | +2.7% | [+0.008; +0.037] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 5 | 213.394 | 235.260 | +21.866 | +18.817 | +10.2% | [-8.503; +58.150] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_median_travel_time_seconds | 5 | 209.900 | 251.300 | +41.400 | +35.000 | +19.7% | [+2.900; +88.100] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_waiting_time_seconds | 5 | 123.711 | 143.914 | +20.203 | +16.044 | +16.3% | [-2.340; +50.453] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_time_loss_seconds | 5 | 160.458 | 182.303 | +21.845 | +18.812 | +13.6% | [-8.503; +58.099] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_stops | 5 | 3.860 | 4.201 | +0.342 | +0.220 | +8.8% | [-0.036; +0.827] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 5 | 0.863 | 0.817 | -0.046 | -0.018 | -5.3% | [-0.091; -0.018] |
| S3_DEMAND_SHIFT | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_departed | 5 | 0.863 | 0.880 | +0.017 | +0.030 | +2.0% | [-0.018; +0.040] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_travel_time_seconds | 5 | 364.618 | 1220.606 | +855.988 | +745.865 | +234.8% | [+686.617; +1039.167] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_median_travel_time_seconds | 5 | 365.300 | 1317.300 | +952.000 | +818.500 | +260.6% | [+709.900; +1205.000] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_waiting_time_seconds | 5 | 246.619 | 956.982 | +710.362 | +613.115 | +288.0% | [+565.489; +862.794] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_time_loss_seconds | 5 | 312.046 | 1167.830 | +855.784 | +746.469 | +274.2% | [+686.756; +1038.914] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_mean_stops | 5 | 5.876 | 24.404 | +18.528 | +17.895 | +315.3% | [+14.677; +22.675] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_completion_ratio_offered | 5 | 0.909 | 0.188 | -0.721 | -0.711 | -79.3% | [-0.748; -0.694] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> B2_LOCAL_PRESSURE | reference_route_completion_ratio_departed | 5 | 0.909 | 0.686 | -0.223 | -0.217 | -24.5% | [-0.267; -0.178] |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 5 | 1220.606 | 758.533 | -462.073 | -441.217 | -37.9% | [-608.594; -333.486] |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_median_travel_time_seconds | 5 | 1317.300 | 745.200 | -572.100 | -511.000 | -43.4% | [-803.400; -370.300] |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_waiting_time_seconds | 5 | 956.982 | 580.535 | -376.446 | -350.545 | -39.3% | [-498.976; -267.333] |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_time_loss_seconds | 5 | 1167.830 | 706.156 | -461.674 | -440.896 | -39.5% | [-608.901; -333.276] |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_mean_stops | 5 | 24.404 | 13.221 | -11.183 | -11.117 | -45.8% | [-14.567; -7.867] |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 5 | 0.188 | 0.309 | +0.121 | +0.121 | +64.1% | [+0.088; +0.153] |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_departed | 5 | 0.686 | 0.807 | +0.121 | +0.131 | +17.6% | [+0.067; +0.161] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_travel_time_seconds | 5 | 364.618 | 758.533 | +393.915 | +385.248 | +108.0% | [+337.011; +455.940] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_median_travel_time_seconds | 5 | 365.300 | 745.200 | +379.900 | +362.000 | +104.0% | [+334.700; +434.600] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_waiting_time_seconds | 5 | 246.619 | 580.535 | +333.916 | +323.596 | +135.4% | [+285.950; +384.479] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_time_loss_seconds | 5 | 312.046 | 706.156 | +394.110 | +385.416 | +126.3% | [+337.512; +455.470] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_mean_stops | 5 | 5.876 | 13.221 | +7.345 | +7.388 | +125.0% | [+5.795; +8.894] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_offered | 5 | 0.909 | 0.309 | -0.600 | -0.601 | -66.0% | [-0.643; -0.563] |
| S4_LOCAL_SATURATION | B0_FIXED_CALIBRATED -> C1_COOPERATIVE_COMPACT | reference_route_completion_ratio_departed | 5 | 0.909 | 0.807 | -0.102 | -0.104 | -11.2% | [-0.125; -0.076] |

## Limitações

1. Cinco seeds: ICs largos e descritivos; não são prova de superioridade.
2. Tempo de viagem condicional à conclusão. No S4 (sobrecarga intencional) a conclusão é baixa e o tempo de viagem dos concluídos não representa os veículos retidos.
3. Uma única rota (O-D oeste-leste por A5); não representa a rede toda.
4. B2 e C1 vêm do Pilot V2 (mesmas rotas, seeds e hashes; ver proveniência); o B0 calibrado foi executado com a árvore de trabalho posterior ao Pilot V2.
5. Pré-final: não substitui a campanha final nem decide contagem de seeds.
