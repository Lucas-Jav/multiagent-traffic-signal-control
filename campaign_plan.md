# Plano de Campanha V1

> **HISTÓRICO / SUBSTITUÍDO (plano pré-Pilot V2).** Este documento registra o plano de pré-voo e as
> verificações do mini-piloto. Não é autoritativo para a metodologia atual. Fontes atuais:
> `docs/methodology/campaign-matrix.md` (estrutura da campanha, seeds, S5), `docs/methodology/baselines.md`,
> `docs/methodology/metrics.md`, `docs/methodology/scenario-validity-gates.md`,
> `docs/experiments.md` (S5 canônico) e `docs/evidencias/pilot-v2/`. Resultado do Pilot V2: MISTO
> (confiança MÉDIA). A contagem final de seeds e o freeze final continuam pendentes; a calibração do B0 está CONCLUÍDA (B0_FIXED_CALIBRATED, ver docs/methodology/fixed-time-calibration.md); a config final ainda deve trocar o B0 por ele.

Status: preparado para revisão, não aprovado para execução da campanha completa.

Este documento congela a intenção de avaliação e as verificações operacionais da campanha V1
final. A campanha completa não deve ser executada até que haja aprovação explícita, após a
resolução dos itens bloqueantes do pré-voo.

## Objetivo

Avaliar controladores semafóricos sob as mesmas entradas de rede, rota, demanda,
razões de conversão, plano de fases, segurança, duração, warmup e passo de simulação
para cada par `scenario + seed`. Apenas o controlador muda dentro de um par comparável.

O mini-piloto deste plano é apenas uma verificação de pipeline. Seus artefatos não devem ser
usados como resultados científicos finais.

## Controladores

A campanha principal inclui:

- `B0_FIXED`
- `B1_LOCAL_ADAPTIVE`
- `B2_LOCAL_PRESSURE`
- `C1_COOPERATIVE_COMPACT`
- `C2_COOPERATIVE_EXPANDED`

Na campanha principal, `C1_COOPERATIVE_COMPACT` e
`C2_COOPERATIVE_EXPANDED` usam:

- `communication.delay_steps: 0`
- `communication.drop_probability: 0.0`
- `communication.rng_seed: null`
- `communication.max_message_age_steps: 1`

A degradação da comunicação permanece separada no S5.

## Cenários

A campanha principal inclui:

- `S1_BALANCED`: `scenarios/grid_3x3/scenario.yaml`
- `S2_DIRECTIONAL_PEAK`:
  `scenarios/grid_3x3/scenario_s2_directional_peak.yaml`
- `S3_DEMAND_SHIFT`: `scenarios/grid_3x3/scenario_s3_demand_shift.yaml`
- `S4_LOCAL_SATURATION`:
  `scenarios/grid_3x3/scenario_s4_local_saturation.yaml`

O `S5` permanece como uma campanha separada de robustez da comunicação.

## Seeds

Versão do pool de seeds: `campaign_v1_seed_pool_2026-09-29`.

Pool ordenado de seeds:

```text
42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001
```

Regras:

- O pool ordenado é fixado antes dos resultados da campanha final.
- As seeds não devem ser selecionadas, removidas ou reordenadas com base no desempenho dos
  controladores.
- O número final de seeds é `N_final`, escolhido após o piloto a partir do tempo de execução
  observado, da variabilidade aproximada e do orçamento de computação disponível.
- A campanha final aprovada deve usar as primeiras `N_final` seeds do pool.
- Execuções do piloto são excluídas dos resultados finais mesmo quando usam seeds deste
  pool; as execuções finais aprovadas devem ser re-executadas após o freeze final.

Contagem planejada de execuções principais:

```text
4 cenários * 5 controladores * N_final = 20 * N_final execuções
```

Teto do pool, se todas as seeds listadas forem aprovadas:

```text
4 cenários * 5 controladores * 10 seeds = 200 execuções
```

Mini-piloto executado:

```text
1 cenário * 5 controladores * 2 seeds = 10 execuções
```

## Razões de Conversão

As razões de conversão são entradas do cenário e permanecem fixas entre controladores. Desde o
Prompt 46.6 elas conduzem o gerador de rotas com seed (deixaram de ser apenas metadados) e todos
os cenários usam a distribuição do protocolo aprovado:

- `S1_BALANCED`, `S2_DIRECTIONAL_PEAK`, `S3_DEMAND_SHIFT`, `S4_LOCAL_SATURATION`: em frente
  `0.70`, esquerda `0.15`, direita `0.15` (as entradas de choque do S3 e de hotspot do S4
  substituem as razões por entrada; ver `docs/scenarios.md`)

O Pilot V1 (`pilot_v1`) rodou com as definições de cenário anteriores (razões declaradas como
`0.60/0.20/0.20` que não moldavam as rotas); é apenas um piloto de validação de infraestrutura.

As razões de conversão não devem ser alteradas entre controladores.

## Contrato de Equidade

Para todo `scenario + seed`, todos os controladores devem usar exatamente o mesmo:

