# Rota de Referência

Status: decisão de rota de referência para a comparação de tempo de viagem entre B0, B2 e C1.
**Nenhum resultado foi calculado** neste documento. A métrica ainda não está implementada; o que
segue define a rota, a justificativa de seleção, a regra de coorte e as métricas futuras.

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

## Métricas futuras (ainda não implementadas)

Para cada run, sobre a coorte da rota de referência:

| Campo (proposto) | Definição |
|---|---|
| `reference_route_offered_vehicle_count` | Veículos da coorte de referência ofertados. |
| `reference_route_departed_vehicle_count` | Inseridos. |
| `reference_route_arrived_vehicle_count` | Concluídos. |
| `reference_route_completion_ratio` | `arrived / offered`. |
| `reference_route_mean_travel_time` | Média de `duration` (`tripinfo.xml`) das viagens concluídas. |
| `reference_route_mean_waiting_time` | Média de `waitingTime` das viagens concluídas. |
| `reference_route_mean_time_loss` | Média de `timeLoss` das viagens concluídas. |
| `reference_route_mean_stops` | Média de `waitingCount` das viagens concluídas. |

Regras de reporte: sempre ler o tempo de viagem junto com a razão de conclusão (o tempo de viagem
exclui veículos não concluídos). Dados necessários já existem: `sumo/tripinfo.xml` por run e os
arquivos de rotas; o cálculo posterior pode ser feito sobre runs existentes sem nova simulação.

## Comparações de controladores

- **B0_FIXED vs B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT**, pareadas por cenário e seed.
- A comparação científica primária permanece **B2 vs C1** (ver `baselines.md`); o B0 serve como
  referência de tempo fixo (use o `B0_FIXED_CALIBRATED` nas comparações finais; o `B0_FIXED_STATIC` é o histórico do Pilot V2).
- Reportar por cenário (S1, S2, S3, S4); não agregar regimes diferentes numa única média.
- Intervalos de confiança descritivos (5 seeds no piloto; contagem final de seeds pendente).

## Limitações

- A rota de referência é uma única origem-destino; não representa o desempenho de toda a rede.
- Os resultados dependem do regime (S4 é sobrecarga intencional).
- Sem resultados calculados até aqui.
