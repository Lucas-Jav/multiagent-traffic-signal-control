# Baselines e Controladores (Documento Canônico)

Status: documento canônico dos controladores do experimento. Resolve a auditoria do Prompt 54.
Fórmulas e parâmetros detalhados permanecem em [`controllers.md`](controllers.md). Este documento
define papéis, informação disponível, semântica temporal e o papel experimental de cada controlador.
Nenhum parâmetro de controlador foi alterado ao escrevê-lo.

```text
PRIMARY_SCIENTIFIC_COMPARISON = B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT
B0_FIXED_STATIC               = historical Pilot V2 baseline (controller_id B0_FIXED, STATIC_DEFAULT)
B0_FIXED_CALIBRATED           = final fixed-time baseline (EMPIRICAL_FIXED_TIME, calibration done)
B0_CALIBRATION_STATUS         = DONE (see fixed-time-calibration.md)
```

Dois baselines de tempo fixo coexistem, com papéis distintos:

| Nome | `controller_id` | Plano | Uso |
|---|---|---|---|
| `B0_FIXED_STATIC` | `B0_FIXED` | Estático de 98 s do `tlLogic` da rede | **Histórico** (Pilot V2) |
| `B0_FIXED_CALIBRATED` | `B0_FIXED_CALIBRATED` | Ciclo de 84 s calibrado (`experiments/fixed_time/b0_fixed_calibrated.json`) | **Campanha final** |

Comparações "B0 vs adaptativo" do Pilot V2 usam o B0 histórico e devem ser rotuladas assim; as
comparações finais usam `B0_FIXED_CALIBRATED`. A comparação primária B2 vs C1 do Pilot V2 não depende
do B0.

## Natureza de todos os controladores

Todos os controladores são **reativos**: decidem com base no estado observado no passo corrente
(filas, ocupação, taxa de chegada medida, mensagens de vizinhos recebidas). Nenhum prevê demanda
futura, aprende parâmetros ou usa aprendizado de máquina. Ver
[`tcc-scope-alignment.md`](tcc-scope-alignment.md).

## Semântica temporal comum

- Passo de simulação: `step_length = 1.0 s`. Cada controlador adaptativo é consultado em todo
  passo (`before_simulation_step`) e emite `KEEP_PHASE` ou o pedido da próxima fase verde.
- Warmup `300 s`, janela de medição `3600 s` (total `3900 s`), idênticos para todos os controladores.
- Restrições de segurança comuns a B1, B2, C1 e C2: verde mínimo `10 s`, verde máximo `60 s`,
  amarelo `3 s`, all-red `2 s`, sequência amarelo/all-red obrigatória.

## Relação com o `PhaseSafetyManager`

| Controlador | Passa pelo `PhaseSafetyManager`? | Observação |
|---|---|---|
| `B0_FIXED` | Não | Não emite atuação TraCI; o programa `tlLogic` do SUMO roda inalterado. |
| `B1_LOCAL_ADAPTIVE` | Sim | Intenção validada (verde mínimo/máximo, amarelo, all-red). |
| `B2_LOCAL_PRESSURE` | Sim | Mesmo caminho de segurança. |
| `C1_COOPERATIVE_COMPACT` | Sim | Mesmo caminho de segurança do B2. |
| `C2_COOPERATIVE_EXPANDED` | Sim | Mesmo caminho de segurança do B2/C1. |

`KEEP_PHASE` em verde estende a fase via `trafficlight.setPhaseDuration` até `max_green_seconds`.
Detalhes em `controllers.md` (Semântica de atuação).

---

## B0_FIXED

- **Papel conceitual**: referência de tempo fixo, sem adaptação.
- **Algoritmo implementado**: nenhum. `FixedTimeController` não faz nada em
  `before_simulation_step`/`after_simulation_step` (`src/traffic_agents/controllers/fixed_time.py`).
  O comportamento é o do programa `tlLogic` estático armazenado em
  `scenarios/grid_3x3/network.net.xml`.
