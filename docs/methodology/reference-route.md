# Rota de Referência

Status: **rota oficial** da comparação de tempo de viagem entre `B0_FIXED_CALIBRATED`, `B2_LOCAL_PRESSURE`
e `C1_COOPERATIVE_COMPACT` (Prompt 56). Este documento define a rota, a seleção, a coorte e as métricas.
Os resultados **não** ficam aqui: estão em `artifacts/reference-route/` (git-ignorado) e na cópia
versionada leve [`../evidencias/reference-route/`](../evidencias/reference-route/), principalmente
`reference-route-analysis.md`.

Papel: evidência **pré-final** e validação de metodologia (5 seeds do Pilot V2). Não substitui a
campanha final S1-S4. As diferenças medem: `B0 -> B2` = contribuição da adaptação local;
`B2 -> C1` = contribuição incremental da cooperação.

## Rota selecionada

**Oeste -> Leste pela linha central**, passando por A5.

Sequência de arestas SUMO (exata):

```text
left1A1  ->  A1B1  ->  B1C1  ->  C1right1
```

Interpretação lógica (mapeamento verificado em `scenarios/grid_3x3/metadata.json` e
[`intersection-glossary.md`](intersection-glossary.md)):

```text
Entrada oeste (left1A1)
  -> A4 (SUMO A1)
  -> A5 (SUMO B1)
  -> A6 (SUMO C1)
  -> Saída leste (C1right1)
```

Verificação do mapeamento: `traffic_light_ids` mapeia `A4 -> A1`, `A5 -> B1`, `A6 -> C1`.
`left1A1` é a aresta de entrada oeste de `A1`; `A1B1` liga A4 a A5; `B1C1` liga A5 a A6; `C1right1`
é a saída leste de `C1`. A rota atravessa as três interseções da linha central (A4, A5, A6) sem
curvas (todas "em frente").

## Justificativa de seleção

A rota foi escolhida **por critérios estruturais, antes de qualquer comparação de desempenho entre
controladores**. Ela não foi selecionada por favorecer C1 ou qualquer outro controlador.

1. **Atravessa A5**, a interseção central e o ponto de saturação do S4 e de passagem do choque do S3.
2. **Alinhada ao corredor direcional do S2** (`west-east-middle-corridor-v2`: entrada `left1A1`,
   arestas `A1B1`, `B1C1`, saída `C1right1`), que já é o objeto de estudo do S2.
3. **Existe nos quatro cenários** (S1, S2, S3, S4) e nas cinco seeds do piloto: a rota está presente
   nos arquivos `routes_s{1..4}_seed_*.rou.xml` como uma rota com essa sequência de arestas.
4. **Tamanho amostral adequado em todos os cenários.** Veículos da coorte de medição com essa
   sequência exata (inspeção dos arquivos de rotas, 5 seeds): S1 ~45-59 por run, S2 ~97-127, S3
   ~106-116, S4 ~188-205. As rotas ortogonais/opostas por A5 (N->S, E->W) têm só ~4-12 veículos por
   run no S2 e por isso não servem como rota única de comparação.
5. **Determinística e reprodutível**: os `.rou.xml` listam veículos explícitos com `id` e `depart`
   fixos por seed e cenário, e o mesmo arquivo é usado por todos os controladores. O mesmo veículo
   existe em B0, B2 e C1.

Candidatas secundárias (não selecionadas como principal): N->S `top1B2 B2B1 B1B0 B0bottom1`
(cruza A5; amostra S2 ~6-11) e E->W `right1C1 C1B1 B1A1 A1left1` (cruza A5; amostra S2 ~9-12). São
úteis, no máximo, como controle fora do S2.

## Regra de seleção por sequência de arestas

Os IDs de rota (`r2`, `r12`, ...) **variam entre cenários e seeds**. A identificação deve ser feita
**pela sequência exata de arestas** da rota do veículo (`left1A1 A1B1 B1C1 C1right1`), nunca pelo ID.

Isto difere da definição de pertencimento ao corredor existente (`corridor_*`), que aceita qualquer
rota com `A1B1` imediatamente seguida de `B1C1` (incluindo, por exemplo, rotas que saem em `C1C0` ou
`C1C2`). A rota de referência é **estritamente a origem-destino oeste-leste** acima.

