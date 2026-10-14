> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/final-scientific-conclusion.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado sem alteracao abaixo.

# Conclusão científica final do Pilot V2

`campaign_role: PILOT`. Comparação B2_LOCAL_PRESSURE (B2) vs C1_COOPERATIVE_COMPACT (C1) no Pilot V2: 4 cenários x 5 seeds (42, 2027, 3253, 4517, 5791), pares por cenário e seed, diferença C1 − B2. Todos os números vêm de `b2-vs-c1-final-comparison-table.csv` e `b2-vs-c1-seed-sensitivity.csv` (Prompt 50); nenhuma simulação nova foi executada e nenhum resultado foi recalculado.

## 1. Conclusão em uma frase

O Pilot V2 **não** fornece evidência suficiente para afirmar superioridade geral do C1 sobre o B2. O resultado é **MIXED** (confiança MEDIUM): o C1 melhorou claramente apenas no cenário saturado S4; piorou nos cenários S1 e S3; e no S2 mostrou um trade-off (menor atraso e fila, mas menor throughput e conclusão).

## 2. Resultado numérico

Média sobre as 5 seeds por cenário. "Seeds C1 melhor" conta as seeds em que o C1 é melhor que o B2. Direção favorável: menor é melhor para espera, time loss, fila e tempo de viagem; maior é melhor para throughput e conclusão. Espera, time loss e tempo de viagem são condicionais à conclusão da viagem e devem ser lidos junto com as colunas de população.

| Cenário | Métrica | B2 | C1 | Diferença (C1−B2) | Seeds C1 melhor |
| --- | --- | --- | --- | --- | --- |
| S1 | espera (s) | 46,8 | 67,7 | +44,7% | 0/5 |
| S1 | time loss (s) | 66,2 | 87,7 | +32,6% | 0/5 |
| S1 | throughput | 1811 | 1807 | −0,2% (neutro) | 2/5 |
| S1 | fila média da rede | 23,8 | 34,3 | +44,1% | 0/5 |
| S1 | tempo de viagem (s) | 119,3 | 140,9 | +18,0% | 0/5 |
| S1 | conclusão (oferecidos) | 0,970 | 0,965 | −0,006 | 0/5 |
| S2 | espera (s) | 164,5 | 143,5 | −12,7% | 5/5 |
| S2 | time loss (s) | 195,8 | 170,2 | −13,1% | 5/5 |
| S2 | throughput | 976,6 | 916,8 | −6,1% | 0/5 |
| S2 | fila média da rede | 45,7 | 38,3 | −16,3% | 5/5 |
| S2 | tempo de viagem (s) | 248,3 | 222,8 | −10,3% | 5/5 |
| S2 | conclusão (oferecidos) | 0,766 | 0,714 | −0,052 | 0/5 |
| S3 | espera (s) | 76,7 | 95,7 | +24,7% | 0/5 |
| S3 | time loss (s) | 102,6 | 120,7 | +17,7% | 0/5 |
| S3 | throughput | 1943 | 1911 | −1,6% | 0/5 |
| S3 | fila média da rede | 43,9 | 53,5 | +21,9% | 0/5 |
| S3 | tempo de viagem (s) | 157,0 | 175,0 | +11,5% | 0/5 |
| S3 | conclusão (oferecidos) | 0,927 | 0,909 | −0,019 | 0/5 |
| S3 | time loss pós-choque (s) | 135,8 | 151,5 | +11,5% | 0/5 |
| S3 | AUC de fila pós-choque (veículo·s) | 115.240 | 131.035 | +13,7% | 0/5 |
| S4 | espera (s) | 927,9 | 738,2 | −20,4% | 5/5 |
| S4 | time loss (s) | 1166,2 | 894,3 | −23,3% | 5/5 |
| S4 | throughput | 1187 | 1330 | +12,0% | 5/5 |
| S4 | fila média da rede | 358,7 | 295,1 | −17,7% | 5/5 |
| S4 | tempo de viagem (s) | 1230,2 | 958,1 | −22,1% | 5/5 |
| S4 | conclusão (oferecidos) | 0,265 | 0,306 | +0,041 | 5/5 |

