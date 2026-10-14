# Pacote de Evidências do Pilot V2 (versionado)

`campaign_role: PILOT`. Este diretório é um pacote **leve** das evidências científicas do Pilot V2,
cujas fontes primárias estão em `artifacts/experiments/pilot_v2/` (git-ignorado). Traces brutos por
run (parquet de telemetria, `tripinfo.xml`) **não** são copiados. Resultados do piloto **não** entram
na campanha final.

- Experimento: `pilot_v2` (batch `20260930T005429_589536Z_d05ca74f`)
- Execução: 100 runs planejadas, 100 concluídas, 0 falhas
- Seeds do piloto: `42, 2027, 3253, 4517, 5791`
- Controladores: `B0_FIXED`, `B1_LOCAL_ADAPTIVE`, `B2_LOCAL_PRESSURE`, `C1_COOPERATIVE_COMPACT`,
  `C2_COOPERATIVE_EXPANDED`; cenários `S1_BALANCED`, `S2_DIRECTIONAL_PEAK`, `S3_DEMAND_SHIFT`,
  `S4_LOCAL_SATURATION`
- Git SHA do código que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` (campo `git_sha` dos
  manifests das runs)
- Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad`
- Hash da rede em todas as runs = hash atual de `scenarios/grid_3x3/network.net.xml`
  (`network_unchanged_since_runs = true` em `evidence-manifest.json`)

## Resultado (resumo; ver `b2-vs-c1-final-comparison.md`)

```text
RESULT_INTERPRETATION        = MIXED
RESULT_CONFIDENCE            = MEDIUM
C1_GENERAL_SUPERIORITY_CLAIMED = NO
C1_SCENARIO_SPECIFIC_BENEFIT = S4
```

S1 favorece B2 sobre C1; S2 é um trade-off; S3 favorece B2 sobre C1; S4 favorece C1 sobre B2
(política `ALLOW_AND_MEASURE` para teleports). Detalhes e ressalvas nos documentos copiados.

## Gate bruto superado

`pilot_v2_gates.json` foi **preservado sem alteração**. Ele reflete a avaliação do Prompt 46.8:

```text
S3_ADAPTATION_SCENARIO_VALID = false
SCIENTIFIC_PILOT_VALID       = false
READY_FOR_SEED_DECISION      = false
```

Esses valores foram **superados** pela adjudicação metodológica posterior: o gate composto do S3
(`s3-composite-gate-reevaluation.md`, Prompt 48) e a decisão de liberação
(`pilot-v2-release-decision.md`, Prompt 49) estabeleceram S1, S2, S3 e S4 como válidos e
`PILOT_V2_RELEASED_FOR_B2_VS_C1 = YES`. O gate composto é um refinamento **post-hoc**; ver
[`../../methodology/scenario-validity-gates.md`](../../methodology/scenario-validity-gates.md).
Os scripts de análise (`analysis/s3_composite_gate.py`, `analysis/b2_vs_c1.py`) **não** foram copiados (permanecem em `artifacts/experiments/pilot_v2/analysis/`). Não use `pilot_v2_analysis.py` (critério antigo de 360 s) para reavaliar o S3.

## Arquivos

Todos os detalhes (caminho de origem, SHA-256 da fonte, experimento, Git SHA, data, tipo
raw/derived, tamanho) estão em `evidence-manifest.json`. Os `.md` copiados começam com um cabeçalho de
proveniência; os demais arquivos são cópias byte a byte e usam o manifest.

| Arquivo | Tipo | Papel |
|---|---|---|
| `pilot-v2-release-decision.md` | derived | Decisão de liberação (supera os gates brutos) |
| `pilot-v2-methodological-decision.md` | derived | Decisão metodológica do S3; política do S4 |
| `s3-composite-gate-reevaluation.md`, `s3-composite-gate-table.csv` | derived | Gate composto do S3 |
| `s3-stability-adjudication.md`, `s3-stability-table.csv` | derived | Estabilidade do S3 (histórico, inclui diagnóstico 360 s) |
| `s4-teleport-audit.md`, `s4-teleport-table.csv` | derived | Auditoria de teleports do S4 |
| `pilot-assessment.md` | derived | Avaliação original (46.8); status do S3 superado |
| `pilot_v2_gates.json` | derived | Saída bruta dos gates do 46.8 (SUPERADA, preservada) |
| `b2-vs-c1-final-comparison.md`, `b2-vs-c1-final-comparison-table.csv`, `b2-vs-c1-seed-sensitivity.csv` | derived | Comparação pareada primária |
| `final-scientific-conclusion.md`, `final-audit.md` | derived | Conclusão e auditoria finais |
| `combined_metrics.parquet` | raw | Métricas agregadas das 100 runs (pipeline canônico) |
| `run-identity-summary.csv` | derived | Identidade das 100 runs (a partir de `manifest.json`) |
| `run-hash-summary.csv` | derived | Hashes de rede/rota/plano de fases por run |
| `evidence-manifest.json` | derived | Proveniência e SHA-256 de cada arquivo |

## Observação de linguagem

Nos documentos copiados, "variação projetada" refere-se à extrapolação por regressão linear da fila
dentro da janela de validação de um cenário (critério estatístico de estabilidade), **não** a
previsão feita por um controlador. Os controladores são **reativos** (ver
[`../../methodology/tcc-scope-alignment.md`](../../methodology/tcc-scope-alignment.md)). O texto
original não foi editado, para preservar a evidência.
