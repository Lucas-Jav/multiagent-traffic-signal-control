# Análise científica final — FINAL_MAIN (200 runs) + FINAL_S5 (90 runs)

> Gerado por `scripts/final_analysis.py` + `scripts/render_final_analysis_md.py`. Nenhuma simulação foi executada;
> nenhum artefato bruto foi alterado. Todos os números vêm das tabelas CSV/parquet desta pasta e são rastreáveis até
> `run_id` / `run_path` em `final_metrics.parquet`. Linguagem: "os resultados indicam", "nas condições simuladas".

## 0. Identidade e população

| Item | Valor |
|---|---|
| `SCIENTIFIC_SOURCE_GIT_SHA` | `176178e36eeafb329a5a1350161be61cf97902b0` |
| `SCIENTIFIC_TREE_SHA256` | `b713917890e2dc65b7c25dfca80c627a7607146539bd2dadf5613f70451cdeff` |
| `FREEZE_MANIFEST_SHA256` | `de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec` |
| Runs analisadas | 290/290 (FINAL_MAIN 200/200; FINAL_S5 90/90) |
| Observação duplicada / run de piloto / calibração / replay incluída | 0 / 0 / 0 / 0 |
| Long paths (S5 C2, seeds 10007/12011/16001) | 12/12 identidades incluídas uma única vez; 290/290 runs legíveis |
| Bootstrap | percentil, 10 000 reamostragens, semente 20260910 (`analysis/statistics.py`); rota de referência: semente-base 20260930 por rótulo (`reference_route.py`) |

