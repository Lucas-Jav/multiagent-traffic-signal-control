# Congelamento da campanha científica final

Especificação imutável da campanha final do TCC (Prompt 59). Nenhuma simulação foi executada para
produzi-la. Manifesto: `artifacts/final-freeze/final-freeze-manifest.json` (local, ignorado pelo
Git) e a cópia versionada `docs/evidencias/final-freeze/final-freeze-manifest.json`.

Verificação a qualquer momento (recalcula todos os hashes e a matriz, sem simular):

```
python scripts/build_final_freeze.py --verify
```

## Identidade do congelamento

- `FINAL_FREEZE_GIT_SHA` base: `b98b440b4a21ae0f53d04774bda479d3211173d9` (árvore limpa no início
  do Prompt 59). O congelamento em si adiciona arquivos (configs finais, cenários das 5 seeds
  novas, manifesto, este documento); o commit que os contém é a identidade definitiva da
  implementação científica. O manifesto registra `scientific_source_sha256` (hash de todo o código
  científico em `src/traffic_agents` e `analysis`, exceto o pacote `replay` e o módulo de
  ferramentas `final_freeze.py`), que **não depende do SHA do commit** e permite verificar que o
  código executado na campanha é o congelado.
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

Rodar `python scripts/build_final_freeze.py --verify` na árvore commitada e, por config,
`traffic-agents experiment freeze --config <cfg> --final` (exige árvore limpa e id de experimento
novo) antes de `experiment run`.
