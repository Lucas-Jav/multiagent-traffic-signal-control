# Metodologia dos Controladores

Este documento faz parte do material de congelamento da metodologia da V1. Ele
documenta as entradas e as fórmulas dos controladores sem ajustar parâmetros
dos controladores. O documento canônico de papéis, semântica temporal e papel experimental é
[`baselines.md`](baselines.md); este arquivo mantém as fórmulas e os parâmetros.

Todos os controladores são **reativos** (decidem com o estado corrente observado); nenhum prevê
demanda futura nem usa aprendizado de máquina (ver [`tcc-scope-alignment.md`](tcc-scope-alignment.md)).

## Semântica de atuação (B1, B2, C1, C2)

Os controladores adaptativos expressam a intenção como `KEEP_PHASE` ou como um
pedido da próxima fase verde válida. O `PhaseSafetyManager` a valida (verde
mínimo, verde máximo, sequência de amarelo e all-red, transições permitidas) e o
`TrafficLightActuator` aplica o comando validado:

- `KEEP_PHASE` em uma fase verde estende a fase do SUMO com o mecanismo de
  duração de fase do TraCI (`trafficlight.setPhaseDuration`), de modo que o
  verde atual permaneça ativo além da duração estática do programa SUMO (18/20 s
  nos programas do grid) enquanto `elapsed_green < max_green_seconds`. O
  período restante de retenção é `max_green_seconds - elapsed_green`; assim, um
  controlador que mantém a fase repetidamente pode segurar o verde até
  `max_green_seconds`.
- Quando `elapsed_green >= max_green_seconds`, o safety manager força a
  transição para a próxima fase do programa (o amarelo), nunca pulando o
  amarelo nem o all-red.
- Uma mudança de fase continua sendo recusada antes de `min_green_seconds` e só
  segue a sequência amarelo/all-red do SUMO; estados brutos de sinal nunca são
  comandados.
- O `B0_FIXED` não emite atuação e permanece inalterado.

Antes do Prompt 46.6, `KEEP_PHASE` era um no-op, de modo que o próprio programa
do SUMO encerrava todo verde em sua duração estática e `max_green_seconds`
era inalcançável. A pontuação, os pesos e os limiares dos controladores não
foram alterados por essa correção.

Nota: os pesos de conversão cooperativos (`straight=0.60`, `left=0.20`,
`right=0.20`) abaixo são parâmetros do controlador para o ajuste cooperativo;
eles são independentes das razões de conversão dos cenários (S1-S4:
0.70/0.15/0.15) e não foram modificados.

## B0_FIXED

- Entradas permitidas: nenhuma do fluxo de observação adaptativo.
- Comportamento: deixa o programa de fases de tempo fixo do SUMO inalterado.
- Fallback: não aplicável.
- Status do controle base final: `B0_FIXED` é um baseline estático de tempo
  fixo, não um baseline otimizado por Webster.
- Auditoria Webster: nenhum cálculo de ciclo de Webster, premissa de fluxo de
  saturação, cálculo de razão de fluxo crítico ou cálculo de divisão de verde
  derivado da demanda é implementado para o `B0_FIXED`. O controlador não emite
  atuação TraCI e não recalcula a temporização dos semáforos durante a
  execução.
- Fonte da temporização: o plano fixo atual vem do `tlLogic` versionado do SUMO
  em `scenarios/grid_3x3/network.net.xml`, gerado por `scripts/generate_grid.py`.
  Os verdes (18/20/20/20 s) são **defaults do `netgenerate`** (layout `incoming`); amarelo
  = 3 s (`--tls.yellow.time`); all-red = 2 s (inserido pelo script); ciclo = 98 s;
  offsets fixos por interseção. Essas temporizações não são calibradas com a metodologia de
  Webster nem a partir da demanda.
- `B0_FIXED_METHOD = STATIC_DEFAULT`; `B0_CALIBRATION_STATUS = DONE`: este é o B0 **histórico** (`B0_FIXED_STATIC`); o baseline final é o `B0_FIXED_CALIBRATED` (`fixed_time_plan.py`, ver `fixed-time-calibration.md`). O B0 do Pilot V2 é um
  baseline de tempo fixo de engenharia/referência, não o baseline calibrado final solicitado pelo
  orientador (ver [`baselines.md`](baselines.md)). Isso não o torna inválido.
