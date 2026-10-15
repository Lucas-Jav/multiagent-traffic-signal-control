# Figuras e tabelas — colocação recomendada no manuscrito

> Fonte: pacote oficial `artifacts/tcc-visuals/final/` (22 figuras e 6 tabelas; todas as figuras de resultado usam N = 10 seeds;
> somente FIG18 e FIG18B mostram o Pilot V2, rotuladas). Nenhum dado plotado foi alterado. Para o texto, preferir os
> arquivos vetoriais (PDF/SVG) em `document/`; para slides, `presentation/` (16:9). Rastreabilidade de cada item:
> `figure-manifest.json`.

## Mapa de colocação

| Figura/Tabela | Seção sugerida | Capítulo | Papel | N | Arquivo vetorial (PDF) |
|---|---|---|---|---|---|
| `FIG01_FINAL_OVERVIEW` | 3.2 Rede e visão geral do experimento | Metodologia | Visão geral: rede 3×3, 5 controladores, 4 cenários, 10 seeds, S5 e 290 execuções. | N = 290 | `artifacts/tcc-visuals/final/01_overview/FIG01_FINAL_OVERVIEW.pdf` |
| `FIG02_MAIN_CONTROLLER_OVERVIEW` | 6.1 Visão geral | Resultados | Médias finais por controlador e cenário (vazão, conclusão, espera, fila). | N = 10 | `artifacts/tcc-visuals/final/01_overview/FIG02_MAIN_CONTROLLER_OVERVIEW.pdf` |
| `FIG03_B0_VS_B2` | 6.2 e 6.6 (adaptação) | Resultados | Efeito da adaptação local em relação ao tempo fixo calibrado (B0 → B2). | N = 10 | `artifacts/tcc-visuals/final/02_adaptation/FIG03_B0_VS_B2.pdf` |
| `FIG04_B2_VS_C1` | 6.2–6.6 (comparação primária) | Resultados | Comparação primária da cooperação (B2 → C1), com IC95%. | N = 10 | `artifacts/tcc-visuals/final/03_cooperation/FIG04_B2_VS_C1.pdf` |
| `FIG05_COOPERATION_RESULT_MATRIX` | 6.6 Síntese | Resultados | Matriz de resultados da cooperação por cenário e métrica. | N = 10 | `artifacts/tcc-visuals/final/03_cooperation/FIG05_COOPERATION_RESULT_MATRIX.pdf` |
| `FIG06_S2_TRADEOFF` | 6.3 S2 | Resultados | Trade-off do S2: menos fila e espera, menor vazão e conclusão. | N = 10 | `artifacts/tcc-visuals/final/03_cooperation/FIG06_S2_TRADEOFF.pdf` |
| `FIG07_S3_SHOCK` | 6.4 S3 | Resultados | Fila da rede antes, durante e depois do choque de 2100 s. | N = 10 | `artifacts/tcc-visuals/final/05_s3_shock/FIG07_S3_SHOCK.pdf` |
| `FIG08_S3_POST_SHOCK_AUC` | 6.4 S3 | Resultados | Área da fila pós-choque (métrica congelada). | N = 10 | `artifacts/tcc-visuals/final/05_s3_shock/FIG08_S3_POST_SHOCK_AUC.pdf` |
| `FIG09_S4_B2_VS_C1` | 6.5 S4 | Resultados | Benefício da cooperação sob saturação localizada e piora do atraso de partida. | N = 10 | `artifacts/tcc-visuals/final/06_s4_saturation/FIG09_S4_B2_VS_C1.pdf` |
| `FIG10_S4_TELEPORTS` | 6.5 S4 | Resultados | Teleports do SUMO no S4 (ALLOW_AND_MEASURE). | N = 10 | `artifacts/tcc-visuals/final/06_s4_saturation/FIG10_S4_TELEPORTS.pdf` |
| `FIG11_REFERENCE_ROUTE` | 6.7 Rota de referência | Resultados | Tempo de viagem e conclusão da rota (B0, B2, C1). | N = 10 | `artifacts/tcc-visuals/final/04_reference_route/FIG11_REFERENCE_ROUTE.pdf` |
| `FIG12_REFERENCE_ROUTE_EFFECTS` | 6.7 Rota de referência | Resultados | Efeitos pareados: adaptação (B0 → B2) e cooperação (B2 → C1) na rota. | N = 10 | `artifacts/tcc-visuals/final/04_reference_route/FIG12_REFERENCE_ROUTE_EFFECTS.pdf` |
| `FIG13_S3_NETWORK_VS_ROUTE` | 6.7 Rota de referência (rede × rota em S3) | Resultados | Escalas diferentes de análise no S3. | N = 10 | `artifacts/tcc-visuals/final/04_reference_route/FIG13_S3_NETWORK_VS_ROUTE.pdf` |
| `FIG14_S5_PACKET_LOSS` | 6.8 S5 | Resultados | Vazão em função da perda de pacotes (C1, C2, B2). | N = 10 | `artifacts/tcc-visuals/final/07_s5_communication/FIG14_S5_PACKET_LOSS.pdf` |
| `FIG14B_S5_COMPLETION` | 6.8 S5 | Resultados | Conclusão em função da perda de pacotes. | N = 10 | `artifacts/tcc-visuals/final/07_s5_communication/FIG14B_S5_COMPLETION.pdf` |
| `FIG15_S5_QUEUE_DELAY` | 6.8 S5 | Resultados | Fila e espera em função da perda de pacotes. | N = 10 | `artifacts/tcc-visuals/final/07_s5_communication/FIG15_S5_QUEUE_DELAY.pdf` |
| `FIG16_COMMUNICATION_COST` | 6.9 Custo de comunicação | Resultados | Mensagens, bytes enviados e entregues (C1 vs C2). | N = 10 | `artifacts/tcc-visuals/final/08_communication_cost/FIG16_COMMUNICATION_COST.pdf` |
| `FIG17_PERFORMANCE_VS_COMMUNICATION_COST` | 6.9 e 7 (discussão do custo) | Resultados/Discussão | Desempenho de C2 vs C1 junto do custo de comunicação. | N = 10 | `artifacts/tcc-visuals/final/08_communication_cost/FIG17_PERFORMANCE_VS_COMMUNICATION_COST.pdf` |
| `FIG18_PILOT_VS_FINAL` | 6.10 Piloto × Final | Resultados (metodológico) | Efeito B2 → C1: piloto (N=5) vs final (N=10), amostras não combinadas. | Piloto 5 seeds; Final 10 seeds (5 comuns) | `artifacts/tcc-visuals/final/09_pilot_vs_final/FIG18_PILOT_VS_FINAL.pdf` |
| `FIG18B_N10_VALUE` | 6.10 Piloto × Final | Resultados (metodológico) | Valor de N=10: direção persistente, ICs mais estreitos. | Piloto 5 / Final 10 | `artifacts/tcc-visuals/final/09_pilot_vs_final/FIG18B_N10_VALUE.pdf` |
| `FIG19_FINAL_RESULT_MATRIX` | 7 Discussão e 10 Conclusão | Discussão/Conclusão | Matriz final de resultados por cenário. | N = 10 | `artifacts/tcc-visuals/final/10_summary/FIG19_FINAL_RESULT_MATRIX.pdf` |
| `FIG20_RESEARCH_QUESTION` | 10.1 Conclusão (e defesa) | Conclusão | Resposta à pergunta de pesquisa. | N = 10 | `artifacts/tcc-visuals/final/10_summary/FIG20_RESEARCH_QUESTION.pdf` |
| `TABLE01_CONTROLLERS` | 3.4 Controladores | Metodologia | Definição dos cinco controladores. | N = 10 | `artifacts/tcc-visuals/final/tables/TABLE01_CONTROLLERS.pdf` |
| `TABLE02_SCENARIOS` | 3.3 Cenários e 3.7 Delineamento | Metodologia | Definição dos cenários S1–S5. | N = 10 | `artifacts/tcc-visuals/final/tables/TABLE02_SCENARIOS.pdf` |
| `TABLE03_PRIMARY_B2_VS_C1` | 6.6 Resultados primários (e 6.2–6.5) | Resultados | Resultado primário B2 → C1 (5 métricas × 4 cenários). Corresponde ao 'TABLE03_PRIMARY_FINAL_RESULTS' citado no plano. | N = 10 | `artifacts/tcc-visuals/final/tables/TABLE03_PRIMARY_B2_VS_C1.pdf` |
| `TABLE04_REFERENCE_ROUTE` | 6.7 Rota de referência | Resultados | Tempo de viagem e conclusão por controlador; Δ B0→B2 e B2→C1. | N = 10 | `artifacts/tcc-visuals/final/tables/TABLE04_REFERENCE_ROUTE.pdf` |
| `TABLE05_S5` | 6.8 S5 | Resultados | S5: desempenho e comunicação por nível de perda. | N = 10 | `artifacts/tcc-visuals/final/tables/TABLE05_S5.pdf` |
| `TABLE06_COMMUNICATION_COST` | 6.9 e 7 Discussão | Resultados/Discussão | Custo de comunicação C1 vs C2. | N = 10 | `artifacts/tcc-visuals/final/tables/TABLE06_COMMUNICATION_COST.pdf` |

