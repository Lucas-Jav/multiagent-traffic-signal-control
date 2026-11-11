> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/pilot-assessment.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado abaixo (texto traduzido para português, sem alteração de números ou conclusões).

> **STATUS SUBSTITUÍDO (auditoria final, Prompt 52).** Esta é a avaliação original do Prompt 46.8, mantida sem alterações abaixo. Seus gates `S3_ADAPTATION_SCENARIO_VALID = NO`, `SCIENTIFIC_PILOT_VALID = NO`, `READY_FOR_SEED_DECISION = NO` e a comparação B2-vs-C1 retida refletem apenas a antiga regra de 360 s. Após o gate composto aprovado (Prompts 47/48), o S3 é válido (5/5 seeds), o Pilot V2 foi liberado para B2 vs C1 (Prompt 49) e a comparação foi concluída (Prompt 50, resultado MISTO). Ver `pilot-v2-release-decision.md`, `b2-vs-c1-final-comparison.md` e `final-scientific-conclusion.md`.

# Avaliação do Pilot V2

`campaign_role: PILOT` - Pilot V1 e V2 nunca são combinados estatisticamente. Não são resultados finais. Nenhum ranking ou ajuste de controladores.

Fontes autoritativas: `manifest.json`/`run_status.jsonl` do executor, `run_metrics.json` por execução + telemetria canônica, `combined_metrics.parquet` (pipeline `experiment aggregate` do projeto). Os critérios de validade de cenário são avaliados nas execuções de referência do `B0_FIXED` (5 seeds) e listados para todos os controladores a título informativo. O script de análise é `artifacts/experiments/pilot_v2/analysis/pilot_v2_analysis.py` (reutiliza `scripts/calibrate_scenarios.py::analyze_run`, sem alteração de código-fonte).

## 1. Execução

- PLANNED_RUNS 100; COMPLETED_RUNS 100; FAILED_RUNS 0
- transições de status por execução (run_status.jsonl): {"RUNNING->COMPLETED": 100}
- metrics_finalized=true em todas as execuções: True; métricas obrigatórias ausentes: 0 []
- Nomes de métricas solicitados vs nomes do projeto: `mean_waiting_time_seconds`->`mean_waiting_time`, `mean_time_loss_seconds`->`mean_time_loss`, `mean_travel_time_seconds`->`mean_travel_time` (as métricas estavam congeladas; verificadas por este mapeamento).
- teleportes por congestionamento (jam) por execução (SUMO): total 17; execuções com teleportes 6; por cenário {'S1_BALANCED': 0, 'S2_DIRECTIONAL_PEAK': 0, 'S3_DEMAND_SHIFT': 0, 'S4_LOCAL_SATURATION': 17}

## 2. Validade de cenário (execuções de referência do B0)

### S1_BALANCED

| seed | razão de partida | concl. partidos | variação proj. últimos 20% / média | participação mín. por junção | conversões s/l/r | verificações que falharam |
| --- | --- | --- | --- | --- | --- | --- |
| 42 | 1.000 | 0.957 | -6.4 / 45.5 | 0.107 | 0.71/0.15/0.15 | - |
| 2027 | 1.000 | 0.960 | -2.2 / 45.7 | 0.107 | 0.70/0.15/0.16 | - |
| 3253 | 1.000 | 0.958 | -6.8 / 50.1 | 0.105 | 0.70/0.15/0.15 | - |
| 4517 | 1.000 | 0.952 | -5.4 / 47.7 | 0.106 | 0.71/0.14/0.15 | - |
| 5791 | 1.000 | 0.955 | -0.9 / 50.5 | 0.108 | 0.70/0.15/0.15 | - |

S1_STABLE_REGIME_VALID = YES

### S2_DIRECTIONAL_PEAK

| seed | participação dominante ofertada | DBI | razão de partida | partida dominante | partida residual | participação esq+dir | verificações que falharam |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 0.805 | 0.805 | 1.000 | 1.000 | 1.000 | 0.310 | - |
| 2027 | 0.804 | 0.804 | 1.000 | 1.000 | 1.000 | 0.297 | - |
| 3253 | 0.804 | 0.804 | 1.000 | 1.000 | 1.000 | 0.300 | - |
| 4517 | 0.806 | 0.806 | 1.000 | 1.000 | 1.000 | 0.305 | - |
| 5791 | 0.804 | 0.804 | 1.000 | 1.000 | 1.000 | 0.289 | - |

S2_DIRECTIONAL_SCENARIO_VALID = YES

### S3_DEMAND_SHIFT