- rede
- arquivo de rotas
- metadados de rota
- razão de conversão
- perfil de demanda, nível de demanda, cronograma de demanda e taxas de fluxo
- duração
- warmup
- passo de simulação
- plano de fases
- modelo de movimentos
- restrições de segurança
- topologia de comunicação

Apenas o `controller_id` muda entre as cinco execuções comparáveis.

A config executável da campanha final deve usar entradas `runs` explícitas, não a forma curta
`controllers + seeds`, para que cada `scenario + seed` possa apontar para seu próprio YAML de
cenário e arquivo de rotas específicos da seed.

## Arquivos Esperados

Plano e configuração:

- `campaign_plan.md`
- config da campanha final, a ser criada após aprovação:
  `experiments/configs/campaign_v1_main.yaml`
- configs de retomada opcionais:
  `experiments/configs/campaign_v1_resume_<batch>.yaml`

Material de cenário final preparado, a ser gerado após a aprovação de `N_final`:

- `scenarios/grid_3x3/campaign_v1/network.net.xml`
- `scenarios/grid_3x3/campaign_v1/metadata.json`
- `scenarios/grid_3x3/campaign_v1/viewsettings.xml`
- `scenarios/grid_3x3/campaign_v1/scenario_s<1-4>_seed_<seed>.yaml`
- `scenarios/grid_3x3/campaign_v1/routes_s<1-4>_seed_<seed>.rou.xml`
- `scenarios/grid_3x3/campaign_v1/routes_s<1-4>_seed_<seed>.metadata.json`

Artefatos congelados:

- `artifacts/experiments/campaign_v1_main/frozen/experiment.yaml`
- `artifacts/experiments/campaign_v1_main/frozen/checksums.json`
- `artifacts/experiments/campaign_v1_main/frozen/freeze_manifest.json`

Artefatos de execução:

- `artifacts/experiments/campaign_v1_main/manifest.json`
- `artifacts/experiments/campaign_v1_main/runs/<batch_id>/<run_id>/manifest.json`
- `artifacts/experiments/campaign_v1_main/runs/<batch_id>/<run_id>/intersection_trace.csv`
- `artifacts/experiments/campaign_v1_main/runs/<batch_id>/<run_id>/performance.json`

O código atual não produz `summary.json`, `results.parquet` nem
`config.snapshot.yaml` diretamente durante a simulação.

## Estimativa de Tempo de Execução

Base do mini-piloto:

- cenário: `S1_BALANCED`
- seeds: `42`, `2027`
- controladores: todos os cinco
- limite de passos: `600`
- passos de medição por execução: `300`
- execuções concluídas: `10`
- tempo de relógio somado das execuções, dos manifestos: cerca de `116 s`

Tempo de relógio médio observado para 600 passos:

| Controlador | Segundos médios | Estimativa para 3900 passos |
| --- | ---: | ---: |
| `B0_FIXED` | 0.846 | 5.5 s |
| `B1_LOCAL_ADAPTIVE` | 13.483 | 87.6 s |
| `B2_LOCAL_PRESSURE` | 13.745 | 89.3 s |
| `C1_COOPERATIVE_COMPACT` | 14.732 | 95.8 s |
| `C2_COOPERATIVE_EXPANDED` | 15.143 | 98.4 s |

Tempo de execução estimado por `scenario + seed` para os cinco controladores:

```text
cerca de 6,3 minutos para cenários de 3900 passos
```

Tempo de execução estimado por seed em S1-S4:

```text
cerca de 26 minutos localmente
```

A estimativa trata o S3 como ligeiramente mais longo porque sua duração total configurada
é maior que a de S1, S2 e S4. O tempo de execução em Docker não é estimado porque o Docker
Desktop não estava disponível durante o pré-voo.

## Estimativa de Disco

Uso de disco do mini-piloto:

```text
cerca de 70.994.982 bytes para 10 execuções de 600 passos
```

Estimativa linear conservadora:

```text
cerca de 44 MB por execução completa de 3900 passos
cerca de 0,9 GB por seed final em 20 execuções
cerca de 9 GB se todas as 10 entradas do pool de seeds forem aprovadas
```

O tamanho real pode diferir conforme o volume de telemetria e o comportamento do controlador.

## Resultados do Mini-Piloto

Config do mini-piloto:

```text
.tmp/campaign_v1_pilot/campaign_v1_mini_pilot.yaml
```

Manifesto do mini-piloto:

```text
artifacts/experiments/campaign_v1_mini_pilot/manifest.json
```

Freeze não final do mini-piloto:

```text
artifacts/experiments/campaign_v1_mini_pilot/frozen/checksums.json
```

Variabilidade aproximada de `vehicles_arrived` na janela medida de 300 passos,
usando apenas duas seeds:

| Controlador | Média de chegados | DP amostral | CV |
| --- | ---: | ---: | ---: |
| `B0_FIXED` | 106.5 | 0.707 | 0.0066 |
| `B1_LOCAL_ADAPTIVE` | 84.0 | 2.828 | 0.0337 |
| `B2_LOCAL_PRESSURE` | 85.0 | 2.828 | 0.0333 |
| `C1_COOPERATIVE_COMPACT` | 89.5 | 3.536 | 0.0395 |
| `C2_COOPERATIVE_EXPANDED` | 87.0 | 2.828 | 0.0325 |