## Ordem mínima exigida

| Figura | Local no manuscrito |
|---|---|
| FIG01 | Metodologia — visão geral |
| FIG03 | Resultados — adaptação |
| FIG04 | Resultados — comparação primária da cooperação |
| FIG06 | Resultados — S2 (trade-off) |
| FIG07 e FIG08 | Resultados — S3 |
| FIG09 e FIG10 | Resultados — S4 |
| FIG11, FIG12 e FIG13 | Resultados — rota de referência |
| FIG14 e FIG15 | Resultados — S5 |
| FIG16 e FIG17 | Resultados/Discussão — custo de comunicação |
| FIG18 | Resultados — comparação metodológica Piloto × Final |
| FIG19 e FIG20 | Discussão e conclusão |

| Tabela | Local |
|---|---|
| TABLE01_CONTROLLERS | Metodologia |
| TABLE02_SCENARIOS | Desenho experimental |
| TABLE03_PRIMARY_B2_VS_C1 (= "resultados primários finais") | Resultados |
| TABLE04_REFERENCE_ROUTE | Subseção da rota de referência |
| TABLE05_S5 | Subseção S5 |
| TABLE06_COMMUNICATION_COST | Discussão |

## Legendas sugeridas (editar conforme a norma da instituição)

**FIG01_FINAL_OVERVIEW** — Diagrama explicativo (não é gráfico de desempenho): rede 3×3, 5 controladores, 4 cenários, 10 seeds e o experimento S5 sobre o tráfego do S2.