| seed | fila pré-choque / S1 mesma janela | média pré-choque | média pós-choque (600 s) | razão | razão A5 | latência (s) | atraso máx de inserção (s) | razão de partida | verificações que falharam |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 1.00 | 48.1 | 65.2 | 1.36 | 2.60 | 130 | 118 | 0.997 | - |
| 2027 | 1.00 | 46.4 | 66.7 | 1.44 | 3.56 | 216 | 367 | 0.975 | - |
| 3253 | 1.00 | 46.1 | 63.1 | 1.37 | 1.79 | 131 | 94 | 0.998 | - |
| 4517 | 1.00 | 47.9 | 69.1 | 1.44 | 3.04 | 145 | 366 | 0.967 | pre_shock_stable |
| 5791 | 1.00 | 47.7 | 63.4 | 1.33 | 2.35 | 158 | 115 | 0.993 | - |

S3_ADAPTATION_SCENARIO_VALID = NO

### S4_LOCAL_SATURATION

| seed | fila média A5 | A5 / demais | vizinhas / cantos | chegadas mín. em 300 s | chegadas últimos 1800 s / ofertados | razão de partida | teleportes | verificações que falharam |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 75.4 | 2.52 | 2.06 | 121 | 767 / 1788 | 0.491 | 2 | - |
| 2027 | 74.6 | 2.44 | 2.02 | 117 | 770 / 1784 | 0.485 | 2 | - |
| 3253 | 74.9 | 2.44 | 2.04 | 117 | 760 / 1787 | 0.485 | 4 | - |
| 4517 | 75.0 | 2.50 | 2.04 | 112 | 791 / 1787 | 0.487 | 2 | - |
| 5791 | 73.9 | 2.41 | 1.95 | 116 | 758 / 1790 | 0.474 | 4 | - |

S4_SATURATION_SCENARIO_VALID = YES

### Informação: intervalos de 300 s sem chegadas e critérios de calibração por controlador (todas as 100 execuções)

| cenário | controlador | execuções com intervalo de 300 s sem chegadas | execuções que passam em todos os critérios de calibração |
| --- | --- | --- | --- |
| S1_BALANCED | B0_FIXED | 0/5 | 5/5 |
| S1_BALANCED | B1_LOCAL_ADAPTIVE | 0/5 | 5/5 |
| S1_BALANCED | B2_LOCAL_PRESSURE | 0/5 | 4/5 |
| S1_BALANCED | C1_COOPERATIVE_COMPACT | 0/5 | 5/5 |
| S1_BALANCED | C2_COOPERATIVE_EXPANDED | 0/5 | 0/5 |
| S2_DIRECTIONAL_PEAK | B0_FIXED | 0/5 | 5/5 |
| S2_DIRECTIONAL_PEAK | B1_LOCAL_ADAPTIVE | 0/5 | 5/5 |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE | 0/5 | 0/5 |
| S2_DIRECTIONAL_PEAK | C1_COOPERATIVE_COMPACT | 0/5 | 0/5 |
| S2_DIRECTIONAL_PEAK | C2_COOPERATIVE_EXPANDED | 0/5 | 0/5 |
| S3_DEMAND_SHIFT | B0_FIXED | 0/5 | 4/5 |
| S3_DEMAND_SHIFT | B1_LOCAL_ADAPTIVE | 0/5 | 3/5 |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE | 0/5 | 3/5 |
| S3_DEMAND_SHIFT | C1_COOPERATIVE_COMPACT | 0/5 | 4/5 |
| S3_DEMAND_SHIFT | C2_COOPERATIVE_EXPANDED | 0/5 | 0/5 |
| S4_LOCAL_SATURATION | B0_FIXED | 0/5 | 5/5 |
| S4_LOCAL_SATURATION | B1_LOCAL_ADAPTIVE | 0/5 | 5/5 |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE | 0/5 | 4/5 |
| S4_LOCAL_SATURATION | C1_COOPERATIVE_COMPACT | 0/5 | 5/5 |
| S4_LOCAL_SATURATION | C2_COOPERATIVE_EXPANDED | 0/5 | 5/5 |

## 3. Equidade de medição do B0

- tuplas distintas (warmup, início, fim, passos, horizon_complete) em todas as 100 execuções: 1 -> ['(300.0, 300.0, 3900.0, 3900, True)']
- arquivos canônicos ausentes: 0; linhas de telemetria de lane do B0 == 3900 x 36 em todas as execuções B0
- coorte ofertada idêntica entre os 5 controladores por (cenário, seed): True
- métricas canônicas presentes para controladores adaptativos mas ausentes para o B0: []

B0_MEASUREMENT_FAIR = YES

## 4. Semântica de retenção de verde (telemetria de junção, todas as 100 execuções)

