# Matriz de Campanha V1

Status: matriz de campanha de pré-execução (pre-flight) para o piloto V1 e as campanhas finais planejadas.

Este documento descreve apenas a estrutura da campanha. Ele não reporta
resultados e não congela a campanha final. Os resultados do piloto não devem
ser mesclados aos resultados da campanha final congelada.

## Política de Seeds

Pool de seeds pré-declarado:

```text
campaign_v1_seed_pool_2026-09-29
42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001
```

Seeds do piloto fixadas antes da execução do piloto:

```text
42, 2027, 3253, 4517, 5791
```

A CONTAGEM FINAL DE SEEDS SERÁ DECIDIDA SOMENTE APÓS O PILOTO.

As seeds não devem ser substituídas, removidas nem reordenadas por causa dos
resultados comparativos dos controladores.

## Piloto

Config:

- `experiments/configs/pilot.yaml`
- `campaign_role: PILOT`

Cenários:

- `S1_BALANCED`
- `S2_DIRECTIONAL_PEAK`
- `S3_DEMAND_SHIFT`
- `S4_LOCAL_SATURATION`

Controladores:

- `B0_FIXED`
- `B1_LOCAL_ADAPTIVE`
- `B2_LOCAL_PRESSURE`
- `C1_COOPERATIVE_COMPACT`
- `C2_COOPERATIVE_EXPANDED`

Seeds:

- `42`
- `2027`
- `3253`
- `4517`
- `5791`

Execuções planejadas:

```text
4 scenarios x 5 seeds x 5 controllers = 100 runs
```

Papel:

- Validar a estabilidade de execução, a completude dos dados, o consumo de
  armazenamento, o tempo de execução, as invariantes de rota/config e a
  variabilidade antes de decidir a contagem final de seeds.
- As saídas do piloto não são resultados da campanha final.

Nota de status (Pilot V2): a interpretação final do resultado do Pilot V2 é
`RESULT_INTERPRETATION=MIXED`, `RESULT_CONFIDENCE=MEDIUM`,
`C1_GENERAL_SUPERIORITY_CLAIMED=NO`, `C1_SCENARIO_SPECIFIC_BENEFIT=S4` e
`READY_FOR_TCC_USE=YES`. O Pilot V2 não provou superioridade geral do C1 sobre
o B2: o C1 se beneficiou claramente no S4 saturado, piorou no S1 e no S3 e, no
S2, apresentou um trade-off (redução de atraso/fila, mas redução de
vazão/razão de conclusão). Este documento permanece uma descrição estrutural da
matriz e não substitui os relatórios de resultados do piloto. Como nota
histórica, a formulação anterior de que o S3 bloquearia o piloto foi superada
pelo gate composto; a política do S4 é `ALLOW_AND_MEASURE` (teleports devem ser
reportados, mas não bloqueiam a validade do S4).

## Final Main

Config:

- `experiments/configs/final_main.yaml`
- `campaign_role: PLANNED_FINAL`
- estado planejado pré-congelamento; não executar como final antes da decisão
  final de seeds e do congelamento.

Cenários:

- `S1_BALANCED`
- `S2_DIRECTIONAL_PEAK`
- `S3_DEMAND_SHIFT`
- `S4_LOCAL_SATURATION`

Controladores:

- `B0_FIXED`
- `B1_LOCAL_ADAPTIVE`
- `B2_LOCAL_PRESSURE`
- `C1_COOPERATIVE_COMPACT`
- `C2_COOPERATIVE_EXPANDED`

Decisão de seeds:

- Pendente da avaliação do piloto.
- A config planejada atual usa o conjunto mínimo de seeds do piloto como um
  modelo executável pré-congelamento, e não como uma decisão final congelada da
  contagem de seeds.

Execuções planejadas atuais:

```text
4 scenarios x 5 seeds x 5 controllers = 100 planned runs
```

## S5 Packet Loss

Config:

- `experiments/configs/final_s5_packet_loss.yaml`
- `campaign_role: PLANNED_FINAL`
- estado planejado pré-congelamento; não executar como final antes da decisão
  final de seeds e do congelamento.

Cenário de tráfego base:

- `S2_DIRECTIONAL_PEAK`

Controladores:

- `B2_LOCAL_PRESSURE` referência
- `C1_COOPERATIVE_COMPACT`
- `C2_COOPERATIVE_EXPANDED`

Matriz de perda de pacotes:

- `drop_probability: 0.00`
- `drop_probability: 0.20`
- `drop_probability: 0.50`
- `drop_probability: 1.00`

Atraso:

- `delay_steps: 0` fixo na campanha obrigatória de perda de pacotes.
- Os estudos de atraso permanecem opcionais e separados.

Decisão de seeds:

- Pendente da avaliação do piloto.
- A config planejada atual usa o conjunto mínimo de seeds do piloto como um
  modelo executável pré-congelamento, e não como uma decisão final congelada da
  contagem de seeds.

Execuções planejadas atuais:

```text
5 seeds x (1 B2 reference + 2 cooperative controllers x 4 drop probabilities)
= 45 planned runs
```

## S5B Delay Opcional

Somente opcional. Nenhuma config obrigatória é necessária para a campanha
central do TCC da V1.

Se executado, mantenha-o separado do S5 packet loss e use:

- `delay_steps: 0`
- `delay_steps: 1`
- `delay_steps: 3`
- `delay_steps: 5`

## Contrato de Equidade (Fairness)

Para o mesmo cenário e a mesma seed, os controladores comparados devem
compartilhar:

- rede
- rota/demanda
- razões de conversão
- warmup
- duração da medição
- passo de simulação (step length)
- plano de fases
- restrições de segurança

Somente o comportamento do controlador e, quando projetado, o comportamento de
comunicação podem diferir.
