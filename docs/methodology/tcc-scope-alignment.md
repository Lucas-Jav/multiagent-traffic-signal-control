# Alinhamento de Escopo do TCC

Status: nota de escopo que alinha o texto acadêmico ao que está **efetivamente implementado e
medido** neste repositório. Resolve a auditoria do Prompt 54 (claims preditivos/ML e redação dos
resultados). Este documento não altera o código nem os resultados.

## Escopo atualmente implementado

```text
CURRENT IMPLEMENTED SCOPE:
Controle semafórico reativo, distribuído e cooperativo.
```

- Um agente por interseção (rede sintética 3x3 no SUMO, via TraCI).
- Controladores locais (B1 heurístico, B2 pressão local) e cooperativos (C1 e C2) que trocam
  mensagens entre interseções adjacentes.
- Todos os controladores decidem com o **estado corrente**: filas observadas, taxa de chegada medida
  agora, ocupação das lanes de saída e mensagens de vizinhos recebidas dentro de uma janela de
  atualidade (`max_message_age_steps`).
- Nenhuma componente aprende, ajusta parâmetros durante a execução ou prevê tráfego futuro.

## NÃO implementado

- Aprendizado de máquina.
- Aprendizado por reforço.
- Predição por rede neural.
- Previsão de tráfego (forecasting).
- Controlador preditivo.

Os nomes `arrival_trend`, `projected_incoming_weight` e "demanda projetada" no código são
**históricos**: o valor é uma estimativa do estado corrente (fila atual + taxa de chegada medida), e
não uma previsão temporal. Ver `controllers.md` e `baselines.md`.

Técnicas preditivas e de ML podem permanecer como **trabalho futuro** (por exemplo, previsão de
demanda de curto prazo para alimentar o ajuste cooperativo, ou aprendizado por reforço
multiagente), explicitamente marcadas como não avaliadas neste trabalho.

## Título recomendado

> **Controle Distribuído e Cooperativo de Semáforos Urbanos**

Evite no título, no resumo, na introdução, na fundamentação teórica e na metodologia: "preditivo",
"inteligência artificial/aprendizado de máquina", "otimizado por aprendizado" ou qualquer
formulação que sugira que o protótipo prevê tráfego ou aprende. O repositório em si não contém tais
claims (auditoria do Prompt 54); o texto do TCC, que vive fora deste repositório, deve ser
revisado com esta lista.

Pontos do texto a verificar:

| Seção do TCC | O que verificar |
|---|---|
| Título | Remover "preditivo"/"inteligente" se presentes; usar o título recomendado. |
| Resumo | Descrever controle reativo cooperativo; não citar ML; citar resultado MIXED. |
| Introdução / objetivos | Hipótese como pergunta de pesquisa; não como resultado confirmado. |
| Fundamentação teórica | ML/RL/previsão aparecem como contexto e trabalho futuro, não como método implementado. |
| Metodologia | Descrever C1/C2 como "demanda de entrada estimada a partir do estado atual". |
| Resultados | Apenas o que o Pilot V2 mostrou (ver abaixo). S5 não tem resultados. |

## Orientação de redação do resumo e dos resultados

Resultado científico atual do Pilot V2 (5 seeds, comparação pareada descritiva B2 vs C1):

```text
RESULT_INTERPRETATION = MIXED
RESULT_CONFIDENCE     = MEDIUM
```

- **S1 (balanceado)**: o B2 é melhor que o C1 (C1 piora: espera +44,7%, fila média da rede +44,1%).
- **S2 (direcional)**: trade-off — C1 reduz atraso/fila, mas reduz vazão e razão de conclusão.
- **S3 (mudança de demanda)**: o B2 é melhor que o C1 (C1: espera +24,7%, fila +21,9%, perda de
  tempo pós-choque +11,5%).
- **S4 (saturação localizada em A5)**: o C1 é melhor que o B2 (espera -20,4%, perda de tempo
  -23,3%, fila -17,7%, tempo de viagem -22,1%, vazão +12,0%; com `ALLOW_AND_MEASURE` para
  teleports).

(Valores de `final-audit.md`/`b2-vs-c1-final-comparison.md` do Pilot V2; intervalos de confiança
descritivos.)

**Não escreva** que o controlador cooperativo "reduz de forma geral o tempo de viagem, as paradas e
as filas". O resultado não sustenta superioridade geral do C1; o benefício observado é específico do
regime saturado (S4).

Redação recomendada:

> "Os resultados preliminares do Pilot V2 indicam que o efeito da cooperação depende do regime de
> tráfego: o controlador cooperativo compacto (C1) apresentou benefício em cenário de saturação
> localizada (S4), piora em cenários de tráfego balanceado (S1) e de mudança de demanda (S3) e um
> compromisso (trade-off) entre atraso e vazão no cenário direcional (S2), em comparação com o
> controlador de pressão local (B2). Os resultados são de um piloto com cinco sementes e não
> sustentam uma superioridade geral da cooperação."

Também:

- Descreva o B0 como baseline de tempo fixo de engenharia/referência, **não Webster** e ainda **não
  calibrado**; o baseline final de tempo fixo é o `B0_FIXED_CALIBRATED` (`EMPIRICAL_FIXED_TIME`, calibração
  concluída, ver `fixed-time-calibration.md`).
- Descreva a validade do S3 como obtida por gate composto **post-hoc** (ver
  `scenario-validity-gates.md`).

### S5 (degradação de comunicação)

```text
S5 NÃO foi executado.
```

Nenhum texto do TCC pode apresentar robustez ou limitação sob perda de pacotes como **resultado**
observado. Só pode apresentá-lo como **avaliação planejada** (perda de 0, 20, 50 e 100%, atraso 0,
sobre demanda S2) ou **hipótese**. Ver `docs/experiments.md`.

## Resumo de status

| Item | Estado |
|---|---|
| Controle implementado | Reativo, distribuído e cooperativo |
| ML/RL/previsão | Não implementado (trabalho futuro) |
| Resultado do piloto | MIXED, confiança MEDIUM |
| S5 | Planejado, não executado |
| B0 | Histórico: estático 98 s (Pilot V2). Final: `B0_FIXED_CALIBRATED` (calibrado, 84 s) |
