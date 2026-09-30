# Protocolo Experimental Final V1

Status: fonte de verdade metodológica aprovada para os experimentos finais da V1.

Este protocolo define as comparações científicas, os cenários, as métricas, o
contrato de equidade (fairness) e a política de seeds da campanha final. Ele
substitui notas de planejamento mais antigas em caso de conflito. A campanha
final não deve ser executada até que as divergências de implementação listadas
ao final deste documento sejam resolvidas e congeladas.

Este documento não reporta resultados experimentais. Ele não deve descrever
nenhum controlador como superior antes de existirem os resultados da campanha
final.

As definições operacionais das métricas estão em `docs/methodology/metrics.md`.
Se um nome de métrica aparecer neste protocolo, sua unidade, fonte, agregação,
janela de medição e política para casos extremos estão definidas naquele
documento.

## Pergunta de Pesquisa

Em uma rede urbana simulada, a troca local de informações entre controladores
semafóricos descentralizados melhora o desempenho da rede em comparação com um
controlador adaptativo local sem cooperação e com o controle de tempo fixo, sob
diferentes condições de demanda de tráfego?

A resposta esperada não é definida previamente. Todas as conclusões devem ser
derivadas dos artifacts finais congelados e da análise estatística.

## Controladores e Papéis Experimentais

A campanha final V1 utiliza cinco controladores:

| Controlador | Papel experimental |
|---|---|
| `B0_FIXED` | Controle base tradicional de tempo fixo |
| `B1_LOCAL_ADAPTIVE` | Controlador adaptativo local secundário |
| `B2_LOCAL_PRESSURE` | Controle base adaptativo não cooperativo primário |
| `C1_COOPERATIVE_COMPACT` | Método cooperativo principal |
| `C2_COOPERATIVE_EXPANDED` | Ablação/comparação com comunicação rica |

O controle base de tempo fixo final é o `B0_FIXED`.

O `B0_FIXED` deve ser descrito apenas como um controle base (baseline)
tradicional/estático de tempo fixo. Ele não é otimizado por Webster. Nenhum
baseline `B0_WEBSTER_FIXED` é implementado na V1, e os relatórios da V1 não
devem usar "Webster" como sinônimo de `B0_FIXED`.

Comparação científica primária:

```text
B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT
```

Motivo: `B2_LOCAL_PRESSURE` e `C1_COOPERATIVE_COMPACT` compartilham o núcleo de
pressão local. A principal diferença experimental é o uso, pelo
`C1_COOPERATIVE_COMPACT`, de informações cooperativas dos vizinhos.

Comparações secundárias:

- `B0_FIXED` vs `B2_LOCAL_PRESSURE`
- `B0_FIXED` vs `C1_COOPERATIVE_COMPACT`
- `B2_LOCAL_PRESSURE` vs `C2_COOPERATIVE_EXPANDED`
- `C1_COOPERATIVE_COMPACT` vs `C2_COOPERATIVE_EXPANDED`

## Contrato Comum de Equidade (Fairness)

Para o mesmo cenário e a mesma seed, todos os controladores comparados devem
compartilhar:

- rede
- rotas
- demanda de tráfego
- razões de conversão
- warmup
- duração da medição
- passo de simulação (step length)
- plano de fases
- modelo de movimentos
- restrições de segurança

Somente o comportamento do controlador e, quando projetado, o comportamento de
comunicação podem diferir.

A equidade científica deve ser verificada por meio de invariantes registradas
de forma independente:

- `network_sha256`
- `route_sha256`
- `phase_plan_sha256`
- `movement_model_sha256`
- `turning_config_sha256`

O `scenario_sha256` pode incluir campos de controlador ou de comunicação na
implementação atual e, portanto, não é a fonte de verdade primária de equidade.

## Seeds

Piloto mínimo: 5 seeds distintas.

A seleção das seeds deve ocorrer antes de examinar os resultados comparativos
dos controladores. Não substitua, remova nem reordene seeds porque uma execução
produziu um resultado desfavorável.

Use o pool de seeds planejado existente:

```text
campaign_v1_seed_pool_2026-09-29
42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001
```

O piloto mínimo usa as cinco primeiras seeds:

```text
42, 2027, 3253, 4517, 5791
```

Se uma campanha final maior for aprovada, ela deve usar as próximas seeds na
ordem fixa acima.

## Cenário S1 - Tráfego Balanceado

Definição:

- ID do cenário: `S1_BALANCED`
- Demanda: demanda balanceada a partir de todas as bordas
- Distribuição final de conversões:
  - em frente: `0.70`
  - esquerda: `0.15`
  - direita: `0.15`
- Objetivo: avaliar o comportamento dos controladores sob demanda estável e
  previsível.

Não defina sucesso como "`C1_COOPERATIVE_COMPACT` deve superar o tempo fixo."

Métricas:

- vazão (throughput)
- tempo médio de viagem
- tempo médio de espera
- perda de tempo média (mean time loss)
- fila média
- fila máxima
- média de paradas

## Cenário S2 - Pico Direcional

