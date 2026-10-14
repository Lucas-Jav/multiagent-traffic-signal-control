# Congelamento da campanha científica final

Especificação imutável da campanha final do TCC (Prompt 59). Nenhuma simulação foi executada para
produzi-la. Manifesto: `artifacts/final-freeze/final-freeze-manifest.json` (local, ignorado pelo
Git) e a cópia versionada `docs/evidencias/final-freeze/final-freeze-manifest.json`.

Verificação a qualquer momento (recalcula todos os hashes e a matriz, sem simular):

```
python scripts/build_final_freeze.py --verify
```

## Identidade do congelamento

- **Duas identidades distintas.**
  - `SCIENTIFIC_SOURCE_GIT_SHA`: commit que contém o código científico e todas as entradas finais.
    **Não é constante no código**: só existe depois do commit, então é informado a
    `scripts/build_final_freeze.py --scientific-source-sha <SHA>` e validado (existe, é ancestral
    de `HEAD` — `HEAD` incluso —, árvore científica igual à atual, árvore limpa). O manifesto grava
    o SHA validado (resolvido para 40 hex). O commit `0abd7be…` das rodadas anteriores está
    **superado** e não tem papel algum na ferramenta.
  - `FREEZE_TOOLING_GIT_SHA`: commit posterior, que contém só ferramentas de hash/freeze, testes e
    evidência do freeze. O gerador **não exige `HEAD == SCIENTIFIC_SOURCE_GIT_SHA`**; exige árvore
    limpa, o commit científico ser ancestral de `HEAD`, nenhuma entrada científica alterada desde
    ele e o `SCIENTIFIC_TREE_SHA256` igual ao do commit científico.
- **Hash canônico (`CANONICAL_TEXT_LF_V1`)** para arquivos de texto: decodifica UTF-8 (descarta
  BOM), converte CRLF e CR isolado em LF, recodifica e aplica SHA-256. Nada além de fim de linha
  e BOM é normalizado (espaços, indentação, linha final e conteúdo contam). O hash canônico é a
  autoridade entre sistemas; o `raw_byte_sha256` é mantido como evidência forense/local (depende do
  `core.autocrlf`). Arquivos fora da lista de texto (`.py .yaml .yml .json .xml .toml .lock .csv
  .md .txt`, incluindo `.net.xml`, `.rou.xml`, `.metadata.json`) usam só o hash bruto. Não há
  `.gitattributes`.
- **Hash semântico (`SCIENTIFIC_METADATA_V1`)** só para `routes_*.metadata.json`: JSON sem a chave
  de topo `generated_at` (única exclusão), `sort_keys`, separadores compactos, SHA-256. Seed,
  demanda, rotas, conversões, contagens, choque etc. continuam na identidade. Os arquivos completos
  seguem com hashes bruto e canônico.
- **`SCIENTIFIC_TREE_SHA256` (`SCIENTIFIC_TREE_V1`)**: SHA-256 da concatenação UTF-8 de
  `<caminho>\t<modo>\t<hash autoritativo>\n`, ordenada por caminho POSIX. Inclui
  `src/traffic_agents/**/*.py` e `analysis/**/*.py`, as duas configs finais, o plano B0, a rede
  (+ `metadata.json`, `scenario.yaml`), os 40 cenários e arquivos de rota finais (canônico), os 40
  metadados de rota (semântico), os geradores de cenário/rota, `pyproject.toml` e `uv.lock`.
  Exclui o pacote `replay`, as ferramentas de freeze (`final_freeze.py`, `freeze_hashing.py`),
  testes, docs, evidência, `artifacts/` e arquivos de GUI. Um teste confirma que nenhum módulo
  científico importa replay nem as ferramentas de freeze. A lista completa com os hashes fica em
  `docs/evidencias/final-freeze/scientific-tree.csv`.
- O manifesto (schema 2) registra `git_working_tree_dirty_at_input_inspection` (estado da árvore
  enquanto as entradas foram inspecionadas; evidência escrita depois não o altera). Nunca embute o
  próprio hash: `FREEZE_MANIFEST_SHA256` sai no CLI e em `final-freeze-manifest.sha256`.
- O manifesto de `docs/evidencias/final-freeze/` é o **único** manifesto corrente (schema 2). O
  manifesto anterior (schema 1, árvore suja, hashes brutos, fonte `b98b440`) foi **substituído** pela
  geração definitiva abaixo; o histórico git o preserva.
