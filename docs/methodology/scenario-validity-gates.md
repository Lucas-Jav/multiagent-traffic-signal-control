# Gates de Validade dos Cenários

Status: formaliza em documentação versionada os gates de validade dos cenários S1-S4 conforme
adjudicados no Pilot V2. As fontes primárias estão em `artifacts/experiments/pilot_v2/` (git-ignorado);
cópias versionadas e hashes estão em [`../evidencias/pilot-v2/`](../evidencias/pilot-v2/README.md).

Princípios:

- A validade de um cenário é avaliada nas runs de referência `B0_FIXED` (5 seeds do piloto). Os
  controladores adaptativos podem alterar o regime realizado; as tabelas por controlador do
  `pilot-assessment.md` acompanham os resultados como informação.
- Nenhum limiar numérico é alterado neste documento. Ele registra o que foi aprovado.
- A comparação B2 vs C1 só é permitida depois que S1, S2, S3 e S4 são válidos.

## Estado dos gates (Pilot V2)

| Gate | Estado | Base |
|---|---|---|
| Execução | 100 planejadas, 100 concluídas, 0 falhas | `manifest.json`, `run_status.jsonl` |
| Métricas finalizadas | SIM (nas 100 runs) | `pilot-assessment.md` |
| `S1_STABLE_REGIME_VALID` | VALID (5/5 seeds B0) | `pilot-assessment.md` |
| `S2_DIRECTIONAL_SCENARIO_VALID` | VALID (5/5 seeds B0) | `pilot-assessment.md` |
| `S3_ADAPTATION_SCENARIO_VALID` | VALID pelo **gate composto** (5/5 seeds válidas; mínimo 4/5) | seção abaixo |
| `S4_SATURATION_SCENARIO_VALID` | VALID, política `ALLOW_AND_MEASURE` | seção abaixo |
| `B0_MEASUREMENT_FAIR` | SIM | `pilot-assessment.md` |
| Decisão de seeds | PENDENTE | `campaign-matrix.md` |
| Congelamento final | NÃO executado | `campaign-matrix.md` |
| S5 packet loss | PLANEJADO, não executado | `experiments.md` |

O arquivo bruto `pilot_v2_gates.json` (Prompt 46.8) registra `S3_ADAPTATION_SCENARIO_VALID=false`,
`SCIENTIFIC_PILOT_VALID=false` e `READY_FOR_SEED_DECISION=false`. Esses valores **foram superados**
pela adjudicação posterior (gate composto do Prompt 48 e decisão de liberação do Prompt 49). O
arquivo bruto foi preservado sem alteração; ver
[`../evidencias/pilot-v2/pilot-v2-release-decision.md`](../evidencias/pilot-v2/pilot-v2-release-decision.md).

## Gate composto do S3 (regra aceita)

O S3 tem uma primeira metade semelhante ao S1 e um choque abrupto na borda oeste roteado por A5
(`shock_start_seconds = 2100`, 50% da janela de medição). A validade exige que o regime base
(pré-choque, passos 300..2099) seja estável e que o choque produza resposta visível.

**Critérios da fase pré-choque, avaliados no B0 em cada seed:**

1. **Sem backlog estrutural**: `departure_ratio` pré-choque >= 0,98 e atraso médio de inserção <= 5 s.
2. **Sem veículos nunca inseridos relevantes**: fração de nunca inseridos <= 0,02.
3. **Sem saturação estrutural de lane**: fração de lane-passos com fila >= 0,8 x capacidade da lane
   <= 0,02.
4. **Janela agregada de 1800 s pré-choque estável**: janela de 1800 s (passos 300..2099); mudança
   projetada por regressão linear (OLS) <= 0,10 x max(média da janela, 5 veículos).
5. **Regra de qualificação de seeds**: **pelo menos 4 de 5 seeds** válidas nos critérios 1-4.

**Verificações mantidas inalteradas em toda seed** (da tabela do Prompt 46.8, removida apenas a
verificação superada `pre_shock_stable` de 360 s): base == S1, primeira metade == S1, choque em
2100 s, origem na borda oeste, choque por A5, resposta visível (razão >= 1,25, latência <= 600 s),
sem backlog de inserção de vários milhares de segundos, AUC pela definição congelada.

**Apenas diagnóstico (não pode reprovar uma seed)**: a regra de 360 s (últimos 20% da medição
pré-choque) e a regra de 720 s.

### Resultado por seed (B0, Pilot V2)

| seed | classe | nunca inseridos | atraso máx. de inserção (s) | saturação de lane | janela 1800 s normalizada (limite 0,10) | diagnóstico 360 s |
|---|---|---|---|---|---|---|
| 42 | VALID | 0 | 1 | 0,00000 | 0,024 | passa (0,052) |
| 2027 | VALID | 0 | 1 | 0,00000 | -0,042 | passa (0,021) |
| 3253 | VALID | 0 | 1 | 0,00000 | -0,092 | passa (-0,099) |
| 4517 | **VALID_WITH_DIAGNOSTIC_WARNING** | 0 | 1 | 0,00000 | 0,031 | **FALHA** (0,130; projetado 6,51 veículos contra limite 5,00) |
| 5791 | VALID | 0 | 1 | 0,00000 | -0,085 | passa (-0,044) |

