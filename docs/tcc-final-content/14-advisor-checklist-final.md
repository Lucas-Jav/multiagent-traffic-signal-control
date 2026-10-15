# Checklist final do feedback do orientador

> Atualização do `docs/advisor-feedback-checklist.md` (Prompts 55/55.5) após a campanha final, o congelamento e a análise final.
> "Status no conteúdo" indica se o item está resolvido nos artefatos científicos e no conteúdo acadêmico preparado nesta etapa.
> **Aplicação ao manuscrito submetido** é uma ação do(a) autor(a): este conteúdo não sobrescreve o manuscrito.

| # | Pedido do orientador | Status no conteúdo | Como foi atendido (evidência) | Aplicar ao manuscrito |
|---|---|---|---|---|
| 1 | Redação consistente entre hipótese e resultados; sem claims preditivos/ML | **DONE** | Pergunta de pesquisa tratada como pergunta; resposta "dependente do cenário" (`12-conclusao.md`); sistema descrito como reativo, distribuído e cooperativo; ML/RL/previsão só como trabalho futuro (`11-trabalhos-futuros.md`) | Substituir resumo, introdução, resultados e conclusão; remover vocabulário preditivo |
| 2 | Um conjunto canônico de métricas | **DONE** | Definições, denominadores e semântica congelados (`metrics.md`; `metric_definitions.py`); pipeline único de métricas; Seção 3.8 | Usar os mesmos nomes e a regra de métricas condicionais |
| 3 | Baselines alinhados | **DONE** | Papéis e semântica temporal de B0/B1/B2/C1/C2 (`baselines.md`); comparação primária B2 vs C1; TABLE01 | Alinhar nomes e a comparação primária |
| 4 | Calibração explícita do tempo fixo (B0) | **DONE** | `B0_FIXED_CALIBRATED`, método `EMPIRICAL_FIXED_TIME`, plano `fx_c84_demand_proportional_alternate`, seeds exclusivas, sem usar B1/B2/C1/C2; Seção 3.4.1 | Rotular o B0 de 98 s como histórico; não chamar de Webster |
| 5 | Nomes de interseção padronizados | **DONE** | A1–A9 no texto e nas figuras; IDs SUMO só na primeira menção (`intersection-glossary.md`; A5 = `B1` no SUMO) | Aplicar A1–A9 em figuras antigas e na prosa |
| 6 | Valores de perda de pacotes padronizados | **DONE** | 0, 20, 50 e 100%, atraso 0, S5 sobre o tráfego do S2 (`experiments.md` e congelamento) | Remover a matriz antiga (atraso {0,1,3,5} × perda {0; 5; 10; 25%}) |
| 7 | Número de seeds padronizado | **DONE** | 10 seeds finais (42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001); decisão documentada na Seção 4.3 | Trocar qualquer menção a 5 seeds como resultado final |
| 8 | Comparação de tempo de viagem em rota de referência (tradicional × adaptativo local × cooperativo) | **DONE** | Rota exata `left1A1 → A1B1 → B1C1 → C1right1`; B0 calibrado, B2 e C1; N = 10; Seção 6.7; FIG11–FIG13; TABLE04 | Substituir qualquer resultado N = 5 pré-final |
| 9 | Reportar B0 → B2 (adaptação) e B2 → C1 (cooperação) separadamente na rota | **DONE** | Seção 6.7 e FIG12; sem agregar os efeitos | — |
| 10 | Intervalos de confiança por seed (diferenças pareadas) | **DONE** | Diferenças pareadas por seed (cenário + seed) com IC95% por bootstrap percentil pareado (10 000 reamostragens); diferenças por seed preservadas em `final_pairwise_summary.csv` | Reportar IC95% junto de toda comparação |
| 11 | Resultados finais reais | **DONE** | Campanha final: 200/200 (principal) + 90/90 (S5) = 290/290 execuções; análise final validada | Substituir todos os números do Pilot V2 usados como resultado final |

## Extras da auditoria

| Item | Estado |
|---|---|
| Divulgação do critério S3 *post-hoc* | Presente (Seções 3.9 e 8) |
| Política de teleports `ALLOW_AND_MEASURE` e totais finais do S4 | Presente (Seções 3.9 e 6.5) |
| Métricas condicionais e viés de sobrevivência | Presente (Seções 3.8, 6.3, 6.5, 6.7) |
| Baseline histórico B0 rotulado como histórico | Presente (Seções 3.4.1, 4.3) |
| Piloto V2 não combinado ao final | Presente (Seção 6.10) |
| Ausência de explicações causais não testadas | Explicações rotuladas como hipóteses (Seção 7.3) |
