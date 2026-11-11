> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/s3-stability-adjudication.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado abaixo (texto traduzido para português, sem alteração de números ou conclusões).

> **Atualização de status (auditoria final, Prompt 52).** Adjudicação histórica (Prompt 46.9), mantida sem alterações. A afirmação de que o S3 "continua NÃO" refere-se apenas à regra congelada de 360 s; a definição do gate foi alterada pela decisão aprovada (Prompt 47) e o S3 passa no gate composto em 5/5 (Prompt 48).

# Adjudicação da estabilidade pré-choque do S3 (Prompt 46.9, parte A)

Dados `campaign_role: PILOT` (Pilot V2) mais dados `CALIBRATION` / `CALIBRATION_DIAGNOSTIC` apenas com B0. Nenhum limiar relaxado, nenhum arquivo do repositório alterado, Pilot V2 não re-executado, nenhum controlador comparado.
Dados: `s3-stability-table.csv` (18 linhas), `artifacts/calibration/pilot_v2-diagnostic/` (`s3_analysis.json`, `s3_seed4517_b0_queue_final600s.csv/.png`).

## A1. Falha exata (S3, seed 4517, B0_FIXED)

- Regra congelada: reta OLS sobre a janela de fila; `projected_change = slope x window_length`; estável sse `projected_change <= 0.10 x max(mean_queue_window, 5.0)`.
- Janela: últimos 20% da medição pré-choque = passos 1740..2099 (360 amostras), choque no passo 2100.
- Observado: inclinação 0,01808 veíc/s, variação projetada **6,51 veíc**, média da janela 50,0, limiar **5,00** (0,10 x 50,0). Margem **-1,51 veíc** (inclinação normalizada 0,130 vs limite 0,100). FALHA.
- Fila na janela: média 50,0, mediana 50,0, mín 41, máx 60.
- Coorte pré-choque (programada 300..2100 s): ofertados 900, partiram 900, chegaram 900 ao fim da execução (86 deles ainda na rede no instante do choque = em trânsito normal), nunca inseridos 0, unfinished_in_network (fim da execução) 0, razão de partida 1,000, atraso de partida médio ~0 s, máx 1 s.
- Fila média pré-choque 46,9 (todo o intervalo 300..2100 s); a regra aplicada a todo o pré-choque de 1800 s é +0,031 normalizado (passa); aos últimos 720 s, +0,238 (falha).

## A2. S3 seed 4517 vs S1 seed 4517 (B0)

- A primeira metade do S3 tem demanda idêntica byte a byte à do S1 (mesmos veículos base, rotas, partidas). As séries de fila da rede do piloto para S3 e S1 são **idênticas nos passos 0..2099 (diferença absoluta máxima 0,0 veículos)**. A mesma janela, portanto, também FALHA no S1 seed 4517 (+0,130 normalizado); a própria janela dos últimos 20% do S1 (2940..3660 s) passa (-0,114 normalizado).
- Razão de partida 1,000, sem backlog de inserção (atraso máx de inserção 1 s), fração de saturação de lane 0,0000, fila máx de lane 9, chegadas em 300..2100 s 892: todos iguais nos dois casos.
- Portanto, a falha não é causada pelo S3 nem pelo choque. O mesmo tráfego estável falha ou passa dependendo de QUAL janela de 360 s é testada.

Classificação da seed 4517: **LOCAL_STOCHASTIC_FLUCTUATION** (com um componente de comprimento de janela; ver A3/A4).

## A3. Todas as cinco seeds do Pilot V2 (B0, S3, janela 1740..2099)

| seed | variação projetada | limiar | margem | normalizado | passa | fila média pré-choque | razão de partida | nunca inseridos | fila máx de lane | crescimento (últimos vs 360 s anteriores) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 2.41 | 4.64 | +2.23 | 0.052 | passa | 48.0 | 1.000 | 0 | 12 | -4.09 |
| 2027 | 0.94 | 4.57 | +3.63 | 0.021 | passa | 46.7 | 1.000 | 0 | 9 | -1.62 |
| 3253 | -4.43 | 4.47 | +8.90 | -0.099 | passa | 46.5 | 1.000 | 0 | 8 | -1.60 |
| 4517 | 6.51 | 5.00 | -1.51 | 0.130 | **FALHA** | 46.9 | 1.000 | 0 | 9 | +5.82 |
| 5791 | -2.11 | 4.78 | +6.89 | -0.044 | passa | 48.6 | 1.000 | 0 | 8 | +1.27 |

A 4517 está **próxima do limiar, não é um outlier claro**: as seeds seguintes são 0,052 (42) e -0,099/-0,044; as filas médias pré-choque são 46,5-48,6 e idênticas em regime entre as seeds. Nenhum backlog estrutural em nenhuma seed (razão de partida 1,000, nunca inseridos 0, saturação 0).