**FIG02_MAIN_CONTROLLER_OVERVIEW** — Médias finais por controlador e cenário para vazão, conclusão, espera e fila média da rede; N = 10 seeds.

**FIG03_B0_VS_B2** — Diferenças relativas pareadas (B2 − B0)/B0 por cenário. Em S1 o B2 reduz espera e fila; em S2, S3 e S4 o tempo fixo calibrado (B0) é favorecido na maior parte das métricas-chave.

**FIG04_B2_VS_C1** — Comparação primária B2 vs C1. S1 e S3: B2 favorecido; S2: trade-off (menos espera/fila, menor vazão/conclusão); S4: C1 favorecido nas métricas principais de congestionamento.

**FIG05_COOPERATION_RESULT_MATRIX** — Matriz cenário × métrica com o lado favorecido e a interpretação geral validada na análise final.

**FIG06_S2_TRADEOFF** — No S2, o C1 reduz espera e fila em 10/10 seeds, mas reduz vazão e conclusão. Tempos menores não podem ser lidos sem a conclusão.

**FIG07_S3_SHOCK** — Série temporal da fila total da rede em S3 para B0, B2 e C1 (média e ± 1 DP entre 10 seeds); choque em 2100 s.

**FIG08_S3_POST_SHOCK_AUC** — post_shock_queue_auc_vehicle_seconds para B0, B2 e C1 (N = 10) com diferenças pareadas e IC95%.

**FIG09_S4_B2_VS_C1** — Efeitos pareados B2 → C1 em S4 com IC95%: o benefício aparece nas métricas de congestionamento; o atraso de partida piora.

**FIG10_S4_TELEPORTS** — Contagem de teleports por controlador no S4 (política ALLOW_AND_MEASURE).

