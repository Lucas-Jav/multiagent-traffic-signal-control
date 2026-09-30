# Experimentos

## S5 Degradação da Comunicação

Objetivo: medir a robustez de controladores cooperativos sob atraso e perda de
mensagens.

O S5 não define um novo cenário de demanda de tráfego. Ele usa a demanda base fixa
`S2_DIRECTIONAL_PEAK` de
`scenarios/grid_3x3/scenario_s2_directional_peak.yaml` e varia apenas o
canal de comunicação dos controladores cooperativos.

Controlador de referência:

- `B2_LOCAL_PRESSURE`

Controladores cooperativos:

- `C1_COOPERATIVE_COMPACT`
- `C2_COOPERATIVE_EXPANDED`, gerado separadamente como config opcional

Matriz:

- `delay_steps`: `0`, `1`, `3`, `5`
- `drop_probability`: `0.00`, `0.05`, `0.10`, `0.25`

A matriz produz 16 combinações cooperativas por controlador cooperativo.
Cada arquivo de experimento gerado também inclui uma execução de referência com
`B2_LOCAL_PRESSURE`.

Configs geradas:

- `experiments/configs/s5_communication_degradation_c1.yaml`
- `experiments/configs/s5_communication_degradation_c2.yaml`

Exemplos de IDs de execução gerados:

- `s5_c1_delay0_drop0`
- `s5_c1_delay3_drop010`
- `s5_c1_delay5_drop025`

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

`communication_seed_policy: derived_from_simulation_seed_delay_drop` significa que a
seed efetiva do RNG do canal de mensagens é derivada de forma determinística da
seed da simulação, de `delay_steps` e de `drop_probability`.

`max_message_age_steps` permanece fixo em `1` em toda a matriz. Ele não é
aumentado automaticamente quando o atraso aumenta, de modo que execuções com `delay_steps > 1` podem
produzir mensagens cooperativas obsoletas (stale).

Regenere as configs do S5 de forma determinística:

```powershell
python scripts\generate_s5_matrix.py
```

Não execute o S5 como parte da validação de smoke. O S5 é uma config de campanha e deve ser
executado somente quando a campanha de degradação da comunicação for iniciada
intencionalmente.