## A4. Evidência apenas de calibração (apenas B0, regra existente exatamente)

Execuções de calibração S3 existentes (seeds 101, 1009, 2029, choque 150; mesmo regime pré-choque para todo nível de choque): 3/3 passam (normalizados 0,050, -0,095, 0,024).
Novas execuções S3 `CALIBRATION_DIAGNOSTIC` (B0, níveis calibrados, seeds 3011, 4021, 5039, 6043, 7057, 8069, 9073, 10091, 11087, 12097): 7 passam / 3 falham (tabela abaixo).

| seed | inclinação normalizada | passa | projetado / limiar |
| --- | --- | --- | --- |
| 3011 | -0.036 | passa | -1.62 / 4.50 |
| 4021 | 0.110 | FALHA | 5.12 / 4.63 |
| 5039 | 0.083 | passa | 3.70 / 4.44 |
| 6043 | -0.112 | passa | -5.54 / 4.94 |
| 7057 | 0.149 | FALHA | 6.95 / 4.65 |
| 8069 | 0.025 | passa | 1.15 / 4.54 |
| 9073 | -0.065 | passa | -2.87 / 4.40 |
| 10091 | 0.253 | FALHA | 12.03 / 4.75 |
| 11087 | -0.125 | passa | -5.73 / 4.57 |
| 12097 | -0.038 | passa | -1.76 / 4.63 |

Todas as 10: razão de partida 1,000, nunca inseridos 0.

Agrupando as 18 observações pré-choque independentes do B0 (5 do piloto + 3 de calibração + 10 diagnósticas): **14 passam / 4 falham, taxa de aprovação 78%** (falhas: 4517, 4021, 7057, 10091). Inclinação normalizada nas 15 observações piloto+diagnósticas: média 0,020, dp 0,109; o limite 0,10 fica apenas 0,73 dp acima da média. Se as seeds falham independentemente em cerca de 22%, a chance de que todas as 5 seeds de um cenário estável passem é cerca de 0,78^5 = 29%.
Verificação por janela deslizante (janelas de 360 s, passo de 30 s, todas as posições pré-choque, B0): 105 de 735 janelas (14%) falham; nas execuções S1 B0 do piloto (300..3900 s), 93 de 545 janelas (17%) falham. Ou seja, a regra sinaliza tráfego genuinamente estável e sem backlog em aproximadamente uma janela a cada seis.
Comprimento da janela: com os mesmos dados, a regra sobre os últimos 720 s falha em 1/15 e sobre todo o pré-choque de 1800 s falha em 0/15 (máx normalizado 0,060); a janela de 360 s é curta frente ao ciclo semafórico de ~98 s e à oscilação de fila de +/-10 veíc.

## A5. Adjudicação

**S3_FAILURE_CLASS = STOCHASTIC_GATE_SENSITIVITY**

- Sem instabilidade estrutural: toda execução pré-choque tem razão de partida 1,000, 0 nunca inseridos, atraso de inserção <= 1 s, saturação de lane 0, fila pré-choque estacionária (tendência de 1800 s normalizada <= 0,06 em 15/15).
- A primeira metade do S3 é igual à do S1 exatamente (diferença da série 0,0), então o cenário não é a causa.
- O gate binário de inclinação de 360 s tem uma taxa de falsa falha medida de cerca de 22% por seed (4/18) e cerca de 14-17% por janela deslizante em tráfego estável.
- Parte da sensibilidade é o comprimento da janela (um componente ANALYSIS_WINDOW), mas a evidência dominante é a flutuação estocástica da fila frente a um limite apertado de 10%.

```
S3_FAILURE_CLASS = STOCHASTIC_GATE_SENSITIVITY
S3_REQUIRES_SCENARIO_CHANGE = NO
S3_REQUIRES_GATE_DEFINITION_CHANGE = YES
S3_REQUIRES_NEW_SIMULATION_RUNS = NO
```

- Mudança de cenário NÃO: a demanda é estável e idêntica à do S1.
- Mudança na definição do gate SIM: apenas se o responsável quiser que o S3 seja declarado válido; com a regra congelada inalterada, o S3 continua NÃO (um regime estável falharia em uma de cinco seeds cerca de 71% das vezes). Nada foi implementado; qualquer nova regra deve ser declarada antes da reavaliação e julgada nas 13 observações fora do piloto, não ajustada na seed 4517.
- Novas execuções NÃO: um gate revisado pode ser reavaliado a partir da telemetria existente do Pilot V2 e das execuções diagnósticas.