- Ambiente: Python 3.12.14, SUMO 1.27.1, traci/sumolib 1.27.1, `uv.lock` sha256
  `46f15418…ee02c`. O CI fixa uv 0.12.5 (validado: `uv lock --check` e `uv sync --frozen`).

## Seeds (N = 10)

`42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001`

As cinco primeiras são as seeds do Pilot V2; as cinco seguintes são o pool de extensão
pré-declarado em `campaign-matrix.md` (`campaign_v1_seed_pool_2026-09-29`). Nenhuma seed foi
escolhida pelo desempenho de controladores.

**Por que N = 10:** o Pilot V2 (N = 5) terminou com resultado misto (MIXED, confiança MEDIUM) e ICs bootstrap
pareados largos para separar efeitos pequenos. N = 10 dobra os pares por cenário sem
inflar o custo da campanha (290 runs) e usa apenas seeds já reservadas antes do piloto.
Os artefatos de cenário/rota das 5 seeds novas foram gerados com o mesmo gerador congelado
(`scripts/generate_scenarios.py`), sem tocar nos arquivos das seeds anteriores; regerar as seeds
42 e 2027 reproduz byte a byte os cenários e rotas versionados (só o campo `generated_at` dos
metadados muda).

## Controladores

Finais: `B0_FIXED_CALIBRATED`, `B1_LOCAL_ADAPTIVE`, `B2_LOCAL_PRESSURE`,
`C1_COOPERATIVE_COMPACT`, `C2_COOPERATIVE_EXPANDED`.
Somente históricos (nunca como baseline final): `B0_FIXED`, `B0_FIXED_STATIC`,
`B0_FIXED_STATIC_V2`.

**Por que o B0 calibrado substitui o B0 histórico:** o `B0_FIXED` mantém o plano estático de 98 s do `tlLogic` da
rede, sem calibração; comparar controladores adaptativos contra um baseline fraco infla ganhos. O
`B0_FIXED_CALIBRATED` é um plano de tempo fixo calibrado e validado em seeds dedicadas
(calibração 101/1009/2029, validação 3011/4021/5003), sem usar seeds finais.

### Identidade do B0 final

| Campo | Valor |
|---|---|
| `controller_id` | `B0_FIXED_CALIBRATED` |
| `plan_id` | `fx_c84_demand_proportional_alternate` |
| ciclo / amarelo / vermelho total | 84 s / 3 s / 2 s |
| estratégia de divisão / de offset | `DEMAND_PROPORTIONAL` / `ALTERNATE` |
| offsets | 0 s / 42 s |
| SHA-256 de `experiments/fixed_time/b0_fixed_calibrated.json` | `a950d82d1d59562766b183c096477f39215f0de8a905960b223a7a6fcef1f0fe` |

Não recalibrar. O hash do arquivo coincide com a evidência de calibração.

## Matriz principal (`final_main`, 200 runs)

4 cenários (`S1_BALANCED`, `S2_DIRECTIONAL_PEAK`, `S3_DEMAND_SHIFT`, `S4_LOCAL_SATURATION`) ×
5 controladores × 10 seeds. `experiments/configs/final_main.yaml`, `campaign_role:
FINAL_SCIENTIFIC`, id estável `final_main` (sem timestamp). O arquivo é **gerado** por
`scripts/build_final_freeze.py` a partir de `traffic_agents.experiments.final_freeze`; edição
manual é detectada pela validação.

## S5 (`final_s5_packet_loss`, 90 runs)

Tráfego base `S2_DIRECTIONAL_PEAK` (S5 é um experimento de comunicação, não um novo padrão de
demanda), atraso 0, perda 0 / 0,20 / 0,50 / 1,00.

- C1: 4 níveis × 10 seeds = 40; C2: 4 × 10 = 40.
- B2 **não usa comunicação**: **uma** referência por seed = 10 (não 40).
- Total S5 = 90. Total final = 200 + 90 = **290**.

Ficam fora dos 290: Pilot V2, calibração, validação da calibração, runs pré-finais da rota de
referência, smokes e replay visual.

## Rota de referência oficial

`left1A1 → A1B1 → B1C1 → C1right1` (entrada oeste, A4, A5, A6, saída leste). Coorte = veículos
oferecidos cuja **sequência de arestas planejada** é exatamente essa e cujo depart programado está
na janela de medição; nunca se usa o id de rota do SUMO. Métricas e interpretação em
`reference-route.md`; análise final compara `B0_FIXED_CALIBRATED`, `B2_LOCAL_PRESSURE` e
`C1_COOPERATIVE_COMPACT`. Congelada com hash em `reference_route.definition_sha256`.