Limites de interpretação:

- Esta é apenas uma verificação de pipeline e de variabilidade aproximada.
- Não é suficiente para ranquear controladores.
- Controladores não devem ser alterados apenas por causa da ordenação do piloto.
- Qualquer mudança de metodologia após este ponto deve ser documentada antes do freeze
  final.

## Tratamento de Falhas

Abortar antes de iniciar a campanha completa se qualquer gate de pré-voo obrigatório estiver vermelho.

Durante a execução aprovada:

- manter todo artefato de execução, inclusive de execuções falhas;
- não sobrescrever diretórios de execuções concluídas;
- não imputar métricas de execuções falhas como zero;
- registrar comando, código de saída, resumo de stderr/stdout, hash da config, hash do
  cenário, hash da rota e id do controlador para toda falha;
- investigar falhas de infraestrutura separadamente do comportamento do controlador;
- re-executar apenas as tuplas `scenario + seed + controller` que falharam, após verificar que
  os checksums congelados ainda correspondem;
- documentar todo lote de re-execução no manifesto da campanha ou em notas complementares.

## Comportamento de Retomada

O executor atual cria um novo diretório de lote com timestamp para cada execução
e não ignora automaticamente execuções concluídas.

Procedimento de retomada aprovado:

1. Ler `artifacts/experiments/campaign_v1_main/manifest.json` e os manifestos de execução
   dos lotes.
2. Identificar as tuplas `scenario + seed + controller` ausentes ou falhas.
3. Criar uma config de retomada explícita contendo apenas essas tuplas.
4. Executar a config de retomada contra as mesmas entradas congeladas.
5. Verificar os checksums e anexar o lote de retomada ao registro da campanha.

Não retomar alterando seeds, rotas, cenários, código de controlador ou restrições de
segurança.

## Registro de Pré-Voo

Executado localmente em 2026-09-29.

| Gate | Status | Evidência |
| --- | --- | --- |
| 1. Árvore de trabalho Git limpa | Passou antes de escrever este plano | `git status --short` estava vazio antes de `campaign_plan.md` ser adicionado. O freeze final ainda exige árvore limpa após revisão/commit. |
| 2. CI verde | Bloqueado | O equivalente local do CI não está verde porque `ruff format --check .` relata que 12 arquivos existentes seriam reformatados. |
| 3. SUMO 1.27.1 | Passou | `scripts/check_sumo.py` detectou `version=1.27.1`. |
| 4. Build do Docker verde | Bloqueado | `docker build --tag traffic-agents-campaign-v1-preflight .` falhou porque o daemon do Docker Desktop não estava disponível. |
| 5. Testes unitários verdes | Passou | `pytest -q -m "not sumo"` passou: `259 passed, 1 deselected`. |
| 6. Smoke de integração SUMO verde | Passou | `pytest -q -m sumo` passou: `1 passed, 259 deselected`. |
| 7. Smoke B0 | Passou | S1, seed 42, 120 passos. |
| 8. Smoke B1 | Passou | S1, seed 42, 120 passos. |
| 9. Smoke B2 | Passou | S1, seed 42, 120 passos. |
| 10. Smoke C1 | Passou | S1, seed 42, 120 passos, atraso/descarte zero. |
| 11. Smoke C2 | Passou | S1, seed 42, 120 passos, atraso/descarte zero. |
| 12. Rotas S1-S4 válidas | Passou | A validação do YAML de cenário passou para S1-S4; o smoke de rota SUMO do B0 passou para S1-S4. |
| 13. Testes de segurança de fase verdes | Passou | `tests/test_phase_safety.py`: `9 passed`. |
| 14. Hashes consistentes | Passou para o piloto | Dentro de cada seed do piloto, os cinco controladores compartilharam hashes idênticos de rede, rota, fases e conversões. A campanha final exige validação do checksum do freeze final. |
| 15. Config de freeze preparada | Passou parcialmente | O freeze não final do mini-piloto passou. O freeze final principal está pendente de `N_final`, disponibilidade do Docker, gate de formatação e árvore limpa. |

## Gate de Aprovação

A campanha não está aprovada para execução completa.

Antes da execução completa:

1. resolver ou dispensar explicitamente o bloqueio de `ruff format --check`;
2. iniciar o Docker Desktop e passar no build do Docker;
3. escolher `N_final` a partir do pool ordenado de seeds sem usar resultados de
   desempenho de controladores;
4. gerar os arquivos finais de cenário e rota específicos por seed;
5. criar `experiments/configs/campaign_v1_main.yaml`;
6. executar o pré-voo final novamente;
7. executar `traffic-agents experiment freeze --config experiments/configs/campaign_v1_main.yaml --final`
   em uma árvore Git limpa;
8. obter aprovação explícita para executar a campanha completa.
