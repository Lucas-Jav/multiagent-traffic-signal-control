# Experimentos

## S5 Degradação da Comunicação (definição canônica ativa)

Esta é a **única definição ativa do S5**. Ela é a mesma de
[`methodology/campaign-matrix.md`](methodology/campaign-matrix.md) e
[`methodology/experimental-protocol.md`](methodology/experimental-protocol.md).

Config: `experiments/configs/final_s5_packet_loss.yaml` (`campaign_role: PLANNED_FINAL`,
estado pré-congelamento). **O S5 ainda não foi executado.** Nenhum resultado de robustez a perda
de pacotes existe; ele só pode ser apresentado como avaliação planejada/hipótese.

- Tráfego base: `S2_DIRECTIONAL_PEAK` (demanda fixa; o S5 não define um novo cenário de demanda).
- Perda de pacotes (`drop_probability`): `0.00`, `0.20`, `0.50`, `1.00` (0%, 20%, 50%, 100%).
- Atraso (`delay_steps`): `0` (fixo).
- Referência: `B2_LOCAL_PRESSURE` (sem comunicação).
- Controladores cooperativos: `C1_COOPERATIVE_COMPACT` e `C2_COOPERATIVE_EXPANDED`.
- Execuções planejadas atuais: `5 seeds x (1 B2 + 2 cooperativos x 4 níveis de perda) = 45 runs`
  (a contagem final de seeds é decisão pendente).
- Com 100% de perda, C1 e C2 recorrem ao fallback local (equivalente à pontuação do B2, mas não
  se assume igualdade exata de métricas finais).

Campos de reprodutibilidade em toda config de execução:

- `scenario_base`
- `scenario`
- `controller_id`
- `seed`
- `communication_seed_policy`
- `communication.delay_steps`
- `communication.drop_probability`
- `communication.rng_seed`
- `communication.max_message_age_steps`

`communication_seed_policy: derived_from_simulation_seed_delay_drop` significa que a seed efetiva
do RNG do canal de mensagens é derivada de forma determinística da seed da simulação, de
`delay_steps` e de `drop_probability`.

`max_message_age_steps` permanece fixo em `1`. Ele não é aumentado automaticamente quando o atraso
aumenta.

### S5B_DELAY (opcional e separado)

Estudo de atraso opcional, reportado separadamente do S5 de perda de pacotes
(`delay_steps` `0`, `1`, `3`, `5`). Não faz parte da campanha central. Sem config obrigatória.

Não execute o S5 como parte da validação de smoke.

---

## DEPRECATED / HISTORICAL: matriz exploratória antiga do S5

> **DEPRECATED / HISTORICAL.** Esta seção descreve a matriz exploratória original do S5 e é
> preservada apenas por história experimental. **Não é a definição ativa.** Foi substituída pela
> definição canônica acima (perda `0/20/50/100%`, atraso `0`).

Configs legadas (geradas por `scripts/generate_s5_matrix.py`, não são a campanha do TCC):

- `experiments/configs/s5_communication_degradation_c1.yaml` (DEPRECATED)
- `experiments/configs/s5_communication_degradation_c2.yaml` (DEPRECATED)

Matriz legada, com seed única `42` e demanda S2:

- `delay_steps`: `0`, `1`, `3`, `5`
- `drop_probability`: `0.00`, `0.05`, `0.10`, `0.25`

A matriz produzia 16 combinações cooperativas por controlador, mais uma execução de referência com
`B2_LOCAL_PRESSURE` por arquivo (17 runs). IDs de execução legados: `s5_c1_delay0_drop0`,
`s5_c1_delay3_drop010`, `s5_c1_delay5_drop025`.

Regeneração (apenas para reproduzir o histórico):

```powershell
python scripts\generate_s5_matrix.py
```