- **Observações usadas**: nenhuma.
- **Comunicação**: nenhuma.
- **Semântica temporal**: ciclo fixo de **98 s** por interseção, com offsets por interseção
  (`metadata.json`: `traffic_light_offsets_seconds`, passo de 10 s entre as interseções lógicas).
- **Relação com o `PhaseSafetyManager`**: não aplicável (sem atuação).
- **Papel experimental**: baseline de tempo fixo de engenharia/referência no Pilot V2.

### Classificação truthful do B0 histórico (`B0_FIXED_STATIC`)

```text
B0_FIXED_METHOD (histórico) = STATIC_DEFAULT
```

- O B0 **não é Webster**. Nenhum cálculo de ciclo de Webster, fluxo de saturação, razão de fluxo
  crítico ou divisão de verde por demanda existe no código ou na documentação formal.
- O B0 **não foi calibrado a partir da demanda** dos cenários S1-S4.
- O B0 usa o `tlLogic` fixo versionado em `network.net.xml`, produzido por
  `scripts/generate_grid.py` a partir dos **defaults do `netgenerate`** (layout `incoming`,
  `--tls.yellow.time 3`), mais intergreen all-red de 2 s inserido pelo script e offsets por
  interseção. O script reproduz exatamente a rede versionada (verificado por regeneração em
  diretório temporário, sem sobrescrever a rede).
- Como cada parâmetro foi obtido:

| Parâmetro | Valor | Origem |
|---|---|---|
| Comprimento do ciclo | 98 s | Consequência da soma dos defaults do `netgenerate` + all-red do script |
| Verdes | 18 / 20 / 20 / 20 s (4 fases, uma aproximação por fase) | Defaults do `netgenerate` (`--tls.layout incoming`); não calibrados |
| Amarelo | 3 s | `--tls.yellow.time 3` (`PHASE_YELLOW_SECONDS`) |
| All-red | 2 s | `apply_traffic_light_intergreen_phases` (`TRAFFIC_LIGHT_INTERGREEN_SECONDS`) |
| Offsets | 0, 10, ..., 80 s conforme a interseção | `build_traffic_light_offsets` (`TLS_OFFSET_STEP_SECONDS = 10`) |

Ciclo: `18 + 20 + 20 + 20 (verdes) + 4 x 3 (amarelos) + 4 x 2 (all-red) = 98 s`.

O B0 do Pilot V2 é um **baseline de tempo fixo de engenharia/referência**, medido com o mesmo
pipeline dos demais (`B0_MEASUREMENT_FAIR = true`). **Não é o baseline de tempo fixo calibrado
final solicitado pelo orientador**; isso não o torna inválido, e ele não deve ser descrito como
"Webster", "ótimo" ou "calibrado". O baseline calibrado final é o `B0_FIXED_CALIBRATED` abaixo.

---

## B0_FIXED_CALIBRATED (baseline de tempo fixo final)

- **Papel conceitual**: baseline de tempo fixo calibrado, sem responsividade ao tráfego, para a
  campanha final.
- **Algoritmo implementado**: `FixedTimePlanController` (`controllers/fixed_time_plan.py`) instala um
  plano estático via TraCI **uma única vez**, antes do primeiro passo (`setProgramLogic`, `setPhase`,
  `setPhaseDuration`), e depois não age mais. Só muda a duração dos verdes e o offset dos programas
  existentes; estados, ordem das fases, amarelo e all-red ficam preservados.
- **Método de calibração**: `EMPIRICAL_FIXED_TIME`, busca em grade predeclarada (ciclo x divisão de
  verde x offset), objetivo e guardas definidos antes de avaliar candidatos, apenas execuções B0, seeds
  exclusivas. **Não é Webster.** Detalhes em [`fixed-time-calibration.md`](fixed-time-calibration.md).
- **Plano selecionado** (`fx_c84_demand_proportional_alternate`): ciclo 84 s; verdes entre 14 e 20 s,
  proporcionais à demanda média de S1-S4 (mín. 10 s, máx. 60 s); amarelo 3 s; all-red 2 s; offsets
  alternados (0 ou 42 s, xadrez).
