> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/pilot-v2-release-decision.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado sem alteracao abaixo.

# Decisão de liberação do Pilot V2 para a comparação B2 vs C1

`campaign_role: PILOT`. Decisão baseada somente em artefatos já existentes; nenhuma simulação nova, nenhum arquivo do repositório alterado. A comparação B2 vs C1 **não foi calculada** neste documento.

## 1. Fontes lidas

- `s3-composite-gate-reevaluation.md` e `s3-composite-gate-table.csv` (Prompt 48).
- `pilot-assessment.md` e `pilot_v2_gates.json` (Prompt 46.8), `s3-stability-adjudication.md`, `s4-teleport-audit.md` (Prompt 46.9), `pilot-v2-methodological-decision.md` (Prompt 47).

## 2. Status final dos gates

| Gate | Status | Base |
| --- | --- | --- |
| Execução | 100 planejadas, 100 concluídas, 0 falhas; transições `RUNNING->COMPLETED` nas 100 | Pilot V2 (46.8) |
| Métricas finalizadas | YES (`metrics_finalized=true` nas 100, nenhuma métrica obrigatória ausente) | 46.8 |
| S1 (regime estável) | **VALID** | 46.8: 5/5 seeds B0 passam todos os critérios |
| S2 (direcional) | **VALID** | 46.8: 5/5 seeds B0 passam todos os critérios |
| S3 (adaptação) | **VALID** (gate composto) | 48: 5/5 seeds válidas (4 VALID, 1 VALID_WITH_DIAGNOSTIC_WARNING), exigência mínima 4/5 |
| S4 (saturação A5) | **VALID**, política ALLOW_AND_MEASURE | 46.8: 5/5 seeds B0 passam; 46.9 e 47: teleports não afetam a validade |
| B0 medido com o mesmo pipeline | YES | 46.8 |
| Green-hold observado | YES | 46.8 (B1/B2/C1/C2 com verdes > 20 s, max 60 s, amarelo 3 s, all-red 2 s, 0 trocas fora de ordem) |

O único gate que tinha falhado no 46.8 era o S3, por um critério de 360 s sem poder de discriminação suficiente (Prompt 46.9). Na reavaliação do Prompt 48 todos os critérios principais passam nas 5 seeds: sem backlog (partida = 100% do oferecido, atraso de inserção máximo 1 s), 0 não inseridos, 0 saturação de faixa, janela agregada de 1800 s estável (normalizado entre −0,092 e +0,031, limite 0,10). As verificações mantidas (base igual à do S1, choque em 2100 s, origem oeste, via A5, resposta visível, AUC) não falharam em nenhuma seed.

## 3. Decisão

```
PILOT_V2_RELEASED_FOR_B2_VS_C1 = YES
B2_VS_C1_COMPARISON_ALLOWED    = YES
```

O bloqueio metodológico do S3 foi removido. Com S1, S2, S3 e S4 válidos, o critério de "comparação só depois das validades" do Prompt 46.8 está satisfeito. Nenhuma nova calibração, definição metodológica ou simulação é necessária.

Escopo da liberação: a comparação pareada (mesma cenário + seed) B2 vs C1, descritiva, com as seis métricas definidas no Prompt 46.8 (espera, time loss, throughput, fila média da rede, tempo de viagem, razão de conclusão) e bootstrap pareado. Sem ranking, sem afinação de controladores, sem mistura de V1 com V2.

## 4. Ressalvas obrigatórias no relatório final

1. **S3 validado por gate composto.** A janela de 1800 s foi escolhida depois de observar os dados da auditoria 46.9 (limiar 0,10 e piso de 5 veículos inalterados). A regra de 4/5 seeds é grosseira para 5 seeds. A falha de 360 s da seed 4517 (projetado 6,51 veículos contra limite 5,00) deve ser reportada como diagnóstico, não escondida.
2. **Validade avaliada no B0.** O regime dos cenários foi validado nas runs de referência `B0_FIXED`. Os controladores adaptativos podem alterar o regime realizado; a tabela informativa por controlador do relatório do 46.8 deve acompanhar os resultados.
3. **S4 (ALLOW_AND_MEASURE).** Reportar `sumo_teleports_total` ao lado de todo resultado do S4 (17 teleports no piloto: B0 14, B2 3 na seed 5791, B1/C1/C2 0). Incluir a sensibilidade do B2 vs C1 sem a dupla S4 seed 5791. A escala do S4 (2.0) está no topo da grade de calibração; `departure_ratio` de 0,33 a 0,49 entre as runs (sobrecarga intencional, metade da demanda não entra).
4. **Métricas condicionais à conclusão.** Espera, time loss, tempo de viagem e paradas só valem junto com offered, departed, arrived e razões de conclusão (tabela de população do 46.8). Não interpretar atraso de viagem isoladamente, principalmente no S4.
5. **Amostra pequena.** 5 seeds: os IC pareados serão largos e descritivos. A agregação entre os 4 cenários mistura regimes; as linhas por cenário (5 duplas) são a leitura interpretável.
6. **Nomes das métricas.** Os nomes pedidos `mean_waiting_time_seconds`, `mean_time_loss_seconds` e `mean_travel_time_seconds` correspondem aos nomes congelados do projeto `mean_waiting_time`, `mean_time_loss` e `mean_travel_time`.
7. **Teleports só testados em B0.** O contrafactual sem teleport foi validado apenas com B0. Não generalizar para os adaptativos.
8. **Pilot V2 é piloto.** Resultados não entram na campanha final. A decisão de número de seeds usa as larguras de IC, não p-valores.

## 5. Próximo passo (não executado)

Executar a análise pareada B2 vs C1 sobre o `combined_metrics.parquet` do Pilot V2 (o bootstrap pareado com semente 20260930 e 10.000 reamostragens está em `analysis/pilot_v2_analysis.py`; atenção: esse script ainda aplica o critério antigo de 360 s no S3 e reteria a comparação, então a execução deve usar o gate composto do Prompt 47 sem alterar os resultados já registrados) e registrar os resultados com as ressalvas acima. Esse passo precisa de pedido explícito.

> **Status update (final audit, Prompt 52).** The next step in section 5 was executed in Prompt 50 with the composite gate (`analysis/b2_vs_c1.py`, not the old 360 s script). Result: MIXED, confidence MEDIUM (`b2-vs-c1-final-comparison.md`).
