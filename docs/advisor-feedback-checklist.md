# Checklist do Feedback do Orientador

Atualizado nos Prompts 55 e 55.5 (alinhamento metodológico e limpeza de documentação). Estados possíveis:
`DONE` (resolvido no repositório), `PARTIAL` (parte resolvida), `PENDING` (não iniciado ou depende de
outra tarefa).

| # | Pedido do orientador | Estado atual | Ação realizada | Ação restante | Status |
|---|---|---|---|---|---|
| 1 | Redação consistente entre hipótese e resultados (inclui: sem claims preditivos/ML não implementados) | Resultado do Pilot V2 = MIXED (confiança MEDIUM). Repositório não contém claims de ML/previsão, mas usava nomes históricos ("demanda projetada", `arrival_trend`). Texto do TCC está fora do repositório. | Criado `methodology/tcc-scope-alignment.md` (escopo reativo, não implementado, título recomendado, redação de resultados MIXED, S5 não executado). Nomes históricos documentados em `controllers.md` e `baselines.md`; comentários no código. | Revisar título, resumo, introdução, fundamentação e metodologia do TCC. Reescrever a hipótese como pergunta/hipótese e os resultados conforme MIXED. | PARTIAL |
| 2 | Um conjunto canônico de métricas | `metric_definitions.py` já era a fonte; `metrics.md` tinha lacunas e aliases soltos. | Tabela canônica única em `metrics.md` (nome, exibição PT, unidade, fonte, população, denominador, fórmula, cenários, ressalva). Aliases resolvidos e documentados (`mean_message_age_steps`, `max_message_age_steps`; `avg_waiting_time` em `report.py` é alias de exibição intencional). Métricas não implementadas listadas como futuras. | Implementar as métricas `reference_route_*` (ver item 8). | DONE |
| 3 | Baselines alinhados | Controladores documentados em `controllers.md` sem papéis/semântica temporal consolidados. | Criado `methodology/baselines.md` (B0, B1, B2, C1, C2: papel, algoritmo, observações, comunicação, semântica temporal, `PhaseSafetyManager`, papel experimental). `PRIMARY_SCIENTIFIC_COMPARISON = B2 vs C1`. | Nenhuma no repositório. | DONE |
| 4 | Calibração explícita do tempo fixo (B0) | Pilot V2 usou `B0_FIXED_STATIC` (`STATIC_DEFAULT`, ciclo 98 s, não Webster). | Calibração concluída (Prompt 55.5): `B0_FIXED_CALIBRATED`, método `EMPIRICAL_FIXED_TIME` (grade predeclarada de 30 planos, objetivo B0-only, seeds exclusivas 101/1009/2029, validação em 3011/4021/5003). Plano: ciclo 84 s, divisão proporcional à demanda, offsets alternados; J validação 0,849. B0 histórico preservado. Ver `methodology/fixed-time-calibration.md`. | Usar `B0_FIXED_CALIBRATED` na campanha final (atualizar `final_main.yaml` antes do congelamento). Reportar que o plano é pior que o estático no S4. | **DONE** (calibração); integração na config final pendente |
| 5 | Nomes de interseção padronizados | Dois esquemas (A1-A9 lógicos; A0..C2 SUMO) sem glossário único. | Criado `methodology/intersection-glossary.md` (mapeamento completo; A5 = `B1`; arestas de borda; regras de uso). | Aplicar A1-A9 em figuras e prosa do TCC. | DONE |
| 6 | Valores de perda de pacotes padronizados | `experiments.md` e configs legadas usavam delay {0,1,3,5} x drop {0, 0.05, 0.10, 0.25}; configs finais usam drop {0, 0.20, 0.50, 1.00}, delay 0. | `experiments.md` reescrito: S5 canônico (perda 0/20/50/100%, atraso 0, base S2, ref. B2, C1/C2). Matriz antiga marcada DEPRECATED/HISTORICAL (docs, configs legadas, gerador). S5B atraso opcional separado. | Executar o S5 somente após a decisão final de seeds e o congelamento. **S5 NÃO foi executado.** | DONE (definição); execução pendente |
| 7 | Número de seeds | Pool predeclarado de 10 seeds; seeds do piloto 42/2027/3253/4517/5791; contagem final pendente (configs finais usam as seeds do piloto como placeholder). | Documentado em `campaign-matrix.md` e `evidencias/pilot-v2/`. | Decidir a contagem final com base na largura dos IC; congelar. | PENDING |
| 8 | Comparação de tempo de viagem em rota de referência (tradicional x adaptativo local x cooperativo) | Dados existem (`tripinfo.xml` por run, rotas determinísticas). Rota selecionada: W->E (`left1A1 A1B1 B1C1 C1right1`; A4->A5->A6). Métrica não implementada; nenhum resultado calculado. | Criado `methodology/reference-route.md` (rota, justificativa estrutural independente de desempenho, regra de coorte, métricas futuras, comparações B0/B2/C1). | Implementar e calcular `reference_route_*` sobre as runs; reportar com razão de conclusão. | PARTIAL |

## Extras da auditoria

| Item | Estado |
|---|---|
| Baseline calibrado | `experiments/fixed_time/b0_fixed_calibrated.json`; evidências em `evidencias/fixed-time-calibration/`. |
| Gate S3 versionado | `methodology/scenario-validity-gates.md` (gate composto, limitação post-hoc explícita). |
| Gate bruto superado (`pilot_v2_gates.json`) | Preservado; supersessão documentada em `evidencias/pilot-v2/README.md`. |
| Evidências do Pilot V2 versionadas | `docs/evidencias/pilot-v2/` (leve; proveniência e SHA-256 em `evidence-manifest.json`). |
| Documentos históricos | `campaign_plan.md`, `v1-readiness-report.md`, README marcados como históricos/superados. |