- **Observações usadas**: nenhuma. **Comunicação**: nenhuma.
- **Semântica temporal**: ciclo fixo de 84 s por interseção; semântica de offset igual à do `tlLogic`
  do SUMO.
- **`PhaseSafetyManager`**: não aplicável (sem atuação adaptativa); os limites de verde (10-60 s) e as
  temporizações de segurança são validados na construção do plano.
- **Identidade no manifest**: `controller_id = B0_FIXED_CALIBRATED`, `fixed_time_plan_id`,
  `fixed_time_plan_sha256`, `traffic_responsive = false`.
- **Papel experimental**: referência de tempo fixo da campanha final (B0 vs B2 vs C1).
- **Resultado da calibração**: bem melhor que o estático em S1-S3 e ligeiramente pior no S4
  (saturação); ver `fixed-time-calibration.md`.

---

## B1_LOCAL_ADAPTIVE

- **Papel conceitual**: baseline adaptativo local simples (heurística de pressão de fila).
- **Algoritmo implementado**: pressão de fase = soma das filas (`incoming_queue`) das lanes da
  fase. Antes de `min_green_seconds`, mantém a fase. Depois, compara a pressão da fase atual com a
  maior pressão entre as fases concorrentes: (i) se o verde atingiu `max_green_seconds` e a
  concorrente tem pressão >= `significant_queue_threshold`, pede a próxima fase; (ii) se a fase
  atual tem pressão >= `significant_queue_threshold` e a concorrente não a supera por mais de
  `pressure_margin`, mantém; (iii) se a concorrente supera a atual por mais de `pressure_margin`,
  pede a próxima fase; caso contrário mantém.
- **Parâmetros**: `min_green_seconds=10.0`, `significant_queue_threshold=2`, `pressure_margin=1.0`,
  `max_green_seconds=60.0`, `internal_clearance_halting_threshold=1`.
- **Observações usadas**: apenas observação local da própria interseção (filas das aproximações).
- **Comunicação**: nenhuma.
- **Semântica temporal**: decisão a cada passo de 1 s, sujeita aos limites de verde.
- **`PhaseSafetyManager`**: sim.
- **Papel experimental**: baseline adaptativo local mais simples; referência para a família
  adaptativa.

## B2_LOCAL_PRESSURE

- **Papel conceitual**: núcleo local de pressão; é o **controle sem cooperação** da comparação
  primária.
- **Algoritmo implementado**: pressão por movimento
  `queue_weight*upstream_queue + arrival_rate_weight*arrival_rate - downstream_occupancy_weight*min(outgoing_occupancy/downstream_saturation_occupancy, 1)`;
  a pontuação da fase é a soma das pressões dos movimentos que ela atende; troca para a fase de
  maior pontuação permitida. Mantém a fase quando nenhum candidato permitido melhora a pontuação.
- **Parâmetros**: `min_green_seconds=10.0`, `max_green_seconds=60.0`, `queue_weight=1.0`,
  `arrival_rate_weight=0.0`, `downstream_occupancy_weight=10.0`,
  `downstream_saturation_occupancy=1.0`, `switch_score_margin=0.0`,
  `internal_clearance_halting_threshold=1`.
- **Observações usadas**: apenas observação local (filas upstream, taxa de chegada medida,
  ocupação das lanes de saída da própria interseção).
- **Comunicação**: nenhuma (`communication_enabled: false`).
- **Semântica temporal**: decisão a cada passo de 1 s.
- **`PhaseSafetyManager`**: sim.
- **Papel experimental**: **referência sem cooperação** da comparação científica primária.

## C1_COOPERATIVE_COMPACT

- **Papel conceitual**: o mesmo núcleo do B2 acrescido de **informação compacta de vizinhos**.
- **Algoritmo implementado**: pontuação local do B2 mais um ajuste cooperativo calculado a partir da
  `CompactNeighborMessage` recebida: soma, para as fases locais compatíveis, a estimativa de
  demanda de entrada enviada pelo vizinho (`sum(outgoing_queue_summary) + arrival_trend`),
  ponderada por `projected_incoming_weight`, pelos pesos de conversão e por
  `directed_pressure_weight`, e subtrai o congestionamento a jusante
  (`downstream_congestion_weight`).