- Nota sobre as constantes `PROTECTED_THROUGH_GREEN_SECONDS = 32` e
  `PROTECTED_TURN_GREEN_SECONDS = 10` de `generate_grid.py`: elas só atuam sobre fases com
  sinais permissivos (`g` minúsculo). A rede `incoming` do grid só tem verdes protegidos (`G`),
  então o passo é inativo e esses valores **não** descrevem o plano real (foram removidos do
  `metadata.json`).
- Classificação: arbitrário/estático com temporizações de segurança
  documentadas; não é Webster calibrado manualmente nem efetivamente calculado
  por Webster.

## B1_LOCAL_ADAPTIVE

- Entradas permitidas: apenas observação local da interseção.
- Política: compara a pressão de fila (queue) da fase verde atual com as fases
  verdes concorrentes após `min_green_seconds`.
- Parâmetros: `min_green_seconds=10.0`,
  `significant_queue_threshold=2`, `pressure_margin=1.0`,
  `max_green_seconds=60.0`,
  `internal_clearance_halting_threshold=1`.
- Fallback: manter a fase atual quando a evidência local for insuficiente.

## B2_LOCAL_PRESSURE

- Entradas permitidas: apenas observação local da interseção.
- Pressão de movimento:

```text
queue_weight * upstream_queue
+ arrival_rate_weight * arrival_rate
- downstream_occupancy_weight * min(
    outgoing_occupancy / downstream_saturation_occupancy,
    1.0
  )
```

- Pontuação da fase: soma das pressões de movimento locais atendidas pela fase
  verde.
- Parâmetros: `min_green_seconds=10.0`, `max_green_seconds=60.0`,
  `queue_weight=1.0`, `arrival_rate_weight=0.0`,
  `downstream_occupancy_weight=10.0`,
  `downstream_saturation_occupancy=1.0`,
  `switch_score_margin=0.0`,
  `internal_clearance_halting_threshold=1`.
- Fallback: manter a fase atual quando nenhum candidato permitido melhora a
  pontuação local.

## C1_COOPERATIVE_COMPACT

- Núcleo: o mesmo núcleo de pressão local do B2.
- Entradas permitidas: observação local mais a `CompactNeighborMessage`
  recebida.
- Atualidade (freshness): uma mensagem recebida só é usada quando
  `current_step - created_step <= max_message_age_steps`; mensagens obsoletas
  são contadas e ignoradas.
- Demanda de entrada estimada a partir do estado atual (compacta):

```text
sum(outgoing_queue_summary.values()) + arrival_trend
```

  Nota: os nomes `arrival_trend`, `projected_incoming_weight` e "demanda projetada" são
  históricos. O valor representa uma estimativa do estado corrente (filas atuais e taxa de chegada
  medida atual); não é previsão temporal nem tendência calculada ao longo do tempo.

- O ajuste cooperativo soma a pressão de entrada estimada às fases locais
  compatíveis usando `projected_incoming_weight`, os pesos de conversão e
  `directed_pressure_weight`; ele subtrai o congestionamento a jusante usando
  `downstream_congestion_weight`.
- Parâmetros: `projected_incoming_weight=1.0`,
  `directed_pressure_weight=0.25`, `downstream_congestion_weight=10.0`,
  pesos de conversão `straight=0.60`, `left=0.20`, `right=0.20`.
- Fallback: sem mensagens válidas, as pontuações de fase ajustadas são iguais
  às pontuações de fase locais do B2 para a mesma observação e o mesmo estado
  de segurança.

## C2_COOPERATIVE_EXPANDED

- Núcleo: o mesmo núcleo de pressão local e o mesmo caminho de segurança do
  C1/B2.
- Entradas permitidas: observação local mais a `ExpandedNeighborMessage`
  recebida.
- Atualidade (freshness): mesmo tratamento de mensagens obsoletas do C1.
- Demanda de entrada estimada a partir do estado atual (expandida):

```text
sum(queue_per_outgoing_movement.values())
+ sum(estimated_arrival_rate_per_relevant_movement.values())
```

- O congestionamento a jusante usa o valor máximo de
  `occupancy_per_downstream_connection`.
- O C2 não é meramente o mesmo payload com mais campos. Ele usa a mesma
  arquitetura e o mesmo núcleo local do B2, mas seu ajuste cooperativo pode
  usar sinais adicionais da mensagem expandida.

## Métrica de Persistência em Lane Interna

`internal_lane_persistence_events` conta veículos observados em lanes internas
em passos de simulação consecutivos. É um proxy para a ocupação persistente de
lane interna, e não uma medição direta e universal de spillback físico ou de
bloqueio da interseção.