| controlador | execuções | verdes | verdes > 20 s | verde máx (s) | valores de amarelo | valores de vermelho total | mudanças não sequenciais |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B0_FIXED | 20 | 28480 | 0 | 20 | [3] | [2] | 0 |
| B1_LOCAL_ADAPTIVE | 20 | 38266 | 3473 | 60 | [3] | [2] | 0 |
| B2_LOCAL_PRESSURE | 20 | 38964 | 2637 | 60 | [3] | [2] | 0 |
| C1_COOPERATIVE_COMPACT | 20 | 36174 | 3786 | 60 | [3] | [2] | 0 |
| C2_COOPERATIVE_EXPANDED | 20 | 26502 | 7012 | 60 | [3] | [2] | 0 |

max_green = 60 s (+1 passo de tolerância de amostragem). Nem todo controlador/cenário precisa reter verdes longos.

GREEN_HOLD_SEMANTICS_OBSERVED = YES

## 5. Tabela de população à prova de viés de sobrevivência (média de 5 seeds; métricas de viagens concluídas são condicionais à conclusão)

| cenário | controlador | ofertados | partiram | chegaram | razão de partida | concl. ofertados | concl. partidos | espera (s) | perda de tempo (s) | viagem (s) | paradas | throughput |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1_BALANCED | B0_FIXED | 1794 | 1794 | 1716 | 1.000 | 0.956 | 0.956 | 93.7 | 113.2 | 166.3 | 2.42 | 1795 |
| S1_BALANCED | B1_LOCAL_ADAPTIVE | 1794 | 1794 | 1732 | 1.000 | 0.965 | 0.965 | 60.6 | 80.4 | 133.6 | 2.53 | 1800 |
| S1_BALANCED | B2_LOCAL_PRESSURE | 1794 | 1794 | 1741 | 1.000 | 0.970 | 0.970 | 46.8 | 66.2 | 119.3 | 2.44 | 1811 |
| S1_BALANCED | C1_COOPERATIVE_COMPACT | 1794 | 1794 | 1731 | 1.000 | 0.965 | 0.965 | 67.7 | 87.7 | 140.9 | 2.60 | 1807 |
| S1_BALANCED | C2_COOPERATIVE_EXPANDED | 1794 | 1790 | 1614 | 0.997 | 0.900 | 0.902 | 197.3 | 225.6 | 278.4 | 3.48 | 1703 |
| S2_DIRECTIONAL_PEAK | B0_FIXED | 1191 | 1191 | 1144 | 1.000 | 0.961 | 0.961 | 95.1 | 114.5 | 167.1 | 2.29 | 1195 |
| S2_DIRECTIONAL_PEAK | B1_LOCAL_ADAPTIVE | 1191 | 1191 | 1152 | 1.000 | 0.967 | 0.967 | 71.6 | 90.8 | 143.5 | 2.30 | 1199 |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE | 1191 | 976 | 913 | 0.820 | 0.766 | 0.935 | 164.5 | 195.8 | 248.3 | 3.56 | 977 |
| S2_DIRECTIONAL_PEAK | C1_COOPERATIVE_COMPACT | 1191 | 903 | 850 | 0.758 | 0.714 | 0.942 | 143.5 | 170.2 | 222.8 | 3.09 | 917 |
| S2_DIRECTIONAL_PEAK | C2_COOPERATIVE_EXPANDED | 1191 | 824 | 773 | 0.692 | 0.649 | 0.938 | 165.5 | 192.5 | 245.0 | 3.12 | 841 |
| S3_DEMAND_SHIFT | B0_FIXED | 2019 | 1991 | 1817 | 0.986 | 0.900 | 0.913 | 114.2 | 138.3 | 192.5 | 2.83 | 1897 |
| S3_DEMAND_SHIFT | B1_LOCAL_ADAPTIVE | 2019 | 2011 | 1884 | 0.996 | 0.933 | 0.937 | 84.9 | 110.5 | 164.9 | 3.10 | 1953 |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE | 2019 | 1995 | 1873 | 0.988 | 0.927 | 0.938 | 76.7 | 102.6 | 157.0 | 3.07 | 1943 |
| S3_DEMAND_SHIFT | C1_COOPERATIVE_COMPACT | 2019 | 1969 | 1835 | 0.975 | 0.909 | 0.932 | 95.7 | 120.7 | 175.0 | 3.07 | 1911 |
| S3_DEMAND_SHIFT | C2_COOPERATIVE_EXPANDED | 2019 | 1832 | 1618 | 0.907 | 0.802 | 0.884 | 215.2 | 246.5 | 300.1 | 3.75 | 1707 |
| S4_LOCAL_SATURATION | B0_FIXED | 3587 | 1738 | 1317 | 0.484 | 0.367 | 0.758 | 573.1 | 680.9 | 740.2 | 11.84 | 1543 |
| S4_LOCAL_SATURATION | B1_LOCAL_ADAPTIVE | 3587 | 1532 | 1020 | 0.427 | 0.284 | 0.666 | 873.4 | 1130.6 | 1194.0 | 29.07 | 1245 |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE | 3587 | 1427 | 951 | 0.398 | 0.265 | 0.664 | 927.9 | 1166.2 | 1230.2 | 26.31 | 1187 |
| S4_LOCAL_SATURATION | C1_COOPERATIVE_COMPACT | 3587 | 1480 | 1096 | 0.413 | 0.306 | 0.741 | 738.2 | 894.3 | 958.1 | 16.73 | 1330 |
| S4_LOCAL_SATURATION | C2_COOPERATIVE_EXPANDED | 3587 | 1462 | 1114 | 0.408 | 0.310 | 0.762 | 609.7 | 702.5 | 765.9 | 9.33 | 1364 |