Resultado agregado: 5/5 seeds válidas (mínimo exigido 4/5). **O S3 passa pelo gate composto.**

### Aviso diagnóstico da seed 4517

A seed 4517 falha no diagnóstico de 360 s (e no de 720 s, normalizado 0,238). Isso **é reportado, não
escondido**, e não é removido de `s3-stability-table.csv`. Sob o gate composto a seed é
`VALID_WITH_DIAGNOSTIC_WARNING`: `departure_ratio` 1,000, 0 nunca inseridos, atraso de inserção
máximo 1 s, saturação de lane 0,00000 e janela de 1800 s estável. A primeira metade do S3 é idêntica
à do S1 nessa seed, de modo que a falha de 360 s reflete flutuação de fila e não o cenário. Como a
regra tolera uma seed em cinco, o resultado agregado seria o mesmo mesmo se a 4517 fosse classificada
como inválida.

### Justificativa

A regra de 360 s tinha taxa de falso reprovado de cerca de 22% por seed em tráfego B0 estável e sem
backlog (4 de 18 observações independentes) e de 14-17% por janela deslizante (auditoria 46.9). O
gate composto testa as propriedades que definem um regime base estável (sem backlog, sem não inserção,
sem saturação e sem tendência em 1800 s) sobre toda a fase pré-choque. **Nenhum limiar numérico foi
alterado**: apenas a janela decisiva da regra de inclinação passou de 360 s para 1800 s.

### Limitação metodológica (obrigatória em qualquer relatório)

> **A regra composta de validade do S3 foi formalizada após a inspeção diagnóstica do comportamento do
> Pilot V2 e, portanto, deve ser reportada como um refinamento metodológico post-hoc.**

Pontos adicionais:

- A janela de 1800 s foi escolhida depois de observar os dados da auditoria 46.9. O limiar `0,10` e o
  piso de 5 veículos permaneceram inalterados.
- A regra de 4 de 5 seeds é grosseira para 5 seeds.
- O S3 foi validado no B0; o regime realizado pelos controladores adaptativos pode diferir.
- O script `analysis/pilot_v2_analysis.py` ainda aplica o critério antigo de 360 s e **não** deve ser
  usado para reavaliar o S3; a avaliação válida usa `analysis/s3_composite_gate.py`.

## S1, S2 e S4

- **S1 (`S1_STABLE_REGIME_VALID`)**: regime estável sem backlog (razão de inserção ~1,0, projeção da
  fila dos últimos 20% da medição dentro do limite normalizado, razões de conversão ~0,70/0,15/0,15,
  participação mínima de junção ~0,105). Calibrado por varredura B0 predeclarada
  (`scripts/calibrate_scenarios.py`, demanda S1 150 veículos/h por entrada).
- **S2 (`S2_DIRECTIONAL_SCENARIO_VALID`)**: demanda direcional dominante do oeste (80%), sem
  starvation de inserção por entrada (`min_entry_departure_ratio`). Nível calibrado 320.
- **S4 (`S4_SATURATION_SCENARIO_VALID`)**: saturação concentrada em A5 (hotspot roteado por A5),
  escala de demanda 2,0 (topo da grade de calibração). Sobrecarga intencional: `departure_ratio` de
  0,33 a 0,49 entre as runs.
- **Política de teleports do S4 = `ALLOW_AND_MEASURE`**: teleports do SUMO não bloqueiam a validade do
  S4. `sumo_teleports_total` é métrica auxiliar obrigatória em todo relatório do S4 (Pilot V2: 17
  teleports em 6 das 25 runs do S4: B0 14, B2 3 na seed 5791, B1/C1/C2 0; nenhum em S1, S2 ou S3). Os
  teleportados permanecem no `tripinfo.xml`. O contrafactual sem teleport foi validado apenas com
  B0. A análise B2 vs C1 do S4 deve incluir a sensibilidade sem a dupla seed 5791.

Os critérios numéricos completos de S1, S2 e S4 estão no `analyze_run` de
`scripts/calibrate_scenarios.py` e nas tabelas do `pilot-assessment.md`.

## Ressalvas gerais

1. Métricas condicionais à conclusão (espera, perda de tempo, tempo de viagem, paradas) só valem lidas
   junto com ofertados, inseridos, concluídos e razões de conclusão.
2. Amostra pequena: 5 seeds, intervalos de confiança pareados largos e descritivos.
3. O Pilot V2 é piloto; seus resultados não entram na campanha final.