Regra predeclarada (célula = cenário x métrica principal, 24 células): 10 favoráveis ao C1, 13 desfavoráveis, 1 neutra. Os intervalos de bootstrap pareado de 95% (10.000 reamostragens, n = 5 por cenário) excluem zero em todas as células classificadas como favoráveis ou desfavoráveis; são descritivos.

Leitura agregada (20 pares, mistura regimes): espera −14,0%, time loss −16,8%, tempo de viagem −14,7%, fila −10,8%, throughput +0,8% (IC [−25,4; +59,8], inclui zero), conclusão −0,009 (IC [−0,03; +0,01], inclui zero). Esses ganhos agregados de atraso vêm principalmente das grandes magnitudes do S4 e **não** indicam benefício geral.

## 3. Interpretação

- **S4 (saturação no A5): benefício claro.** O C1 foi melhor nas 5 seeds nas seis métricas principais: menos espera, menos time loss, menos fila, mais throughput e mais conclusão. Como a demanda do S4 é intencionalmente sobrecarregada (cerca de metade não entra), o ganho refere-se ao regime saturado, e as razões de partida (0,398 contra 0,413) não diferem de forma clara (3/5 seeds, IC inclui zero); o ganho de conclusão vem principalmente da fração dos veículos que entraram (conclusão entre partidos 0,664 contra 0,741).
- **S1 (balanceado) e S3 (choque): o C1 é pior.** Em todas as seeds o C1 teve mais espera, time loss, tempo de viagem e fila que o B2, com conclusão ligeiramente menor. No S3 o efeito se mantém depois do choque (time loss pós-choque +11,5%, AUC de fila pós-choque +13,7%). No S1 o throughput é neutro.
- **S2 (pico direcional): trade-off.** O C1 reduz atraso e fila nas 5 seeds, mas reduz throughput (−6,1%), a razão de partida (0,820 contra 0,758) e a conclusão (−0,052) nas 5 seeds. A redução do atraso das viagens concluídas acontece junto com menos viagens concluídas; não se deve ler o menor atraso isoladamente como melhora.
- **Indicadores secundários** (mesma direção geral, sem alterar a conclusão): `internal_lane_persistence_events` é menor no C1 em S2 (−8,1%), S3 (−2,0%) e S4 (−44,2%) nas 5 seeds, e neutro no S1. O tempo de viagem do corredor é menor no C1 em S2, S3 e S4 (condicional à conclusão) e maior no S1.
- **Sensibilidade sem a dupla S4 seed 5791** (única com teleports no B2): a direção de espera, time loss, tempo de viagem e fila se mantém no agregado e no S4 (os IC do S4 continuam excluindo zero). O ganho de throughput do C1 no S4 cai de +142,6 para +85,5 veículos (IC [59,5; 111,5]) e o sinal do throughput agregado inverte (de +11,7 para −7,2; IC [−32,0; +19,2]): o throughput agregado é sensível a essa seed. Na retirada de uma seed de cada vez, as direções se mantêm, exceto o throughput agregado ao retirar a seed 5791.
- **Teleports (métrica auxiliar):** B2 teve 3 teleports, apenas em S4 seed 5791; C1 teve 0.

## 4. Decisões metodológicas registradas

- **S3:** a janela curta de 360 s foi considerada sensível demais (falso-fail de cerca de 22% por seed em tráfego estável e sem backlog). O S3 foi aprovado pelo **gate composto** (sem backlog estrutural, sem não inseridos relevantes, sem saturação de faixa, janela agregada de 1800 s estável, pelo menos 4 de 5 seeds válidas): 5/5 seeds válidas. A seed 4517 é `VALID_WITH_DIAGNOSTIC_WARNING`: a falha de 360 s (variação projetada de 6,51 veículos contra limite de 5,00) permanece como **diagnóstico** e não bloqueou a comparação.
- **S4:** aceito como `ALLOW_AND_MEASURE`. Os teleports do SUMO (padrão de 300 s) foram auditados: 17 eventos em 6 de 25 runs, nenhum no A5, impacto LOW nas métricas; são reportados como métrica auxiliar e a sensibilidade sem a dupla S4 seed 5791 foi incluída.