- **Nota de nomenclatura**: `projected_incoming_weight`, `projected_demand` e `arrival_trend` são
  nomes históricos. O valor representa uma **estimativa do estado corrente** (filas atuais e taxa
  de chegada medida atual); **não é previsão temporal** nem tendência calculada ao longo do tempo.
- **Parâmetros**: `projected_incoming_weight=1.0`, `directed_pressure_weight=0.25`,
  `downstream_congestion_weight=10.0`, conversão `straight=0.60`, `left=0.20`, `right=0.20`.
- **Observações usadas**: observação local + mensagens recebidas dos vizinhos adjacentes
  (topologia `GRID_3X3_ADJACENT_INTERSECTIONS`).
- **Comunicação**: `CompactNeighborMessage` via `MessageBus`. A cada passo cada agente publica e
  em seguida recebe. Mensagem com `delay_steps = 0` é entregue no mesmo passo de criação;
  `delay_steps = d` agenda a entrega para `created_step + d`. Mensagem usada somente se
  `current_step - created_step <= max_message_age_steps` (padrão `1`); caso contrário é contada
  como `messages_stale` e ignorada. Perda: `drop_probability` com RNG derivada da seed.
- **Semântica temporal**: decisão a cada passo de 1 s.
- **`PhaseSafetyManager`**: sim, mesmo caminho do B2.
- **Fallback**: sem mensagens válidas, a pontuação ajustada é igual à do B2.
- **Papel experimental**: tratamento cooperativo da comparação primária.

## C2_COOPERATIVE_EXPANDED

- **Papel conceitual**: variante cooperativa com mensagem expandida.
- **Algoritmo implementado**: mesma arquitetura, mesmo núcleo local e mesmo caminho de segurança do
  C1/B2, usando `ExpandedNeighborMessage` (filas por movimento de saída, taxa de chegada estimada
  por movimento relevante, ocupação por conexão a jusante). A demanda de entrada estimada é
  `sum(queue_per_outgoing_movement) + sum(estimated_arrival_rate_per_relevant_movement)` e o
  congestionamento a jusante usa o máximo de `occupancy_per_downstream_connection`. Mesma
  observação sobre nomenclatura histórica de "projetada" do C1.
- **Observações usadas**: local + mensagem expandida dos vizinhos.
- **Comunicação**: `ExpandedNeighborMessage`, mesmas regras de atraso, perda e atualidade do C1.
- **Semântica temporal**: decisão a cada passo de 1 s.
- **`PhaseSafetyManager`**: sim.
- **Papel experimental**: análise secundária/sensibilidade ao conteúdo da mensagem; não faz parte da
  comparação científica primária.

---

## Comparação científica primária

```text
PRIMARY_SCIENTIFIC_COMPARISON = B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT
```

B2 e C1 pertencem à **mesma família de pressão local**: C1 reutiliza o núcleo do B2 e acrescenta
apenas a informação compacta de vizinhos. Assim, a diferença pareada (mesmo cenário e seed) isola o
efeito da cooperação compacta. B0 (tempo fixo) e B1 servem como referências de contexto (tempo fixo e
adaptativo local simples); C2 é análise secundária de conteúdo da mensagem.

| Controlador | Papel |
|---|---|
| `B0_FIXED` (`B0_FIXED_STATIC`) | Referência de tempo fixo histórica (Pilot V2) |
| `B0_FIXED_CALIBRATED` | Referência de tempo fixo final, calibrada (campanha final) |
| `B1_LOCAL_ADAPTIVE` | Referência adaptativa local simples |
| `B2_LOCAL_PRESSURE` | Controle primário sem cooperação |
| `C1_COOPERATIVE_COMPACT` | Tratamento primário cooperativo |
| `C2_COOPERATIVE_EXPANDED` | Variante secundária (mensagem expandida) |