## Regra de coorte

- População: veículos ofertados cuja rota tem exatamente a sequência de arestas acima **e** cuja
  partida AGENDADA está em `[warmup, warmup + measurement_duration) = [300, 3900)` s.
- A coorte é idêntica entre controladores para o mesmo cenário e seed (determinada pelo arquivo de
  rotas).
- Métricas de viagem usam as viagens **concluídas** dessa coorte (condicional à conclusão), sempre
  acompanhadas das contagens de população abaixo.

## Métricas (implementadas em `experiments/reference_route.py`)

Para cada run, sobre a coorte da rota de referência:

| Campo | Definição |
|---|---|
| `reference_route_offered` | Veículos da coorte de referência ofertados. |
| `reference_route_departed` | Inseridos (presentes no `tripinfo.xml`). |
| `reference_route_arrived` | Concluídos (chegaram antes do fim da run). |
| `reference_route_never_inserted` | `offered - departed`. |
| `reference_route_unfinished` | `departed - arrived`. |
| `reference_route_mean_travel_time_seconds` | Média de `duration` das viagens concluídas. |
| `reference_route_median_travel_time_seconds` | Mediana de `duration` das viagens concluídas. |
| `reference_route_mean_waiting_time_seconds` | Média de `waitingTime` das viagens concluídas. |
| `reference_route_mean_time_loss_seconds` | Média de `timeLoss` das viagens concluídas. |
| `reference_route_mean_stops` | Média de `waitingCount` das viagens concluídas. |
| `reference_route_completion_ratio_offered` | `arrived / offered`. |
| `reference_route_completion_ratio_departed` | `arrived / departed`. |

Médias e medianas usam **somente viagens concluídas**; uma viagem não concluída nunca recebe duração zero; o tempo de viagem é sempre lido com
a razão de conclusão. Os dados vêm de `sumo/tripinfo.xml` por run e dos arquivos de rotas; B2 e C1
reaproveitam o `tripinfo.xml` do Pilot V2 (invariantes verificadas) e só o B0 calibrado é executado.

## Comparações de controladores

- **B0_FIXED vs B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT**, pareadas por cenário e seed.
- A comparação científica primária permanece **B2 vs C1** (ver `baselines.md`); o B0 serve como
  referência de tempo fixo (use o `B0_FIXED_CALIBRATED` nas
  comparações finais; o `B0_FIXED_STATIC` é o histórico do Pilot V2).
- Reportar por cenário (S1, S2, S3, S4); não agregar regimes diferentes numa única média.
- Intervalos de confiança descritivos (5 seeds no piloto; contagem final de seeds pendente).

## Limitações

- A rota de referência é uma única origem-destino; não representa o desempenho de toda a rede.
- Os resultados dependem do regime (S4 é sobrecarga intencional).
- Cinco seeds: ICs largos e descritivos; o tempo de viagem é condicional à conclusão (no S4 a conclusão é baixa).
- Evidência pré-final: não decide a contagem final de seeds.

## Ordem de decisão (a rota não foi escolhida pelo desempenho)

1. A rota foi proposta na auditoria do Prompt 54 por critérios **estruturais** (cruza A4, A5 e A6;
   é o corredor oeste-leste do S2; existe nos quatro cenários; amostra adequada), com contagem apenas
   dos arquivos de rotas.
2. Nenhum resultado de tempo de viagem de B0, B2 ou C1 nessa rota havia sido calculado quando a rota
   foi escolhida; os resultados do Pilot V2 (B2 vs C1) eram agregados por cenário, não por rota.
3. As faixas de amostra do Prompt 54 (S1 45-59, S2 97-127, S3 106-116, S4 188-205 por run) servem
   apenas como verificação de sanidade; os tamanhos reais são medidos e relatados, nunca forçados.
4. A coorte vem do arquivo de rotas, portanto é idêntica entre controladores na mesma seed.

## Verificações de pareamento

Para cada cenário+seed, B0 calibrado, B2 e C1 devem ter `network_sha256`, `route_sha256`,
`turning_config_sha256`, `scenario_sha256`, perfil de demanda, seed, warmup e duração de medição
**idênticos**. Qualquer divergência é CRITICAL e interrompe a análise (`pairing_mismatches`).