## 5. Limitações

- O Pilot V2 é um piloto; seus resultados não entram na campanha final e não foram combinados com o Pilot V1.
- Apenas 5 seeds por cenário; os intervalos de bootstrap são descritivos, não um teste de significância.
- A validação dos gates S1 a S4 foi feita nas runs de referência do B0; os controladores adaptativos podem alterar o regime realizado.
- Espera, time loss e tempo de viagem são condicionais à conclusão e dependem de offered, departed e arrived; isso pesa especialmente no S2 e no S4.
- O contrafactual sem teleport foi testado apenas com B0; o comportamento de B2 e C1 sem teleport é desconhecido.
- O S3 foi aprovado por um gate composto definido depois de observar os diagnósticos (janela de 1800 s escolhida a posteriori, limiares inalterados); a regra de 4 de 5 seeds é grosseira.
- O S4 (escala 2.0, topo da grade de calibração) deixa cerca de metade da demanda sem entrar.
- O throughput agregado é sensível à seed 5791.
- Um único ajuste de comunicação (atraso 0, perda 0); o custo de mensagens do C1 não foi analisado.
- O C1 não foi ajustado nem afinado com base nestes resultados.

## 6. Implicação científica

- O controlador cooperativo compacto mostra **potencial em saturação localizada** (S4), onde a coordenação reduziu atraso, fila e persistência de veículos em junções e aumentou o throughput em todas as seeds.
- Em regimes estáveis (S1) e de choque de demanda (S3) ele foi pior que o controlador local por pressão em todas as seeds, e no pico direcional (S2) trocou menor atraso por menor vazão. Portanto ele ainda **não apresenta robustez** para adoção geral sem refinamento.
- Um achado de piloto com 5 seeds serve para orientar o desenho da próxima campanha, não para generalizar.

## 7. O que o Pilot V2 permite afirmar e o que não permite

Permite afirmar:
- Em S4, nas condições do piloto, o C1 foi melhor que o B2 em todas as seeds e métricas principais.
- Em S1 e S3, o C1 foi pior que o B2 em todas as seeds nas métricas de atraso e fila.
- No S2 há trade-off entre atraso/fila e throughput/conclusão.
- O resultado global é misto e dependente do regime.

Não permite afirmar:
- Superioridade geral do C1.
- Que o benefício do S4 generaliza para outras saturações ou outras seeds.
- Significância estatística, nem ranking final de controladores.

## 8. Recomendações para os próximos experimentos

1. Não apresentar o C1 como superior em geral; reportar os resultados por cenário, com as populações (offered/departed/arrived).
2. Investigar por que o C1 perde no S1 e no S3 (por exemplo, a cooperação pode adicionar custo em regime não saturado) antes de qualquer afinação, e declarar qualquer ajuste dos controladores antes da campanha final.
3. Definir o número de seeds da campanha final a partir das larguras dos IC e da variabilidade entre seeds do piloto, com mais seeds para reduzir a sensibilidade observada no throughput agregado.
4. Reavaliar o gate de estabilidade do S3 e a escala do S4 (topo da grade, demanda sobrecarregada) com a mesma disciplina de critérios predeclarados e calibração só com B0.
5. Manter `sumo_teleports_total` como métrica auxiliar obrigatória e, se a política de teleports mudar, validar B1, B2, C1 e C2 (não só B0).
6. Reportar sempre espera, time loss e tempo de viagem junto com offered, departed, arrived e as razões de conclusão.