**FIG11_REFERENCE_ROUTE** — Tempo de viagem médio e conclusão da coorte da rota exata para B0, B2 e C1 em S1–S4 (N = 10), em conjunto.

**FIG12_REFERENCE_ROUTE_EFFECTS** — Efeito da adaptação (B0→B2) e da cooperação (B2→C1) no tempo de viagem da rota, com IC95% e variação da conclusão.

**FIG13_S3_NETWORK_VS_ROUTE** — No S3, o B2 é favorecido na rede inteira e o C1 reduz o tempo de viagem da rota de referência: são populações diferentes.

**FIG14_S5_PACKET_LOSS** — Vazão média de C1 e C2 por nível de perda, com B2 como referência; padrão não monotônico.

**FIG14B_S5_COMPLETION** — Fração dos veículos oferecidos concluída por C1 e C2 por nível de perda, com B2 como referência.

**FIG15_S5_QUEUE_DELAY** — Fila média da rede e espera média de C1 e C2 por nível de perda (painéis com escalas próprias), B2 como referência.

**FIG16_COMMUNICATION_COST** — Mensagens enviadas, bytes enviados e bytes entregues por run para C1 e C2 em cada nível de perda (S2).

**FIG17_PERFORMANCE_VS_COMMUNICATION_COST** — Efeito de C2 vs C1 em vazão e espera por cenário, junto do custo adicional de comunicação (≈ 2,3× bytes).

**FIG18_PILOT_VS_FINAL** — Estimativas do efeito B2→C1 no piloto (N=5) e no final (N=10) para S1–S4, rotuladas e sem combinar amostras.

**FIG18B_N10_VALUE** — Direção persistiu em 50/51 comparações; ICs de vazão estreitaram; efeito de vazão em S4 menor com N=10.

**FIG19_FINAL_RESULT_MATRIX** — Resumo por cenário das comparações B0 vs B2 e B2 vs C1 e da interpretação principal.

**FIG20_RESEARCH_QUESTION** — Síntese slide-ready: efeito da cooperação dependente do cenário; sem superioridade geral.

**TABLE01_CONTROLLERS** — Definições dos controladores (todos reativos; nenhum prevê demanda nem usa aprendizado de máquina). Tamanho da mensagem: média de bytes por mensagem enviada (S5, perda 0%).

**TABLE02_SCENARIOS** — Aquecimento de 300 s e medição de 3600 s em todos os cenários; 10 seeds por condição. O S5 usa o tráfego do S2 e varia apenas a perda de comunicação.

**TABLE03_PRIMARY_B2_VS_C1** — Diferença = C1 − B2, pareada por seed (N = 10); IC95% por bootstrap pareado. Relativo = diferença média / média do B2. Espera é condicional às viagens concluídas.

**TABLE04_REFERENCE_ROUTE** — Tempo de viagem médio (s) e conclusão (fração dos oferecidos) da coorte da rota; diferenças pareadas (tratamento − baseline), IC95% bootstrap (N = 10). Tempos valem só para viagens concluídas — leia-os junto da conclusão.

**TABLE05_S5** — Médias por run (N = 10 seeds por linha). B2 é a referência sem comunicação (10 seeds, não duplicada). Espera é condicional às viagens concluídas. Com 100% de perda, C1 e C2 têm as mesmas métricas de tráfego do B2 e nenhuma mensagem é entregue.

**TABLE06_COMMUNICATION_COST** — Médias por run (S2, perda 0%, N = 10). Benefício geral de tráfego conforme a classificação final C1 vs C2 por cenário (análise final N = 10).

## Recomendações de uso

1. Mantenha o aviso de que a seed 42 dos vídeos é apenas ilustrativa; as figuras de resultado usam as 10 seeds.
2. Em todas as figuras de tempo de espera, perda de tempo e tempo de viagem, mantenha a nota de que são **condicionais a viagens concluídas**.
3. Não recolora as figuras com "verde = bom / vermelho = ruim"; os rótulos de controladores e marcadores são os mesmos em todo o pacote.
4. Não some Piloto + Final em uma mesma figura de resultado (as cinco primeiras seeds coincidem).
5. Se o editor de texto exigir PNG, use `document/*_A4w_300dpi.png`.