Definição:

- ID do cenário: `S2_DIRECTIONAL_PEAK`
- Demanda: forte viés de demanda de Oeste para Leste
- Alvo: aproximadamente 80% da demanda injetada associada ao
  corredor/direção dominante
- O comportamento de conversão deve ser preservado. O alvo não significa que
  80% dos veículos devam seguir apenas em frente por toda a rede.
- O cenário deve conter movimentos em frente, à esquerda e à direita.
- Objetivo: avaliar se os controladores locais e cooperativos lidam com um
  fluxo direcional dominante e com demanda semelhante a pelotões (platoons).

Não afirme que existe uma onda verde a menos que ela seja observada nos
artifacts finais usando uma definição explícita.

Métricas:

- média de paradas
- perda de tempo (time loss)
- tempo de viagem no corredor
- vazão no corredor
- vazão da rede
- filas

## Cenário S3 - Mudança Abrupta de Demanda

Definição:

- ID do cenário: `S3_DEMAND_SHIFT`
- Use duas janelas de demanda explícitas.
- Primeiros 50%: tráfego balanceado.
- Últimos 50%: forte choque de demanda direcional/localizado.
- O instante exato de início do choque deve ser congelado antes da campanha.
- Objetivo: avaliar a resposta dos controladores após uma mudança de regime de
  demanda.

Política da métrica de recuperação selecionada:

Os produtos de dados atualmente implementados ainda não definem um limiar
cientificamente defensável para `recovery_time_seconds` sem ajuste arbitrário.
Portanto, o protocolo final da V1 não deve inventar uma métrica de tempo de
recuperação baseada em limiar até que uma regra seja implementada e congelada.

Use estas métricas pós-choque no lugar:

- fila média pós-choque
- fila máxima pós-choque
- área sob a curva de fila após o choque
- perda de tempo pós-choque

## Cenário S4 - Saturação Localizada

Definição:

- ID do cenário: `S4_LOCAL_SATURATION`
- Demanda: forte demanda direcionada à região A5
- O cenário pode intencionalmente se aproximar da capacidade local ou excedê-la.
- Objetivo: avaliar se a cooperação mitiga a propagação de congestionamento
  localizado em comparação com o controle apenas local.

Não afirme que qualquer controlador deva resolver a sobrecarga.

Métricas:

- fila média
- fila máxima
- vazão
- perda de tempo
- tempo de viagem
- ocupação a jusante, quando disponível
- `internal_lane_persistence_events`

`internal_lane_persistence_events` é um proxy para a ocupação persistente da
interseção interna. Não é uma medição direta e universal de spillback, gridlock
ou bloqueio físico.

Não use "duração de gridlock" a menos que uma definição operacional explícita
seja implementada e congelada antes da campanha final.

## Cenário S5 - Degradação da Comunicação

Definição:

- ID do cenário: `S5_COMMUNICATION_DEGRADATION`
- Use um perfil de demanda de tráfego existente, preferencialmente
  `S2_DIRECTIONAL_PEAK`.
- Experimento de perda de pacotes sobre `drop_probability`:
  - `0.00`
  - `0.20`
  - `0.50`
  - `1.00`
- Controladores primários:
  - `C1_COOPERATIVE_COMPACT`
  - `C2_COOPERATIVE_EXPANDED`
- Controlador de referência:
  - `B2_LOCAL_PRESSURE`

Com 100% de perda de pacotes, `C1_COOPERATIVE_COMPACT` e
`C2_COOPERATIVE_EXPANDED` devem recorrer ao comportamento de fallback local.
Não assuma que suas métricas finais serão exatamente iguais às do
`B2_LOCAL_PRESSURE`, a menos que a semântica da implementação garanta
equivalência exata.

Métricas:

- vazão
- tempo de espera
- perda de tempo
- fila
- mensagens de comunicação enviadas
- mensagens de comunicação entregues
- mensagens de comunicação descartadas
- bytes
- idade da mensagem

## Estudo Secundário Opcional de Atraso

`S5B_DELAY` é secundário e opcional. Não é obrigatório para a campanha central
do TCC.

Se executado, use:

- `delay_steps: 0`
- `delay_steps: 1`
- `delay_steps: 3`
- `delay_steps: 5`

O estudo de atraso não deve ser misturado com a comparação obrigatória de perda
de pacotes, a menos que a análise o rotule separadamente.

## Lista Final de Métricas por Cenário

| Cenário | Métricas finais |
|---|---|
| `S1_BALANCED` | vazão; tempo médio de viagem; tempo médio de espera; perda de tempo média; fila média; fila máxima; média de paradas |
| `S2_DIRECTIONAL_PEAK` | média de paradas; perda de tempo; tempo de viagem no corredor; vazão no corredor; vazão da rede; filas |
| `S3_DEMAND_SHIFT` | fila média pós-choque; fila máxima pós-choque; área sob a curva de fila após o choque; perda de tempo pós-choque |
| `S4_LOCAL_SATURATION` | fila média; fila máxima; vazão; perda de tempo; tempo de viagem; ocupação a jusante, quando disponível; `internal_lane_persistence_events` |
| `S5_COMMUNICATION_DEGRADATION` | vazão; tempo de espera; perda de tempo; fila; mensagens enviadas; mensagens entregues; mensagens descartadas; bytes; idade da mensagem |
| `S5B_DELAY` | igual ao S5, reportado separadamente como opcional/secundário |