**Proveniência dos retries (S5).** `S5_RETRIED = 12`: falha de infraestrutura (limite de 260 caracteres de caminho no Windows ao gravar
`junction_telemetry.parquet`) em `C2_COOPERATIVE_EXPANDED`, seeds 10007, 12011 e 16001, perdas 0/20/50/100%. Foram refeitas com
`--resume --retry-failed` (mesmo código/config/freeze; execução a partir de unidade `subst` curta). Tentativas falhas não geraram
resultados; cada identidade científica contribui **uma** vez (N continua 10 seeds por condição). Detalhe: `artifacts/final-s5/retry-log.json`.
Na análise, os arquivos brutos são abertos com o prefixo de caminho estendido `\\?\` (somente leitura; nada foi renomeado, movido ou regravado).

## 1. Método (congelado)

- Unidade pareada: **cenário + seed**; diferença = tratamento − baseline. N = 10 pares por comparação.
- IC95% = bootstrap percentil das diferenças pareadas (plano estatístico congelado). Não foram usados testes de hipótese nem valores-p.
- Diferença relativa = diferença média / média do baseline (plano congelado); a média das razões por par (implementação congelada) fica em `final_pairwise_summary.csv`.
- Classificação (regra fixada antes de examinar resultados): por métrica-chave, "melhor" só se o IC95% exclui 0 naquele sentido.
  Métricas de serviço: `throughput`, `completion_ratio_offered`, `departure_ratio`. Métricas de atraso/fila: `mean_waiting_time`, `mean_time_loss`, `mean_network_queue_vehicles`.
  Rótulo do cenário: `TRADE_OFF` se há metrica favorável a um lado e outra favorável ao outro; senão o lado melhor; senão `NO_CLEAR_DIFFERENCE`.
  `mean_travel_time` não entra na votação por ser condicional a viagens concluídas.
- **Regra de métricas condicionais.** `mean_waiting_time`, `mean_time_loss` e `mean_travel_time` só existem para viagens concluídas;
  sempre são lidas junto de `departure_ratio`, `completion_ratio_offered`, `never_inserted_vehicle_count` e `unfinished_in_network_count`
  (colunas `ctx_*` e `conditional_warning` em `final_pairwise_summary.csv`).
- Nenhum outlier ou seed foi removido. A regra 1,5×IQR do código congelado sinalizou 209 observações (todas mantidas; `final_outliers_flagged_not_removed.csv`).
- Verificações de consistência: valores recalculados batem com o agregado congelado `combined_metrics.parquet` (4600 valores, 0 divergências);
  as 30 runs do S5 a 0% de perda e a referência B2 reproduzem **exatamente** as runs correspondentes de S2 no FINAL_MAIN (30/30 idênticas), o que indica execução determinística.

## 2. Resultados descritivos (N = 10 por controlador/cenário)

Tabela completa (N, média, mediana, desvio-padrão, IQR, mín., máx. de todas as métricas): `final_controller_summary.csv`.

**S1_BALANCED** (N=10 seeds; média ± desvio-padrão)

| Ctrl | throughput | completion_ratio_offered | departure_ratio | mean_waiting_time | mean_time_loss | mean_travel_time | mean_network_queue_vehicles | max_network_queue_vehicles | mean_stops | mean_depart_delay_seconds | never_inserted_vehicle_count | unfinished_in_network_count | sumo_teleports_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 1805.0 ± 5.7 | 0.967 ± 0.003 | 1.000 ± 0.000 | 58.6 ± 1.3 | 79.0 ± 1.5 | 132.1 ± 1.9 | 29.5 ± 0.6 | 46.9 ± 1.5 | 2.57 ± 0.04 | 0.5 ± 0.1 | 0.0 ± 0.0 | 58.6 ± 4.6 | 0.00 ± 0.00 |
| B1 | 1802.5 ± 7.1 | 0.966 ± 0.002 | 1.000 ± 0.000 | 59.8 ± 1.7 | 79.5 ± 1.8 | 132.5 ± 2.1 | 30.2 ± 0.8 | 47.9 ± 2.8 | 2.52 ± 0.03 | 0.5 ± 0.1 | 0.0 ± 0.0 | 60.3 ± 4.3 | 0.00 ± 0.00 |
| B2 | 1810.3 ± 5.6 | 0.969 ± 0.003 | 1.000 ± 0.000 | 49.7 ± 4.9 | 69.0 ± 4.9 | 122.0 ± 4.8 | 25.3 ± 2.4 | 42.3 ± 2.2 | 2.45 ± 0.06 | 0.5 ± 0.1 | 0.0 ± 0.0 | 55.1 ± 6.1 | 0.00 ± 0.00 |
| C1 | 1804.2 ± 9.5 | 0.965 ± 0.003 | 1.000 ± 0.000 | 67.1 ± 3.4 | 87.0 ± 3.5 | 140.0 ± 3.4 | 33.9 ± 1.7 | 50.2 ± 2.9 | 2.58 ± 0.04 | 0.5 ± 0.1 | 0.0 ± 0.0 | 63.4 ± 5.6 | 0.00 ± 0.00 |
| C2 | 1706.9 ± 28.3 | 0.904 ± 0.017 | 0.998 ± 0.002 | 192.8 ± 17.5 | 220.9 ± 18.9 | 273.5 ± 18.9 | 96.5 ± 8.6 | 156.2 ± 21.1 | 3.46 ± 0.16 | 1.4 ± 0.9 | 2.8 ± 3.7 | 169.2 ± 29.3 | 0.00 ± 0.00 |

**S2_DIRECTIONAL_PEAK** (N=10 seeds; média ± desvio-padrão)

| Ctrl | throughput | completion_ratio_offered | departure_ratio | mean_waiting_time | mean_time_loss | mean_travel_time | mean_network_queue_vehicles | max_network_queue_vehicles | mean_stops | mean_depart_delay_seconds | never_inserted_vehicle_count | unfinished_in_network_count | sumo_teleports_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 1200.1 ± 3.4 | 0.970 ± 0.002 | 1.000 ± 0.000 | 56.8 ± 0.5 | 78.0 ± 0.7 | 130.8 ± 1.0 | 19.0 ± 0.2 | 38.9 ± 1.3 | 2.56 ± 0.02 | 0.5 ± 0.0 | 0.0 ± 0.0 | 35.3 ± 2.9 | 0.00 ± 0.00 |
| B1 | 1196.8 ± 4.9 | 0.967 ± 0.003 | 1.000 ± 0.000 | 71.8 ± 1.1 | 91.1 ± 1.5 | 143.8 ± 1.8 | 24.2 ± 0.4 | 41.9 ± 2.1 | 2.31 ± 0.05 | 0.5 ± 0.0 | 0.0 ± 0.0 | 39.5 ± 3.4 | 0.00 ± 0.00 |
| B2 | 973.0 ± 23.2 | 0.765 ± 0.020 | 0.822 ± 0.022 | 166.0 ± 7.1 | 197.3 ± 7.9 | 249.9 ± 8.0 | 46.1 ± 1.5 | 74.3 ± 4.5 | 3.56 ± 0.09 | 271.9 ± 41.3 | 211.9 ± 26.6 | 67.6 ± 7.2 | 0.00 ± 0.00 |
| C1 | 917.4 ± 17.1 | 0.716 ± 0.015 | 0.761 ± 0.013 | 140.8 ± 4.3 | 167.1 ± 4.9 | 219.6 ± 5.2 | 37.7 ± 1.0 | 58.3 ± 3.2 | 3.04 ± 0.08 | 294.3 ± 12.9 | 285.0 ± 15.8 | 52.9 ± 3.9 | 0.00 ± 0.00 |
| C2 | 841.4 ± 11.8 | 0.651 ± 0.009 | 0.696 ± 0.010 | 163.6 ± 3.1 | 190.4 ± 3.5 | 242.9 ± 3.8 | 40.2 ± 0.6 | 60.2 ± 1.9 | 3.10 ± 0.07 | 357.7 ± 22.5 | 362.3 ± 11.7 | 53.4 ± 3.3 | 0.00 ± 0.00 |

**S3_DEMAND_SHIFT** (N=10 seeds; média ± desvio-padrão)

| Ctrl | throughput | completion_ratio_offered | departure_ratio | mean_waiting_time | mean_time_loss | mean_travel_time | mean_network_queue_vehicles | max_network_queue_vehicles | mean_stops | mean_depart_delay_seconds | never_inserted_vehicle_count | unfinished_in_network_count | sumo_teleports_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 1956.4 ± 27.3 | 0.935 ± 0.014 | 0.999 ± 0.002 | 72.3 ± 3.7 | 96.4 ± 4.4 | 150.7 ± 4.2 | 42.8 ± 3.4 | 99.8 ± 19.6 | 2.87 ± 0.09 | 0.5 ± 0.1 | 1.6 ± 3.8 | 130.6 ± 24.8 | 0.00 ± 0.00 |
| B1 | 1955.9 ± 8.7 | 0.935 ± 0.004 | 0.997 ± 0.002 | 83.3 ± 2.9 | 108.5 ± 3.3 | 162.9 ± 3.5 | 47.6 ± 1.7 | 96.7 ± 6.1 | 3.07 ± 0.05 | 2.0 ± 1.1 | 6.3 ± 4.7 | 125.6 ± 9.5 | 0.00 ± 0.00 |
| B2 | 1944.0 ± 6.3 | 0.927 ± 0.003 | 0.989 ± 0.003 | 78.5 ± 4.7 | 104.3 ± 5.0 | 158.6 ± 4.9 | 45.0 ± 2.5 | 99.1 ± 6.7 | 3.07 ± 0.06 | 5.9 ± 1.8 | 21.8 ± 6.3 | 124.6 ± 6.7 | 0.00 ± 0.00 |
| C1 | 1911.1 ± 14.2 | 0.910 ± 0.006 | 0.976 ± 0.003 | 95.3 ± 2.7 | 120.4 ± 3.0 | 174.5 ± 3.1 | 53.3 ± 1.7 | 110.6 ± 7.5 | 3.06 ± 0.04 | 13.4 ± 2.1 | 48.5 ± 5.5 | 133.0 ± 8.4 | 0.00 ± 0.00 |
| C2 | 1709.2 ± 32.2 | 0.805 ± 0.014 | 0.907 ± 0.009 | 210.8 ± 16.3 | 241.8 ± 17.6 | 295.2 ± 17.8 | 108.4 ± 7.4 | 189.0 ± 15.3 | 3.71 ± 0.16 | 44.7 ± 3.9 | 187.2 ± 17.5 | 207.5 ± 17.3 | 0.00 ± 0.00 |

**S4_LOCAL_SATURATION** (N=10 seeds; média ± desvio-padrão)

| Ctrl | throughput | completion_ratio_offered | departure_ratio | mean_waiting_time | mean_time_loss | mean_travel_time | mean_network_queue_vehicles | max_network_queue_vehicles | mean_stops | mean_depart_delay_seconds | never_inserted_vehicle_count | unfinished_in_network_count | sumo_teleports_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 1476.3 ± 15.8 | 0.352 ± 0.004 | 0.471 ± 0.006 | 649.8 ± 22.7 | 802.1 ± 29.8 | 861.1 ± 30.1 | 335.1 ± 11.7 | 397.9 ± 10.5 | 17.24 ± 0.74 | 454.6 ± 16.4 | 1899.1 ± 21.0 | 425.0 ± 19.4 | 2.80 ± 1.62 |
| B1 | 1249.1 ± 18.1 | 0.285 ± 0.005 | 0.428 ± 0.010 | 876.0 ± 24.3 | 1135.0 ± 32.8 | 1198.0 ± 32.6 | 352.0 ± 8.8 | 421.7 ± 7.2 | 29.23 ± 1.05 | 750.0 ± 19.0 | 2051.0 ± 35.3 | 512.4 ± 26.9 | 0.00 ± 0.00 |
| B2 | 1227.3 ± 101.6 | 0.277 ± 0.028 | 0.411 ± 0.029 | 913.8 ± 43.1 | 1151.5 ± 50.7 | 1215.3 ± 51.3 | 356.4 ± 6.6 | 450.6 ± 13.5 | 26.33 ± 1.19 | 731.8 ± 58.0 | 2112.3 ± 105.6 | 482.2 ± 11.7 | 0.30 ± 0.95 |
| C1 | 1334.9 ± 20.8 | 0.307 ± 0.005 | 0.414 ± 0.004 | 735.4 ± 25.0 | 890.7 ± 32.7 | 954.3 ± 33.2 | 294.9 ± 6.7 | 356.1 ± 10.8 | 16.69 ± 1.06 | 854.5 ± 25.4 | 2103.4 ± 14.3 | 383.7 ± 8.3 | 0.00 ± 0.00 |
| C2 | 1364.2 ± 28.2 | 0.310 ± 0.007 | 0.407 ± 0.008 | 613.7 ± 23.4 | 708.1 ± 28.8 | 771.4 ± 29.0 | 254.5 ± 6.7 | 319.0 ± 7.2 | 9.53 ± 0.61 | 993.8 ± 22.3 | 2128.8 ± 27.0 | 346.0 ± 12.1 | 0.00 ± 0.00 |

## 3. Comparação primária: B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT

B2 e C1 pertencem à mesma família de pressão local; C1 acrescenta informação compacta dos vizinhos.

Classificação por cenário (todas as comparações congeladas):

| Cenário | B2 → C1 | B0 → B2 | B0 → B1 | C1 → C2 |
|---|---|---|---|---|
| S1_BALANCED | B2_BETTER | B2_BETTER | NO_CLEAR_DIFFERENCE | C1_BETTER |
| S2_DIRECTIONAL_PEAK | TRADE_OFF | B0_BETTER | B0_BETTER | C1_BETTER |
| S3_DEMAND_SHIFT | B2_BETTER | B0_BETTER | B0_BETTER | C1_BETTER |
| S4_LOCAL_SATURATION | C1_BETTER | B0_BETTER | B0_BETTER | TRADE_OFF |

| Cen. | Métrica | B2 média | C1 média | dif. (trat.−base) (rel.) IC95% | seeds favoráveis | efeito |
|---|---|---|---|---|---|---|
| S1 | throughput | 1810.3 | 1804.2 | -6.1 (-0.3%) [-11.20; -0.90] | 3/10 | baseline melhor |
| S1 | completion_ratio_offered | 0.969 | 0.965 | -0.005 (-0.5%) [-0.01; -0.00] | 1/10 | baseline melhor |
| S1 | departure_ratio | 1.000 | 1.000 | +0.000 (+0.0%) [0.00; 0.00] | 0/10 | sem diferença clara |
| S1 | mean_waiting_time | 49.7 | 67.1 | +17.4 (+35.0%) [14.53; 20.38] | 0/10 | baseline melhor |
| S1 | mean_time_loss | 69.0 | 87.0 | +18.0 (+26.1%) [15.01; 21.11] | 0/10 | baseline melhor |
| S1 | mean_travel_time | 122.0 | 140.0 | +18.0 (+14.7%) [15.01; 21.08] | 0/10 | baseline melhor |
| S1 | mean_network_queue_vehicles | 25.3 | 33.9 | +8.6 (+34.2%) [7.16; 10.16] | 0/10 | baseline melhor |
| S1 | max_network_queue_vehicles | 42.3 | 50.2 | +7.9 (+18.7%) [5.20; 10.30] | 0/10 | baseline melhor |
| S1 | mean_stops | 2.45 | 2.58 | +0.13 (+5.4%) [0.09; 0.17] | 0/10 | baseline melhor |
| S1 | mean_depart_delay_seconds | 0.5 | 0.5 | +0.0 (+0.0%) [0.00; 0.00] | 0/10 | sem diferença clara |
| S1 | never_inserted_vehicle_count | 0.0 | 0.0 | +0.0 [0.00; 0.00] | 0/10 | sem diferença clara |
| S1 | unfinished_in_network_count | 55.1 | 63.4 | +8.3 (+15.1%) [3.40; 12.30] | 1/10 | baseline melhor |
| S1 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S2 | throughput | 973.0 | 917.4 | -55.6 (-5.7%) [-75.50; -38.60] | 0/10 | baseline melhor |
| S2 | completion_ratio_offered | 0.765 | 0.716 | -0.049 (-6.4%) [-0.07; -0.03] | 0/10 | baseline melhor |
| S2 | departure_ratio | 0.822 | 0.761 | -0.061 (-7.5%) [-0.08; -0.04] | 0/10 | baseline melhor |
| S2 | mean_waiting_time | 166.0 | 140.8 | -25.3 (-15.2%) [-30.83; -20.28] | 10/10 | tratamento melhor |
| S2 | mean_time_loss | 197.3 | 167.1 | -30.3 (-15.3%) [-36.41; -24.89] | 10/10 | tratamento melhor |
| S2 | mean_travel_time | 249.9 | 219.6 | -30.3 (-12.1%) [-36.44; -24.89] | 10/10 | tratamento melhor |
| S2 | mean_network_queue_vehicles | 46.1 | 37.7 | -8.4 (-18.3%) [-9.62; -7.42] | 10/10 | tratamento melhor |
| S2 | max_network_queue_vehicles | 74.3 | 58.3 | -16.0 (-21.5%) [-18.90; -13.10] | 10/10 | tratamento melhor |
| S2 | mean_stops | 3.56 | 3.04 | -0.52 (-14.6%) [-0.58; -0.47] | 10/10 | tratamento melhor |
| S2 | mean_depart_delay_seconds | 271.9 | 294.3 | +22.5 (+8.3%) [1.68; 46.17] | 4/10 | baseline melhor |
| S2 | never_inserted_vehicle_count | 211.9 | 285.0 | +73.1 (+34.5%) [52.40; 93.30] | 0/10 | baseline melhor |
| S2 | unfinished_in_network_count | 67.6 | 52.9 | -14.7 (-21.7%) [-18.30; -11.00] | 10/10 | tratamento melhor |
| S2 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S3 | throughput | 1944.0 | 1911.1 | -32.9 (-1.7%) [-38.70; -27.10] | 0/10 | baseline melhor |
| S3 | completion_ratio_offered | 0.927 | 0.910 | -0.017 (-1.9%) [-0.02; -0.02] | 0/10 | baseline melhor |
| S3 | departure_ratio | 0.989 | 0.976 | -0.013 (-1.3%) [-0.02; -0.01] | 0/10 | baseline melhor |
| S3 | mean_waiting_time | 78.5 | 95.3 | +16.8 (+21.4%) [14.42; 19.28] | 0/10 | baseline melhor |
| S3 | mean_time_loss | 104.3 | 120.4 | +16.0 (+15.3%) [13.43; 18.69] | 0/10 | baseline melhor |
| S3 | mean_travel_time | 158.6 | 174.5 | +15.9 (+10.0%) [13.27; 18.59] | 0/10 | baseline melhor |
| S3 | mean_network_queue_vehicles | 45.0 | 53.3 | +8.3 (+18.5%) [6.97; 9.74] | 0/10 | baseline melhor |
| S3 | max_network_queue_vehicles | 99.1 | 110.6 | +11.5 (+11.6%) [7.70; 15.00] | 0/10 | baseline melhor |
| S3 | mean_stops | 3.07 | 3.06 | -0.01 (-0.2%) [-0.04; 0.03] | 4/10 | sem diferença clara |
| S3 | mean_depart_delay_seconds | 5.9 | 13.4 | +7.6 (+129.3%) [5.86; 9.31] | 0/10 | baseline melhor |
| S3 | never_inserted_vehicle_count | 21.8 | 48.5 | +26.7 (+122.5%) [22.30; 31.10] | 0/10 | baseline melhor |
| S3 | unfinished_in_network_count | 124.6 | 133.0 | +8.4 (+6.7%) [3.40; 13.10] | 2/10 | baseline melhor |
| S3 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S4 | throughput | 1227.3 | 1334.9 | +107.6 (+8.8%) [69.10; 169.80] | 10/10 | tratamento melhor |
| S4 | completion_ratio_offered | 0.277 | 0.307 | +0.030 (+10.8%) [0.02; 0.05] | 10/10 | tratamento melhor |
| S4 | departure_ratio | 0.411 | 0.414 | +0.002 (+0.6%) [-0.01; 0.02] | 4/10 | sem diferença clara |
| S4 | mean_waiting_time | 913.8 | 735.4 | -178.4 (-19.5%) [-196.54; -158.67] | 10/10 | tratamento melhor |
| S4 | mean_time_loss | 1151.5 | 890.7 | -260.8 (-22.6%) [-281.41; -237.77] | 10/10 | tratamento melhor |
| S4 | mean_travel_time | 1215.3 | 954.3 | -261.1 (-21.5%) [-281.85; -237.99] | 10/10 | tratamento melhor |
| S4 | mean_network_queue_vehicles | 356.4 | 294.9 | -61.5 (-17.3%) [-65.59; -57.87] | 10/10 | tratamento melhor |
| S4 | max_network_queue_vehicles | 450.6 | 356.1 | -94.5 (-21.0%) [-100.90; -87.90] | 10/10 | tratamento melhor |
| S4 | mean_stops | 26.33 | 16.69 | -9.64 (-36.6%) [-10.23; -9.03] | 10/10 | tratamento melhor |
| S4 | mean_depart_delay_seconds | 731.8 | 854.5 | +122.7 (+16.8%) [89.44; 162.00] | 0/10 | baseline melhor |
| S4 | never_inserted_vehicle_count | 2112.3 | 2103.4 | -8.9 (-0.4%) [-76.80; 35.90] | 4/10 | sem diferença clara |
| S4 | unfinished_in_network_count | 482.2 | 383.7 | -98.5 (-20.4%) [-106.90; -89.70] | 10/10 | tratamento melhor |
| S4 | sumo_teleports_total | 0.30 | 0.00 | -0.30 (-100.0%) [-0.90; 0.00] | 1/10 | sem diferença clara |

## 4. Comparações secundárias

### 4.1 B0_FIXED_CALIBRATED vs B2_LOCAL_PRESSURE (efeito da adaptação por pressão local)

| Cen. | Métrica | B0 média | B2 média | dif. (trat.−base) (rel.) IC95% | seeds favoráveis | efeito |
|---|---|---|---|---|---|---|
| S1 | throughput | 1805.0 | 1810.3 | +5.3 (+0.3%) [1.60; 9.40] | 7/10 | tratamento melhor |
| S1 | completion_ratio_offered | 0.967 | 0.969 | +0.002 (+0.2%) [-0.00; 0.00] | 6/10 | sem diferença clara |
| S1 | departure_ratio | 1.000 | 1.000 | +0.000 (+0.0%) [0.00; 0.00] | 0/10 | sem diferença clara |
| S1 | mean_waiting_time | 58.6 | 49.7 | -8.9 (-15.2%) [-11.64; -5.76] | 9/10 | tratamento melhor |
| S1 | mean_time_loss | 79.0 | 69.0 | -10.0 (-12.7%) [-12.87; -6.83] | 10/10 | tratamento melhor |
| S1 | mean_travel_time | 132.1 | 122.0 | -10.1 (-7.6%) [-12.91; -6.85] | 10/10 | tratamento melhor |
| S1 | mean_network_queue_vehicles | 29.5 | 25.3 | -4.3 (-14.4%) [-5.63; -2.71] | 9/10 | tratamento melhor |
| S1 | max_network_queue_vehicles | 46.9 | 42.3 | -4.6 (-9.8%) [-5.80; -3.40] | 10/10 | tratamento melhor |
| S1 | mean_stops | 2.57 | 2.45 | -0.12 (-4.8%) [-0.15; -0.09] | 10/10 | tratamento melhor |
| S1 | mean_depart_delay_seconds | 0.5 | 0.5 | +0.0 (+0.0%) [0.00; 0.00] | 0/10 | sem diferença clara |
| S1 | never_inserted_vehicle_count | 0.0 | 0.0 | +0.0 [0.00; 0.00] | 0/10 | sem diferença clara |
| S1 | unfinished_in_network_count | 58.6 | 55.1 | -3.5 (-6.0%) [-7.40; 0.00] | 6/10 | sem diferença clara |
| S1 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S2 | throughput | 1200.1 | 973.0 | -227.1 (-18.9%) [-240.00; -213.30] | 0/10 | baseline melhor |
| S2 | completion_ratio_offered | 0.970 | 0.765 | -0.205 (-21.1%) [-0.22; -0.19] | 0/10 | baseline melhor |
| S2 | departure_ratio | 1.000 | 0.822 | -0.178 (-17.8%) [-0.19; -0.16] | 0/10 | baseline melhor |
| S2 | mean_waiting_time | 56.8 | 166.0 | +109.2 (+192.4%) [105.11; 113.67] | 0/10 | baseline melhor |
| S2 | mean_time_loss | 78.0 | 197.3 | +119.3 (+153.0%) [114.76; 124.23] | 0/10 | baseline melhor |
| S2 | mean_travel_time | 130.8 | 249.9 | +119.1 (+91.1%) [114.52; 123.95] | 0/10 | baseline melhor |
| S2 | mean_network_queue_vehicles | 19.0 | 46.1 | +27.1 (+142.1%) [26.09; 27.99] | 0/10 | baseline melhor |
| S2 | max_network_queue_vehicles | 38.9 | 74.3 | +35.4 (+91.0%) [32.30; 38.30] | 0/10 | baseline melhor |
| S2 | mean_stops | 2.56 | 3.56 | +1.00 (+39.3%) [0.96; 1.05] | 0/10 | baseline melhor |
| S2 | mean_depart_delay_seconds | 0.5 | 271.9 | +271.4 (+54635.4%) [245.75; 294.26] | 0/10 | baseline melhor |
| S2 | never_inserted_vehicle_count | 0.0 | 211.9 | +211.9 [196.00; 226.90] | 0/10 | baseline melhor |
| S2 | unfinished_in_network_count | 35.3 | 67.6 | +32.3 (+91.5%) [27.80; 36.70] | 0/10 | baseline melhor |
| S2 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S3 | throughput | 1956.4 | 1944.0 | -12.4 (-0.6%) [-26.20; 1.60] | 5/10 | sem diferença clara |
| S3 | completion_ratio_offered | 0.935 | 0.927 | -0.007 (-0.8%) [-0.01; -0.00] | 3/10 | baseline melhor |
| S3 | departure_ratio | 0.999 | 0.989 | -0.010 (-1.0%) [-0.01; -0.01] | 0/10 | baseline melhor |
| S3 | mean_waiting_time | 72.3 | 78.5 | +6.2 (+8.6%) [3.85; 8.89] | 1/10 | baseline melhor |
| S3 | mean_time_loss | 96.4 | 104.3 | +8.0 (+8.3%) [5.31; 10.79] | 0/10 | baseline melhor |
| S3 | mean_travel_time | 150.7 | 158.6 | +7.9 (+5.2%) [5.26; 10.72] | 0/10 | baseline melhor |
| S3 | mean_network_queue_vehicles | 42.8 | 45.0 | +2.1 (+5.0%) [0.61; 3.59] | 2/10 | baseline melhor |
| S3 | max_network_queue_vehicles | 99.8 | 99.1 | -0.7 (-0.7%) [-10.30; 9.20] | 6/10 | sem diferença clara |
| S3 | mean_stops | 2.87 | 3.07 | +0.19 (+6.7%) [0.15; 0.24] | 0/10 | baseline melhor |
| S3 | mean_depart_delay_seconds | 0.5 | 5.9 | +5.3 (+1027.8%) [4.24; 6.28] | 0/10 | baseline melhor |
| S3 | never_inserted_vehicle_count | 1.6 | 21.8 | +20.2 (+1262.5%) [16.70; 23.60] | 0/10 | baseline melhor |
| S3 | unfinished_in_network_count | 130.6 | 124.6 | -6.0 (-4.6%) [-19.90; 7.50] | 5/10 | sem diferença clara |
| S3 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S4 | throughput | 1476.3 | 1227.3 | -249.0 (-16.9%) [-311.70; -207.40] | 0/10 | baseline melhor |
| S4 | completion_ratio_offered | 0.352 | 0.277 | -0.075 (-21.4%) [-0.09; -0.06] | 0/10 | baseline melhor |
| S4 | departure_ratio | 0.471 | 0.411 | -0.059 (-12.6%) [-0.08; -0.05] | 0/10 | baseline melhor |
| S4 | mean_waiting_time | 649.8 | 913.8 | +264.0 (+40.6%) [245.88; 280.82] | 0/10 | baseline melhor |
| S4 | mean_time_loss | 802.1 | 1151.5 | +349.4 (+43.6%) [329.73; 367.42] | 0/10 | baseline melhor |
| S4 | mean_travel_time | 861.1 | 1215.3 | +354.2 (+41.1%) [334.29; 372.31] | 0/10 | baseline melhor |
| S4 | mean_network_queue_vehicles | 335.1 | 356.4 | +21.3 (+6.4%) [15.07; 27.74] | 0/10 | baseline melhor |
| S4 | max_network_queue_vehicles | 397.9 | 450.6 | +52.7 (+13.2%) [44.60; 61.00] | 0/10 | baseline melhor |
| S4 | mean_stops | 17.24 | 26.33 | +9.08 (+52.7%) [8.55; 9.57] | 0/10 | baseline melhor |
| S4 | mean_depart_delay_seconds | 454.6 | 731.8 | +277.2 (+61.0%) [238.22; 310.24] | 0/10 | baseline melhor |
| S4 | never_inserted_vehicle_count | 1899.1 | 2112.3 | +213.2 (+11.2%) [163.50; 280.30] | 0/10 | baseline melhor |
| S4 | unfinished_in_network_count | 425.0 | 482.2 | +57.2 (+13.5%) [43.70; 70.40] | 0/10 | baseline melhor |
| S4 | sumo_teleports_total | 2.80 | 0.30 | -2.50 (-89.3%) [-3.50; -1.60] | 10/10 | tratamento melhor |

Pós-choque (S3, `post_shock_queue_auc_vehicle_seconds`): B0 100739, B1 116447,
B2 115334, C1 130943, C2 251136 veículo·s;
B0→B2 +14596 (+14.5%) [9557.70; 19852.67]; B2→C1 +15608 (+13.5%) [12937.65; 18707.47].

### 4.2 B0_FIXED_CALIBRATED vs B1_LOCAL_ADAPTIVE

| Cen. | Métrica | B0 média | B1 média | dif. (trat.−base) (rel.) IC95% | seeds favoráveis | efeito |
|---|---|---|---|---|---|---|
| S1 | throughput | 1805.0 | 1802.5 | -2.5 (-0.1%) [-6.90; 2.00] | 4/10 | sem diferença clara |
| S1 | completion_ratio_offered | 0.967 | 0.966 | -0.001 (-0.1%) [-0.00; 0.00] | 3/10 | sem diferença clara |
| S1 | departure_ratio | 1.000 | 1.000 | +0.000 (+0.0%) [0.00; 0.00] | 0/10 | sem diferença clara |
| S1 | mean_waiting_time | 58.6 | 59.8 | +1.2 (+2.0%) [-0.54; 2.67] | 2/10 | sem diferença clara |
| S1 | mean_time_loss | 79.0 | 79.5 | +0.5 (+0.6%) [-1.37; 2.03] | 2/10 | sem diferença clara |
| S1 | mean_travel_time | 132.1 | 132.5 | +0.4 (+0.3%) [-1.39; 2.01] | 2/10 | sem diferença clara |
| S1 | mean_network_queue_vehicles | 29.5 | 30.2 | +0.7 (+2.2%) [-0.18; 1.38] | 2/10 | sem diferença clara |
| S1 | max_network_queue_vehicles | 46.9 | 47.9 | +1.0 (+2.1%) [-1.10; 3.00] | 3/10 | sem diferença clara |
| S1 | mean_stops | 2.57 | 2.52 | -0.05 (-1.9%) [-0.07; -0.03] | 10/10 | tratamento melhor |
| S1 | mean_depart_delay_seconds | 0.5 | 0.5 | +0.0 (+0.0%) [0.00; 0.00] | 0/10 | sem diferença clara |
| S1 | never_inserted_vehicle_count | 0.0 | 0.0 | +0.0 [0.00; 0.00] | 0/10 | sem diferença clara |
| S1 | unfinished_in_network_count | 58.6 | 60.3 | +1.7 (+2.9%) [-0.90; 4.00] | 3/10 | sem diferença clara |
| S1 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S2 | throughput | 1200.1 | 1196.8 | -3.3 (-0.3%) [-7.20; 0.90] | 1/10 | sem diferença clara |
| S2 | completion_ratio_offered | 0.970 | 0.967 | -0.004 (-0.4%) [-0.01; -0.00] | 1/10 | baseline melhor |
| S2 | departure_ratio | 1.000 | 1.000 | +0.000 (+0.0%) [0.00; 0.00] | 0/10 | sem diferença clara |
| S2 | mean_waiting_time | 56.8 | 71.8 | +15.0 (+26.4%) [14.35; 15.72] | 0/10 | baseline melhor |
| S2 | mean_time_loss | 78.0 | 91.1 | +13.1 (+16.8%) [12.40; 13.92] | 0/10 | baseline melhor |
| S2 | mean_travel_time | 130.8 | 143.8 | +13.1 (+10.0%) [12.38; 13.86] | 0/10 | baseline melhor |
| S2 | mean_network_queue_vehicles | 19.0 | 24.2 | +5.1 (+26.9%) [4.91; 5.36] | 0/10 | baseline melhor |
| S2 | max_network_queue_vehicles | 38.9 | 41.9 | +3.0 (+7.7%) [1.90; 4.20] | 0/10 | baseline melhor |
| S2 | mean_stops | 2.56 | 2.31 | -0.25 (-9.8%) [-0.27; -0.23] | 10/10 | tratamento melhor |
| S2 | mean_depart_delay_seconds | 0.5 | 0.5 | +0.0 (+0.8%) [0.00; 0.01] | 0/10 | sem diferença clara |
| S2 | never_inserted_vehicle_count | 0.0 | 0.0 | +0.0 [0.00; 0.00] | 0/10 | sem diferença clara |
| S2 | unfinished_in_network_count | 35.3 | 39.5 | +4.2 (+11.9%) [2.10; 6.30] | 1/10 | baseline melhor |
| S2 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S3 | throughput | 1956.4 | 1955.9 | -0.5 (-0.0%) [-18.00; 16.70] | 5/10 | sem diferença clara |
| S3 | completion_ratio_offered | 0.935 | 0.935 | +0.000 (+0.0%) [-0.01; 0.01] | 5/10 | sem diferença clara |
| S3 | departure_ratio | 0.999 | 0.997 | -0.002 (-0.2%) [-0.00; -0.00] | 2/10 | baseline melhor |
| S3 | mean_waiting_time | 72.3 | 83.3 | +11.0 (+15.3%) [8.63; 13.66] | 0/10 | baseline melhor |
| S3 | mean_time_loss | 96.4 | 108.5 | +12.2 (+12.6%) [9.35; 15.20] | 0/10 | baseline melhor |
| S3 | mean_travel_time | 150.7 | 162.9 | +12.2 (+8.1%) [9.39; 15.12] | 0/10 | baseline melhor |
| S3 | mean_network_queue_vehicles | 42.8 | 47.6 | +4.7 (+11.1%) [2.67; 6.99] | 0/10 | baseline melhor |
| S3 | max_network_queue_vehicles | 99.8 | 96.7 | -3.1 (-3.1%) [-16.60; 9.90] | 6/10 | sem diferença clara |
| S3 | mean_stops | 2.87 | 3.07 | +0.19 (+6.7%) [0.14; 0.25] | 0/10 | baseline melhor |
| S3 | mean_depart_delay_seconds | 0.5 | 2.0 | +1.5 (+292.2%) [0.90; 2.12] | 0/10 | baseline melhor |
| S3 | never_inserted_vehicle_count | 1.6 | 6.3 | +4.7 (+293.8%) [1.60; 8.00] | 2/10 | baseline melhor |
| S3 | unfinished_in_network_count | 130.6 | 125.6 | -5.0 (-3.8%) [-21.00; 10.80] | 5/10 | sem diferença clara |
| S3 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S4 | throughput | 1476.3 | 1249.1 | -227.2 (-15.4%) [-237.90; -217.60] | 0/10 | baseline melhor |
| S4 | completion_ratio_offered | 0.352 | 0.285 | -0.067 (-18.9%) [-0.07; -0.06] | 0/10 | baseline melhor |
| S4 | departure_ratio | 0.471 | 0.428 | -0.042 (-9.0%) [-0.05; -0.04] | 0/10 | baseline melhor |
| S4 | mean_waiting_time | 649.8 | 876.0 | +226.3 (+34.8%) [207.45; 243.79] | 0/10 | baseline melhor |
| S4 | mean_time_loss | 802.1 | 1135.0 | +333.0 (+41.5%) [309.06; 355.34] | 0/10 | baseline melhor |
| S4 | mean_travel_time | 861.1 | 1198.0 | +336.9 (+39.1%) [312.99; 359.20] | 0/10 | baseline melhor |
| S4 | mean_network_queue_vehicles | 335.1 | 352.0 | +16.9 (+5.0%) [8.66; 25.29] | 1/10 | baseline melhor |
| S4 | max_network_queue_vehicles | 397.9 | 421.7 | +23.8 (+6.0%) [16.30; 31.40] | 0/10 | baseline melhor |
| S4 | mean_stops | 17.24 | 29.23 | +11.99 (+69.5%) [11.41; 12.56] | 0/10 | baseline melhor |
| S4 | mean_depart_delay_seconds | 454.6 | 750.0 | +295.4 (+65.0%) [279.02; 311.64] | 0/10 | baseline melhor |
| S4 | never_inserted_vehicle_count | 1899.1 | 2051.0 | +151.9 (+8.0%) [131.60; 171.20] | 0/10 | baseline melhor |
| S4 | unfinished_in_network_count | 425.0 | 512.4 | +87.4 (+20.6%) [68.00; 106.60] | 0/10 | baseline melhor |
| S4 | sumo_teleports_total | 2.80 | 0.00 | -2.80 (-100.0%) [-3.80; -1.90] | 10/10 | tratamento melhor |

### 4.3 C1_COOPERATIVE_COMPACT vs C2_COOPERATIVE_EXPANDED

| Cen. | Métrica | C1 média | C2 média | dif. (trat.−base) (rel.) IC95% | seeds favoráveis | efeito |
|---|---|---|---|---|---|---|
| S1 | throughput | 1804.2 | 1706.9 | -97.3 (-5.4%) [-112.20; -79.10] | 0/10 | baseline melhor |
| S1 | completion_ratio_offered | 0.965 | 0.904 | -0.061 (-6.3%) [-0.07; -0.05] | 0/10 | baseline melhor |
| S1 | departure_ratio | 1.000 | 0.998 | -0.002 (-0.2%) [-0.00; -0.00] | 0/10 | baseline melhor |
| S1 | mean_waiting_time | 67.1 | 192.8 | +125.7 (+187.4%) [113.32; 136.01] | 0/10 | baseline melhor |
| S1 | mean_time_loss | 87.0 | 220.9 | +133.9 (+153.9%) [120.60; 144.93] | 0/10 | baseline melhor |
| S1 | mean_travel_time | 140.0 | 273.5 | +133.5 (+95.4%) [120.29; 144.55] | 0/10 | baseline melhor |
| S1 | mean_network_queue_vehicles | 33.9 | 96.5 | +62.6 (+184.5%) [56.30; 67.51] | 0/10 | baseline melhor |
| S1 | max_network_queue_vehicles | 50.2 | 156.2 | +106.0 (+211.2%) [93.50; 118.20] | 0/10 | baseline melhor |
| S1 | mean_stops | 2.58 | 3.46 | +0.89 (+34.4%) [0.77; 0.99] | 0/10 | baseline melhor |
| S1 | mean_depart_delay_seconds | 0.5 | 1.4 | +1.0 (+195.0%) [0.47; 1.48] | 0/10 | baseline melhor |
| S1 | never_inserted_vehicle_count | 0.0 | 2.8 | +2.8 [0.90; 5.20] | 0/10 | baseline melhor |
| S1 | unfinished_in_network_count | 63.4 | 169.2 | +105.8 (+166.9%) [86.90; 120.30] | 0/10 | baseline melhor |
| S1 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S2 | throughput | 917.4 | 841.4 | -76.0 (-8.3%) [-86.90; -63.80] | 0/10 | baseline melhor |
| S2 | completion_ratio_offered | 0.716 | 0.651 | -0.065 (-9.1%) [-0.07; -0.06] | 0/10 | baseline melhor |
| S2 | departure_ratio | 0.761 | 0.696 | -0.065 (-8.5%) [-0.07; -0.06] | 0/10 | baseline melhor |
| S2 | mean_waiting_time | 140.8 | 163.6 | +22.8 (+16.2%) [20.59; 25.17] | 0/10 | baseline melhor |
| S2 | mean_time_loss | 167.1 | 190.4 | +23.3 (+14.0%) [20.98; 25.85] | 0/10 | baseline melhor |
| S2 | mean_travel_time | 219.6 | 242.9 | +23.2 (+10.6%) [20.88; 25.81] | 0/10 | baseline melhor |
| S2 | mean_network_queue_vehicles | 37.7 | 40.2 | +2.5 (+6.7%) [2.14; 2.98] | 0/10 | baseline melhor |
| S2 | max_network_queue_vehicles | 58.3 | 60.2 | +1.9 (+3.3%) [0.40; 3.50] | 2/10 | baseline melhor |
| S2 | mean_stops | 3.04 | 3.10 | +0.06 (+1.9%) [0.03; 0.09] | 0/10 | baseline melhor |
| S2 | mean_depart_delay_seconds | 294.3 | 357.7 | +63.4 (+21.5%) [51.32; 74.91] | 0/10 | baseline melhor |
| S2 | never_inserted_vehicle_count | 285.0 | 362.3 | +77.3 (+27.1%) [66.50; 86.90] | 0/10 | baseline melhor |
| S2 | unfinished_in_network_count | 52.9 | 53.4 | +0.5 (+0.9%) [-2.00; 2.80] | 4/10 | sem diferença clara |
| S2 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S3 | throughput | 1911.1 | 1709.2 | -201.9 (-10.6%) [-225.00; -179.90] | 0/10 | baseline melhor |
| S3 | completion_ratio_offered | 0.910 | 0.805 | -0.106 (-11.6%) [-0.12; -0.10] | 0/10 | baseline melhor |
| S3 | departure_ratio | 0.976 | 0.907 | -0.069 (-7.0%) [-0.07; -0.06] | 0/10 | baseline melhor |
| S3 | mean_waiting_time | 95.3 | 210.8 | +115.5 (+121.2%) [105.43; 126.20] | 0/10 | baseline melhor |
| S3 | mean_time_loss | 120.4 | 241.8 | +121.4 (+100.9%) [110.59; 132.99] | 0/10 | baseline melhor |
| S3 | mean_travel_time | 174.5 | 295.2 | +120.7 (+69.2%) [109.94; 132.20] | 0/10 | baseline melhor |
| S3 | mean_network_queue_vehicles | 53.3 | 108.4 | +55.1 (+103.3%) [50.26; 59.98] | 0/10 | baseline melhor |
| S3 | max_network_queue_vehicles | 110.6 | 189.0 | +78.4 (+70.9%) [67.70; 88.50] | 0/10 | baseline melhor |
| S3 | mean_stops | 3.06 | 3.71 | +0.65 (+21.4%) [0.56; 0.76] | 0/10 | baseline melhor |
| S3 | mean_depart_delay_seconds | 13.4 | 44.7 | +31.3 (+232.9%) [28.07; 34.31] | 0/10 | baseline melhor |
| S3 | never_inserted_vehicle_count | 48.5 | 187.2 | +138.7 (+286.0%) [126.60; 151.20] | 0/10 | baseline melhor |
| S3 | unfinished_in_network_count | 133.0 | 207.5 | +74.5 (+56.0%) [63.90; 83.80] | 0/10 | baseline melhor |
| S3 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |
| S4 | throughput | 1334.9 | 1364.2 | +29.3 (+2.2%) [16.70; 41.90] | 8/10 | tratamento melhor |
| S4 | completion_ratio_offered | 0.307 | 0.310 | +0.003 (+1.1%) [0.00; 0.01] | 7/10 | tratamento melhor |
| S4 | departure_ratio | 0.414 | 0.407 | -0.007 (-1.7%) [-0.01; -0.00] | 2/10 | baseline melhor |
| S4 | mean_waiting_time | 735.4 | 613.7 | -121.7 (-16.5%) [-138.84; -103.82] | 10/10 | tratamento melhor |
| S4 | mean_time_loss | 890.7 | 708.1 | -182.6 (-20.5%) [-204.86; -159.48] | 10/10 | tratamento melhor |
| S4 | mean_travel_time | 954.3 | 771.4 | -182.9 (-19.2%) [-205.20; -159.68] | 10/10 | tratamento melhor |
| S4 | mean_network_queue_vehicles | 294.9 | 254.5 | -40.4 (-13.7%) [-46.08; -34.58] | 10/10 | tratamento melhor |
| S4 | max_network_queue_vehicles | 356.1 | 319.0 | -37.1 (-10.4%) [-45.30; -28.90] | 10/10 | tratamento melhor |
| S4 | mean_stops | 16.69 | 9.53 | -7.15 (-42.9%) [-7.81; -6.46] | 10/10 | tratamento melhor |
| S4 | mean_depart_delay_seconds | 854.5 | 993.8 | +139.3 (+16.3%) [117.42; 160.47] | 0/10 | baseline melhor |
| S4 | never_inserted_vehicle_count | 2103.4 | 2128.8 | +25.4 (+1.2%) [13.00; 38.50] | 2/10 | baseline melhor |
| S4 | unfinished_in_network_count | 383.7 | 346.0 | -37.7 (-9.8%) [-46.90; -29.40] | 10/10 | tratamento melhor |
| S4 | sumo_teleports_total | 0.00 | 0.00 | +0.00 [0.00; 0.00] | 0/10 | sem diferença clara |

### 4.4 Complementar exploratório: B0 vs C1/C2 (fora da lista de comparações congeladas)

A pergunta de pesquisa compara a cooperação também com o tempo fixo; B0×C1 não está entre as comparações congeladas da rede.
Calculado com o mesmo estimador congelado e **marcado como exploratório** (`supplementary_B0_vs_cooperative_exploratory.csv`);
não é usado para a classificação principal.

| Cen. | Métrica | B0 média | C1 média | dif. (C1−B0) (rel.) IC95% | efeito |
|---|---|---|---|---|---|
| S1 | throughput | 1805.0 | 1804.2 | -0.8 (-0.0%) [-6.40; 4.60] | sem diferença clara |
| S1 | completion_ratio_offered | 0.967 | 0.965 | -0.003 (-0.3%) [-0.01; 0.00] | sem diferença clara |
| S1 | mean_waiting_time | 58.6 | 67.1 | +8.5 (+14.5%) [5.89; 11.12] | baseline melhor |
| S1 | mean_time_loss | 79.0 | 87.0 | +8.0 (+10.1%) [5.12; 10.75] | baseline melhor |
| S1 | mean_network_queue_vehicles | 29.5 | 33.9 | +4.4 (+14.9%) [3.10; 5.64] | baseline melhor |
| S2 | throughput | 1200.1 | 917.4 | -282.7 (-23.6%) [-292.80; -273.30] | baseline melhor |
| S2 | completion_ratio_offered | 0.970 | 0.716 | -0.254 (-26.2%) [-0.26; -0.25] | baseline melhor |
| S2 | mean_waiting_time | 56.8 | 140.8 | +84.0 (+147.9%) [81.37; 86.50] | baseline melhor |
| S2 | mean_time_loss | 78.0 | 167.1 | +89.1 (+114.2%) [86.14; 91.89] | baseline melhor |
| S2 | mean_network_queue_vehicles | 19.0 | 37.7 | +18.6 (+97.7%) [18.02; 19.20] | baseline melhor |
| S3 | throughput | 1956.4 | 1911.1 | -45.3 (-2.3%) [-56.30; -34.60] | baseline melhor |
| S3 | completion_ratio_offered | 0.935 | 0.910 | -0.024 (-2.6%) [-0.03; -0.02] | baseline melhor |
| S3 | mean_waiting_time | 72.3 | 95.3 | +23.0 (+31.9%) [19.80; 26.29] | baseline melhor |
| S3 | mean_time_loss | 96.4 | 120.4 | +24.0 (+24.9%) [20.31; 27.72] | baseline melhor |
| S3 | mean_network_queue_vehicles | 42.8 | 53.3 | +10.5 (+24.5%) [8.03; 12.98] | baseline melhor |
| S4 | throughput | 1476.3 | 1334.9 | -141.4 (-9.6%) [-151.60; -131.00] | baseline melhor |
| S4 | completion_ratio_offered | 0.352 | 0.307 | -0.045 (-12.9%) [-0.05; -0.04] | baseline melhor |
| S4 | mean_waiting_time | 649.8 | 735.4 | +85.6 (+13.2%) [74.95; 96.67] | baseline melhor |
| S4 | mean_time_loss | 802.1 | 890.7 | +88.7 (+11.1%) [74.38; 103.60] | baseline melhor |
| S4 | mean_network_queue_vehicles | 335.1 | 294.9 | -40.2 (-12.0%) [-44.98; -35.88] | tratamento melhor |

## 5. Leitura por cenário

### S1 — Balanceado
- Tempo fixo calibrado (B0): espera média 58.6 s, conclusão 0.967, sem veículos nunca inseridos.
- Adaptação local: B0→B2 reduz espera (-15.2%), perda de tempo (-12.7%) e fila média (-14.4%); vazão praticamente igual (+0.3%). Classificação: B2 melhor. B0→B1: sem diferença clara (apenas menos paradas).
- Cooperação: B2→C1 **piora** espera (+35.0%), fila média (+34.2%) e conclusão (-0.005), com 0/10 seeds favoráveis no atraso. Classificação: B2 melhor.
- Piloto V2 (N=5) mostrava a mesma direção (ver §10); sem agrupamento de amostras.

### S2 — Pico direcional
- B0 mantém conclusão 0.970 e vazão 1200; B2 cai para 0.765 e 973, com 212 veículos nunca inseridos por run (B0: 0). B0 é melhor que B2 e que B1 em atraso/fila; vazão de B1 não difere claramente de B0.
- B2→C1 é um **trade-off**: C1 reduz espera (-15.2%), perda de tempo (-15.3%), fila média (-18.3%) e tempo de viagem (-12.1%) em 10/10 seeds, mas reduz vazão (-5.7%), conclusão (-0.049) e partida (-0.061), e deixa +73.1 veículos a mais fora da rede.
- **Aviso de sobrevivência:** o menor tempo de viagem condicional de C1 não é evidência de melhora, porque menos viagens partem e concluem (a fila de entrada cresce). As métricas de atraso valem para os veículos que entraram.

### S3 — Mudança de demanda
- Metodologia S3 congelada (choque em 2100 s; `post_shock_queue_auc_vehicle_seconds`); nenhuma métrica de recuperação nova foi criada.
- B0 é melhor que B2 (conclusão, partida, atraso, fila) e que B1 (partida, atraso, fila), e na área de fila pós-choque (B0→B2 +14.5%; B0→B1 +15.6%); a vazão total não difere claramente entre B0 e B2.
- B2→C1: B2 melhor em todas as métricas-chave; área pós-choque +13.5% com C1 (0/10 seeds favoráveis). C2 piora fortemente (área +91.8% sobre C1).
- **Limitação preservada:** o gate composto de validade do S3 foi formalizado após a inspeção diagnóstica do Pilot V2; é um refinamento metodológico *post-hoc*. Todas as 50 runs de S3 têm `shock_start_seconds = 2100` e horizonte completo.

### S4 — Saturação localizada
- Regime de saturação severa: conclusão entre 0.28 e 0.35; ≈1899–2129 veículos por run nunca são inseridos, conforme o controlador. As métricas de tempo valem para uma minoria de viagens (regra condicional).
- B2→C1: C1 melhor em vazão (+8.8%), conclusão, espera (-19.5%), perda de tempo (-22.6%), fila média (-17.3%), tempo de viagem (-21.5%) e paradas (-36.6%), em 10/10 seeds; `departure_ratio` sem diferença clara; o atraso de partida **piora** (+16.8%). Classificação: C1 melhor. Efeito em vazão menor que no piloto (+12,0% → +8.8%).
- B0 (exploratório e congelado B0→B2/B1): B0 tem vazão e conclusão maiores que B1/B2; B0 vs C1 tem vazão maior (B0), espera menor (B0), mas fila média menor com C1 (-12.0%).
- C1→C2: trade-off (C2 menor espera -16.5% e fila -13.7%, vazão +2.2%; porém menor `departure_ratio` e maior atraso de partida +16.3%).
- Variabilidade entre seeds: coeficiente de variação da espera (10 seeds) B2 0.047, C1 0.034; as seeds 6–10 reduziram a largura do IC de vazão (ver §10). Efeitos por seed em `paired_differences` de `final_pairwise_summary.csv`.

**Teleports em S4 (`ALLOW_AND_MEASURE`, nenhum excluído).** 11 das 50 runs S4 tiveram teleports (31 no total):
B0 28 (em 10/10 runs, máx. 6), B2 3 (1/10, seed [5791]), B1/C1/C2 0. Em S1–S3: 0 teleports.
Os teleports estão em B0 (o controlador de maior vazão em S4) e quase ausentes nos demais; devem ser lidos junto da severidade da congestão, e não como falha (`s4_teleports_by_run.csv`).

## 6. Rota de referência oficial (`left1A1 → A1B1 → B1C1 → C1right1`, N = 10)

Coorte: veículos oferecidos cuja **sequência de arestas planejada** é exatamente a rota e cujo depart programado está na janela de medição
(o id de rota do SUMO nunca é usado). Estatística congelada de `reference_route.py`; evidência do N=5 antigo **não** reutilizada.

| Cen. | B0 viagem (s) | B0 concl. | B2 viagem (s) | B2 concl. | C1 viagem (s) | C1 concl. | B0→B2 (viagem; concl.) | IC95% viagem | B2→C1 (viagem; concl.) | IC95% viagem |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 129.2 | 0.977 | 116.7 | 0.971 | 139.8 | 0.964 | -12.5 s; compl. -0.7 p.p. | [-16.9; -8.8] | +23.2 s; compl. -0.6 p.p. | [+17.4; +28.9] |
| S2 | 129.3 | 0.967 | 322.4 | 0.673 | 283.0 | 0.649 | +193.2 s; compl. -29.4 p.p. | [+182.7; +203.5] | -39.4 s; compl. -2.4 p.p. | [-55.5; -22.5] |
| S3 | 226.7 | 0.858 | 278.7 | 0.817 | 232.5 | 0.826 | +52.0 s; compl. -4.1 p.p. | [+41.6; +63.1] | -46.2 s; compl. +0.9 p.p. | [-54.4; -33.9] |
| S4 | 370.2 | 0.899 | 1165.4 | 0.202 | 779.9 | 0.293 | +795.2 s; compl. -69.7 p.p. | [+694.9; +907.5] | -385.5 s; compl. +9.1 p.p. | [-489.1; -293.2] |

Contexto da coorte (médias por run):

| Cen. | Ctrl | coorte oferecida | partiu | chegou | nunca inserida | inacabada |
|---|---|---|---|---|---|---|
| S1 | B0 | 52.0 | 52.0 | 50.8 | 0.0 | 1.2 |
| S1 | B2 | 52.0 | 52.0 | 50.4 | 0.0 | 1.6 |
| S1 | C1 | 52.0 | 52.0 | 50.1 | 0.0 | 1.9 |
| S2 | B0 | 108.7 | 108.7 | 105.2 | 0.0 | 3.5 |
| S2 | B2 | 108.7 | 80.4 | 73.0 | 28.3 | 7.4 |
| S2 | C1 | 108.7 | 77.2 | 70.6 | 31.5 | 6.6 |
| S3 | B0 | 113.1 | 113.1 | 97.0 | 0.0 | 16.1 |
| S3 | B2 | 113.1 | 108.8 | 92.4 | 4.3 | 16.4 |
| S3 | C1 | 113.1 | 106.2 | 93.4 | 6.9 | 12.8 |
| S4 | B0 | 200.2 | 199.6 | 179.9 | 0.6 | 19.7 |
| S4 | B2 | 200.2 | 58.0 | 40.7 | 142.2 | 17.3 |
| S4 | C1 | 200.2 | 74.2 | 58.8 | 126.0 | 15.4 |

Métricas completas por cenário/controlador (média e mediana de viagem, espera, perda de tempo, paradas, conclusão):

| Cen. | Ctrl | viagem média (s) | viagem mediana (s) | espera (s) | perda de tempo (s) | paradas | concl. / oferecida | concl. / partida |
|---|---|---|---|---|---|---|---|---|
| S1 | B0 | 129.2 | 129.2 | 55.0 | 76.4 | 2.83 | 0.977 | 0.977 |
| S1 | B2 | 116.7 | 116.8 | 44.5 | 63.9 | 2.43 | 0.971 | 0.971 |
| S1 | C1 | 139.8 | 138.8 | 66.9 | 87.0 | 2.67 | 0.964 | 0.964 |
| S2 | B0 | 129.3 | 129.4 | 52.2 | 76.4 | 2.88 | 0.967 | 0.967 |
| S2 | B2 | 322.4 | 321.1 | 228.1 | 269.4 | 4.52 | 0.673 | 0.908 |
| S2 | C1 | 283.0 | 281.9 | 193.0 | 230.1 | 3.95 | 0.649 | 0.915 |
| S3 | B0 | 226.7 | 226.3 | 134.9 | 173.9 | 4.04 | 0.858 | 0.858 |
| S3 | B2 | 278.7 | 325.4 | 174.6 | 225.9 | 5.36 | 0.817 | 0.849 |
| S3 | C1 | 232.5 | 246.5 | 141.2 | 179.7 | 4.18 | 0.826 | 0.879 |
| S4 | B0 | 370.2 | 371.1 | 251.0 | 317.6 | 5.96 | 0.899 | 0.901 |
| S4 | B2 | 1165.4 | 1184.7 | 904.1 | 1113.0 | 24.08 | 0.202 | 0.697 |
| S4 | C1 | 779.9 | 765.9 | 597.1 | 727.7 | 14.03 | 0.293 | 0.791 |

- **B0→B2 (adaptação, rota):** S1 menor tempo de viagem (-12.5 s); em S2, S3 e S4 o tempo de viagem condicional **aumenta** e a conclusão cai (S4: −69,7 p.p.), ou seja, a coorte de B2 é bem menor/mais seletiva — ler com cautela.
- **B2→C1 (cooperação, rota):** S1 pior (+23 s); S2/S3/S4 menor tempo de viagem condicional, mas com conclusão sem diferença clara em S2/S3 e maior em S4 (+9,1 p.p.).
- Em S2 e S4 a coorte de B2/C1 é parcial (nunca inseridos: S2 ≈28–32 de 109; S4 ≈126–142 de 200) enquanto B0 insere quase toda a coorte; comparações de tempo são condicionais a viagens concluídas.

**Rede × rota.** Direções por cenário (rede = todas as viagens; rota = coorte exata):

| Cen. | Comparação | rede: Δ viagem (s) IC95% | rota: Δ viagem (s) IC95% | rede: Δ concl. (p.p.) | rota: Δ concl. (p.p.) |
|---|---|---|---|---|---|
| S1 | B0->B2 | -10.1 [-12.91,-6.85] | -12.5 [-16.94,-8.78] | +0.2 | -0.7 |
| S1 | B2->C1 | +18.0 [15.01,21.08] | +23.2 [17.40,28.94] | -0.5 | -0.6 |
| S2 | B0->B2 | +119.1 [114.52,123.95] | +193.2 [182.73,203.48] | -20.5 | -29.4 |
| S2 | B2->C1 | -30.3 [-36.44,-24.89] | -39.4 [-55.51,-22.50] | -4.9 | -2.4 |
| S3 | B0->B2 | +7.9 [5.26,10.72] | +52.0 [41.63,63.14] | -0.7 | -4.1 |
| S3 | B2->C1 | +15.9 [13.27,18.59] | -46.2 [-54.44,-33.93] | -1.7 | +0.9 |
| S4 | B0->B2 | +354.2 [334.29,372.31] | +795.2 [694.93,907.53] | -7.5 | -69.7 |
| S4 | B2->C1 | -261.1 [-281.85,-237.99] | -385.5 [-489.07,-293.21] | +3.0 | +9.1 |

Em S3, B2→C1 **piora** o tempo de viagem da rede (+15,9 s) mas **melhora** o da rota de referência (−46,2 s). Isto não é contradição automática:
rede e coorte são populações diferentes (a coorte é só a corrente oeste→leste A4–A5–A6; o choque de S3 entra pela borda oeste via A5, o que pode torná-la mais sensível, mas isso não foi testado aqui).
B0→B2 e B2→C1 são efeitos distintos (adaptação vs. cooperação) e não devem ser agregados em um único efeito.

## 7. S5 — Degradação de comunicação (tráfego-base S2_DIRECTIONAL_PEAK, atraso 0)

Estrutura: C1 e C2 com perda 0/20/50/100% (N=10 cada), B2 uma referência por seed (N=10, reutilizada nas comparações pareadas por seed; sem duplicação).

**Validade da comunicação (fatos de validação, não conclusões de tráfego):**
0%: zero descartes; 20%: taxa observada 19.9–20.2%;
50%: 49.7–50.2%;
100%: 1,872,000 enviadas, 1,872,000 descartadas, 0 entregues, 0 bytes entregues.

| Ctrl | Perda | msgs enviadas/run | entregues | descartadas | obsoletas | MB enviados | MB entregues | taxa de descarte obs. (min–max) | idade média/máx (passos) |
|---|---|---|---|---|---|---|---|---|---|
| C1 | 0% | 93600 | 93600 | 0 | 0 | 30.26 | 30.23 | 0.00–0.00% | 0.00/0 |
| C1 | 20% | 93600 | 74856 | 18744 | 0 | 30.35 | 24.25 | 19.90–20.17% | 0.00/0 |
| C1 | 50% | 93600 | 46806 | 46794 | 0 | 30.43 | 15.20 | 49.75–50.22% | 0.00/0 |
| C1 | 100% | 93600 | 0 | 93600 | 0 | 30.34 | 0.00 | 100.00–100.00% | 0.00/0 |
| C2 | 0% | 93600 | 93600 | 0 | 0 | 70.28 | 70.26 | 0.00–0.00% | 0.00/0 |
| C2 | 20% | 93600 | 74856 | 18744 | 0 | 70.42 | 56.30 | 19.90–20.17% | 0.00/0 |
| C2 | 50% | 93600 | 46806 | 46794 | 0 | 70.60 | 35.29 | 49.75–50.22% | 0.00/0 |
| C2 | 100% | 93600 | 0 | 93600 | 0 | 70.40 | 0.00 | 100.00–100.00% | 0.00/0 |

### 7.1 Desempenho (N=10, média ± desvio-padrão)

| Condição | throughput | completion_ratio_offered | departure_ratio | mean_waiting_time | mean_time_loss | mean_travel_time | mean_network_queue_vehicles | max_network_queue_vehicles | mean_stops | mean_depart_delay_seconds | never_inserted_vehicle_count | unfinished_in_network_count |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B2 (ref.) | 973.0 ± 23.2 | 0.765 ± 0.020 | 0.822 ± 0.022 | 166.0 ± 7.1 | 197.3 ± 7.9 | 249.9 ± 8.0 | 46.1 ± 1.5 | 74.3 ± 4.5 | 3.56 ± 0.09 | 271.9 ± 41.3 | 211.9 ± 26.6 | 67.6 ± 7.2 |
| C1 0% | 917.4 ± 17.1 | 0.716 ± 0.015 | 0.761 ± 0.013 | 140.8 ± 4.3 | 167.1 ± 4.9 | 219.6 ± 5.2 | 37.7 ± 1.0 | 58.3 ± 3.2 | 3.04 ± 0.08 | 294.3 ± 12.9 | 285.0 ± 15.8 | 52.9 ± 3.9 |
| C1 20% | 996.1 ± 6.3 | 0.785 ± 0.006 | 0.831 ± 0.004 | 136.1 ± 3.5 | 164.6 ± 4.2 | 217.2 ± 4.2 | 38.7 ± 1.1 | 60.5 ± 3.6 | 3.29 ± 0.08 | 227.2 ± 12.3 | 201.0 ± 5.1 | 55.0 ± 4.7 |
| C1 50% | 1012.2 ± 10.5 | 0.799 ± 0.008 | 0.849 ± 0.005 | 138.8 ± 4.1 | 168.1 ± 4.9 | 220.7 ± 5.1 | 40.2 ± 1.1 | 62.0 ± 2.9 | 3.39 ± 0.11 | 208.8 ± 6.9 | 179.3 ± 5.5 | 59.8 ± 5.8 |
| C1 100% | 973.0 ± 23.2 | 0.765 ± 0.020 | 0.822 ± 0.022 | 166.0 ± 7.1 | 197.3 ± 7.9 | 249.9 ± 8.0 | 46.1 ± 1.5 | 74.3 ± 4.5 | 3.56 ± 0.09 | 271.9 ± 41.3 | 211.9 ± 26.6 | 67.6 ± 7.2 |
| C2 0% | 841.4 ± 11.8 | 0.651 ± 0.009 | 0.696 ± 0.010 | 163.6 ± 3.1 | 190.4 ± 3.5 | 242.9 ± 3.8 | 40.2 ± 0.6 | 60.2 ± 1.9 | 3.10 ± 0.07 | 357.7 ± 22.5 | 362.3 ± 11.7 | 53.4 ± 3.3 |
| C2 20% | 974.9 ± 7.4 | 0.765 ± 0.008 | 0.813 ± 0.005 | 140.9 ± 4.3 | 169.8 ± 4.7 | 222.5 ± 5.1 | 39.3 ± 1.1 | 62.5 ± 2.5 | 3.35 ± 0.06 | 258.9 ± 10.3 | 222.5 ± 6.6 | 56.8 ± 5.1 |
| C2 50% | 1005.6 ± 7.7 | 0.794 ± 0.005 | 0.842 ± 0.005 | 140.2 ± 4.0 | 169.7 ± 4.7 | 222.3 ± 5.0 | 40.3 ± 1.1 | 63.9 ± 2.7 | 3.42 ± 0.09 | 219.0 ± 10.3 | 188.5 ± 5.7 | 57.3 ± 4.1 |
| C2 100% | 973.0 ± 23.2 | 0.765 ± 0.020 | 0.822 ± 0.022 | 166.0 ± 7.1 | 197.3 ± 7.9 | 249.9 ± 8.0 | 46.1 ± 1.5 | 74.3 ± 4.5 | 3.56 ± 0.09 | 271.9 ± 41.3 | 211.9 ± 26.6 | 67.6 ± 7.2 |

### 7.2 Degradação em relação a 0% (pareado por seed)

| Ctrl | Mudança | Métrica | média 0% | média nível | dif. abs. (rel.) IC95% | efeito (dir. = melhor em lado do nível) |
|---|---|---|---|---|---|---|
| C1 | 0%→20% | throughput | 917.4 | 996.1 | +78.7 (+8.6%) [69.00; 88.90] | tratamento melhor |
| C1 | 0%→20% | completion_ratio_offered | 0.716 | 0.785 | +0.069 (+9.6%) [0.06; 0.08] | tratamento melhor |
| C1 | 0%→20% | departure_ratio | 0.761 | 0.831 | +0.071 (+9.3%) [0.06; 0.08] | tratamento melhor |
| C1 | 0%→20% | mean_waiting_time | 140.8 | 136.1 | -4.7 (-3.3%) [-7.62; -1.84] | tratamento melhor |
| C1 | 0%→20% | mean_time_loss | 167.1 | 164.6 | -2.5 (-1.5%) [-5.78; 0.62] | sem diferença clara |
| C1 | 0%→20% | mean_travel_time | 219.6 | 217.2 | -2.4 (-1.1%) [-5.66; 0.68] | sem diferença clara |
| C1 | 0%→20% | mean_network_queue_vehicles | 37.7 | 38.7 | +1.0 (+2.7%) [0.15; 1.83] | baseline melhor |
| C1 | 0%→20% | max_network_queue_vehicles | 58.3 | 60.5 | +2.2 (+3.8%) [-1.40; 5.40] | sem diferença clara |
| C1 | 0%→20% | mean_stops | 3.04 | 3.29 | +0.25 (+8.1%) [0.20; 0.29] | baseline melhor |
| C1 | 0%→20% | never_inserted_vehicle_count | 285.0 | 201.0 | -84.0 (-29.5%) [-93.50; -75.20] | tratamento melhor |
| C1 | 0%→50% | throughput | 917.4 | 1012.2 | +94.8 (+10.3%) [85.70; 104.80] | tratamento melhor |
| C1 | 0%→50% | completion_ratio_offered | 0.716 | 0.799 | +0.083 (+11.6%) [0.08; 0.09] | tratamento melhor |
| C1 | 0%→50% | departure_ratio | 0.761 | 0.849 | +0.089 (+11.7%) [0.08; 0.10] | tratamento melhor |
| C1 | 0%→50% | mean_waiting_time | 140.8 | 138.8 | -2.0 (-1.4%) [-4.76; 0.93] | sem diferença clara |
| C1 | 0%→50% | mean_time_loss | 167.1 | 168.1 | +1.0 (+0.6%) [-2.13; 4.38] | sem diferença clara |
| C1 | 0%→50% | mean_travel_time | 219.6 | 220.7 | +1.1 (+0.5%) [-2.05; 4.38] | sem diferença clara |
| C1 | 0%→50% | mean_network_queue_vehicles | 37.7 | 40.2 | +2.5 (+6.7%) [1.86; 3.14] | baseline melhor |
| C1 | 0%→50% | max_network_queue_vehicles | 58.3 | 62.0 | +3.7 (+6.3%) [1.70; 5.50] | baseline melhor |
| C1 | 0%→50% | mean_stops | 3.04 | 3.39 | +0.35 (+11.4%) [0.29; 0.41] | baseline melhor |
| C1 | 0%→50% | never_inserted_vehicle_count | 285.0 | 179.3 | -105.7 (-37.1%) [-115.10; -96.90] | tratamento melhor |
| C1 | 0%→100% | throughput | 917.4 | 973.0 | +55.6 (+6.1%) [38.60; 75.50] | tratamento melhor |
| C1 | 0%→100% | completion_ratio_offered | 0.716 | 0.765 | +0.049 (+6.9%) [0.03; 0.07] | tratamento melhor |
| C1 | 0%→100% | departure_ratio | 0.761 | 0.822 | +0.061 (+8.1%) [0.04; 0.08] | tratamento melhor |
| C1 | 0%→100% | mean_waiting_time | 140.8 | 166.0 | +25.3 (+17.9%) [20.28; 30.83] | baseline melhor |
| C1 | 0%→100% | mean_time_loss | 167.1 | 197.3 | +30.3 (+18.1%) [24.89; 36.41] | baseline melhor |
| C1 | 0%→100% | mean_travel_time | 219.6 | 249.9 | +30.3 (+13.8%) [24.89; 36.44] | baseline melhor |
| C1 | 0%→100% | mean_network_queue_vehicles | 37.7 | 46.1 | +8.4 (+22.4%) [7.42; 9.62] | baseline melhor |
| C1 | 0%→100% | max_network_queue_vehicles | 58.3 | 74.3 | +16.0 (+27.4%) [13.10; 18.90] | baseline melhor |
| C1 | 0%→100% | mean_stops | 3.04 | 3.56 | +0.52 (+17.1%) [0.47; 0.58] | baseline melhor |
| C1 | 0%→100% | never_inserted_vehicle_count | 285.0 | 211.9 | -73.1 (-25.6%) [-93.30; -52.40] | tratamento melhor |
| C2 | 0%→20% | throughput | 841.4 | 974.9 | +133.5 (+15.9%) [125.40; 140.50] | tratamento melhor |
| C2 | 0%→20% | completion_ratio_offered | 0.651 | 0.765 | +0.115 (+17.6%) [0.11; 0.12] | tratamento melhor |
| C2 | 0%→20% | departure_ratio | 0.696 | 0.813 | +0.117 (+16.9%) [0.11; 0.12] | tratamento melhor |
| C2 | 0%→20% | mean_waiting_time | 163.6 | 140.9 | -22.7 (-13.9%) [-24.60; -20.75] | tratamento melhor |
| C2 | 0%→20% | mean_time_loss | 190.4 | 169.8 | -20.5 (-10.8%) [-22.44; -18.67] | tratamento melhor |
| C2 | 0%→20% | mean_travel_time | 242.9 | 222.5 | -20.4 (-8.4%) [-22.23; -18.55] | tratamento melhor |
| C2 | 0%→20% | mean_network_queue_vehicles | 40.2 | 39.3 | -0.9 (-2.3%) [-1.53; -0.30] | tratamento melhor |
| C2 | 0%→20% | max_network_queue_vehicles | 60.2 | 62.5 | +2.3 (+3.8%) [0.40; 4.10] | baseline melhor |
| C2 | 0%→20% | mean_stops | 3.10 | 3.35 | +0.24 (+7.9%) [0.22; 0.27] | baseline melhor |
| C2 | 0%→20% | never_inserted_vehicle_count | 362.3 | 222.5 | -139.8 (-38.6%) [-145.70; -133.50] | tratamento melhor |
| C2 | 0%→50% | throughput | 841.4 | 1005.6 | +164.2 (+19.5%) [155.90; 171.60] | tratamento melhor |
| C2 | 0%→50% | completion_ratio_offered | 0.651 | 0.794 | +0.143 (+21.9%) [0.14; 0.15] | tratamento melhor |
| C2 | 0%→50% | departure_ratio | 0.696 | 0.842 | +0.146 (+21.0%) [0.14; 0.15] | tratamento melhor |
| C2 | 0%→50% | mean_waiting_time | 163.6 | 140.2 | -23.4 (-14.3%) [-25.92; -21.10] | tratamento melhor |
| C2 | 0%→50% | mean_time_loss | 190.4 | 169.7 | -20.7 (-10.9%) [-23.41; -18.33] | tratamento melhor |
| C2 | 0%→50% | mean_travel_time | 242.9 | 222.3 | -20.6 (-8.5%) [-23.21; -18.24] | tratamento melhor |
| C2 | 0%→50% | mean_network_queue_vehicles | 40.2 | 40.3 | +0.1 (+0.3%) [-0.52; 0.73] | sem diferença clara |
| C2 | 0%→50% | max_network_queue_vehicles | 60.2 | 63.9 | +3.7 (+6.1%) [2.20; 5.30] | baseline melhor |
| C2 | 0%→50% | mean_stops | 3.10 | 3.42 | +0.32 (+10.3%) [0.28; 0.36] | baseline melhor |
| C2 | 0%→50% | never_inserted_vehicle_count | 362.3 | 188.5 | -173.8 (-48.0%) [-181.00; -165.80] | tratamento melhor |
| C2 | 0%→100% | throughput | 841.4 | 973.0 | +131.6 (+15.6%) [123.40; 140.30] | tratamento melhor |
| C2 | 0%→100% | completion_ratio_offered | 0.651 | 0.765 | +0.114 (+17.6%) [0.11; 0.12] | tratamento melhor |
| C2 | 0%→100% | departure_ratio | 0.696 | 0.822 | +0.126 (+18.2%) [0.12; 0.14] | tratamento melhor |
| C2 | 0%→100% | mean_waiting_time | 163.6 | 166.0 | +2.4 (+1.5%) [-1.49; 6.43] | sem diferença clara |
| C2 | 0%→100% | mean_time_loss | 190.4 | 197.3 | +6.9 (+3.6%) [2.78; 11.27] | baseline melhor |
| C2 | 0%→100% | mean_travel_time | 242.9 | 249.9 | +7.0 (+2.9%) [2.96; 11.32] | baseline melhor |
| C2 | 0%→100% | mean_network_queue_vehicles | 40.2 | 46.1 | +5.9 (+14.7%) [5.11; 6.77] | baseline melhor |
| C2 | 0%→100% | max_network_queue_vehicles | 60.2 | 74.3 | +14.1 (+23.4%) [11.30; 16.90] | baseline melhor |
| C2 | 0%→100% | mean_stops | 3.10 | 3.56 | +0.46 (+14.9%) [0.43; 0.50] | baseline melhor |
| C2 | 0%→100% | never_inserted_vehicle_count | 362.3 | 211.9 | -150.4 (-41.5%) [-161.70; -138.30] | tratamento melhor |

### 7.3 C1 e C2 vs B2 (referência única por seed)

| Ctrl | Perda | Métrica | B2 média | Ctrl média | dif. (Ctrl−B2) (rel.) IC95% | efeito |
|---|---|---|---|---|---|---|
| C1 | 0% | throughput | 973.0 | 917.4 | -55.6 (-5.7%) [-75.50; -38.60] | baseline melhor |
| C1 | 0% | completion_ratio_offered | 0.765 | 0.716 | -0.049 (-6.4%) [-0.07; -0.03] | baseline melhor |
| C1 | 0% | mean_waiting_time | 166.0 | 140.8 | -25.3 (-15.2%) [-30.83; -20.28] | tratamento melhor |
| C1 | 0% | mean_time_loss | 197.3 | 167.1 | -30.3 (-15.3%) [-36.41; -24.89] | tratamento melhor |
| C1 | 0% | mean_travel_time | 249.9 | 219.6 | -30.3 (-12.1%) [-36.44; -24.89] | tratamento melhor |
| C1 | 0% | mean_network_queue_vehicles | 46.1 | 37.7 | -8.4 (-18.3%) [-9.62; -7.42] | tratamento melhor |
| C1 | 0% | never_inserted_vehicle_count | 211.9 | 285.0 | +73.1 (+34.5%) [52.40; 93.30] | baseline melhor |
| C1 | 20% | throughput | 973.0 | 996.1 | +23.1 (+2.4%) [8.10; 36.80] | tratamento melhor |
| C1 | 20% | completion_ratio_offered | 0.765 | 0.785 | +0.020 (+2.6%) [0.01; 0.03] | tratamento melhor |
| C1 | 20% | mean_waiting_time | 166.0 | 136.1 | -29.9 (-18.0%) [-34.60; -25.68] | tratamento melhor |
| C1 | 20% | mean_time_loss | 197.3 | 164.6 | -32.8 (-16.6%) [-38.03; -28.01] | tratamento melhor |
| C1 | 20% | mean_travel_time | 249.9 | 217.2 | -32.6 (-13.1%) [-37.90; -27.90] | tratamento melhor |
| C1 | 20% | mean_network_queue_vehicles | 46.1 | 38.7 | -7.4 (-16.1%) [-8.59; -6.26] | tratamento melhor |
| C1 | 20% | never_inserted_vehicle_count | 211.9 | 201.0 | -10.9 (-5.1%) [-26.70; 5.50] | sem diferença clara |
| C1 | 50% | throughput | 973.0 | 1012.2 | +39.2 (+4.0%) [23.80; 52.90] | tratamento melhor |
| C1 | 50% | completion_ratio_offered | 0.765 | 0.799 | +0.034 (+4.4%) [0.02; 0.05] | tratamento melhor |
| C1 | 50% | mean_waiting_time | 166.0 | 138.8 | -27.2 (-16.4%) [-31.21; -23.22] | tratamento melhor |
| C1 | 50% | mean_time_loss | 197.3 | 168.1 | -29.2 (-14.8%) [-33.62; -24.88] | tratamento melhor |
| C1 | 50% | mean_travel_time | 249.9 | 220.7 | -29.2 (-11.7%) [-33.59; -24.83] | tratamento melhor |
| C1 | 50% | mean_network_queue_vehicles | 46.1 | 40.2 | -5.9 (-12.9%) [-6.97; -4.97] | tratamento melhor |
| C1 | 50% | never_inserted_vehicle_count | 211.9 | 179.3 | -32.6 (-15.4%) [-48.50; -16.30] | tratamento melhor |
| C1 | 100% | throughput | 973.0 | 973.0 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C1 | 100% | completion_ratio_offered | 0.765 | 0.765 | +0.000 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C1 | 100% | mean_waiting_time | 166.0 | 166.0 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C1 | 100% | mean_time_loss | 197.3 | 197.3 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C1 | 100% | mean_travel_time | 249.9 | 249.9 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C1 | 100% | mean_network_queue_vehicles | 46.1 | 46.1 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C1 | 100% | never_inserted_vehicle_count | 211.9 | 211.9 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C2 | 0% | throughput | 973.0 | 841.4 | -131.6 (-13.5%) [-140.30; -123.40] | baseline melhor |
| C2 | 0% | completion_ratio_offered | 0.765 | 0.651 | -0.114 (-15.0%) [-0.12; -0.11] | baseline melhor |
| C2 | 0% | mean_waiting_time | 166.0 | 163.6 | -2.4 (-1.5%) [-6.43; 1.49] | sem diferença clara |
| C2 | 0% | mean_time_loss | 197.3 | 190.4 | -6.9 (-3.5%) [-11.27; -2.78] | tratamento melhor |
| C2 | 0% | mean_travel_time | 249.9 | 242.9 | -7.0 (-2.8%) [-11.32; -2.96] | tratamento melhor |
| C2 | 0% | mean_network_queue_vehicles | 46.1 | 40.2 | -5.9 (-12.8%) [-6.77; -5.11] | tratamento melhor |
| C2 | 0% | never_inserted_vehicle_count | 211.9 | 362.3 | +150.4 (+71.0%) [138.30; 161.70] | baseline melhor |
| C2 | 20% | throughput | 973.0 | 974.9 | +1.9 (+0.2%) [-12.60; 14.20] | sem diferença clara |
| C2 | 20% | completion_ratio_offered | 0.765 | 0.765 | +0.000 (+0.0%) [-0.01; 0.01] | sem diferença clara |
| C2 | 20% | mean_waiting_time | 166.0 | 140.9 | -25.1 (-15.1%) [-28.61; -22.30] | tratamento melhor |
| C2 | 20% | mean_time_loss | 197.3 | 169.8 | -27.5 (-13.9%) [-31.41; -24.35] | tratamento melhor |
| C2 | 20% | mean_travel_time | 249.9 | 222.5 | -27.4 (-11.0%) [-31.35; -24.28] | tratamento melhor |
| C2 | 20% | mean_network_queue_vehicles | 46.1 | 39.3 | -6.8 (-14.8%) [-7.71; -6.01] | tratamento melhor |
| C2 | 20% | never_inserted_vehicle_count | 211.9 | 222.5 | +10.6 (+5.0%) [-4.70; 26.60] | sem diferença clara |
| C2 | 50% | throughput | 973.0 | 1005.6 | +32.6 (+3.4%) [17.30; 46.40] | tratamento melhor |
| C2 | 50% | completion_ratio_offered | 0.765 | 0.794 | +0.028 (+3.7%) [0.02; 0.04] | tratamento melhor |
| C2 | 50% | mean_waiting_time | 166.0 | 140.2 | -25.8 (-15.5%) [-28.56; -23.19] | tratamento melhor |
| C2 | 50% | mean_time_loss | 197.3 | 169.7 | -27.7 (-14.0%) [-30.62; -24.85] | tratamento melhor |
| C2 | 50% | mean_travel_time | 249.9 | 222.3 | -27.6 (-11.0%) [-30.54; -24.81] | tratamento melhor |
| C2 | 50% | mean_network_queue_vehicles | 46.1 | 40.3 | -5.8 (-12.6%) [-6.42; -5.18] | tratamento melhor |
| C2 | 50% | never_inserted_vehicle_count | 211.9 | 188.5 | -23.4 (-11.0%) [-39.60; -6.50] | tratamento melhor |
| C2 | 100% | throughput | 973.0 | 973.0 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C2 | 100% | completion_ratio_offered | 0.765 | 0.765 | +0.000 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C2 | 100% | mean_waiting_time | 166.0 | 166.0 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C2 | 100% | mean_time_loss | 197.3 | 197.3 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C2 | 100% | mean_travel_time | 249.9 | 249.9 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C2 | 100% | mean_network_queue_vehicles | 46.1 | 46.1 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| C2 | 100% | never_inserted_vehicle_count | 211.9 | 211.9 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |

### 7.4 C1 vs C2 por nível de perda

| Perda | Métrica | C1 média | C2 média | dif. (C2−C1) (rel.) IC95% | efeito |
|---|---|---|---|---|---|
| 0% | throughput | 917.4 | 841.4 | -76.0 (-8.3%) [-86.90; -63.80] | baseline melhor |
| 0% | completion_ratio_offered | 0.716 | 0.651 | -0.065 (-9.1%) [-0.07; -0.06] | baseline melhor |
| 0% | mean_waiting_time | 140.8 | 163.6 | +22.8 (+16.2%) [20.59; 25.17] | baseline melhor |
| 0% | mean_time_loss | 167.1 | 190.4 | +23.3 (+14.0%) [20.98; 25.85] | baseline melhor |
| 0% | mean_travel_time | 219.6 | 242.9 | +23.2 (+10.6%) [20.88; 25.81] | baseline melhor |
| 0% | mean_network_queue_vehicles | 37.7 | 40.2 | +2.5 (+6.7%) [2.14; 2.98] | baseline melhor |
| 0% | never_inserted_vehicle_count | 285.0 | 362.3 | +77.3 (+27.1%) [66.50; 86.90] | baseline melhor |
| 20% | throughput | 996.1 | 974.9 | -21.2 (-2.1%) [-24.70; -17.70] | baseline melhor |
| 20% | completion_ratio_offered | 0.785 | 0.765 | -0.020 (-2.5%) [-0.02; -0.02] | baseline melhor |
| 20% | mean_waiting_time | 136.1 | 140.9 | +4.8 (+3.6%) [2.14; 7.83] | baseline melhor |
| 20% | mean_time_loss | 164.6 | 169.8 | +5.3 (+3.2%) [2.29; 8.58] | baseline melhor |
| 20% | mean_travel_time | 217.2 | 222.5 | +5.2 (+2.4%) [2.27; 8.53] | baseline melhor |
| 20% | mean_network_queue_vehicles | 38.7 | 39.3 | +0.6 (+1.5%) [-0.21; 1.47] | sem diferença clara |
| 20% | never_inserted_vehicle_count | 201.0 | 222.5 | +21.5 (+10.7%) [17.40; 25.80] | baseline melhor |
| 50% | throughput | 1012.2 | 1005.6 | -6.6 (-0.7%) [-11.40; -1.70] | baseline melhor |
| 50% | completion_ratio_offered | 0.799 | 0.794 | -0.006 (-0.7%) [-0.01; -0.00] | baseline melhor |
| 50% | mean_waiting_time | 138.8 | 140.2 | +1.4 (+1.0%) [-0.89; 3.81] | sem diferença clara |
| 50% | mean_time_loss | 168.1 | 169.7 | +1.6 (+0.9%) [-1.00; 4.28] | sem diferença clara |
| 50% | mean_travel_time | 220.7 | 222.3 | +1.6 (+0.7%) [-1.00; 4.31] | sem diferença clara |
| 50% | mean_network_queue_vehicles | 40.2 | 40.3 | +0.1 (+0.4%) [-0.51; 0.83] | sem diferença clara |
| 50% | never_inserted_vehicle_count | 179.3 | 188.5 | +9.2 (+5.1%) [4.40; 13.90] | baseline melhor |
| 100% | throughput | 973.0 | 973.0 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| 100% | completion_ratio_offered | 0.765 | 0.765 | +0.000 (+0.0%) [0.00; 0.00] | sem diferença clara |
| 100% | mean_waiting_time | 166.0 | 166.0 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| 100% | mean_time_loss | 197.3 | 197.3 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| 100% | mean_travel_time | 249.9 | 249.9 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| 100% | mean_network_queue_vehicles | 46.1 | 46.1 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |
| 100% | never_inserted_vehicle_count | 211.9 | 211.9 | +0.0 (+0.0%) [0.00; 0.00] | sem diferença clara |

### 7.5 Leitura de robustez (apenas do que os dados mostram)
- **Não houve degradação monotônica.** Em C1, a perda de 20% e 50% **aumentou** vazão (+8.6% e +10.3%) e conclusão em relação a 0%, com atraso de partida/nunca inseridos menores, enquanto a fila média e as paradas pioraram levemente; em C2, a perda de 20% e 50% melhorou fortemente vazão (+15.9% e +19.5%), espera e conclusão, em 10/10 seeds. O C2 com informação completa (0%) é o pior ponto de C2.
- **Perda moderada (20–50%)**: C1 e C2 ficam próximos ou melhores que B2 em serviço (vazão/conclusão) e melhores em atraso/fila (S2). Mecanismos explicativos **não foram testados** e não são afirmados aqui.
- **Perda total (100%)**: as 20 runs cooperativas terminaram, com métricas finalizadas e 0 mensagens entregues. Em todas as 20, as métricas de tráfego de C1 e C2 foram **idênticas** às do B2 da mesma seed (diferenças exatamente 0), consistente com o comportamento de recuo local do controlador cooperativo (`local_pressure_controller_id = B2_LOCAL_PRESSURE` no manifesto). Isto é uma observação empírica; não há prova formal aqui.
- Não é declarado limiar de tolerância a perda: há apenas quatro níveis, e o efeito não é monotônico.
- `FALLBACK_OPERATIONAL = YES` refere-se a operação sem mensagens entregues (simulação conclui, métricas finalizadas). **Não** é verificação formal de segurança de sinal: ela é sustentada separadamente pelo `PhaseSafetyManager` inalterado e pelos testes de software.

## 8. Custo de comunicação: C1 vs C2

| Experimento | Cen. | Perda | C2/C1 mensagens | C1 MB/run | C2 MB/run | C2/C1 bytes |
|---|---|---|---|---|---|---|
| FINAL_MAIN | S1 | 0% | 1.000 | 31.99 | 75.43 | 2.36× |
| FINAL_MAIN | S2 | 0% | 1.000 | 30.26 | 70.28 | 2.32× |
| FINAL_MAIN | S3 | 0% | 1.000 | 32.31 | 75.51 | 2.34× |
| FINAL_MAIN | S4 | 0% | 1.000 | 33.40 | 75.73 | 2.27× |
| FINAL_S5 | S2 | 0% | 1.000 | 30.26 | 70.28 | 2.32× |
| FINAL_S5 | S2 | 20% | 1.000 | 30.35 | 70.42 | 2.32× |
| FINAL_S5 | S2 | 50% | 1.000 | 30.43 | 70.60 | 2.32× |
| FINAL_S5 | S2 | 100% | 1.000 | 30.34 | 70.40 | 2.32× |

- C1 e C2 enviam o **mesmo número** de mensagens por run (93 600), mas a mensagem de C2 tem ≈751 bytes contra ≈324 bytes de C1, ou seja ≈2,3× mais bytes enviados.
- Desempenho: C2 é pior que C1 em S1, S2 e S3 (conclusão, atraso e filas; ex.: S1 espera +187.4%, S3 espera +121.2%); em S4 há trade-off (menor espera/fila, maior atraso de partida e menor `departure_ratio`). No S5, C1 é melhor ou igual a C2 em todos os níveis: a 0% e 20% em serviço e atraso; a 50% só em serviço (atraso sem diferença clara); a 100% idênticos (ver §7.4).
- **Resposta:** a comunicação expandida **não** trouxe benefício de tráfego suficiente para justificar ≈2,3× mais bytes nas condições simuladas; o benefício restringe-se a atraso/fila em S4, com custo em partida. Resposta: *sem benefício claro / dependente do cenário*.

## 9. Resumo por pergunta

| Pergunta | Resposta apoiada pelos dados |
|---|---|
| Primária B2 vs C1 | Dependente do cenário: C1 melhor só em S4; B2 melhor em S1 e S3; trade-off em S2. |
| B0 vs B2 | B2 melhor em S1; B0 melhor em S2, S3 e S4 (mais forte em S2/S4). |
| B0 vs B1 | Sem diferença clara em S1; B0 melhor em S2, S3 e S4. |
| C1 vs C2 | C1 melhor em S1–S3; trade-off em S4; C2 ≈2,3× bytes. |

## 10. Piloto V2 (N=5) vs Final (N=10) — comparação metodológica, sem agrupar

Como as 5 primeiras seeds do Final são as do Piloto, **não** há N=15. Reexecutar essas 5 seeds no Final reproduziu **exatamente**
as diferenças do Piloto em 57/57 (cenário × métrica) comparações, e os valores por run coincidem (diferença máx. 0,0 excluindo métricas de tempo de relógio). Logo, o que o Final acrescenta são as seeds 6–10 (6841, 8089, 10007, 12011, 16001).

| Cen. | Métrica | Piloto N=5: Δ C1−B2 [IC95%] | Final N=10: Δ C1−B2 [IC95%] | direção persistiu | largura IC final/piloto | |efeito| final/piloto | veredicto piloto | veredicto final |
|---|---|---|---|---|---|---|---|---|
| S1 | throughput | -4.2 [-10.0; 2.0] | -6.1 [-11.2; -0.9] | sim | 0.86 | 1.45 | sem diferença clara | baseline melhor |
| S1 | completion_ratio_offered | -0.006 [-0.007; -0.004] | -0.005 [-0.007; -0.002] | sim | 1.71 | 0.83 | baseline melhor | baseline melhor |
| S1 | mean_waiting_time | +20.9 [17.8; 24.0] | +17.4 [14.5; 20.4] | sim | 0.94 | 0.83 | baseline melhor | baseline melhor |
| S1 | mean_time_loss | +21.6 [18.5; 24.8] | +18.0 [15.0; 21.1] | sim | 0.97 | 0.83 | baseline melhor | baseline melhor |
| S1 | mean_network_queue_vehicles | +10.5 [9.0; 11.9] | +8.6 [7.2; 10.2] | sim | 1.01 | 0.82 | baseline melhor | baseline melhor |
| S1 | max_network_queue_vehicles | +11.0 [10.0; 12.2] | +7.9 [5.2; 10.3] | sim | 2.32 | 0.72 | baseline melhor | baseline melhor |
| S2 | throughput | -59.8 [-92.6; -35.4] | -55.6 [-75.5; -38.6] | sim | 0.65 | 0.93 | baseline melhor | baseline melhor |
| S2 | completion_ratio_offered | -0.052 [-0.080; -0.030] | -0.049 [-0.066; -0.033] | sim | 0.66 | 0.94 | baseline melhor | baseline melhor |
| S2 | mean_waiting_time | -21.0 [-26.2; -15.9] | -25.3 [-30.8; -20.3] | sim | 1.02 | 1.20 | tratamento melhor | tratamento melhor |
| S2 | mean_time_loss | -25.6 [-31.2; -20.2] | -30.3 [-36.4; -24.9] | sim | 1.05 | 1.18 | tratamento melhor | tratamento melhor |
| S2 | mean_network_queue_vehicles | -7.5 [-8.4; -6.5] | -8.4 [-9.6; -7.4] | sim | 1.11 | 1.13 | tratamento melhor | tratamento melhor |
| S2 | max_network_queue_vehicles | -16.8 [-20.6; -13.4] | -16.0 [-18.9; -13.1] | sim | 0.81 | 0.95 | tratamento melhor | tratamento melhor |
| S3 | throughput | -31.8 [-40.6; -22.6] | -32.9 [-38.7; -27.1] | sim | 0.64 | 1.03 | baseline melhor | baseline melhor |
| S3 | completion_ratio_offered | -0.019 [-0.022; -0.016] | -0.017 [-0.020; -0.015] | sim | 0.75 | 0.93 | baseline melhor | baseline melhor |
| S3 | mean_waiting_time | +19.0 [15.0; 22.3] | +16.8 [14.4; 19.3] | sim | 0.67 | 0.89 | baseline melhor | baseline melhor |
| S3 | mean_time_loss | +18.1 [13.5; 21.9] | +16.0 [13.4; 18.7] | sim | 0.63 | 0.88 | baseline melhor | baseline melhor |
| S3 | mean_network_queue_vehicles | +9.6 [7.4; 11.5] | +8.3 [7.0; 9.7] | sim | 0.68 | 0.87 | baseline melhor | baseline melhor |
| S3 | max_network_queue_vehicles | +9.8 [3.2; 16.4] | +11.5 [7.7; 15.0] | sim | 0.55 | 1.17 | baseline melhor | baseline melhor |
| S4 | throughput | +142.6 [68.6; 257.0] | +107.6 [69.1; 169.8] | sim | 0.53 | 0.75 | tratamento melhor | tratamento melhor |
| S4 | completion_ratio_offered | +0.041 [0.019; 0.073] | +0.030 [0.018; 0.048] | sim | 0.54 | 0.74 | tratamento melhor | tratamento melhor |
| S4 | mean_waiting_time | -189.7 [-206.0; -168.6] | -178.4 [-196.5; -158.7] | sim | 1.01 | 0.94 | tratamento melhor | tratamento melhor |
| S4 | mean_time_loss | -271.9 [-288.5; -247.4] | -260.8 [-281.4; -237.8] | sim | 1.06 | 0.96 | tratamento melhor | tratamento melhor |
| S4 | mean_network_queue_vehicles | -63.6 [-70.3; -57.4] | -61.5 [-65.6; -57.9] | sim | 0.60 | 0.97 | tratamento melhor | tratamento melhor |
| S4 | max_network_queue_vehicles | -103.0 [-107.2; -98.0] | -94.5 [-100.9; -87.9] | sim | 1.41 | 0.92 | tratamento melhor | tratamento melhor |

- Direção da diferença C1−B2: persistiu em 50/51 comparações com diferença não nula; veredito (IC) mudou em 2: S1 throughput, S2 mean_depart_delay_seconds.
- Largura mediana do IC (final/piloto, métricas de serviço/atraso): S1 0.97, S2 1.02, S3 0.64, S4 1.01; só vazão: S1 0.86, S2 0.65, S3 0.64, S4 0.53.
- Razão mediana |efeito| final/piloto: S1 0.83, S2 1.13, S3 0.89, S4 0.94 (valores < 1: efeito estimado menor com N=10; > 1: maior).
- **Valor de N=10 (retrospectivo, não é nova regra de parada):** nenhuma direção mudou; os ICs de vazão estreitaram em S2, S3 e S4 (razões acima) e os de atraso/fila mudaram pouco na maioria dos cenários; o efeito de vazão em S4 foi estimado menor com N=10 (piloto +12,0% → final +8.8%), evitando superestimação. N=10 foi útil por precisão e por checagem de superestimação, não por inversão de conclusão.

## 11. Resposta à pergunta de pesquisa

**Expectativa inicial.** O protocolo não definiu a resposta esperada; a hipótese de trabalho implícita no título (controle distribuído e cooperativo) era que a troca local de informação melhora o desempenho em relação ao adaptativo local sem cooperação e ao tempo fixo. O Pilot V2 já indicava resultado misto (MIXED), com benefício aparente da cooperação restrito ao regime saturado (S4). A hipótese original não é reescrita.

**Observação final.**
- Cooperação vs adaptativo local (C1 vs B2): *depende do cenário* — benefício em S4, piora em S1 e S3, trade-off em S2.
- Cooperação vs tempo fixo (B0 × C1, exploratório): B0 teve menor espera/fila em S1, e maior vazão/conclusão e menor espera em S2–S4; em S4 o C1 teve fila média menor. Não há evidência de superioridade geral da cooperação sobre B0.
- Adaptação local vs tempo fixo (B0 vs B2/B1): B2 melhor só em S1; em S2–S4 B0 melhor.
- Comunicação mais rica (C2) não melhora o desempenho de modo geral e custa ≈2,3× em bytes.

Os resultados indicam, portanto, que o efeito da cooperação **variou por cenário** e **não** sustentam superioridade geral da cooperação.
Expectativa "cooperação ajuda sob congestão": confirmada apenas em S4 (e com piora no atraso de partida); expectativa "adaptação local supera o tempo fixo em todos os cenários": **não** observada (apenas S1).

## 12. Resultados inesperados ou contraintuitivos
1. O tempo fixo calibrado (B0) superou B1 e B2 em S2, S3 e S4 (e B2 deixou ≈212 veículos/run fora da rede em S2).
2. C2 (comunicação expandida) foi muito pior que C1 em S1–S3 (espera +187%/+121% sobre C1 em S1/S3).
3. S5 **não monotônico**: perdas de 20–50% melhoraram C1/C2 em vazão/conclusão em relação a 0%.
4. Com 100% de perda, C1 e C2 reproduziram exatamente o B2 em todas as métricas de tráfego.
5. Em S3, B2→C1 piora a rede e melhora a rota de referência.
6. Teleports de S4 concentrados em B0 (28 de 31), o controlador de maior vazão em S4.

## 13. Limitações reforçadas pelos resultados
- Uma única rede 3×3 simulada em SUMO; sem validação em campo; sem generalização para outras topologias.
- N=10 seeds por condição; IC por bootstrap de 10 diferenças pareadas pode ser anti-conservador; sem correção para múltiplas métricas/comparações; sem valores-p.
- Resultados valem para os parâmetros congelados dos controladores; B0 passou por calibração dedicada, conforme o congelamento.
- S3: validade pelo gate composto *post-hoc*.
- S4: regime de saturação severa, com ≈65–72% das viagens oferecidas não concluídas e teleports mensurados (não excluídos); métricas de tempo são condicionais.
- S2/S4: métricas de tempo condicionais a coortes parciais; atraso de partida e veículos nunca inseridos devem acompanhar qualquer leitura.
- S5 usa só S2, atraso 0 e 4 níveis de perda; sem limiar de tolerância; mecanismos do efeito não testados.
- A comparação B0×C1 de rede é exploratória (fora do plano congelado).
- 12 runs de S5 precisaram de retry por limite de caminho do Windows (infraestrutura); resultados idênticos aos esperados por execução determinística, mas as tentativas falhas existem nos logs.

## 14. Alegações NÃO sustentadas
- Superioridade geral/universal da cooperação, de qualquer controlador ou "da IA".
- Causa dos efeitos (por que perdas moderadas melhoram C1/C2 em S2; por que B2 é fraco em S2).
- Limiar de tolerância a perda de pacotes.
- Verificação formal de segurança de sinal a partir dos artefatos.
- Generalização para tráfego real, outras redes, outras demandas ou outros atrasos de comunicação.
- Ganho de C2 que justifique o custo de comunicação.

## 15. Rastreabilidade
- `final_metrics.parquet`: cada observação com `experiment`, `scenario`, `controller`, `seed`, `packet_loss`, `run_id`, `run_path`, `config_run_id`, `attempts`, hashes de cenário/rota/rede, `scientific_source_git_sha` e `freeze_manifest_sha256`.
- Pares por seed: `paired_seeds` / `paired_differences` em `final_pairwise_summary.csv`, `s5_pairwise.csv`, `reference_route_pairwise.csv`.
- Validação: `analysis-validation.json` (população exata 200+90, sem duplicatas, sem piloto/calibração/replay, `LONG_PATH_S5_IDENTITIES_INCLUDED = 12/12`).