## Terminologia

Nomes acadêmicos `A1`–`A9`; os ids do SUMO (`A0`..`C2`) são só identificadores de implementação.
Glossário versionado: `intersection-glossary.md` (A5 lógico = B1 no SUMO).

## Cenários

- **S1, S2, S3, S4:** demanda, geração de rotas, aquecimento (300 s), duração da medição (3600 s) e
  critérios de validade congelados (hashes por cenário × seed em
  `docs/evidencias/final-freeze/scenario-inputs.csv`; critérios em `scenario-validity-gates.md`).
- **S2:** demanda dominante oeste-leste. É a base de tráfego do S5.
- **S3:** choque em `shock_start_seconds = 2100` (50 % da janela de medição); métrica
  `post_shock_queue_auc_vehicle_seconds`. **Limitação:** o gate composto revisado do S3 foi
  formalizado após a inspeção diagnóstica do Pilot V2 e é, portanto, um refinamento metodológico
  *post-hoc*. Nenhuma outra mudança no gate S3 após o congelamento.
- **S4:** saturação localizada em A5. `SUMO_TELEPORT_POLICY = ALLOW_AND_MEASURE`:
  `sumo_teleports_total` é sempre preservado e um teleport não invalida a run automaticamente.

## Métricas canônicas

Definições, denominadores e semântica congelados em
`traffic_agents.experiments.metric_definitions` (hash `canonical_metrics.definitions_sha256`) mais as
métricas da rota de referência. Antes do congelamento foi adicionada a entrada de registro de
`sumo_teleports_total` (já medida e persistida; apenas a definição canônica faltava).
Nenhuma fórmula pode mudar.

**Regra condicional:** `mean_waiting_time`, `mean_time_loss` e `mean_travel_time` são condicionais a
viagens concluídas e devem sempre ser lidas junto com `departure_ratio`,
`completion_ratio_offered`, `never_inserted_vehicle_count` e `unfinished_in_network_count`
(especialmente em S2 e S4).

## Comparações e plano estatístico

- **Primária:** `B2_LOCAL_PRESSURE` vs `C1_COOPERATIVE_COMPACT`. B2 e C1 compartilham a família de
  controle por pressão local e o C1 apenas acrescenta informação compacta dos vizinhos; é a
  comparação mais limpa para isolar o efeito da cooperação.
- **Secundárias:** B0 calibrado vs B2 (efeito da adaptação por pressão local sobre o tempo fixo
  calibrado); B0 calibrado vs B1 (adaptação local simples); C1 vs C2 (efeito/custo de comunicação
  mais rica).
- Unidade pareada: cenário + seed. Reportar N, média, mediana, desvio-padrão, IQR; diferença média
  e mediana pareadas (tratamento − baseline), diferença relativa e IC 95 % por bootstrap percentil
  pareado, 10 000 reamostragens.
- Sementes do bootstrap (determinísticas): análise geral `20260910`
  (`analysis/statistics.py`); rota de referência base `20260930` com semente estável por rótulo.
- `analysis/statistics.py::DEFAULT_CONTROLLER_PAIRS` foi alinhado ao congelamento (antes apontava
  para `B0_FIXED`). Nenhum método inferencial novo após ver resultados.
- O alias histórico `B0 → B0_FIXED` de `CONTROLLER_ALIASES` permanece; a análise final deve usar
  sempre o id completo `B0_FIXED_CALIBRATED`.

## Hashes científicos

Rede, configs de cenário, arquivos e config de geração de rotas, conversões, movimentos, topologia de
fases, configuração de cada controlador, plano B0, topologia de comunicação, definições de
métricas, lista de seeds, rota de referência, configs principal e S5, plano estatístico e a matriz
de runs estão no manifesto. A justiça entre controladores usa o hash neutro ao controlador
(`scenario_neutral_sha256`), nunca o `scenario_sha256` (que inclui `controller_id`).
Tabelas: `run-matrix.csv` (290 linhas) e `scenario-inputs.csv` (40 linhas).

## Replay

O sistema de replay sincronizado existe nesta implementação (`replay.replay_source_sha256` no
manifesto). Demonstrações visuais futuras devem referenciar esta versão; são evidência ilustrativa
e **não** fazem parte das 290 runs.

## Política de mudança