## Definições Exatas de Cenário a Congelar

Os artifacts executáveis finais devem codificar estas definições antes da
execução da campanha:

| Cenário | Definição de demanda e comunicação |
|---|---|
| `S1_BALANCED` | Demanda balanceada a partir de todas as bordas; razões de conversão em frente `0.70`, esquerda `0.15`, direita `0.15`; sem degradação especial de comunicação na campanha principal |
| `S2_DIRECTIONAL_PEAK` | Forte viés de demanda de Oeste para Leste; aproximadamente 80% da demanda injetada associada ao corredor/direção dominante, preservando movimentos em frente, à esquerda e à direita |
| `S3_DEMAND_SHIFT` | Duas janelas explícitas; primeiros 50% balanceados; últimos 50% com forte choque de demanda direcional/localizado; início do choque congelado antes da campanha |
| `S4_LOCAL_SATURATION` | Forte demanda direcionada a A5; pode se aproximar da capacidade local ou excedê-la |
| `S5_COMMUNICATION_DEGRADATION` | Demanda base existente, preferencialmente S2; matriz de perda de pacotes C1/C2 nas probabilidades de descarte `0.00`, `0.20`, `0.50`, `1.00`; referência B2 |
| `S5B_DELAY` | Matriz de atraso opcional sobre `delay_steps` `0`, `1`, `3`, `5`; reportada separadamente |

## Divergências Atuais de Implementação

Status após a remediação do Pilot V1 (Prompt 46.6): os itens 1 e 3 estão
resolvidos pelos artifacts de cenário regenerados (`scripts/generate_scenarios.py`,
`docs/scenarios.md`); suas intensidades de demanda foram calibradas no Prompt 46.7
(`docs/scenarios.md`). O item 4 é coberto pelo pipeline canônico de métricas
(`docs/methodology/metrics.md`). As métricas de fila são nomeadas por escopo
(`mean_network_queue_vehicles`, `max_network_queue_vehicles`, ..., veja o
documento de métricas); "fila média" e "fila máxima" nas listas de métricas
acima referem-se a essas métricas com escopo.

As seguintes divergências foram listadas antes que a campanha final pudesse ser
congelada ou executada:

1. `S1_BALANCED` usava razões de conversão em frente `0.60`, esquerda `0.20`,
   direita `0.20`, que eram apenas metadados; os cenários agora usam a
   distribuição do protocolo (em frente `0.70`, esquerda `0.15`, direita
   `0.15`) e as razões alimentam o gerador de rotas. (Resolvido.)
2. As configs exploratórias antigas do S5 usam valores de `drop_probability`
   `0.00`, `0.05`, `0.10` e `0.25`, e os combinam com valores de atraso. A
   config central planejada de perda de pacotes do S5 usa `0.00`, `0.20`,
   `0.50` e `1.00`; o atraso permanece como um estudo opcional separado,
   `S5B_DELAY`.
3. A implementação do `S3_DEMAND_SHIFT` precisava ser verificada ou atualizada
   para que seus primeiros 50% fossem balanceados e seus últimos 50% fossem o
   choque direcional/localizado congelado especificado por este protocolo. Ele
   agora tem uma primeira metade semelhante ao S1 e um choque abrupto em uma
   borda roteado por A5 a 50% da janela de MEDIÇÃO
   (`shock_start_seconds = 2100`). (Resolvido; intensidade calibrada no Prompt 46.7.)
4. As métricas específicas de corredor para o S2 e as métricas pós-choque para
   o S3 devem estar disponíveis nas saídas da análise final antes do relatório
   final.

## Trabalho de Implementação Ainda Necessário

Antes de executar a campanha final:

1. Atualizar ou gerar os artifacts de cenário finais para corresponder a este
   protocolo.
2. Manter a contagem final de seeds pendente até que a avaliação do piloto
   esteja concluída.
3. Manter os experimentos de atraso sob o rótulo opcional `S5B_DELAY`, se forem
   executados.
4. Garantir que a análise final inclua as métricas específicas de cenário
   listadas neste protocolo, especialmente as métricas de corredor do S2 e as
   métricas pós-choque do S3.
5. Congelar todas as entradas finais e verificar as invariantes de
   rota/config/hash antes da execução da campanha.

## Ações Proibidas

- Não ajuste controladores com base no desempenho observado.
- Não selecione, remova nem reordene seeds com base no desempenho observado.
- Não altere a lógica dos controladores, a menos que explicitamente exigido por
  este protocolo.
- Não descreva nenhum controlador como superior antes de existirem resultados
  finais.
- Não execute a campanha final antes que os artifacts de cenário finais e as
  entradas congeladas correspondam a este protocolo.
