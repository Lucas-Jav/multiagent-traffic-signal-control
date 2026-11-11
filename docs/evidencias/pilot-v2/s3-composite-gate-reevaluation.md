> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/s3-composite-gate-reevaluation.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado abaixo (texto traduzido para português, sem alteração de números ou conclusões).

# Reavaliação do gate composto do S3 (Prompt 48)

`campaign_role: PILOT` (Pilot V2). Apenas telemetria existente: nenhuma simulação, nenhum arquivo do repositório alterado, nenhum limiar alterado, nenhuma comparação B2-vs-C1.
Gate definido em `pilot-v2-methodological-decision.md` (Prompt 47). Avaliado nas execuções S3 do `B0_FIXED` (5 seeds do piloto), fase pré-choque (programada 300..2100 s; passos 300..2099). Script: `analysis/s3_composite_gate.py`; dados por seed: `s3-composite-gate-table.csv`.

## Gate

1. Sem backlog estrutural: `departure_ratio` pré-choque >= 0,98 e atraso médio de inserção <= 5 s.
2. Sem veículos nunca inseridos relevantes: fração <= 0,02.
3. Sem saturação estrutural de lane: fração de lane-passos com fila >= 0,8 x capacidade da lane <= 0,02.
4. A janela agregada pré-choque de 1800 s (passos 300..2099) passa na regra congelada: variação OLS projetada <= 0,10 x max(média da janela, 5).
5. Pelo menos 4 de 5 seeds válidas nos critérios 1-4.
Mantidas sem alteração em toda seed (tomadas da tabela S3 do Prompt 46.8, removendo apenas a verificação `pre_shock_stable` de 360 s substituída): base == S1, primeira metade == S1, choque em 2100 s, origem na borda oeste, choque via A5, resposta visível (razão >= 1,25, latência <= 600 s), sem backlog de inserção de vários milhares de segundos, AUC de definição congelada.
Apenas diagnósticas (não podem reprovar uma seed): a regra de 360 s (últimos 20% da medição pré-choque) e a regra de 720 s.

## Resultado por seed

| seed | classe | ofertados | partiram | nunca inseridos | atraso máx de inserção (s) | saturação de lane | 1800 s normalizado (limite 0,10) | margem 1800 s (veíc) | verificações mantidas que falharam | diagnóstico de 360 s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | **VALID** | 900 | 900 | 0 (0.0000) | 1 | 0.00000 | 0.024 | 3.67 | - | passa (0.052, margem 2.23) |
| 2027 | **VALID** | 900 | 900 | 0 (0.0000) | 1 | 0.00000 | -0.042 | 6.64 | - | passa (0.021, margem 3.63) |
| 3253 | **VALID** | 900 | 900 | 0 (0.0000) | 1 | 0.00000 | -0.092 | 8.95 | - | passa (-0.099, margem 8.89) |
| 4517 | **VALID_WITH_DIAGNOSTIC_WARNING** | 900 | 900 | 0 (0.0000) | 1 | 0.00000 | 0.031 | 3.22 | - | FALHA (0.130, margem -1.51) |
| 5791 | **VALID** | 900 | 900 | 0 (0.0000) | 1 | 0.00000 | -0.085 | 8.97 | - | passa (-0.044, margem 6.89) |

Flags dos critérios por seed (1 backlog, 2 nunca inseridos, 3 saturação, 4 janela de 1800 s): 42: 1111; 2027: 1111; 3253: 1111; 4517: 1111; 5791: 1111 (1 = passa).

## Agregado

- Seeds válidas (VALID ou VALID_WITH_DIAGNOSTIC_WARNING): **5/5**; a regra exige >= 4/5.
- Classes: 42 VALID, 2027 VALID, 3253 VALID, 4517 VALID_WITH_DIAGNOSTIC_WARNING, 5791 VALID.
- **O S3 PASSA no gate composto.**

## Efeito da seed 4517

- O diagnóstico de 360 s ainda FALHA para a seed 4517 (variação projetada 6,51 veíc vs limiar 5,00, margem -1,51, normalizado 0,130 vs 0,100). Esta falha é reportada aqui, não escondida, e não é removida de `s3-stability-table.csv` nem da avaliação do Pilot V2.
- No gate composto, a seed 4517 é **VALID_WITH_DIAGNOSTIC_WARNING**: razão de partida 1,000, 0 nunca inseridos, atraso máx de inserção 1 s, saturação de lane 0,00000, e a janela de 1800 s é estável (normalizado 0,031, margem 3,22 veíc).
- Seeds com aviso diagnóstico: [4517]. O diagnóstico de 720 s para a 4517 é FALHA (normalizado 0,238).
- Como a regra agregada tolera uma seed em cinco, o resultado seria o mesmo mesmo que a seed 4517 fosse classificada INVALID, desde que as outras quatro sejam válidas: sim, as outras quatro seeds são válidas.

## Justificativa metodológica

- A regra de 360 s tinha uma taxa de falsa falha medida de cerca de 22% por seed em tráfego B0 estável e sem backlog (4 de 18 observações independentes) e cerca de 14-17% por janela deslizante (Prompt 46.9); a primeira metade do S3 é idêntica à do S1 para a seed 4517, então a falha reflete flutuação de fila, não o cenário.
- O gate composto testa as propriedades que definem um regime base estável (sem backlog, sem não inserção, sem saturação, sem tendência de 1800 s) em toda a fase pré-choque. Nenhum limiar mudou; apenas a janela decisiva da regra de inclinação passou de 360 s para 1800 s, conforme aprovado no Prompt 47.
- Limitação herdada do Prompt 47: a janela de 1800 s foi escolhida após observar os diagnósticos do 46.9; a regra inclui o limite original de 0,10 e o piso de 5 veíc. Com 5 seeds, 4 de 5 é grosseiro.

## Conclusão

O S3 passa no gate composto. Os gates de validade de cenário S1, S2, S3 e S4 estão então todos satisfeitos, portanto o bloqueio do S3 sobre a comparação B2 vs C1 é suspenso. A comparação NÃO foi calculada nesta tarefa.