Após o congelamento não podem mudar: controladores, parâmetros, plano B0, demanda, rotas, seeds,
topologia de fases, níveis de perda, aquecimento, duração da medição, instante do choque,
definições de métricas, rota de referência e plano estatístico.

Se um defeito de correção for descoberto: (1) parar a campanha; (2) documentar o defeito;
(3) corrigir; (4) commitar; (5) criar um **novo** congelamento; (6) reexecutar a evidência afetada.

## Antes da campanha (Prompt 60)

Na árvore commitada rodar `python scripts/build_final_freeze.py --verify --scientific-source-sha
176178e36eeafb329a5a1350161be61cf97902b0`. Os freezes de experimento (schema 3) já foram gerados em
`artifacts/experiments/final_main/frozen` e `.../final_s5_packet_loss/frozen` (locais, ignorados
pelo Git): se ausentes, regerar com `traffic-agents experiment freeze --config <cfg> --final`
(árvore limpa e id novo) antes de `experiment run`.

## Validação de rotas independente de fim de linha (Prompt 59.1C)

`validate_route_artifacts` comparava o hash **bruto** de `network.net.xml` e `routes_*.rou.xml` com
os metadados; um checkout LF vs CRLF reprovava artefatos cientificamente idênticos. Agora (só
aceitação/rejeição; nenhum dado, rota, comando SUMO, controlador ou métrica muda):

1. metadado com `route_canonical_sha256` / `network_canonical_sha256` (`CANONICAL_TEXT_LF_V1`):
   vale o hash canônico;
2. senão, hash bruto histórico (`route_hash`/`network_hash`): igualdade aceita como antes;
3. se o bruto diverge, aceita **só** se o hash bruto registrado for uma identidade legada conhecida
   (`legacy_artifact_hashes.py`, derivada dos blobs commitados por
   `scripts/build_legacy_route_hash_table.py`) e o hash canônico do arquivo for o valor confiável
   dessa entrada. Hash desconhecido ou conteúdo alterado é rejeitado.

Os metadados históricos (Pilot V2 etc.) não foram reescritos. O gerador passou a gravar, além dos
campos antigos, `route_raw_sha256`, `route_canonical_sha256`, `network_raw_sha256` e
`network_canonical_sha256`. A implementação do hash canônico fica em `text_hashing.py` (uma só),
reexportada por `freeze_hashing.py`.

Como `route_artifacts.py` é código de execução, o `SCIENTIFIC_TREE_SHA256` mudou e o commit
`0abd7be…` deixou de ser a fonte científica (superado). O novo commit científico é informado por
`--scientific-source-sha`; nenhum SHA é fixado no código.

## Freeze de experimento independente de fim de linha (Prompt 59.1D)

`traffic-agents experiment freeze` (`freeze.py`) também comparava hashes brutos. Agora o
`checksums.json` é schema 2: cada arquivo de texto registra `sha256`/`raw_byte_sha256` (forense,
chave legada mantida), `canonical_sha256` e `hash_schema = CANONICAL_TEXT_LF_V1`; binários só o
hash bruto. Verificação: com `canonical_sha256` registrado, vale o canônico; registro legado
(schema 1, só `sha256`): hash bruto igual é aceito como antes, e uma divergência só é aceita se o
hash bruto registrado for uma identidade legada **conhecida** (`legacy_artifact_hashes.py`) cujo
canônico confere. Mudança real de conteúdo, binário diferente ou hash desconhecido são rejeitados.
`experiment_config_canonical_sha256` é registrado ao lado do bruto e entra nos manifestos de run
(aditivo). Há uma única implementação do hash canônico (`text_hashing.py`), usada por freeze, validação
de rotas e ferramentas de freeze.

`freeze.py` roda dentro do `ExperimentRunner` (valida o freeze e gera campos dos manifestos de
run); por isso, pela regra de inclusão (todo `src/traffic_agents` exceto `replay` e as ferramentas
`final_freeze.py`/`freeze_hashing.py`), pertence ao `SCIENTIFIC_TREE_V1`.

## Caminhos portáteis no freeze de experimento (Prompt 59.1E)