## 6. Comparação primária do piloto: B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT (cenário+seed pareados)

RETIDA: pelo menos um gate de validade de cenário é NO (comparação apenas após a validade passar).

## 7. Tempo de execução, armazenamento, variabilidade

- soma dos tempos de relógio das execuções: 165,5 min; média por execução por controlador: B0_FIXED 55 s, B1_LOCAL_ADAPTIVE 106 s, B2_LOCAL_PRESSURE 105 s, C1_COOPERATIVE_COMPACT 113 s, C2_COOPERATIVE_EXPANDED 118 s
- armazenamento de `artifacts/experiments/pilot_v2`: 147,6 MB (1,5 MB/execução)
- mediana entre cenários do coeficiente de variação entre seeds (dp/média sobre 5 seeds):

| métrica | B0_FIXED | B1_LOCAL_ADAPTIVE | B2_LOCAL_PRESSURE | C1_COOPERATIVE_COMPACT | C2_COOPERATIVE_EXPANDED |
| --- | --- | --- | --- | --- | --- |
| mean_network_queue_vehicles | 0.016 | 0.019 | 0.044 | 0.024 | 0.041 |
| throughput | 0.009 | 0.005 | 0.013 | 0.010 | 0.015 |
| mean_waiting_time | 0.018 | 0.022 | 0.053 | 0.028 | 0.051 |

## 8. Diferenças de engenharia V1 -> V2 (sem combinação estatística)

- Demanda estável: o S1 do V1 estava supersaturado; os níveis do V2 vêm de uma calibração pré-declarada apenas com B0 (S1 150, S2 320, S3 base 150 + choque 150, S4 escala 2,0 veíc/h por entrada).
- Medição de fila: as filas do V1 vinham de rastros do lado do controlador (ausentes para o B0, lanes duplicadas); o V2 usa uma telemetria canônica de lanes únicas para todo controlador.
- Semântica de retenção de verde: no V1, o KEEP_PHASE era efetivamente limitado ao verde estático; o V2 estende os verdes até `max_green` com amarelo/vermelho total ainda impostos.
- Realização das conversões: no V1, as razões declaradas não moldavam as rotas; o V2 usa um passeio de rota por razões de conversão com seed (70/15/15), com proporções realizadas nos metadados.
- Choque do S3: o choque do V2 é uma onda de uma borda (oeste) roteada via A5 exatamente no ponto médio da medição (2100 s), com base igual ao S1.
- Hotspot do S4: os veículos de hotspot do V2 são todos roteados por A5 (entradas de fundo + hotspot).
- Finalização de métricas: o V2 finaliza `run_metrics.json` automaticamente (`metrics_finalized=true`) e agrega `combined_metrics.parquet` no executor.

## 9. Riscos metodológicos

- Apenas 5 seeds: os ICs pareados são largos e descritivos; a decisão sobre seeds deve usar as larguras dos ICs acima, não valores-p.
- A validade de cenário é julgada no B0; controladores podem alterar o regime realizado (ver tabela informativa por controlador).
- A escala 2,0 do S4 é o topo da grade de calibração; sobrecarga pesada limitada por inserção e teleportes por congestionamento (contagem acima) podem distorcer a física das filas.
- As métricas de viagens concluídas são condicionais à conclusão e enviesadas quando as razões de conclusão diferem entre controladores.
- Agrupar os 4 cenários em uma única média pareada mistura regimes; as linhas por cenário são a visão interpretável.
- Os nomes de métricas solicitados diferem dos nomes congelados do projeto (mapeamento listado na seção 1).

## 10. Gates finais

```
PLANNED_RUNS = 100
COMPLETED_RUNS = 100
FAILED_RUNS = 0
METRICS_FINALIZED_ALL_RUNS = YES
S1_STABLE_REGIME_VALID = YES
S2_DIRECTIONAL_SCENARIO_VALID = YES
S3_ADAPTATION_SCENARIO_VALID = NO
S4_SATURATION_SCENARIO_VALID = YES
B0_MEASUREMENT_FAIR = YES
GREEN_HOLD_SEMANTICS_OBSERVED = YES
SCIENTIFIC_PILOT_VALID = NO
READY_FOR_SEED_DECISION = NO
```