O `checksums.json` agora é schema 3. Os arquivos congelados são identificados por
`relative_path`: caminho **relativo à raiz do repositório**, em POSIX (`/`), sem letra de unidade,
barra inicial, UNC, segmentos `.`/`..`/vazios nem barra invertida (ex.:
`experiments/configs/final_main.yaml`). As entradas derivadas usam `scenario_relative_path`. A
localização do repositório no disco **não faz parte da identidade científica**: o mesmo freeze
verifica depois de mover ou clonar o repositório, em Linux, CI ou Docker. A raiz vem de
`git rev-parse --show-toplevel` a partir da âncora (config ou diretório do freeze), nunca só do
diretório atual, então geração e verificação funcionam a partir de subdiretórios. Hashes de
conteúdo (`CANONICAL_TEXT_LF_V1`), SHA da fonte científica e `SCIENTIFIC_TREE_SHA256` seguem sendo
a identidade autoritativa.

Segurança: registros do schema 3 com caminho absoluto, de unidade, UNC, `..` ou que resolvam
(inclusive por symlink) para fora do repositório são rejeitados, assim como um campo `path`
absoluto em schema 3. Uma entrada científica fora do repositório não pode ser congelada (auditado:
nenhuma entrada das campanhas finais está fora do repositório). O manifesto do freeze
(`freeze_manifest.json`) também guarda o config de origem como caminho relativo.

Registros históricos (schema 1 e 2) com caminhos absolutos continuam sendo verificados como antes
quando o caminho exato existe; não são reescritos nem mapeados por adivinhação e são considerados
**não portáteis**. A campanha final usa o schema 3.

## Freeze definitivo (Prompt 59.2)

Gerado com a árvore limpa (`git_working_tree_dirty_at_input_inspection = false`), sem executar
simulações, por `python scripts/build_final_freeze.py --scientific-source-sha <SHA>`.

| Item | Valor |
|---|---|
| `SCIENTIFIC_SOURCE_GIT_SHA` | `176178e36eeafb329a5a1350161be61cf97902b0` |
| `SCIENTIFIC_TREE_SHA256` (`SCIENTIFIC_TREE_V1`, 183 arquivos) | `b713917890e2dc65b7c25dfca80c627a7607146539bd2dadf5613f70451cdeff` |
| `FREEZE_MANIFEST_SHA256` (canônico; fora do manifesto) | `de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec` |
| Esquemas de hash | `CANONICAL_TEXT_LF_V1`, `SCIENTIFIC_METADATA_V1`, `SCIENTIFIC_TREE_V1` |
| Seeds (N = 10) | 42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001 |
| Runs | main 200 + S5 90 = **290** (200 e 90 identidades únicas, 0 duplicadas) |
| S5 | C1 40 + C2 40 + B2 10 (uma referência por seed) |
| B0 | `B0_FIXED_CALIBRATED`, plano `fx_c84_demand_proportional_alternate`, ciclo 84 s, amarelo 3 s, vermelho total 2 s, `DEMAND_PROPORTIONAL`, `ALTERNATE`, offsets 0/42 s |
| B0 bruto / canônico | `a950d82d1d59562766b183c096477f39215f0de8a905960b223a7a6fcef1f0fe` / `4ebbed94ef4feae63f7af62bc70944634bc5cbf399d0cd7856693d6758e6da19` |
| Rede bruto / canônico | `46953c48351b0fdecf9babca662354bd5e45a5772553b153bc6f354c5332b48e` / `4fc7401a613eed05d08a0ff577469f3f5eb575709ddc04785b06694abc5a8f5b` |
| Rota de referência | `left1A1 A1B1 B1C1 C1right1` (sequência exata de arestas) |
| Bootstrap | percentil 95 %, 10 000 reamostragens; semente da análise `20260910`; base da rota de referência `20260930` |
| `uv.lock` | `46f15418f777ca5df069c8923a82e0e7f18444835cc469322540ebd0d39ee02c` |

Política de S3 (gate composto *post-hoc* do Pilot V2), política de S4 (`ALLOW_AND_MEASURE`,
`sumo_teleports_total` canônico), desenho do S5, hashes e caminhos portáteis (schema 3, caminhos
relativos POSIX) estão descritos nas seções acima. Evidência versionada em
`docs/evidencias/final-freeze/` (`final-freeze-manifest.json`, `final-freeze-manifest.sha256`,
`run-matrix.csv`, `scenario-inputs.csv`, `scientific-tree.csv`, `statistical-plan.json`).
Verificação: `python scripts/build_final_freeze.py --verify --scientific-source-sha
176178e36eeafb329a5a1350161be61cf97902b0` (OK). Após o commit do registro do freeze, o SHA fonte
continua sendo `176178e…`; `HEAD` passa a ser descendente (a árvore científica não muda).
